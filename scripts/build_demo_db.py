"""Pre-index the big raw CSVs into a fast local SQLite database.

Reads:
  - LoRaWAN export   (real road-sensor data — has surface_temperature directly)
  - OpenWeatherMap   (atmospheric data — temperature in Kelvin!)

Writes:
  data/demo.db   (gitignored — ~50 MB after indexing both inputs)

Usage:
    python scripts/build_demo_db.py \\
        --lorawan /path/to/lorawanglatteisv3_full_export.csv \\
        --owm     /path/to/openweathermaphofv1_full_export.csv

Why pre-index:
  - 1.6 GB combined → CSV iteration during API calls would be too slow for live demo.
  - SQLite with WAL + indices gives <10 ms lookups regardless of input size.
  - Reproducible: ships with stations.json seeded so /scenarios always works.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "demo.db"
STATIONS_JSON = ROOT / "data" / "stations.json"

KELVIN_OFFSET = 273.15
BATCH_SIZE = 10_000

DEVICE_RX = re.compile(
    r"^(?P<prefix>[A-Z]{3})-TPK-(?P<code>\d{4})-N(?P<lat>\d+\.\d+)-E(?P<lon>\d+\.\d+)$"
)


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS stations (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    lat         REAL,
    lon         REAL,
    source      TEXT,
    is_demo     INTEGER DEFAULT 0,
    profile_tag TEXT
);

CREATE TABLE IF NOT EXISTS lorawan_obs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp            TEXT NOT NULL,
    device_name          TEXT NOT NULL,
    station_prefix       TEXT,
    lat                  REAL,
    lon                  REAL,
    air_temperature      REAL,
    air_humidity         REAL,
    dew_point            REAL,
    surface_temperature  REAL,
    sensor_temperature   REAL,
    battery_voltage      REAL
);
CREATE INDEX IF NOT EXISTS idx_lorawan_device_ts ON lorawan_obs(device_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_lorawan_ts        ON lorawan_obs(timestamp);

CREATE TABLE IF NOT EXISTS owm_obs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    city        TEXT NOT NULL,
    lat         REAL,
    lon         REAL,
    temp_c      REAL,
    temp_min_c  REAL,
    temp_max_c  REAL,
    humidity    REAL,
    wind_speed  REAL,
    wind_deg    REAL,
    clouds      REAL,
    rain        REAL,
    pressure    REAL,
    weather_id  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_owm_city_ts ON owm_obs(city, timestamp);
CREATE INDEX IF NOT EXISTS idx_owm_ts      ON owm_obs(timestamp);
"""


def to_float(v: str | None) -> float | None:
    if v in (None, "", "NaN", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_int(v: str | None) -> int | None:
    f = to_float(v)
    return int(f) if f is not None else None


def kelvin_to_c(k: float | None) -> float | None:
    return None if k is None else round(k - KELVIN_OFFSET, 3)


@contextmanager
def progress(label: str):
    start = time.time()
    print(f"→ {label} …", flush=True)
    yield
    print(f"  ✓ {label} in {time.time() - start:.1f}s", flush=True)


def seed_stations(conn: sqlite3.Connection) -> None:
    data = json.loads(STATIONS_JSON.read_text(encoding="utf-8"))
    rows = [
        (s["id"], s["name"], s["lat"], s["lon"], s["source"],
         1 if s.get("is_demo") else 0, s.get("profile_tag"))
        for s in data["stations"]
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO stations(id,name,lat,lon,source,is_demo,profile_tag) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"  seeded {len(rows)} demo stations")


def parse_device(name: str) -> tuple[str | None, float | None, float | None]:
    m = DEVICE_RX.match(name or "")
    if not m:
        return None, None, None
    return m.group("prefix"), float(m.group("lat")), float(m.group("lon"))


def import_lorawan(conn: sqlite3.Connection, path: Path) -> int:
    conn.execute("DELETE FROM lorawan_obs")
    rows_inserted = 0
    batch: list[tuple] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            device = row.get("deviceName", "")
            prefix, dev_lat, dev_lon = parse_device(device)
            batch.append((
                row.get("event_timestamp", "")[:19],
                device,
                prefix,
                dev_lat if dev_lat is not None else to_float(row.get("rxLatitude")),
                dev_lon if dev_lon is not None else to_float(row.get("rxLongitude")),
                to_float(row.get("air_temperature")),
                to_float(row.get("air_humidity")),
                to_float(row.get("dew_point")),
                to_float(row.get("surface_temperature")),
                to_float(row.get("sensor_temperature")),
                to_float(row.get("battery_voltage")),
            ))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO lorawan_obs(timestamp,device_name,station_prefix,lat,lon,"
                    "air_temperature,air_humidity,dew_point,surface_temperature,"
                    "sensor_temperature,battery_voltage) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                rows_inserted += len(batch)
                batch.clear()
                if rows_inserted % 500_000 == 0:
                    print(f"    {rows_inserted:>10,} rows", flush=True)
        if batch:
            conn.executemany(
                "INSERT INTO lorawan_obs(timestamp,device_name,station_prefix,lat,lon,"
                "air_temperature,air_humidity,dew_point,surface_temperature,"
                "sensor_temperature,battery_voltage) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            rows_inserted += len(batch)

    conn.commit()
    return rows_inserted


def import_owm(conn: sqlite3.Connection, path: Path) -> int:
    conn.execute("DELETE FROM owm_obs")
    rows_inserted = 0
    batch: list[tuple] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch.append((
                row.get("event_timestamp", "")[:19],
                row.get("city", ""),
                to_float(row.get("lat")),
                to_float(row.get("lon")),
                kelvin_to_c(to_float(row.get("temp"))),
                kelvin_to_c(to_float(row.get("temp_min"))),
                kelvin_to_c(to_float(row.get("temp_max"))),
                to_float(row.get("humidity")),
                to_float(row.get("wind_speed")),
                to_float(row.get("wind_deg")),
                to_float(row.get("clouds")),
                to_float(row.get("rain")),
                to_float(row.get("pressure")),
                to_int(row.get("weather_id")),
            ))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO owm_obs(timestamp,city,lat,lon,temp_c,temp_min_c,temp_max_c,"
                    "humidity,wind_speed,wind_deg,clouds,rain,pressure,weather_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                rows_inserted += len(batch)
                batch.clear()
                if rows_inserted % 500_000 == 0:
                    print(f"    {rows_inserted:>10,} rows", flush=True)
        if batch:
            conn.executemany(
                "INSERT INTO owm_obs(timestamp,city,lat,lon,temp_c,temp_min_c,temp_max_c,"
                "humidity,wind_speed,wind_deg,clouds,rain,pressure,weather_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            rows_inserted += len(batch)

    conn.commit()
    return rows_inserted


def summarize(conn: sqlite3.Connection) -> None:
    print("\n── Summary ──")
    for table, label in [
        ("stations", "demo stations"),
        ("lorawan_obs", "LoRaWAN observations"),
        ("owm_obs", "OpenWeatherMap observations"),
    ]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {label:30s} {n:>12,}")

    n_devices = conn.execute(
        "SELECT COUNT(DISTINCT device_name) FROM lorawan_obs"
    ).fetchone()[0]
    n_cities = conn.execute(
        "SELECT COUNT(DISTINCT city) FROM owm_obs"
    ).fetchone()[0]
    print(f"  unique LoRaWAN devices         {n_devices:>12,}")
    print(f"  unique OWM cities              {n_cities:>12,}")

    size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"  demo.db size                   {size_mb:>10.1f} MB")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lorawan", type=Path, help="Path to LoRaWAN export CSV")
    ap.add_argument("--owm", type=Path, help="Path to OpenWeatherMap export CSV")
    ap.add_argument(
        "--rebuild", action="store_true",
        help="Delete existing demo.db before importing",
    )
    args = ap.parse_args()

    if not (args.lorawan or args.owm):
        ap.error("Provide at least one of --lorawan or --owm")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.rebuild and DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    with progress("Seed stations"):
        seed_stations(conn)

    if args.lorawan:
        if not args.lorawan.exists():
            sys.exit(f"LoRaWAN CSV not found: {args.lorawan}")
        with progress(f"Import LoRaWAN ({args.lorawan.name})"):
            n = import_lorawan(conn, args.lorawan)
            print(f"  inserted {n:,} rows")

    if args.owm:
        if not args.owm.exists():
            sys.exit(f"OWM CSV not found: {args.owm}")
        with progress(f"Import OpenWeatherMap ({args.owm.name})"):
            n = import_owm(conn, args.owm)
            print(f"  inserted {n:,} rows")

    with progress("ANALYZE (query planner stats)"):
        conn.executescript("ANALYZE;")

    summarize(conn)
    conn.close()
    print(f"\n✓ Demo database ready: {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
