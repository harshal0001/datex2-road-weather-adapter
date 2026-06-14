"""Canonical internal model. Every Source emits this; every output reads this."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SurfaceCondition(IntEnum):
    """Bavarian road maintenance taxonomy (Cisneros et al., 2025)."""
    DRY = 0
    DAMP = 1
    WET = 2
    HOARFROST = 3
    SNOW = 4
    ICE = 5
    UNCLASSIFIABLE = 255


Horizon = Literal["now", "in_3h", "in_18h"]


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    elevation_m: Optional[float] = None


class WeatherInputs(BaseModel):
    """The six paper features + ancillary atmospherics.

    None = not measured/derived by this source. Mapper handles missing values.
    """
    air_temp_c: Optional[float] = None
    dew_point_c: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    humidity_pct: Optional[float] = None
    road_surface_temp_c: Optional[float] = None
    subsurface_temp_5cm_c: Optional[float] = None
    subsurface_temp_30cm_c: Optional[float] = None
    precipitation_mm: Optional[float] = None


class CanonicalObservation(BaseModel):
    """One station, one timestamp, one forecast horizon."""
    station_id: str
    timestamp: datetime
    horizon: Horizon = "now"
    coordinates: Coordinates
    weather: WeatherInputs
    surface_condition: SurfaceCondition = SurfaceCondition.UNCLASSIFIABLE
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str
    model_version: Optional[str] = None
