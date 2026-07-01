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


def test_owm_air_temp_kelvin_harmonized_to_celsius():
    """OpenWeather reports air temp in Kelvin — it must be converted to °C."""
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    row = fp.canonical_row("openweather", {"temp": 276.15})
    assert row["air_temp_c"] == pytest.approx(3.0, abs=0.01)


def test_fusion_reports_cross_source_agreement():
    """Multi-source fields carry candidates + an agreement/confidence verdict."""
    from adapter.fusion import load_fusion_profile

    fp = load_fusion_profile()
    raw = {
        "sws": {"air_temperature_celsius": 2.0},
        "dwd": {"air_temperature_celsius": 2.3},
        "openweather": {"temp": 275.3},   # 2.15 °C after K→°C
    }
    res = fp.fuse(1, raw, selected=["sws", "dwd", "openweather"])
    at = res.fields["air_temp_c"]
    assert at.source == "sws" and at.value == 2.0
    assert set(at.candidates) == {"sws", "dwd", "openweather"}
    assert at.agreement == "agree"          # spread 0.3 within 1.0 °C tolerance
    # an outlier flips it to disagreement
    raw["openweather"]["temp"] = 290.0      # ~16.8 °C
    res2 = fp.fuse(1, raw, selected=["sws", "dwd", "openweather"])
    assert res2.fields["air_temp_c"].agreement == "spread"
    assert res2.confidence()["level"] in {"low", "medium", "high"}


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


def test_sensors_endpoint_all_sources():
    """Real sensor network: per-source stations with coordinates from full exports."""
    d = client.get("/api/segments/sensors").json()
    if not d.get("sensors"):
        import pytest
        pytest.skip("sensors.json not built (run scripts/build_sensors.py)")
    assert d["counts"].get("sws", 0) >= 1   # the in-road ground-truth stations
    s = d["sensors"][0]
    assert s["source"] in {"sws", "lorawan", "dwd", "openweather"}
    assert -90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180


def test_sensors_endpoint_is_moment_aligned():
    """Markers for a named moment carry that moment's readings (same instant as the
    fused segment layer), not each station's absolute latest."""
    d = client.get("/api/segments/sensors?moment=ice-event-night").json()
    sensors = d.get("sensors") or []
    if not sensors:
        import pytest
        pytest.skip("sensors.json not built moment-aware (run scripts/build_sensors.py)")
    dated = [s["ts"] for s in sensors if s.get("ts")]
    assert dated, "moment sensors should carry timestamps"
    # the ice event is 24 Nov 2025 — every marker's reading sits around it (day-of or
    # the day before), never each station's absolute latest stuck in 2024/2026
    assert all(t[:7] == "2025-11" for t in dated)
    assert all(t[:10] in {"2025-11-23", "2025-11-24"} for t in dated)


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
def test_fused_one_endpoint_for_compare():
    """Single-segment fuse (compare view): condition depends on the selection."""
    fused = client.get("/api/segments/fused?sources=sws&limit=1").json()
    seg = fused["segments"][0]["segment_id"]
    a = client.get(f"/api/segments/fused/{seg}?sources=sws,dwd").json()
    b = client.get(f"/api/segments/fused/{seg}?sources=dwd,openweather").json()
    assert a["validation"]["status"] == "valid"
    assert "confidence" in a and "agreement" in a
    # dropping SWS removes the ground-truth condition
    assert b["condition"] == "Unknown"


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
    # time-series steps must NOT clutter the named-moment dropdown
    assert not any(i.startswith("ts:") for i in ids)


@needs_db
def test_timeline_endpoint_is_ordered():
    """Time slider: ordered ts:* steps, each usable as a ?moment= value."""
    tl = client.get("/api/segments/timeline").json()["timeline"]
    if not tl:
        import pytest
        pytest.skip("time series not built (run scripts/build_timeseries.py)")
    ids = [s["id"] for s in tl]
    assert all(i.startswith("ts:") for i in ids)
    assert ids == sorted(ids)  # chronological
    # a step drives the same fusion path as any moment
    r = client.get(f"/api/segments/coverage?sources=sws&moment={ids[0]}")
    assert r.status_code == 200 and r.json()["total_segments"] > 0


@needs_db
def test_ice_moment_shows_ice_segments():
    """The 2025-11-24 ice event moment must colour many segments Ice (real data)."""
    r = client.get("/api/segments/coverage?sources=sws&moment=ice-event-night")
    if "ice-event-night" not in [m["id"] for m in client.get("/api/segments/moments").json()["moments"]]:
        import pytest
        pytest.skip("moments not built (run scripts/build_moments.py)")
    dist = r.json()["condition_distribution"]
    assert dist.get("Ice", 0) > 100


def test_forecast_module_predicts_or_absent():
    """Forecast inference: absent model returns None; present model predicts a class."""
    from adapter import forecast as fc

    if not fc.available():
        assert fc.predict({"air_temp_c": -3}) is None
        import pytest
        pytest.skip("forecast model not built (run scripts/train_forecast.py)")
    # a cold, sub-zero surface should lean towards ice/snow, with a valid prob dist
    out = fc.predict({"air_temp_c": -4, "road_surface_temp_c": -3, "humidity_pct": 96,
                      "dew_point_c": -4, "elevation_m": 600})
    assert out["label"] in {"Dry", "Damp", "Wet", "Ice", "Snow"}
    assert 0.0 <= out["probability"] <= 1.0
    assert abs(sum(out["probabilities"].values()) - 1.0) < 0.01


@needs_db
def test_forecast_endpoint_predicted_vs_observed():
    from adapter import forecast as fc

    if not fc.available():
        import pytest
        pytest.skip("forecast model not built")
    fused = client.get("/api/segments/fused?sources=sws&limit=1").json()
    seg = fused["segments"][0]["segment_id"]
    d = client.get(f"/api/segments/forecast/{seg}?moment=ice-event-night").json()
    assert d["predicted"]["label"] in {"Dry", "Damp", "Wet", "Ice", "Snow"}
    assert "observed" in d and "match" in d
    # the predicted condition is published as valid DATEX II (forecast)
    assert d["datex"]["status"] == "valid"
    assert d["datex"]["probability_of_occurrence"] in {"probable", "riskOf"}


@needs_db
def test_source_yields_canonical_observation():
    from adapter.models import CanonicalObservation
    from sources.registry import get_source

    obs = next(get_source("sws").iter_observations(), None)
    assert isinstance(obs, CanonicalObservation)
    assert obs.source == "sws"
    assert -90 <= obs.coordinates.lat <= 90
