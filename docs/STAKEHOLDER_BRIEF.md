# Stakeholder Brief — DATEX II Road-Weather Adapter

A single explanation that works for both a Project Manager and a Data Architect,
with every abbreviation expanded in round brackets at the point of use.

---

## 0a. Personal introduction (say this first)

> "Good morning — I'm **Harshal Kothari**, a master's student at Hof University
> of Applied Sciences, in the **Applied Research in Computer Science** track.
> In this programme we carry out a research project every semester, and for
> this semester I chose to work on the **interoperability side of an existing
> project**: the university's AI (Artificial Intelligence)-based road-weather
> forecasting system, built together with the Bavarian road authority. That
> system works well — but its data only speaks an internal, proprietary format.
> My research project is about making that data **usable beyond our own
> systems**, by bringing it into the European standard for traffic and road
> information. What I'll show you today is the working prototype of that."

*(Then continue directly with the elevator pitch below — they chain naturally.)*

---

## 0. The 30-second elevator pitch (open the meeting with this)

> "Bavaria has excellent road-weather sensors and a strong AI (Artificial
> Intelligence) prediction system — but the data speaks a proprietary language
> only our own systems understand. This project built the translator: it takes
> four completely different sensor networks, merges them field by field with
> full traceability, and publishes the result in **DATEX II (Data Exchange II)**
> — the European standard that Austrian, Czech and Swiss traffic centres already
> consume, and that EU (European Union) regulation requires on our corridors by
> 2027. Everything you'll see today is real recorded data, running through the
> real pipeline, validated against the official standard on every single
> request."

---

## 0b. Pre-demo checklist (do this 15 minutes before)

1. **Start the server** (in WSL / Ubuntu terminal):
   ```bash
   cd /mnt/c/Users/ASUS/datex2-adapter
   .venv/bin/python -m uvicorn api.main:app --port 8000
   ```
2. **Wait until healthy:** open http://localhost:8000/health — should show
   `"status": "ok"` (first load can take ~30 s).
3. **Open the 4 tabs** from section 5 + `profiles/fusion.yaml` in an editor.
4. **Hard-refresh the dashboard** (Ctrl+Shift+R) so no stale copy is cached.
5. **Click through once:** select All sources → switch to Ice event → click a
   red segment → check the DATEX II panel shows ✅. Then reset to Latest with
   nothing selected (clean starting state for the demo).

**If something breaks mid-demo:**

| Symptom | Fix |
|---|---|
| Map is blank | No sources selected — click **All** (this is by design, not a bug) |
| Panel looks stale/odd | Ctrl+Shift+R (hard refresh) |
| Server not responding | Ctrl+C in the terminal, run the start command again, wait for /health |
| Port already in use | `pkill -f uvicorn` then start again |

---

## Abbreviation glossary

| Abbreviation | Full form | In one phrase |
|---|---|---|
| **DATEX II** | Data Exchange II | the European standard format for traffic & road data |
| **CEN** | European Committee for Standardization (Comité Européen de Normalisation) | Europe's official standards body |
| **EN 16157** | European Norm 16157 | the standard document series that defines DATEX II |
| **XML** | Extensible Markup Language | the structured text format DATEX II messages are written in |
| **XSD** | XML Schema Definition | the official "rulebook" file a DATEX II message is checked against |
| **EU** | European Union | — |
| **ITS** | Intelligent Transport Systems | the EU's digital-transport legislation area |
| **TEN-T** | Trans-European Transport Network | the EU's core road corridors (ours: Hof→Prague, →Salzburg, →Linz) |
| **CEF** | Connecting Europe Facility | the EU funding programme (2024–2027) tied to compliance |
| **SWS** | Straßenwetterstationen (road weather stations) | Bavaria's in-road sensors — measure the road surface itself |
| **DWD** | Deutscher Wetterdienst (German Weather Service) | the official national weather agency |
| **LoRaWAN** | Long Range Wide Area Network | low-power radio network for small IoT sensors |
| **IoT** | Internet of Things | small connected devices/sensors |
| **OWM** | OpenWeatherMap | a commercial weather-data service (city-level values) |
| **AI** | Artificial Intelligence | here: the road-condition prediction model |
| **JSON** | JavaScript Object Notation | the data format our raw sources and API use |
| **API** | Application Programming Interface | the machine-to-machine access point of our service |
| **REST** | Representational State Transfer | the standard web style our API follows |
| **YAML** | YAML Ain't Markup Language | a human-readable configuration file format |
| **MDM / Mobilithek** | Mobilitäts Daten Marktplatz (Mobility Data Marketplace) | Germany's national access point for traffic data |
| **ASFINAG** | Autobahnen- und Schnellstraßen-Finanzierungs-Aktiengesellschaft | the Austrian motorway operator |
| **ŘSD** | Ředitelství silnic a dálnic (Czech Roads and Motorways Directorate) | the Czech national road authority |

---

## 1. What is DATEX II?

**Say this:**

> "DATEX II (Data Exchange II) is the official **European standard for exchanging
> traffic and road information**. It is defined in the standard series EN 16157
> (European Norm 16157) and maintained by CEN (the European Committee for
> Standardization) — the same body behind other European engineering norms. Road
> authorities in over 30 European countries already use it to publish traffic and
> weather data.
>
> The simplest way to picture it: every region's sensors speak their own local
> dialect — different formats, different units, different field names. **DATEX II
> (Data Exchange II) is the agreed common language.** If Bavaria publishes road
> conditions in DATEX II, a traffic centre in Austria or Czechia can read them
> immediately, with no custom software — the same way a PDF opens on any computer.
>
> Technically, a DATEX II message is an XML (Extensible Markup Language) document —
> structured text — and what makes the standard strong is that it comes with an
> official XSD (XML Schema Definition). That's a machine-readable rulebook: any
> document either passes the check against that rulebook or it doesn't. So
> 'compliant' is never an opinion — it's a **verifiable yes or no**, and our system
> runs that check on every single output."

*(The last paragraph satisfies the Data Architect while the Project Manager still
follows — one sentence of "how", anchored to the "why it matters".)*

---

## 2. Why did we choose DATEX II for this project?

**Say this:**

> "Three reasons — and the first one means it wasn't really optional.
>
> **First, it's legally required.** The EU (European Union) ITS (Intelligent
> Transport Systems) Directive 2010/40/EU and its Delegated Regulation 2022/670
> mandate that road-weather information on the TEN-T (Trans-European Transport
> Network) — the EU's core corridors — must be provided in DATEX II (Data
> Exchange II), with 2027 as the target horizon. Bavaria's freight corridors from
> Hof toward Prague, Salzburg and Linz are all TEN-T. So a DATEX II capability is
> a **compliance prerequisite**, and it's also a condition for funding eligibility
> under the CEF (Connecting Europe Facility) programme running 2024–2027.
>
> **Second, the real gap was in data exchange, not in intelligence.** Bavaria —
> Hof University together with the road authority — already has a strong AI
> (Artificial Intelligence) road-condition system with validation accuracy above
> 85%. What stops a Czech or Austrian system from using it is not model quality —
> it's that the output sits in a proprietary JSON (JavaScript Object Notation)
> format that only the internal system understands. Making the model 2% better
> helps nobody across the border; **standardizing the output helps everybody**.
> So we solved the problem at the data-exchange layer.
>
> **Third, the consumers already speak it.** Germany's national access point —
> the MDM (Mobilitäts Daten Marktplatz / Mobility Data Marketplace, now called
> Mobilithek) — plus ASFINAG (Autobahnen- und Schnellstraßen-Finanzierungs-
> Aktiengesellschaft, the Austrian motorway operator) and ŘSD (Ředitelství silnic
> a dálnic, the Czech Roads and Motorways Directorate) all consume DATEX II today.
> Publishing in their language means one integration instead of a separate custom
> integration and maintenance contract per partner.
>
> And one design principle worth stating: we built this as a **non-invasive
> adapter** — a translator service that sits *beside* the existing systems, not
> inside them. Nothing in the existing sensors, databases or models had to change."

---

## 3. How is DATEX II beneficial — now and in the future?

**Say this:**

> "**What it gives us today:**
>
> - **One integration instead of many.** We publish once, in the standard — and
>   every DATEX II (Data Exchange II)-aware consumer can ingest it: the German
>   national access point, neighbouring authorities, navigation providers. No
>   custom parsers on their side, no bespoke maintenance on ours.
> - **It's exactly the high-value data category.** Road-surface condition — ice,
>   snow — is what consumers act on: winter-maintenance dispatch, hazard warnings,
>   variable speed limits. This is safety data, not statistics.
> - **Provable quality, not claimed quality.** Every output is validated against
>   the official XSD (XML Schema Definition) rulebook as a hard gate — in our
>   evaluation, **100% of outputs passed conformance**, at roughly **6 milliseconds
>   per transformation**. When we say 'standards-compliant', that's a measured
>   number.
> - **It's the compliance demonstrator** for the 2027 regulatory deadline and the
>   CEF (Connecting Europe Facility) funding case.
>
> **What it enables in the future:**
>
> - **Cross-border safety warnings** — a Czech traffic centre warning drivers
>   about ice *before* they cross into Bavaria, using our data directly.
> - **Reuse in any other region.** Adapting this system to a new jurisdiction
>   means editing **configuration files** — which local condition code maps to
>   which standard term, which source to trust for which measurement — **not
>   writing new software**. That's the core research contribution: a config-driven,
>   reusable adapter, not a one-off converter.
> - **It's ready to carry predictions, not just measurements.** The standard has
>   constructs for forecast data with validity times, and we've already mapped our
>   prediction confidence onto the standard's probability vocabulary. When the
>   time-ahead forecast — plus-3-hour, plus-18-hour — is added later, the
>   publishing layer is already in place.
> - **Longevity.** A European Norm evolves slowly and carefully — the road-weather
>   part of the standard is stable across versions 3.4 to 3.6, and our system
>   regenerates its internals automatically from whichever official schema version
>   is current."

---

## 4. The prototype structure — the one explanation for both

**Show this picture (or draw it):**

```
   4 REAL DATA SOURCES                  OUR ADAPTER                        OUTPUT
┌───────────────────────┐   ┌───────────────────────────────┐   ┌───────────────────────┐
│ SWS — 13 in-road      │   │ 1  TRANSLATE  every source    │   │  DATEX II XML         │
│       stations        │   │    into one common field      │   │  ✓ validated against  │
│ LoRaWAN — 137 IoT     │ → │    vocabulary                 │ → │    the official XSD   │
│       road sensors    │   │ 2  FUSE  per field, by a      │   │  + interactive map    │
│ DWD — national        │   │    configurable trust order   │   │  + plain-English view │
│       weather station │   │ 3  STANDARDIZE  into DATEX II │   │  + REST API           │
│ OWM — 24 city feeds   │   │ 4  VALIDATE  — hard gate      │   └───────────────────────┘
└───────────────────────┘   └───────────────────────────────┘
  different formats, units,     every value keeps: source,
  clocks, and coverage          timestamp, agreement info
```

**Say this:**

> "The prototype has four stages, and the demo shows all of them live.
>
> **Stage 1 — Translate.** Four real sensor networks feed the system: SWS
> (Straßenwetterstationen — road weather stations), Bavaria's 13 in-road stations,
> the only source that measures the road surface itself; a LoRaWAN (Long Range
> Wide Area Network) of 137 small IoT (Internet of Things) road sensors; the DWD
> (Deutscher Wetterdienst — the German national weather service); and
> OpenWeatherMap, a commercial city-level feed. Each arrives in its own format,
> own units, own clock. First, everything is mapped into one common field
> vocabulary — including unit fixes; one source reported temperature in Kelvin,
> and our cross-checking caught it.
>
> **Stage 2 — Fuse.** For every measurement, a **configurable trust order**
> decides which source wins — per field, not globally. Road-surface temperature
> trusts the in-road sensor first; air pressure trusts the weather service. You
> see this live in the dashboard's priority table — and the crucial part:
> **every value remembers where it came from and when**. That's full provenance.
>
> **Stage 3 — Standardize.** The fused result is mapped into DATEX II (Data
> Exchange II) vocabulary — our local condition code 3 becomes the standard's
> term for ice — using a mapping table in a YAML (YAML Ain't Markup Language)
> configuration file. New region? New table. No new code.
>
> **Stage 4 — Validate.** Before anything leaves the system, it's checked against
> the official XSD (XML Schema Definition). Not sample-tested — every document,
> every time.
>
> On top sits a REST (Representational State Transfer) API (Application
> Programming Interface) — a standard web interface other systems call — and the
> dashboard you'll see, which is just a window onto that same API. And one number
> to remember: the whole pipeline — fuse, standardize, validate — runs in about
> **6 milliseconds** per road segment, across **1,021 segments** of the Hof
> network."

---

## 5. Demo script — open EXACTLY these things, nothing else

### Before the meeting: open these 4 browser tabs (in this order)

| Tab | URL | Used for |
|---|---|---|
| **Tab 1** | http://localhost:8000/dashboard | Part A — everyone |
| **Tab 2** | http://localhost:8000/demo | Part A closing — everyone |
| **Tab 3** | http://localhost:8000/docs | Part B — Data Architect |
| **Tab 4** | http://localhost:8000/api/segments/datex?segment_id=16117045&sources=sws,lorawan,dwd,openweather | Part B — Data Architect (the raw validated XML) |

Also open **one editor window** with a single file: `profiles/fusion.yaml`.
That's everything. Do not open anything else.

### Part A — for everyone (Tab 1, ~8 min)

1. **Tab 1, Moment = Latest.** Say: "one instant of the road network" — point
   at the **🕐 data as of** badge. Click source chips one by one (SWS →
   LoRaWAN → DWD → OpenWeather) — map fills in as sources join.
2. Scroll to the **Per-field source priority** table — "the trust policy:
   ★ = who is supplying each value right now." Toggle SWS off → the ★ hops to
   the next source. Toggle it back on.
3. **Moment → Ice event (24 Nov 03:00)** — map turns red (643 icy segments).
   "A real recorded night, replayed through the same pipeline."
4. **Click one red segment** — show: values with `[source]`, the competing
   values underneath ("also …"), the reading timestamps, "Sources agree: n/m
   fields." Click **📡 Ground sensors** → nearest physical station appears.
5. **DATEX II panel** (bottom right): XML view → ✅ validated badge → switch to
   **Plain English**. Say: "this exact document is what an Austrian or Czech
   system would ingest."
6. **Tab 2 (/demo)**, pick the *black ice* scenario: raw → standard → meaning
   in one screen. Close Part A on the numbers: **1,021 segments · ~6 ms ·
   100% XSD (XML Schema Definition) conformance**.

### Part B — for the Data Architect ONLY (Tabs 3–4 + the YAML, ~7 min)

Show exactly these four artifacts, in this order:

1. **The config file** (editor window, `profiles/fusion.yaml`) — scroll through
   `field_priority`, `unit_conversions` (point at the OpenWeather Kelvin
   offset −273.15), `agreement_tolerance`.
   Say: *"behaviour is versioned configuration, not code."*
2. **Tab 4 — the raw DATEX II XML** for segment 16117045. Point at the enum
   value (e.g. `ice`), the `PointByCoordinates` location, the timestamps.
   Say: *"straight off the API, validated against the official XSD on this
   very request."*
3. **Tab 3 — Swagger UI → `POST /api/transform`** → "Try it out" → Execute
   (the pre-filled example works). Show the response: validated XML +
   response headers `X-Validation-Status: valid` and `X-Transform-Time-Ms`.
   Then change `road_condition_code` from `3.0` to `2.0` → Execute again →
   the condition enum in the XML changes. Say: *"a generic contract — raw
   rows from any source in, standard out."*
4. **Tab 3 — `GET /api/segments/fused/{segment_id}`** → Try it out with
   `segment_id = 16117045`, `sources = sws,lorawan,dwd,openweather` → show the
   JSON: `values`, `provenance`, `agreement`, `times`, `confidence`.
   Say: *"full per-field lineage survives standardization — every value knows
   its source and its timestamp."*

If (and only if) asked about scale: describe the build/request split verbally —
7 GB of raw CSVs processed offline into small committed artifacts; the request
path only reads those (that's the ~6 ms). No extra tab needed.

## 5b. Upcoming feature — future predictions (roadmap slide)

**Say this:**

> "One more thing this dashboard is prepared for: **future predictions**. Today
> everything you've seen is observed or fused *current* data. The next step —
> which our colleague **Sonali is already working on** — is **time-ahead
> forecasting**: predicting the road-surface condition at plus-3-hour and
> plus-18-hour horizons, using AI (Artificial Intelligence) models driven by
> DWD (Deutscher Wetterdienst — German Weather Service) numerical weather
> forecasts.
>
> The important point for this project: **the publishing side is already
> built.** DATEX II (Data Exchange II) has native constructs for forecast data —
> a validity time saying *'this condition applies at 15:00'*, and a probability
> vocabulary (`probable` / `riskOf`) that we have already mapped our model
> confidence onto. Our prototype even contains a working prediction pipeline —
> a trained model that infers the road condition from the surrounding weather
> where no in-road sensor exists, published as validated DATEX II — which we've
> kept out of today's demo to keep it focused. So when Sonali's forecasting
> models are ready, they plug into this dashboard and this standard output —
> the horizon selector on the map, the forecast document per segment — **without
> re-architecting anything**."

*(If asked what exactly exists today: a nowcasting model — HistGradientBoosting,
86% held-out accuracy, ice F1 0.97 — served at `/api/segments/forecast/{id}`,
publishing XSD (XML Schema Definition)-validated DATEX II with
`probabilityOfOccurrence`. What's missing for true time-ahead forecasts is
future-horizon labels and forecast-weather inputs — which is the work in
progress.)*

---

## 6. Numbers to have ready

- Sources: SWS (Straßenwetterstationen) 13 stations (ground-truth road condition)
  · LoRaWAN (Long Range Wide Area Network) 137 devices · DWD (Deutscher
  Wetterdienst) station 02261 · OpenWeatherMap 24 cities
- Multi-source overlap window: Sep 2025 → early 2026; demo snapshots Oct–Dec 2025
- The Kelvin anecdote: *the cross-source agreement check caught one source
  silently reporting temperature in Kelvin — that's why multi-source validation
  matters.*

---

## 7. The API (Application Programming Interface) surface — 22 endpoints

One-liner if asked: *"one generic transform endpoint that IS the adapter, plus
read endpoints exposing every intermediate stage — raw sensors, fused values
with provenance, and the validated standard document — so the whole pipeline is
inspectable over REST (Representational State Transfer)."*

**App & health (5)**

| Endpoint | What it does |
|---|---|
| `GET /` | Landing route — points to dashboard, demo, docs |
| `GET /health` | Liveness: app up, data stores readable, profiles loaded |
| `GET /sources` | Auto-discovered source plug-ins + per-source health/coverage |
| `GET /dashboard` | Serves the main dashboard page |
| `GET /demo` | Serves the non-technical raw → DATEX II → plain-English page |

**The generic adapter contract (3) — the research core**

| Endpoint | What it does |
|---|---|
| `POST /api/transform` | **The core operation.** Raw per-source JSON (JavaScript Object Notation) rows in → per-field fusion → XSD (XML Schema Definition)-validated DATEX II XML out, with `X-Validation-Status`, `X-Transform-Time-Ms`, `X-Source-Used` headers |
| `GET /api/scenarios` | Lists predefined demo scenarios (icy night, snow, freezing, dry) |
| `GET /api/scenarios/{id}` | One scenario's raw per-source rows, ready to POST to `/transform` |

**Road-segment data & fusion (9)**

| Endpoint | What it does |
|---|---|
| `GET /api/segments` | Catalogue of the 1,021 segments (name, class, length, elevation, centroid) |
| `GET /api/segments/geojson` | **Drives the map** — all segments fused for the chosen `sources=` + `moment=`, with condition, colour, values, provenance, agreement, timestamps |
| `GET /api/segments/coverage` | Per-source coverage counts + condition distribution |
| `GET /api/segments/priority` | The per-field source priority (from `fusion.yaml`) |
| `GET /api/segments/fused` | Fused records for many segments (JSON, with provenance) |
| `GET /api/segments/fused/{id}` | One segment in full detail — powers the selected-segment panel & Compare |
| `GET /api/segments/moments` | Moment dropdown entries + each moment's reference timestamp (the "data as of" badge) |
| `GET /api/segments/timeline` | The 31 hourly steps (feeds the time slider; UI currently disabled) |
| `GET /api/segments/map` | Legacy server-rendered map (fallback; dashboard uses `/geojson`) |

**DATEX II output (2)**

| Endpoint | What it does |
|---|---|
| `GET /api/segments/datex?segment_id=…` | Validated DATEX II XML for one segment (the DATEX panel + download) |
| `GET /api/segments/datex/city` | One validated multi-segment publication for the whole network |

**Sensors & prediction (3)**

| Endpoint | What it does |
|---|---|
| `GET /api/segments/sensors?moment=…` | Real physical sensor network (177 stations), **moment-aware** readings + timestamps |
| `GET /api/segments/stations` | Legacy 8-station LoRaWAN subset (superseded by `/sensors`) |
| `GET /api/segments/forecast/{id}` | Prediction path: condition inferred from non-SWS sources vs observed SWS, + validated forecast DATEX II (UI card hidden; endpoint live) |

Auto-generated by FastAPI: `GET /docs` (Swagger UI — use this live), `GET /redoc`,
`GET /openapi.json`.

---

## 8. What to show the Data Architect — exactly 5 things

Don't tour everything; show the five artifacts an architect actually judges:

1. **The config files** (`profiles/fusion.yaml` + `segment_conditions.yaml`) —
   per-field priorities, unit conversions, tolerances, code→enum mapping.
   *Message: behaviour is versioned configuration, not code.*
2. **One fused segment with provenance** (click a segment / `GET /fused/{id}`) —
   values, winning source per field, competing candidates, agreement,
   timestamps. *Message: lineage survives standardization.*
3. **`POST /api/transform` in Swagger** — raw rows in, validated XML out,
   response headers; optionally break a value to show the structured 422 error.
   *Message: the adapter is a real, generic, testable contract.*
4. **The validated DATEX II document** (XML toggle + ✅ badge) and where the
   XSD (XML Schema Definition) gate lives. *Message: conformance is enforced,
   not sampled.*
5. **The build/request split** (one slide or the PROJECT_STRUCTURE diagram):
   7 GB raw CSVs processed offline by DuckDB scripts → small committed
   artifacts → millisecond request path. *Message: it scales sensibly.*

Everything else (tests, model, docs) you mention verbally and offer on request.

---

## 9. URL cheat-sheet (all verified working — paste into the browser)

**Pages (5 real web pages):**

| URL | What opens |
|---|---|
| http://localhost:8000/dashboard | **The main demo** — fusion map, sources, moments, DATEX II panel |
| http://localhost:8000/demo | Non-technical view: raw → validated DATEX II → plain English |
| http://localhost:8000/docs | Swagger UI (interactive API) — **the Data Architect page** |
| http://localhost:8000/redoc | Same API reference, read-only layout |
| http://localhost:8000/api/segments/map?sources=sws,lorawan,dwd,openweather | Legacy server-rendered map (fallback — only if asked) |

**Data URLs worth pasting live for the Data Architect** (JSON/XML straight in the browser):

| URL | What it proves |
|---|---|
| http://localhost:8000/health | Service + data stores status in one call |
| http://localhost:8000/sources | Source plug-ins auto-discovered, with coverage |
| http://localhost:8000/api/segments/priority | The trust policy (per-field priority) served from config |
| http://localhost:8000/api/segments/fused/16117045?sources=sws,lorawan,dwd,openweather | One fused segment: values + provenance + agreement + timestamps |
| http://localhost:8000/api/segments/datex?segment_id=16117045&sources=sws,lorawan,dwd,openweather | The validated DATEX II XML document itself |
| http://localhost:8000/api/segments/sensors?moment=ice-event-night | Moment-aware sensor readings (177 stations, aligned timestamps) |
| http://localhost:8000/openapi.json | The machine-readable API contract (OpenAPI 3) |

Tip: keep `/dashboard`, `/demo` and `/docs` open in three browser tabs before the
meeting starts; the table above is for live drill-downs when the architect asks.

---

## 10. Data Architect question ladder — from simple to very complex

### Tier 1 — Warm-up (fact questions)

- **"Which DATEX II version do you target?"** → v3.4 (mandated by Regulation
  (EU) 2022/670); the road-weather model is stable through v3.6; bindings
  regenerate from whichever XSD (XML Schema Definition) version we point at.
- **"How many data sources, and what are they?"** → Four real ones: SWS
  (Straßenwetterstationen, 13 in-road stations), LoRaWAN (Long Range Wide Area
  Network, 137 IoT sensors), DWD (Deutscher Wetterdienst, station 02261),
  OpenWeatherMap (24 city feeds).
- **"How much data / how many segments?"** → 1,021 road segments; source
  histories total ~7 GB of raw CSV; multi-source overlap Sep 2025 → early 2026.
- **"What's the tech stack?"** → Python, FastAPI, Pydantic v2, xsdata
  (generates 913 typed classes from the official XSDs), xmlschema + lxml for
  validation, DuckDB for offline builds, SQLite for the segment store, Leaflet
  for the map. No heavyweight frameworks.
- **"Is this live data?"** → Historical demo dataset replayed through the live
  pipeline; the request path is identical to what a live feed would use.

### Tier 2 — Core design (expect most questions here)

- **"What's your canonical/intermediate data model?"** → A source-agnostic
  canonical schema; every source maps to the same field names before fusion.
  DATEX II is only the output serialization, never the internal model.
- **"Two sources disagree — who wins?"** → Per-field priority order from
  configuration. Each field has its own trust chain (road-surface temp trusts
  the in-road sensor; pressure trusts the weather service). Winner recorded as
  provenance.
- **"Why priority selection instead of averaging?"** → Averaging fabricates a
  value no sensor reported and destroys lineage; for safety data you want a
  real, attributable reading. Disagreement isn't hidden in a mean — it's
  surfaced as the agreement indicator.
- **"How do you handle units?"** → Declarative unit conversions in config
  (factor/offset/clamp) applied during canonical mapping. Real catch: one feed
  delivered Kelvin; the cross-source agreement check exposed it.
- **"Are the sources time-synchronized?"** → No — cadences differ (≈15 min for
  SWS/OpenWeatherMap, hourly DWD, bursty LoRaWAN). Every reading carries its
  own timestamp, shown in the UI (User Interface); snapshots align sources to
  one reference instant.
- **"What's the join key / entity identity?"** → `segment_id` +
  `event_timestamp` for segment data. Caveat we know: the raw exports' `SID`
  column is an import UUID (Universally Unique Identifier), not a sensor
  identity — station identity is `station_id` / `deviceName`.
- **"How do I add a new source?"** → One plug-in class (auto-registered) + one
  config block (their column names → canonical fields + where they sit in each
  priority chain). No core changes.
- **"How do you map local condition codes to the standard?"** → A YAML mapping
  table per jurisdiction (code → `WeatherRelatedRoadConditionTypeEnum` literal
  + labels + colour). The literal set is extracted from the official schema, so
  an invalid enum can't be emitted.
- **"Where's the provenance stored?"** → On every fused field: winning source,
  all candidate values, agreement classification, spread, reading timestamp —
  all queryable via `GET /fused/{id}`.

### Tier 3 — Advanced (data engineering & conformance depth)

- **"How do you align unsynchronized time series?"** → ASOF (as-of) joins in
  DuckDB: for each reference instant, each source's most recent reading
  at-or-before it — causal, never a future value. Exact-timestamp joins lose
  76–78% of rows; ASOF keeps nearly all.
- **"What about stale readings?"** → ASOF can pick up a slightly old value in
  sparse gaps — that's why timestamps are displayed everywhere. The sensor
  layer additionally drops stations silent for more than 48 h at the shown
  moment (treated as offline).
- **"Is XSD validation really on every request? What's the cost?"** → Yes —
  hard gate in the request path; failures return HTTP 422 with XPath-level
  diagnostics. Whole transform ≈ 6 ms mean, p95 ≈ 7 ms, so the gate is cheap.
- **"Structural validity isn't semantic correctness. How do you know values are
  right?"** → Three layers: unit harmonization is declarative and reviewed;
  cross-source agreement flags outliers (caught the Kelvin bug); a semantic
  round-trip test re-parses emitted XML and checks values survive unchanged.
- **"Any lossy mappings to the standard?"** → Yes, documented: *hoarfrost* narrows
  to *frost* (the standard has no hoarfrost literal). Six of seven Bavarian
  codes map one-to-one.
- **"How is location referenced in the output?"** → DATEX II
  `PointLocation → PointByCoordinates` with the segment centroid (from the
  official locationReferencing namespace). Full linear referencing (e.g.
  OpenLR / ALERT-C / linear locations along the road) is a known production
  upgrade — the standard supports it; the prototype uses points.
- **"Build-time vs request-time?"** → Heavy work (7 GB CSVs, DuckDB joins,
  model training) runs offline into small committed artifacts (segment store,
  sensor file, model). The request path only reads those and fuses live —
  which is why a config edit changes output immediately with no rebuild.
- **"Schema evolution — what happens at v3.5/v3.6?"** → Regenerate the typed
  bindings from the new XSD; incompatibilities surface as compile/test failures
  rather than silently invalid XML. The road-weather model is stable across
  3.4–3.6.
- **"Why SQLite/DuckDB and not a real database server?"** → Right-sized for a
  reproducible research prototype: committed artifacts make a fresh clone run
  instantly. The adapter core is storage-agnostic; production would swap the
  store behind the same interfaces.

### Tier 4 — Hard / adversarial (be ready, answer honestly)

- **"Your fused 'current' view mixes readings minutes apart. Is that sound?"**
  → It's the standard nowcasting trade-off: each value is the freshest
  available per source, each carries its timestamp, and the agreement check
  flags when the mix is inconsistent. The alternative — waiting for full
  synchronization — means publishing nothing most of the time.
- **"Is the prediction confidence calibrated? How does it map to
  `probabilityOfOccurrence`?"** → Not formally calibrated — stated openly. The
  mapping is conservative and documented: model probability ≥ 0.66 →
  `probable`, below → `riskOf`, and **never** `certain` (reserved for observed
  data). Calibration (e.g. isotonic/Platt) is named future work.
- **"Your model's 86% — is there temporal leakage?"** → Partly, yes — random
  (not temporal) split, so adjacent timestamps can appear in train and test;
  0.86 is therefore mildly optimistic. A time-based split is the stricter
  number and is on the roadmap. (Saying this unprompted builds credibility.)
- **"Train/serve skew?"** → Avoided by construction: training features are
  built by the *same* non-SWS priority coalesce + unit harmonization the
  fusion engine applies at request time.
- **"Different sensors have different accuracy classes. Do you model
  measurement uncertainty?"** → Not per-sensor error models — priority order +
  agreement tolerance is the pragmatic proxy. Per-source uncertainty weighting
  is a legitimate extension the config structure could carry.
- **"Who owns the config? What's the governance model?"** → The mapping/priority
  YAML is a versioned artifact in Git — changes are reviewable diffs, deployable
  without code release. In production it would sit under the road authority's
  change-control like any operational configuration.
- **"What's missing for production?"** → Honest list: live feed connectors
  (the source interface exists; demo runs on snapshots), authentication/TLS
  (Transport Layer Security) termination, monitoring/alerting on validation
  failures, a proper database, linear location referencing, and the time-ahead
  forecast integration (in progress — Sonali's models).
- **"Why not publish through the national access point directly / why an
  adapter at all?"** → The adapter *is* the path to the access point: MDM/
  Mobilithek accepts DATEX II. The design decision was non-invasiveness —
  standardization as a sidecar so the operational system stays untouched.
- **"Data licensing/privacy?"** → Environmental sensor data, no personal data —
  GDPR (General Data Protection Regulation) exposure is minimal; source
  licensing (DWD open data, commercial OpenWeatherMap terms) is the item to
  clear before public republication.

---

## 11. Project Manager question ladder (shorter — expect these)

- **"What exactly was delivered this semester?"** → A working prototype: the
  generic adapter service, the fusion engine over four real data sources, the
  validated DATEX II (Data Exchange II) output, the interactive dashboard, an
  automated test suite (50 tests), and documentation. All demonstrated live
  today on real recorded data.
- **"Is the data real?"** → Yes — real historical recordings from the four
  networks (2022–2026 coverage; the demo replays Oct–Dec 2025 events). Nothing
  is simulated; the pipeline is the same one a live feed would use.
- **"Who would consume this?"** → Germany's national access point (MDM /
  Mobilithek — Mobility Data Marketplace), neighbouring road authorities
  (ASFINAG in Austria, ŘSD in Czechia), navigation and traffic-service
  providers, and cross-border corridor projects.
- **"What does it cost to run?"** → Very little — a single small service
  container (Docker); the heavy data processing happens offline. No licence
  fees for the standard itself.
- **"Who maintains it? What's the maintenance burden?"** → Low by design:
  region- and source-specific behaviour lives in configuration files, so
  adapting or tuning it doesn't require a developer to touch core code.
- **"What are the risks?"** → Format risk is near zero (the standard is
  EU-mandated). The real dependencies are: access to live feeds for
  production, source data licensing for public republication, and operational
  hardening (monitoring, authentication) — all named, none architectural.
- **"What's next?"** → Three steps: (1) connect live feeds instead of recorded
  snapshots, (2) integrate the time-ahead forecasts Sonali is developing
  (+3 h / +18 h horizons — the publishing layer is already forecast-ready),
  (3) production hardening and a pilot with a real consumer (e.g. via the
  national access point).
- **"Can other regions use it?"** → Yes — that's the core design goal.
  Adopting a new jurisdiction is a matter of writing a new mapping/priority
  configuration, not building new software.
- **"How do we know it actually works?"** → Measured, not claimed: 100% schema
  conformance on the evaluation sample, ~6 ms per transformation, 50 automated
  tests including a conformance matrix over every condition the system can
  emit, and the live demo you just watched.
