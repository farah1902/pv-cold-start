# Decisions

One entry per choice, numbered D01, D02, … in order; never renumbered. **[guide deviation]** marks a change to the
plan in `docs/research_guide.md`. D01–D07 answer the guide's open decisions D1–D7 (guide §9) in the same order.

### D01 — Data corrections accepted: inverter units, AC rating from the model name, DC from modules, first day of telemetry, errata [data, Phase 0]
- **Request or reason:** guide §9, decision D1. Approved by the author on 18 Nov 2026.
- **Change:** the unit of analysis is the inverter (44 units, 5-min files aggregated to 15 min). P_AC comes from the
  inverter model name and is cross-checked against the 99.9th percentile of observed power; P_DC = number of modules ×
  module watt-peak. Units with a metadata error keep the empirical AC limit, are left out of the DC/AC-prior test and
  stay in the forecasting test with the g = 1 prior. The errata of guide §2 are published with the code. The start
  date rule is refined by D08.
- **Alternatives considered:** the metadata rated power (it is the AC rating, although the data paper calls the total
  "2,230.8 kWp"); the metadata connection date (it differs from the first telemetry by up to 113 days, F06).
- **Evidence:** guide §2; F06, F11. **Code:** `src/pvcold/prep` (NB1, NB2), not yet written.

### D02 — The DC/AC gain prior is contribution 2; G0, G1 and G2 are tested [method, Phase 0]
- **Request or reason:** guide §9, decision D2. Approved by the author on 18 Nov 2026.
- **Change:** the prior ĝ = β r T (guide §3.5) is a contribution. G0 (g = 1), G1 (β r) and G2 (β r T, with the Perez
  transposition factor) are compared on the validation units; G2 is kept only if it beats G1 there.
- **Evidence:** the pilot figures quoted in the guide are not from this repository and are not citable (see
  `results_summary.md`). **Code:** `src/pvcold/fleet` (NB3), not yet written.

### D03 — Horizons of 2–6 h use the fleet only, with the limitation stated [scope, Phase 0]
- **Request or reason:** guide §9, decision D3. Approved by the author on 18 Nov 2026 ("ok").
- **Change:** no weather-forecast or satellite input enters the main model at any horizon. The paper states that 2–6 h
  skill is bounded by what the fleet's own history can predict. The optional historical Open-Meteo forecast baseline
  (guide §6, item 16) is not done.
- **Alternatives considered:** adding a weather-forecast baseline (more downloads, and it weakens the "no external
  input" thesis).

### D04 — Execution: light notebooks locally, heavy runs on Google Colab; the local repository is the master copy [environment, Phase 0]
- **Request or reason:** guide §9, decision D4. The author, 18 Nov 2026: "fine, Colab is ready".
- **Change:** the agent writes all code. Data audit, preprocessing and index notebooks run locally (Python 3.12.1).
  The LightGBM bank (NB5) and the TCN ablation (NB5b) run on Colab, from a Google Drive mirror of this repository, as
  in the grid project. Each run is resumable and writes `summary.json` with versions and backend.

### D05 — Target journal: *Solar Energy* [venue, Phase 0]
- **Request or reason:** guide §9, decision D5. Approved by the author on 18 Nov 2026.
- **Change:** the paper is written for *Solar Energy* (Elsevier). Its Guide for Authors (length, abstract,
  highlights, graphical abstract, declarations) is still to be fetched and recorded in `CLAUDE.md` before writing.

### D06 — Conformal cold-start intervals and the past-weather ablation are adopted [method, Phase 0]
- **Request or reason:** guide §9, decision D6. Approved by the author on 18 Nov 2026 ("yes to both").
- **Change:** (i) conformalised quantile regression (Romano et al. 2019, to verify at citation) calibrated on pseudo
  cold starts, where each donor is treated as new before the event start and scored with its prior gain (guide §6,
  item 14); (ii) an ablation adding past temperature, relative humidity and visibility (guide §6, item 15).

### D07 — Morocco: Safi external case and validation kit in this paper; the virtual fleets move to the follow-up paper [scope, Phase 0] [guide deviation]
- **Request or reason:** guide §9, decision D7, and the agent's recommendation of 17 Nov 2026. The author, 18 Nov 2026:
  "ok, tell me what you want and I will give it to you".
- **Change:**
  - *In this paper:* the Safi rooftop external case (M2: transfer levels T0, T1 and T2; fleet vs the on-site reference
    cell), the validation kit and the bridge equation (M3), and the regional PV-density areas used in the Introduction
    and Discussion (guide §8, uses 1 and 3).
  - *Moved to the follow-up paper:* the Benguerir virtual fleet, the regional virtual fleet, the distance-weighted local
    fleet index and the donor-radius test, notebooks NB8b and NB8c, Figs. 11 and 12, the virtual-fleet success
    criterion (guide §1), use 2 of the density areas, and download rows 1, 4 and 5 (guide §8).
  - The guide of 18 Nov still lists these items; this decision overrides them.
- **Alternatives considered:** keeping the virtual fleets in the supplement.
- **Reason:** their inputs are not in hand (the CAMS all-sky grid and the 8 Open-Meteo cluster points); 3–5 km
  satellite pixels cannot represent short-range cloud differences; and the paper's claims rest on real starts.

### D08 — Event list: 14 scored events with observed starts, 3 sensitivity events, 2 removed [data, Phase 0]
- **Request or reason:** review audit of 18 Nov 2026 (`docs/history/review-audit-18-nov.md`), approved by the author
  and applied by the author to the guide (§2, Start dates and events).
- **Change:**
  - An event starts at the earliest production in any file, site or inverter. The start is observed only if that file
    begins before the unit produces (a mid-month first day with a morning ramp, or a file that precedes the others).
    A file that begins on the 1st of a month while already producing makes the start left-censored.
  - **Scored (14):** SQ Block S, Zone A5, SQ Block R, Zone A7, Zone A6, Zone J2 (from 2021-11-13; site series as target
    until its inverter file starts on 2021-12-08), Indoor Sports Centre, Zone D (both inverters, station level, from
    2022-01-19, site series as target), Library, UG Hall 8, UG Hall 9, Zone A2 inverters 2–3, SQ Block P, Shaw
    Auditorium.
  - **Sensitivity (3), left-censored:** Wong Check She, Zone J1, Zone L2.
  - **Removed (2):** Zone D inverter 1 (its file marks the end of an outage, not a new unit), S H Ho Sports Hall
    (anomalous first months and a left-censored start).
  - A donor must have started at least 14 full days before the event.
- **Evidence:** F03, F04, F05, F06, F07, F16.

### D09 — Primary horizon: 1 h, fixed before scoring [statistics, Phase 0]
- **Request or reason:** review audit of 18 Nov 2026, approved by the author; guide §1 and §4.4.
- **Change:** every hypothesis test runs at 1 h (one-sided exact Wilcoxon, n = 14). The other five horizons are
  secondary, with Holm correction.

### D10 — Drifted window: effect sizes, plus per-event Diebold–Mariano tests; boundary rule fixed before scoring [statistics, Phase 0]
- **Request or reason:** review audit of 18 Nov 2026, approved by the author; guide §4.4.
- **Change:** with about 5 drifted events no Wilcoxon test can reach significance (F12). The paper reports
  Hodges–Lehmann differences with day-block bootstrap intervals and the number of events won. Significance comes from
  per-event Diebold–Mariano tests at 1 h, with Holm correction across the drifted events. The drift boundary comes from
  PELT on the daily log-ratio of measured GHI to the fleet proxy k̂ G_cs. An event is drifted if at least half of its
  90 test days fall after the boundary. Both rules are fixed before any test event is scored.
- **Evidence:** F12.

### D11 — The 2021–2022 sensor period is called "stable", not "healthy" [wording, Phase 0]
- **Request or reason:** agent's remark of 17 Nov 2026; review audit of 18 Nov 2026, approved by the author.
- **Change:** "stable" vs "drifted" everywhere. In 2021–2022 the sensor reads about 0.8 of clear-sky, which is not
  "healthy" (F09).

### D12 — Daily window: issue times 06:00 to 17:55 minus the horizon; common target window 12:00–17:55; site files as an evening sensitivity check [protocol, Phase 0]
- **Request or reason:** F01; agent's recommendation of 17 Nov 2026; review audit of 18 Nov 2026; the author, 18 Nov
  2026: "yes, do it".
- **Change:** forecasts are issued from 06:00 to 17:55 − h, so a 6-h forecast is issued at 11:55 at the latest.
  Comparisons across horizons use the common target window 12:00–17:55, which every horizon reaches. Full-window scores
  per horizon are secondary. A sensitivity run uses the site files (00:00–23:45) to measure what the missing evening
  changes. Implemented in NB2 and NB6.
- **Evidence:** F01.

### D13 — Timestamps are parsed with an explicit two-format parser that stops on any failure [data, Phase 0]
- **Request or reason:** F02; review audit of 18 Nov 2026.
- **Change:** `%Y-%m-%d %H:%M:%S` and `%Y/%m/%d %H:%M` are tried explicitly. Any unparsed timestamp raises an error.
  No automatic format inference.

### D14 — CAMS is downloaded again with sky type "Observed cloud"; A9 and the HKUST satellite check depend on it [data, Phase 0]
- **Request or reason:** F08; review audit of 18 Nov 2026; guide §8 (note of 18 Nov).
- **Change:** rows 2 and 3 of the guide's download table are requested again with "Observed cloud" (it also returns
  the clear-sky columns). Safi runs to 2018-12-31. If CAMS has no all-sky data for Hong Kong, baseline A9 and the
  satellite check of the HKUST sensor are dropped. The McClear files stay as a second clear-sky model.

### D15 — The project gets its own repository; data are moved into the roadmap layout and never committed [repository, Phase 0]
- **Request or reason:** on 17 Nov 2026 `git rev-parse --show-toplevel` in `pv paper/` returned `C:/Users/Dell`, a
  repository whose remote is an unrelated project (ESA_LandCover_Streamlit). The author, 18 Nov 2026: "ok, create the
  repo please".
- **Change:**
  - `git init` in `C:\Users\Dell\Desktop\phd_ehtp\pv paper`; private GitHub repository `farah1902/pv-cold-start`.
  - Data moved to `data/raw/` and `data/external/` (old → new paths in `data/README.md`). The data are git-ignored
    (1,673.8 MB, above GitHub's limits). `data/MANIFEST_sha256.csv` (165 files) is committed and checked by
    `tools/make_data_manifest.py --check`.
  - The guide moved byte-for-byte to `docs/research_guide.md`; earlier documents went to `docs/history/`.
  - Repo-local `core.autocrlf=false`, so working files and committed files have the same bytes.
- **Code:** `tools/make_data_manifest.py`.

### D17 — CAMS all-sky files received: baseline A9 and the satellite check of the HKUST sensor stay [data, Phase 0]
- **Request or reason:** D14's condition is met: the author downloaded the "Observed cloud" files on 18 Nov 2026 and
  they cover Hong Kong (F17).
- **Change:** `data/external/cams/observed/` is the satellite source for A9 and for the independent check of the
  sensor drift. The McClear files stay as a second clear-sky model. A duplicate copy of the HKUST data paper (same
  SHA-256) was deleted from the folder root. The Safi companion article to request is SETA 43 (2021) 100915, not the
  guide's "Energy Reports 2020" (F18).

### D18 — Hidden-unit cold starts form a second test bed, fixed before scoring [protocol, Phase 0]
- **Request or reason:** agent's proposal 1 of 18 Nov 2026; the author: "yes to 1".
- **Change:**
  - Long-running inverters (about 35, counted in NB2) are split into 5 groups by station, with all inverters of a
    station in the same group.
  - For each group and each pseudo-start date, the index is built without the group and donor gains are fitted
    before the date. Each unit of the group is forecast from its DC/AC prior, with the same code and frozen
    configuration as the real events.
  - One pseudo-start date in the stable window and one in the drifted window, chosen in NB2 before scoring.
  - Two uses: (i) statistical power for the sensor comparison after the drift (about 35 units instead of 5);
    (ii) real starts vs hidden-unit starts on the same days, which measures how much the usual "hide a station"
    protocol flatters results (contribution 3).
  - All units share one sky, so the inference resamples days (block bootstrap), not units.
- **Alternatives considered:** leave-one-unit-out (about 35 times more model fits for little gain).

### D19 — The satellite is used twice: a second drift reference and a same-time satellite row [protocol, Phase 0]
- **Request or reason:** agent's proposal 2 of 18 Nov 2026; the author: "yes to 2". Possible because of D17.
- **Change:**
  - PELT also runs on the daily log-ratio of measured GHI to CAMS all-sky GHI. The fleet-based boundary of D10
    still defines the windows; the agreement of the two dates is reported. The same comparison tests whether the
    2021–2022 level of about 0.8 comes from the sensor or from the clear-sky model.
  - A same-time satellite clear-sky index row sits next to the fleet oracle A7: "40 inverters or one satellite
    pixel as a virtual pyranometer".
  - CAMS steps with reliability < 1 are flagged.

### D20 — The release adds a drift flag and a fleet-derived irradiance series for the HKUST dataset [release, Phase 0]
- **Request or reason:** agent's proposal 3 of 18 Nov 2026; the author: "yes to 3".
- **Change:** the sensor package of guide §4.5 gains (i) a daily flag of the drift periods and (ii) the fleet-derived
  GHI proxy k̂ G_cs at 15 min, so that other users of the dataset can avoid the drifting pyranometer.

### D21 — A git tag freezes the protocol before any test event is scored [protocol, Phase 0]
- **Request or reason:** agent's proposal 5 of 18 Nov 2026; the author: "yes to 5".
- **Change:** once the validation runs fix the configuration, the tag `protocol-freeze` is pushed with the frozen
  configuration hash; the paper cites its commit and date.

### D22 — The prior's empirical-Bayes weight is reported in days [reporting, Phase 0]
- **Request or reason:** agent's proposal 6 of 18 Nov 2026; the author: "yes to 6".
- **Change:** w0 = s1²/σp² (guide §3.6) is reported as "the nameplate prior is worth about w0 days of the inverter's
  own data", with its spread across events.

### D23 — Deep-learning rows: four modern baselines replace the TCN [models, Phase 0] [guide deviation]
- **Request or reason:** the agent proposed Chronos-2 and TimeXer on 18 Nov 2026. The author: "I agree for
  Chronos-2, TimesFM, TabPFN-TS, also for TimeXer".
- **Change:** the TCN ablation A6 (guide §5.4) is dropped. Baselines:
  - zero-shot foundation models with known future covariates: Chronos-2, TimesFM 2.5 and TabPFN-TS;
  - trained exogenous transformer: TimeXer, given the sun geometry through its future-exogenous variant (its
    Appendix H.1) and trained with the 9-quantile pinball loss.

  All get the same information set as the main model. Packages, licences and local inference (no data sent to a
  cloud API) are checked at NB0. If one model is too slow at full scale, a fixed subsample of issue times is chosen
  on the validation units before scoring.
- **Evidence:** F19, F20.

### D24 — The author's own named transformer is built as a novel index forecaster [models, Phase 0] [guide deviation]
- **Request or reason:** the author, 18 Nov 2026: build "another advanced transformer-based time series forecaster,
  more optimized than TimeXer, with our proposed name as a novel approach … I need novelty".
- **Change:** a new transformer for the campus index. This overrides guide §1 ("no new deep architecture") and the
  §6 writing rule against "a novel architecture". The design, name and selection rule were proposed on 18 Nov 2026
  and **approved the same day (D25)**:
  - **Design:** censoring-aware donor tokens, coordinate-free donor-set attention, a solar-time daylight encoder,
    horizon queries built from the known future sun geometry, and a monotone 9-quantile head.
  - **Name:** KappaFormer, HelioSet or SkyFleet.
  - **Selection rule:** built and tuned on the validation units only. It becomes the main index forecaster only if it
    beats LightGBM there at 1 h, before the protocol freeze (D21).
- **Evidence:** F20 (closest work and the gap).

### D25 — Name PVSetFormer, new working title, rules R1 and R2 approved; the research guide revised [models, writing, Phase 0] [guide deviation]
- **Request or reason:** the author, 18 Nov 2026: name "PVSetFormer"; R1 supported ("it's important to help our model
  many times to beat any other models, this is the real work"); R2 "strongly supported"; "the methodology must
  change … change the methodology and the title".
- **Change:**
  - **Name:** PVSetFormer. No model of that name was found (F20 searches plus one more on 18 Nov; re-check before
    submission).
  - **Working title:** *PVSetFormer: forecasting new rooftop PV inverters from day one, without history or a
    pyranometer.* If R1 keeps LightGBM as the main model, the fallback title is *Forecasting new rooftop PV inverters
    from day one, without history or a pyranometer: a causal fleet index and a nameplate gain prior.*
  - **R1:** PVSetFormer may go through as many design rounds as needed, on development data only: the 10 validation
    units and the fleet index before the first test event (2021-10-05). Every variant tried is logged as a decision,
    and their number is reported. All models get the same hyperparameter-search budget. PVSetFormer becomes the main
    index forecaster only if it beats LightGBM on the validation units at 1 h, before the `protocol-freeze` tag (D21).
  - **R2:** TimeXer gets the same per-donor series; PVSetFormer is also run on the fleet summary only (A6e).
  - **Guide revised at the author's request:** 42 edits, applied all-or-nothing by a script, integrate D07 and
    D17–D25. The previous version is `docs/history/methodology_2026-11-18_audit.md`; 978 → 1,007 lines.
- **Consequence:** D24 is approved (no longer pending).

### D26 — Implementation choices of NB0 and NB1 [data, Phase 2]
- **Request or reason:** the author asked to start NB0 and NB1 (18 Nov 2026).
- **Change:**
  - Package `src/pvcold/`: `config.py` (every constant of the guide, with its source), `io_hkust.py` (two-format
    timestamp parser, readers, CAMS reader in W/m², Brick parser without rdflib, explicit AC table of 23 model
    strings, name alias for Indoor Sports Centre), `audit.py` (inventory, start rule, reproductions, sensor checks,
    draft figures, all-or-nothing outputs).
  - Notebooks are generated by `tools/make_nb0.py` and `tools/make_nb1.py` and executed with nbconvert.
  - Clear sky in the audit: pvlib Ineichen at the campus coordinate, altitude 124 m (median of the station altitudes).
  - Audit fleet proxy: median over the 10 units online before 2021-05-22 of the daily normalised yield
    (06:00–17:55), on days with at least 6 such units and 90% valid slots. It serves the audit only; NB3 builds the
    real index.
  - Days with sensor / CAMS below 0.3 count as a dead sensor and are left out of the change-point search.
  - The audit-level drift date comes from a one-break binary segmentation. PELT with a 2σ² log n penalty
    over-segments (F23), so the final boundary rule of D10 is fixed in NB3, before scoring.
- **Evidence:** `results/nb0_setup/`, `results/nb1_audit/`; F21–F24.

### D27 — Library moves to the sensitivity set: 13 scored events, 4 sensitivity events [data, Phase 2]
- **Request or reason:** F22. Both Library files begin on 2022-06-01 and already produce that day, so the written D08
  rule calls the start left-censored. The connection date (one day earlier) cannot prove the start, because units
  produced before their connection date elsewhere on campus (UG Hall8: 55 days). The agent recommended the move; the
  author, 18 Nov 2026: "ok move Library to the sensitivity set, leaving 13 scored events".
- **Change:** scored events: 13 (8 stable, 5 drifted). Sensitivity events: Library, Wong Check She, Zone J1, Zone L2.
  The model-fit count is unchanged (17 events). Primary test: n = 13; the smallest one-sided exact p is
  1/8192 = 1.2 × 10⁻⁴. Updated in the guide, `config.py`, `CLAUDE.md`, `README.md` and the handoff.

### D28 — Zone A2 inverters 2 and 3 enter the DC/AC prior test [method, Phase 2] [guide deviation]
- **Request or reason:** F21. Their metadata are complete (SE55K and SE50K with JKM410N modules, DC/AC 1.33), and
  both peak within 2% of their AC rating. The agent recommended it; the author, 18 Nov 2026: "include them".
- **Change:** the only capacity addition is tested with the prior (G1, G2), not with g = 1. Guide §4.3 and the event
  table now say so; the guide's erratum "Zone A2 has no module blocks" is replaced by the Zone D inverter-2 error.

### D29 — Implementation choices of NB2 [data, Phase 2]
- **Request or reason:** the author asked to move to NB2 (18 Nov 2026).
- **Change:**
  - **AC corrections:** Indoor Sports Centre 33.3 kW (station rating, standard SE33_3K, observed clip 33.4 kW).
    Zone D inverter 2 50 kW, from its observed limit (49.9 kW). That last value uses the unit's own data, the
    "own-peak" trap, so NB6 adds a sensitivity run without the two metadata-error events (Indoor Sports Centre,
    Zone D). Both stay out of the DC/AC prior test (D01).
  - **Time base:** the shift that maximises the correlation with clear sky (F26): +3.0 min for 5-min values; 15-min
    slots at slot + 8 min; site series in the same slots.
  - **Quality control:** flags are kept as a bitmask (night, negative, frozen ≥ 1 h, y > 1.05, outage = zero power
    while the crude fleet index exceeds 0.3 and G̃ > 0.1). Only negative and night values are set to missing.
  - **Aggregation:** 15-min mean of the three 5-min values, valid if at least 2; flags OR-ed.
  - **Daylight** for the start rule and for valid days means G̃ > 0.1. A valid day has at least 70% valid daylight
    slots.
  - **Event starts:** the approved observed starts (D08, D27); validation units start at their first row. Donors use
    the 70% rule start.
  - **Event targets:** Zone J2, Zone J1 and Zone L2 use their site series until the inverter file starts. Zone D is
    station level (site series, AC 83.3 kW). Multi-inverter events sum their inverters.
  - **Hidden-unit test bed (D18):** pseudo-starts on 1 April 2022 and 1 April 2023, the same season in both windows.
    Units must have been online for at least 90 days, have at least 30 valid days in the window, and not be inside
    their own real event window. Stations go to 5 groups balanced by unit count (greedy, seed 20261118).
  - **Outputs:** the Parquet panels (25 MB, rebuilt by NB2 in about 30 s) are git-ignored; CSV, JSON and figures are
    committed.
- **Evidence:** `results/nb2_panel/`; F25–F27.

### D30 — Implementation choices of NB3 [method, Phase 4]
- **Request or reason:** the author asked for NB3 (19 Nov 2026).
- **Change:**
  - Donor slots with any QC flag are left out of the index and of the gain fits.
  - The censored index is minimised on a 0.005 grid, then a local 0.0005 grid. This stands in for the guide's
    golden-section refinement, with the same precision.
  - In the alternating gain fit, the leave-one-out index is the median index for both estimators, so both share
    the donor gains and differ only at the index step. An exact vectorised leave-one-out median was checked against
    `nanmedian` (identical to machine precision, 24 times faster).
  - Gains are fitted from the unit's rule start to the event start and fixed there (cold-start mode).
  - Transposition (G2): clear-sky Perez, albedo 0.2, over the event's 90-day window, with equal module shares for
    slash orientations; T = 1 for flat and "Mixed".
  - Empirical-Bayes weights: one-day gains of the donors over the last 60 days, against the leave-one-out index.
  - Drift boundary (D10): PELT on the daily log-ratio of the sensor to the NB1 fleet proxy (10 fixed long-running
    units), dead-sensor days removed, penalty raised geometrically until one change point remains. A free PELT
    over-segments this series (F23).
  - **The freeze has two parts.** Part 1 (this notebook) fixes the index, gains, prior and drift boundary. Part 2
    fixes the forecasters after the LightGBM and PVSetFormer development on validation data. The `protocol-freeze`
    tag (D21) comes after part 2, before any test event is scored.
  - The frozen YAML excludes its writing time, so its hash depends on content only.
  - All outputs are written with LF line endings (CSV, YAML, JSON), so hashes match on every OS. Earlier runs
    wrote CRLF on Windows, and the frozen-config hash did not match its own file; NB1 and NB2 outputs keep CRLF
    until their next run.
  - Guard: `fleet.validation_scores` refuses to read any target that is not a validation unit.
- **Evidence:** `results/nb3_index/`; F28-F32.

### D31 — Selections under the pre-registered rules, and part 1 of the frozen configuration [method, Phase 4]
- **Request or reason:** NB3 rules 1-4, written in the notebook before any number was computed.
- **Change:** k_min = 0.3; index estimator = censored; prior = G2, with G0 for the two
  metadata-error targets; drift boundary = 2023-02-17. Frozen configuration part 1:
  `results/nb3_index/frozen_config_part1.yaml`, sha256 `cb671b7f67138e7e82eeece27241e60a37284fd124946ac72d42e9a2daa80252`.
- **Evidence:** F28-F31.

### D32 — Implementation choices of NB4: sensor and satellite index sources [method, Phase 4] [guide deviation]
- **Request or reason:** the author asked for NB4 (19 Nov 2026).
- **Change:**
  - **Time base (addition).** The pyranometer and CAMS are aligned to the panel clock by the whole-minute lag that
    maximises the correlation of the within-day 5-min changes of their clear-sky index with those of the NB2 fleet
    index: pyranometer 3 min (its value labelled t belongs to panel time t + 3), CAMS 5 min. The guide's clear-day
    method (§2 step 1) has no interior peak for one sensor (F33). Aligning a baseline can only help it.
  - **Physical limits [guide deviation].** The lower limit (−2 W/m²) applies to the raw reading, as in the guide. The
    BSRN upper limit applies to the calibrated value: on raw readings it would remove about 2,300 real minutes in
    May–October 2023, when the sensor reads about 1.35 times too high; after calibration 12 remain in those months
    (F34). Spikes (up to 3,600 W/m²) are removed by this limit; no separate spike filter (guide §2 step 8 lists one,
    §3.10 assigns spikes to the BSRN limits).
  - **Night offset.** Night minutes within the BSRN band (−2 to 50 W/m²) over the 7 days before the day; at least 360
    minutes, otherwise the last offset is kept.
  - **Dead days (addition).** A day whose sensor irradiation is below 3% of clear sky (elevation above 10°, at least
    300 minutes) gets no corrected value and no calibration weight. The rule uses the sensor only, because A4b may
    not use the fleet or the satellite.
  - **Clear-sky detection.** pvlib `detect_clearsky` with its defaults, one calendar month per call, so its
    rescaling factor is fitted per month and uses no later data.
  - **Calibration guards (addition).** A month's factor is valid with at least 120 clear minutes (zenith below 70°)
    and 0.5 ≤ c ≤ 2; month m applies the latest valid earlier month. Without the guards the detector's rescaling
    locks onto dead-sensor or overcast stretches (c = 44.9 in March 2021, 2.56 in June 2021; F34).
  - **15-min values.** At least 10 valid minutes; k = G / G_cs at the panel slot (the Ineichen clear sky of the
    fleet index); missing where G̃ ≤ 0.05; bounded to [0, 1.5] except the raw sensor (A4).
  - **Gains (guide §4.2 step 5).** Donor gains are refitted against each source with the frozen part-1 gain-fit rule
    (k_min 0.3, QC-clean slots, G̃ > 0.2, from the donor's rule start to the event start), on a 0.3–3.0 grid and
    without renormalisation, because the gain carries the source's calibration. The prior is the frozen G2; for the
    metadata-error targets, G0 = the median donor gain, the analogue of the fleet's g = 1. The fit sums the loss by
    day, so all events reuse one pass per donor; on the first scored event it equals `fleet.fit_gain` for all 20
    donors.
  - **Satellite index.** NB4 also builds the CAMS index for A9 and A9n (reliability 1 only, same clear-sky
    denominator, lag 5 min) with its refitted gains: the same kind of index swap.
  - **Not here.** The fleet-derived GHI proxy of D20 is a release item, assembled at NB9 from the NB3 index. The
    hidden-unit test bed (D18) gets its gains with its runs in NB5 (`sensor.external_gains` takes any donors and
    dates).
  - The settings are in `results/nb4_sensor/sensor_config.yaml` (sha256 `4c47bfac9fa359fe…`); they enter the frozen
    configuration part 2 and the `protocol-freeze` tag (D21).
- **Evidence:** `results/nb4_sensor/`; F33–F37.

### D33 — Implementation choices of NB5a: forecasting development before the freeze [method, Phase 5] [guide deviation]
- **Request or reason:** the author asked for NB5 (19 Nov 2026).
- **Change:**
  - **NB5 is split [guide deviation].** NB5a develops the forecasting pipeline on the 10 validation units: the
    LightGBM setting (guide §5.2), every simple baseline, the composition with the prior, the scores and the R1
    reference. The test run of guide NB5 (all models on the 17 events and the hidden-unit test bed) comes after the
    `protocol-freeze` tag: R1 compares PVSetFormer with LightGBM on validation before the freeze (D25), and no test
    event may be scored before it (D21).
  - **Tuning index.** The censored index of the validation unit with the most donors (SQ Apartment25-36, 16
    donors), data before 2021-10-05. Folds: targets in July, August and September 2021, expanding training from
    15 May 2021. Ties are broken toward the guide's starting values (31, 0.03, 100), parameter by parameter, then
    toward fewer leaves. This completes rule 1, which only covered a tie with the starting point, after
    num_leaves 31 and 63 tied exactly (identical models, F42); the validation scores are the same either way.
  - **Features (guide §3.7).** Computed on the full 15-min grid with the night left empty, so no lag crosses the
    night: 16 lags, 1-h and 2-h means (at least 2 and 4 values), 1-h standard deviation (at least 3), last change,
    sigma, c, n, the index at the target slot one day earlier, and the 8 terms of the future geometry: 32 features.
  - **Pairs.** Training pairs obey the issue rule (G̃ > 0.05, n ≥ 8 unclipped donors, index present) and the target
    rule (target slot at most 17:45, G̃ > 0.02), from 15 May 2021, with targets before the origin. Each origin
    forecasts the issue times in [origin, min(origin + 30 days, start + 90 days)).
  - **LightGBM.** Early stopping on the last 20% of the window (by time), then a refit on the whole window with the
    best number of rounds: the guide does not say whether to refit, and the refit keeps the latest days, which
    matter most in a cold start. One thread per fit, deterministic, fixed seed; fits run in parallel with joblib,
    which is installed with scikit-learn (no new package).
  - **Baselines.** Every model yields 9 index quantiles and is composed the same way; point forecasts are point
    masses. A0 and PeEn: empirical quantiles of the index at the target slot over the previous 60 and 20 days (at
    least 10 days). CLIPER: least-squares persistence weight on the training pairs, bounded to [0, 1], with A0's
    median as climatology. A5: 50 nearest training states over the 32 standardised features, missing values at the
    training mean. A7: the same-time index (oracle).
  - **Composition (guide §3.8).** Stratified index levels; the gain draws use the same levels in a fixed random
    order (seed 20261118), so index and gain draws are independent and both stratified. Gain members = prior × the
    empirical quantile of B / median(B); for the metadata-error targets (prior G0) the donor gains are used.
  - **Scoring.** Slots where every model has a forecast and the observation exists; QC-flagged slots are kept (guide
    §2); full window and common window 12:00–17:55 (D12).
  - **R1 metric, fixed before the run:** the median over the 10 validation units of the nRMSE at 1 h (full window,
    member mean, common slots). PVSetFormer must be lower.
  - The LightGBM setting is written to `results/nb5a_dev/lgb_config_part2a.yaml` (sha256 `d03bb0b86827009e…`). It
    joins the frozen configuration part 2 at the tag.
- **Evidence:** `results/nb5a_dev/`; F38–F42.

### D34 — LightGBM forecasts the change of the index from persistence [method, Phase 5] [guide deviation]
- **Request or reason:** the first NB5a run, with the bank of guide §5.2 forecasting the index level, barely beat
  persistence and lost to CLIPER on the validation units. The four LightGBM variants below were then compared on the
  same units (`NB5a_variants`, development data only).
- **Change:**
  - Each LightGBM model forecasts k(t + h) − k(t), and k(t) is added back. This stays inside the guide's
    formula f(s_t, u_{t+h}), since k(t) is part of the state; trees represent "persistence plus a correction" far
    better than the level when the history is short.
  - Variants at 1 h, validation median nRMSE (units beating CLIPER): level 0.1913 (2 of 10), **change 0.1815
    (9 of 10)**, change with pooled horizons 0.1873 (3 of 10), level with pooled horizons 0.2032 (2 of 10). Pooling
    hurts, so one model per horizon and quantile stays.
  - Rule 1 was re-run for the adopted target; it chose num_leaves 31, learning rate 0.05, min_data_in_leaf 200.
  - Four LightGBM development rounds are counted (level, change, level pooled, change pooled). The anchor belongs
    to the shared forecasting interface and is recommended for PVSetFormer and TimeXer.
  - The first run's outputs were replaced; its validation numbers are reproduced by the `level` variant in
    `results/nb5a_variants/`.
- **Evidence:** `results/nb5a_variants/`, `results/nb5a_dev/`; F39.

### D35 — Conformal calibration on pseudo cold starts (D06 implemented) [method, Phase 5]
- **Request or reason:** NB5a's 80% intervals covered only 0.63–0.71 (F40); the author asked to continue with the
  conformal calibration (20 Nov 2026).
- **Change:**
  - **Calibration set.** For each event, origin and horizon: pseudo cold starts of the event's donors (clean-metadata
    donors for a G1/G2 target, all donors for a G0 target), each with its leave-one-out prior and uncertainty set.
    Their index forecasts are the early-stopped LightGBM models' predictions on the last 20% of the training pairs:
    out of sample for those models, already computed in every fit, and available even for the shortest validation
    histories (median 12 calibration days).
  - **Approximation, stated:** the donor is still inside the event's index; only its prior is leave-one-out. Its own
    power weighs about 1/n in the index. The pseudo cold starts' raw 80% coverage at 1 h (0.714) equals the true
    cold starts' raw coverage on the validation units (0.714), so the approximation does not visibly flatter the
    calibration.
  - **Score.** CQR (Romano et al. 2019; to verify at citation) per horizon and per central interval (80, 60, 40 and
    20%), normalised by G̃(t + h), so the widening follows the clear-sky level. The correction is the
    ⌈(1 − α)(n + 1)⌉-th smallest score; with fewer than 50 scores there is none (never the case on validation). The
    median and the point forecast are unchanged; the quantiles are sorted and bounded to [0, 1.05].
  - **Scope.** The main model gets the layer. Every trained index forecaster (PVSetFormer, TimeXer) gets its own,
    from its own early-stopping predictions; the simple baselines stay raw.
  - **Keep rule, fixed before the run:** kept if, on the validation units, the median PICP80 at 1 h moves closer to
    0.80 and the median IS80 at 1 h does not rise. Met: kept.
  - Settings in `results/nb5a_conformal/conformal_config_part2b.yaml` (sha256 `c68d5a3aa17a6806…`); they join the
    frozen configuration part 2.
- **Evidence:** `results/nb5a_conformal/`; F43.

### D36 — PVSetFormer development protocol under rule R1 [method, Phase 5]
- **Request or reason:** the author: "start PVSetFormer" (20 Nov 2026), under rule R1 (D25): as many design rounds as
  needed, on development data only, every variant logged, the same tuning budget as LightGBM.
- **Change:**
  - **Model** (`src/pvcold/setformer.py`, guide §5.4). The inputs are donor tokens over the last 4 h in four 1-h
    patches: each donor's implied index κ_d = y_d / (g_d G̃), capped at 2, plus its clipping and validity flags. Static
    features: gain, DC/AC ratio (0 without clean metadata), metadata flag and tilt class. The layers are, in order:
    - set attention across the donors online, per patch;
    - attention pooling to 4 sky tokens;
    - a causal temporal encoder with sun-geometry positions;
    - a decoder with 6 horizon queries (future geometry, the index one day earlier);
    - a monotone 9-quantile head on the change from persistence (as LightGBM, D34), zero-initialised so that
      training starts at persistence.
  - **Training.** Pinball loss and AdamW. Early stopping on the last 20% of the training issue times (by time), then
    a refit on all of them for the best number of epochs; the early-stopped model's predictions on that 20% are the
    conformal calibration set (D35). Interface, issue rules, horizons, origins and composition with the prior are
    NB5a's. Options added by later variants default to off and are created after the existing layers, so earlier
    variants reproduce exactly (checked: V1 retrained, max difference 0.0 over 5,060 forecast rows).
  - **Round runner** `tools/pvsf_dev.py`. One round is every validation unit and origin, for n seeds. Scores come from
    exactly the slots NB5a scored (an assertion stops the run otherwise), so the LightGBM numbers compare directly.
    Output goes to `results/nb5c_variants/<variant>/` plus one row of `log.csv`, with every variant in
    `docs/pvsetformer_log.md`.
  - **Search** `tools/pvsf_cv.py`. The LightGBM budget and protocol: 18 settings × 3 folds on the same development
    index (SQ Apartment25-36, masked from 2021-10-05), the same monthly folds (July, August, September 2021) and the
    same criterion (mean pinball over quantiles, horizons and folds). Grid: d ∈ {32, 64} × lr ∈ {3·10⁻⁴, 10⁻³,
    3·10⁻³} × weight decay ∈ {0.01, 0.1, 0.5}. Ties (within 10⁻⁶) go to the base setting, then to fewer parameters.
    Fixed: 4 heads, 4 sky tokens, 2 + 2 layers, dropout 0.1, batch 256, at most 100 epochs, patience 15, donor
    dropout 0.1.
  - **R1 number:** the median, over the 10 validation units, of the nRMSE at 1 h of the composed power forecast,
    computed as for LightGBM (0.18098). Each round reports the single-seed value. The final R1 run uses 5 seeds
    (guide §5.4) and reports the per-seed mean and s.d. and the seed ensemble (mean of the sorted quantiles). R1
    compares the 5-seed ensembles of both models (D37).
  - **Compute:** local CPU (torch 2.2.0+cpu), one thread per training, 8 in parallel; a round takes about 30–40 min.
    The test run is planned on Colab GPU (D04).
- **Caveat, stated in the paper:** the rounds and the final comparison use the same 10 validation units, so the
  comparison favours the model with more rounds (PVSetFormer; LightGBM had 4, D34). The test run is the unbiased check.
- **Evidence:** `results/nb5c_variants/`, `docs/pvsetformer_log.md`.

### D37 — Rule R1 compares 5-seed ensembles of both models [method, Phase 5] [author decision]
- **Request or reason:** asked which number decides R1 when PVSetFormer is trained with 5 seeds, the author chose
  (21 Nov 2026) "Ensemble for both". PVSetFormer's 5-seed ensemble is compared with LightGBM's 5-seed ensemble, so
  that neither model gains from seed averaging alone. Neural networks gain more from it than LightGBM, whose only
  randomness is bagging.
- **Change:**
  - Both models use the seeds C.SEED + 1 … C.SEED + 5. In LightGBM the seed drives the bagging and feature
    fractions (0.8 each); the rest of NB5a's bank is unchanged (configuration part 2a, sha256 `d03bb0b86827009e…`,
    checked by the runner).
  - Ensemble: the mean of the sorted quantiles across the seeds, sorted again. Composition with the prior and scoring
    are unchanged. Both models are scored by `tools/r1_score.py`, which reproduces the round runner's scores on V1
    (max difference 1·10⁻¹⁶).
  - R1 bar: the median validation nRMSE at 1 h of LightGBM's ensemble (`tools/r1_lgb_seeds.py`, results in
    `results/nb5c_variants/LGB_seeds/`). The per-seed mean and s.d. of both models are reported beside it.
    Single-seed development rounds keep the single-seed bar 0.18098 as their reference.
  - Check: refitted with NB5a's seed C.SEED, the bank reproduces NB5a's LightGBM forecasts (max difference
    6·10⁻⁸ on SQ567, origin 2 Jun 2021; float32 storage).
  - Proposed, to confirm at the freeze: the test run treats both models the same way (5-seed ensembles).
- **Evidence:** `tools/r1_score.py`, `tools/r1_lgb_seeds.py`.

### D16 — pvlib 0.16.1 and ruptures 1.1.10 are installed locally and pinned [environment, Phase 0]
- **Request or reason:** both are in the guide's software list (§5.6) and were missing locally on 18 Nov 2026.
- **Change:** `pip install pvlib==0.16.1 ruptures==1.1.10`. A dry run first showed that nothing else would be
  installed or upgraded; numpy 1.26.4 and pandas 2.2.0 are unchanged. Both are pinned in `requirements.txt`, because
  solar position, clear sky and change points feed the results directly.
