"""API routes for the multi-source fusion + road-segment map dashboard."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from adapter.fusion import load_fusion_profile
from adapter.profiles import load_profile
from adapter.scenarios import get_scenario, list_scenarios
from adapter.segments import (
    ALL_SOURCES,
    FusedSegment,
    Segment,
    fuse_one,
    fuse_segments,
    list_moments,
    load_segments,
    source_coverage,
)
from adapter.segment_map import build_map
from outputs.datex_segment import (
    city_summary_datex,
    segment_to_datex_validated,
)

router = APIRouter(prefix="/api/segments", tags=["segments"])
transform_router = APIRouter(prefix="/api", tags=["transform"])


def _parse_sources(sources: str | None) -> list[str]:
    # None  = parameter omitted        -> default to all sources
    # ""    = parameter present, empty  -> an explicit empty selection (no sources)
    if sources is None:
        return list(ALL_SOURCES)
    picked = [s.strip().lower() for s in sources.split(",") if s.strip()]
    bad = [s for s in picked if s not in ALL_SOURCES]
    if bad:
        raise HTTPException(400, f"unknown source(s): {bad}. valid: {ALL_SOURCES}")
    return picked  # may be [] when the user deselects everything


@router.get("/moments")
def moments():
    """Available map moments (historical timestamps + 'latest')."""
    return {"moments": list_moments()}


@router.get("/timeline")
def timeline():
    """Ordered hourly time-series steps for the map time slider."""
    from adapter.segments import list_timeline

    return {"timeline": list_timeline()}


@router.get("/coverage")
def coverage(sources: str | None = Query(None), moment: str = Query("latest")):
    """Source coverage + fused condition distribution for the selection."""
    selected = _parse_sources(sources)
    fused = fuse_segments(selected, moment)
    by_cond: dict[str, int] = {}
    unknown = 0
    for fs in fused:
        by_cond[fs.condition_label] = by_cond.get(fs.condition_label, 0) + 1
        if fs.condition_code == 255:
            unknown += 1
    return {
        "selected_sources": selected,
        "total_segments": len(fused),
        "coverage_per_source": source_coverage(),
        "condition_distribution": by_cond,
        "segments_without_condition": unknown,
    }


@router.get("/stations")
def stations(moment: str = Query("latest")):
    """Physical ground-sensor stations (real coordinates) + representative reading.

    Used by the dashboard to draw the ground-sensor layer and, when a segment is
    selected, the nearest station (haversine) with a connector line.
    """
    from adapter.segments import station_readings

    return {"stations": station_readings(moment)}


@router.get("/priority")
def priority():
    """The per-field fusion priority config (the research artefact)."""
    fp = load_fusion_profile()
    return {
        "source_priority": fp.source_priority,
        "field_priority": fp.field_priority,
    }


@router.get("/fused")
def fused(sources: str | None = Query(None), limit: int = 200, moment: str = Query("latest")):
    """Fused per-segment records (JSON) with provenance — for the data table."""
    selected = _parse_sources(sources)
    out = []
    for fs in fuse_segments(selected, moment)[:limit]:
        out.append({
            "segment_id": fs.segment.segment_id,
            "road_name": fs.segment.road_name,
            "elevation_m": fs.segment.elevation_m,
            "condition": fs.condition_label,
            "condition_de": fs.condition_label_de,
            "datex2": fs.datex2_value,
            "values": {k: v.value for k, v in fs.fusion.fields.items() if v.value is not None},
            "provenance": fs.fusion.provenance(),
            "sources_used": fs.fusion.sources_used,
        })
    return {"selected_sources": selected, "count": len(out), "segments": out}


@router.get("/fused/{segment_id}")
def fused_one(segment_id: int, sources: str | None = Query(None), moment: str = Query("latest")):
    """One fused segment (values + provenance + agreement) for the compare view."""
    selected = _parse_sources(sources)
    fs = fuse_one(segment_id, selected, moment)
    if fs is None:
        raise HTTPException(404, f"segment {segment_id} not found")
    _, result = segment_to_datex_validated(fs, selected) if selected else (None, None)
    return {
        "segment_id": fs.segment.segment_id,
        "road_name": fs.segment.road_name,
        "selected_sources": selected,
        "condition": fs.condition_label,
        "condition_de": fs.condition_label_de,
        "datex2": fs.datex2_value,
        "color": fs.color,
        "values": {k: v.value for k, v in fs.fusion.fields.items() if v.value is not None},
        "provenance": fs.fusion.provenance(),
        "agreement": {k: v.agreement for k, v in fs.fusion.fields.items() if v.value is not None},
        "confidence": fs.fusion.confidence(),
        "sources_used": fs.fusion.sources_used,
        "validation": {"status": (result.status if result else "n/a")},
    }


FORECAST_FEATURE_SOURCES = ["dwd", "lorawan", "openweather"]  # non-SWS (no road sensor)


@router.get("/forecast/{segment_id}")
def forecast_segment(segment_id: int, moment: str = Query("latest")):
    """Predict road condition from atmospheric sources only (no SWS road sensor),
    and compare to the observed SWS condition for the same segment/moment."""
    from adapter import forecast as fc

    if not fc.available():
        raise HTTPException(503, "forecast model not built (run scripts/train_forecast.py)")

    feat_fs = fuse_one(segment_id, FORECAST_FEATURE_SOURCES, moment)
    if feat_fs is None:
        raise HTTPException(404, f"segment {segment_id} not found")
    features = {k: v.value for k, v in feat_fs.fusion.fields.items() if v.value is not None}
    features["elevation_m"] = feat_fs.segment.elevation_m
    pred = fc.predict(features)

    obs_fs = fuse_one(segment_id, ["sws"], moment)
    observed = {
        "label": obs_fs.condition_label if obs_fs else "Unknown",
        "datex2": obs_fs.datex2_value if obs_fs else "other",
        "has_truth": bool(obs_fs and obs_fs.condition_code != 255),
    }

    # publish the predicted condition as validated DATEX II (probabilityOfOccurrence)
    datex = {"status": "n/a"}
    if pred:
        pred_fs = FusedSegment(
            segment=feat_fs.segment, fusion=feat_fs.fusion,
            condition_code=pred["code"], condition_label=pred["label"],
            condition_label_de=pred["label"], datex2_value=pred["datex2"], color="",
        )
        from outputs.datex_segment import segment_forecast_to_datex_validated

        xml, result = segment_forecast_to_datex_validated(pred_fs, pred["probability"])
        datex = {"status": result.status,
                 "probability_of_occurrence": "probable" if pred["probability"] >= 0.66 else "riskOf"}

    return {
        "segment_id": segment_id,
        "moment": moment,
        "feature_sources": [s for s in FORECAST_FEATURE_SOURCES if s in feat_fs.fusion.sources_used],
        "predicted": pred,
        "observed": observed,
        "match": bool(pred and observed["has_truth"] and pred["label"] == observed["label"]),
        "datex": datex,
    }


@router.get("/geojson")
def geojson(sources: str | None = Query(None), moment: str = Query("latest")):
    """Fused segments as a GeoJSON FeatureCollection (for client-side Leaflet).

    Each feature carries the fused condition, colour, values and per-field
    provenance in its properties, so the client can render + recolour instantly.
    """
    from shapely import wkt as shapely_wkt
    from shapely.geometry import mapping

    selected = _parse_sources(sources)
    features = []
    for fs in fuse_segments(selected, moment):
        if not fs.segment.geom_wkt:
            continue
        geom = mapping(shapely_wkt.loads(fs.segment.geom_wkt))
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "segment_id": fs.segment.segment_id,
                "road_name": fs.segment.road_name,
                "elevation_m": fs.segment.elevation_m,
                "lat": fs.segment.lat,
                "lon": fs.segment.lon,
                "condition": fs.condition_label,
                "condition_de": fs.condition_label_de,
                "datex2": fs.datex2_value,
                "color": fs.color,
                "values": {k: v.value for k, v in fs.fusion.fields.items() if v.value is not None},
                "provenance": fs.fusion.provenance(),
                "candidates": {k: v.candidates for k, v in fs.fusion.fields.items() if len(v.candidates) > 1},
                "agreement": {k: v.agreement for k, v in fs.fusion.fields.items() if v.value is not None},
                "confidence": fs.fusion.confidence(),
                "sources_used": fs.fusion.sources_used,
            },
        })
    return {"type": "FeatureCollection", "selected_sources": selected, "features": features}


@router.get("/map", response_class=HTMLResponse)
def segment_map(sources: str | None = Query(None)):
    """Full folium map HTML (legacy/fallback — the Leaflet dashboard uses /geojson)."""
    selected = _parse_sources(sources)
    fused = fuse_segments(selected)
    return HTMLResponse(build_map(fused, selected).get_root().render())


@router.get("/datex")
def datex(segment_id: int, sources: str | None = Query(None), moment: str = Query("latest")):
    """XSD-validated DATEX II XML for one fused segment.

    The response carries `X-Validation-Status: valid|invalid` (validated against the
    official DATEX II v3 schema) and `X-Validation-Errors` when invalid.
    """
    selected = _parse_sources(sources)
    match = [fs for fs in fuse_segments(selected, moment) if fs.segment.segment_id == segment_id]
    if not match:
        raise HTTPException(404, f"segment {segment_id} not found")
    xml, result = segment_to_datex_validated(match[0], selected)
    headers = {"X-Validation-Status": result.status}
    if not result.valid:
        headers["X-Validation-Errors"] = "; ".join(result.errors[:3])[:500]
    return Response(content=xml, media_type="application/xml", headers=headers)


@router.get("")
def segments_catalogue(limit: int = 500):
    """Road-segment catalogue (geometry centroid + metadata) — the ≈/stations list."""
    segs = list(load_segments().values())[:limit]
    return {
        "count": len(segs),
        "segments": [
            {
                "segment_id": s.segment_id, "road_name": s.road_name,
                "road_class": s.road_class, "length_km": s.length_km,
                "elevation_m": s.elevation_m, "lat": s.lat, "lon": s.lon,
            }
            for s in segs
        ],
    }


class TransformRequest(BaseModel):
    """Generic raw → DATEX II request: arbitrary per-source rows for one location."""
    lat: float
    lon: float
    sources: dict[str, dict] = Field(
        ..., description="per-source raw rows, e.g. {'sws': {'road_condition_code': 3.0, ...}}"
    )
    segment_id: int = 0
    selected: list[str] | None = None
    road_name: str | None = None
    elevation_m: float | None = None


@transform_router.get("/scenarios")
def scenarios():
    """Predefined illustrative demo scenarios (icy night, snow, freezing, dry)."""
    return {"scenarios": list_scenarios()}


@transform_router.get("/scenarios/{scenario_id}")
def scenario(scenario_id: str):
    """Full scenario incl. the raw per-source rows (POST these to /api/transform)."""
    s = get_scenario(scenario_id)
    if not s:
        raise HTTPException(404, f"unknown scenario: {scenario_id}")
    return s


@transform_router.post("/transform")
def transform(req: TransformRequest):
    """Transform arbitrary raw multi-source data into validated DATEX II.

    This is the generic adapter operation: drop in raw rows from any selected
    sources, they are fused per-field (with provenance), mapped to the canonical
    condition, and emitted as XSD-validated DATEX II. Returns XML with an
    `X-Validation-Status` header.
    """
    selected = req.selected or list(req.sources.keys()) or list(ALL_SOURCES)
    fp = load_fusion_profile()
    cond = load_profile("segment_conditions")

    fr = fp.fuse(req.segment_id, req.sources, selected=selected)
    raw_code = fr.value("surface_condition")
    code = int(raw_code) if raw_code is not None else 255
    mapping = cond.condition_codes.get(code) or cond.condition_codes[255]

    fs = FusedSegment(
        segment=Segment(
            segment_id=req.segment_id, road_name=req.road_name, road_class=None,
            length_km=None, elevation_m=req.elevation_m, lat=req.lat, lon=req.lon,
            geom_wkt="",
        ),
        fusion=fr, condition_code=code,
        condition_label=mapping.label, condition_label_de=mapping.label_de or mapping.label,
        datex2_value=mapping.datex2, color=mapping.color or "#95a5a6",
    )
    xml, result = segment_to_datex_validated(fs, selected)
    headers = {
        "X-Validation-Status": result.status,
        "X-Source-Used": ",".join(fr.sources_used) or "none",
        "X-Profile": "segment_conditions",
    }
    if not result.valid:
        headers["X-Validation-Errors"] = "; ".join(result.errors[:3])[:500]
    return Response(content=xml, media_type="application/xml", headers=headers)


@router.get("/datex/city")
def datex_city(sources: str | None = Query(None)):
    """XSD-validated DATEX II covering all fused segments (city-wide publication)."""
    selected = _parse_sources(sources)
    xml = city_summary_datex(fuse_segments(selected), selected)
    from adapter.validator import validate

    result = validate(xml)
    headers = {"X-Validation-Status": result.status}
    if not result.valid:
        headers["X-Validation-Errors"] = "; ".join(result.errors[:3])[:500]
    return Response(content=xml, media_type="application/xml", headers=headers)
