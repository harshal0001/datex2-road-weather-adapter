"""Smoke tests — these must always pass. If they fail, the demo will fail."""
import csv
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from adapter.models import (
    CanonicalObservation,
    Coordinates,
    SurfaceCondition,
    WeatherInputs,
)
from adapter.profiles import load_profile
from api.main import app

client = TestClient(app)


def test_root_responds():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "DATEX II Adapter"


def test_health_responds():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("ok", "degraded")


def test_bavaria_profile_loads():
    profile = load_profile("bavaria")
    assert profile.name == "bavaria"
    for code in (0, 1, 2, 3, 4, 5, 255):
        assert code in profile.condition_codes
    # Values verified against WeatherRelatedRoadConditionTypeEnum (literals.csv).
    assert profile.datex2_for(0) == "dry"
    assert profile.datex2_for(5) == "ice"
    assert profile.datex2_for(255) == "other"


def test_profile_enum_values_are_real_datex2_literals():
    """Every condition-code mapping must be a real WeatherRelatedRoadConditionType
    literal. Guards against the `iceOnRoad`/`snowOnRoad`/`unknown` regression that
    would fail XSD validation (see docs/PANEL_QA.md §2).
    """
    literals_csv = (
        Path(__file__).resolve().parents[1]
        / "schemas" / "DATEXII_3_Profile" / "literals.csv"
    )
    if not literals_csv.exists():
        import pytest

        pytest.skip("DATEX II literals.csv not present (schema not downloaded)")

    valid = set()
    with literals_csv.open(encoding="utf-8-sig") as f:
        for row in csv.reader(f, delimiter=";"):
            if len(row) >= 3 and row[1] == "WeatherRelatedRoadConditionTypeEnum":
                valid.add(row[2])

    assert valid, "no WeatherRelatedRoadConditionTypeEnum literals found"
    profile = load_profile("bavaria")
    for code, entry in profile.condition_codes.items():
        value = profile.datex2_for(code)
        assert value in valid, (
            f"condition code {code} maps to '{value}', which is NOT a valid "
            f"WeatherRelatedRoadConditionTypeEnum literal"
        )


def test_datex2_dataclasses_importable():
    """Verify xsdata generation produced our workhorse classes.

    If this fails: re-run `python scripts/generate_dataclasses.py`.
    """
    from generated.datex2.payload_publication import PayloadPublication
    from generated.datex2.measured_data_publication import MeasuredDataPublication
    from generated.datex2.elaborated_data_publication import ElaboratedDataPublication
    from generated.datex2.measurement_site_table_publication import (
        MeasurementSiteTablePublication,
    )
    from generated.datex2.road_surface_conditions import RoadSurfaceConditions

    for cls in (
        PayloadPublication,
        MeasuredDataPublication,
        ElaboratedDataPublication,
        MeasurementSiteTablePublication,
        RoadSurfaceConditions,
    ):
        assert hasattr(cls, "__dataclass_fields__"), f"{cls.__name__} is not a dataclass"


def test_canonical_observation_roundtrip():
    obs = CanonicalObservation(
        station_id="GAT-TPK-0004",
        timestamp=datetime(2026, 1, 15, 3, 0, tzinfo=timezone.utc),
        horizon="now",
        coordinates=Coordinates(lat=50.34312, lon=11.97851),
        weather=WeatherInputs(
            air_temp_c=-2.0,
            road_surface_temp_c=-1.5,
            humidity_pct=95.0,
        ),
        surface_condition=SurfaceCondition.ICE,
        confidence=0.87,
        source="lorawan_csv",
    )
    assert obs.surface_condition == 5
    dumped = obs.model_dump_json()
    reloaded = CanonicalObservation.model_validate_json(dumped)
    assert reloaded.station_id == obs.station_id
    assert reloaded.surface_condition == SurfaceCondition.ICE
