"""Build the forecast training set: atmospheric features (DWD/LoRaWAN/OpenWeather)
→ SWS road-condition label, for predicting road condition WITHOUT a road sensor.

Each SWS label row (stratified-sampled per class) is matched to each feature
source's most recent prior reading per segment via an ASOF join (the same
"latest at-or-before" logic used for the map moments). Features are assembled by
the SAME non-SWS priority coalesce the fusion engine uses at inference, with unit
harmonization, so training and serving see identical feature semantics.

Output:  data/_training.parquet  (git-ignored via data/_*)

Run:  .venv/bin/python scripts/build_training.py --downloads "/mnt/e/Ice Prediction"
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "_training.parquet"
SEG_DB = ROOT / "data" / "segments.db"

PER_CLASS_CAP = 80000   # stratified cap per condition class


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=Path("/mnt/e/Ice Prediction"))
    args = ap.parse_args()
    base = args.downloads

    import duckdb

    d = duckdb.connect()
    d.execute("PRAGMA threads=4")
    sws = f"{base}/agg_swsdata_2025-06_2025-11.csv"
    dwd = f"{base}/agg_dwddata_2025-06_2025-11.csv"
    lor = f"{base}/agg_lorawan_2025-06_2025-11.csv"
    owm = f"{base}/agg_openweather_by_segment_2025-06_2025-11.csv"

    # segment elevation (a strong ice predictor) from segments.db
    con = sqlite3.connect(SEG_DB)
    elev_rows = con.execute("SELECT segment_id, elevation_m FROM segments").fetchall()
    con.close()
    elev = d.from_df(__import__("pandas").DataFrame(elev_rows, columns=["segment_id", "elevation_m"]))
    d.register("elev", elev)

    print("Stratified-sampling SWS labels ...")
    d.execute(f"""
        CREATE TEMP TABLE lbl AS
        SELECT segment_id, event_timestamp::timestamp AS ts, CAST(road_condition_code AS INT) AS y
        FROM read_csv_auto('{sws}')
        WHERE road_condition_code IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY road_condition_code ORDER BY random()) <= {PER_CLASS_CAP}
    """)
    n = d.execute("SELECT count(*) FROM lbl").fetchone()[0]
    print(f"  {n:,} label rows")

    # feature source tables (needed columns only), sorted for ASOF
    print("Loading feature sources ...")
    d.execute(f"""CREATE TEMP TABLE dwd AS SELECT segment_id, event_timestamp::timestamp ts,
        air_temperature_celsius da, relative_humidity_percent dh, dew_point_celsius dd,
        wind_speed_ms dws, wind_direction_degrees dwd_dir, precipitation_mm dp,
        air_pressure_sea_level_hpa dpr, cloud_cover_oktas dok, visibility_meters dvis,
        soil_temperature_5cm_celsius dsoil FROM read_csv_auto('{dwd}')""")
    d.execute(f"""CREATE TEMP TABLE lor AS SELECT segment_id, event_timestamp::timestamp ts,
        surface_temperature lsurf, air_temperature la, air_humidity lh, dew_point ld
        FROM read_csv_auto('{lor}')""")
    d.execute(f"""CREATE TEMP TABLE owm AS SELECT segment_id, event_timestamp::timestamp ts,
        temp ot, humidity oh, pressure opr, wind_speed ows, wind_deg odir,
        clouds ocl, rain orain, visibility ovis FROM read_csv_auto('{owm}')""")

    print("ASOF-joining features and harmonizing units ...")
    # canonical features via non-SWS priority coalesce (matches fusion.yaml minus sws)
    d.execute(f"""
        COPY (
        SELECT
            lbl.y AS y,
            COALESCE(la, da, ot - 273.15)                       AS air_temp_c,
            COALESCE(lh, dh, oh)                                AS humidity_pct,
            COALESCE(ld, dd)                                    AS dew_point_c,
            lsurf                                               AS road_surface_temp_c,
            dsoil                                               AS subsurface_temp_5cm_c,
            COALESCE(dp, orain * 0.3333333)                     AS precipitation_mm_h,
            COALESCE(dws, ows)                                  AS wind_speed_ms,
            COALESCE(dwd_dir, odir)                             AS wind_direction_deg,
            COALESCE(dpr, opr)                                  AS pressure_hpa,
            COALESCE(dvis, ovis)                                AS visibility_m,
            COALESCE(dok * 12.5, ocl)                           AS cloud_cover_pct,
            elev.elevation_m                                    AS elevation_m
        FROM lbl
        ASOF LEFT JOIN dwd ON lbl.segment_id = dwd.segment_id AND lbl.ts >= dwd.ts
        ASOF LEFT JOIN lor ON lbl.segment_id = lor.segment_id AND lbl.ts >= lor.ts
        ASOF LEFT JOIN owm ON lbl.segment_id = owm.segment_id AND lbl.ts >= owm.ts
        LEFT JOIN elev ON lbl.segment_id = elev.segment_id
        ) TO '{OUT}' (FORMAT PARQUET)
    """)
    total = d.execute(f"SELECT count(*) FROM read_parquet('{OUT}')").fetchone()[0]
    dist = d.execute(f"SELECT y, count(*) FROM read_parquet('{OUT}') GROUP BY 1 ORDER BY 1").fetchall()
    print(f"\nDone → {OUT}  ({total:,} rows)")
    print("  class distribution:", dict(dist))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
