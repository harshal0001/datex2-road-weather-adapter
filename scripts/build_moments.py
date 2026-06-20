"""Build named historical 'moments' into segments.db for the map time-selector.

Each moment is a real timestamp from the data (e.g. the 2025-11-24 ice event). For
every source we take each segment's most recent reading at-or-before the moment
(within a lookback window), so the map can show authentic ice/snow conditions —
not synthetic data.

Adds table:  segment_moment(moment, segment_id, source, event_timestamp, raw_json)

Run:  .venv/bin/python scripts/build_moments.py --downloads "/mnt/e/Ice Prediction"
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DB = ROOT / "data" / "segments.db"

SOURCE_FILES = {
    "sws": "agg_swsdata_*.csv",
    "lorawan": "agg_lorawan_*.csv",
    "dwd": "agg_dwddata_*.csv",
    "openweather": "agg_openweather_by_segment_*.csv",
}

# Real timestamps discovered in the data (UTC, naive).
MOMENTS = [
    {"id": "ice-event-night", "label": "Ice event — 24 Nov 03:00 (643 ice, 180 snow)",
     "ts": "2025-11-24 03:00:00"},
    {"id": "hard-freeze", "label": "Hard freeze — 24 Nov 00:00 (696 ice)",
     "ts": "2025-11-24 00:00:00"},
    {"id": "wet-autumn", "label": "Wet autumn day — 23 Oct 12:00 (870 wet)",
     "ts": "2025-10-23 12:00:00"},
]
LOOKBACK_HOURS = 6


def _find(downloads: Path, pattern: str) -> Path | None:
    hits = sorted(downloads.glob(pattern))
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=Path("/mnt/e/Ice Prediction"))
    args = ap.parse_args()

    if not OUT_DB.exists():
        sys.stderr.write(f"{OUT_DB} not found — run build_segment_snapshots.py first.\n")
        return 1

    import duckdb

    con = sqlite3.connect(OUT_DB)
    con.execute("DROP TABLE IF EXISTS segment_moment")
    con.execute(
        """
        CREATE TABLE segment_moment (
            moment          TEXT,
            segment_id      INTEGER,
            source          TEXT,
            event_timestamp TEXT,
            raw_json        TEXT,
            PRIMARY KEY (moment, segment_id, source)
        )
        """
    )
    con.execute("CREATE INDEX idx_moment ON segment_moment(moment)")
    con.execute("DROP TABLE IF EXISTS moment_meta")
    con.execute("CREATE TABLE moment_meta (moment TEXT PRIMARY KEY, label TEXT)")
    con.executemany(
        "INSERT INTO moment_meta VALUES (?,?)",
        [(m["id"], m["label"]) for m in MOMENTS],
    )
    con.commit()

    duck = duckdb.connect()
    for moment in MOMENTS:
        total = 0
        for source, pattern in SOURCE_FILES.items():
            path = _find(args.downloads, pattern)
            if not path:
                print(f"  [{moment['id']}/{source}] file missing — skip")
                continue
            cols = [c[0] for c in duck.execute(
                f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchall()]
            seg_col = next(c for c in cols if "segment_id" in c.lower())
            ts_col = next(c for c in cols if "event_timestamp" in c.lower())
            q = f"""
                SELECT * EXCLUDE (_rn) FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY "{seg_col}" ORDER BY "{ts_col}" DESC) AS _rn
                    FROM read_csv_auto('{path}')
                    WHERE "{ts_col}"::timestamp <= TIMESTAMP '{moment['ts']}'
                      AND "{ts_col}"::timestamp >= TIMESTAMP '{moment['ts']}'
                          - INTERVAL {LOOKBACK_HOURS} HOUR
                ) WHERE _rn = 1
            """
            df = duck.execute(q).fetchdf()
            rows = []
            skip = {seg_col, ts_col, "inserted_at"}
            for _, r in df.iterrows():
                raw = {k: (None if v != v else v) for k, v in r.items() if k not in skip}
                raw = json.loads(json.dumps(raw, default=lambda o: float(o)))
                rows.append((moment["id"], int(r[seg_col]), source, str(r[ts_col]),
                             json.dumps(raw)))
            con.executemany("INSERT OR REPLACE INTO segment_moment VALUES (?,?,?,?,?)", rows)
            con.commit()
            total += len(rows)
        print(f"  [{moment['id']}] {total} rows  ({moment['label']})")

    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    print(f"\nDone → {OUT_DB} (segment_moment)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
