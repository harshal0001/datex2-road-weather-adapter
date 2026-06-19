# DATEX II Road-Weather Adapter

Turns Bavaria's heterogeneous road-weather data (SWS road stations, DWD climate, LoRaWAN
sensors, OpenWeatherMap) into the **European DATEX II v3** standard — by **fusing multiple
sources per field** and emitting **XSD-validated** output that any European traffic centre
can consume.

> Your sensor speaks Bavarian. **DATEX II is the European common language.** This adapter is
> the translator.

Built around four extension points — add capability by **configuration or one plug-in**, not
a rewrite:

- **`Source` plug-in** (`sources/*.py`) — one class per input system
- **`fusion.yaml`** — per-field source priority (the research artefact)
- **`MappingProfile` YAML** (`profiles/*.yaml`) — condition-code & field-name tables per jurisdiction
- **`outputs/*.py`** — DATEX II today; other formats tomorrow

## What it does

```
 SWS · DWD · LoRaWAN · OpenWeather        FUSION ENGINE              OUTPUT
 (raw rows, keyed by segment_id)   ─►  per-field priority      ─►  DATEX II v3 XML
 road_segments_with_elevation         + provenance                (XSD-validated)
        │  (geometry)                       │                      GeoJSON · JSON
        └────────── segments.db ────────────┘                      Leaflet map · plain English
```

Only **SWS** carries the ground-truth road condition; **DWD/OpenWeather** own atmospherics;
**LoRaWAN** is a sparse newer sensor. The fusion engine reconciles them per field (with full
provenance) before standardizing — so no single source needs to be complete.

## Quickstart

`segments.db` (the demo store) and the DATEX II schema bundle are **committed**, so the
dashboard works straight from a clone — the only build step is generating the dataclasses.

```bash
git clone <repo> && cd datex2-road-weather-adapter
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# generate the DATEX II dataclasses from the committed XSDs (xsdata)
python scripts/generate_dataclasses.py

# run
python -m uvicorn api.main:app --reload --port 8000
```

Then open:
- **http://localhost:8000/dashboard** — multi-source fusion map (toggle sources, click a segment)
- **http://localhost:8000/demo** — non-technical view: raw → validated DATEX II → plain English
- **http://localhost:8000/docs** — Swagger UI

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + store/profile status |
| GET | `/sources` | Auto-discovered source plug-ins + health/coverage |
| POST | `/api/transform` | **Generic: any raw multi-source data → validated DATEX II** |
| GET | `/api/segments` | Road-segment catalogue |
| GET | `/api/segments/geojson` | Fused segments as GeoJSON (drives the map) |
| GET | `/api/segments/datex?segment_id=…` | XSD-validated DATEX II for one segment |
| GET | `/api/segments/datex/city` | Validated multi-segment publication |
| GET | `/api/segments/coverage` · `/priority` · `/fused` | Fusion stats / config / data |
| GET | `/api/scenarios` · `/api/scenarios/{id}` | Demo scenarios |

Responses carry `X-Validation-Status`, `X-Transform-Time-Ms`; `/transform` adds `X-Source-Used`, `X-Profile`.

## Adopting for a new jurisdiction (config, not code)

1. **Condition scheme** — copy `profiles/segment_conditions.yaml` → `profiles/<region>.yaml`;
   map your codes to `WeatherRelatedRoadConditionTypeEnum` literals (verified set in
   `schemas/.../literals.csv`).
2. **Source field names / priority** — edit `profiles/fusion.yaml`: add a `source_fields` block
   (their column → canonical field) and per-field `field_priority`.
3. **New input system** — add one `sources/<name>.py` subclass of `Source`; it's auto-registered.

No change to the core (fusion engine, mapper, validator) is needed.

## Tests & evaluation

```bash
pytest -q                          # full suite (incl. XSD conformance matrix + round-trip)
python scripts/evaluate.py         # latency, conformance %, condition distribution, provenance
```

Indicative results (Hof network, 1,021 segments): transform **~5.7 ms mean** (p95 ~6.9 ms),
**100% XSD-conformance** on the validation sample.

## Rebuilding the data store (optional)

`segments.db` is committed. To rebuild from raw exports (the parquet + four aggregated CSVs):

```bash
python scripts/build_segment_snapshots.py --downloads <dir-with-csvs-and-parquet> --rebuild
```

## Docker

```bash
docker compose up        # builds, regenerates dataclasses, serves on :8000
```

## Project layout

```
adapter/   core — canonical model, fusion engine, segment store, validator, profile loader
sources/   input plug-ins (sws/dwd/lorawan/openweather sqlite + wdms live stub) + registry
outputs/   DATEX II builder (xsdata dataclasses → validated <payload>)
api/       FastAPI app + routers (/dashboard, /demo, /sources, /api/*)
profiles/  fusion.yaml + condition profiles (bavaria 6-class, segment_conditions 5-class)
schemas/   DATEX II v3 XSDs + data dictionary (committed)
generated/ xsdata dataclasses (gitignored — regenerate)
data/      segments.db (committed, 4 MB) · demo.db (gitignored)
scripts/   build_segment_snapshots · build_demo_db · generate_dataclasses · evaluate
docs/      PROTOTYPE · ARCHITECTURE · PANEL_QA · PROGRESS · SOFTWARE_SPECIFICATION_AND_DESIGN
static/    dashboard.html · demo.html
```

## Documentation

- `docs/PROTOTYPE.md` — what & why, build plan
- `docs/ARCHITECTURE.md` — how it works (diagrams, data flow)
- `docs/PROGRESS.md` — task/progress tracker
- `docs/PANEL_QA.md` — thesis-defense Q&A + alternative architectures
- `docs/SOFTWARE_SPECIFICATION_AND_DESIGN.md` — full specification report

> Targets DATEX II **v3.4** (current at project inception); the road-weather model is stable
> through v3.6. Bindings regenerate from whichever XSD version you point at.
