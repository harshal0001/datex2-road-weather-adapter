# DATEX II Adapter — Architecture & How It Works

> Companion to `docs/PROTOTYPE.md` (what & why), `docs/PANEL_QA.md` (defense), and
> `docs/SOFTWARE_SPECIFICATION_AND_DESIGN.md` (the formal spec & design record).
> This document focuses on **how the system is structured and how data flows through it**.
> Last updated: 2026-06-14.

> **Two tracks, one architecture.** The work now spans two complementary paths that share
> the same canonical pivot and DATEX II output layer:
>
> - **TRACK A — Segment-fusion (PRIMARY, built & demoable).** A config-driven multi-source
>   **fusion engine** reconciles four per-segment weather feeds into one provenance-tagged
>   record per road segment, recolours a live Leaflet dashboard, and emits per-segment
>   DATEX II XML. This is what runs end-to-end today and carries the research contribution.
> - **TRACK B — Station-transform (ORIGINAL, partial).** The per-station `/transform`
>   conformance pipeline (Source plug-ins → normalizer → mapper → XSD validator). The ports
>   contract (`sources/base.py`) exists, but the concrete sources, normalizer, mapper and
>   validator are **not yet built** — XSD validation (Step 6) is the pending keystone.
>
> Sections §1–§3 describe the shared architecture; §4 covers **Track A** (the working flow) and
> §4c the dashboard; §4b is the original **Track B** station flow (pending).

---

## 1. System context (the 10,000-ft view)

Where the adapter sits relative to the existing Bavaria system and the European ecosystem.
It is a **sidecar**: it reads the same upstream data the existing system uses, and publishes
the standardized result — *without modifying the existing Flask/Vue stack*.

In **Track A** the upstream inputs are four **aggregated, per-segment** feeds (each keyed by
`segment_id` + `event_timestamp`) plus a geometry file — see §4. The sidecar framing is
unchanged: the adapter only *reads* this data and *publishes* the standardized result.

```
   UPSTREAM DATA                  THIS PROTOTYPE                 DOWNSTREAM CONSUMERS
 ┌──────────────────────┐     ┌──────────────────────┐        ┌────────────────────────┐
 │ agg_swsdata    (SWS) │     │                      │        │ National Access Point  │
 │ agg_lorawan          │ ──► │   DATEX II ADAPTER    │  ───►  │ (DE: MDM / Mobilithek) │
 │ agg_dwddata    (DWD) │     │   (sidecar service)   │        │ Neighbouring countries │
 │ agg_openweather      │     │                      │        │ (AT ASFINAG, FR …)     │
 │ road_segments.parquet│     └──────────────────────┘        │ Navigation / traffic   │
 │ (geometry+elevation) │              │                       │ service providers      │
 │ WDMS Flask API (B)   │              │ (does NOT modify)     └────────────────────────┘
 └──────────────────────┘             │
   ┌──────────────────────────────────▼──────────────────────────┐
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
   │  ┌──────────────┐      ┌──────────────────────────┐                      │
   │  │ sws / lorawan │──┐   │  FUSION ENGINE  (Track A) │     ┌──────────────┐ │
   │  │ dwd / openw.  │  │   │  per-field source-priority│ ┌─► │ DATEX II XML  │ │
   │  │ (per-segment) │  ├─► │  resolver + PROVENANCE    │ │   │ (template;    │ │
   │  │               │  │   │  (uses fusion.yaml)       │ │   │  not yet      │ │
   │  │ SwsSqlite (B) │  │   └────────────┬─────────────┘ │   │  XSD-valid')  │ │
   │  │ WdmsApi(B,live)│─┘                │               │   └──────────────┘ │
   │  └──────────────┘      ┌─────────────▼────────────┐  │   ┌──────────────┐ │
   │        ▲               │  FieldNormalizer (B, ⬜) │  ├─► │ GeoJSON / map │ │
   │        │               └─────────────┬────────────┘  │   └──────────────┘ │
   │  reads agg CSV →                      ▼               │   ┌──────────────┐ │
   │  segments.db / demo.db   ┌────────────────────┐      ├─► │ JSON (debug)  │ │
   │                          │ Canonical record    │      │   └──────────────┘ │
   │                          │  (the contract)     │      │   ┌──────────────┐ │
   │                          └─────────┬───────────┘      └─► │ Plain English │ │
   │                                    ▼               (B)│   │      (B, ⬜)  │ │
   │                          ┌────────────────────┐       │   └──────────────┘ │
   │                          │   Mapper (B, ⬜)    │───────┘                    │
   │                          │ (canonical→DATEX II)│                            │
   │                          └─────────┬───────────┘                            │
   │   MappingProfile (YAML) ───────────┘  ▲                                     │
   │   condition_codes (+ field_map)       │ Validator (xmlschema vs XSD; B, ⬜) │
   │   fusion.yaml = source-priority cfg   └─────────────────────────────────────│
   │                                                                            │
   │   API LAYER (FastAPI): / · /health · /dashboard · /api/segments/* (A) ✅   │
   │     pending (B): /transform · /publication · /sources · /stations          │
   │                  /scenarios · /demo  + response middleware                  │
   └──────────────────────────────────────────────────────────────────────────┘
```

> **What is built:** the **Fusion engine**, the two YAML profiles, the output adapters
> (GeoJSON / folium map / per-segment DATEX II XML / JSON) and the API layer for Track A are
> implemented (✅). The Track-B normalizer, mapper, validator and concrete Source plug-ins are
> still to be written (⬜). The DATEX II XML is **template-based and structurally accurate**
> but **not yet XSD-validated** — validation is the keystone Step 6.

### The three extension points (this is the reusability story)

| Want to… | Do this | Touch the core? |
|----------|---------|-----------------|
| Add a new input system | Write one **Source** plug-in (`sources/*.py`) | ❌ No |
| Adapt to a new jurisdiction | Write one **MappingProfile** YAML (`profiles/*.yaml`) | ❌ No |
| Emit a new output format | Write one **Output** plug-in (`outputs/*.py`) | ❌ No |
| Re-rank which source wins per field | Edit the **fusion profile** YAML (`profiles/fusion.yaml`) | ❌ No |

Everything between the ports — the canonical record, fusion engine, mapper, validator — stays
the same regardless of which source, jurisdiction, output, or fusion ranking you plug in.

**Config artifacts.** Two kinds of YAML drive the core, with **no code changes**:
`profiles/fusion.yaml` (Track A: per-field source priority + per-source raw→canonical column
maps) and the condition **MappingProfiles** — `profiles/bavaria.yaml` (the original 6-class ID3
scheme) and `profiles/segment_conditions.yaml` (the current 5-class SWS/LightGBM scheme used by
Track A). Having two condition profiles in-tree is itself a demonstration of the config-driven
reuse claim: two schemes, zero code change.

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

> **Track A note.** The fusion engine emits the *same canonical field names*
> (`road_surface_temp_c`, `air_temp_c`, `surface_condition`, …) — but as a `FusionResult` that
> additionally tags **each field with the source that supplied it** (provenance). The condition
> code is then mapped to a DATEX II literal through the same `MappingProfile` mechanism. So the
> canonical pivot above is the shared contract; Track A enriches it with per-field provenance.

---

## 4. Track A — the segment-fusion data flow (the working path)

This is what runs end-to-end today. Four aggregated per-segment feeds are pre-indexed into a
tiny committed store, fused per field with provenance, then rendered to the map and to DATEX II.

```
  BUILD TIME (offline, scripts/build_segment_snapshots.py)        SERVE TIME (FastAPI)
  ┌──────────────────────────────────────────────┐
  │ agg_swsdata · agg_dwddata · agg_lorawan ·      │
  │ agg_openweather   (~5 GB, keyed segment_id+ts) │   DuckDB streams each big CSV,
  │ road_segments_with_elevation.parquet           │   window-fn "latest row per
  │   (1021 segments, WKB geom EPSG:25832)          │   segment"; shapely/pyproj
  └───────────────────────┬────────────────────────┘   reproject geom → WGS84
                          │  (1)                                    │
                          ▼                                         │
                ┌────────────────────────────────┐                 │
                │ data/segments.db  (4 MB, COMMIT) │ ◄───────────────┘
                │  segments        1021 rows       │
                │  segment_snapshot 3619 rows      │  (latest raw JSON per
                │  (sws1021 dwd1021 owm911 lora666)│   segment × source)
                └───────────────┬──────────────────┘
                                │  (2) adapter/segments.py reads + caches
                                ▼
                ┌────────────────────────────────────────────────┐
                │ FUSION ENGINE  (adapter/fusion.py)               │
                │  for each of 1021 segments:                      │  (3)
                │   for each canonical field:                      │
                │     walk priority_for(field) ∩ selected sources, │
                │     take first non-null  → value + [source]      │
                │  driven by profiles/fusion.yaml                  │
                └───────────────┬──────────────────────────────────┘
                                │  (4) map surface_condition code →
                                │      label / colour / DATEX value
                                │      (profiles/segment_conditions.yaml)
                                ▼
            ┌───────────────────────────────────────────────────────┐
            │ OUTPUTS                                                 │
            │  GeoJSON   /api/segments/geojson  → Leaflet dashboard   │  (5)
            │  folium    /api/segments/map      (fallback HTML)       │
            │  DATEX XML /api/segments/datex[/city] (template, ⬜XSD) │
            │  JSON      /api/segments/fused · /coverage · /priority  │
            └───────────────────────────────┬───────────────────────┘
                                            │  (6)
                                            ▼
                          INTERACTIVE LEAFLET DASHBOARD  /dashboard
                          (static/dashboard.html — see §4c)
```

**Step-by-step:**
1. **Index (build time)** — `scripts/build_segment_snapshots.py` uses **DuckDB** to stream the
   multi-GB aggregated CSVs and keep only the latest row per `(segment_id, source)` via a window
   function, and **shapely/pyproj** to load each segment's WKB geometry and reproject it from
   EPSG:25832 to WGS84. Result: `data/segments.db` — 1021 `segments` rows (geometry WKT +
   centroid lat/lon + road metadata) and 3619 `segment_snapshot` rows (raw JSON per segment ×
   source). Coverage: sws 1021, dwd 1021, openweather 911, lorawan 666.
2. **Load** — `adapter/segments.py` reads and caches the segments and the per-segment,
   per-source raw rows from `segments.db`.
3. **Fuse** — `adapter/fusion.py` resolves each canonical field by walking that field's source
   priority (intersected with the user's selected sources) and taking the first non-null value,
   recording **which source supplied it** (full provenance). Priorities come from
   `profiles/fusion.yaml` (`source_priority [sws, lorawan, dwd, openweather]` with per-field
   overrides; `source_fields` maps each source's raw columns to canonical fields).
4. **Classify** — the fused `surface_condition` code is mapped to an English/German label, a
   map colour, and a real `WeatherRelatedRoadConditionTypeEnum` literal via
   `profiles/segment_conditions.yaml`. Missing condition → code 255 → `other`/grey.
5. **Emit** — fused segments are served as GeoJSON (dashboard), a folium map (fallback),
   per-segment DATEX II XML, and JSON (fused records / coverage / priority).
6. **Visualize** — the Leaflet dashboard recolours instantly client-side from the GeoJSON.

> **DATEX II caveat (Track A).** `outputs/datex_segment.py` builds the XML from a string
> **template** with verified element names and an actual enum literal for the condition, and
> records per-field provenance as inline comments. It is structurally accurate but **not yet
> XSD-validated** — full validation against the generated bindings is the pending keystone
> (Step 6). The structure is built to match that target so validation is a small delta.

---

## 4b. Track B — the station-transform flow (original / pending)

> **Status: original design, partial.** The `Source` ABC (`sources/base.py`) defines the port,
> but the concrete Source plug-ins, `FieldNormalizer`, `Mapper`, and the `Validator` are **not
> yet built**, and the `/transform` family of endpoints + response middleware are pending. This
> is the per-station conformance pipeline; Track A is the path that runs today.

What is *intended* to happen when a request asks for station **P047** as DATEX II. Numbers in
the diagram correspond to the steps below.

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
    │                      │                  │◄──── VALID / errors ────────│  (⬜ Step 6)
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
7. **Validate** — the Validator would check the XML against the official XSD (hard gate).
   *This is the pending keystone — Step 6 — and is not yet built.*
8. **Annotate** — middleware attaches timing/validation/source/profile response headers.
9. **Respond** — conformant DATEX II XML (or JSON / plain-English on the demo endpoints).

---

## 4c. The interactive dashboard (`/dashboard`)

`static/dashboard.html` is a single-page **Leaflet** app (the earlier folium-iframe version is
retained only as the `/api/segments/map` fallback). It is the primary demo surface.

```
  ┌──────────────────────────── /dashboard ────────────────────────────┐
  │  SOURCE CHIPS  [✓ SWS] [✓ LoRaWAN] [✓ DWD] [✓ OpenWeather]          │
  │     multi-select toggle → refetch /geojson?sources=… → instant       │
  │     client-side recolour (NO page reload)                            │
  │  ┌──────────────────────────────┐  ┌─────────────────────────────┐  │
  │  │  Leaflet map: 1021 segments  │  │ SIDE PANEL (click a segment)│  │
  │  │  coloured by fused condition │  │  • fused field table:        │  │
  │  │  hover → tooltip             │  │     value + [source] prov.   │  │
  │  │                              │  │  • that segment's live       │  │
  │  └──────────────────────────────┘  │     DATEX II XML             │  │
  │  coverage stats · condition distribution · per-field priority table │  │
  └──────────────────────────────────────────────────────────────────────┘
```

**The "drop SWS → all grey" demonstration.** Only **SWS** carries the ground-truth
`road_condition_code` (the fusion profile lists `surface_condition: [sws]` with no fallback).
So toggling the SWS chip **off** drops the condition for every one of the 1021 segments — the
whole map turns **grey ("Unknown")**, while the other fused fields (air temp, humidity, …) keep
their values from the remaining sources. This single interaction makes the architecture's two
core claims *visible*: why SWS is the priority base, and why **per-field** fallback (not
per-record) is what keeps the rest of the map alive.

---

## 5. Which DATEX II publication is produced

Aligned to the official **Road Weather Information Recommended Profile**. The Mapper (Track B,
⬜) chooses the publication that fits the data kind. Track A's `outputs/datex_segment.py` today
emits the `SituationPublication` / `WeatherRelatedRoadConditions` branch (the hazard-state path
highlighted below) per fused segment — template-based and **not yet XSD-validated** (Step 6).

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
network.** Achieved by pre-indexing the raw source data into local stores, one per track.

```
  BUILD TIME (once, offline)                       DEMO TIME (no network)
  ┌────────────────────────────┐                  ┌──────────────────────────────┐
  │ agg per-segment CSVs ~5 GB  │  DuckDB stream   │ Track A reads segments.db     │
  │ + road_segments.parquet     │ ───────────────► │ (4 MB, COMMITTED) — fuse +    │
  │                            │  window + reproj  │  recolour, <ms in-memory      │
  └────────────────────────────┘                  └──────────────────────────────┘
  ┌────────────────────────────┐                  ┌──────────────────────────────┐
  │ raw station CSVs (B)        │  build_demo_db   │ Track B reads demo.db         │
  │ LoRaWAN + OWM observations  │ ───────────────► │ (908 MB, GITIGNORED), indexed │
  └────────────────────────────┘  parse, index    └──────────────────────────────┘
                                                            │
                                                  Everything downstream is
                                                  pure CPU — no I/O risk live.
```

- **`data/segments.db` (4 MB, COMMITTED)** — the Track A store, built by
  `scripts/build_segment_snapshots.py` via **DuckDB** (streaming the ~5 GB aggregated CSVs) +
  shapely/pyproj (geometry). Small enough to check into git, so the dashboard runs out of the
  box with no rebuild. Tables: `segments` (1021) and `segment_snapshot` (3619).
- **`data/demo.db` (908 MB, GITIGNORED)** — the Track B station-observation store (LoRaWAN +
  OpenWeather), indexed on `(station_id, timestamp)`, WAL mode. Rebuilt locally, not committed.
- `/health` reports both stores (`segments_db`, `demo_db`) plus `profiles_available`, so a
  pre-demo check is a single request.
- The WDMS live-API source (Track B) is **optional** — the offline stores carry the same IDs,
  so the demo never needs the Flask system running.

---

## 7. Component & directory map

```
datex2-adapter/
├── adapter/                  CORE DOMAIN (source/output-agnostic)
│   ├── models.py             CanonicalObservation, SurfaceCondition, WeatherInputs   ✅
│   ├── profiles/             MappingProfile loader (load_profile)                    ✅
│   ├── fusion.py             FUSION ENGINE: per-field source-priority + provenance   ✅ (A)
│   ├── segments.py           segments.db → fuse all 1021 segments → FusedSegment     ✅ (A)
│   ├── segment_map.py        folium map renderer (fallback)                          ✅ (A)
│   ├── normalizer.py         FieldNormalizer                                         ⬜ (B)
│   ├── mapper.py             canonical → DATEX II dataclasses                        ⬜ (B)
│   └── validator.py          xmlschema XSD gate (Step 6 keystone)                    ⬜ (B)
├── sources/                  INPUT PORTS (one class per system)
│   ├── base.py               Source ABC (health, iter_observations)                 ✅
│   └── {sws,dwd,lorawan,owm}_sqlite.py · wdms_api.py  (no concrete plug-ins yet)    ⬜ (B)
├── outputs/
│   └── datex_segment.py      per-segment DATEX II XML (template, not yet XSD-valid)  ✅ (A)
│   └── {xml,json,plain}.py   Track B output plug-ins                                ⬜ (B)
├── api/
│   ├── main.py               FastAPI app: / · /health · /dashboard                   ✅
│   └── segments_routes.py    /api/segments/{coverage,priority,fused,geojson,         ✅ (A)
│                              map,datex,datex/city}
├── profiles/fusion.yaml      CONFIG: per-field source priority (research artefact)    ✅ (A)
├── profiles/segment_conditions.yaml  5-class SWS/LightGBM condition scheme           ✅ (A)
├── profiles/bavaria.yaml     6-class ID3 condition scheme: condition_codes+field_map ✅
├── data/segments.db          Track A store: 1021 segments + 3619 snapshots (4 MB)    ✅ committed
├── data/{demo.db,stations.json}   Track B station substrate (908 MB, gitignored)     ✅
├── schemas/DATEXII_3_Profile/     official XSDs + data dictionary (literals.csv)     ✅
├── generated/datex2/         914 xsdata dataclasses (gitignored)                     ✅
├── static/dashboard.html     INTERACTIVE LEAFLET DASHBOARD (chips, recolour, panel)  ✅ (A)
├── static/demo.html          Track B frontend mockup                                ✅
└── scripts/                  build_segment_snapshots.py (A, DuckDB) ·                ✅
                              build_demo_db.py · generate_dataclasses.py
```

**Dependency rule (hexagonal):** `sources/` and `outputs/` depend on `adapter/` (the core).
The core depends on **nothing** outward — it knows only `CanonicalObservation` and the profile.
This is what keeps the plug-ins swappable.

---

## 8. Runtime / deployment view

```
  ┌─────────────────── Docker container (python:3.12-slim) ───────────────────┐
  │   uvicorn ──► FastAPI app (api.main:app)  ──► core + plug-ins              │
  │                     │                                                      │
  │   mounts:  ./data (segments.db + demo.db)  ./schemas (XSD)                 │
  │            ./profiles  ./generated  ./static                              │
  │   health:  GET /health  every 30s   ·   UI: /dashboard                     │
  └────────────────────────────────────────────────────────────────────────────┘
         exposes :8000          `docker compose up`  →  one-command demo
```

> **Stack.** Python 3.12 · FastAPI · Pydantic v2 · xsdata (914 dataclasses in
> `generated/datex2`) · xmlschema (planned for Step 6 validation) · DuckDB · shapely + pyproj ·
> folium + Leaflet · SQLite. 14 pytest tests pass (incl. a regression test asserting every
> condition mapping is a real `WeatherRelatedRoadConditionTypeEnum` literal).

- **Stateless** transform → horizontally scalable (run N replicas behind a load balancer).
- **Production evolution** (not in prototype scope): put a message broker (e.g. Kafka) in front
  for real-time fan-in at 500+ stations, and add a DATEX II **Exchange** delivery plug-in
  (one of the 3 operating modes) to publish to the NAP. Both *wrap* this architecture — the
  canonical model is exactly the on-the-wire schema they'd build on.

---

## 9. How the reusability claim plays out concretely

Adopting the adapter for a **new jurisdiction** (e.g. a different country's road network):

```
  1. Copy a condition profile → profiles/<region>.yaml
       • remap condition_codes  (their codes → WeatherRelatedRoadConditionTypeEnum literals)
  2. Write profiles/<region>_fusion.yaml      (Track A)
       • declare source_priority + per-field overrides + per-source column maps
     OR remap field_map in the condition profile  (Track B)
  3. If their data lives somewhere new → write one Source plug-in (≈ a SQL query or HTTP call)
  4. Select it: ?sources=… (Track A)  or  ?profile=<region> (Track B)
       → fused, standardized DATEX II out, with ZERO changes to the core.
```

> The in-tree pairing of `bavaria.yaml` (6-class) and `segment_conditions.yaml` (5-class) is a
> concrete instance of step 1: two condition schemes coexist with no code change.

The boundary of "config-only": **field names, units, condition codes, source priority** are
pure YAML.
**Location referencing** beyond coordinates (ALERT-C/OpenLR) and consumer-specific profile
choices may need code — the one honest caveat (see `docs/PANEL_QA.md` §5).

---

## 10. Cross-references

- **Formal specification & design record** → `docs/SOFTWARE_SPECIFICATION_AND_DESIGN.md`
- **What & why, build plan, status** → `docs/PROTOTYPE.md`
- **Defense Q&A, alternative architectures, limitations** → `docs/PANEL_QA.md`
- **Live interactive dashboard** → `/dashboard` (served from `static/dashboard.html`)
- **Track B frontend mockup** → `static/demo.html`
