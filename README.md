# DATEX II Adapter

Pluggable Python service that transforms road-weather forecasts from any source into validated
**DATEX II v3.4** XML/JSON. Built around three abstractions:

- **`Source` plug-in** — one class per input system (WDMS REST, LoRaWAN CSV, OpenWeatherMap, …)
- **`MappingProfile` YAML** — condition-code & field-name tables (no code change to support a new jurisdiction)
- **`OutputFormat` plug-in** — DATEX II today; NeTEx / custom formats tomorrow

## Architecture

```
[ existing system (Flask, Vue, Redis) ]   [ LoRaWAN CSV ]   [ OpenWeatherMap CSV ]
            └──────────────┬─────────────────────┴────────────────────┘
                           ▼  Source plug-ins emit CanonicalObservation
                 ┌────────────────────────────────┐
                 │  Mapper (driven by YAML profile)│
                 │  → xsdata DATEX II dataclasses  │
                 │  → XmlSerializer / JsonSerializer│
                 │  → xmlschema XSD validation     │
                 └────────────────┬───────────────┘
                                  ▼
                    FastAPI (Swagger UI at /docs, demo UI at /demo)
```

## Quickstart

```bash
# 1. Install
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Download the DATEX II v3.4 profile (manual — see schemas/README.md)
#    Place datex2-v3.4.xsd into schemas/
python scripts/generate_dataclasses.py

# 3. Build the demo database (one-time, ~10 min)
python scripts/build_demo_db.py \
    --lorawan "/mnt/c/Users/ASUS/Downloads/lorawanglatteisv3_full_export.csv" \
    --owm     "/mnt/c/Users/ASUS/Downloads/openweathermaphofv1_full_export.csv"

# 4. Run
uvicorn api.main:app --reload --port 8000
# → http://localhost:8000/docs
# → http://localhost:8000/health
```

## Project layout

```
adapter/         core: canonical model, mapper, serializer, validator, profile loader
sources/         input plug-ins (one file = one source)
outputs/         output plug-ins (DATEX II today, others later)
api/             FastAPI app + routers
profiles/        YAML mapping profiles (bavaria.yaml ships by default)
schemas/         DATEX II XSDs (gitignored — download via webtool.datex2.eu)
generated/       xsdata-generated dataclasses (gitignored — regenerate)
data/            stations.json + demo.db (gitignored)
scripts/         one-shot tooling (build_demo_db, generate_dataclasses, …)
tests/           pytest suite + smoke tests for the live demo
```

## Demo safety guarantees

- All demo scenarios served from local SQLite — **no live network during the demo path**.
- Every response carries `X-Validation-Status: passed`.
- `/health` shows every source's status — run before the defense.
- `docker compose up` reproduces the whole demo on any laptop.

## Adopting this in your system

1. Implement a `Source` subclass in `sources/` (~30 lines).
2. Copy `profiles/bavaria.yaml` → `profiles/your-jurisdiction.yaml`, edit the code table.
3. Run. That's it.

See `sources/base.py` for the contract and `profiles/bavaria.yaml` for an annotated example.
