"""Standardize a fused road segment into DATEX II v3 (Road Weather profile).

Produces a SituationPublication carrying WeatherRelatedRoadConditions plus the
fused measured values, with per-field source provenance recorded as comments.

NOTE (scope): this emits a well-formed DATEX II payload using the VERIFIED element
names and the WeatherRelatedRoadConditionTypeEnum literal for the condition. Full
XSD validation against the generated bindings is the keystone next step (Step 6);
the structure here is built to match that target so validation is a small delta.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from adapter.segments import FusedSegment

NS = "http://datex2.eu/schema/3/situation"
NS_COMMON = "http://datex2.eu/schema/3/common"


def _fmt(v, nd=1):
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return escape(str(v))


def segment_to_datex(fs: FusedSegment, selected: list[str]) -> str:
    seg = fs.segment
    f = fs.fusion.fields

    def measured(field, elem, unit_comment=""):
        fld = f.get(field)
        if not fld or fld.value is None:
            return ""
        prov = f' <!-- source: {fld.source}{unit_comment} -->'
        return f"        <{elem}>{_fmt(fld.value)}</{elem}>{prov}\n"

    measurements = "".join([
        measured("road_surface_temp_c", "roadSurfaceTemperature"),
        measured("air_temp_c", "airTemperature"),
        measured("humidity_pct", "relativeHumidity"),
        measured("dew_point_c", "dewPointTemperature"),
        measured("precipitation_mm", "precipitationIntensity", " (unit varies by source)"),
        measured("wind_speed_ms", "windSpeed"),
        measured("visibility_m", "visibility"),
        measured("pressure_hpa", "airPressure"),
    ])

    cond_source = f["surface_condition"].source or "none"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<d2:payload xmlns:d2="{NS}" xmlns:com="{NS_COMMON}"
            xsi:type="SituationPublication" lang="de"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <!-- Fused from selected sources: {', '.join(selected)} -->
  <!-- Per-field provenance shown as inline comments -->
  <situation id="HOF-SEG-{seg.segment_id}">
    <headerInformation>
      <confidentiality>noRestriction</confidentiality>
      <informationStatus>real</informationStatus>
    </headerInformation>
    <situationRecord xsi:type="WeatherRelatedRoadConditions" id="SEG-{seg.segment_id}-RWC">
      <groupOfLocations xsi:type="Point">
        <pointByCoordinates>
          <pointCoordinates>
            <latitude>{seg.lat:.6f}</latitude>
            <longitude>{seg.lon:.6f}</longitude>
          </pointCoordinates>
        </pointByCoordinates>
      </groupOfLocations>
      <roadSurfaceConditionMeasurements>
{measurements}      </roadSurfaceConditionMeasurements>
      <weatherRelatedRoadConditionType>{fs.datex2_value}</weatherRelatedRoadConditionType>
      <!-- condition ({fs.condition_label}) source: {cond_source} -->
    </situationRecord>
  </situation>
</d2:payload>
"""


def city_summary_datex(fused: list[FusedSegment], selected: list[str]) -> str:
    """A compact city-coverage summary (matches the reference dashboard's codebox)."""
    n = len(fused)
    by_cond: dict[str, int] = {}
    for fs in fused:
        by_cond[fs.datex2_value] = by_cond.get(fs.datex2_value, 0) + 1
    breakdown = ", ".join(f"{k}:{v}" for k, v in sorted(by_cond.items()))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<d2:payload xmlns:d2="{NS}" xsi:type="SituationPublication"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <groupOfLocations>HOF_CITY_COVERAGE</groupOfLocations>
  <coveredSegments>{n}</coveredSegments>
  <selectedSources>{', '.join(selected)}</selectedSources>
  <conditionBreakdown>{escape(breakdown)}</conditionBreakdown>
</d2:payload>
"""
