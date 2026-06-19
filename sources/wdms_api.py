"""Live WDMS source — the existing Hof Flask API (GET :4000/get_data).

Optional integration path: the offline SWS source already serves the same station
IDs, so the demo never needs this. Implemented so the registry shows the
live-integration option and reports whether the Flask system is reachable.
"""
from __future__ import annotations

import socket
from datetime import datetime
from typing import Iterator, Optional

from adapter.models import CanonicalObservation
from sources.base import Source

WDMS_HOST = "127.0.0.1"
WDMS_PORT = 4000


class WdmsApiSource(Source):
    name = "wdms"

    def health(self) -> dict:
        try:
            with socket.create_connection((WDMS_HOST, WDMS_PORT), timeout=0.3):
                return {"status": "ok", "detail": f"reachable at {WDMS_HOST}:{WDMS_PORT}"}
        except OSError:
            return {
                "status": "down",
                "detail": "live Flask system not running (optional — SWS covers it offline)",
            }

    def iter_observations(
        self,
        station_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Iterator[CanonicalObservation]:
        # Live fetch + normalization is future work; offline SWS is the demo path.
        return iter(())
