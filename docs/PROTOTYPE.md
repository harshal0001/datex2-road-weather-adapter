# DATEX II Adapter — Prototype Specification

> **One sentence:** A generic adapter service that turns Bavaria's road‑weather data
> (sensor observations **and** AI surface‑condition forecasts) into the **DATEX II v3.4**
> European standard — validated, reusable for other jurisdictions, and safe to demo offline.

- **Status:** Foundation complete (Steps 0–2). Building the pipeline (Steps 3–14).
- **Author:** founder@curriculo.me (thesis prototype)
- **DATEX II version targeted:** **v3.4** (current at project inception). Latest published
  is **v3.6** (June 2025; model download v3.7). The road-weather data model is stable across
  v3.4–v3.6, so the targeting is deliberate and low-risk — see `docs/PANEL_QA.md` §2.
- **Last updated:** 2026-06-12

---

## 1. Why this exists

Bavaria (region of Hof) runs an AI system that predicts road **surface condition**
(dry / damp / wet / hoarfrost / snow / ice) from weather sensors, based on an ID3 Decision
Tree (Cisneros et al., ISM 2025). The predictions and the raw sensor data live in a
custom JSON format that only the local Flask/Vue system understands.

**The problem:** no other European traffic authority can consume that data. Each country
speaks its own dialect.

**DATEX II** (CEN/TS 16157) is the common European language for road traffic and
travel data — used by national access points (e.g. Germany's MDM, Austria's ASFINAG,
France's Bison Futé). If Bavaria's data is expressed in DATEX II, *any* compliant system
across 30+ countries can read it without bespoke integration.

**This prototype is the translator.** Raw data goes in → validated DATEX II XML comes out.

### Goals

| # | Goal | What it means |
|---|------|---------------|
| G1 | **Standardize** | Emit DATEX II v3.4 XML that validates against the official XSD. |
| G2 | **Generic / reusable** | New data sources or new jurisdictions need *config*, not code rewrites. |
| G3 | **Demo‑safe** | Runs fully offline from a pre‑indexed local database — no live network needed. |
| G4 | **Explainable to non‑technical people** | A visual "your data → DATEX II → plain English" view. |
| G5 | **Provably correct** | Every output is validated; forecasts can be checked against real observations. |

### Non‑goals (for the prototype)
- Not a production deployment (no auth, scaling, or HA).
- Does not retrain or modify the AI model — it consumes the model's outputs.
- Does not modify the existing Flask/Vue system — it sits beside it (sidecar).

---

## 2. Architecture — Ports & Adapters (hexagonal / sidecar)

The core idea that delivers **G2 (reusability)**: everything funnels through one
**canonical internal model**. Inputs and outputs are pluggable around that core.

```
   INPUT SOURCES (plug-ins)          CORE                    OUTPUT (plug-ins)
 ┌───────────────────────┐                                 ┌────────────────────┐
 │ SWS road stations     │─┐                            ┌─►│ DATEX II v3.4 XML   │
 │ DWD climate (hourly)  │─┤    ┌──────────────────┐    │  │ (validated vs XSD)  │
 │ LoRaWAN network       │─┼──► │   FieldNormalizer │    ├─►│ JSON (debug view)   │
 │ OpenWeatherMap        │─┤    │        ↓          │    │  │ Plain-English text  │
 │ WDMS live Flask API   │─┘    │ CanonicalObservation │ │  └────────────────────┘
 └───────────────────────┘      │        ↓          │──┘
                                │   Mapper (driven   │
   MappingProfile (YAML) ──────►│   by profile YAML) │◄──── MappingProfile (YAML)
   condition codes, field map   └──────────────────┘
```

- **Add a new input system?** Write one `Source` plug-in. The core is untouched.
- **Adapt to a new jurisdiction?** Write one `MappingProfile` YAML (different condition
  codes, field names, station IDs). No code change.
- **Need a different output format?** Write one `OutputFormat` plug-in.

### The three extension points

| Abstraction | File(s) | What you change to extend |
|-------------|---------|---------------------------|
| **Source** plug-in | `sources/*.py` | One class per input system (`iter_observations`, `health`). |
| **MappingProfile** | `profiles/*.yaml` | Condition‑code table + field‑name map. Pure config. |
| **OutputFormat** plug-in | `outputs/*.py` | One class per output (DATEX II XML, JSON, …). |

---

## 3. The canonical model (the contract)

Everything in the system is normalized to **`CanonicalObservation`** (`adapter/models.py`).
This is the single source of truth that decouples inputs from outputs.

```
CanonicalObservation
├── station_id:        str
├── timestamp:         datetime (UTC)
├── horizon:           "now" | "in_3h" | "in_18h"
├── coordinates:       {lat, lon, elevation_m}
├── weather:           WeatherInputs (all optional)
│   ├── air_temp_c, dew_point_c, humidity_pct
│   ├── wind_speed_ms, wind_direction_deg
│   ├── road_surface_temp_c, subsurface_temp_5cm_c, subsurface_temp_30cm_c
│   └── precipitation_mm
├── surface_condition: SurfaceCondition  (enum below)
├── confidence:        float 0..1   → DATEX II probabilityOfOccurrence
├── source:            str          (which plug-in produced it)
└── model_version:     str | None
```

### Surface condition codes (the AI model's scheme)

Target enum is **`WeatherRelatedRoadConditionTypeEnum`** (DATEX II Common namespace).
Values below are **verified** against `schemas/DATEXII_3_Profile/literals.csv`.

| Code | Canonical name | DATEX II enum (Bavaria profile) | Note |
|------|----------------|---------------------------------|------|
| 0 | DRY | `dry` | |
| 1 | DAMP | `moist` | |
| 2 | WET | `wet` | |
| 3 | HOARFROST | `glaze` | domain choice — kept distinct from code 5 |
| 4 | SNOW | `snowOnTheRoad` | |
| 5 | ICE | `ice` | |
| 255 | UNCLASSIFIABLE | `other` | enum has no `unknown` literal |

> ⚠️ The enum has **no** `iceOnRoad`, `snowOnRoad`, or `unknown` literals — earlier
> drafts used those and would have failed XSD validation. Corrected 2026-06 after
> verifying against the official data dictionary. See `docs/PANEL_QA.md` §2.

Horizons: **now**, **+3 h**, **+18 h** (the model's three forecast windows).

---

## 4. Data sources

Five sources, all normalized into the canonical model. SWS and DWD are the
authoritative Bavarian feeds; the others extend coverage.

| Source | Type | Stations | Rows | Cadence | Span | Role |
|--------|------|----------|------|---------|------|------|
| **SWS** | Road weather stations (Strassenwetterstation) | 13 (`P047`…) | 1.36 M | ~17 min | 2022‑11 → 2026‑05 | **Primary road observations** — same IDs the live Flask API serves; carries observed `road_condition_code`, road surface temp, water film. |
| **DWD** | Deutscher Wetterdienst climate (official) | 1 (`02261`, Hof) | 13.4 K | hourly | 2024‑11 → 2026‑05 | **Meteorological ground truth** — soil temps 5–100 cm, pressure, visibility, weather code. |
| **LoRaWAN** | IoT road sensor network | 137 | 3.05 M | sub‑hourly | 2025‑09 → 2026‑03 | Expansion network; surface temp measured directly. |
| **OpenWeatherMap** | Atmospheric API export | 26 cities | 1.22 M | hourly | 2024‑07 → 2026‑03 | Atmospheric augmentation / forecast. |
| **WDMS live API** | Existing Flask `:4000/get_data` | 516 | live | on request | live | Live‑integration story (optional for demo — SWS covers it offline). |

### Why SWS is the keystone
- Station **`P047`** is exactly what the existing system serves at
  `GET /get_data?STATID=P047`.
- The `P`‑prefixed IDs are the Bavarian network the **AI model was trained on**.
- SWS carries an **observed** `road_condition_code` — and the AI **predicts** the same
  kind of code. This enables a **predicted‑vs‑observed** comparison, both expressed in
  DATEX II (see §6).

> **Open item:** the SWS `road_condition_code` legend likely differs from the AI model's
> `0=Dry … 5=Ice` scheme. Needs cross‑referencing (enumerate distinct values from the CSV
> and map in the profile).

---

## 5. DATEX II output design

Road weather is *not* a single DATEX II publication — it maps onto several. The prototype
emits the publication that fits each kind of data, **aligned to the official DATEX II
[Road Weather Information Recommended Profile](https://docs.datex2.eu/recommended-profiles/rsp/roadweatherinformation/)**
(which uses exactly `SituationPublication` + `MeasuredDataPublication` +
`MeasurementSiteTablePublication`):

| Data kind | DATEX II publication | Notes |
|-----------|----------------------|-------|
| Station catalogue (where the sensors are) | `MeasurementSiteTablePublication` | One‑time / reference. |
| Raw sensor readings (temp, humidity, surface temp) | `MeasuredDataPublication` | The observations. Specializations: Humidity, PrecipitationInformation, TemperatureInformation, WindInformation, `RoadSurfaceConditionInformation`. |
| Hazard state (weather-related road condition) | `SituationPublication` → `WeatherRelatedRoadConditions` → `RoadSurfaceConditionMeasurements` | What downstream consumers act on. |
| AI forecasts (surface condition + confidence) | `ElaboratedDataPublication` | The "money shot" — model outputs as standard data. **Note:** the official Road Weather profile models *measured* data only and has no native forecast/confidence representation, so carrying the AI forecast + uncertainty is a deliberate **extension** of the profile (a genuine contribution — see `docs/PANEL_QA.md` §2). |

Generated DATEX II v3.4 Python dataclasses live in `generated/datex2/` (**914 classes**,
produced by `xsdata` from the official XSDs — gitignored, regenerate with
`scripts/generate_dataclasses.py`).

---

## 6. Validation strategy (how we prove conformance)

Five layers, cheapest/strongest first. This is what makes G1 + G5 defensible.

1. **XSD schema validation (automatic, primary).** Every output is validated in code with
   `xmlschema` against the official v3.4 XSDs before it leaves the service. Becomes the
   `X-Validation-Status` response header and a hard gate in tests.
2. **Official DATEX II online validator (independent).** Paste a generated instance into
   webtool.datex2.eu's validator → screenshot "valid" as external evidence for the thesis.
3. **Conformance matrix test.** Validate *every* output the adapter can emit — all 7
   condition codes × 3 horizons × edge cases (missing fields, low confidence, negative
   temps). Defensible claim: "every possible output is conformant."
4. **Semantic round‑trip.** Re‑parse the XML and assert values survived (DB says −1.5 °C
   and ICE → XML still says −1.5 °C and `iceOnRoad`). Catches mapping bugs the XSD can't.
5. **Predicted‑vs‑observed agreement.** For a station/time, emit the AI forecast
   (`ElaboratedDataPublication`) *and* the SWS observation (`MeasuredDataPublication`),
   both XSD‑valid, and show they agree. Strong, concrete thesis result.

---

## 7. Demo experience (for non‑technical audiences) — G4

A single page at `GET /demo`. The persuasive weight is in showing, not telling.

```
 Top: scenario picker  [icy night] [snow event] [dry day] [drop your own file]
 ┌──────────────────┬─────────────────────┬────────────────────────┐
 │ 📥 YOUR DATA     │ 📤 DATEX II v3.4    │ 🗣 PLAIN ENGLISH       │
 │ (raw CSV/JSON)   │  ✅ VALID           │  "Station P047 reports │
 │ temp: -1.5 ──────┼─► <airTemperature>  │   ICE at 03:00 (87%).  │
 │ surface: ICE ────┼─►   iceOnRoad       │   Any European traffic │
 │ conf: 0.87       │                     │   centre can read this"│
 └──────────────────┴─────────────────────┴────────────────────────┘
 Bottom: 🛂 Data Passport — ✅ DATEX II v3.4 · 🇪🇺 CEN/TS 16157 · ⏱ 47 ms · 🔬 XSD-validated
```

- **Left panel** = the proof (your number → its place in the standard, with connector lines).
- **Middle panel** = syntax‑highlighted XML + green VALID badge.
- **Right panel** = what it *means* + why it matters (the "so what").
- **Data Passport badge** = credibility in one glance (non‑technical viewers read badges,
  not XML).
- **Drag‑and‑drop** = "*you* try it," not "watch me click."

The pitch line: *"Your sensor speaks Bavarian. DATEX II is the European common language.
This adapter is the translator."*

---

## 8. API surface

| Method | Path | Purpose | Status |
|--------|------|---------|--------|
| GET | `/` | Service info | ✅ |
| GET | `/health` | Liveness + demo DB / profile stats | ✅ |
| GET | `/sources` | List source plug-ins + health (auto-discovery) | ⬜ |
| GET | `/stations` | Station catalogue | ⬜ |
| POST | `/transform` | Raw payload → DATEX II (the core operation) | ⬜ |
| GET | `/publication` | Batch publication (N stations, XML/JSON) | ⬜ |
| GET | `/scenarios`, `/scenarios/{name}` | Frozen demo moments | ⬜ |
| GET | `/demo`, `/demo/compare` | Side‑by‑side HTML view | ⬜ |

Response middleware (planned): `X-Transform-Time-Ms`, `X-Validation-Status`,
`X-Source-Used`, `X-Profile` + colour‑coded logging.

---

## 9. Repository layout

```
datex2-adapter/
├── adapter/              # core
│   ├── models.py         # CanonicalObservation, SurfaceCondition, WeatherInputs  ✅
│   ├── profiles/         # MappingProfile loader (load_profile)                   ✅
│   ├── normalizer.py     # FieldNormalizer (in3h/in_3h fix)                       ⬜
│   ├── mapper.py         # canonical → DATEX II dataclasses                       ⬜
│   └── validator.py      # xmlschema XSD gate                                     ⬜
├── sources/              # input plug-ins
│   ├── base.py           # Source ABC                                             ✅
│   ├── sws_sqlite.py     #                                                        ⬜
│   ├── dwd_sqlite.py     #                                                        ⬜
│   ├── lorawan_sqlite.py #                                                        ⬜
│   ├── owm_sqlite.py     #                                                        ⬜
│   └── wdms_api.py       # live Flask                                             ⬜
├── outputs/              # output plug-ins (DATEX II XML, JSON)                   ⬜
├── api/main.py           # FastAPI app                                           ✅(partial)
├── profiles/bavaria.yaml # condition codes + field map                           ✅
├── data/
│   ├── stations.json     # demo station catalogue                                 ✅
│   └── demo.db           # pre-indexed SQLite (offline demo)                      ✅
├── schemas/DATEXII_3_Profile/  # official DATEX II v3.4 XSDs                       ✅
├── generated/datex2/     # 914 xsdata dataclasses (gitignored)                    ✅
├── scripts/
│   ├── build_demo_db.py        # CSV → SQLite indexer                             ✅
│   └── generate_dataclasses.py # XSD → dataclasses                                ✅
├── tests/                # smoke ✅ · conformance ⬜ · integration ⬜
├── docs/PROTOTYPE.md     # this file
├── Dockerfile · docker-compose.yml · pyproject.toml                              ✅
```

---

## 10. Tech stack

- **Python 3.12**, **FastAPI** + **uvicorn**, **Pydantic v2**.
- **xsdata** — XSD → dataclasses. **xmlschema** — XSD validation. **lxml** — XML.
- **SQLite** — pre‑indexed demo store (offline safety).
- **pytest** — test pyramid. **ruff** — lint/format.
- **Docker** — `docker compose up` one‑command run.

> Always invoke via the venv: `.venv/bin/python`, `.venv/bin/pytest`.

---

## 11. Build plan & status

### ✅ Done — Foundation (Steps 0–2)
- [x] Repo scaffold, FastAPI app, Docker, pyproject, smoke tests
- [x] Canonical model (`CanonicalObservation`, `SurfaceCondition`, `WeatherInputs`)
- [x] MappingProfile loader + `bavaria.yaml`
- [x] Source ABC
- [x] DATEX II v3.4 dataclasses generated (914 classes)
- [x] Demo SQLite pre-indexed (LoRaWAN 3.05 M + OWM 1.22 M rows)
- [x] `/health` green, 5 smoke tests pass

### ⬜ Remaining — Pipeline (Steps 3–14)

| Step | Deliverable |
|------|-------------|
| 2b | **Add SWS + DWD** to `build_demo_db.py` + profile; rebuild `demo.db` (~1.3 GB) |
| 3 | `FieldNormalizer` (handles `in3h`/`in_3h`, per-source field maps) |
| 4 | Source plug-ins: SWS, DWD, LoRaWAN, OWM (+ WDMS live, optional) |
| 5 | Source registry + `GET /sources` |
| 6 | 🔑 **First valid DATEX II XML** — one station, XSD‑validated |
| 7 | Full mapper (7 codes × 3 horizons, confidence → probabilityOfOccurrence) |
| 8 | Batch publication (N stations, XML + JSON) |
| 9 | Standard endpoints (`/transform`, `/publication`, `/stations`) |
| 10 | Demo endpoints (`/scenarios`, `/demo` side‑by‑side, `/demo/compare`) |
| 11 | Middleware (timing/validation/source/profile headers) + colour logging |
| 12 | Test pyramid (conformance matrix, round‑trip, integration) |
| 13 | Evaluation / benchmarks across stations |
| 14 | Packaging (README adoption guide, `docker compose up`) |

**Critical path:** 2b → 3 → 4 → **6**. Step 6 is the riskiest (first XSD‑valid XML) and
collapses most of the project's uncertainty once it lands.

### Rough effort (remaining)
~13 h optimistic · **~21 h likely** · up to ~32 h if XSD validation fights back.
Step 6 is the swing factor.

---

## 12. Key decisions & open items

**Decisions made**
- Hexagonal/sidecar architecture (don't modify the existing Flask/Vue system).
- Canonical model normalizes the `in3h` vs `in_3h` naming bug to `in_3h`.
- Demo safety via pre‑indexed SQLite — zero live network at demo time.
- SWS chosen as primary offline source (same IDs as the live system → no Flask needed).
- LoRaWAN surface temp is measured directly → road‑temp derivation model demoted to an
  OWM‑only fallback.
- `MeteorologicalInformationPublication` is **not** a top‑level profile → road weather is
  modelled via Measured / Elaborated / MeasurementSiteTable / Situation publications.
- **Publication choice aligned to the official Road Weather Information Recommended Profile**
  (verified 2026-06 against docs.datex2.eu) — de-risks the keystone Step 6.
- **Condition enum verified** against the official data dictionary: target is
  `WeatherRelatedRoadConditionTypeEnum`; the invalid `iceOnRoad`/`snowOnRoad`/`unknown`
  values were corrected to `glaze`/`snowOnTheRoad`/`ice`/`other`. A regression test now
  guards every profile value against `literals.csv`.

**Open items**
- [ ] Confirm hoarfrost (code 3) → `glaze` with the road-domain expert (alt: `icyPatches` /
      generic `ice`). Mapping-fidelity decision — justify in the thesis.
- [ ] SWS `road_condition_code` legend → map to DATEX II enum in the profile.
- [ ] Confirm DWD station `02261` ↔ which SWS/AI stations it should anchor.
- [ ] Decide default publication(s) for `/transform` (likely Measured + Elaborated).
- [ ] Decide how confidence is carried (forecast is an *extension* of the official profile).
