"""Standardize fused road segments into XSD-valid DATEX II v3 (Road Weather profile).

Builds a real `SituationPublication` from the generated xsdata dataclasses, serializes
it as a `<payload xsi:type="sit:SituationPublication">` document, and validates it
against the official DATEX II XSD. Each road segment becomes a `Situation` carrying a
`WeatherRelatedRoadConditions` record (condition + point location), with per-field
source provenance recorded as XML comments.

This replaces the earlier string-template output: the XML here is schema-conformant
(see adapter/validator.py and tests/test_datex.py).
"""
from __future__ import annotations

import importlib

from lxml import etree
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.models.datatype import XmlDateTime

from adapter.segments import FusedSegment
from adapter.validator import ValidationResult, validate

# ── namespaces ────────────────────────────────────────────────────────────────
D2 = "http://datex2.eu/schema/3/d2Payload"
SIT = "http://datex2.eu/schema/3/situation"
COM = "http://datex2.eu/schema/3/common"
LOC = "http://datex2.eu/schema/3/locationReferencing"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS = {"sit": SIT, "com": COM, "loc": LOC, "xsi": XSI}

PUBLICATION_CREATOR_COUNTRY = "de"
PUBLICATION_CREATOR_ID = "HOF-ROAD-WEATHER-ADAPTER"


def _k(mod, cls):
    return getattr(importlib.import_module(f"generated.datex2.{mod}"), cls)


# Generated dataclasses (resolved once at import).
_SituationPublication = _k("situation_publication", "SituationPublication")
_Situation = _k("situation", "Situation")
_HeaderInformation = _k("header_information", "HeaderInformation")
_WRRC = _k("weather_related_road_conditions", "WeatherRelatedRoadConditions")
_Validity = _k("validity", "Validity")
_OverallPeriod = _k("overall_period", "OverallPeriod")
_PointLocation = _k("point_location", "PointLocation")
_PointByCoordinates = _k("point_by_coordinates", "PointByCoordinates")
_PointCoordinates = _k("point_coordinates", "PointCoordinates")
_InternationalIdentifier = _k("international_identifier", "InternationalIdentifier")
_IS2 = _k("information_status_enum_2", "InformationStatusEnum2")
_IS1 = _k("information_status_enum_1", "InformationStatusEnum1")
_VS2 = _k("validity_status_enum_2", "ValidityStatusEnum2")
_VS1 = _k("validity_status_enum_1", "ValidityStatusEnum1")
_PO2 = _k("probability_of_occurrence_enum_2", "ProbabilityOfOccurrenceEnum2")
_PO1 = _k("probability_of_occurrence_enum_1", "ProbabilityOfOccurrenceEnum1")
_WT2 = _k("weather_related_road_condition_type_enum_2", "WeatherRelatedRoadConditionTypeEnum2")
_WT1 = _k("weather_related_road_condition_type_enum_1", "WeatherRelatedRoadConditionTypeEnum1")
_RSCM = _k("road_surface_condition_measurements", "RoadSurfaceConditionMeasurements")
_TemperatureValue = _k("temperature_value", "TemperatureValue")
_MetreDistanceValue = _k("floating_point_metre_distance_value", "FloatingPointMetreDistanceValue")


def _measurements(fs: FusedSegment):
    """Map fused measured values into a RoadSurfaceConditionMeasurements (or None)."""
    surface_temp = fs.fusion.value("road_surface_temp_c")
    water_film_mm = fs.fusion.value("water_film_mm")
    kwargs = {}
    if surface_temp is not None:
        kwargs["road_surface_temperature"] = _TemperatureValue(temperature=float(surface_temp))
    if water_film_mm is not None:
        # DATEX water film is in metres; our source is mm.
        kwargs["water_film_thickness"] = _MetreDistanceValue(distance=float(water_film_mm) / 1000.0)
    return _RSCM(**kwargs) if kwargs else None


def _now() -> XmlDateTime:
    # Deterministic stamp keeps demo output stable; real deployments use event time.
    return XmlDateTime.from_string("2026-01-15T03:00:00Z")


def _record(fs: FusedSegment):
    """One WeatherRelatedRoadConditions record for a fused segment."""
    ts = _now()
    return _WRRC(
        id=f"SEG-{fs.segment.segment_id}-RWC",
        version="1",
        situation_record_creation_time=ts,
        situation_record_version_time=ts,
        probability_of_occurrence=_PO2(value=_PO1.CERTAIN),  # SWS = observed
        validity=_Validity(
            validity_status=_VS2(value=_VS1.ACTIVE),
            validity_time_specification=_OverallPeriod(overall_start_time=ts),
        ),
        location_reference=_PointLocation(
            point_by_coordinates=_PointByCoordinates(
                point_coordinates=_PointCoordinates(
                    latitude=round(fs.segment.lat, 6),
                    longitude=round(fs.segment.lon, 6),
                )
            )
        ),
        weather_related_road_condition_type=[_WT2(value=_WT1(fs.datex2_value))],
        road_surface_condition_measurements=_measurements(fs),
    )


def _situation(fs: FusedSegment):
    return _Situation(
        id=f"HOF-SEG-{fs.segment.segment_id}",
        header_information=_HeaderInformation(
            information_status=_IS2(value=_IS1.REAL)
        ),
        situation_record=[_record(fs)],
    )


def build_publication(fused: list[FusedSegment]):
    """Build a SituationPublication covering the given fused segments."""
    return _SituationPublication(
        publication_time=_now(),
        publication_creator=_InternationalIdentifier(
            country=PUBLICATION_CREATOR_COUNTRY,
            national_identifier=PUBLICATION_CREATOR_ID,
        ),
        lang="de",
        situation=[_situation(fs) for fs in fused],
    )


def _provenance_comment(fused: list[FusedSegment], selected: list[str]) -> str:
    lines = [f" DATEX II SituationPublication — fused from sources: {', '.join(selected)} "]
    for fs in fused[:1]:  # provenance of the (first) segment's key fields
        prov = fs.fusion.provenance()
        keys = ["surface_condition", "road_surface_temp_c", "air_temp_c", "humidity_pct"]
        items = [f"{k}<-{prov.get(k) or '—'}" for k in keys]
        lines.append(f" segment {fs.segment.segment_id} provenance: {', '.join(items)} ")
    return "\n".join(lines)


def to_payload_xml(pub, comment: str | None = None) -> str:
    """Serialize a SituationPublication as a `<payload xsi:type=…>` document.

    xsdata renders the concrete class as its own root; the DATEX II schema declares a
    single global `payload` element of the abstract PayloadPublication type, so we
    re-root under `<d2:payload>` and add the `xsi:type`. Prefixes are pinned via ns_map
    so the nested `xsi:type` QNames (sit:…, loc:…) resolve under the new root.
    """
    raw = XmlSerializer(config=SerializerConfig()).render(pub, ns_map=dict(NS)).encode()
    old = etree.fromstring(raw)
    root = etree.Element(f"{{{D2}}}payload", nsmap={None: D2, **NS})
    for k, v in old.attrib.items():
        root.set(k, v)
    root.set(f"{{{XSI}}}type", "sit:SituationPublication")
    if comment:
        root.append(etree.Comment(comment))
    for child in old:
        root.append(child)
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    ).decode()


def segment_to_datex(fs: FusedSegment, selected: list[str]) -> str:
    """XSD-valid DATEX II XML for one fused segment."""
    pub = build_publication([fs])
    return to_payload_xml(pub, _provenance_comment([fs], selected))


def segment_to_datex_validated(fs: FusedSegment, selected: list[str]) -> tuple[str, ValidationResult]:
    xml = segment_to_datex(fs, selected)
    return xml, validate(xml)


def city_summary_datex(fused: list[FusedSegment], selected: list[str]) -> str:
    """XSD-valid DATEX II covering all fused segments (city-wide publication)."""
    pub = build_publication(fused)
    return to_payload_xml(pub, _provenance_comment(fused, selected))
