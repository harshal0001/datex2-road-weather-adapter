# DATEX II Adapter — Task / Progress Plan

> Living tracker for the prototype. Tick items as they land. Companion to
> `docs/PROTOTYPE.md` (what & why), `docs/ARCHITECTURE.md` (how),
> `docs/PANEL_QA.md` (defense), `docs/SOFTWARE_SPECIFICATION_AND_DESIGN.md` (paper).
>
> **Last updated:** 2026-06-14

---

## At a glance

| Track | State |
|-------|-------|
| Foundation (repo, canonical model, schema, demo store) | ✅ Done |
| **Multi-source fusion + road-segment map dashboard** | ✅ Done (the research core, demoable) |
| **Conformance track (DATEX II XSD validation + mapper)** | ⬜ Pending — **next priority** |
| Standard API + source plug-ins | ⬜ Pending |
| Demo polish (scenarios, side-by-side, middleware) | ⬜ Partial |
| Quality / evaluation / packaging | ⬜ Pending |

**Keystone next step:** Step 6 — XSD-validate the DATEX II output. Everything in the
conformance track unblocks once it lands.

---

## ✅ Done

### Foundation (Steps 0–2)
- [x] Repo scaffold, FastAPI app, Docker, `pyproject.toml`
- [x] Canonical model — `CanonicalObservation`, `SurfaceCondition`, `WeatherInputs`
- [x] MappingProfile loader + `bavaria.yaml` (6-class)
- [x] `Source` ABC (`sources/base.py`)
- [x] DATEX II v3.4 dataclasses generated (914 classes, `generated/datex2/`)
- [x] Demo SQLite for station obs (`demo.db`, 908 MB — LoRaWAN + OWM)
- [x] Condition enum verified vs official data dictionary; regression test guards it
- [x] `/health` green

### Fusion + segment + dashboard track
- [x] Aggregated 4 sources (SWS/DWD/LoRaWAN/OWM) keyed by `segment_id`
- [x] `scripts/build_segment_snapshots.py` — DuckDB streams ~5 GB CSVs + parquet → `segments.db` (4 MB)
- [x] `segments.db` — 1,021 segments (geometry WGS84) + 3,619 latest-per-source snapshots
- [x] **Fusion engine** (`adapter/fusion.py`) — per-field source priority + provenance
- [x] `profiles/fusion.yaml` — per-field priority + per-source field maps (research artefact)
- [x] `profiles/segment_conditions.yaml` — 5-class SWS/LightGBM scheme (2nd profile = reuse proof)
- [x] Segment store + fusion-all (`adapter/segments.py`)
- [x] folium map renderer (`adapter/segment_map.py`)
- [x] Per-segment DATEX II XML (`outputs/datex_segment.py`) — template-based, verified enums
- [x] API: `/api/segments/{coverage,priority,fused,geojson,map,datex,datex/city}`
- [x] **Interactive Leaflet dashboard** (`/dashboard`) — source toggles, instant recolor, click→DATEX
- [x] 14 pytest tests pass
- [x] Docs: PROTOTYPE, ARCHITECTURE, PANEL_QA, SOFTWARE_SPECIFICATION_AND_DESIGN

---

## ⬜ Pending — by milestone

### Milestone A — Conformance 🔑 (highest value; critical path 6 → 7 → 8)
- [x] **Step 6 — XSD-validate DATEX II output.** ✅ `adapter/validator.py` (xmlschema vs the
      official D2Payload XSD); `outputs/datex_segment.py` builds a real `SituationPublication`
      from the generated dataclasses → re-rooted `<payload xsi:type="sit:SituationPublication">`;
      `/api/segments/datex` emits validated XML. **Keystone done.**
- [x] Emit `X-Validation-Status: valid` header — done on `/datex` and `/datex/city`.
- [x] Conformance matrix test — all 7 condition literals validate (`tests/test_datex.py`).
- [x] **Step 7 (core) — measurements in the record**: fused `road_surface_temp_c` +
      `water_film_mm` now emitted as `RoadSurfaceConditionMeasurements` (validated).
      Remaining: `confidence → probabilityOfOccurrence` + forecast via `ElaboratedDataPublication`
      (needs the model run — observed data uses `certain`).
- [x] **Step 8 — Batch publication** — `/api/segments/datex/city` emits a validated
      multi-segment `SituationPublication`. Remaining (optional): MeasurementSiteTable cross-ref.

### Milestone B — Standard API + sources
- [x] **Step 4 — Concrete `Source` plug-ins**: `SegmentSqliteSource` base + `sws`/`dwd`/
      `lorawan`/`openweather` (read segments.db, yield CanonicalObservations) + `wdms` live stub.
- [x] **Step 5 — Source registry + `GET /sources`**: auto-discovers Source subclasses; endpoint
      reports per-source health + coverage (sws/dwd 1021, owm 911, lorawan 666; wdms down/optional).
- [x] **Step 9 (core) — Standard endpoints**: `POST /api/transform` (generic raw → validated
      DATEX, with `X-Validation-Status`/`X-Source-Used`/`X-Profile` headers) + `GET /api/segments`
      catalogue + `GET /api/segments/datex/city` (publication). Remaining: a station-style alias if needed.
- [ ] **Step 3 — Unit harmonization** in the normalizer (precip mm/s vs mm vs mm/3h; cloud
      oktas vs %; `in3h`/`in_3h`).

### Milestone C — Demo polish
- [x] **Step 10 — `/demo` view wired live**: 3-panel (raw → validated DATEX II → plain English)
      driving `POST /api/transform`; scenario picker (icy night / snow / freezing / dry) via
      `GET /api/scenarios` + `/api/scenarios/{id}`; ✅ VALID badge + Data Passport.
- [x] **Step 11 — timing middleware**: every response carries `X-Transform-Time-Ms`
      (`/transform` also sets `X-Source-Used` / `X-Profile`).
- [x] **Winter map colors** — real historical "moments" (`scripts/build_moments.py`) from the
      24 Nov 2025 ice event (696 ice segments) + hard-freeze + wet-autumn; map has a moment
      selector (`GET /api/segments/moments`, `?moment=` on geojson/coverage/fused/datex).
- [ ] `/demo/compare` side-by-side (optional).

### Milestone D — Quality / evaluation / packaging
- [x] **Step 12 — Test pyramid**: XSD conformance matrix (7 condition values), **semantic
      round-trip** (re-parse → assert values survived), fusion/source/endpoint integration tests
      (32 tests total).
- [x] **Step 13 — Evaluation** (`scripts/evaluate.py`): transform latency (mean ~5.7 ms,
      p95 ~6.9 ms), XSD conformance (100% on sample), condition distribution + source provenance.
- [x] **Step 14 — Packaging**: README adoption guide; Dockerfile regenerates dataclasses
      (clean-clone build); `playwright` added to dev deps; compose no longer shadows `generated/`.
      Remaining: predicted-vs-observed agreement (needs the model).

### Milestone E — Frontend (later, per request)
- [ ] Optional MapLibre/React (or Vue) upgrade; layout refinements.

---

## Critical path & recommended order

```
  [✅ Foundation] ─► [✅ Fusion + dashboard]
                          │
                          ▼
   1. Step 6  XSD validation  🔑  ──►  2. Step 11 middleware (X-Validation-Status badge)
                          │
                          ▼
   3. Step 7 full mapper ─► Step 8 batch ─► Step 9 standard endpoints
                          │
                          ▼
   4. Step 10 demo polish (winter scenarios, side-by-side) 
                          │
                          ▼
   5. Steps 4/5 sources+registry ─► 12 tests ─► 13 eval ─► 14 packaging
```

**Rough remaining effort:** ~13 h optimistic · ~21 h likely · up to ~32 h if XSD
validation fights back. Step 6 is the swing factor.

---

### Still blocked on external input
- [ ] **Forecast path** (`confidence → probabilityOfOccurrence`, `ElaboratedDataPublication`,
      predicted-vs-observed) — needs the trained **LightGBM model files** (`road_condition_*.txt`),
      not present in the supplied data.
- [ ] **Step 3 unit harmonization** (precip mm/s vs mm vs mm/3h; cloud oktas vs %) — doable now.

## Open decisions (need a call)
- [ ] Hoarfrost (ID3 code 3) → `glaze` vs `icyPatches` vs generic `ice` (domain expert).
- [ ] Default publication(s) for `/transform` (likely Measured + Elaborated).
- [ ] How confidence is carried (forecast *extends* the official Road Weather profile).

---

## Progress log
- **2026-06** — Foundation complete (repo, canonical model, 914 dataclasses, demo.db, /health).
- **2026-06** — DATEX II enum verified vs official dictionary; profile values corrected; regression test added.
- **2026-06** — Multi-source fusion engine + `segments.db` (1,021 segments) built; interactive Leaflet dashboard shipped at `/dashboard`.
- **2026-06** — Docs synced: PROTOTYPE, ARCHITECTURE updated; research paper + this progress plan added.
- **2026-06-15** — **Step 6 keystone landed**: DATEX II output now XSD-validates against the
  official v3 schema (`adapter/validator.py`); real `SituationPublication` built from generated
  dataclasses; `/api/segments/datex` returns validated XML with `X-Validation-Status: valid`;
  dashboard shows a ✅ XSD-valid badge; 23 tests pass (incl. 7-value conformance matrix).
- **2026-06-15** — **Steps 7–9 (core)**: fused measurements (surface temp, water film) embedded
  in the DATEX record; generic `POST /api/transform` (any raw multi-source data → validated
  DATEX II) + `GET /api/segments` catalogue + validated city publication; 25 tests pass.
- **2026-06-20** — **Steps 10–11**: live `/demo` (raw → DATEX → plain English) + scenario
  endpoints; global `X-Transform-Time-Ms` middleware. **Steps 4–5**: concrete Source plug-ins
  (sws/dwd/lorawan/openweather/wdms) + auto-discovery registry + `GET /sources`. 31 tests pass.
- **2026-06-20** — **Steps 12–14**: semantic round-trip test + `scripts/evaluate.py`
  (latency / conformance / provenance numbers); README adoption guide; Dockerfile regenerates
  dataclasses for clean-clone builds; playwright dev dep. 32 tests pass. **All non-data/model
  steps complete.**
