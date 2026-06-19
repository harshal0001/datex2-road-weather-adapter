"""Evaluation harness — produces thesis Results numbers.

Measures, over the real Hof road network (segments.db):
  1. Transform latency (raw fused segment → DATEX II XML) — p50/p95/max.
  2. DATEX II conformance — % of a validation sample that passes the official XSD.
  3. Condition distribution + source provenance (which source supplied each field).

Run:  .venv/bin/python scripts/evaluate.py [--validate-sample N]
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # import generated/ etc.

from adapter.segments import ALL_SOURCES, fuse_segments
from adapter.validator import validate
from outputs.datex_segment import segment_to_datex


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-sample", type=int, default=150,
                    help="how many segments to XSD-validate (0 = all)")
    args = ap.parse_args()

    print("Fusing all segments (all sources)…")
    fused = fuse_segments(ALL_SOURCES)
    n = len(fused)
    print(f"  {n} segments\n")

    # 1. transform latency (build DATEX for every segment)
    times_ms = []
    for fs in fused:
        t0 = time.perf_counter()
        segment_to_datex(fs, ALL_SOURCES)
        times_ms.append((time.perf_counter() - t0) * 1000)
    times_ms.sort()

    def pct(p):
        return times_ms[min(len(times_ms) - 1, int(p / 100 * len(times_ms)))]

    print("== Transform latency (raw → DATEX II XML) ==")
    print(f"  mean {statistics.mean(times_ms):.2f} ms | p50 {pct(50):.2f} | "
          f"p95 {pct(95):.2f} | max {max(times_ms):.2f} ms")
    print(f"  throughput ≈ {1000 / statistics.mean(times_ms):.0f} segments/s/core\n")

    # 2. conformance
    sample = fused if args.validate_sample == 0 else fused[: args.validate_sample]
    print(f"== DATEX II conformance (XSD-validating {len(sample)} segments) ==")
    valid = 0
    first_errors: list[str] = []
    for fs in sample:
        res = validate(segment_to_datex(fs, ALL_SOURCES))
        if res.valid:
            valid += 1
        elif not first_errors:
            first_errors = res.errors[:3]
    pct_valid = 100 * valid / len(sample)
    print(f"  {valid}/{len(sample)} valid ({pct_valid:.1f}%)")
    if first_errors:
        print(f"  first failure: {first_errors}")
    print()

    # 3. distribution + provenance
    print("== Condition distribution (all sources fused) ==")
    for cond, c in Counter(fs.condition_label for fs in fused).most_common():
        print(f"  {cond:10} {c:5}  ({100*c/n:.1f}%)")
    print("\n== Provenance: which source supplied the field ==")
    for field in ("surface_condition", "road_surface_temp_c", "air_temp_c", "pressure_hpa"):
        prov = Counter(fs.fusion.fields[field].source or "—" for fs in fused
                       if field in fs.fusion.fields)
        print(f"  {field:22} {dict(prov)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
