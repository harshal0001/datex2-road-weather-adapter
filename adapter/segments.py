"""Road-segment store: read segments.db, fuse per-segment multi-source data.

Bridges the demo store (built by scripts/build_segment_snapshots.py) and the
fusion engine, producing fused, provenance-tagged records ready for the map and
for DATEX II standardization.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from adapter.fusion import FusionResult, load_fusion_profile
from adapter.profiles import load_profile

DB = Path(__file__).resolve().parents[1] / "data" / "segments.db"
ALL_SOURCES = ["sws", "lorawan", "dwd", "openweather"]


@dataclass
class Segment:
    segment_id: int
    road_name: str | None
    road_class: str | None
    length_km: float | None
    elevation_m: float | None
    lat: float
    lon: float
    geom_wkt: str


@dataclass
class FusedSegment:
    segment: Segment
    fusion: FusionResult
    condition_code: int          # 0..4, or 255 if unknown/missing
    condition_label: str         # English label
    condition_label_de: str      # German label
    datex2_value: str            # WeatherRelatedRoadConditionTypeEnum literal
    color: str                   # hex for the map


def _conn() -> sqlite3.Connection:
    if not DB.exists():
        raise FileNotFoundError(
            f"{DB} not found — run scripts/build_segment_snapshots.py --rebuild"
        )
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


@lru_cache(maxsize=1)
def load_segments() -> dict[int, Segment]:
    con = _conn()
    out = {}
    for r in con.execute("SELECT * FROM segments"):
        out[r["segment_id"]] = Segment(
            segment_id=r["segment_id"],
            road_name=r["road_name"],
            road_class=r["road_class"],
            length_km=r["length_km"],
            elevation_m=r["elevation_m"],
            lat=r["lat"],
            lon=r["lon"],
            geom_wkt=r["geom_wkt"],
        )
    con.close()
    return out


@lru_cache(maxsize=1)
def _snapshots() -> dict[int, dict[str, dict]]:
    """{segment_id: {source: raw_row_dict}}"""
    con = _conn()
    out: dict[int, dict[str, dict]] = {}
    for r in con.execute("SELECT segment_id, source, raw_json FROM segment_snapshot"):
        out.setdefault(r["segment_id"], {})[r["source"]] = json.loads(r["raw_json"])
    con.close()
    return out


def source_coverage() -> dict[str, int]:
    """How many segments each source covers (for the dashboard)."""
    snaps = _snapshots()
    cov = {s: 0 for s in ALL_SOURCES}
    for per_source in snaps.values():
        for s in per_source:
            cov[s] = cov.get(s, 0) + 1
    return cov


def fuse_segments(selected: list[str] | None = None) -> list[FusedSegment]:
    """Fuse every segment using the given source selection."""
    selected = selected or ALL_SOURCES
    fp = load_fusion_profile()
    cond_profile = load_profile("segment_conditions")
    segments = load_segments()
    snaps = _snapshots()

    results: list[FusedSegment] = []
    for seg_id, seg in segments.items():
        per_source = snaps.get(seg_id, {})
        fr = fp.fuse(seg_id, per_source, selected=selected)

        raw_code = fr.value("surface_condition")
        code = int(raw_code) if raw_code is not None else 255
        mapping = cond_profile.condition_codes.get(code) or cond_profile.condition_codes[255]

        results.append(FusedSegment(
            segment=seg,
            fusion=fr,
            condition_code=code,
            condition_label=mapping.label,
            condition_label_de=mapping.label_de or mapping.label,
            datex2_value=mapping.datex2,
            color=mapping.color or "#95a5a6",
        ))
    return results
