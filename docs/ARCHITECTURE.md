# DATEX II Adapter — Architecture & How It Works

> Companion to `docs/PROTOTYPE.md` (what & why) and `docs/PANEL_QA.md` (defense).
> This document focuses on **how the system is structured and how data flows through it**.
> Last updated: 2026-06-12.

---

## 1. System context (the 10,000-ft view)

Where the adapter sits relative to the existing Bavaria system and the European ecosystem.
It is a **sidecar**: it reads the same upstream data the existing system uses, and publishes
the standardized result — *without modifying the existing Flask/Vue stack*.

```
   UPSTREAM DATA                  THIS PROTOTYPE                 DOWNSTREAM CONSUMERS
 ┌───────────────────┐        ┌──────────────────────┐        ┌────────────────────────┐
 │ SWS road stations │        │                      │        │ National Access Point  │
 │ DWD climate       │  ───►  │   DATEX II ADAPTER    │  ───►  │ (DE: MDM / Mobilithek) │
 │ LoRaWAN network   │        │   (sidecar service)   │        │ Neighbouring countries │
 │ OpenWeatherMap    │        │                      │        │ (AT ASFINAG, FR …)     │
 │ WDMS Flask API    │        └──────────────────────┘        │ Navigation / traffic   │
 └───────────────────┘                  │                      │ service providers      │
                                         │ (does NOT modify)    └────────────────────────┘
   ┌─────────────────────────────────────▼──────────────────────┐
   │  EXISTING HOF SYSTEM  (Flask + Redis + Vue + AI model)      │  ← untouched
   └─────────────────────────────────────────────────────────────┘
```

**Key property:** the adapter is *additive*. It consumes the same sources, so it can run and
demo entirely on its own — and in production it would publish to the NAP alongside the
existing system, not in place of it.

---

## 2. Internal architecture (Ports & Adapters / hexagonal)

The whole design exists to serve one goal: **decouple N inputs from M outputs through a single
canonical model**, so adding either side is a configuration/plug-in change, not a rewrite.

```
   ┌──────────────────────────── DATEX II ADAPTER ────────────────────────────┐
   │                                                                          │
   │   INPUT PORTS                  CORE DOMAIN                  OUTPUT PORTS  │
   │  (Source plug-ins)                                       (Output plug-ins)│
   │                                                                          │
   │  ┌──────────────┐         ┌────────────────────┐                         │
   │  │ SwsSqlite     │──┐      │  FieldNormalizer    │      ┌──────────────┐  │
   │  │ DwdSqlite     │  │      │  (uses MappingProfile│      │ DATEX II XML  │  │
   │  │ LoRaWANSqlite │  ├────► │   field_map)         │ ┌──► │ (+ validate)  │  │
   │  │ OwmSqlite     │  │      └─────────┬───────────┘ │   └──────────────┘  │
   │  │ WdmsApi(live) │──┘                ▼             │   ┌──────────────┐  │
   │  └──────────────┘         ┌────────────────────┐  ├──► │ JSON (debug)  │  │
   │        ▲                  │ CanonicalObservation│  │   └──────────────┘  │
   │        │                  │  (the contract)     │  │   ┌──────────────┐  │
   │   reads CSV/JSON/SQLite   └─────────┬───────────┘  └──► │ Plain English │  │
   │                                     ▼              │   └──────────────┘  │
   │                          ┌────────────────────┐    │                     │
   │                          │   Mapper            │────┘                     │
   │                          │ (canonical→DATEX II)│                          │
   │                          └─────────┬───────────┘                          │
   │   MappingProfile (YAML) ───────────┘  ▲                                   │
   │   condition_codes + field_map         │ Validator (xmlschema vs XSD)      │
   │                                       └───────────────────────────────────│
   │                                                                          │
   │   API LAYER (FastAPI): /transform · /publication · /sources · /stations  │
   │                        /scenarios · /demo · /health   + middleware       │
   └──────────────────────────────────────────────────────────────────────────┘
```

### The three extension points (this is the reusability story)

| Want to… | Do this | Touch the core? |
|----------|---------|-----------------|
| Add a new input system | Write one **Source** plug-in (`sources/*.py`) | ❌ No |
| Adapt to a new jurisdiction | Write one **MappingProfile** YAML (`profiles/*.yaml`) | ❌ No |
| Emit a new output format | Write one **Output** plug-in (`outputs/*.py`) | ❌ No |

Everything between the ports — the canonical model, normalizer, mapper, validator — stays the
same regardless of which source, jurisdiction, or output you plug in.

---

## 3. The canonical model — the pivot everything turns on

Every source is normalized into one `CanonicalObservation` (`adapter/models.py`). This is the
*contract* that makes N+M possible instead of N×M.

```
                    Without canonical model            With canonical model
                    (point-to-point: N×M)              (hub-and-spoke: N+M)

   SWS ─┐                                           SWS ─┐                 ┌─ XML
   DWD ─┼─ each source mapped to each output        DWD ─┤                 ├─ JSON
   LoRa─┼─  = 5 sources × 3 outputs = 15 maps       LoRa─┼─► CANONICAL ───►┼─ Plain
   OWM ─┤                                           OWM ─┤    MODEL        └─ …
   WDMS─┘                                           WDMS─┘   5 in + 3 out = 8 maps
```

```
CanonicalObservation
├── station_id        str
├── timestamp         datetime (UTC)
├── horizon           "now" | "in_3h" | "in_18h"     ← AI forecast window
├── coordinates       {lat, lon, elevation_m}
├── weather           WeatherInputs (all optional)
│   ├── air_temp_c, dew_point_c, humidity_pct
│   ├── wind_speed_ms, wind_direction_deg
│   ├── road_surface_temp_c, subsurface_temp_5cm_c, subsurface_temp_30cm_c
│   └── precipitation_mm
├── surface_condition SurfaceCondition (0..5, 255)   ← AI output, mapped via profile
├── confidence        float 0..1                     → DATEX II probabilityOfOccurrence
├── source            str
└── model_version     str | None
```

---

## 4. End-to-end data flow — one transform, step by step

What actually happens when a request asks for station **P047** as DATEX II. Numbers in the
diagram correspond to the steps below.

```
  CLIENT                API LAYER            CORE                         OUTPUT
    │                      │                  │                             │
    │  GET /transform      │                  │                             │
    │  ?station=P047 ─(1)─►│                  │                             │
    │                      │─(2) pick source─►│                             │
    │                      │   + profile      │                             │
    │                      │                  │─(3) read raw row ──► demo.db│
    │                      │                  │◄──── {TEMP, BTEMP, …} ──────│
    │                      │                  │                             │
    │                      │                  │─(4) FieldNormalizer         │
    │                      │                  │     raw → canonical fields  │
    │                      │                  │     (TEMP→air_temp_c, fix    │
    │                      │                  │      in3h→in_3h, K→°C)       │
    │                      │                  │                             │
    │                      │                  │─(5) build CanonicalObservation
    │                      │                  │     surface_condition=5(ICE)│
    │                      │                  │                             │
    │                      │                  │─(6) Mapper + MappingProfile │
    │                      │                  │     5 → "ice"               │
    │                      │                  │     conf 0.87 → prob 87     │
    │                      │                  │     → DATEX II dataclasses ─►│ serialize XML
    │                      │                  │                             │
    │                      │                  │─(7) Validator (xmlschema) ─►│ check vs XSD
    │                      │                  │◄──── VALID / errors ────────│
    │                      │◄─(8) XML + headers│                            │
    │◄─(9) 200 OK ─────────│   X-Validation-Status: valid                   │
    │   <payload>…</payload>   X-Transform-Time-Ms: 47                      │
    │                          X-Source-Used: sws_sqlite  X-Profile: bavaria│
```

**Step-by-step:**
1. **Request** — client calls `/transform` for a station (+ optional source/profile/horizon).
2. **Resolve** — API selects the Source plug-in (default `sws_sqlite`) and the MappingProfile
   (default `bavaria`).
3. **Read** — the Source reads the raw record from `demo.db` (or a live feed in production).
4. **Normalize** — `FieldNormalizer` renames source fields to canonical ones using the
   profile's `field_map`, fixes the `in3h`/`in_3h` naming bug, and converts units (e.g. K→°C).
5. **Canonicalize** — a `CanonicalObservation` is built — the source-agnostic representation.
6. **Map** — the Mapper turns it into DATEX II dataclasses, using the profile's
   `condition_codes` (e.g. `5 → "ice"`) and confidence→`probabilityOfOccurrence`, then
   serializes to XML.
7. **Validate** — the Validator checks the XML against the official XSD (hard gate).
8. **Annotate** — middleware attaches timing/validation/source/profile response headers.
9. **Respond** — conformant DATEX II XML (or JSON / plain-English on the demo endpoints).

---

## 5. Which DATEX II publication is produced

Aligned to the official **Road Weather Information Recommended Profile**. The Mapper chooses the
publication that fits the data kind:

```
 CanonicalObservation ──► Mapper ──┬─► MeasurementSiteTablePublication   (where the station is)
                                   ├─► MeasuredDataPublication           (raw sensor readings)
                                   │      └ Humidity · TemperatureInformation
                                   │        PrecipitationInformation · WindInformation
                                   │        RoadSurfaceConditionInformation
                                   ├─► SituationPublication              (hazard state)
                                   │      └ WeatherRelatedRoadConditions
                                   │          └ RoadSurfaceConditionMeasurements
                                   │              └ WeatherRelatedRoadConditionTypeEnum
                                   │                 (dry|moist|wet|glaze|snowOnTheRoad|ice|other)
                                   └─► ElaboratedDataPublication         (AI FORECAST — *extends*
                                          └ probabilityOfOccurrence ◄ confidence   the profile)
```

> The official profile is **measurement-only**; the `ElaboratedDataPublication` forecast path
> with uncertainty is a deliberate **extension** — a core contribution of the work.

---

## 6. Demo-safety architecture

The single most important non-functional property: **the demo must not depend on a live
network.** Achieved by pre-indexing the source CSVs into a local SQLite store.

```
  BUILD TIME (once, offline)                      DEMO TIME (no network)
  ┌──────────────────────────┐                   ┌──────────────────────────┐
  │ raw CSVs (SWS, DWD,       │   build_demo_db   │ Source plug-ins read      │
  │ LoRaWAN, OWM)  ~1.6 GB    │ ────────────────► │ demo.db  (indexed,        │
  │                          │   parse, index    │  <10 ms lookups)          │
  └──────────────────────────┘                   └──────────────────────────┘
                                                            │
                                                  Everything downstream is
                                                  pure CPU — no I/O risk live.
```

- `demo.db` is pre-built, indexed on `(station_id, timestamp)`, WAL mode.
- The WDMS live-API source is **optional** — SWS provides the same station IDs offline, so the
  demo never needs the Flask system running.
- `/scenarios` serves frozen, known-good moments so the demo path is deterministic.

---

## 7. Component & directory map

```
datex2-adapter/
├── adapter/                  CORE DOMAIN (source/output-agnostic)
│   ├── models.py             CanonicalObservation, SurfaceCondition, WeatherInputs   ✅
│   ├── profiles/             MappingProfile loader (load_profile)                    ✅
│   ├── normalizer.py         FieldNormalizer                                         ⬜
│   ├── mapper.py             canonical → DATEX II dataclasses                        ⬜
│   └── validator.py          xmlschema XSD gate                                      ⬜
├── sources/                  INPUT PORTS (one class per system)
│   ├── base.py               Source ABC (health, iter_observations)                 ✅
│   └── {sws,dwd,lorawan,owm}_sqlite.py · wdms_api.py                                 ⬜
├── outputs/                  OUTPUT PORTS (DATEX II XML, JSON, plain-English)        ⬜
├── api/main.py               API LAYER (FastAPI) + middleware                        ✅(partial)
├── profiles/bavaria.yaml     CONFIG: condition_codes + field_map                     ✅
├── data/{demo.db,stations.json}   demo substrate                                     ✅
├── schemas/DATEXII_3_Profile/     official XSDs + data dictionary                    ✅
├── generated/datex2/         914 xsdata dataclasses (gitignored)                     ✅
├── static/demo.html          frontend mockup                                        ✅
└── scripts/{build_demo_db,generate_dataclasses}.py                                   ✅
```

**Dependency rule (hexagonal):** `sources/` and `outputs/` depend on `adapter/` (the core).
The core depends on **nothing** outward — it knows only `CanonicalObservation` and the profile.
This is what keeps the plug-ins swappable.

---

## 8. Runtime / deployment view

```
  ┌─────────────────── Docker container (python:3.11-slim) ───────────────────┐
  │   uvicorn ──► FastAPI app (api.main:app)  ──► core + plug-ins              │
  │                     │                                                      │
  │   mounts:  ./data (demo.db)  ./schemas (XSD)  ./profiles  ./generated      │
  │   health:  GET /health  every 30s                                         │
  └────────────────────────────────────────────────────────────────────────────┘
         exposes :8000          `docker compose up`  →  one-command demo
```

- **Stateless** transform → horizontally scalable (run N replicas behind a load balancer).
- **Production evolution** (not in prototype scope): put a message broker (e.g. Kafka) in front
  for real-time fan-in at 500+ stations, and add a DATEX II **Exchange** delivery plug-in
  (one of the 3 operating modes) to publish to the NAP. Both *wrap* this architecture — the
  canonical model is exactly the on-the-wire schema they'd build on.

---

## 9. How the reusability claim plays out concretely

Adopting the adapter for a **new jurisdiction** (e.g. a different country's road network):

```
  1. Copy profiles/bavaria.yaml → profiles/<region>.yaml
       • remap condition_codes  (their codes → WeatherRelatedRoadConditionTypeEnum literals)
       • remap field_map        (their column names → canonical fields)
  2. If their data lives somewhere new → write one Source plug-in (≈ a SQL query or HTTP call)
  3. Point /transform at ?profile=<region>
       → valid DATEX II out, with ZERO changes to the core, mapper, or validator.
```

The boundary of "config-only": **field names, units, condition codes** are pure YAML.
**Location referencing** beyond coordinates (ALERT-C/OpenLR) and consumer-specific profile
choices may need code — the one honest caveat (see `docs/PANEL_QA.md` §5).

---

## 10. Cross-references

- **What & why, build plan, status** → `docs/PROTOTYPE.md`
- **Defense Q&A, alternative architectures, limitations** → `docs/PANEL_QA.md`
- **Frontend mockup** → `static/demo.html`
