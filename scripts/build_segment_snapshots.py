"""Build the road-segment demo store: geometry + latest reading per source.

Inputs (defaults point at ~/Downloads; override with CLI flags):
  - road_segments_with_elevation.parquet   (geometry in EPSG:25832 + elevation)
  - agg_swsdata_*.csv                       (SWS road stations  — ground truth)
  - agg_lorawan_*.csv                       (LoRaWAN sensors)
  - agg_dwddata_*.csv                       (DWD climate)
  - agg_openweather_by_segment_*.csv        (OpenWeather)

Output: data/segments.db  (tiny, offline, demo-safe)
  - segments         : one row per road segment (geometry as WGS84 WKT + centroid)
  - segment_snapshot : latest reading per (segment_id, source), raw fields as JSON

Strategy: DuckDB streams each multi-GB CSV and keeps only the most recent row per
segment (window function), so memory stays flat and the result is a few thousand rows.

Run:  .venv/bin/python scripts/build_segment_snapshots.py --rebuild
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOADS = Path("/mnt/c/Users/ASUS/Downloads")
OUT_DB = ROOT / "data" / "segments.db"

# source name -> default CSV filename (glob-matched in the downloads dir)
SOURCE_FILES = {
    "sws":         "agg_swsdata_*.csv",
    "lorawan":     "agg_lorawan_*.csv",
    "dwd":         "agg_dwddata_*.csv",
    "openweather": "agg_openweather_by_segment_*.csv",
}

# Source CRS of the parquet geometry. predict_forecast.py confirms the values are
# UTM zone 32N metres (EPSG:25832) even where mislabelled; we transform to WGS84.
SRC_CRS = "EPSG:25832"
DST_CRS = "EPSG:4326"


def _find(downloads: Path, pattern: str) -> Path | None:
    hits = sorted(downloads.glob(pattern))
    return hits[0] if hits else None


def build_segments(con: sqlite3.Connection, parquet: Path) -> int:
    import pandas as pd
    from pyproj import Transformer
    from shapely import wkb as shapely_wkb
    from shapely.ops import transform as shp_transform

    df = pd.read_parquet(parquet)
    tf = Transformer.from_crs(SRC_CRS, DST_CRS, always_xy=True)

    con.execute("DROP TABLE IF EXISTS segments")
    con.execute(
        """
        CREATE TABLE segments (
            segment_id        INTEGER PRIMARY KEY,
            road_id           INTEGER,
            road_class        TEXT,
            road_number       INTEGER,
            road_name         TEXT,
            length_km         REAL,
            elevation_m       REAL,
            elevation_range_m REAL,
            geom_wkt          TEXT,   -- WGS84 (lon lat) LineString
            lat               REAL,   -- centroid
            lon               REAL
        )
        """
    )

    rows = []
    for _, r in df.iterrows():
        geom = shapely_wkb.loads(bytes(r["geometry"]))
        geom_wgs = shp_transform(lambda x, y, z=None: tf.transform(x, y), geom)
        c = geom_wgs.centroid
        rows.append((
            int(r["segment_id"]),
            int(r["road_id"]) if pd.notna(r["road_id"]) else None,
            r.get("Straßenklasse (String)") or r.get("Straßenklasse"),
            int(r["Straßennummer"]) if pd.notna(r.get("Straßennummer")) else None,
            r.get("Straßenbezeichnung (String)") or r.get("Straßenbezeichnung"),
            float(r["Länge"]) if pd.notna(r.get("Länge")) else None,
            float(r["elevation_m"]) if pd.notna(r.get("elevation_m")) else None,
            float(r["elevation_range_m"]) if pd.notna(r.get("elevation_range_m")) else None,
            geom_wgs.wkt,
            float(c.y),
            float(c.x),
        ))
    con.executemany(
        "INSERT OR REPLACE INTO segments VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    con.commit()
    return len(rows)


def build_snapshots(con: sqlite3.Connection, downloads: Path) -> dict[str, int]:
    import duckdb

    con.execute("DROP TABLE IF EXISTS segment_snapshot")
    con.execute(
        """
        CREATE TABLE segment_snapshot (
            segment_id      INTEGER,
            source          TEXT,
            event_timestamp TEXT,
            raw_json        TEXT,
            PRIMARY KEY (segment_id, source)
        )
        """
    )

    counts: dict[str, int] = {}
    duck = duckdb.connect()
    for source, pattern in SOURCE_FILES.items():
        path = _find(downloads, pattern)
        if not path:
            print(f"  [{source}] file not found ({pattern}) — skipping")
            counts[source] = 0
            continue

        cols = [c[0] for c in duck.execute(
            f"DESCRIBE SELECT * FROM read_csv_auto('{path}')"
        ).fetchall()]
        seg_col = next(c for c in cols if "segment_id" in c.lower())
        ts_col = next(c for c in cols if "event_timestamp" in c.lower())

        # latest row per segment via window function — streams the whole file
        q = f"""
            SELECT * EXCLUDE (_rn) FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY "{seg_col}" ORDER BY "{ts_col}" DESC
                ) AS _rn
                FROM read_csv_auto('{path}')
            ) WHERE _rn = 1
        """
        df = duck.execute(q).fetchdf()

        rows = []
        skip = {seg_col, ts_col, "inserted_at"}
        for _, r in df.iterrows():
            raw = {k: (None if (v != v) else v)  # NaN -> None
                   for k, v in r.items() if k not in skip}
            # JSON-safe (numpy types -> python)
            raw = json.loads(json.dumps(raw, default=lambda o: float(o)))
            rows.append((
                int(r[seg_col]),
                source,
                str(r[ts_col]),
                json.dumps(raw),
            ))
        con.executemany(
            "INSERT OR REPLACE INTO segment_snapshot VALUES (?,?,?,?)", rows
        )
        con.commit()
        counts[source] = len(rows)
        print(f"  [{source}] {len(rows):,} segments  (latest from {path.name})")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=DEFAULT_DOWNLOADS,
                    help="directory holding the parquet + agg CSVs")
    ap.add_argument("--parquet", type=Path, default=None)
    ap.add_argument("--rebuild", action="store_true",
                    help="overwrite an existing segments.db")
    args = ap.parse_args()

    parquet = args.parquet or _find(args.downloads, "road_segments_with_elevation.parquet")
    if not parquet or not parquet.exists():
        sys.stderr.write("Parquet not found. Pass --parquet or --downloads.\n")
        return 1

    if OUT_DB.exists() and not args.rebuild:
        sys.stderr.write(f"{OUT_DB} exists. Use --rebuild to overwrite.\n")
        return 1
    OUT_DB.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(OUT_DB)
    con.execute("PRAGMA journal_mode=WAL")

    print(f"Building segments from {parquet.name} ...")
    n_seg = build_segments(con, parquet)
    print(f"  {n_seg:,} road segments (geometry → WGS84)")

    print("Building latest-per-segment snapshots ...")
    counts = build_snapshots(con, args.downloads)

    con.close()
    total = sum(counts.values())
    print(f"\nDone → {OUT_DB}")
    print(f"  segments: {n_seg:,}  |  snapshot rows: {total:,}  ({counts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
