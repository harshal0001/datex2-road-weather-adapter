"""Representative demo scenarios for the /demo view.

These are *illustrative* raw readings (not historical records) used to drive the
generic /transform pipeline live — so the demo can show icy/snowy conditions and
their validated DATEX II output regardless of what the latest snapshot holds.
Each scenario's raw rows are exactly what a real source would emit, so the
transform path exercised is identical to production.
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    {
        "id": "icy-mountain-night",
        "title": "Icy mountain night",
        "emoji": "❄️",
        "blurb": "Sub-zero road surface on an elevated segment — black-ice risk.",
        "lat": 50.4112, "lon": 11.6210, "elevation_m": 655.0,
        "road_name": "St 2198 (Geroldsgrün)",
        "selected": ["sws", "dwd"],
        "sources": {
            "sws": {
                "road_condition_code": 3.0,            # → ice
                "road_surface_temperature_celsius": -2.5,
                "air_temperature_celsius": -1.5,
                "dew_point_celsius": -1.8,
                "relative_humidity_percent": 96.0,
                "water_film_mm": 0.0,
            },
            "dwd": {"air_pressure_sea_level_hpa": 1019.0, "visibility_meters": 180.0},
        },
    },
    {
        "id": "urban-snow",
        "title": "Urban snow",
        "emoji": "🌨️",
        "blurb": "Snow lying on a city segment in Hof.",
        "lat": 50.3110, "lon": 11.9120, "elevation_m": 470.0,
        "road_name": "B15 (Hof Zentrum)",
        "selected": ["sws", "dwd"],
        "sources": {
            "sws": {
                "road_condition_code": 4.0,            # → snowOnTheRoad
                "road_surface_temperature_celsius": -3.2,
                "air_temperature_celsius": -2.0,
                "relative_humidity_percent": 92.0,
                "water_film_mm": 0.0,
            },
            "dwd": {"air_pressure_sea_level_hpa": 1012.0, "visibility_meters": 600.0},
        },
    },
    {
        "id": "freezing-transition",
        "title": "Freezing transition",
        "emoji": "💧",
        "blurb": "Wet road hovering around 0 °C — about to freeze.",
        "lat": 50.3600, "lon": 11.9200, "elevation_m": 560.0,
        "road_name": "St 2192 (Töpen)",
        "selected": ["sws", "dwd"],
        "sources": {
            "sws": {
                "road_condition_code": 2.0,            # → wet
                "road_surface_temperature_celsius": 0.3,
                "air_temperature_celsius": 0.5,
                "dew_point_celsius": 0.1,
                "relative_humidity_percent": 90.0,
                "water_film_mm": 0.4,
            },
            "dwd": {"air_pressure_sea_level_hpa": 1008.0, "visibility_meters": 3400.0},
        },
    },
    {
        "id": "dry-day",
        "title": "Lowland dry day",
        "emoji": "☀️",
        "blurb": "Mild, dry conditions on a lowland segment.",
        "lat": 50.3000, "lon": 12.0040, "elevation_m": 520.0,
        "road_name": "St 2188 (Regnitzlosau)",
        "selected": ["sws", "dwd", "openweather"],
        "sources": {
            "sws": {
                "road_condition_code": 0.0,            # → dry
                "road_surface_temperature_celsius": 14.0,
                "air_temperature_celsius": 11.8,
                "relative_humidity_percent": 54.0,
                "water_film_mm": 0.0,
            },
            "dwd": {"air_pressure_sea_level_hpa": 1021.0, "visibility_meters": 24000.0},
        },
    },
]

_BY_ID = {s["id"]: s for s in SCENARIOS}


def list_scenarios() -> list[dict]:
    """Lightweight list (no raw payloads) for the picker."""
    return [
        {k: s[k] for k in ("id", "title", "emoji", "blurb", "road_name")}
        for s in SCENARIOS
    ]


def get_scenario(scenario_id: str) -> dict | None:
    return _BY_ID.get(scenario_id)
