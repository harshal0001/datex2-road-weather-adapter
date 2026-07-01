"""Extract the real physical sensor stations (with coordinates) from the raw
*_full_export.csv files into a small committed file the dashboard can draw.

The aggregated/segment-keyed pipeline drops station identity; the full exports keep
it. This pulls the DISTINCT stations per source and, for **every dashboard moment**,
each station's reading **at-or-before that moment's timestamp** — so the sensor
markers share one coherent instant with the fused segment snapshot (no more markers
stuck in 2026 while the selected segment shows late-2025).

  SWS  →  station_id (P0xx) + lat/lon            (the in-road condition sensors)
  LoRaWAN → deviceName + coords (parsed/columns)
  DWD  →  station_id + lat/lon
  OWM  →  city + lat/lon

Moments come from segments.db (`segment_moment` + the `latest` snapshot), so the
sensor layer and the segment layer are driven by the *same* time reference.

Output:  data/sensors.json   (committed) — shape:
  { "moments": { "<moment_id>": {"counts": {...}, "sensors": [ {..., "ts", "reading"} ]}, ... } }

Run:  .venv/bin/python scripts/build_sensors.py --downloads "/mnt/e/Ice Prediction"
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sensors.json"
SEG_DB = ROOT / "data" / "segments.db"

FILES = {
    "sws": "swsweatherreports_full_export.csv",
    "lorawan": "lorawanglatteisv3_full_export.csv",
    "dwd": "dwdclimateweatherhourly_full_export.csv",
    "openweather": "openweathermaphofv1_full_export.csv",
}
_DEVNAME_COORDS = re.compile(r"N(-?\d+\.\d+)-E(-?\d+\.\d+)")


def _clean(v):
    return None if (v is None or v != v) else v   # NaN/None → None


def _ts(v):
    """event_timestamp → ISO-ish string the dashboard can show ('as of …')."""
    return None if (v is None or v != v) else str(v)


def _moment_refs() -> dict[str, str]:
    """{moment_id: reference timestamp} from segments.db — the SAME instants the
    fused segment layer uses, so both layers stay in lock-step."""
    refs: dict[str, str] = {}
    if not SEG_DB.exists():
        raise SystemExit(f"{SEG_DB} not found — run build_segment_snapshots.py first")
    con = sqlite3.connect(SEG_DB)
    try:
        for moment, ts in con.execute(
            "SELECT moment, max(event_timestamp) FROM segment_moment GROUP BY moment"
        ):
            if ts:
                refs[moment] = ts
        latest = con.execute("SELECT max(event_timestamp) FROM segment_snapshot").fetchone()[0]
        if latest:
            refs["latest"] = latest
    finally:
        con.close()
    return refs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=Path("/mnt/e/Ice Prediction"))
    # A station whose newest reading is older than this (relative to the moment) is
    # treated as offline at that moment and dropped — so we don't show a marker
    # "as of 2024" next to a late-2025 snapshot. 0 disables the filter.
    ap.add_argument("--max-staleness-hours", type=float, default=48.0)
    args = ap.parse_args()
    base = args.downloads
    max_stale = args.max_staleness_hours

    import duckdb

    refs = _moment_refs()
    print(f"Moments: {len(refs)} (latest + named + hourly steps)")
    refs_values = ",\n".join(
        f"('{m}', TIMESTAMPTZ '{ts}')" for m, ts in refs.items()
    )
    ref_dt = {m: datetime.fromisoformat(ts) for m, ts in refs.items()}

    def too_stale(moment, ts) -> bool:
        """True if this station's reading is missing or older than the cutoff."""
        if ts is None:
            return True
        if not max_stale:
            return False
        r = ref_dt.get(moment)
        try:
            return (r - ts) > timedelta(hours=max_stale)
        except TypeError:
            return False

    d = duckdb.connect()
    d.execute("PRAGMA threads=4")

    by_moment: dict[str, list] = defaultdict(list)
    counts_by_moment: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    def readings_per_moment(path, part_col, cols):
        """For each (station, moment): the station's row at-or-before the moment ref.

        Returns rows of (moment, station, ts, *cols) via a single ASOF join.
        """
        sel = ", ".join(f'"{c}"' for c in cols)
        rsel = ", ".join(f'R."{c}"' for c in cols)
        q = f"""
            WITH refs(moment, ts_m) AS (VALUES {refs_values}),
            R AS (
                SELECT "{part_col}" AS station,
                       TRY_CAST("event_timestamp" AS TIMESTAMPTZ) AS ts,
                       {sel}
                FROM read_csv_auto('{path}')
            ),
            S AS (SELECT DISTINCT station FROM R WHERE station IS NOT NULL),
            SM AS (SELECT S.station, refs.moment, refs.ts_m FROM S CROSS JOIN refs)
            SELECT SM.moment, SM.station, R.ts, {rsel}
            FROM SM ASOF LEFT JOIN R
              ON SM.ts_m >= R.ts AND SM.station = R.station
        """
        return d.execute(q).fetchall()

    # ---- SWS: in-road road-weather stations ----
    p = base / FILES["sws"]
    if p.exists():
        for moment, sid, ts, lat, lon, code, st, at, hum in readings_per_moment(
            p, "station_id",
            ["latitude", "longitude", "road_condition_code",
             "road_surface_temperature_celsius", "air_temperature_celsius",
             "relative_humidity_percent"],
        ):
            if too_stale(moment, ts) or lat is None or lon is None:
                continue
            by_moment[moment].append({"source": "sws", "id": sid, "name": sid,
                            "lat": float(lat), "lon": float(lon), "ts": _ts(ts),
                            "reading": {"condition_code": _clean(code),
                                        "surface_temp_c": _clean(st),
                                        "air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum)}})
            counts_by_moment[moment]["sws"] += 1
        print("  [sws] done")

    # ---- LoRaWAN: IoT devices (coords parsed from deviceName, fallback columns) ----
    p = base / FILES["lorawan"]
    if p.exists():
        for moment, name, ts, lat, lon, st, at, hum in readings_per_moment(
            p, "deviceName",
            ["lat", "lon", "surface_temperature", "air_temperature", "air_humidity"],
        ):
            if too_stale(moment, ts) or not name:
                continue
            m = _DEVNAME_COORDS.search(str(name))
            la, lo = (float(m.group(1)), float(m.group(2))) if m else (_clean(lat), _clean(lon))
            if la is None or lo is None:
                continue
            by_moment[moment].append({"source": "lorawan", "id": name,
                            "name": str(name).split("-N")[0],
                            "lat": float(la), "lon": float(lo), "ts": _ts(ts),
                            "reading": {"surface_temp_c": _clean(st),
                                        "air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum)}})
            counts_by_moment[moment]["lorawan"] += 1
        print("  [lorawan] done")

    # ---- DWD: the Hof climate station ----
    p = base / FILES["dwd"]
    if p.exists():
        for moment, sid, ts, lat, lon, at, hum, ok in readings_per_moment(
            p, "station_id",
            ["latitude", "longitude", "air_temperature_celsius",
             "relative_humidity_percent", "cloud_cover_oktas"],
        ):
            if too_stale(moment, ts) or lat is None or lon is None:
                continue
            by_moment[moment].append({"source": "dwd", "id": str(sid), "name": f"DWD {sid}",
                            "lat": float(lat), "lon": float(lon), "ts": _ts(ts),
                            "reading": {"air_temp_c": _clean(at),
                                        "humidity_pct": _clean(hum),
                                        "cloud_oktas": _clean(ok)}})
            counts_by_moment[moment]["dwd"] += 1
        print("  [dwd] done")

    # ---- OpenWeather: city points ----
    p = base / FILES["openweather"]
    if p.exists():
        for moment, city, ts, lat, lon, temp, hum, cl in readings_per_moment(
            p, "city",
            ["lat", "lon", "temp", "humidity", "clouds"],
        ):
            if too_stale(moment, ts) or lat is None or lon is None:
                continue
            t = _clean(temp)
            by_moment[moment].append({"source": "openweather", "id": str(city), "name": str(city),
                            "lat": float(lat), "lon": float(lon), "ts": _ts(ts),
                            "reading": {"air_temp_c": (round(t - 273.15, 1) if t is not None else None),
                                        "humidity_pct": _clean(hum),
                                        "clouds_pct": _clean(cl)}})
            counts_by_moment[moment]["openweather"] += 1
        print("  [openweather] done")

    moments = {
        m: {"counts": dict(counts_by_moment[m]), "sensors": by_moment[m]}
        for m in sorted(by_moment)
    }
    OUT.write_text(json.dumps({"moments": moments}, indent=1), encoding="utf-8")
    latest = moments.get("latest", {})
    print(f"Done → {OUT}")
    print(f"  {len(moments)} moments · latest counts: {latest.get('counts')}"
          f" ({len(latest.get('sensors', []))} stations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
