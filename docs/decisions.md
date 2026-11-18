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

### D16 — pvlib 0.16.1 and ruptures 1.1.10 are installed locally and pinned [environment, Phase 0]
- **Request or reason:** both are in the guide's software list (§5.6) and were missing locally on 18 Nov 2026.
- **Change:** `pip install pvlib==0.16.1 ruptures==1.1.10`. A dry run first showed that nothing else would be
  installed or upgraded; numpy 1.26.4 and pandas 2.2.0 are unchanged. Both are pinned in `requirements.txt`, because
  solar position, clear sky and change points feed the results directly.
