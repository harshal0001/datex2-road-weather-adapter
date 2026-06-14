"""FastAPI entrypoint. Minimal for Step 0 — routers added in later phases."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapter import __version__
from adapter.profiles import list_profiles

DEMO_DB = Path(__file__).resolve().parents[1] / "data" / "demo.db"

app = FastAPI(
    title="DATEX II Adapter",
    version=__version__,
    description=(
        "Pluggable adapter that transforms road-weather forecasts into validated "
        "DATEX II v3.4 XML/JSON. Swagger UI below; demo UI at /demo (added in Phase D)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _demo_db_status() -> dict[str, Any]:
    if not DEMO_DB.exists():
        return {
            "status": "missing",
            "hint": "Run scripts/build_demo_db.py to seed the demo data.",
        }
    try:
        conn = sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True)
        stations = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        lorawan = conn.execute("SELECT COUNT(*) FROM lorawan_obs").fetchone()[0]
        owm = conn.execute("SELECT COUNT(*) FROM owm_obs").fetchone()[0]
        conn.close()
        return {
            "status": "ready",
            "stations": stations,
            "lorawan_observations": lorawan,
            "owm_observations": owm,
        }
    except sqlite3.Error as e:
        return {"status": "error", "detail": str(e)}


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "DATEX II Adapter",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness + dependency status. Run this before every demo."""
    db = _demo_db_status()
    overall = "ok" if db.get("status") == "ready" else "degraded"
    return {
        "status": overall,
        "version": __version__,
        "demo_db": db,
        "profiles_available": list_profiles(),
    }
