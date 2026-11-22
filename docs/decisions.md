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
    `docs/pvsetformer_log.md` and recorded as its own decision (D39 onward), as D25 asks.
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
    (max difference 1·10⁻¹⁶) and NB5a's own LightGBM scores when given NB5a's LightGBM forecasts (all 60
    unit–horizon rows, same slot counts, max difference 4·10⁻¹⁰), so the two models are scored alike.
  - The decision is made in `notebooks/NB5c_R1_decision.ipynb` (`tools/make_nb5c.py --final <variant>`). It trains
    nothing: it checks that both rounds used the same seeds and slots, applies the rule and writes
    `results/nb5c_r1/` with the frozen configuration part 2c (the chosen index forecaster and its settings).
  - R1 bar: the median validation nRMSE at 1 h of LightGBM's ensemble (`tools/r1_lgb_seeds.py`, results in
    `results/nb5c_variants/LGB_seeds/`). The per-seed mean and s.d. of both models are reported beside it.
    Single-seed development rounds keep the single-seed bar 0.18098 as their reference.
  - Check: refitted with NB5a's seed C.SEED, the bank reproduces NB5a's LightGBM forecasts (max difference
    6·10⁻⁸ on SQ567, origin 2 Jun 2021; float32 storage).
  - Proposed, to confirm at the freeze: the test run treats both models the same way (5-seed ensembles).
- **Evidence:** `tools/r1_score.py`, `tools/r1_lgb_seeds.py`.

### D38 — TimeXer and the summary-only ablation A6e under rule R2; correction of D23 [models, Phase 5]
- **Request or reason:** rule R2 (D25): TimeXer gets the same per-donor series, and PVSetFormer is also run on the
  fleet summary only (A6e).
- **Change:**
  - **Sources checked on 21 Nov 2026.** The TimeXer paper (Wang et al., arXiv:2402.19072 v4, doi
    10.48550/arXiv.2402.19072, Section 3, Eqs. 2–8) and the structure of the official code (github.com/thuml/TimeXer:
    `models/TimeXer.py`, `layers/Embed.py`, `layers/SelfAttention_Family.py`, `run.py`, the EPF script). The
    repository declares no licence, so `src/pvcold/timexer.py` is an original implementation from these
    descriptions; no code was copied. The NeurIPS 2024 venue was not confirmed from these pages (re-check at citation).
  - **Kept from TimeXer:**
    - the endogenous series in non-overlapping patches, each embedded linearly without bias, plus a fixed sinusoidal
      position embedding;
    - one learnable global token, and one variate token per exogenous series (a linear map of its look-back window,
      no position embedding); time-mark channels become further variate tokens;
    - each block: self-attention over the patches and the global token; cross-attention with the global token as the
      only query; a feed-forward network. Each has a residual and a LayerNorm;
    - a flatten head.
  - **Adapted to the common interface (guide §3.7):**
    - endogenous: the campus index over 4 h in four 1-h patches (values and validity flags);
    - exogenous: one token per donor with PVSetFormer's per-donor inputs (implied index, clip and validity flags over
      4 h, static features), with offline donors masked; plus σ, c, n and the 7 sun-geometry channels;
    - output: 9 monotone quantiles per horizon on the change from persistence (D34), starting at persistence;
    - TimeXer's instance normalisation is replaced by the persistence anchor, and there is no output dropout.
  - **Correction of D23.** D23 said TimeXer gets the sun geometry "through its future-exogenous variant (its Appendix
    H.1)". Appendix H.1 ("Intuitive Showcases for Exogenous Variable Utilization") is a qualitative showcase. It
    states that the model "has access to future predicted values of the exogenous variables", but it does not
    describe how they enter and reports no numbers. The known future (sun geometry at t + h, the index one day
    earlier) therefore enters TimeXer through a per-horizon linear map in the head, the same horizon information
    every learned index forecaster gets.
  - **Training and tuning:** setformer's code path (`arch=timexer`), with the same early stopping, refit, calibration
    predictions, donor dropout and horizon-balanced loss. The search budget is the same, 18 settings × 3 folds
    (`tools/pvsf_cv.py --name CVX --set arch=timexer balance=1`). Fixed as for PVSetFormer: 4 heads, 2 blocks,
    feed-forward width 2d, dropout 0.1. The paper's d_model of 128–512 and the code's 8 heads are for data sets much
    larger than a 2-month index history.
  - **A6e** (`summary_only=1`): the chosen PVSetFormer variant without its donor tokens, set attention and pooling,
    so one fleet-summary token per patch (index values, validity, σ, c, n). Same hyperparameters, no separate search:
    it removes an input, it is not a new model.
  - **Check:** with both options present, V4a retrained on its shortest task reproduces its forecasts exactly.
- **Evidence:** `src/pvcold/timexer.py`, `src/pvcold/setformer.py`; results in `results/nb5c_variants/CVX/`, `TX1/`,
  `A6e/`.

### D39 — PVSetFormer variant V1: the guide's design [R1 round, Phase 5]
- **Change:** guide §5.4 as built (D36), d 64, 2 + 2 layers. **Result** (single seed, validation): nRMSE 0.1858 at 1 h
  against LightGBM's 0.1810; at 15 min worse than persistence (0.1422 vs 0.1338). **Verdict:** base of V2.
  Details in `docs/pvsetformer_log.md`.

### D40 — PVSetFormer variant V2: fleet-summary token and horizon-balanced loss [R1 round, Phase 5]
- **Change:** one fleet-summary token per patch, and each horizon's pinball loss divided by persistence's error there.
  **Result:** 0.1864 at 1 h (within single-seed noise of V1); 15 min 0.1422 → 0.1395. **Verdict:** kept, as the base
  of the search.

### D41 — PVSetFormer search CV2 on V2 [R1 round, Phase 5]
- **Change:** 18 settings × 3 folds, the LightGBM budget (D36). **Result:** d 32, lr 10⁻³, weight decay 0.5 chosen;
  CV pinball 0.07003 against LightGBM's 0.06855, the gap at the short horizons. Weight decay barely matters.
  **Verdict:** the setting is used from V3 on.

### D42 — PVSetFormer variant V3: V2 with the CV2 setting [R1 round, Phase 5]
- **Result:** 0.1825 at 1 h (gap 0.8%); LightGBM better on 9 of 10 units; 15 min still worse than persistence.
  **Verdict:** kept, as the base of V4a and V4b. (V3 ran twice with identical scores; `log.csv` marks the duplicate.)

### D43 — PVSetFormer variant V4a: linear path on the index lags [R1 round, Phase 5]
- **Change:** per horizon, a linear map from the index lags (as change from k(t)), their flags, σ, c, n and the
  horizon query to the 9 head outputs, zero start, no weight decay. **Result:** 0.1795 at 1 h, the first variant below
  the single-seed bar (4 of 10 units; within single-seed noise); better than LightGBM in nRMSE from 1 h to 6 h,
  behind at 15 min. **Verdict:** kept; it goes to the 5-seed R1 round (D37).

### D44 — PVSetFormer variant V4b: auxiliary donor-forecast loss [R1 round, Phase 5]
- **Change:** V3 plus a loss on each donor's own future implied index (aggregate median plus a donor offset; one-sided
  for clipped readings), weight 0.5. **Result:** 0.1890 at 1 h, worse than V3 at every horizon. **Verdict:**
  rejected; not combined with V4a.

### D45 — Rule R1 met: PVSetFormer (variant V4a) becomes the main index forecaster [method, Phase 5]
- **Request or reason:** rule R1 (D25), applied as D37 sets it: 5-seed ensembles of both models, median validation
  nRMSE at 1 h.
- **Change:**
  - `notebooks/NB5c_R1_decision.ipynb` (`python tools/make_nb5c.py --final V4a_5s`, run 21 Nov 2026) compared the
    ensembles on the 10 validation units: PVSetFormer **0.18001**, LightGBM **0.18130** (−0.71%). PVSetFormer is the
    main index forecaster and the working title of D25 stands.
  - Frozen configuration part 2c: `results/nb5c_r1/r1_config_part2c.yaml`, sha256 `d6a24ddb931d0b88…`. It holds the
    V4a setting (60,157 parameters), the seeds C.SEED + 1 … + 5 and the LightGBM setting of part 2a.
  - LightGBM stays in the paper as the main learned baseline, also as a 5-seed ensemble (D37).
  - The margin is narrow (F44): 4 of 10 units at 1 h, Wilcoxon p = 1.0, and 3 of PVSetFormer's 5 single seeds
    score above LightGBM's ensemble. R1 is a pre-registered selection rule, not a result. Under guide §3.10
    (differences below about 3%), the paper does not claim from this evidence that PVSetFormer beats LightGBM at 1 h.
  - Variants tried before the decision: 6 (V1, V2, CV2, V3, V4a, V4b), all on development data. The paper reports
    the count. LightGBM had 4 formulation variants (D34) and its grid search.
  - Proposed: further design rounds remain allowed before the freeze (D25). A later variant replaces V4a only if its
    5-seed ensemble scores below V4a's at 1 h, and NB5c is then re-run with it as the final variant.
- **Evidence:** `results/nb5c_r1/` (summary.json, r1_medians.csv, r1_units_1h.csv, r1_pairs.csv, fig_r1),
  `results/nb5c_variants/V4a_5s/`, `results/nb5c_variants/LGB_seeds/`.

### D46 — The conformal layer of D35 applied to PVSetFormer, and kept [method, Phase 5]
- **Request or reason:** R1 made PVSetFormer the main index forecaster (D45). The conformal layer of D35 was fitted
  for LightGBM, so the main model needs its own.
- **Change:**
  - `notebooks/NB5c_conformal.ipynb` (`python tools/make_nb5c_conformal.py`, after NB5c) applies the rules of D35
    unchanged: CQR on the donors' pseudo cold starts, per event, origin and horizon, at the 80, 60, 40 and 20%
    intervals, normalised by G̃(t + h), with no correction under 50 scores; the median is unchanged. The keep rule is
    also unchanged.
  - The calibration set comes from PVSetFormer itself: in each seed, the early-stopped model predicts the last 20% of
    the training issue times before the refit (`setformer.fit_predict`, as for LightGBM in D35). The 5 seeds'
    predictions are ensembled like the forecasts.
  - Checks: the notebook verifies the hashes of part 2c and of the final variant's summary. The raw PICP80 it
    computes equals the R1 scores of the ensemble (maximum difference 0). All 180 groups have at least 50 scores.
  - Keep rule met (F45): at 1 h, PICP80 0.713 → 0.799 and IS80 0.5937 → 0.5897 (lower on 8 of 10 units). Settings:
    `results/nb5c_conformal/conformal_config_part2b_pvsf.yaml`, sha256 `cc1b10eb80f3afc8…`. They join the frozen
    part 2 beside LightGBM's part 2b, which stays the layer for LightGBM's rows.
  - Proposed, to settle at the freeze: if the test run treats LightGBM as a 5-seed ensemble (D37), its layer must be
    rebuilt from that ensemble's calibration predictions, which `tools/r1_lgb_seeds.py` does not yet save.
- **Evidence:** `results/nb5c_conformal/`.

### D47 — PVSetFormer variant V5a: volatility features of the index [R1 round, Phase 5]
- **Change:** V4a plus 6 features computed inside the model from the index lags. They are the log s.d. over the last
  1 h (at least 3 valid lags) and over the last 2 h (at least 4), and log |k(t) − k(t − 1)|, each as
  log((x + 0.01)/0.1) times its validity flag, followed by the flag. A per-horizon linear map (zero start, no weight
  decay) adds them to the 9 head outputs. Near the start the spread logits sit in softplus's exponential tail, so a
  weight β on a log s.d. makes the spread scale roughly as s.d.^β, which is what LightGBM does (F46). 60,481
  parameters (+324).
- **Checks:** the features equal `forecast.state`'s `sd_1h` and |`dk`| (maximum difference 2·10⁻⁷, same validity
  flags). V5a's initial outputs equal V4a's exactly, and V4a still reproduces exactly with the option present.
- **Result (21 Nov):** 0.17950 at 1 h (V4a at the same seed 0.17949). The intervals now follow volatility: at 15 min
  the 10–90% width goes from 0.233 (calmest quartile) to 0.451 (most volatile), coverage 0.847 and 0.741,
  close to LightGBM (`results/nb5c_diag/V5a/`). But the index pinball does not improve (+10.1% against LightGBM
  at 15 min; V4a +9.5%), and nRMSE is worse at 15 min (0.1344 vs 0.1339), 4 h (0.2390 vs 0.2336) and 6 h
  (0.2134 vs 0.2073). **Verdict:** rejected. The calm-state deficit lies in the median, not the spread (F49).

### D48 — PVSetFormer variant V5b: volatility gate on the median shift [R1 round, Phase 5]
- **Change:** V5a plus a per-horizon gate 1 + tanh(w · vol + b), with w and b zero at the start (gate 1), on the
  transformer head's median output only (not on the spread logits). The model can then shrink the transformer's
  median shift toward persistence in calm states, where its median is worse than LightGBM's (F46). 60,523
  parameters (+42).
- **Result (21 Nov):** 0.18263 at 1 h, worse than V4a at the same seed at every horizon except 15 min (0.1335 vs
  0.1339): 30 min 0.1582, 2 h 0.2157, 4 h 0.2414, 6 h 0.2136. At 15 min the calm-quartile pinball gap to
  LightGBM falls from 41% to 22%, which supports the diagnosis (F49), but the gate costs the longer horizons.
  **Verdict:** rejected.

### D49 — TimeXer's setting (search CVX) and its validation round TX1 [models, Phase 5]
- **Request or reason:** rule R2 (D25, D38). TimeXer gets the same search budget as LightGBM and PVSetFormer.
- **Change:**
  - Search CVX (`tools/pvsf_cv.py --name CVX --set arch=timexer balance=1`): the same 18 settings × 3 folds on the
    development index. It chose d 32, lr 3·10⁻³, weight decay 0.01, with CV pinball 0.06800, against LightGBM's
    0.06855 and PVSetFormer's CV2 0.07003 (which was searched on V2, before the linear path). The chosen learning
    rate is the largest in the shared grid; the grid is the fixed budget, so it is not extended. Runtime 17 min.
  - Round TX1, 1 seed (the seed of V4a's single-seed round): 0.18174 at 1 h (LightGBM's single seed 0.18098, V4a
    0.17949). Against V4a with the same seed it is better at 15 min (nRMSE −1.5%, CRPS −4.4%) and 2 h (−0.9%), level
    at 30 min, and worse at 1, 4 and 6 h (+1.3%, +1.7%, +2.4%). 37,224 parameters; 4.5 min.
  - TimeXer with the 5 R1 seeds (TX1_5s): ensemble **0.17845** at 1 h, below PVSetFormer's 0.18001 and LightGBM's
    0.18130; single seeds 0.17961–0.18208 (mean 0.18109, s.d. 0.0011), the same mean as PVSetFormer's. None of
    the differences is significant across units (F48).
- **Evidence:** `results/nb5c_variants/CVX/`, `results/nb5c_variants/TX1/`.

### D50 — The main model after A6e: keep developing until the freeze [method, Phase 5] [author decision]
- **Request or reason:** with 5 seeds, PVSetFormer without donor tokens (A6e) equals the full model on validation
  (F47). Asked how to handle the main model, the author chose (21 Nov 2026) "Keep trying until freeze".
- **Change:**
  - More design rounds, on development data only, try to make the donors useful (for example their timing relative
    to the index, or their disagreement), and to close the short-horizon gap (F46, F49).
  - At the freeze, if A6e still equals the full model, the paper reports that the fleet index carries the donor
    information, and the author then decides the main model and the title.
  - Every round stays logged as a decision and in `docs/pvsetformer_log.md`; the paper reports the number of
    variants.
- **Evidence:** F47; this session's question and answer.

### D51 — The sensor and satellite rows use LightGBM [method, Phase 5] [author decision] [guide deviation]
- **Request or reason:** guide §4.2 defines A4, A4b and A9 as "the main model" with the sensor or satellite index in
  place of the fleet index. With PVSetFormer as the main model this is ill-defined: PVSetFormer reads individual
  donors, and a sensor or a satellite pixel is one series. Asked which learner to use, the author chose (21 Nov 2026)
  LightGBM.
- **Change:**
  - A4 (raw pyranometer index) and A4b (corrected pyranometer index) use LightGBM with the frozen setting of part
    2a and the change-from-persistence target (D34), on the NB4 index sources and their refitted gains (D32).
    LightGBM on the fleet index is reported beside them, so the index source is compared with the learner held
    fixed. The features come from the source alone (σ, c and n left empty); the issue and target rules are the
    fleet's, so all rows share the fleet models' slots (`forecast.run_origin_source`).
  - **Correction (21 Nov 2026).** The question put to the author grouped A9 with the learner rows. The guide
    defines A9 as the satellite index *persisted* forward × prior gain, and A9n as its same-time value (oracle),
    so neither has a learner. They stay as the guide defines them; the author's answer applies to A4 and A4b.
    A LightGBM row on the satellite index would be an addition and is not made without the author.
  - A4c is the main model plus the corrected sensor index as an extra input.
- **Evidence:** this session's question and answer.

### D52 — PVSetFormer variant V6a: horizon queries kept apart in the decoder [R1 round, Phase 5]
- **Change:** V4a with a diagonal self-attention mask in the decoder, so each horizon query attends only to itself
  (and to the encoder). It tests F49's hypothesis that the 15-min median inherits the long horizons' mean reversion
  through the decoder. No new parameter (60,157); same initial outputs as V4a.
- **Result (21 Nov 2026):** rejected. Median nRMSE against V4a at the same seed: 15 min 0.1333 vs 0.1339,
  1 h 0.18053 vs 0.17949 (+0.6%), 6 h 0.2112 vs 0.2073 (+1.9%). At 15 min in the calmest quartile the median
  moves further from persistence (0.037 vs 0.034), and on clear spells its bias grows (−0.035 vs −0.031). The
  horizons' mutual attention is not the cause of F49 (F50).

### D53 — PVSetFormer variant V6b: per-horizon deviation from the shared head [R1 round, Phase 5]
- **Change:** V4a plus, per horizon, a linear readout of the decoder output added to the shared head (zero start,
  normal weight decay, so it stays a shrunk deviation). TimeXer reads each horizon out with its own weights (F49).
  61,939 parameters (+1,782).
- **Result (21 Nov 2026):** not kept as is. Best 15 min so far: 0.1311 vs 0.1339 (−2.1%, better on 8 of 10
  units); the 15-min pinball gap to LightGBM falls from +9.5% to +6.2% (calmest quartile +41% → +30%); on clear
  spells the median's bias falls from −0.031 to −0.013. But 1 h +0.4%, 4 h +5.2%, 6 h +6.3%, and training stops
  earlier (mean best epoch 14, V4a 17): the separate readouts over-fit the long horizons (F50). Next: the readout
  at 15 min only (V8a, D57).

### D54 — PVSetFormer variant V7a: learned donor identity [R1 round, Phase 5]
- **Change:** V4a plus a learned embedding per donor (a table over the panel's 44 units, zero start, normal weight
  decay), added to the donor's tokens. Donor tokens were anonymous: the set attention saw only gain, DC/AC ratio,
  metadata flag and tilt class, so it could not learn that a given roof dims before the others. The metadata give
  station names but no coordinates (F10), so position enters only through this learned identity. 62,205 parameters.
  The static donor features now carry the unit index as a 7th column; every model reads only the first 6 for its
  static features (V4a and TimeXer TX1 reproduce exactly).
- **Result (21 Nov 2026):** within 0.11% of V4a at every horizon (1 h 0.17938 vs 0.17949), but better at 1 h
  on 9 of 10 units, at 15 min on 9 and at 6 h on 7 (same seed). A small, consistent effect inside one seed's
  spread. Kept for the combination V8b (D58).

### D55 — PVSetFormer variant V7b: each donor's deviation from the index [R1 round, Phase 5]
- **Change:** V4a plus, per step, the donor's implied index minus the campus index (where both are valid), mapped
  into the donor token by a zero-start linear layer. The donor tokens did not see the index (it enters only through
  the fleet token, after pooling), so "this roof is darker than the fleet now" had to be inferred. 60,317 parameters.
- **Result (21 Nov 2026):** lowest single-seed 1 h so far, 0.17927 vs 0.17949 (−0.1%); 2 h −0.5%, 6 h −0.7%;
  CRPS −0.4% at 1 h and −0.9% at 6 h; better at 1 h on 5 of 10 units. Within single-seed noise. Kept for the
  combination V8b (D58).

### D56 — A4c: the main model plus the corrected sensor index (option `ext`) [models, Phase 5]
- **Request or reason:** D51: A4c is the main model with the corrected sensor index as an extra input (guide §4.2:
  "adding the sensor helps or hurts").
- **Change:**
  - `ext=<source>` (e.g. `sensor_corr`) adds NB4's 15-min index of that source to the event series. Its values and
    validity flags over the 4-h window follow the fleet-summary columns of each patch and enter the fleet token
    through a zero-start linear layer, created last. The model therefore starts exactly at the main model and can
    learn to use the sensor, or not.
  - Every reader of the fleet tensor now takes the first 11 columns explicitly (linear path, TimeXer's marks), so
    the extra columns reach nothing else. `tools/pvsf_dev.py` and `tools/pvsf_cv.py` add the source when `ext` is set;
    the CV runner masks it after 2021-10-05 like the index.
  - Checks: V4a, A6e and TimeXer TX1 reproduce exactly; with `ext=sensor_corr` the initial outputs equal V4a's
    (60,445 parameters); a 2-epoch run is finite and sorted.
  - A development round A4c (1 seed, paired with V4a) follows NB5d.
- **Result (21 Nov 2026):** the sensor does not help. Against V4a at the same seed, median nRMSE +0.8% at 15 min,
  +0.5% at 30 min and at 1 h (0.18038 vs 0.17949; better on 2 of 10 units), −0.3%, −0.1% and −0.4% at 2, 4 and
  6 h; CRPS +0.3% at 1 h, −0.5% at 6 h. All within single-seed noise (F51). On the test events A4c is rerun with
  the final main model.
- **Evidence:** `src/pvcold/setformer.py`; results in `results/nb5c_variants/A4c/`.

### D57 — PVSetFormer variant V8a: the per-horizon readout at 15 min only [R1 round, Phase 5]
- **Reason:** V6b's per-horizon readout removed most of the 15-min drift (F49) but over-fitted the long horizons, and
  at 30 min it did not help (0.1570 vs 0.1562); F50.
- **Change:** option `hhead_n` (V8): the deviation from the shared head on the first n horizons only (0 = all, V6b's
  behaviour). V8a = V4a + `hhead=1 hhead_n=1`: only the 15-min horizon gets its own readout. 60,454 parameters
  (+297). Checks: V4a and V6b reproduce exactly on their shortest task; V8a starts at V4a's outputs; a 2-epoch run is
  finite and sorted.
- **Result (21 Nov 2026, 1 seed):** best 15 min so far, 0.1308 vs 0.1339 (−2.3%, better on 7 of 10 units; pinball
  gap to LightGBM at 15 min +7.1%, V4a +9.5%), and the long horizons are kept (6 h +0.8%, against V6b's +6.3%).
  But 30 min +1.4% and 1 h +1.1% (0.18138; better on 2 of 10 units), CRPS at 1 h +1.4%. The 1-h loss is within
  the single-seed spread (s.d. 0.0014, about 0.8%), so V8a runs with the 5 R1 seeds (V8a_5s) before a verdict.
- **Result with 5 seeds (21 Nov 2026, V8a_5s):** not kept. Ensemble against V4a_5s: 15 min 0.1309 vs 0.1329
  (−1.6%, better on 7 of 10 units, Wilcoxon p 0.28; CRPS −2.6%), but 30 min 0.1585 vs 0.1566 (+1.2%, 1 of 10,
  p 0.08), 1 h 0.18061 vs 0.18001 (+0.3%, 2 of 10, p 0.11), 2 h +0.6%, 6 h +1.1%. The single seeds spread more
  at 1 h (s.d. 0.0025 against 0.0014). The diagnosis shows why: on 15-min clear spells the drift is removed
  (median move 0.028, bias −0.011; V4a 0.047, −0.029), but it moves to 30 min (0.082, −0.044; V4a 0.067, −0.030).
  V4a stays the candidate.

### D58 — PVSetFormer variant V8b: donor identity and donor deviation together [R1 round, Phase 5]
- **Reason:** V7a and V7b each moved the forecast slightly in the right direction (F50); the two act on different
  parts of the donor token (who the donor is; how far it is from the campus index now).
- **Change:** V4a + `donor_id=1 donor_rel=1`. 62,365 parameters. Starts at V4a's outputs (checked); a 2-epoch run is
  finite and sorted.
- **Result (21 Nov 2026, 1 seed):** rejected. Against V4a at the same seed: 15 min −0.2%, 30 min +0.8%, 1 h +0.3%
  (0.18000; better on 4 of 10 units), 6 h −0.6%; CRPS at 1 h −0.2%. The two donor options together do no better
  than either alone, and every difference is within one seed's spread: the donor tokens still add nothing
  measurable (F47). The V8a + V8b combination is not run.

### D59 — Foundation-model baselines A6a (Chronos-2) and A6b (TimesFM 2.5): interface, environment, settings [models, Phase 5] [guide deviation]
- **Request or reason:** D23 and guide §5.4 (rows A6a–A6c): zero-shot foundation models with the past fleet state as
  past covariates and u(t + h) as known future covariates, inference local; their settings belong to the freeze.
- **Sources checked (21 Nov 2026):** the model cards `amazon/chronos-2` (Apache-2.0; 120M parameters; context 8,192;
  GPU and CPU) and `google/timesfm-2.5-200m-pytorch` (Apache-2.0); the chronos-forecasting and timesfm READMEs and
  pyproject files; and the installed sources. Chronos-2 (chronos-forecasting 2.3.2): `predict_quantiles` masks
  missing values in the context and in the future covariates, and the nine levels 0.1–0.9 are among its 21 native
  quantiles. TimesFM 2.5 (package `timesfm` 3.0.2, module `timesfm_2p5`): missing values are filled by linear
  interpolation; covariates enter only through XReg, a per-input linear model on covariates known over context and
  horizon, so a past-only covariate cannot enter. **This is the guide deviation:** A6b cannot receive the fleet state.
- **Change:**
  - **Environment:** a separate `.venv_fm` (`requirements-fm.txt`, git-ignored) or Colab. The packages bring numpy 2,
    torch 2.15 and transformers 5, so the main environment stays untouched (torch 2.2.0, numpy 1.26.4) and the
    PVSetFormer rounds keep reproducing; the two exchange parquet files only. The weights are public and downloaded
    once without a token (a stored, expired Hugging Face token is not sent); no data leave the machine.
  - **Inputs** (`NB5b_inputs`, `results/nb5b_inputs/`): each validation event's index, fleet state and sun geometry
    from the fleet's start (2021-05-15, LightGBM's first training day), and NB5a's 37,619 issue times; sha256 manifest
    checked by every run.
  - **Grid:** the daylight slots 06:00–17:45 (48 a day). The index exists only there (D12); on this grid step h is
    t + 15 h for every scored target.
  - **A6a Chronos-2:** the index as target; σ, c and n as past-only covariates; the eight geometry features of
    LightGBM's future set (Gt, cos z, sin and cos of azimuth, hour angle and day of year) as known covariates.
  - **A6b TimesFM 2.5:** XReg (`xreg + timesfm`, ridge 0) on the six within-day geometry features (the day of year
    is constant over a window), with the context's gaps filled by linear interpolation for the linear model.
    Forecast settings as on the model card (input normalisation, continuous quantile head, flip invariance,
    positivity, quantile-crossing fix); `torch_compile` off. The fleet state cannot enter.
  - **Settings grid, fixed before any score:** context 336 or 1,344 daylight steps (7 or 28 days) × covariates on
    (the guide's interface) or off (what the covariates add), for each model: 8 runs, deterministic (seed 1).
    **Rule:** per model, the setting with the lowest median validation nRMSE at 1 h, on NB5a's slots after composition
    with the frozen prior (`NB5b_foundation`, configuration part 2d `fm_config_part2d.yaml`).
  - **Where:** Colab GPU (D04), with `NB5b_colab` (resumable, hash-checked); the same notebook runs locally on the
    CPU through `.venv_fm`. Local smoke tests on 3 issue times per unit (30), 3 threads, beside a PVSetFormer
    round, model load included: Chronos-2 144 s, TimesFM 409 s without and 296 s with XReg, each writing sorted quantiles for the 6 horizons. The 37,619 issue times × 8 settings are not feasible on this CPU.
  - **A6c TabPFN-TS:** pending the author. Its default engine is Prior Labs' cloud API (excluded: data would leave
    the machine) and it collects telemetry by default; local inference needs the TabPFN-2 weights (Prior Labs
    License, Apache-2.0 with an attribution clause) or the default TabPFN-3.5 weights (non-commercial, licence
    accepted through the author's account).
- **Evidence:** `tools/fm_infer.py`, `tools/make_nb5b.py`, `requirements-fm.txt`, `results/nb5b_inputs/inputs_manifest.json`.
- **Result (21 Nov 2026).** The author ran `NB5b_colab` on a Colab GPU (all 8 settings, 184,353 rows each;
  Chronos-2 86–3,658 s, TimesFM 172–736 s per setting; Colab's torch 2.14.1+cu130, chronos-forecasting 2.3.2,
  transformers 5.22.1, timesfm 3.0.2, jax 0.11.1, scikit-learn 1.6.1, numpy 2.4.6, pandas 2.2.3, recorded per run).
  `fetch_drive_runs.py` brought them back (input hashes, row counts and sorted quantiles checked), and
  `NB5b_foundation` (415 s) scored them on NB5a's slots. Its PVSetFormer reference is now the candidate V9_5s
  (D60) instead of V4a_5s (`make_nb5b.py --only NB5b_foundation`; the other two notebooks are not rewritten).
  Median nRMSE at 1 h: Chronos-2 0.1776 (28 days, covariates) / 0.1783 (28 days, none) / 0.1795 (7 days,
  covariates) / 0.1817 (7 days, none); TimesFM 2.5 0.1790 (28 days, none) / 0.1801 (7 days, XReg) / 0.1806
  (7 days, none) / 0.1806 (28 days, XReg). **By the rule: A6a = Chronos-2 with 1,344 daylight steps and the
  covariates; A6b = TimesFM 2.5 with 1,344 steps and no XReg.** Part 2d: `results/nb5b_fm/fm_config_part2d.yaml`
  (sha256 `d637d1b05e16aac8…`), with the weights' revisions. The comparison with the trained forecasters is F56.

### D60 — Search CV4: the shared search on V4a's own architecture [R1 round, Phase 5]
- **Reason:** PVSetFormer's setting (d 32, lr 10⁻³, weight decay 0.5) was chosen by CV2 on V2 (D41), before V4a's
  linear path (D43) changed the architecture. LightGBM's and TimeXer's settings come from a search on their own
  final architecture (NB5a, CVX). In CV2 the two best settings were close (wd 0.5: 0.07003; wd 0.01: 0.07014), and
  TimeXer's search chose the other end of the grid (lr 3·10⁻³, wd 0.01). The linear path is not shrunk, so it may
  change how much the transformer needs to be.
- **Change:** `python tools/pvsf_cv.py --name CV4 --set fleet_token=1 balance=1 lin=1`: the D36 search unchanged
  (18 settings × 3 monthly folds on the development index SQ Apartment25-36, masked from 2021-10-05; mean pinball;
  ties toward d 64, lr 10⁻³, wd 0.01, then fewer parameters), on V4a. **Rule, fixed before the result:** if CV4
  chooses V4a's setting, V4a stands, and its setting is confirmed on its own architecture. Otherwise V9 = V4a with
  the CV4 setting runs with the 5 R1 seeds and replaces V4a as the candidate if its ensemble is lower at 1 h. The
  budget stays equal across models: each final model has its setting from one search on its own architecture.
- **Result (21 Nov 2026, 85 min):** CV4 chooses d 64, lr 10⁻³, weight decay 0.5 (224,317 parameters), CV pinball
  0.07059; then d 64 / wd 0.01 (0.07103) and d 32 / lr 3·10⁻⁴ / wd 0.5 (0.07114). V4a's setting (d 32, lr 10⁻³,
  wd 0.5) ranks 10th of 18 (0.07237). On the development index the linear path does not lower the CV pinball:
  CV2's best on V2 was 0.07003 (LightGBM 0.06855, TimeXer 0.06800). By the rule, V9 = V4a with the CV4 setting
  runs with the 5 R1 seeds (V9_5s), queued after V10a_5s.
- **Result of V9_5s (21 Nov 2026, 154 min): V9 replaces V4a as the PVSetFormer candidate.** Ensemble median nRMSE
  at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h: 0.13320 / 0.15717 / 0.17848 / 0.20754 / 0.23241 / 0.20607, against
  V4a_5s's 0.13294 / 0.15661 / 0.18001 / 0.20926 / 0.23336 / 0.20679 (+0.19, +0.36, −0.85, −0.82, −0.41, −0.35%;
  5 or 6 of 10 units better; Wilcoxon p ≥ 0.23). Single seeds at 1 h 0.17772–0.18475, mean 0.18072 (s.d. 0.0028,
  twice V4a's 0.0014). Against LightGBM's ensemble: +3.2% at 15 min, +0.6% at 30 min, −1.6% at 1 h (6 of 10
  units, p 0.56), −1.3% at 2 h, −1.8% at 4 h (9 of 10, p 0.004), −5.5% at 6 h (8 of 10, p 0.010). Against
  TimeXer's ensemble at 1 h: 0.17848 against 0.17845, level (V9 lower on 3 of 10 units). The short-horizon
  pattern is V4a's: calmest-quartile 15-min pinball 40.4% above LightGBM's, clear-spell bias −0.030, reversion
  slopes 0.115 → 0.163 (`results/nb5c_diag/V9_5s/`, `drift_V9/`). Rule R1 (part 2c) and PVSetFormer's conformal
  layer (D46) still name V4a_5s; they are rerun on the final candidate at the freeze (`make_nb5c.py --final`,
  `NB5c_conformal`). By D63, V11a (on V4a's setting) is then compared with V9 at 1 h if it meets its rule.

### D61 — PVSetFormer variant V10a: a volatility gate on the linear path's reversion [R1 round, Phase 5]
- **Reason:** F52: the short-horizon drift is the linear path's reversion toward the recent mean, with the same
  strength in calm and volatile states.
- **Change:** option `vlin` (V10). Per horizon, a gate g_h = exp(clip(u_h · v + b_h, −3, 3)), where v holds the six
  volatility features of V5a (log s.d. of the index over the last 1 h and 2 h, log |last change|, each with its
  flag). The gate multiplies the median coefficients of the linear path's change terms (the 16 lags minus k(t), and
  the day-earlier index minus k(t)), so the strength of the reversion can follow the recent volatility. The spread,
  the other linear terms and the transformer are unchanged. u and b start at zero (g = 1, exactly V4a) and have no
  weight decay. 60,199 parameters (+42).
- **Checks:** V4a reproduces exactly on its shortest task (max difference 0 over 5,060 rows); V10a starts at V4a's
  outputs; the gate receives a gradient; the change columns are the lags and the day-earlier change; a 2-epoch run
  is finite and sorted.
- **Protocol:** directly with the 5 R1 seeds (V10a_5s), against V4a_5s, because one seed cannot show differences
  below about 2% (F50). **Rule, fixed before the result:** V10a replaces V4a as the candidate if its ensemble's
  median nRMSE is lower at 1 h and no more than 1% higher at any other horizon. The drift diagnosis (F52) is
  repeated on it.
- **Result (21 Nov 2026, 92 min):** not kept; V4a stays the candidate. Ensemble median nRMSE at 15 min / 30 min /
  1 h / 2 h / 4 h / 6 h: 0.13242 / 0.15694 / 0.18011 / 0.21032 / 0.23336 / 0.20637, against V4a_5s's 0.13294 /
  0.15661 / 0.18001 / 0.20926 / 0.23336 / 0.20679 (−0.39, +0.21, +0.06, +0.51, 0.00, −0.20%; better at 1 h on
  7 of 10 units; Wilcoxon p ≥ 0.27 at every horizon). Single seeds at 1 h: 0.17908–0.18331, mean 0.18114 (s.d.
  0.0018). The gate does change the mechanism F52 found: the 15-min reversion slope, calmest → most volatile
  quartile, becomes 0.094 / 0.099 / 0.134 / 0.183 (V4a 0.112 / 0.101 / 0.127 / 0.158; truth 0.039 → 0.217), and
  at 30 min 0.152 → 0.320 (V4a 0.192 → 0.279; truth 0.112 → 0.364). But the calmest quartile's 15-min pinball gap
  to LightGBM hardly moves (39.3% against 40.1%), nor does the clear-spell bias (calmest quartile, k(t) > 0.9:
  −0.028 against −0.029). The reversion toward the 4-h mean is therefore not what keeps the calm-state median
  off persistence (`results/nb5c_diag/drift_V10a/`, `nb5c_diag/V10a_5s/`).

### D62 — Matched-history diagnostic: is the late-origin gap data or season? [diagnostic, Phase 5]
- **Reason:** on the validation units PVSetFormer's and TimeXer's index-level pinball gaps to LightGBM at 1 h grow
  from the first origin to the third (recorded by the tool in `by_origin.csv`). Training always starts
  at the fleet's start (2021-05-15), so a later origin has both more history and a later season. The scored test
  units start between 2021-10-05 and 2023-07-09 (5 to 26 months of history, against 0.5 to 4 months on validation),
  so the answer bears on how the validation ranking carries to the test.
- **Change:** `tools/learn_window.py`. At the third origin of each validation unit, LightGBM (part-2a setting,
  seeds of LGB_seeds), PVSetFormer (V4a's setting) and TimeXer (TX1's) are refitted with 5 seeds on only as much
  history as the unit had at its first origin, ending at the origin. History is hidden by setting the index, σ, c
  and n to missing before the window. Forecast rows must equal the full-history rounds' (asserted). Index-level
  pinball and median MAE. Development data only; no rule or setting of the protocol changes with the result.
- **Result (21 Nov 2026, 39 min, 150 fits):** the windows hold 18–61 days (all start on 2021-07-14, 60 days after
  the fleet's start), against 78–121 days of full history; 656–2,704 training issue times. With matched history,
  PVSetFormer is still behind LightGBM at the third origin (1 h: +7.5%), so the late-origin gap is not a matter
  of the amount of history; the extra 60 days help PVSetFormer more than LightGBM. Numbers and reading: F53.

### D63 — PVSetFormer variant V11a: a volatility gate on the whole median change [R1 round, Phase 5]
- **Reason:** F54: in calm states the transformer head and both parts of the linear path move the median off
  persistence, so a gate on one part (V10a on the change terms, V5b on the head) leaves the others.
- **Change:** option `vmed` (V11). Per horizon, a gate g_h = exp(clip(u_h · v + b_h, −3, 3)) from V5a's six
  volatility features multiplies the whole median change (the head's plus the linear path's). The forecast
  distribution can then stay at persistence in calm states and move further in volatile ones; the spread is
  unchanged. u and b start at zero (g = 1, exactly V4a) and have no weight decay. 60,199 parameters (+42). V4a's
  setting (d 32, lr 10⁻³, weight decay 0.5), so the comparison isolates the gate.
- **Checks:** V4a and V10a_5s reproduce exactly on their shortest tasks (max difference 0 over 5,060 rows each);
  V11a starts at V4a's outputs; with g = 2 every quantile moves by exactly the median change; the gate receives a
  gradient; a 2-epoch run is finite and sorted.
- **Protocol:** directly with the 5 R1 seeds (V11a_5s), queued after V9_5s. **Rule, fixed before the result:** V11a
  replaces V4a as the candidate if its ensemble's median nRMSE is lower at 1 h and no more than 1% higher at any other
  horizon. If V9 (D60) and V11a both meet their rules, the candidate is the one with the lower ensemble at 1 h, and
  V12 (V9's setting with the gate) runs with 5 seeds. The diagnoses of F46, F49 and F52 are repeated on it.
- **Result (21 Nov 2026, 112 min): not kept.** Ensemble median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h:
  0.13176 / 0.15741 / 0.18022 / 0.21101 / 0.23715 / 0.20976, against V4a_5s's 0.13294 / 0.15661 / 0.18001 /
  0.20926 / 0.23336 / 0.20679 (−0.88, +0.51, +0.12, +0.84, +1.63, +1.44%): higher at 1 h, and more than 1% higher
  at 4 and 6 h. At 15 min it is lower on 9 of 10 units (Wilcoxon p 0.084), and the short-horizon diagnoses move
  the right way: calmest-quartile 15-min pinball 30.4% above LightGBM's (V4a 40.1%), 30-min 16.3% (21.1%);
  clear-spell bias at 15 min −0.021 (−0.029); calm 15-min reversion slope 0.098 (0.112; truth 0.039). The cost is
  at the long horizons, where training becomes unstable: the s.d. over seeds of the per-seed median nRMSE is
  0.0058 at 4 h and 0.0064 at 6 h, against 0.0012 and 0.0018 for V4a (F55). Single seeds at 1 h 0.17870–0.18507,
  mean 0.18135 (s.d. 0.0023). V9 stays the candidate; V12 is redefined in D67 (the gate on 15 and 30 min only).
  `results/nb5c_variants/V11a_5s/`, `nb5c_diag/V11a_5s/`, `nb5c_diag/drift_V11a/`.

### D64 — LightGBM enters the test as its 5-seed ensemble; its conformal layer is rebuilt from that ensemble [author decision, Phase 5]
- **Request:** the author, 21 Nov 2026, answering the question left open in D46: "yes, LightGBM be a 5-seed ensemble
  at test".
- **Change:** LightGBM's rows at the test use the ensemble of the 5 R1 seeds (`LGB_seeds`, D37: mean of the sorted
  quantiles, sorted again), like PVSetFormer's. Its conformal layer is rebuilt from that ensemble with the rules of D35
  unchanged, as D46 proposed:
  - `tools/lgb_seeds_cal.py` refits the bank (part-2a setting) with the same seeds through `forecast.cal_task`
    (NB5a_conformal's code path) and keeps the early-stopped models' predictions on the last 20% of the training
    pairs. Its forecasts must equal `LGB_seeds`' rows seed by seed (asserted). Smoke test on two tasks: 10,120 rows
    matched, max difference 6·10⁻⁸ (float32 storage), 914 calibration rows.
  - `python tools/make_nb5c_conformal.py --model lgb` writes `notebooks/NB5c_conformal_lgb.ipynb`: PVSetFormer's
    conformal notebook with only the setup, the reference table, the figure title and the output names changed
    (cells 2–5 and 8 identical; the PVSetFormer notebook regenerates with identical sources). Output
    `results/nb5c_conformal_lgb/`, settings `conformal_config_part2b_lgb5.yaml`.
  - Queued after V11a_5s (memory is short while two 8-worker runs would overlap).
- **Consequence:** part 2b holds LightGBM's 5-seed layer for its test rows; NB5a's single-seed layer stays on record.
- **Result (21 Nov 2026): kept.** `lgb_seeds_cal.py` (150 bank fits, 13 min): all 919,910 forecast rows equal
  `LGB_seeds`' (max difference 6·10⁻⁸), 411,365 calibration rows, every one of the 82,273 calibration keys with all
  5 seeds. `NB5c_conformal_lgb` (55 s; 180 groups, none without a correction): median PICP80 at 1 h 0.709 raw,
  0.795 conformal; median IS80 at 1 h 0.5756 → 0.5705, lower on 9 of 10 units; so the keep rule of D35 is met.
  Conformal PICP80 over horizons 0.756–0.802 (lowest at 2 h). The single-seed layer (NB5a) gave 0.714 → 0.797 and
  0.5739 → 0.5716 (8 of 10). Settings `results/nb5c_conformal_lgb/conformal_config_part2b_lgb5.yaml` (sha256
  `feb062a2dda885a5…`), with the LightGBM part-2a configuration and `LGB_seeds`' summary hashed in its summary.

### D65 — TabPFN-TS (row A6c) waits for the author to accept the TabPFN licence [author decision, Phase 5]
- **Request:** the author, 21 Nov 2026, on the three options of D59 (local TabPFN-2 weights with telemetry off, the
  TabPFN-3.5 weights once the author has accepted their licence, or dropping the row): "u can wait to accept the
  licence".
- **Change:** none yet. A6c stays in the plan; it runs locally (never the cloud API) once the author has accepted the
  licence through their own account and the weights can be downloaded. If the download needs a Hugging Face login
  (the stored token has expired), the author logs in on this machine themselves; no token is ever written into the
  repository or the chat.
- **Consequence:** if the licence is not available by the freeze, the author decides then between TabPFN-2 and
  dropping the row.

### D66 — The Colab run of NB5b goes through a minimal Google Drive mirror [environment, Phase 5]
- **Request:** the author, 21 Nov 2026, asked what exactly to run on Colab, whether the repository is on Drive so the
  notebook opens from there, and how the results come back.
- **Change:**
  - `tools/make_drive_mirror.py` copies only what `NB5b_colab` reads (the notebook, `tools/fm_infer.py`,
    `src/pvcold/*.py`, `requirements-fm.txt`, `results/nb5b_inputs/`): 16 files, 1.68 MB, no raw data and no
    documents, each checked by SHA-256 and listed in `MIRROR_MANIFEST.json`. Created on 21 Nov 2026 at `G:/My
    Drive/pv-cold-start` (Google Drive for desktop, streaming mode), the folder `DRIVE_REPO` names in the notebook.
  - Before the upload, a copy of the mirror ran `fm_infer.py` on its own (`.venv_fm`, Chronos-2, context 336,
    covariates on, one issue time per unit): 10 tasks, 60 rows.
  - `tools/fetch_drive_runs.py` brings `results/nb5b_runs/` back from the mirror: every record must come from the
    local input hashes, must not be a smoke test, and its parquet must hold the recorded rows with sorted quantiles;
    all-or-nothing, idempotent (tested on a synthetic mirror). Then `NB5b_foundation` runs locally.
- **Rule:** the local repository stays the master copy (D04). The mirror is never edited by hand; to refresh it,
  delete the Drive folder and rerun the tool.
- **What happened (21 Nov 2026):** My Drive now holds two folders named `pv-cold-start`: the mirror (17:33) and a
  copy made at 17:54, which Google Drive for desktop shows as `G:/My Drive/pv-cold-start (1)`. Colab's
  `/content/drive/MyDrive/pv-cold-start` resolved to the copy, so the runs are there. Its code and inputs equal
  the mirror's manifest file for file (SHA-256); the runs were fetched with
  `python tools/fetch_drive_runs.py "G:/My Drive/pv-cold-start (1)"`. Before another Colab run, one of the
  two folders should be removed (the author's choice; nothing on Drive is deleted by the agent).

### D67 — PVSetFormer variant V12: the median-change gate on the 15- and 30-min horizons only, on V9's setting [R1 round, Phase 5]
- **Reason:** V11a (D63, F55) lowers the 15-min ensemble on 9 of 10 units and narrows the calm-state gap, but on the
  long horizons the gate makes training unstable (seed s.d. at 4 h about five times V4a's) and raises the error by
  up to 1.6%. The long horizons do not need it: there PVSetFormer is already below LightGBM (V9: −1.8% at 4 h, −5.5%
  at 6 h). D63's V12 (V9's
  setting with the gate on every horizon) is therefore replaced by the gate on the short horizons only.
- **Change:** option `vmed_n` (V12): V11's gate on the first n horizons only, gate 1 on the others; `vmed_n=2`
  covers 15 and 30 min (the two horizons where V11a's calmest-quartile pinball gap fell, 40 → 30% and 21 → 16%).
  On V9's setting (d 64, lr 10⁻³, weight decay 0.5), the candidate: 224,331 parameters (+14). `vmed_n=0` keeps
  V11 (the gate on all six horizons).
- **Checks:** V11a_5s reproduces exactly on its shortest task (5,060 rows, max difference 0); V12 starts
  at V9's outputs; with g = 2 the 15- and 30-min quantiles move by exactly the median change and the later
  horizons are unchanged; the gate receives a gradient; a 2-epoch run is finite and sorted.
- **Protocol:** directly with the 5 R1 seeds (V12_5s), queued after LightGBM's 5-seed conformal layer (D64).
  **Rule, fixed before the result:** V12 replaces V9 as the candidate if its ensemble's median nRMSE is lower at
  15 min, no more than 0.5% higher at 1 h, and no more than 1% higher at any other horizon. The rule's target is
  15 min because the variant aims at the short-horizon gap (D50); the bound at 1 h is tighter because rule R1 is
  decided there. The diagnoses of F46, F49 and F52 are repeated on it.
- **Result (21 Nov 2026, 185 min): meets its rule; V12 replaces V9 as the candidate.** Ensemble median nRMSE at
  15 min / 30 min / 1 h / 2 h / 4 h / 6 h: 0.13290 / 0.15667 / 0.17782 / 0.20719 / 0.23154 / 0.20555, against V9's
  0.13320 / 0.15717 / 0.17848 / 0.20754 / 0.23241 / 0.20607 (−0.22, −0.32, −0.37, −0.17, −0.38, −0.25%).
  **Caveat, reported with the result:** the gain is real only at 15 and 30 min (8 and 7 of 10 units lower; mean over
  units −0.35 and −0.33%). From 1 h on the median falls but most units rise: at 1 h 2 of 10 units are lower (p
  0.13), the mean over units is +0.21%, and per unit the change runs from −0.71 to +0.69%; at 2–6 h the means are
  +0.09 to +0.39%. Every difference is below 1% and no p is below 0.13. Single seeds spread more than V9's: s.d. of
  the per-seed median 0.0035 at 1 h (V9 0.0028) and 0.0077 at 6 h (0.0031); at 1 h 0.17800–0.18644, mean 0.18090.
  The short-horizon diagnoses move as V11a's did: calmest-quartile 15-min pinball 31.7% above LightGBM's (V9
  40.4%), 30-min 16.8% (21.2%), but 1-h 10.2% (7.7%); clear-spell bias at 15 min −0.022 (−0.030). Against the four
  others (`nb5c_diag/vs_all/V12_5s.csv`): lowest at no horizon; at 1 h +0.15% against Chronos-2, −0.35% against
  TimeXer, −1.9% against LightGBM (6 of 10 units, p 0.77). By D69, if V13 meets its rule, V14 = V12 + V13's input.

### D68 — PVSetFormer stays the main model; the development target is to beat all four other forecasters [author decision, Phase 5]
- **Request:** the author, 21 Nov 2026, after F56: "i want honestly to keep my model the main one and become the best
  of all the 4 others, so please refine tuning the model and make it the best one, i can re train it in colab or
  what ever u want but the goal of this paper is to show that PVSetFormer is the best".
- **Change:**
  - PVSetFormer is the main model and the title stays the PVSetFormer title (D25). This agrees with rule R1 as it
    stands: the candidate V9 is 1.6% below LightGBM's ensemble at 1 h on the validation units (D60); R1 is still
    rerun on the final candidate at the freeze.
  - **Development target:** the PVSetFormer ensemble's median nRMSE below each of LightGBM's ensemble, TimeXer's
    ensemble, Chronos-2 and TimesFM 2.5 (the part-2d settings, D59) at every horizon, 1 h first. Scoreboard:
    `python tools/pvsf_vs_all.py <round>` (`results/nb5c_diag/vs_all/`). Each variant keeps its own keep rule, fixed
    before its result.
  - Development uses development data only (the 10 validation units, the index before 2021-10-05); the test events
    stay unseen (rule 8). Heavier rounds may run on Colab (the author's offer).
  - Fairness (D25, guide): the four other forecasters keep their frozen settings. An input added to PVSetFormer that
    LightGBM could also read (V13's daily statistics, D69) is reported as such, and before the paper credits a gain
    to the architecture, an ablation gives LightGBM the same input.
- **Starting point (V9_5s, `results/nb5c_diag/vs_all/V9_5s.csv`):** lowest of the five at no horizon. Against the
  lowest of the other four: +2.3% at 15 min (TimeXer), +0.6% at 30 min (LightGBM), +0.5% at 1 h, +2.2% at 2 h, +6.0%
  at 4 h and +3.0% at 6 h (Chronos-2).
- **Consequence:** the paper says PVSetFormer is the best forecaster only where the test run shows it, under the
  guide's 3% threshold and the paired tests (rules of truth 4 and 7); until then the must-not-claim list stands.

### D69 — PVSetFormer variant V13: the index at the target's time of day over the past 7 and 28 days [R1 round, Phase 5]
- **Reason:** F56 and D68: Chronos-2 is lower than V9 from 1 h on, most at 4 h (by 5.7%), and its 28-day context beats
  its 7-day context. PVSetFormer reads only the last 4 h and the index one day before the target time. At 4–6 h,
  what the index usually does at that time of day is the natural prior.
- **Change:** option `clim` (V13). For each horizon, the mean and s.d. of the index at the target's time of day over
  the past 7 days (at least 3 valid) and 28 days (at least 7 valid), with their flags: 6 more rows of the linear
  path (zero start, no weight decay; means as changes from k(t)). Every value lies at least 18 h before the issue
  time. The query tensor carries them after its 11 base columns; the decoder query and TimeXer read only the base
  columns. V9's setting (d 64, lr 10⁻³, weight decay 0.5); 224,641 parameters (+324). LightGBM's part-2a features do
  not include them (D68: an ablation follows if V13 is kept).
- **Checks:** V9_5s and TX1_5s reproduce exactly on their shortest tasks (5,022 rows each, max difference 0); the
  features equal a direct pandas computation (max difference 3·10⁻⁸) and do not change when the index from 17.75 h
  before the issue time onwards is replaced (causal); V13 starts at V9's outputs; the new rows receive a gradient;
  a 2-epoch run is finite and sorted.
- **Protocol:** directly with the 5 R1 seeds (V13_5s), queued after V12_5s. **Rule, fixed before the result:** V13
  replaces V9 as the candidate if its ensemble's median nRMSE is lower at 1 h and no more than 1% higher at any
  other horizon. If V12 (D67) and V13 both meet their rules, V14 combines them with 5 seeds.
- **Result (22 Nov 2026, 160 min):** the rule is met. Ensemble median nRMSE 0.13178 / 0.15625 / 0.17812 /
  0.20759 / 0.23022 / 0.20292 (15 min to 6 h); against V9 −1.06 / −0.59 / −0.20 / +0.02 / −0.94 / −1.53%, lower
  on 7 / 6 / 6 / 7 / 9 / 8 of 10 units (Wilcoxon p 0.010 at 4 h, 0.020 at 6 h); unit mean lower at every
  horizon; seed s.d. at 1 h 0.0011 (V9 0.0028). V13 is 0.17% above V12 at 1 h, so V12 stays the candidate and,
  as fixed above, V14 combines the two (D71). Lowest of the five forecasters at no horizon (F58).

### D70 — A Chronos-2 input for PVSetFormer (V15): Chronos-2 at every issue time of the validation units [author decision, Phase 5]
- **Request:** the author, 21 Nov 2026: "yes, add the chronos forcast as input too, but is this step is good and give
  a value to our model or not?"
- **Evidence before building (F57):** equal-weight averages of forecasts already run (`tools/combo_diag.py`, nothing
  fitted). PVSetFormer (V12) + Chronos-2 is below Chronos-2 alone at 30 min to 2 h and at 6 h (−0.02 to −1.1%) and
  above it at 15 min and 4 h; it is below V12 alone everywhere (−0.4 to −4.5%). At 2–6 h it is also below TimeXer +
  Chronos-2 (−0.7 to −1.5%) and LightGBM + Chronos-2 (−1.2 to −2.8%); at 15 min to 1 h the three pairs are within 1%.
- **Assessment given to the author:** the input should lower PVSetFormer's errors, mostly from 2 h, where its pairing
  with Chronos-2 beats the other pairings, so part of the gain belongs to PVSetFormer (the donors). Costs: the gain
  must be shown against TimeXer and LightGBM given the same input (D68), PVSetFormer then depends on a 120M-parameter
  pretrained model run at every issue time, and the paper's claim becomes "PVSetFormer improves on a foundation
  model", not "beats" it. Whether Chronos-2's pretraining data include this dataset has not been checked (this also
  applies to row A6a).
- **Change:**
  - `tools/make_nb5e.py` writes `results/nb5e_inputs/`: every issue time PVSetFormer trains on or forecasts on the 10
    validation units, from the fleet's start to each event's last NB5a slot (52,907, which include NB5a's 37,619; the
    latest on 12 Oct 2021, inside the validation units' own NB5a windows); the series is a byte copy of NB5b's. It
    also writes `notebooks/NB5e_colab.ipynb`: A6a's part-2d setting (Chronos-2, 1,344 daylight steps, covariates on),
    one part per event, resumable. `fm_infer.py --events` restricts a run to some events. Local smoke test (CPU, one
    event, 2 issue times): 12 rows, 165 s.
  - The Drive mirror `G:/My Drive/pv-cold-start-nb5e` (`make_drive_mirror.py --set nb5e`; 16 files, 1.71 MB, hashes
    checked); results come back with `fetch_drive_runs.py --set nb5e`.
  - Chronos-2 is zero-shot and its forecast at t uses data up to t only, so its forecasts at training and at forecast
    times are equally out of sample: no stacking leak.
  - Option `fm` (V15), on V12: the Chronos-2 quantiles at each horizon, as changes from k(t), and their flag, as more
    rows of the linear path (zero start, so V15 starts at V12).
- **Fairness:** before the paper credits PVSetFormer, TimeXer and LightGBM receive the same input (ablation rows), and
  PVSetFormer without it stays a row. At the test, Chronos-2 runs at every issue time of the test events, after the
  freeze.
- **Checks of option `fm` (synthetic Chronos-2 part for one event, the real parts not yet run):** V12_5s reproduces
  exactly on its shortest task (5,022 rows, max difference 0); `fm_array` places all 17,340 synthetic rows at their
  grid time and horizon and `samples` carries them with their flag; V15 starts at V12's outputs (224,871 parameters,
  +540); a unit weight on Chronos-2's median adds exactly (median − k(t)); the new rows get a gradient; a 2-epoch
  run is finite and sorted. `pvsf_dev.py` loads the parts when `fm=1`, prints their coverage and records their
  sha256 in the round's summary.
- **Colab run (the author, 22 Nov 2026, 01:00–02:24, 84 min of GPU):** `NB5e_colab` wrote the 10 parts; fetched
  with `fetch_drive_runs.py --set nb5e` (hashes checked). Checks (`check_nb5e.py`, scratch): every part names its
  event, the model revision and setting of NB5b's run, and the hashes of the local `nb5e_inputs`; 259,386 rows,
  exactly the in-day horizons of all 52,907 issue times, none repeated, none missing, quantiles finite and sorted;
  on all 184,353 rows of NB5b's run the largest difference is 1.2·10⁻⁶ (the run reproduces NB5b); the two pairs
  of events with identical inputs (SQ Apartment13-24 and 37-48, Zone A1 and A4) have identical forecasts.
- **V15's rule, fixed before its run (22 Nov 2026):** V15_5s = the candidate after D71's rule (V14 if it meets it,
  otherwise V12) plus `fm=1`, 5 R1 seeds. V15 replaces the candidate if its ensemble's median nRMSE is lower at
  1 h and no more than 1% higher at any other horizon. Whether a model that needs Chronos-2 at every issue time
  becomes the main model is the author's decision at the freeze (D50); what the paper may claim follows D72's
  rule. Queue (`queue_v15.py`, scratch): V14_5s, then D71's rule, V15_5s, TX2_5s, LGB_fm_seeds.
- **Result (22 Nov 2026, 141 min):** the rule is not met; V12 stays the candidate. V15_5s = V12_5s + `fm=1`
  (D71's rule kept V12); its log shows Chronos-2 present for 100.00% of the defined targets of each unit.
  - Ensemble median nRMSE 0.13170 / 0.15593 / 0.17898 / 0.20761 / 0.22966 / 0.20507 (15 min to 6 h).
  - Against V12: −0.90 / −0.47 / +0.65 / +0.20 / −0.81 / −0.24%, so 0.65% higher at 1 h.
  - By unit the input helps more than the medians show: the mean per-unit change is negative at every horizon
    (−0.22 / −0.25 / −0.61 / −1.18 / −2.13 / −2.84%), and V15 is lower on 8, 9 and 9 of 10 units at 2, 4 and 6 h (Wilcoxon p
    0.037, 0.004, 0.006); at 1 h on 7 of 10 (p 0.23). The rule, fixed before the
    run, uses the median over units and stays as fixed.
  - Single seeds at 1 h are lower than V12's (mean 0.17978 against 0.18090) and agree more
    (s.d. 0.0019 against 0.0035), but averaging the 5 seeds gains less (−0.45% against
    −1.70%).
  - Above Chronos-2 alone at every horizon (+1.52 / +1.14 / +0.80 / +2.20 / +4.75 / +2.51%), and above the plain equal average of V12
    and Chronos-2 (F57) at every horizon (+1.09 to +3.91%). Lowest of the five at no horizon.
  - The ablation and what the paper may claim: D72, F60.

### D71 — PVSetFormer variant V14: V12's short-horizon gate with V13's 7- and 28-day input [R1 round, Phase 5]
- **Reason:** V12 (D67) and V13 (D69) both met their rules, and D69 fixed in advance that V14 then combines them
  with 5 seeds. The two act on different parts: V12's gate scales the median change at 15 and 30 min; V13's input
  adds rows to the linear path and helps most at 4 and 6 h (F58).
- **Change:** no new code. `python tools/pvsf_dev.py --name V14_5s --seeds 5 --set fleet_token=1 balance=1 d=64
  lr=0.001 weight_decay=0.5 lin=1 vmed=1 vmed_n=2 clim=1`; 224,655 parameters (V12's 224,331 + 324, as built).
- **Rule, fixed at the run's start (22 Nov 2026, 01:45), before any result:** V14 replaces V12 as the candidate if
  its ensemble's median nRMSE is lower than V12's at 1 h and no more than 1% higher at any other horizon. Otherwise
  V12 stays the candidate (V13 is above V12 at 1 h, so it does not replace V12 under the same rule).
- **Next:** V15 (D70) adds the Chronos-2 input to whichever variant is the candidate when the author's `NB5e_colab`
  run is back.
- **Result (22 Nov 2026, 153 min):** the rule is not met; V12 stays the candidate.
  - Ensemble median nRMSE 0.13199 / 0.15817 / 0.18032 / 0.20989 / 0.23051 / 0.20514 (15 min to 6 h).
  - Against V12: −0.68 / +0.96 / +1.41 / +1.30 / −0.44 / −0.20%. It is lower at 15 min, 4 h and 6 h, but 1.41%
    higher at 1 h.
  - From 30 min to 2 h V14 is above both V12 and V13. At 4 h it keeps most of V13's gain (+0.13% against V13), at
    6 h little of it (+1.09%).
  - Every difference against V12 is below 1.5%, and none is consistent across units (5–8 of 10 lower, Wilcoxon
    p ≥ 0.38).
  - Single seeds at 1 h: mean 0.18232 (V12 0.18090, V13 0.18015), s.d. 0.0018 (V12 0.0035, V13 0.0011).
  - Lowest of the five forecasters at no horizon.
  - The queue then started V15_5s on V12 (D70), at 04:19.

### D72 — Ablation of the Chronos-2 input: TimeXer and LightGBM receive what V15 receives [fairness, Phase 5]
- **Reason:** D70 and D68. Before the paper credits PVSetFormer with a gain from Chronos-2's forecast, the other two
  trained forecasters get the same input under the same conditions. Otherwise a gain may belong to Chronos-2 alone.
- **Change:**
  - TimeXer, option `fm` (`timexer.py`): the same 10 features per horizon as V15's rows (Chronos-2's 9 quantiles at
    t + h as changes from k(t), times their flag, and the flag) through a zero-start per-horizon linear map `fm_w`
    (6 × 10 × 9 = 540 parameters, no weight decay, as for PVSetFormer's rows). Nothing else changes: TX2_5s = TX1's
    setting plus `fm=1` (37,764 parameters). TimeXer now also refuses PVSetFormer's options `vmed` and `clim`, which no
    TimeXer run used.
  - LightGBM: `FC.run_origin(..., extra=...)` appends further features after the 25 of part 2a (LightGBM only;
    `extra=None` is NB5a's path). `tools/r1_lgb_seeds.py --fm` appends Chronos-2's 9 quantiles at t + h as changes
    from k(t), NaN where absent (LightGBM's own missing-value handling), and writes `LGB_fm_seeds` (5 seeds, part-2a
    setting). It prints and records Chronos-2's coverage of NB5a's forecast slots (it stops below 99.9%) and of the
    issue-rule rows it trains on.
- **Equal treatment:** no forecaster is retuned for the input. PVSetFormer keeps its candidate's setting, TimeXer
  its CVX setting and LightGBM part 2a; same 5 seeds, slots and scorer. LightGBM's part-2a setting learns nothing at
  the shortest first origins (F59), so it cannot use the input there; the ablation reports this with its result.
- **LightGBM's setting stays (author decision, 22 Nov 2026):** asked whether to change it after F59, the author
  answered "u can leaving it as it is". Part 2a stays as rule 1 chose it, in every LightGBM row; F59 is reported as
  a caveat on the validation leads over LightGBM.
- **Rule, fixed before any run with the input (22 Nov 2026):** the paper may say that PVSetFormer uses the Chronos-2
  input better than the other trained forecasters at a horizon only if V15's ensemble median nRMSE there is lower
  than both TX2_5s's and LGB_fm_seeds's. It may say that PVSetFormer improves on Chronos-2 only where V15 is lower
  than Chronos-2 alone. Both apply to validation now; at the test, only where the test shows it (D68). Below 3% a
  difference is called level (guide §3.10). The six rows (V15, TX2_5s, LGB_fm_seeds and their bases) are reported
  whatever the outcome.
- **Checks** (`check_d72.py`, scratch; development data): TX1_5s reproduces exactly on its shortest task (5,022
  rows, difference 0); NB5a's LightGBM reproduces through the changed `run_origin` (5,060 rows, largest difference
  6·10⁻⁸); with a synthetic Chronos-2 part (17,125 rows), LightGBM's extra features equal the stored quantile minus
  k(t) exactly, and a fit with them gives finite forecasts on the same slots; TimeXer with `fm` starts at TX1's
  outputs exactly, has 540 more parameters (`fm_w`, in `NO_DECAY`), a unit weight on Chronos-2's median adds
  exactly (median − k_t) where present and nothing where absent, `fm_w` receives a gradient, and a 2-epoch run is
  finite and sorted.
- **Protocol:** after V15_5s, one 8-worker run at a time: TX2_5s (`pvsf_dev.py --name TX2_5s --seeds 5 --set
  arch=timexer d=32 lr=0.003 weight_decay=0.01 balance=1 fm=1`, which is TX1's configuration plus `fm`; TX1_5s
  took 21 min), then `r1_lgb_seeds.py --fm` (LGB_seeds
  took 9 min).
- **Scoring:** `python tools/fm_ablation.py` (CSV only, seconds) reads the six ensembles and Chronos-2 and
  TimesFM 2.5 at their part-2d settings, asserts the same slots, and applies this rule and V15's (D70) as written;
  it also reports each forecaster's gain from the input and the same comparisons without SQ567 and UG Hall2 2F
  (F59). Written before any run with the input; a dry run with stand-ins (V14_5s for V15, the bases for TX2 and
  LGB_fm) reproduced `vs_all/V14_5s.csv` exactly and gave zero gains for the stand-ins.
- **Result (22 Nov 2026; `tools/fm_ablation.py`, `results/nb5c_diag/fm_ablation/`):** TX2_5s took 21 min,
  LGB_fm_seeds 9 min; Chronos-2 present at 100.00% of every unit's slots in all three runs; LightGBM's
  `--check` reproduced NB5a (5,060 rows).
  - Gain from the input, ratio of medians at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h:
    - PVSetFormer (V15 vs V12): −0.90 / −0.47 / +0.65 / +0.20 / −0.81 / −0.24%;
    - TimeXer (TX2 vs TX1): −0.40 / +0.04 / +0.50 / −1.52 / −1.67 / −0.73%;
    - LightGBM (LGB_fm vs LGB_seeds): −0.29 / −0.67 / −0.89 / −2.51 / −2.18 / −3.32%, lower on 10 / 10 / 10 / 10 / 10 / 9 of 10 units
      (p ≤ 0.004).
  - **First rule** ("uses the input better": V15 below both TX2_5s and LGB_fm_seeds): met at 1 h, 4 h and 6 h, not
    at 15 min, 30 min or 2 h. Every difference is below 3% (largest 2.69%), so all are level (guide §3.10).
    The paper may not say that PVSetFormer uses the input better.
  - **Second rule** ("improves on Chronos-2": V15 below Chronos-2 alone): met at no horizon (+1.52 / +1.14 / +0.80 / +2.20 / +4.75 / +2.51%).
  - Without SQ567 and UG Hall2 2F (F59): V15 against TX2_5s +0.16 / −0.20 / −0.37 / −0.11 / −0.87 / −0.70%,
    against LGB_fm_seeds +0.86 / 0.00 / −0.78 / +1.06 / −0.73 / −2.84%, against Chronos-2
    −0.12 / +0.24 / +0.32 / +2.71 / +3.77 / +4.66%.
  - Lowest of the eight rows (the six, Chronos-2, TimesFM 2.5): LightGBM with the input at 15 min
    (0.12874); Chronos-2 alone from 30 min to 6 h. None of the three trained forecasters with the input is
    below Chronos-2 alone from 30 min (F60).

### D16 — pvlib 0.16.1 and ruptures 1.1.10 are installed locally and pinned [environment, Phase 0]
- **Request or reason:** both are in the guide's software list (§5.6) and were missing locally on 18 Nov 2026.
- **Change:** `pip install pvlib==0.16.1 ruptures==1.1.10`. A dry run first showed that nothing else would be
  installed or upgraded; numpy 1.26.4 and pandas 2.2.0 are unchanged. Both are pinned in `requirements.txt`, because
  solar position, clear sky and change points feed the results directly.
