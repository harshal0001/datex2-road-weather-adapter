"""Concrete Source plug-ins backed by the offline segment store (segments.db).

One class per upstream system (SWS / DWD / LoRaWAN / OpenWeather). Each reads the
latest-per-segment snapshot, maps raw columns to canonical fields via the fusion
profile's `source_fields`, and yields CanonicalObservations — satisfying the
Source ABC so a new system is genuinely "one plug-in".
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from adapter.fusion import load_fusion_profile
from adapter.models import (
    CanonicalObservation,
    Coordinates,
    SurfaceCondition,
    WeatherInputs,
)
from sources.base import Source

DB = Path(__file__).resolve().parents[1] / "data" / "segments.db"

# SWS road_condition_code (5-class) -> canonical SurfaceCondition (6-class taxonomy).
# eisglätte(3)->ICE(5), schneeglätte(4)->SNOW(4).
_SWS_CODE_TO_SURFACE = {
    0: SurfaceCondition.DRY, 1: SurfaceCondition.DAMP, 2: SurfaceCondition.WET,
    3: SurfaceCondition.ICE, 4: SurfaceCondition.SNOW,
}
_WEATHER_FIELDS = set(WeatherInputs.model_fields)


class SegmentSqliteSource(Source):
    """Base for sources reading their snapshot rows from segments.db."""

    name = ""

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con

    def health(self) -> dict:
        if not DB.exists():
            return {"status": "down", "detail": "segments.db not built"}
        try:
            con = self._conn()
            row = con.execute(
                "SELECT COUNT(*) n, MAX(event_timestamp) latest "
                "FROM segment_snapshot WHERE source=?",
                (self.name,),
            ).fetchone()
            con.close()
            n = row["n"]
            return {
                "status": "ok" if n else "degraded",
                "segments_covered": n,
                "latest_observation": row["latest"],
            }
        except sqlite3.Error as e:
            return {"status": "down", "detail": str(e)}

    def iter_observations(
        self,
        station_id: Optional[str] = None,  # here: segment_id
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Iterator[CanonicalObservation]:
        if not DB.exists():
            return
        profile = load_fusion_profile()
        field_map = profile.source_fields.get(self.name, {})
        con = self._conn()
        sql = (
            "SELECT s.segment_id, s.lat, s.lon, s.elevation_m, "
            "       snap.event_timestamp, snap.raw_json "
            "FROM segment_snapshot snap JOIN segments s USING (segment_id) "
            "WHERE snap.source=?"
        )
        args: list = [self.name]
        if station_id is not None:
            sql += " AND s.segment_id=?"
            args.append(int(station_id))
        for r in con.execute(sql, args):
            raw = json.loads(r["raw_json"])
            canon = {field_map[k]: v for k, v in raw.items() if k in field_map}
            weather = WeatherInputs(
                **{k: v for k, v in canon.items() if k in _WEATHER_FIELDS}
            )
            code = canon.get("surface_condition")
            surface = (
                _SWS_CODE_TO_SURFACE.get(int(code), SurfaceCondition.UNCLASSIFIABLE)
                if code is not None
                else SurfaceCondition.UNCLASSIFIABLE
            )
            yield CanonicalObservation(
                station_id=str(r["segment_id"]),
                timestamp=_parse_ts(r["event_timestamp"]),
                coordinates=Coordinates(lat=r["lat"], lon=r["lon"], elevation_m=r["elevation_m"]),
                weather=weather,
                surface_condition=surface,
                source=self.name,
            )
        con.close()


def _parse_ts(s: str) -> datetime:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now()


class SwsSqliteSource(SegmentSqliteSource):
    name = "sws"


class DwdSqliteSource(SegmentSqliteSource):
    name = "dwd"


class LoRaWANSqliteSource(SegmentSqliteSource):
    name = "lorawan"


class OwmSqliteSource(SegmentSqliteSource):
    name = "openweather"
