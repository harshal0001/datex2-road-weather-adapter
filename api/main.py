"""FastAPI entrypoint. Minimal for Step 0 — routers added in later phases."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from adapter import __version__
from adapter.profiles import list_profiles
from api.segments_routes import router as segments_router
from api.segments_routes import transform_router

ROOT = Path(__file__).resolve().parents[1]
DEMO_DB = ROOT / "data" / "demo.db"
SEGMENTS_DB = ROOT / "data" / "segments.db"
STATIC_DIR = ROOT / "static"

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

app.include_router(segments_router)
app.include_router(transform_router)


@app.middleware("http")
async def add_timing_header(request, call_next):
    """Stamp every response with how long it took to produce (Step 11)."""
    import time

    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Transform-Time-Ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
    return response


def _segments_db_status() -> dict[str, Any]:
    if not SEGMENTS_DB.exists():
        return {"status": "missing",
                "hint": "Run scripts/build_segment_snapshots.py --rebuild"}
    try:
        conn = sqlite3.connect(f"file:{SEGMENTS_DB}?mode=ro", uri=True)
        segs = conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        snaps = conn.execute("SELECT COUNT(*) FROM segment_snapshot").fetchone()[0]
        conn.close()
        return {"status": "ready", "segments": segs, "snapshot_rows": snaps}
    except sqlite3.Error as e:
        return {"status": "error", "detail": str(e)}


@app.get("/sources")
def sources() -> dict[str, Any]:
    """Auto-discovered source plug-ins + live health (Step 5)."""
    from sources.registry import health_report

    return {"sources": health_report()}


# serve the single-file UIs fresh — they change often during development, so never
# let the browser cache a stale copy
_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}


@app.get("/dashboard")
def dashboard() -> FileResponse:
    """Multi-source fusion + road-segment map dashboard."""
    return FileResponse(STATIC_DIR / "dashboard.html", headers=_NO_CACHE)


@app.get("/demo")
def demo() -> FileResponse:
    """Non-technical demo: raw data → validated DATEX II → plain English."""
    return FileResponse(STATIC_DIR / "demo.html", headers=_NO_CACHE)


# demo.db row-counts are invariant at runtime (built once by build_demo_db.py), so we
# COUNT them once and cache the result. Without this, every /health re-scans ~4.3M rows
# (~13 s) — the worst offender found by the jMeter benchmark.
_DEMO_COUNTS: dict[str, int] | None = None


def _demo_db_status() -> dict[str, Any]:
    global _DEMO_COUNTS
    if not DEMO_DB.exists():
        return {
            "status": "missing",
            "hint": "Run scripts/build_demo_db.py to seed the demo data.",
        }
    try:
        if _DEMO_COUNTS is None:  # one-time populate; served from cache thereafter
            conn = sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True)
            _DEMO_COUNTS = {
                "stations": conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0],
                "lorawan_observations": conn.execute("SELECT COUNT(*) FROM lorawan_obs").fetchone()[0],
                "owm_observations": conn.execute("SELECT COUNT(*) FROM owm_obs").fetchone()[0],
            }
            conn.close()
        return {"status": "ready", **_DEMO_COUNTS}
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
    seg = _segments_db_status()
    overall = "ok" if seg.get("status") == "ready" else "degraded"
    return {
        "status": overall,
        "version": __version__,
        "demo_db": db,
        "segments_db": seg,
        "profiles_available": list_profiles(),
    }
