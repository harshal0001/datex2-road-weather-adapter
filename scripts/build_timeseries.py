"""Build an hourly time series of per-segment snapshots for the map time slider.

Adds, for each timestamp in a window, a `segment_moment` row per (segment, source)
with each segment's most recent reading at-or-before that timestamp (within a
lookback). Timestamp moments use id `ts:<iso>` so they are distinct from the named
moments built by build_moments.py; this script is additive and idempotent (it only
rewrites its own `ts:` rows).

Each big source CSV is scanned ONCE into an in-memory window, then sliced per hour.

Run:  .venv/bin/python scripts/build_timeseries.py --downloads "/mnt/e/Ice Prediction"
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DB = ROOT / "data" / "segments.db"

SOURCE_FILES = {
    "sws": "agg_swsdata_*.csv",
    "lorawan": "agg_lorawan_*.csv",
    "dwd": "agg_dwddata_*.csv",
    "openweather": "agg_openweather_by_segment_*.csv",
}

# Window around the 24 Nov 2025 ice event (UTC, naive) — hourly steps.
WINDOW_START = datetime(2025, 11, 23, 12, 0)
WINDOW_END = datetime(2025, 11, 24, 18, 0)
STEP_HOURS = 1
LOOKBACK_HOURS = 6


def _find(downloads: Path, pattern: str) -> Path | None:
    hits = sorted(downloads.glob(pattern))
    return hits[0] if hits else None


def _steps() -> list[datetime]:
    out, t = [], WINDOW_START
    while t <= WINDOW_END:
        out.append(t)
        t += timedelta(hours=STEP_HOURS)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=Path("/mnt/e/Ice Prediction"))
    args = ap.parse_args()

    if not OUT_DB.exists():
        sys.stderr.write(f"{OUT_DB} not found — run build_segment_snapshots.py first.\n")
        return 1

    import duckdb

    steps = _steps()
    print(f"Building {len(steps)} hourly steps "
          f"({WINDOW_START:%d %b %H:%M} → {WINDOW_END:%d %b %H:%M}) ...")

    con = sqlite3.connect(OUT_DB)
    # tables may already exist (named moments live here too) — create if absent
    con.execute(
        """CREATE TABLE IF NOT EXISTS segment_moment (
            moment TEXT, segment_id INTEGER, source TEXT,
            event_timestamp TEXT, raw_json TEXT,
            PRIMARY KEY (moment, segment_id, source))"""
    )
    con.execute("CREATE TABLE IF NOT EXISTS moment_meta (moment TEXT PRIMARY KEY, label TEXT)")
    # idempotent: clear any prior time-series rows
    con.execute("DELETE FROM segment_moment WHERE moment LIKE 'ts:%'")
    con.execute("DELETE FROM moment_meta WHERE moment LIKE 'ts:%'")
    con.commit()

    duck = duckdb.connect()
    win_lo = (WINDOW_START - timedelta(hours=LOOKBACK_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    win_hi = WINDOW_END.strftime("%Y-%m-%d %H:%M:%S")

    # one full scan per source into an in-memory window
    src_meta = {}
    for source, pattern in SOURCE_FILES.items():
        path = _find(args.downloads, pattern)
        if not path:
            print(f"  [{source}] file missing — skip")
            continue
        cols = [c[0] for c in duck.execute(
            f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchall()]
        seg_col = next(c for c in cols if "segment_id" in c.lower())
        ts_col = next(c for c in cols if "event_timestamp" in c.lower())
        print(f"  [{source}] scanning window from {path.name} ...")
        duck.execute(f"DROP TABLE IF EXISTS w_{source}")
        duck.execute(
            f"""CREATE TEMP TABLE w_{source} AS
                SELECT * FROM read_csv_auto('{path}')
                WHERE "{ts_col}"::timestamp BETWEEN TIMESTAMP '{win_lo}'
                                               AND TIMESTAMP '{win_hi}'"""
        )
        n = duck.execute(f"SELECT count(*) FROM w_{source}").fetchone()[0]
        src_meta[source] = (seg_col, ts_col)
        print(f"      {n:,} rows in window")

    for ts in steps:
        mid = "ts:" + ts.strftime("%Y-%m-%dT%H:%M")
        tss = ts.strftime("%Y-%m-%d %H:%M:%S")
        total = 0
        for source, (seg_col, ts_col) in src_meta.items():
            q = f"""
                SELECT * EXCLUDE (_rn) FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY "{seg_col}" ORDER BY "{ts_col}" DESC) AS _rn
                    FROM w_{source}
                    WHERE "{ts_col}"::timestamp <= TIMESTAMP '{tss}'
                      AND "{ts_col}"::timestamp >= TIMESTAMP '{tss}'
                          - INTERVAL {LOOKBACK_HOURS} HOUR
                ) WHERE _rn = 1
            """
            df = duck.execute(q).fetchdf()
            skip = {seg_col, ts_col, "inserted_at"}
            rows = []
            for _, r in df.iterrows():
                raw = {k: (None if v != v else v) for k, v in r.items() if k not in skip}
                raw = json.loads(json.dumps(raw, default=lambda o: float(o)))
                rows.append((mid, int(r[seg_col]), source, str(r[ts_col]), json.dumps(raw)))
            con.executemany("INSERT OR REPLACE INTO segment_moment VALUES (?,?,?,?,?)", rows)
            total += len(rows)
        con.execute("INSERT OR REPLACE INTO moment_meta VALUES (?,?)",
                    (mid, ts.strftime("%d %b %H:%M")))
        con.commit()
        print(f"  [{mid}] {total} rows")

    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print(f"\nDone → {OUT_DB} ({len(steps)} time steps as ts:* moments)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
