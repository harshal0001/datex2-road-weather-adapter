"""API routes for the multi-source fusion + road-segment map dashboard."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from adapter.fusion import load_fusion_profile
from adapter.segments import ALL_SOURCES, fuse_segments, source_coverage
from adapter.segment_map import build_map
from outputs.datex_segment import city_summary_datex, segment_to_datex

router = APIRouter(prefix="/api/segments", tags=["segments"])


def _parse_sources(sources: str | None) -> list[str]:
    if not sources:
        return list(ALL_SOURCES)
    picked = [s.strip().lower() for s in sources.split(",") if s.strip()]
    bad = [s for s in picked if s not in ALL_SOURCES]
    if bad:
        raise HTTPException(400, f"unknown source(s): {bad}. valid: {ALL_SOURCES}")
    return picked or list(ALL_SOURCES)


@router.get("/coverage")
def coverage(sources: str | None = Query(None)):
    """Source coverage + fused condition distribution for the selection."""
    selected = _parse_sources(sources)
    fused = fuse_segments(selected)
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


@router.get("/priority")
def priority():
    """The per-field fusion priority config (the research artefact)."""
    fp = load_fusion_profile()
    return {
        "source_priority": fp.source_priority,
        "field_priority": fp.field_priority,
    }


@router.get("/fused")
def fused(sources: str | None = Query(None), limit: int = 200):
    """Fused per-segment records (JSON) with provenance — for the data table."""
    selected = _parse_sources(sources)
    out = []
    for fs in fuse_segments(selected)[:limit]:
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


@router.get("/geojson")
def geojson(sources: str | None = Query(None)):
    """Fused segments as a GeoJSON FeatureCollection (for client-side Leaflet).

    Each feature carries the fused condition, colour, values and per-field
    provenance in its properties, so the client can render + recolour instantly.
    """
    from shapely import wkt as shapely_wkt
    from shapely.geometry import mapping

    selected = _parse_sources(sources)
    features = []
    for fs in fuse_segments(selected):
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
                "condition": fs.condition_label,
                "condition_de": fs.condition_label_de,
                "datex2": fs.datex2_value,
                "color": fs.color,
                "values": {k: v.value for k, v in fs.fusion.fields.items() if v.value is not None},
                "provenance": fs.fusion.provenance(),
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
def datex(segment_id: int, sources: str | None = Query(None)):
    """DATEX II XML for one fused segment."""
    selected = _parse_sources(sources)
    match = [fs for fs in fuse_segments(selected) if fs.segment.segment_id == segment_id]
    if not match:
        raise HTTPException(404, f"segment {segment_id} not found")
    xml = segment_to_datex(match[0], selected)
    return Response(content=xml, media_type="application/xml")


@router.get("/datex/city")
def datex_city(sources: str | None = Query(None)):
    """DATEX II city-coverage summary XML."""
    selected = _parse_sources(sources)
    xml = city_summary_datex(fuse_segments(selected), selected)
    return Response(content=xml, media_type="application/xml")
