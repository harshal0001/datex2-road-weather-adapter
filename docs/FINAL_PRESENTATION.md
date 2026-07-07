# Final Research Project Presentation (~20 minutes)

**Title:** A Configuration-Driven Adapter for Standardizing Multi-Source Road-Weather Data to DATEX II v3
**Presenter:** Harshal Kothari · M.Sc. Applied Research in Computer Science · Hof University of Applied Sciences
**Context:** Semester research project — interoperability layer for the Winterdienst Road-Condition Forecasting System (Landkreis Hof)

---

## How this deck is organized

- **16 slides + live demo = 20:00 exactly** — 17:00 of slides + a hard 3:00 demo block (including the browser switch). Every slide heading carries its time budget in m:ss; the running clock with checkpoints is in **Part 4**.
- `📸 SCREENSHOT n` markers show exactly where a dashboard screenshot goes — the capture list with URLs and click-steps is in **Appendix A**.
- **Say:** blocks are speakable notes (abbreviations expanded in round brackets, as you prefer) — each is deliberately written *under* its slide's m:ss budget, so you have breathing room and never have to rush.
- The **Peinl defense** is not one defensive slide — it is engineered into slides 4, 5, 9, 11 (DKSR stakeholder validation), 12, 13 and 14. A dedicated Q&A prep section is in **Appendix B**.
- The talk ends with a **3:00 live demo block** (slide 16 has the timed 4-beat choreography + fallback plan).

---

# PART 1 — THE SLIDES

---

## Slide 1 — Title (0:30)

**On the slide:**
> **From Heterogeneous Sensors to a European Standard**
> A Configuration-Driven Adapter for Multi-Source Road-Weather Fusion and DATEX II v3 Standardization
>
> Harshal Kothari · Applied Research in Computer Science · Hof University
> Research project within: Road-Condition Forecasting System — Landkreis Hof (Winterdienst / CIVORA)

**Say:**
"Good [morning/afternoon]. I am Harshal Kothari, Applied Research in Computer Science. My project addresses the *interoperability* side of the road-condition forecasting system for Landkreis Hof. The question: once we have sensor data and machine-learning output, **how do we make it usable outside our own system** — in a form road authorities across Europe can actually consume?"

---

## Slide 1.5 — The published scientific foundation: the ISM 2025 paper (1:00) ⚑ *Peinl anchor #0*

*(Numbered 1.5 to keep all cross-references in this document stable — in your actual deck it is simply slide 2, right after the title.)*

**On the slide** (keep it sparse — citation + 4 bullets + the hook):
> Cisneros Saldaña et al. (2025) — **"AI-based System for Road Surface Condition Forecasting Using Multi-Source Meteorological Data"**
> *Procedia Computer Science* (Elsevier) · ISM 2025 · Hof University + Landesbaudirektion Bayern

- **Published & deployed:** road-state forecasting across Bavaria, integrated into the state's winter-service system (WDMS)
- **Multi-source:** 516 road weather stations + vehicle thermal mapping + elevation data
- **Interpretable by design:** decision trees, auditable by public agencies — **87.6–100 % accuracy** at evaluated stations
- **Forecasts at now / +3 h / +18 h**, refreshed every 15 minutes from DWD forecast inputs

> ⚠ **Not covered by the paper: standardized data exchange — "DATEX" appears 0 times.** ← *my research gap*

**Say (1:00):**
"This work builds on a published line of research: last year, colleagues at our institute, with the Bavarian State Building Authority, published this system at the ISM conference — road-condition forecasting across Bavaria, fusing over five hundred road weather stations, thermal-mapping vehicles and elevation data. Auditable decision trees, up to one hundred percent accuracy at evaluated stations, deployed in Bavaria's winter-service system, forecasting at now, plus three and plus eighteen hours.

But the paper is entirely about *producing* predictions. Standardized *exchange* — DATEX II — never appears in it. That open end is exactly where my project picks up."

*→ transition into slide 2 (the Landkreis Hof / CIVORA parent project).*

> 💡 **Details held back for Q&A** (not on the slide): per-station local models + one generalized altitude-aware model for sensor-less roads; Flask/Vue.js/Redis/Docker stack; training winters Nov 2022–Apr 2025; the six-class Bavarian taxonomy is the same one the Hof pipeline labels use and my `segment_conditions.yaml` maps to DATEX II — semantic continuity across all three systems.

> ⚑ **Why this is Peinl anchor #0:** it establishes, before any critique can land, that (a) you stand on peer-reviewed work from your own institute, and (b) your project addresses a gap that published work *explicitly leaves open* — the classic form of a legitimate research contribution. If Peinl later asks "what's the delta over the state of the art?", you can point back to this slide: the state of the art is this paper, and it stops where you start.

---

## Slide 2 — The parent project in 45 seconds (0:45)

**On the slide** (one simple diagram, left→right):
```
LoRaWAN ice sensors ─┐
OpenWeather API ─────┤→ CIVORA platform (DKSR) → ETL pipeline → ML model → ice warnings
SWS road stations ───┤    (PostGIS, 15-min road-segment time series)
DWD climate data ────┘
```

**Bullets:**
- Winterdienst project: predict icy roads per road segment in Landkreis Hof (now, +3 h, +18 h)
- Milestone 1 (Feb 2026): CIVORA (DKSR) confirmed as central data platform; BAYSIS road network as spatial backbone
- Milestone 2 (Mar 2026): LoRaWAN + OpenWeather streams live; ML-ready `road_segment_timeseries`; ID3 decision-tree model
- **My project sits at the OUTPUT side: it did not exist in this picture**

**Say:**
"The parent project: four data sources feed the CIVORA platform run by DKSR (Data Competence Center for Cities and Regions). An ETL (Extract, Transform, Load) pipeline maps every reading onto the BAYSIS road network, builds 15-minute time series per road segment, and a machine-learning model predicts black ice. Pipeline and model are led by my colleague Sonali Singh. What is missing: **everything here speaks a project-internal schema** — nothing outside can consume it. That gap is my research project."

> ⚠️ **Careful wording** (interconnection with the shared docs): the M1/M2 reports are Sonali's milestones on the CIVORA side. Present them as *context you build on*, never as your own work. One sentence of credit: "The pipeline and model work is led by my colleague Sonali Singh; I work on the standardization layer."

---

## Slide 3 — The problem: data heterogeneity + an EU mandate (1:30)

**On the slide** — two columns:

**Left — the heterogeneity problem (from the real data):**
| | SWS | LoRaWAN | OpenWeather | DWD |
|---|---|---|---|---|
| Measures | road state itself | road surface, live | atmosphere + forecast | soil temp, precip type |
| Units | °C | °C | **Kelvin** | °C, oktas |
| Cadence | 15 min | ~10 min bursts | 15 min | 60 min |
| Coverage | 13 stations, wide | 137 sensors, dense-local | every segment | 1 station |
| History | since Nov 2022 | since Sep 2025 | since Jul 2024 | since Nov 2024 |

**Right — the interoperability mandate:**
- EU ITS Directive 2010/40/EU + Delegated Regulation (EU) 2022/670
- Road-condition data on the TEN-T (Trans-European Transport Network) **must be available in DATEX II by 2027**
- Hof sits on the A9 / A93 corridors → this applies to exactly this region
- Consumers: the National Access Points (NAPs — the official data portals every EU member state must operate) and road operators across Europe

**Say:**
"Two problems. Technical: the four sources disagree in what they measure, in units — OpenWeather reports Kelvin, everything else Celsius — in cadence, coverage and history depth. You cannot just union these tables. And each exists for a physical reason: SWS (Straßenwetterstationen, road weather stations) observes the road state itself; LoRaWAN (Long Range Wide Area Network) sensors see the road surface live; OpenWeather alone has a forecast and full coverage; DWD (Deutscher Wetterdienst, the German weather service) adds soil temperature and precipitation type — atmosphere, surface, ground.

Regulatory: European Union regulation 2022/670 mandates DATEX II for safety-related road data on the trans-European network by 2027. Hof lies on the A9 and A93 corridors — a legal requirement arriving in eighteen months."

---

## Slide 4 — Research questions (1:30) ⚑ *Peinl anchor #1*

**On the slide:**

> **RQ1 — Architecture:** Can multi-source standardization be driven entirely by *declarative configuration*, so that adding a source, changing a priority, or targeting a new region requires **zero code changes**?
>
> **RQ2 — Fusion:** How can asynchronous, multi-cadence, partially disagreeing sources be fused into *one* standard-conformant snapshot per road segment — with per-field provenance and temporal consistency?
>
> **RQ3 — Standard expressiveness:** Where does DATEX II v3 *fail* to express what a modern multi-source ML system produces — and what are the workarounds?

**Method line at the bottom:**
Design Science Research: build a working artifact → evaluate it quantitatively (latency, conformance, agreement) → extract generalizable design knowledge.

**Say:**
"This is a research project, so let me be precise about the research questions — 'mapping field A to field B' is *not* one of them. RQ1, architecture: can the entire standardization behaviour live in declarative configuration, so the code never changes when the data landscape does? RQ2, fusion: these sources tick at different rates and sometimes contradict each other — how do you produce one defensible, timestamped, provenance-carrying snapshot? RQ3, the standard itself: where does DATEX II break when you push fused, machine-learning-derived data through it? Method: design science — build the artifact, evaluate it with measurements, extract generalizable knowledge. I will come back to each with results."

> ⚑ **Why this slide defuses Peinl:** it reframes the project *before* he can. Semantic mapping is demoted to "one mechanism inside RQ1." The deliverables are an evaluated architecture pattern (RQ1), a fusion method (RQ2), and empirical findings about a European standard (RQ3).

---

## Slide 5 — Why DATEX II, and why it is not trivial (1:00) ⚑ *Peinl anchor #2*

**On the slide:**
- DATEX II v3.4 = EN 16157, the CEN (European Committee for Standardization) standard for road-traffic data exchange — *the* named format in EU regulation
- Not a flat schema: **913 generated classes**, deep hierarchy (`SituationPublication → Situation → SituationRecord → WeatherRelatedRoadConditions`)
- Mandatory concepts with **no equivalent in our data**: `probabilityOfOccurrence`, situation versioning, location referencing systems
- Our 6 local condition codes ↛ 1:1 DATEX II enums (hoarfrost? freezing rain?) — **mapping decisions with safety consequences**

**Say:**
"Why DATEX II? It is the format the regulation names — European Norm 16157. And it is not renaming columns: version 3 is a deeply nested object model — 913 Python classes generated from the official XSD (XML Schema Definition) schemas. It forces concepts our data does not have, like `probabilityOfOccurrence`, and lacks concepts our data *does* have — I'll show those in the findings. Even the labels are a real mapping problem: hoarfrost (Reifglätte) and freezing rain (Glatteis) onto DATEX II's enumeration is a decision with road-safety consequences, not a lookup table."

---

## Slide 6 — Architecture of the adapter (1:15)

**On the slide** (layer diagram):
```
profiles/           fusion.yaml · segment_conditions.yaml · bavaria.yaml
(CONFIG = the       per-field source priority · unit conversions ·
research artifact)  agreement tolerances · enum mappings
        │ drives
adapter/            fusion engine · temporal alignment · validation gate
(pure Python core)
        │
outputs/            xsdata classes → DATEX II v3 XML → XSD validation (hard gate)
        │
api/ + static/      FastAPI (22 endpoints) · Leaflet dashboard · Swagger
```
- 1,021 road segments · 177 physical sensors · 4 sources
- **Every request is validated against the official XSD before it leaves the system**

**Say:**
"The architecture in one picture. At the top: configuration — deliberately, the research artifact. `fusion.yaml` declares per field which source is trusted first, which unit conversions apply, and how much sources may differ before we flag disagreement. The core engine is pure Python with no knowledge of any specific source. Below that, serialization into DATEX II — and every response passes XSD validation as a hard gate: if the document does not conform, the request fails. On top, a FastAPI (a Python web framework) layer and the dashboard.

RQ1 concretely: adding Bavaria-wide mappings was one new YAML file — `bavaria.yaml` — zero lines of code. The architecture claim, demonstrated."

📸 **SCREENSHOT 7 (optional, small corner inset):** Swagger `/docs` page — signals "real, documented API" without spending time on it.

---

## Slide 7 — The prototype: live dashboard (1:00)

📸 **SCREENSHOT 1 — full-width, the hero image of the deck:** entire dashboard — map with colored segments + sensor markers, source checkboxes, Moment picker with "data as of" badge, segment table.

**On the slide:** the screenshot + three callout arrows:
1. → source checkboxes: "fusion recomputed live per request"
2. → map: "1,021 BAYSIS road segments, colour = fused condition"
3. → Moment picker: "reproducible historical snapshots (e.g. ice event, 24 Nov 2025 03:00)"

**Say:**
"The running prototype. Every coloured segment is a real road in Landkreis Hof; the colour is the *fused* condition. The checkboxes are the four sources — untick one and fusion re-runs live; nothing is precomputed. The Moment picker gives reproducible snapshots — here, the ice event of November 24th, 2025 at 3 a.m., when 643 segments were icy. And every view states 'data as of' a timestamp — with asynchronous sources, an honest timestamp is part of correctness."

---

## Slide 8 — Per-field fusion with provenance (1:15)

📸 **SCREENSHOT 4 — the selected-segment table:** per-source values side by side, the winning value, the "Sources agree: n/m fields" badge, and the 🕐 per-source timestamps.
📸 **SCREENSHOT 3 — the per-field priority table** with ★ on the currently supplying source (place beside or below Screenshot 4).

**On the slide, next to the screenshots:**
- Fusion is **per field**, not per source: road temp from SWS, humidity from LoRaWAN, cloud cover from DWD — in the *same* output record
- Every value carries: source, timestamp, unit-converted original
- Agreement check across sources → "Sources agree: n/m fields"
- **This check caught a real bug: an upstream feed delivering Kelvin as Celsius**

**Say:**
"Here 'just mapping' visibly ends. Fusion happens per *field*: for one segment, surface temperature may come from SWS, humidity from LoRaWAN, cloud cover from DWD — each chosen by declared priority, each carrying its own source and timestamp. Where sources overlap, the adapter checks agreement within a configured tolerance — 'sources agree on n of m fields.' Not cosmetic: this check exposed a real bug — temperatures arriving in Kelvin but labelled Celsius, a 273-degree disagreement. A single-source pipeline would have shipped that straight into an ice warning."

---

## Slide 9 — The temporal alignment problem (1:15) ⚑ *Peinl anchor #3*

📸 **SCREENSHOT 2 — Moment picker open + map sensor tooltip showing its 🕐 timestamp**, demonstrating that markers and segment table now show the same instant.

**On the slide:**
- Naive approach: "show each source's latest value" → map and table silently show **different points in time**
- Sources tick at 10/15/15/60-minute cadences; naive 'latest' mixes instants
- Solution: **moment-aware alignment** — one reference instant per view; every source snapshotted to it via ASOF joins (DuckDB), with a 48 h staleness cutoff
- Found because a professor asked "why do these two timestamps differ?" — the fix is a *methodological* point: temporal consistency is a first-class requirement of multi-source standardization

**Say:**
"One concrete research lesson. My first version showed each sensor's most recent value — which sounds right, and is wrong: because the sources tick at different rates, the map and the table were silently describing *different moments in time* — and a professor immediately spotted it. The fix: every view is anchored to one reference instant, every source aligned to it with an ASOF join — 'the most recent reading at or before this moment' — plus a 48-hour staleness cutoff. The generalizable finding: **temporal consistency is not a UI detail, it is part of the data contract.**"

---

## Slide 10 — The standard output: validated DATEX II XML (1:00)

📸 **SCREENSHOT 6 — browser showing the DATEX II XML** for one segment (`/api/segments/datex?segment_id=16117045&sources=sws,lorawan,dwd,openweather`), ideally with DevTools network tab open showing the `x-validation-status: valid` response header.

**On the slide:**
- One HTTP call: fused segment → `SituationPublication` / `WeatherRelatedRoadConditions`
- `probabilityOfOccurrence` set honestly: *probable* / *risk of* — never *certain* (fused + modelled data)
- Validated against the official CEN XSD on **every request** — response header `x-validation-status: valid`
- This XML is what the European National Access Points and road operators would ingest

**Say:**
"The deliverable of the whole chain: standard DATEX II version 3 XML, one HTTP call per segment. Two honest choices: `probabilityOfOccurrence` is never 'certain' — this is fused, partially modelled data, so 'probable' or 'risk of'. And the validation status is in the response header of every request — the consumer can see the document passed the official schema. This is precisely the format the National Access Points (the official road-data portals of every European Union member state) and road operators expect."

---

## Slide 11 — Evaluation: measured, not asserted (1:30)

**On the slide** (big numbers, minimal text):
| Metric | Result |
|---|---|
| XSD conformance (official CEN schema) | **100 %** across all 1,021 segments × source combinations |
| Transform latency | **5.7 ms mean · 6.9 ms p95** per segment |
| Test suite | **50 automated tests** (fusion, agreement, endpoints, XSD matrix, temporal alignment) |
| Live fusion inputs | 4 sources · 177 sensors · 1,021 segments · 35 reproducible moments |
| Data-quality catches | Kelvin/Celsius bug · dead-since-2024 stations filtered |
| **Stakeholder evaluation** | **Demonstrated live to DKSR (platform operator): project manager + data architect — work acknowledged, strong interest expressed** |
| **Publication** | **Paper planned including this prototype — continuing the published ISM 2025 research line** |

**Say:**
"Evaluation — claims must be measured. Conformance: one hundred percent of documents validate against the official schema, on every request. Performance: five point seven milliseconds mean per transform. Fifty automated tests, including one asserting temporal alignment — the professor's question, turned into a regression test.

And the relevance side of design science: last week I demonstrated the prototype live to DKSR — the operator of the CIVORA platform — with their project manager and data architect. The data architect examined the fusion configuration and the validated output in detail; both acknowledged the work and expressed strong interest. And this line continues: we plan to write a paper that includes this prototype — carrying the published research I opened with one step further."

> 💡 **Why this placement is the clever one:** stakeholder/expert evaluation is a *recognized evaluation method* in Design Science Research (Hevner's relevance cycle). Framed as an evaluation row — not as an anecdote — the DKSR demo becomes scientific evidence, and it lands one slide before the findings, right where Prof. Peinl's "where is the research?" pressure is highest. Do not oversell it ("they loved it"); the dry phrasing "acknowledged, strong interest" is more credible. The planned-paper row lands here naturally: stakeholder validation → publication plan reads as momentum, and it closes the loop with the ISM 2025 slide — the research line the panel saw at the start continues *through your prototype*.

---

## Slide 12 — Findings: where DATEX II bends and breaks (1:30) ⚑ *Peinl anchor #4 — the knowledge contribution*

**On the slide:**

**What fit cleanly ✔**
- Condition classes → `WeatherRelatedRoadConditions` enums
- Uncertainty → `probabilityOfOccurrence`
- Observation time → situation record timestamps

**What did NOT fit — findings ✘**
1. **Per-field provenance has no home** — DATEX II assumes one publisher; "surface temp from SWS at 03:00, humidity from LoRaWAN at 02:58" is not expressible → kept in the API layer / would need a DATEX II extension
2. **Fused-source disagreement** ("2 of 4 sources agree") — no native concept
3. **Point vs linear referencing** — segments are lines; prototype publishes centroids (`PointByCoordinates`); full linear location referencing (OpenLR / ALERT-C) is the production step
4. **Forecast horizons (+3 h / +18 h)** map awkwardly — DATEX II 'forecast' situations exist but not per-field, per-model-horizon

**Say:**
"The RQ3 findings — the clearest research content in the project, because none of this is documented anywhere; you only find it by pushing real fused data through the real schema. Four gaps. First, DATEX II assumes *one publisher, one observation* — per-field provenance, the whole value of fusion, has no home and would need an extension. Second, the same for disagreement information. Third, my segments are lines, but the prototype publishes centroid points — production would need linear referencing like OpenLR. Fourth, the plus-three and plus-eighteen-hour forecast horizons fit DATEX II's forecast model only awkwardly. Each gap is a transferable finding for anyone standardizing sensor-fusion output in Europe — and input for the standardization community itself."

---

## Slide 13 — Answering the research questions (0:30)

**On the slide:**
- **RQ1 ✔** Zero-code extensibility demonstrated: second region profile (`bavaria.yaml`) = 0 lines of code; source priorities/tolerances changed at runtime via YAML
- **RQ2 ✔** Per-field priority fusion + ASOF temporal alignment + agreement checking; provenance preserved end-to-end; caught real data errors
- **RQ3 ✔** Four documented expressiveness gaps in DATEX II v3 for fused/ML data, with workarounds

**Say:**
"Against the questions from slide 4: RQ1 — demonstrated, config-only extension works, and you will see it live. RQ2 — the fusion method works and demonstrably improves data quality — no pure mapping exercise achieves that. RQ3 — four documented gaps with workarounds. The contribution: an evaluated architecture pattern, a fusion method, and empirical findings about a European standard."

---

## Slide 14 — Positioning within the parent project & future work (1:00)

**On the slide** (the slide-2 diagram, now extended):
```
CIVORA pipeline → ML model (ID3, Sonali) ──→ [ MY ADAPTER ] ──→ DATEX II v3
     (M1/M2, done)      now/+3h/+18h            fusion +           ↓
                        (in progress)           validation    EU National Access Points · road operators
                                                              (EU mandate 2027)
```
**Future work:**
- Ingest Sonali's +3 h / +18 h predictions → DATEX II *forecast* situations (design already sketched)
- Live CIVORA feeds instead of historical exports (source plug-ins exist; it's a config change)
- Linear location referencing (OpenLR) instead of centroids
- Calibrated confidence for published probabilities

**Say:**
"Next steps. The parent model — Sonali's work — will produce predictions at now, plus three and plus eighteen hours; my adapter is the publication channel for exactly that. Switching from historical exports to the live CIVORA feed is configuration, not re-engineering — and after last week's demonstration, DKSR's own team signalled interest in this layer. The endpoint is the 2027 European mandate: this prototype is the missing last mile between a regional machine-learning system and the European infrastructure legally required to receive it."

---

## Slide 15 — Conclusion → hand-off to live demo (0:30)

**On the slide:**
> **Built:** a working, tested, 100 %-schema-conformant DATEX II v3 adapter fusing 4 real sensor networks across 1,021 road segments — in milliseconds, fully configuration-driven.
>
> **Learned:** temporal consistency is part of the data contract · fusion with agreement checks is a data-quality instrument · DATEX II v3 has 4 concrete gaps for multi-source ML data.
>
> **Enables:** the Hof forecasting system to meet the EU 2027 DATEX II mandate — and any similar regional system to reuse the pattern by writing YAML, not code.

**Say:**
"To conclude: a working, measured, fully standard-conformant adapter; findings about multi-source standardization — and about the standard itself — written nowhere else; and a configuration-driven path to the European mandate, for Hof and any comparable region. Rather than telling you — let me show you. The system is running live."

*→ switch to the browser.*

---

## Slide 16 — "Live demo" placeholder slide (leave on screen while you switch — demo block 3:00 hard)

**On the slide** (so the projector isn't blank if the switch takes a second):
> **Live demo** — `localhost:8000/dashboard`
> 4 sources → per-field fusion → validated DATEX II v3

### Demo choreography — 3:00 total: browser switch 0:10 · beat 1 0:40 · beat 2 0:45 · beat 3 0:40 · beat 4 0:35 · closing line 0:10. Rehearse with a timer; cut beat 3 first if running over (saves 0:40).

**Before the talk (non-negotiable):** server started (`cd /mnt/c/Users/ASUS/datex2-adapter && .venv/bin/python -m uvicorn api.main:app --port 8000`, wait ~30 s, check `/health`), two browser tabs pre-opened: **Tab A** `http://localhost:8000/dashboard` (hard-refreshed, all 4 sources ticked, Moment = latest), **Tab B** `http://localhost:8000/api/segments/datex?segment_id=16117045&sources=sws,lorawan,dwd,openweather`. Browser zoom ~125 % for the projector.

1. **The fused map (Tab A).** "This is the live system — 1,021 real road segments in Landkreis Hof; colour is the fused condition, and the 'data as of' badge tells you exactly which instant you are looking at."
2. **Fusion, live.** Untick SWS → map and segment table re-render. "Nothing here is precomputed — I just removed the highest-priority source, and fusion re-ran per field; watch the ★ in the priority table move to the next source. Re-tick — it comes back." *(This is the RQ1 demonstration: behaviour follows configuration, live.)*
3. **The ice event.** Switch Moment to **ice-event-night**. "Same system, snapshotted at 3 a.m. on 24 November 2025 — 643 segments icy. Every source is aligned to this instant; click any sensor and the timestamp matches the table." *(This is the RQ2/temporal-contract demonstration.)*
4. **The standard output (Tab B).** "And this is the deliverable: the same segment as validated DATEX II XML — the exact format the European National Access Points and road operators ingest, schema-checked on every request." *(Optionally F12 → show `x-validation-status: valid`.)*

**Closing line, back on the conclusion or thank-you slide:**
"That is the full chain — four sensor networks in, one European standard out, in real time. Thank you; I'm happy to take questions."

**Demo failure fallback:** if the server or projector misbehaves, do NOT debug on stage — say "I'll show the live system afterwards to anyone interested" and use Screenshots 1, 2 and 6 (already in the deck) to walk the same four beats. The talk loses nothing structurally.

---

## Slide 17 — Backup slides (not presented, keep ready)

1. 📸 **SCREENSHOT 5 — compare modal** showing a real source disagreement (for the Kelvin-bug story in Q&A)
2. `fusion.yaml` excerpt (for "show me the config" questions)
3. Endpoint catalogue table (22 endpoints — from `docs/STAKEHOLDER_BRIEF.md` §7)
4. Data coverage timeline chart (SWS Nov 2022→ · OWM Jul 2024→ · DWD Nov 2024→ · LoRaWAN Sep 2025→; 4-source overlap from Sep 2025)
5. Label taxonomy table: 6 local classes (trocken → glatteis) vs DATEX II enums, with the mapping decisions annotated
6. M2 pipeline diagram (Sonali's ERD) — for "how does the upstream work" questions
7. Design Science Research method diagram (Hevner: build → evaluate → learn)

---

# PART 2 — SCREENSHOT CAPTURE LIST (Appendix A)

Start the server first:
```
cd /mnt/c/Users/ASUS/datex2-adapter && .venv/bin/python -m uvicorn api.main:app --port 8000
```
Wait ~30 s, confirm `http://localhost:8000/health` says `"status": "ok"`, then hard-refresh the dashboard (Ctrl+Shift+R). Capture at a maximized browser window, hide bookmarks bar (Ctrl+Shift+B) for clean shots.

| # | Used on slide | URL | What to set up before capturing |
|---|---|---|---|
| **1** | 7 (hero) | `http://localhost:8000/dashboard` | All 4 sources ticked · Moment = **ice-event-night** (dramatic red/blue map) · one segment selected so the table is populated · whole window |
| **2** | 9 | `/dashboard` | Moment dropdown **open** showing the options + "data as of" badge; then a second shot hovering a sensor marker so its tooltip 🕐 timestamp is visible |
| **3** | 8 | `/dashboard` | Scroll to the **per-field source priority table** (★ = supplying the value now); crop to just the table |
| **4** | 8 | `/dashboard` | Click a segment covered by multiple sources → capture the **selected-segment table** incl. "Sources agree: n/m fields" badge and 🕐 per-source times |
| **5** | Backup 1 | `/dashboard` | Open the **compare modal** on a segment where sources disagree (untick/re-tick to find one with agreement < m/m) |
| **6** | 10 | `http://localhost:8000/api/segments/datex?segment_id=16117045&sources=sws,lorawan,dwd,openweather` | Browser rendering the XML; optionally F12 → Network → click the request → show `x-validation-status: valid` header |
| **7** | 6 (inset, optional) | `http://localhost:8000/docs` | Swagger UI, endpoints expanded one level |

Tips: capture at 100 % browser zoom → then zoom the *slide image*, not the browser (keeps text crisp). Use the same Moment (ice-event-night) in screenshots 1–5 so all numbers/timestamps in the deck are mutually consistent — the professor *will* cross-check timestamps between your screenshots.

---

# PART 3 — THE PEINL DEFENSE (Appendix B)

Prof. René Peinl's stated critique: *"This is not a research project — it's just semantic mapping of data."*

## Strategy
Do **not** rebut him defensively in the talk. The deck pre-empts the critique structurally: research questions before the artifact (slide 4), findings that only research produces (slides 9, 12), quantitative evaluation (slide 11), explicit method (Design Science Research). If it still comes up in Q&A, agree with the kernel and reframe:

## The core spoken answer (memorize this)

> "You're right that semantic mapping alone wouldn't be research — a lookup table isn't a contribution. But mapping is only one mechanism inside this project, and the research lies in three places where mapping ends:
>
> **First, the fusion problem.** Four sources with different cadences, units, coverage and reliability have to become *one* defensible statement per road segment. That required per-field priority fusion, temporal alignment via ASOF joins, and cross-source agreement checking — and that agreement checking found a real Kelvin-vs-Celsius data error that a mapping would have propagated silently into an ice warning. A mapping transforms data; this architecture *judges* it.
>
> **Second, the negative results about the standard.** DATEX II cannot express per-field provenance, cannot express source disagreement, and handles ML forecast horizons awkwardly. Those gaps are not documented anywhere — I found them empirically by pushing real fused data through the real schema, and they are transferable knowledge for anyone in Europe standardizing sensor-fusion output, and potentially input to the standard's own evolution.
>
> **Third, the evaluated architecture claim.** The hypothesis was that the entire standardization behaviour can live in declarative configuration — and I can demonstrate it: a second regional profile was zero lines of code, and I can change fusion behaviour live in YAML in front of you. That's a design-science contribution: artifact, evaluation, generalizable pattern."

## Likely follow-up jabs and answers

**"Fusion by priority list — that's trivial, not novel."**
→ "The priority list is the simplest component, deliberately — operators must be able to audit it. The non-trivial parts are around it: temporal alignment across asynchronous cadences with staleness handling, agreement checking with per-field tolerances, and provenance that survives all the way into the API response. And simplicity is a *requirement* here, not a limitation: this feeds winter-service decisions, so every fused value must be explainable to a road operator in one sentence. I did evaluate the design against that requirement."

**"Where is the scientific evaluation? 100 % XSD validity just means your code isn't broken."**
→ "Correct — conformance is a necessary gate, not the contribution. The evaluation is layered: conformance as the correctness floor, latency to show standardization costs nothing operationally, the 50-test suite including temporal-alignment regressions as behavioural evidence, and — most importantly — the RQ3 gap analysis, which is a qualitative result about the standard itself, evidenced by the concrete workarounds in the artifact."

**"Anyone could have done this with a commercial ETL tool."**
→ "An ETL tool gives you field mapping and unit conversion. It does not give you DATEX II situation-model semantics — deciding what a fused, partially modelled observation means in terms of `probabilityOfOccurrence` and situation versioning — and it has no answer for per-field provenance or cross-source disagreement, because the target standard itself has none; that's finding one. The 913-class object model, the validation gate, and the temporal contract are exactly the parts ETL tooling leaves to you."

**"What's the delta over the state of the art?"**
→ "Published DATEX II work covers single-publisher traffic-management feeds. I found no documented treatment of multi-source *fused* sensor data with provenance under DATEX II v3 — the standard's own design assumption is one publisher per situation. The delta is precisely that mismatch, characterized and worked around in a running system, plus the config-driven architecture pattern evaluated on real regional data."

**"Why not contribute this as a DATEX II extension proposal, then?"**
→ (He might offer this as constructive criticism — take it.) "That is exactly the right next step, and the gap analysis on slide 12 is written to be the input for it. Within one semester the scope was to characterize the gaps in a working system; drafting a Level-B extension for fused-data provenance is the natural follow-up, potentially the master's thesis."

**"The ML model isn't yours, the platform isn't yours — what's left?"**
→ "Correct, and clearly credited — the pipeline and model are Sonali's work on CIVORA. My contribution is the layer neither of those produces: the standardization architecture, the fusion-with-provenance method, the temporal contract, and the standard-gap findings. In the project's own terms: M1/M2 made the data ML-ready; my work makes the results *Europe-ready* — which is what the 2027 regulation demands."

**"This is engineering for practitioners, not science."**
→ "Design science treats practitioner relevance as one half of the rigour–relevance cycle, and I evaluated both halves. Rigour: measured conformance, latency, and a documented gap analysis of the standard. Relevance: I presented the running system to DKSR — the platform operator — with their project manager and data architect; the data architect went through the fusion configuration and the validated output in depth, and they acknowledged the approach and expressed concrete interest. An artifact that survives both quantitative evaluation *and* scrutiny by the deploying organisation's architect is exactly what design-science research produces."

## Honest-weakness list (concede fast if pressed — credibility beats bluffing)
- Published locations are segment **centroids**, not linear references — production would need OpenLR; named as future work.
- "Sources agree n/m" is a **count, not a calibrated confidence** — deliberately renamed to stay factual.
- The demo model's 86 % accuracy has **temporal-leakage risk** in its split; the parent project's AP5 validation phase addresses evaluation properly.
- Historical exports, not live CIVORA feeds — the plug-in seam exists (`sources/`), switching is future work.

---

# PART 4 — TIMING & REHEARSAL PLAN (exact 20:00)

Every **Say:** block above is now written *under* its slide's budget (~110–120 words per minute of budget), so the clock below has built-in slack for slide changes and breathing. The "Clock" column is the running total — it tells you when you must be *leaving* each slide.

| Slide | Content | Budget | Clock — leave by |
|---|---|---|---|
| 1 | Title | 0:30 | 0:30 |
| 1.5 | ISM 2025 paper (context) | 1:00 | 1:30 |
| 2 | Parent project | 0:45 | 2:15 |
| 3 | Heterogeneity + EU mandate | 1:30 | 3:45 |
| 4 | Research questions | 1:30 | 5:15 |
| 5 | Why DATEX II is not trivial | 1:00 | 6:15 |
| 6 | Architecture | 1:15 | 7:30 |
| 7 | Dashboard (hero) | 1:00 | 8:30 |
| 8 | Per-field fusion | 1:15 | 9:45 |
| 9 | Temporal alignment | 1:15 | 11:00 |
| 10 | Validated DATEX II XML | 1:00 | 12:00 |
| 11 | Evaluation (incl. DKSR) | 1:30 | 13:30 |
| 12 | DATEX II gaps (findings) | 1:30 | 15:00 |
| 13 | RQ answers | 0:30 | 15:30 |
| 14 | Positioning + future | 1:00 | 16:30 |
| 15 | Conclusion → demo hand-off | 0:30 | **17:00** |
| 16 | **Live demo** (switch 0:10 + 4 beats + closing 0:10) | **3:00** | **20:00** |

**Three checkpoints while presenting** (glance at the clock only here):
- **5:15 — leaving slide 4** (research questions delivered). If late: slides 5–7 are where you make it up; tighten, don't skip.
- **11:00 — leaving slide 9** (walkthrough half done). If late: compress slide 10 to one sentence plus the screenshot (saves ~0:30).
- **17:00 — switching to the browser.** If late: cut demo beat 3, the ice event (saves 0:40) — the demo must still end by 20:00.

Because the live demo shows the dashboard for real, keep slides 7–10 *brisk* — the screenshots establish the concepts; the demo proves them. Don't demo-narrate twice: on slides 7–10 explain *what and why*, in the demo show *that it's real*.

**Never trim slides 4, 11, 12 or the demo** — they carry the research claim and the proof.

Rehearse twice with a timer: once slides-only (target **17:00 ± 0:30**), once end-to-end including the browser switch and demo (target **20:00, hard stop**). Rehearse the Peinl core answer (Part 3) out loud twice — it must sound composed, not defensive.
