"""Render fused road segments onto a folium map (Leaflet HTML).

Mirrors the visualization style of predict_forecast.py: one coloured PolyLine per
road segment, coloured by the fused road-surface condition, with a tooltip that
shows the fused values AND which source supplied each (the provenance).
"""
from __future__ import annotations

import folium
from shapely import wkt as shapely_wkt

from adapter.segments import FusedSegment

HOF_CENTER = [50.31, 11.91]

# Legend order (matches segment_conditions.yaml)
LEGEND = [
    ("Trocken / Dry", "#2ecc71"),
    ("Feucht / Damp", "#3498db"),
    ("Nass / Wet", "#2980b9"),
    ("Eisglätte / Ice", "#e74c3c"),
    ("Schneeglätte / Snow", "#9b59b6"),
    ("Unbekannt / Unknown", "#95a5a6"),
]

_FIELDS_IN_TOOLTIP = [
    ("road_surface_temp_c", "Surface temp", "°C"),
    ("air_temp_c", "Air temp", "°C"),
    ("humidity_pct", "Humidity", "%"),
    ("precipitation_mm_h", "Precip", "mm/h"),
    ("visibility_m", "Visibility", "m"),
    ("pressure_hpa", "Pressure", "hPa"),
]


def _tooltip(fs: FusedSegment) -> str:
    seg = fs.segment
    rows = [
        f"<b>Segment {seg.segment_id}</b> — {seg.road_name or '?'}",
        f"Elevation: {seg.elevation_m:.0f} m" if seg.elevation_m is not None else "",
        f"<b>Condition: {fs.condition_label_de} ({fs.condition_label})</b> "
        f"→ DATEX II <code>{fs.datex2_value}</code>",
        f"Surface source: <b>{fs.fusion.fields['surface_condition'].source or '—'}</b>",
        "<hr style='margin:4px 0'>",
    ]
    for field, label, unit in _FIELDS_IN_TOOLTIP:
        fld = fs.fusion.fields.get(field)
        if fld and fld.value is not None:
            try:
                val = f"{float(fld.value):.1f}{unit}"
            except (TypeError, ValueError):
                val = f"{fld.value}{unit}"
            rows.append(f"{label}: {val} <i>[{fld.source}]</i>")
    rows.append(f"<hr style='margin:4px 0'>Sources used: {', '.join(fs.fusion.sources_used) or '—'}")
    return "<br>".join(r for r in rows if r)


def _legend_html() -> str:
    items = "".join(
        f'<div style="margin:3px 0"><span style="display:inline-block;width:12px;'
        f'height:12px;background:{c};border-radius:2px;margin-right:8px"></span>{label}</div>'
        for label, c in LEGEND
    )
    return f"""
    <div style="position:fixed;bottom:24px;left:24px;z-index:1000;
        background:rgba(15,23,42,0.85);color:#fff;padding:12px 16px;border-radius:10px;
        font-family:Inter,sans-serif;font-size:12px;line-height:1.4">
        <b style="font-size:13px">Straßenzustand / Road condition</b>
        <div style="margin-top:6px">{items}</div>
    </div>"""


def build_map(fused: list[FusedSegment], selected: list[str]) -> folium.Map:
    m = folium.Map(location=HOF_CENTER, zoom_start=11, tiles="CartoDB dark_matter")

    drawn = 0
    for fs in fused:
        if not fs.segment.geom_wkt:
            continue
        geom = shapely_wkt.loads(fs.segment.geom_wkt)
        lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
        for line in lines:
            coords = [(lat, lon) for lon, lat in line.coords]  # folium wants lat,lon
            if len(coords) < 2:
                continue
            folium.PolyLine(
                locations=coords,
                color=fs.color,
                weight=5,
                opacity=0.85,
                tooltip=folium.Tooltip(_tooltip(fs), sticky=True),
            ).add_to(m)
            drawn += 1

    title = (
        f'<div style="position:fixed;top:14px;left:50%;transform:translateX(-50%);'
        f'z-index:1000;background:rgba(15,23,42,0.85);color:#fff;padding:8px 16px;'
        f'border-radius:20px;font-family:Inter,sans-serif;font-size:13px">'
        f'Hof road network · {len(fused)} segments · sources: '
        f'<b>{", ".join(selected) or "none"}</b></div>'
    )
    m.get_root().html.add_child(folium.Element(title))
    m.get_root().html.add_child(folium.Element(_legend_html()))
    return m


def map_html(selected: list[str] | None = None) -> str:
    """Convenience: fuse + render, return the full HTML document as a string."""
    from adapter.segments import ALL_SOURCES, fuse_segments

    selected = selected or ALL_SOURCES
    fused = fuse_segments(selected)
    return build_map(fused, selected).get_root().render()
