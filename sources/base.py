"""Source plug-in contract. Implement this ABC to add a new input system.

Example:
    class MyCustomSource(Source):
        name = "my_source"

        def health(self):
            return {"status": "ok"}

        def iter_observations(self, station_id=None, since=None, until=None):
            for row in my_db.query(...):
                yield CanonicalObservation(...)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterator, Optional

from adapter.models import CanonicalObservation


class Source(ABC):
    """Pluggable data source. One class per input system.

    Subclasses are auto-discovered by sources.registry.list_sources().
    """

    name: str = ""  # must be set by subclass; matches profile references

    @abstractmethod
    def health(self) -> dict:
        """Return source liveness. Shape: {'status': 'ok'|'degraded'|'down', 'detail': str}."""
        ...

    @abstractmethod
    def iter_observations(
        self,
        station_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Iterator[CanonicalObservation]:
        """Yield canonical observations matching the filters.

        - station_id: if given, restrict to that station; else all stations.
        - since/until: time-window filter; both optional.
        """
        ...
