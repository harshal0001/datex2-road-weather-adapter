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


def test_unit_harmonization_to_canonical_units():
    """Step 3 — raw units (mm/s, mm/3h, oktas) are converted to canonical units."""
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    # SWS precipitation intensity 0.001 mm/s -> 3.6 mm/h
    sws = fp.canonical_row("sws", {"precipitation_intensity_mm_s": 0.001})
    assert sws["precipitation_mm_h"] == pytest.approx(3.6)
    # DWD cloud cover 4 oktas -> 50 %
    dwd = fp.canonical_row("dwd", {"cloud_cover_oktas": 4})
    assert dwd["cloud_cover_pct"] == pytest.approx(50.0)
    # DWD precipitation is already mm/h -> identity passthrough
    assert fp.canonical_row("dwd", {"precipitation_mm": 2.0})["precipitation_mm_h"] == 2.0
    # OpenWeather 3 mm over 3h -> 1 mm/h
    owm = fp.canonical_row("openweather", {"rain": 3.0})
    assert owm["precipitation_mm_h"] == pytest.approx(1.0)


def test_unit_harmonization_clamps_and_skips_non_numeric():
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    # oktas 9 (sky obscured) clamps to 100 %, never above
    assert fp.canonical_row("dwd", {"cloud_cover_oktas": 9})["cloud_cover_pct"] == 100.0
    # condition codes (non-converted) pass through unchanged
    assert fp.canonical_row("sws", {"road_condition_code": 3})["surface_condition"] == 3


def test_fusion_compares_like_units_after_harmonization():
    """After harmonization, the same rainfall from two sources is comparable."""
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    raw = {
        "dwd": {"precipitation_mm": 3.6},            # mm/h
        "openweather": {"rain": 10.8},               # mm/3h -> 3.6 mm/h
    }
    res = fp.fuse(1, raw, selected=["dwd", "openweather"])
    # DWD wins by priority; both now express the SAME physical rate
    assert res.value("precipitation_mm_h") == pytest.approx(3.6)
    owm_only = fp.fuse(1, raw, selected=["openweather"])
    assert owm_only.value("precipitation_mm_h") == pytest.approx(3.6)


def test_segment_conditions_profile_enum_valid():
    """5-class scheme values must be real DATEX II literals."""
    from adapter.profiles import load_profile

    p = load_profile("segment_conditions")
    assert p.datex2_for(0) == "dry"
    assert p.datex2_for(3) == "ice"
    assert p.datex2_for(4) == "snowOnTheRoad"


def test_haversine_distance_sane():
    """Haversine sanity: ~1 deg latitude ≈ 111 km; identical points = 0."""
    from adapter.segments import haversine_km

    assert haversine_km(50.0, 11.0, 50.0, 11.0) == pytest.approx(0.0)
    assert haversine_km(50.0, 11.0, 51.0, 11.0) == pytest.approx(111.2, abs=1.0)


@needs_db
def test_stations_endpoint_returns_located_sensors():
    """Ground-sensor layer: real LoRaWAN stations with coords + a reading."""
    r = client.get("/api/segments/stations")
    assert r.status_code == 200
    sts = r.json()["stations"]
    assert len(sts) >= 1
    s = sts[0]
    assert -90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180
    assert s["name"]
    # reading is canonical-unit keyed (or empty if no lorawan segment nearby)
    assert isinstance(s["reading"], dict)


@needs_db
def test_geojson_carries_segment_centroid():
    """Client needs the segment centroid to find the nearest ground sensor."""
    gj = client.get("/api/segments/geojson?sources=sws").json()
    props = gj["features"][0]["properties"]
    assert "lat" in props and "lon" in props


@needs_db
def test_coverage_endpoint():
    r = client.get("/api/segments/coverage?sources=sws,dwd")
    assert r.status_code == 200
    d = r.json()
    assert d["total_segments"] > 0
    assert d["coverage_per_source"]["sws"] > 0


@needs_db
def test_empty_selection_means_no_sources():
    """sources= (present but empty) must mean NO sources, not a silent 'all'."""
    r = client.get("/api/segments/coverage?sources=")
    d = r.json()
    assert d["selected_sources"] == []
    # every segment fuses to no data -> all Unknown
    assert d["segments_without_condition"] == d["total_segments"]
    assert set(d["condition_distribution"]) <= {"Unknown"}


@needs_db
def test_omitted_sources_defaults_to_all():
    """Omitting the param entirely still defaults to all sources (back-compat)."""
    d = client.get("/api/segments/coverage").json()
    assert set(d["selected_sources"]) == {"sws", "lorawan", "dwd", "openweather"}


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


def test_registry_discovers_all_sources():
    from sources.registry import list_sources

    names = set(list_sources())
    assert {"sws", "dwd", "lorawan", "openweather", "wdms"} <= names


def test_sources_endpoint():
    r = client.get("/sources")
    assert r.status_code == 200
    by_name = {s["name"]: s for s in r.json()["sources"]}
    assert "sws" in by_name
    # wdms is the optional live system — reported but expected down in the demo
    assert by_name["wdms"]["status"] == "down"


def test_moments_endpoint_lists_latest():
    r = client.get("/api/segments/moments")
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["moments"]]
    assert "latest" in ids


@needs_db
def test_ice_moment_shows_ice_segments():
    """The 2025-11-24 ice event moment must colour many segments Ice (real data)."""
    r = client.get("/api/segments/coverage?sources=sws&moment=ice-event-night")
    if "ice-event-night" not in [m["id"] for m in client.get("/api/segments/moments").json()["moments"]]:
        import pytest
        pytest.skip("moments not built (run scripts/build_moments.py)")
    dist = r.json()["condition_distribution"]
    assert dist.get("Ice", 0) > 100


@needs_db
def test_source_yields_canonical_observation():
    from adapter.models import CanonicalObservation
    from sources.registry import get_source

    obs = next(get_source("sws").iter_observations(), None)
    assert isinstance(obs, CanonicalObservation)
    assert obs.source == "sws"
    assert -90 <= obs.coordinates.lat <= 90
