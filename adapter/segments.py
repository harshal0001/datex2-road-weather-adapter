"""Road-segment store: read segments.db, fuse per-segment multi-source data.

Bridges the demo store (built by scripts/build_segment_snapshots.py) and the
fusion engine, producing fused, provenance-tagged records ready for the map and
for DATEX II standardization.
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from adapter.fusion import FusionResult, load_fusion_profile
from adapter.profiles import load_profile

DB = Path(__file__).resolve().parents[1] / "data" / "segments.db"
STATIONS_FILE = Path(__file__).resolve().parents[1] / "data" / "stations.json"
ALL_SOURCES = ["sws", "lorawan", "dwd", "openweather"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS84 points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


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


@lru_cache(maxsize=8)
def _snapshots(moment: str = "latest") -> dict[int, dict[str, dict]]:
    """{segment_id: {source: raw_row_dict}} for a moment ('latest' = current snapshot)."""
    con = _conn()
    out: dict[int, dict[str, dict]] = {}
    if moment == "latest":
        rows = con.execute("SELECT segment_id, source, raw_json FROM segment_snapshot")
    else:
        rows = con.execute(
            "SELECT segment_id, source, raw_json FROM segment_moment WHERE moment=?",
            (moment,),
        )
    for r in rows:
        out.setdefault(r["segment_id"], {})[r["source"]] = json.loads(r["raw_json"])
    con.close()
    return out


def list_moments() -> list[dict]:
    """Named historical moments for the dropdown (+ 'latest'). Excludes the
    hourly time-series steps (ts:*), which the time slider serves separately."""
    moments = [{"id": "latest", "label": "Latest reading"}]
    if not DB.exists():
        return moments
    con = _conn()
    try:
        rows = con.execute(
            "SELECT moment, label FROM moment_meta WHERE moment NOT LIKE 'ts:%' ORDER BY rowid"
        ).fetchall()
        moments += [{"id": r["moment"], "label": r["label"]} for r in rows]
    except sqlite3.Error:
        pass  # moment_meta not built yet
    finally:
        con.close()
    return moments


def list_timeline() -> list[dict]:
    """Ordered hourly time-series steps (ts:*) for the map time slider."""
    if not DB.exists():
        return []
    con = _conn()
    try:
        rows = con.execute(
            "SELECT moment, label FROM moment_meta WHERE moment LIKE 'ts:%' ORDER BY moment"
        ).fetchall()
        return [{"id": r["moment"], "ts": r["moment"][3:], "label": r["label"]} for r in rows]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def source_coverage() -> dict[str, int]:
    """How many segments each source covers (for the dashboard)."""
    snaps = _snapshots()
    cov = {s: 0 for s in ALL_SOURCES}
    for per_source in snaps.values():
        for s in per_source:
            cov[s] = cov.get(s, 0) + 1
    return cov


def fuse_segments(
    selected: list[str] | None = None, moment: str = "latest"
) -> list[FusedSegment]:
    """Fuse every segment using the given source selection, for a given moment.

    selected=None means "all sources"; selected=[] is an explicit empty selection
    (every segment fuses to no data -> Unknown).
    """
    selected = ALL_SOURCES if selected is None else selected
    fp = load_fusion_profile()
    cond_profile = load_profile("segment_conditions")
    segments = load_segments()
    snaps = _snapshots(moment)

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


def fuse_one(
    segment_id: int, selected: list[str] | None = None, moment: str = "latest"
) -> FusedSegment | None:
    """Fuse a single segment (used by the compare view — avoids fusing all 1,021)."""
    selected = ALL_SOURCES if selected is None else selected
    seg = load_segments().get(segment_id)
    if seg is None:
        return None
    fp = load_fusion_profile()
    cond_profile = load_profile("segment_conditions")
    per_source = _snapshots(moment).get(segment_id, {})
    fr = fp.fuse(segment_id, per_source, selected=selected)
    raw_code = fr.value("surface_condition")
    code = int(raw_code) if raw_code is not None else 255
    mapping = cond_profile.condition_codes.get(code) or cond_profile.condition_codes[255]
    return FusedSegment(
        segment=seg, fusion=fr, condition_code=code,
        condition_label=mapping.label, condition_label_de=mapping.label_de or mapping.label,
        datex2_value=mapping.datex2, color=mapping.color or "#95a5a6",
    )


@lru_cache(maxsize=1)
def load_stations() -> list[dict]:
    """The physical ground-sensor stations with real coordinates (stations.json)."""
    if not STATIONS_FILE.exists():
        return []
    data = json.loads(STATIONS_FILE.read_text(encoding="utf-8"))
    return [s for s in data.get("stations", []) if s.get("lat") and s.get("lon")]


SENSORS_FILE = Path(__file__).resolve().parents[1] / "data" / "sensors.json"


@lru_cache(maxsize=1)
def load_sensors() -> dict:
    """Real physical sensor stations per source (extracted from the full exports)."""
    if not SENSORS_FILE.exists():
        return {"counts": {}, "sensors": []}
    return json.loads(SENSORS_FILE.read_text(encoding="utf-8"))


def station_readings(moment: str = "latest") -> list[dict]:
    """Ground stations + a representative reading for each.

    Only LoRaWAN stations carry true coordinates in the data. Each station's
    reading is taken from the road segment nearest to the station that actually
    holds a LoRaWAN snapshot (i.e. the segment its readings were assigned to),
    mapped to canonical fields/units. This is what the dashboard draws as the
    "nearest ground sensor" when a segment is selected.
    """
    stations = load_stations()
    if not stations:
        return []
    fp = load_fusion_profile()
    segments = load_segments()
    snaps = _snapshots(moment)
    lorawan_segs = [
        (sid, segments[sid])
        for sid in snaps
        if "lorawan" in snaps.get(sid, {}) and sid in segments
    ]

    out: list[dict] = []
    for st in stations:
        best_sid, best_d = None, None
        for sid, seg in lorawan_segs:
            d = haversine_km(st["lat"], st["lon"], seg.lat, seg.lon)
            if best_d is None or d < best_d:
                best_sid, best_d = sid, d
        reading = (
            fp.canonical_row("lorawan", snaps[best_sid]["lorawan"])
            if best_sid is not None
            else {}
        )
        out.append({
            "id": st.get("id"),
            "name": st.get("name"),
            "lat": st["lat"],
            "lon": st["lon"],
            "source": st.get("source", "lorawan"),
            "profile_tag": st.get("profile_tag"),
            "nearest_segment_id": best_sid,
            "reading": reading,
        })
    return out
