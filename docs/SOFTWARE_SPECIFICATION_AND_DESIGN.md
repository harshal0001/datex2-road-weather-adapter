# Enhancing Cross-Border Interoperability of Road Weather Systems

### A Multi-Source DATEX II Adapter Prototype for AI-Based Road Surface Condition Forecasting

**Software Specification & Design Report**

*Hof University of Applied Sciences — Graduate School*
*Software Engineering for Industrial Applications*

---

## Table of Contents

- List of Abbreviations
- List of Tables
- List of Figures
1. Introduction
2. Project Context
3. Project and Task
   - 3.1 Technology Stack
     - 3.1.1 DATEX II v3.4
     - 3.1.2 Python and Adapter Tooling
     - 3.1.3 Real Weather Data Sources
     - 3.1.4 Geospatial, Tooling, Testing and Deployment
4. Software Specification
   - 4.1 User Stories
   - 4.2 Functional Requirements
   - 4.3 Non-Functional Requirements
   - 4.4 Use Cases
     - 4.4.1 Overview of Adapter Service Interactions
     - 4.4.2 Selecting Sources and Fusing a Segment
     - 4.4.3 Transforming and Retrieving a DATEX II Publication
     - 4.4.4 Validating XML against the XSD
5. Software Design
   - 5.1 Architectural Style: Ports and Adapters
   - 5.2 The Canonical Model
   - 5.3 The Multi-Source Fusion Engine
   - 5.4 Semantic Mapping to DATEX II
   - 5.5 The Road-Segment Data Store
   - 5.6 Runtime Architecture and API Surface
   - 5.7 The Interactive Dashboard
   - 5.8 Activity and Sequence Views
   - 5.9 Reusability and Configuration
6. Conclusion
7. Bibliography

---

## List of Abbreviations

| Abbreviation | Definition |
|---|---|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| ASFINAG | Autobahnen- und Schnellstraßen-Finanzierungs-Aktiengesellschaft (Austrian motorway operator) |
| CEN | Comité Européen de Normalisation (European Committee for Standardization) |
| CRS | Coordinate Reference System |
| CSV | Comma-Separated Values |
| DATEX II | Data Exchange standard for traffic and travel information (EN 16157 series) |
| DT | Decision Tree |
| DWD | Deutscher Wetterdienst (German Weather Service) |
| EU | European Union |
| F.R. | Functional Requirement |
| GeoJSON | Geographic JSON encoding (RFC 7946) |
| ITS | Intelligent Transport Systems |
| JSON | JavaScript Object Notation |
| LoRaWAN | Long Range Wide Area Network (IoT sensor protocol) |
| N.F.R. | Non-Functional Requirement |
| OWM | OpenWeatherMap |
| REST | Representational State Transfer |
| RSP | Recommended Service Profile (DATEX II) |
| RWS | Road Weather Station |
| ŘSD | Ředitelství silnic a dálnic (Czech Roads and Motorways Directorate) |
| SWS | Strassenwetterstation / road weather station feed (Bavarian road-side sensors) |
| TEN-T | Trans-European Transport Network |
| UML | Unified Modeling Language |
| UTM | Universal Transverse Mercator (projected CRS; EPSG:25832 = zone 32N) |
| WDMS | Winter Service Management System (Winterdienst-Management-System) |
| WGS84 | World Geodetic System 1984 (EPSG:4326) |
| WKB / WKT | Well-Known Binary / Well-Known Text (geometry encodings) |
| XML | Extensible Markup Language |
| XSD | XML Schema Definition |

## List of Tables

- Table 1. Technology stack of the prototype.
- Table 2. The four ingested data sources and their characteristics.
- Table 3. Per-field source coverage across the four feeds.
- Table 4. AI condition codes mapped to the DATEX II `WeatherRelatedRoadConditionTypeEnum`.
- Table 5. Functional requirements.
- Table 6. Non-functional requirements.
- Table 7. The per-field fusion priority configuration.

## List of Figures

- Figure 1. System context: the adapter as a non-invasive sidecar.
- Figure 2. Ports-and-adapters internal architecture.
- Figure 3. The canonical-model pivot (N×M vs. N+M integration).
- Figure 4. Use-case overview of adapter–actor interactions.
- Figure 5. Activity diagram: select sources → fuse → standardize → render.
- Figure 6. Sequence diagram: end-to-end transform of one road segment.

---

## 1. Introduction

Cross-border road travel within Europe routinely encounters information discontinuities at national
boundaries, despite a clear regulatory mandate from the EU ITS Directive 2010/40/EU and
Commission Delegated Regulation (EU) 2022/670 to provide standardised real-time traffic and
weather information across the Trans-European Transport Network (TEN-T). Bavaria, in collaboration
between Hof University of Applied Sciences and the Bavarian road authority, has developed an
AI-based road surface condition forecasting system that predicts surface conditions at current,
3-hour, 6-hour and 18-hour horizons with validation accuracy exceeding 85 %. However, both the
forecasts and the sensor feeds that drive them remain in proprietary, system-specific formats,
preventing direct consumption by neighbouring Austrian, Czech or Swiss authorities.

The concept paper produced in the previous semester argued that this gap between a state-of-the-art
AI forecasting capability and Europe-wide interoperability frameworks must be closed at the
*data-exchange layer* rather than the model layer. It identified **DATEX II v3.4 (EN 16157:2018)** as
the appropriate target standard: it is mandated by the EU ITS Directive, maintained by CEN Technical
Committee 278, and already adopted by most European road authorities for traffic and weather
publications. Adoption should be realised through a **non-invasive adapter service** that sits beside —
not inside — the existing forecasting pipeline, so that the trained models, the operational database
and the update cycle remain untouched.

This Software Specification and Design Report describes the prototype built during the current
semester. The realised system goes one step beyond the original concept. Rather than transforming a
single proprietary JSON feed, the prototype is a **generic, configuration-driven adapter** that ingests
*four heterogeneous real data sources* — the Bavarian road-weather stations (SWS), the German
Weather Service (DWD), a LoRaWAN road-sensor network, and OpenWeatherMap — and reconciles
them, **field by field**, through a documented **multi-source fusion engine** before standardising the
result into DATEX II. The fused, standardised conditions are published both as validated DATEX II
documents and as an interactive road-segment map. The central research contribution is therefore not
merely format translation but *interoperable data fusion*: producing one authoritative, standards-
compliant view of the road network from several incomplete, overlapping sensor feeds, with full
provenance for every value.

The forthcoming chapters present the project context, the technology stack, the functional and
non-functional requirements, the use cases captured during analysis, and the software design —
including the ports-and-adapters realisation, the canonical model, the fusion engine, the semantic
mapping to DATEX II, the runtime architecture, and the activity and sequence views for the principal
workflows. The report closes with a conclusion and a bibliography of the standards, regulations and
tooling consulted.

> *Versioning note.* The prototype targets DATEX II v3.4, the version current at project inception and
> named by Regulation (EU) 2022/670. The latest published revision is v3.6 (June 2025); the road
> weather data model is stable across v3.4–v3.6, and the adapter regenerates its bindings from
> whichever profiled XSD it is given, so the targeting is deliberate and forward-compatible.

## 2. Project Context

This work is carried out as part of the Applied Research in Computer Science module at Hof University
of Applied Sciences and builds directly on the AI-based road surface condition forecasting system
published in 2025 by Cisneros Saldana, Acharya, Fallah Tehrani, Lehmann and Markus. The published
system combines fixed Road Weather Stations deployed across Bavaria, thermal measurements from
mobile maintenance vehicles, and elevation data, processed by machine-learning models chosen for
interpretability — crucial for operational trust — and inference efficiency. The Bavarian network is
reported to comprise up to 516 stations.

The forecasting capability sits inside a broader operational stack: a Flask backend orchestrates the
predictor, a Redis cache exposes recent results, a REST API delivers the forecasts, and a Vue.js
frontend displays them to road-maintenance staff. The pipeline refreshes every 15 minutes and stores
classified surface conditions per station and horizon. The system is in a development and pilot phase,
focused on a regional subset of stations in and around the Hof district.

Three structural facts about this host system are decisive for the present work. **First**, the forecasting
algorithm is mature enough that improving accuracy further is no longer the limiting factor for
cross-border deployment. **Second**, the output surface and the underlying sensor feeds are
heterogeneous and system-specific, so any external integration today requires bespoke client code and
custom field mappings — and no single feed is complete. **Third**, the current scope explicitly excludes
any modification to the trained models, the database schema or the operational web interface, to keep
the pilot stable while standardisation work is in flight. These constraints together justify an
adapter-based approach in which standardisation and fusion are implemented as a separate, replaceable
component.

From a regulatory perspective, the project addresses Commission Delegated Regulation (EU) 2022/670,
which mandates DATEX II for road-weather information on the TEN-T network. Bavaria's freight
corridors to Prague (A93), Salzburg (A8) and Passau–Linz (A3) all fall under TEN-T, so a working
DATEX II adapter is a prerequisite both for cross-border coordination and for eligibility under the
Connecting Europe Facility funding programme. The prototype is therefore the technical demonstrator
for that compliance roadmap.

## 3. Project and Task

The deliverable for the current semester is a working software prototype of a **multi-source DATEX II
adapter** for the Bavarian road-weather domain. The adapter ingests aggregated observations from four
real sources, reconciles them per road segment through a configurable fusion engine, generates
schema-conformant DATEX II v3.4 output, validates it against the official XSD, and exposes the result
through a RESTful API and an interactive map dashboard.

The realised data foundation uses **real aggregated observations** spanning June–November 2025,
keyed by `segment_id` and timestamp, together with a road-network geometry file describing **1,021 road
segments** (Bavarian state and district roads around Hof) with per-segment elevation. Road geometry is
supplied as Well-Known Binary in the projected CRS EPSG:25832 and reprojected to WGS84 for web
mapping. For each segment, the prototype keeps the most recent observation per source — a compact,
fully offline demonstration substrate — and fuses these into a single canonical record.

The road surface condition vocabulary of the host system has two historical encodings, both supported
by the prototype through configuration: the earlier seven-value Decision-Tree scheme (dry, damp, wet,
hoarfrost, snow, ice, plus an unclassifiable code) and the **current five-class scheme** carried in the SWS
ground-truth `road_condition_code` (0 = dry/*trocken*, 1 = damp/*feucht*, 2 = wet/*nass*,
3 = ice/*Eisglätte*, 4 = snow/*Schneeglätte*). Each AI code is mapped to a verified literal of the DATEX II
`WeatherRelatedRoadConditionTypeEnum`.

Two design decisions deserve early emphasis because they shape every subsequent chapter. **First**, the
prototype is *non-invasive*: it reads exported/aggregated feeds rather than modifying any upstream
system, so deployment requires only adding a service container alongside the existing stack. **Second**,
*validation against the official DATEX II XSD* is treated as a design gate rather than an afterthought: the
semantic mapper is generated from the official schema, every enumeration value used is verified against
the DATEX II data dictionary, and the validation wrapper is positioned in the request path so that
non-conformant output cannot leave the service silently.

### 3.1 Technology Stack

The stack is shaped by three forces: the host Bavarian system is written in Python, the DATEX II
ecosystem has its strongest open tooling in the Java and Python communities, and the prototype must
run on a single developer laptop while remaining easy to containerise. The stack therefore stays inside
the Python ecosystem and treats the official DATEX II XSD as the binding contract.

#### 3.1.1 DATEX II v3.4

DATEX II is the CEN data-exchange specification for traffic and travel information, defined in the
EN 16157 series. The standard provides not only XML message formats but a complete exchange model:
publication and subscription patterns, exchange profiles, and a hierarchy of profiled XML Schema
Definitions that constrain a subset of the full model to a specific domain.

The **Recommended Service Profile for Road Weather Information** narrows the model to the elements
relevant to surface conditions, atmospheric measurements and forecast metadata. Verification against
the official profile establishes the publication constructs the prototype uses:

- `MeasurementSiteTablePublication` — the catalogue of measurement locations (road segments).
- `MeasuredDataPublication` — observed values (air temperature, humidity, dew point, wind,
  precipitation, road surface temperature) via specialisations such as `TemperatureInformation`,
  `Humidity`, `WindInformation`, `PrecipitationInformation` and `RoadSurfaceConditionInformation`.
- `SituationPublication` → `WeatherRelatedRoadConditions` → `RoadSurfaceConditionMeasurements`
  — the hazard state acted upon by downstream consumers.
- `ElaboratedDataPublication` — used by the prototype as a documented **extension** to carry AI
  forecasts and their confidence, since the official road-weather profile models measured data only.

The road-condition vocabulary is the enumeration `WeatherRelatedRoadConditionTypeEnum`. Its
literals were verified directly from the DATEX II data dictionary (`literals.csv`); the prototype maps to
real literals only, avoiding non-existent values that would fail validation (see Table 4).

#### 3.1.2 Python and Adapter Tooling

Python 3.12 is the implementation language. The adapter relies on three complementary libraries to
handle the DATEX II contract end-to-end:

- **xsdata** converts the profiled XSD into typed Python dataclasses with XML/JSON serialisation. The
  prototype generates **914 dataclasses** from the official schema, so the type system cannot drift from
  the standard — a schema change breaks compilation rather than producing silently invalid output.
- **xmlschema** (with **lxml**) is a pure-Python XSD validator with structured error reporting, used to
  enforce that generated XML conforms to the official schema and to surface diagnostics on failure.
- **FastAPI** with **Pydantic v2** provides the REST surface, automatic OpenAPI/Swagger UI from type
  hints, and content negotiation; **uvicorn** is the ASGI server.

#### 3.1.3 Real Weather Data Sources

The prototype is driven by **four real, aggregated data sources**, each exported as CSV keyed by
`segment_id` and `event_timestamp` over June–November 2025. Their complementary coverage is what
makes the fusion problem real and non-trivial.

**Table 2. The four ingested data sources.**

| Source | Nature | Distinguishing fields | Coverage (segments) |
|---|---|---|---|
| **SWS** | Bavarian road-side weather stations — the trusted ground truth | `road_condition_code`, road surface temp, water-film, subsurface temp | 1,021 |
| **DWD** | German Weather Service climate feed | soil temps (5–100 cm), pressure, visibility, cloud cover, precipitation type | 1,021 |
| **OpenWeather** | Atmospheric API export | pressure, visibility, cloud cover, rain | 911 |
| **LoRaWAN** | Newer IoT road-sensor network (sparse) | directly measured surface temperature | 666 |

A road-network geometry file (`road_segments_with_elevation`) supplies the **1,021 segment geometries**
and elevations. Surface condition ground truth exists **only** in SWS; atmospheric quantities such as
pressure, visibility and cloud cover exist only in DWD and OpenWeather; LoRaWAN and SWS are the
only feeds with directly measured road-surface temperature. No single source is complete — the
motivation for per-field fusion (Table 3).

**Table 3. Per-field source coverage (✓ = field present).**

| Canonical field | SWS | LoRaWAN | DWD | OpenWeather |
|---|:--:|:--:|:--:|:--:|
| road surface temperature | ✓ | ✓ | — | — |
| road condition (ground truth) | ✓ | — | — | — |
| water film | ✓ | — | — | — |
| air temperature / humidity / dew point | ✓ | ✓ | ✓ | ✓ (no dew) |
| subsurface / soil temperature | ✓ | — | ✓ | — |
| precipitation | ✓ | — | ✓ | ✓ |
| wind | ✓ | — | ✓ | ✓ |
| pressure / visibility / cloud cover | — | — | ✓ | ✓ |

#### 3.1.4 Geospatial, Tooling, Testing and Deployment

Because the prototype operates on road geometry, the stack adds a geospatial layer: **DuckDB** streams
the multi-gigabyte source CSVs and extracts the latest observation per segment per source with a single
windowed query; **pyarrow/pandas** read the geometry file; **shapely** and **pyproj** parse Well-Known
Binary and reproject EPSG:25832 → EPSG:4326; **folium**/**Leaflet** render the road segments as a web
map. The fused snapshot is materialised into a compact **SQLite** store (≈ 4 MB, 1,021 segments and
3,619 source snapshots), so the demonstration runs fully offline with sub-10 ms lookups.

The development tooling is intentionally lightweight: **pytest** with **httpx** drives unit and integration
tests; **ruff** lints and formats; **Git/GitHub** provide version control; **Docker** with **docker-compose**
packages the service for reproducible deployment.

**Table 1. Technology stack of the prototype.**

| Layer | Technology | Purpose |
|---|---|---|
| Language / Runtime | Python 3.12, uvicorn (ASGI) | Implementation; matches host system |
| Standardisation | DATEX II v3.4 profiled XSD (Road Weather Information) | Authoritative output contract |
| Code generation | xsdata (914 dataclasses) | Typed dataclasses + serializers from the XSD |
| Validation | xmlschema, lxml | Pure-Python XSD validation with diagnostics |
| API framework | FastAPI, Pydantic v2 | REST endpoints, content negotiation, Swagger UI |
| Fusion / config | PyYAML mapping & fusion profiles | Per-field source priority, condition mappings |
| Geospatial | DuckDB, pandas, pyarrow, shapely, pyproj | CSV streaming, geometry parsing, reprojection |
| Mapping / frontend | folium, Leaflet, vanilla JS | Interactive road-segment map dashboard |
| Demo store | SQLite | Offline, pre-indexed fused snapshots |
| Testing | pytest, httpx | Unit and integration tests |
| Packaging | Docker, docker-compose | Reproducible deployment |
| Source control | Git, GitHub | Version control and open-source release |

## 4. Software Specification

The specification records the user stories that motivate the prototype, the functional requirements that
translate them into testable behaviour, the non-functional requirements that constrain how those
behaviours are delivered, and the use cases that capture the principal interactions between the adapter
and its actors.

### 4.1 User Stories

1. *As a transportation-authority data consumer* (e.g. a developer at ASFINAG, ŘSD or ASTRA), I want
   to retrieve Bavaria's road surface conditions in DATEX II v3.4, so that I can ingest them into my
   existing DATEX II-aware platform without writing custom parsers for proprietary formats.
2. *As a traffic-operations analyst*, I want to select which sensor sources are trusted and see the road
   network coloured by the **fused** condition, so that I can understand the network at a glance and
   judge how coverage degrades when a source is unavailable.
3. *As an integration developer*, I want each road segment's fused values to carry **provenance** (which
   source supplied each field), so that I can audit and trust the standardised output.
4. *As an adapter maintainer*, I want every transformation validated against the official DATEX II XSD
   with structured diagnostics on failure, so that I can detect mapping regressions before they reach
   consumers.
5. *As an operations engineer at the host group*, I want the adapter to consume exported feeds rather
   than modify any upstream system, so that deployment requires no changes to models, database or
   frontend.
6. *As an evaluator in the thesis defence*, I want an interactive dashboard and Swagger UI with realistic
   Bavarian data, so that I can demonstrate the full pipeline live without command-line preparation.

### 4.2 Functional Requirements

**Table 5. Functional requirements.**

| F.R. No. | Requirement | Description |
|---|---|---|
| FR_1 | Multi-source ingestion | Ingest aggregated SWS, DWD, LoRaWAN and OpenWeather feeds keyed by `segment_id`/timestamp, plus the segment geometry, into an offline store. |
| FR_2 | Source selection | Accept a caller-chosen subset of the four sources (`?sources=`) and apply it consistently to fusion, mapping and rendering. |
| FR_3 | Per-field fusion | For each canonical field, select the value from the highest-priority *selected* source that carries it, per a configurable priority (`fusion.yaml`). |
| FR_4 | Provenance | Record, for every fused field, which source supplied it, and expose it via API and map tooltips. |
| FR_5 | Condition mapping | Map AI condition codes to verified `WeatherRelatedRoadConditionTypeEnum` literals via a configurable condition profile; support both the 5-class and 6-class schemes. |
| FR_6 | DATEX II output | Produce DATEX II v3.4 output per segment (`SituationPublication` / `WeatherRelatedRoadConditions` with the fused `RoadSurfaceConditionMeasurements`) and a city-coverage summary. |
| FR_7 | XSD validation | Validate generated XML against the official DATEX II v3.4 XSD; report diagnostics on failure. |
| FR_8 | GeoJSON + map | Expose fused segments as GeoJSON and render an interactive map coloured by condition, recolouring on source-selection change. |
| FR_9 | Coverage & distribution | Report per-source coverage and the condition distribution for the current selection. |
| FR_10 | Health & readiness | Provide `GET /health` reporting liveness and the readiness/row counts of the demo store. |
| FR_11 | Interactive documentation | Auto-generate OpenAPI/Swagger UI from the route definitions. |
| FR_12 | Forecast/confidence encoding (design) | Reserve `ElaboratedDataPublication` + `probabilityOfOccurrence` to carry AI forecasts and confidence as a documented profile extension. |

### 4.3 Non-Functional Requirements

**Table 6. Non-functional requirements.**

| N.F.R. No. | Classification | Description |
|---|---|---|
| NFR_1 | Performance | Per-segment fusion + mapping below 50 ms; full 1,021-segment GeoJSON assembly within a few hundred milliseconds. |
| NFR_2 | Standards compliance | Generated XML must use only verified DATEX II elements and enumeration literals; validation is a request-path gate, not a periodic audit. |
| NFR_3 | Demo safety / reliability | The demonstration must run fully offline from the pre-indexed store, with no live-network dependency for data (only map tiles require the network). |
| NFR_4 | Usability | A non-developer evaluator must be able to toggle sources, inspect a segment and view its DATEX II output without editing JSON or using the command line. |
| NFR_5 | Maintainability | New sources require a plug-in/config entry, not core changes; type hints and docstrings on public functions; regression tests guard enum validity. |
| NFR_6 | Portability | Runs on Linux, macOS and Windows via a single Docker image; no host-OS-specific runtime dependencies. |
| NFR_7 | Reusability | A new jurisdiction is onboarded by editing YAML (field maps, condition codes, fusion priority), without modifying the core. |
| NFR_8 | Observability | Structured request logging including transformation timing and validation status (design: `X-Transform-Time-Ms`, `X-Validation-Status`). |

### 4.4 Use Cases

#### 4.4.1 Overview of Adapter Service Interactions

**Actors:** Data Consumer (partner authority / navigation provider), Operations Analyst, Adapter
Maintainer. **Goal:** obtain a fused, standards-compliant view of the Bavarian road network. The Data
Consumer retrieves DATEX II documents or GeoJSON; the Operations Analyst uses the dashboard to
select sources and inspect segments; the Maintainer exercises validation during regression testing. All
interactions are served by the adapter from its offline fused store (Figure 4).

#### 4.4.2 Selecting Sources and Fusing a Segment

**Primary actor:** Operations Analyst. **Pre-condition:** demo store is loaded. **Main flow:** (1) the analyst
opens the dashboard; (2) the dashboard requests the fused GeoJSON for the default source set; (3) the
adapter fuses every segment per the priority configuration and returns coloured features with
provenance; (4) the analyst toggles a source off/on; (5) the adapter re-fuses and the map recolours.
**Alternative flow:** if SWS is deselected, segments with no ground-truth condition are returned as
*Unknown* and rendered grey, visibly demonstrating coverage dependence. **Post-condition:** the map
reflects the chosen source set.

#### 4.4.3 Transforming and Retrieving a DATEX II Publication

**Primary actor:** Data Consumer. **Pre-condition:** a segment (or the whole network) is selected. **Main
flow:** (1) the consumer requests the DATEX II representation of a segment for a source set; (2) the
adapter fuses the segment, maps the condition to the verified enumeration, and serialises a
`SituationPublication` carrying `WeatherRelatedRoadConditions` and the fused measurements; (3) the
document is returned with provenance recorded as comments. **Extension:** a city-coverage summary
aggregates the condition distribution across all segments. **Post-condition:** the consumer holds a
DATEX II document ingestible by any compliant platform.

#### 4.4.4 Validating XML against the XSD

**Primary actor:** Adapter Maintainer. **Main flow:** (1) the maintainer triggers a transformation; (2) the
adapter generates the XML; (3) the XML is validated against the official DATEX II v3.4 XSD; (4) on
success the document is returned and the validation status recorded; (5) on failure, structured
diagnostics (rule, location, message) are produced. **Regression guard:** an automated test asserts that
every condition code maps to a literal that genuinely exists in the DATEX II data dictionary, preventing
the reintroduction of invalid enumeration values.

## 5. Software Design

### 5.1 Architectural Style: Ports and Adapters

The system is built in the **ports-and-adapters (hexagonal)** style. Input feeds enter through *source
ports*; outputs leave through *output ports*; the core domain — the canonical model, the fusion engine,
the semantic mapper and the validator — depends on nothing outward. This is what makes both sides
pluggable: a new feed is a new source mapping; a new output is a new serialiser; the core is unchanged
(Figure 2).

```
   INPUT PORTS                 CORE DOMAIN                       OUTPUT PORTS
  SWS  ─┐                ┌───────────────────────┐            ┌─ DATEX II XML (+ XSD validate)
  DWD  ─┤  segment_id    │  Canonical model        │           ├─ GeoJSON  (→ Leaflet map)
  LoRa ─┼──────────────► │  Fusion engine (per-    │ ────────► ├─ JSON (coverage / fused)
  OWM  ─┘  + geometry    │   field priority + prov)│           └─ City-coverage summary
                         │  Semantic mapper        │
   fusion.yaml ─────────►│  XSD validator          │◄────── condition profiles (YAML)
                         └───────────────────────┘
```
*Figure 2. Ports-and-adapters internal architecture.*

### 5.2 The Canonical Model

All sources are normalised into a single `CanonicalObservation` carrying station/segment identity,
timestamp, horizon, coordinates, a `WeatherInputs` block (air/dew/road-surface/subsurface
temperatures, humidity, wind, precipitation), a surface-condition code, a confidence value and source
metadata. This canonical type is the pivot that turns an *N sources × M outputs* integration problem into
*N + M* mappings: each source maps inward once, each output maps outward once (Figure 3).

```
  point-to-point (N×M)            hub-and-spoke via canonical model (N+M)
  4 sources × 4 outputs = 16      4 in + 4 out = 8 mappings
```
*Figure 3. The canonical-model pivot.*

### 5.3 The Multi-Source Fusion Engine

The fusion engine is the central contribution. It is driven entirely by `fusion.yaml`, which declares a
global source priority and **per-field overrides** listing only the sources that actually carry each field, in
priority order (Table 7). At request time the engine intersects each field's priority list with the caller's
*selected* sources and takes the first available non-null value, recording the supplying source as
**provenance**. Fields with no available source (e.g. road condition when SWS is deselected) are returned
as null, which the downstream layers render honestly as *Unknown* rather than fabricating a value.

**Table 7. Excerpt of the per-field fusion priority (`fusion.yaml`).**

| Canonical field | Priority order |
|---|---|
| `surface_condition` | SWS |
| `road_surface_temp_c` | SWS → LoRaWAN |
| `subsurface_temp_5cm_c` | SWS → DWD |
| `air_temp_c` | SWS → LoRaWAN → DWD → OpenWeather |
| `pressure_hpa` / `visibility_m` / `cloud_cover_pct` | DWD → OpenWeather |

This design makes the trust model explicit and configurable: SWS is the trusted base for road-surface
state; DWD and OpenWeather supply atmospheric context; LoRaWAN is a fallback for surface
temperature. Re-prioritising sources, or onboarding a new jurisdiction with different sensors, is a
configuration edit, not a code change.

### 5.4 Semantic Mapping to DATEX II

The fused canonical record is mapped to DATEX II using the typed dataclasses generated from the
official XSD. The condition code is mapped to a verified `WeatherRelatedRoadConditionTypeEnum`
literal (Table 4); measured fields are placed into the corresponding `RoadSurfaceConditionMeasurements`
elements; provenance is recorded as inline comments. A `SituationPublication` carrying
`WeatherRelatedRoadConditions` is produced per segment, and a city-coverage summary aggregates the
network. The mapping is profile-driven: the condition profile (`segment_conditions.yaml` for the 5-class
scheme, `bavaria.yaml` for the 6-class scheme) supplies labels, colours and DATEX II literals.

**Table 4. AI condition codes → DATEX II literals (verified against the data dictionary).**

| AI code | Label (DE) | DATEX II `WeatherRelatedRoadConditionTypeEnum` |
|---|---|---|
| 0 | Trocken (dry) | `dry` |
| 1 | Feucht (damp) | `moist` |
| 2 | Nass (wet) | `wet` |
| 3 | Eisglätte (ice) | `ice` |
| 4 | Schneeglätte (snow) | `snowOnTheRoad` |
| (255) | Unbekannt (unknown) | `other` |

The enumeration has no `iceOnRoad`, `snowOnRoad` or `unknown` literals; an automated regression test
asserts that every mapped value exists in the DATEX II `literals.csv`, preventing invalid values that
would fail XSD validation.

### 5.5 The Road-Segment Data Store

A build script ingests the four multi-gigabyte source CSVs and the geometry file into a compact SQLite
store. DuckDB extracts the latest observation per `(segment_id, source)` via a windowed query, keeping
memory flat; shapely/pyproj parse the Well-Known Binary geometries and reproject EPSG:25832 →
WGS84, computing per-segment centroids. The result — 1,021 segments and 3,619 source snapshots in
≈ 4 MB — is the offline, demo-safe substrate that satisfies NFR_3.

### 5.6 Runtime Architecture and API Surface

A FastAPI application serves the API and the dashboard. The principal endpoints are: `GET /health`
(readiness); `GET /api/segments/geojson` (fused features for the map); `GET /api/segments/coverage`
(per-source coverage + condition distribution); `GET /api/segments/priority` (the fusion configuration);
`GET /api/segments/fused` (fused records with provenance); `GET /api/segments/datex` and
`/api/segments/datex/city` (DATEX II output); and `GET /dashboard` (the interactive UI). Every data
endpoint accepts a `?sources=` selection that flows consistently into fusion, mapping and rendering.

### 5.7 The Interactive Dashboard

The dashboard renders the 1,021 segments client-side with Leaflet from the GeoJSON endpoint.
Toggling a source recolours the map instantly without a full reload; hovering a segment shows its fused
values and provenance; clicking a segment opens its fused field table and its standardised DATEX II
document. Coverage counts, the condition distribution, and the per-field priority table update with the
selection — making the fusion logic, and its dependence on source availability, directly observable
(satisfying user stories 2 and 3, and NFR_4).

### 5.8 Activity and Sequence Views

```
[select sources] → [load fused GeoJSON] → for each segment:
     [gather per-source snapshots] → [fuse by per-field priority]
     → [map code → DATEX literal] → [colour + provenance]
   → [render map] → (on click) [serialise + validate DATEX II] → [show]
```
*Figure 5. Activity diagram: select → fuse → standardise → render.*

```
Client → API: GET /api/segments/datex?segment_id&sources
API → Store:  read per-source snapshots for the segment
API → Fusion: fuse(selected) → fused record + provenance
API → Mapper: canonical → DATEX II dataclasses (verified enum)
API → Validator: validate against official XSD
API → Client: DATEX II XML  (+ validation status)
```
*Figure 6. Sequence diagram: end-to-end transform of one segment.*

### 5.9 Reusability and Configuration

The reusability claim is concrete: onboarding a new jurisdiction means (1) copying a condition profile
and remapping its codes to DATEX II literals, (2) adding the new feed's columns to the fusion profile's
field map, and (3) setting its place in the per-field priority — all in YAML. The coexistence of two
condition schemes (5-class and 6-class) and four heterogeneous feeds in the current prototype
demonstrates this without any change to the core, the mapper or the validator.

## 6. Conclusion

The prototype demonstrates that the cross-border interoperability gap for Bavaria's road-weather data
can be closed at the data-exchange layer, non-invasively, and that doing so well requires more than
format translation. Because no single sensor feed is complete, the decisive step is **per-field, provenance-
tracked fusion** of several heterogeneous sources into one canonical view, which is then standardised
into DATEX II using types generated from — and enumeration values verified against — the official
schema. The realised system ingests four real feeds over 1,021 road segments, fuses them through a
configuration-driven priority model, maps conditions to verified DATEX II literals, and presents the
result both as DATEX II documents and as an interactive map on which the effect of trusting or
distrusting each source is immediately visible.

Two properties make the result defensible for a thesis and credible for deployment. First, *correctness is
designed in*: the mapper is generated from the official XSD, every enumeration value is verified against
the data dictionary, and a regression test guards against invalid literals. Second, *the architecture is
reusable by configuration*: new sources and new jurisdictions are onboarded through YAML, not code.

Work remaining for production maturity is well scoped: wiring the XSD validation gate into every
response and surfacing the `X-Validation-Status` header; completing the forecast/confidence encoding
through `ElaboratedDataPublication` and `probabilityOfOccurrence`; implementing the DATEX II
Exchange delivery profile (publisher push / client pull) for National Access Point integration; adding
linear/OpenLR location referencing for segment-level pinning; and unit-harmonising heterogeneous
precipitation and cloud-cover measures. None of these alters the architecture; each extends a defined
slot. The prototype therefore stands as a working technical demonstrator for the Regulation (EU)
2022/670 compliance roadmap and as a reusable pattern for multi-source road-weather interoperability.

## 7. Bibliography

1. Cisneros Saldana, J., Acharya, A., Fallah Tehrani, A., Lehmann, M., Markus, A. (2025).
   *AI-based System for Road Surface Condition Forecasting Using Multi-Source Meteorological Data.*
   International Symposium on Measurement and Control (ISM) 2025.
2. European Parliament and Council. *Directive 2010/40/EU on the framework for the deployment of
   Intelligent Transport Systems in the field of road transport (ITS Directive).*
3. European Commission. *Commission Delegated Regulation (EU) 2022/670 supplementing Directive
   2010/40/EU with regard to real-time traffic information services.*
4. CEN/TS 16157 (EN 16157 series). *Intelligent transport systems — DATEX II data exchange
   specifications for traffic management and information.*
5. DATEX II Organisation. *DATEX II v3 documentation, profiles and data dictionary* — datex2.eu,
   docs.datex2.eu (Road Weather Information Recommended Service Profile; Exchange specification).
6. xsdata — *Naming-aware XML/JSON data binding for Python* (code generation from XSD).
7. xmlschema — *Pure-Python XML Schema validation library.*
8. FastAPI / Pydantic v2 / uvicorn — *Python web framework, data validation and ASGI server.*
9. DuckDB, pandas, pyarrow, shapely, pyproj, folium/Leaflet — *Data and geospatial tooling.*

---

*This report documents the prototype in `datex2-road-weather-adapter`. Companion engineering
documents: `docs/PROTOTYPE.md` (build plan & status), `docs/ARCHITECTURE.md` (component view),
`docs/PANEL_QA.md` (defence preparation).*
