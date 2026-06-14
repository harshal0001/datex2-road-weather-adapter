"""Tests for the multi-source fusion + road-segment dashboard."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

SEGMENTS_DB = Path(__file__).resolve().parents[1] / "data" / "segments.db"
needs_db = pytest.mark.skipif(
    not SEGMENTS_DB.exists(),
    reason="segments.db not built (run scripts/build_segment_snapshots.py)",
)

client = TestClient(app)


def test_fusion_priority_loads():
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    # SWS must outrank LoRaWAN for road surface temp; only SWS has condition truth.
    assert fp.priority_for("road_surface_temp_c")[0] == "sws"
    assert fp.priority_for("surface_condition") == ["sws"]


def test_fusion_picks_by_priority():
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    raw = {
        "sws": {"road_surface_temperature_celsius": 1.0, "road_condition_code": 3.0},
        "lorawan": {"surface_temperature": 9.9},
        "dwd": {"air_pressure_sea_level_hpa": 1010.0},
    }
    # all sources → SWS wins surface temp, DWD supplies pressure
    res = fp.fuse(1, raw, selected=["sws", "lorawan", "dwd"])
    assert res.value("road_surface_temp_c") == 1.0
    assert res.fields["road_surface_temp_c"].source == "sws"
    assert res.value("pressure_hpa") == 1010.0
    # drop SWS → surface temp falls back to LoRaWAN, condition disappears
    res2 = fp.fuse(1, raw, selected=["lorawan", "dwd"])
    assert res2.value("road_surface_temp_c") == 9.9
    assert res2.fields["road_surface_temp_c"].source == "lorawan"
    assert res2.value("surface_condition") is None


def test_segment_conditions_profile_enum_valid():
    """5-class scheme values must be real DATEX II literals."""
    from adapter.profiles import load_profile

    p = load_profile("segment_conditions")
    assert p.datex2_for(0) == "dry"
    assert p.datex2_for(3) == "ice"
    assert p.datex2_for(4) == "snowOnTheRoad"


@needs_db
def test_coverage_endpoint():
    r = client.get("/api/segments/coverage?sources=sws,dwd")
    assert r.status_code == 200
    d = r.json()
    assert d["total_segments"] > 0
    assert d["coverage_per_source"]["sws"] > 0


@needs_db
def test_without_sws_loses_condition():
    """Only SWS carries ground-truth condition — without it, all go unknown."""
    r = client.get("/api/segments/coverage?sources=dwd,openweather")
    d = r.json()
    assert d["segments_without_condition"] == d["total_segments"]


@needs_db
def test_datex_uses_verified_enum():
    fused = client.get("/api/segments/fused?sources=sws&limit=1").json()
    seg_id = fused["segments"][0]["segment_id"]
    xml = client.get(f"/api/segments/datex?segment_id={seg_id}&sources=sws,dwd").text
    assert "weatherRelatedRoadConditionType" in xml
    assert "WeatherRelatedRoadConditions" in xml


@needs_db
def test_map_renders_leaflet():
    r = client.get("/api/segments/map?sources=sws")
    assert r.status_code == 200
    assert "leaflet" in r.text.lower()


def test_invalid_source_rejected():
    r = client.get("/api/segments/coverage?sources=bogus")
    assert r.status_code == 400
