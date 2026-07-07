# Q&A Preparation — Final Presentation Panel

Likely questions from Prof. Peinl and the rest of the panel, with short, direct answers.
Rules: **answer in 2–3 sentences, concede weaknesses immediately, never bluff, bridge back to a slide when possible.** The three killer facts to have ready at all times: the **Kelvin bug** (fusion as data-quality instrument), the **four DATEX II gaps** (empirical findings), and **`bavaria.yaml` = zero lines of code** (evaluated architecture claim).

---

## 1. Research value & methodology (Peinl territory)

**Q: This is just semantic mapping. Where is the research?**
A: Mapping is one mechanism inside the project, not the contribution. The contributions are: a fusion method that demonstrably catches real data errors (Kelvin bug), four undocumented expressiveness gaps in DATEX II found empirically, and an evaluated zero-code architecture claim. A mapping transforms data; this system *judges* it.

**Q: What is the delta over the state of the art?**
A: Published DATEX II work covers single-publisher traffic-management feeds. I found no documented treatment of multi-source *fused* sensor data with per-field provenance under DATEX II v3 — the standard itself assumes one publisher per situation. That mismatch, characterized and worked around in a running system, is the delta.

**Q: What is your research method, precisely?**
A: Design Science Research: build an artifact addressing a real problem, evaluate it rigorously (conformance, latency, tests), and extract generalizable design knowledge (the RQ3 gap analysis, the temporal-contract finding). Stakeholder evaluation with DKSR covers the relevance cycle.

**Q: Your evaluation is just "my code works." Where is the scientific evaluation?**
A: Conformance and latency are the correctness floor, not the contribution. The scientific results are qualitative: four documented gaps in a European standard, evidenced by concrete workarounds in the artifact, plus the temporal-consistency finding. Negative results about a standard are results.

**Q: Is one case study (Hof) enough to generalize?**
A: For the architecture claim, I have two data points: the Hof profile and the Bavaria profile, added with zero code. For the standard-gap findings, generality follows from the standard, not the region — any multi-source system hits the same missing concepts. Full external validity needs a third, foreign region; named as future work.

**Q: What is your hypothesis, and could it have failed?**
A: RQ1's hypothesis — all standardization behaviour in declarative config — was falsifiable and partially *did* fail in interesting ways: temporal alignment and validation had to stay in code because they are invariants, not policy. Knowing which behaviour belongs in config and which does not is itself a finding.

**Q: Why should this be publishable?**
A: The ISM 2025 paper covers prediction; no publication covers standardized exchange of fused road-weather data. The gap analysis is directly usable by the DATEX II community, and the planned paper packages exactly that with the prototype as evidence.

---

## 2. Fusion & data quality

**Q: Priority-list fusion is trivial. Why not something smarter — weighted averaging, Kalman filters, ML fusion?**
A: Deliberate design decision: winter-service operators must be able to explain every published value in one sentence, so auditability was a requirement. Averaging two disagreeing sensors invents a value nobody measured; priority-with-agreement-checking keeps values traceable to a physical sensor. Smarter fusion is possible later — it is one config key plus one strategy class.

**Q: How did you choose the agreement tolerances?**
A: Per field, in config, based on sensor spec sheets and observed cross-source spreads (e.g. air temperature ±1.5 °C between co-located sources). They are declared, not hidden — an operator can tighten them without touching code.

**Q: Tell me about the Kelvin bug.**
A: One upstream feed delivered Kelvin values labelled as Celsius. The cross-source agreement check flagged a ~273-degree disagreement immediately; a single-source pipeline would have published it. It is my strongest evidence that fusion is a data-quality instrument, not overhead.

**Q: Why a 48-hour staleness cutoff and not something else?**
A: It is one line in `fusion.yaml`, chosen to bridge normal outages while excluding dead sensors — we had stations silent since 2024 that would otherwise masquerade as current. The exact number is policy, and the point is that it is *declared* policy, not a buried constant.

**Q: What happens when all sources disagree, or all are stale?**
A: Disagreement: the highest-priority value wins and the output says "sources agree on n of m fields" — the conflict is published, not hidden. All stale: the field is omitted and the segment reports reduced confidence; we never publish a value we cannot timestamp.

**Q: "2 of 4 sources agree" — is that a confidence measure?**
A: No, and I deliberately do not call it one. It is a factual agreement count. Turning it into calibrated confidence requires a statistical model of each sensor's error — named as future work.

**Q: How do you map point sensors onto road segments?**
A: Spatial nearest-neighbour assignment with a distance cutoff (the parent pipeline uses ≤500 m for LoRaWAN), so a sensor only speaks for roads it plausibly represents. Segments without any nearby sensor fall back to the full-coverage source, OpenWeather.

---

## 3. Temporal alignment

**Q: Explain the temporal alignment approach.**
A: Every view is anchored to one reference instant; each source is joined to it with an ASOF join — the most recent reading at or before that instant — plus the staleness cutoff. Result: map, table and XML all describe the same moment, and every response carries "data as of".

**Q: Why is that research and not a bug fix?**
A: Because the naive design — show each source's latest value — is what everyone builds first, and it silently mixes points in time. The generalizable finding is that temporal consistency is part of the data contract of any multi-source standardization layer; it is now also a regression test.

**Q: Why DuckDB for that?**
A: Native ASOF joins over timestamped columnar data, embedded, zero infrastructure. For 1,021 segments and four sources it is far below its limits; the choice is swappable behind the source interface.

---

## 4. DATEX II & standards

**Q: Why DATEX II v3 and not v2, or OCIT, or something simpler like JSON?**
A: Delegated Regulation 2022/670 names DATEX II as the exchange format for the National Access Points, and v3 is the current EN 16157 series. The consumer side is fixed by law; the research question was what it costs a multi-source system to comply.

**Q: The standard has extension mechanisms. Why didn't you just extend it?**
A: A Level-B extension for per-field provenance is exactly the right next step, and the gap analysis is written to be its input. Within one semester, the scope was to characterize the gaps in a working system; drafting the extension is future work, potentially the thesis.

**Q: Why do you publish centroids instead of linear road references?**
A: Honest limitation: segments are lines, and full linear referencing (OpenLR / ALERT-C) was out of scope. `PointByCoordinates` is valid DATEX II and sufficient for the prototype; linear referencing is the named production step.

**Q: How do you set `probabilityOfOccurrence` and why never "certain"?**
A: Fused and partially modelled data is by definition not a certain observation, so I publish "probable" or "risk of". That is what the field exists for; claiming "certain" would be semantically wrong and, for safety data, irresponsible.

**Q: Have you validated against a real National Access Point, e.g. Mobilithek?**
A: No — conformance is proven against the official CEN XSD schemas, which is the technical entry condition every NAP states. An end-to-end submission to Mobilithek is a concrete future step and mostly an organisational one (registration, data offer), not a technical one.

**Q: Is XSD validity the same as semantic correctness?**
A: No. XSD guarantees structure; semantics are covered by the config-driven enum mappings (reviewed against the Bavarian taxonomy definitions) and the test suite asserting specific inputs produce specific DATEX II situations. A formally valid but semantically wrong document is exactly what the tests exist to prevent.

**Q: The 6-class Bavarian taxonomy → DATEX II enums: who decided the mapping, and what if it's wrong?**
A: The mapping is declared in `segment_conditions.yaml` with each decision documented, using DWD/Bavarian winter-service definitions as ground truth. Because it is config, a domain expert can correct it without a release — that is precisely why the mapping is *not* hard-coded.

---

## 5. Architecture & implementation

**Q: Why YAML configuration instead of a rules engine, database, or DSL?**
A: YAML is versionable, diffable, reviewable by non-programmers, and sufficient for declarative policy (priorities, tolerances, mappings). A DSL or rules engine adds power the problem does not need and auditability costs it cannot afford.

**Q: Isn't "zero code changes" just moving complexity into config?**
A: Yes — deliberately. Policy that domain experts must audit and change belongs in config; invariants (validation, temporal alignment) stay in code. The evaluation point is that the second region worked with config only, so the boundary was drawn correctly.

**Q: Why Python/FastAPI? Would this scale?**
A: Python for the xsdata code generation from the official schemas and the data tooling; FastAPI for typed, self-documenting endpoints. At 5.7 ms mean / 6.9 ms p95 per transform, one instance handles far more than 1,021 segments; the service is stateless, so it scales horizontally.

**Q: What do the 50 tests actually cover?**
A: Fusion logic, agreement checking, unit conversions, temporal alignment (the professor's-question regression test), all endpoints, and an XSD conformance matrix across source combinations. They pin behaviour so config changes cannot silently break the standard output.

**Q: What happens when an upstream source changes its schema?**
A: Each source has an isolated input adapter; a schema change breaks exactly one adapter and its tests, never the core. That isolation is a direct consequence of the layered architecture.

**Q: Security, authentication, GDPR?**
A: The prototype serves only environmental sensor data — no personal data, so no GDPR surface. Auth/TLS are standard deployment concerns intentionally out of research scope; the API is designed to sit behind a normal gateway.

**Q: Are you processing live data right now?**
A: The prototype runs on historical exports with 35 reproducible moments — deliberately, because reproducible evaluation needs frozen inputs. The source interface is the seam for live CIVORA feeds; switching is configuration plus credentials, and DKSR's interest makes that step realistic.

---

## 6. Boundary to the parent project (expect this from every professor)

**Q: What exactly is yours, and what is Sonali's / the ISM authors'?**
A: Mine: everything from fused output to Europe — the adapter, fusion engine, temporal alignment, DATEX II serialization, validation gate, dashboard, evaluation. Sonali leads the CIVORA pipeline and ML model; the ISM paper is the institute's published forecasting system. My layer did not exist in either.

**Q: Why should we grade you on a system whose data pipeline you didn't build?**
A: You should grade the layer I built and its findings. In the project's own terms: M1/M2 made the data ML-ready; my work makes the results Europe-ready — a separable, individually evaluated contribution with its own research questions.

**Q: The model accuracy you show — is it valid?**
A: The demo model's ~86 % is illustrative and I flag its temporal-leakage risk myself; proper validation is the parent project's AP5 phase. My claims do not depend on model accuracy — the adapter standardizes whatever the upstream produces, with honest uncertainty labels.

**Q: Doesn't your work depend entirely on the parent project surviving?**
A: The Hof deployment does; the contribution does not. The gaps in DATEX II and the config-driven pattern apply to any regional multi-source system in Europe — that independence is exactly why it generalizes.

---

## 7. Practical & deployment

**Q: Who would operate this in production, and what does it cost them?**
A: Natural home: the CIVORA platform, i.e. DKSR — which is why their architect's review last week matters. Operationally it is one stateless container plus config; the 5.7 ms transform means no meaningful compute cost.

**Q: Are you allowed to republish OpenWeather / DWD data under an EU portal?**
A: DWD data is open (GD-compatible); OpenWeather has licensing limits on redistribution of raw values. In production the adapter would publish *derived* road conditions rather than raw third-party readings, and the per-field provenance makes source filtering a config switch. Genuine deployment question, flagged, not solved.

**Q: What breaks first if this goes to production tomorrow?**
A: Location referencing — consumers doing route matching need linear references, not centroids. Then live-feed hardening (retries, backpressure) and the licensing review. All three are named future work; none invalidates the findings.

---

## 8. Reflection (any professor, often the closer)

**Q: What was the hardest problem?**
A: Temporal alignment. It looks like a display detail and is actually a correctness property; getting one consistent instant across four asynchronous sources changed the core design.

**Q: What would you do differently?**
A: Start with the moment-based temporal model from day one instead of retrofitting it, and involve DKSR's architect earlier — the stakeholder review sharpened priorities more than any literature did.

**Q: What did you learn beyond the technical result?**
A: That standards are hypotheses about data, and building is how you test them. The most valuable outputs were the mismatches — things no document told me and the artifact forced me to discover.

**Q: Next steps / thesis?**
A: Three-step line: ingest the +3 h/+18 h forecasts as DATEX II forecast situations, integrate live CIVORA feeds, and draft the provenance extension — the last being a natural master's thesis, feeding the planned paper that includes this prototype.

---

## Quick facts card (memorize)

| Fact | Value |
|---|---|
| Segments / sensors / sources | 1,021 / 177 / 4 |
| Transform latency | 5.7 ms mean · 6.9 ms p95 |
| XSD conformance | 100 %, validated per request (`x-validation-status: valid`) |
| Tests / moments | 50 automated tests · 35 reproducible moments |
| Generated classes | 913 (xsdata, official EN 16157 schemas) |
| Config artifacts | `fusion.yaml` · `segment_conditions.yaml` · `bavaria.yaml` (0 LOC region add) |
| Source histories | SWS Nov 2022 · OpenWeather Jul 2024 · DWD Nov 2024 · LoRaWAN Sep 2025 |
| Regulation | EU 2022/670 under ITS Directive 2010/40/EU — DATEX II on TEN-T by 2027 (Hof: A9/A93) |
| Staleness cutoff | 48 h, declared in config |
| Ice event demo moment | 24 Nov 2025, 03:00 — 643 segments icy |
