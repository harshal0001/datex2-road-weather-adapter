"""Step 6 conformance: DATEX II output validates against the official XSD."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adapter.fusion import FusedField, FusionResult
from adapter.segments import FusedSegment, Segment
from adapter.validator import validate
from api.main import app
from outputs.datex_segment import segment_to_datex

SEGMENTS_DB = Path(__file__).resolve().parents[1] / "data" / "segments.db"
needs_db = pytest.mark.skipif(not SEGMENTS_DB.exists(), reason="segments.db not built")

client = TestClient(app)

# Every DATEX value our two condition profiles can emit.
ALL_VALUES = ["dry", "moist", "wet", "glaze", "ice", "snowOnTheRoad", "other"]


def _fake_segment(datex2_value: str) -> FusedSegment:
    seg = Segment(
        segment_id=1, road_name="Test St", road_class="St", length_km=0.1,
        elevation_m=585.0, lat=50.1567, lon=11.9572, geom_wkt="",
    )
    fr = FusionResult(
        segment_id=1,
        fields={"surface_condition": FusedField(value=0, source="sws")},
        sources_used=["sws"], sources_selected=["sws"],
    )
    return FusedSegment(
        segment=seg, fusion=fr, condition_code=0,
        condition_label="x", condition_label_de="x",
        datex2_value=datex2_value, color="#000",
    )


@pytest.mark.parametrize("value", ALL_VALUES)
def test_every_condition_value_produces_valid_datex(value):
    """Conformance matrix: each WeatherRelatedRoadConditionType literal validates."""
    xml = segment_to_datex(_fake_segment(value), ["sws"])
    result = validate(xml)
    assert result.valid, f"'{value}' produced invalid DATEX II: {result.errors[:3]}"


def test_payload_root_and_xsi_type():
    xml = segment_to_datex(_fake_segment("ice"), ["sws"])
    assert "<payload" in xml
    assert 'xsi:type="sit:SituationPublication"' in xml
    assert 'modelBaseVersion="3"' in xml
    assert "weatherRelatedRoadConditionType>ice<" in xml


@needs_db
def test_datex_endpoint_sets_valid_header():
    fused = client.get("/api/segments/fused?sources=sws&limit=1").json()
    seg_id = fused["segments"][0]["segment_id"]
    r = client.get(f"/api/segments/datex?segment_id={seg_id}&sources=sws,dwd")
    assert r.status_code == 200
    assert r.headers.get("X-Validation-Status") == "valid"
