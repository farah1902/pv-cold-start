# Research log

One entry per work session: what was asked, what was done, the key numbers, what is still open.

## 2026-11-17 — Kick-off read-in

- **Asked:** read the roadmap (`RESEARCH_AGENT_ROADMAP.md`), the full methodology and the HKUST dataset, then discuss.
- **Done:** read the roadmap (Parts 1–11), the methodology (969 lines), the Dryad README, the audit of 31 Oct and the
  13-page data paper. Checked the files: structure and headers of inverter, site, weather and metadata files; first
  and last rows of all 44 inverter files; site-file starts of the 18 event stations; Zone J2 and Zone L2 energy before
  their inverter files; metadata connection dates; CAMS headers; the git root.
- **Key results:** F01–F04, F06–F12, F15, F16. The folder had no repository of its own (D15).
- **Open:** the guide's decisions D1–D7.

## 2026-11-18 — Decisions and repository

- **Asked:** read the updated methodology and the review audit of 18 Nov; the author answered D1–D7 (accept, accept,
  ok, Colab ready, Solar Energy, yes to both, Morocco as recommended), approved the 17:55 handling and asked for the
  repository.
- **Done:**
  - Diffed the 2 Nov and 18 Nov versions of the guide: 14 scored events, 3 sensitivity, 2 removed; observed-start
    rule; primary horizon 1 h; drifted window by effect sizes; "stable" instead of "healthy"; issue window 06:00 to
    17:55 − h with the common target window 12:00–17:55; two-format parser; CAMS to re-download.
  - Recorded D01–D16 and F01–F16.
  - Moved the files into the roadmap layout (`data/README.md` maps old to new paths). Wrote
    `tools/make_data_manifest.py`; manifest of 165 files, 1,673.8 MB; `--check` reports 0 differences.
  - Installed pvlib 0.16.1 and ruptures 1.1.10 (dry run: no other package changed).
  - Created `CLAUDE.md`, `README.md`, `requirements.txt`, `.gitignore`, the `docs/` skeleton and `src/pvcold/`.
    Initialised the repository and pushed it to the private GitHub repository `farah1902/pv-cold-start`.
- **Open:** CAMS "Observed cloud" downloads (D14); the Safi companion papers (inverter AC ratings); the *Solar Energy*
  Guide for Authors (D05); next build step NB0 (environment, config, Drive mirror) and NB1 (HKUST audit).

## 2026-11-18 (afternoon) — CAMS all-sky and the Safi article

- **Asked:** the author downloaded the CAMS files and two PDFs, and asked for low-effort improvements before the
  notebooks.
- **Done:** checked and filed the CAMS all-sky files (F17, D17) and the Safi *Data in Brief* article (F18); the second
  PDF was a duplicate of the HKUST data paper and was deleted (identical SHA-256). Manifest: 168 files, 2,012.7 MB,
  `--check` 0 differences. Proposed improvements to the author (not yet decided).
- **Open:** the SETA 2021 article (Safi inverter details); the author's answer on the proposed improvements; NB0/NB1.

## 2026-11-18 (evening) — Improvements approved; model search for the deep-learning rows

- **Asked:** the author approved proposals 1, 2, 3, 5 and 6 (now D18–D22) and asked for a foundation model plus "the
  latest most advanced" trained model instead of the TCN.
- **Done:**
  - Filed the SETA screenshot (255 Wp confirmed; inverter details cut off; F18).
  - Searched the literature and opened the primary pages: the Chronos-2 model card; the TimeXer full text (exogenous
    inputs over the look-back only in the core setup, L2 loss, a future-exogenous variant in its Appendix H.1); the
    TiDE full text (covariates over look-back and horizon, MSE loss); Za'ter and Hodge (2026, arXiv:2604.22077), a
    power-system benchmark that includes TimeXer, TFT and foundation models; and Longarini et al. (2026), the closest
    competitor (F19).
  - Manifest regenerated (169 files).
- **Open:** the author's choice of models for the deep-learning rows; then NB0/NB1.

## 2026-11-18 (night) — Baselines fixed; the author's own transformer

- **Asked:** the author accepted Chronos-2, TimesFM, TabPFN-TS and TimeXer and asked for a new named transformer of
  their own, more optimized than TimeXer.
- **Done:** recorded D23 (baselines, TCN dropped) and D24 (own model, pending design approval). Checked prior art and
  names (F20): Simeunović et al. (TSTE), SolarCrossFormer (TSTE 2025), Solar-VLM (2026); no clash for the name
  candidates. Proposed a design to the author.
- **Open:** the author's approval of the name, the design and the selection rule; NB0/NB1.

## 2026-11-18 (late) — PVSetFormer approved; guide and title revised

- **Asked:** the author named the model PVSetFormer, approved R1 (with as many design rounds as needed) and R2, and
  asked for the methodology and the title to be changed before NB0 and NB1.
- **Done:** a web search found no model named PVSetFormer. Backed up the guide
  (`docs/history/methodology_2026-11-18_audit.md`) and applied 42 edits by an all-or-nothing script. A first run
  stopped on an ambiguous table-row prefix before writing anything; after the fix, all edits applied, and the guide
  grew from 978 to 1,007 lines, still LF. New title in the guide, `CLAUDE.md` and `README.md`; D25 recorded, D24
  approved; forbidden claims updated.
- **Open:** NB0 and NB1.

## 2026-11-18 (night) — NB0 and NB1 built and executed

- **Done:**
  - Wrote `src/pvcold/{config,io_hkust,audit}.py` and `tools/make_nb0.py`, `tools/make_nb1.py`.
  - The parser's assertions caught three issues before any result was produced: a model string missing from the AC
    table (SE82_8K_), six inverters without a model name, and the Indoor_Sport_Center spelling. All 104 data files
    now map one-to-one to the metadata.
  - NB0: data manifest check passes; Python 3.12.1, lightgbm 4.6.0, pvlib 0.16.1; 12 s.
  - NB1: 252 s. It reproduces F01, F02, F05, F06 and F16 from code; adds F21–F24 and D26.
  - Draft figures were checked by eye. The 30-day medians first bridged the dead-sensor gap and two legends overlapped
    the data; both were fixed (time-based windows on a daily index, legends moved) and NB1 was re-run.
- **Open, for the author:** Library start (F22): keep scored with a written exception, or move to the sensitivity
  set. Zone A2 inverters 2–3 can enter the DC/AC prior test (F21).
- **Next:** NB2 (QC, 15-min panel, time-label shift, events and donor sets).

## 2026-11-18 (night, cont.) — D27, D28 and NB2

- **Asked:** the author moved Library to the sensitivity set (13 scored) and included Zone A2 inverters 2–3 in the
  prior test, then asked for NB2.
- **Done:**
  - D27 and D28 applied to the guide (previous version in `docs/history/`), `config.py`, `CLAUDE.md`, the README and
    the handoff.
  - Wrote `src/pvcold/prep.py` and `tools/make_nb2.py`. The first run failed in its output cell
    (`Series.reset_index(names=…)` does not exist in pandas 2.2.0); nothing was written. Fixed and re-run: 28 s.
  - Findings F25–F27 and decision D29. Both draft figures (Fig. 1 timeline, time-label curves) checked by eye.
- **Next:** NB3 (median and censored index, donor gains, DC/AC priors, the final drift boundary, tuning on the
  validation units, then the freeze).

## 2026-11-19 — NB3: index, gains, priors, drift boundary, freeze part 1

- **Asked:** the author asked for NB3.
- **Done:**
  - Wrote `src/pvcold/fleet.py` and `tools/make_nb3.py`. A vectorised leave-one-out median replaced `nanmedian`
    (identical results, 24 times faster); the gain fit for the largest donor set fell from 73 s.
  - The first run was stopped by the agent: the generator still wrote the frozen YAML after the all-or-nothing
    rename (a failed edit). After the fix, a second run completed.
  - Looking at its figures showed that Fig. 3 was unreadable (sensor and CAMS indices at dawn divided by a clear sky
    near zero), and that the freeze hash included the writing time. Both were fixed and NB3 re-run; the selections and
    every table were reproduced.
  - A hash check then showed that the summary's hash did not match the YAML file: Windows text mode had turned
    its line endings into CRLF. The writer now writes LF everywhere. The first attempt at that fix was applied
    through a bash heredoc that turned the two characters of a newline escape into a real line break, so `audit.py`
    no longer compiled. The next run failed on import, yet reported exit code 0 because the last command of the
    pipeline was `tail`. Both were caught by checking file timestamps and bytes. The line was fixed with the editor,
    every module compiled, a writer self-test gave no CR byte, and NB3 was run once more with its own exit code.
  - Selections: k_min 0.3, censored index, prior G2, boundary 2023-02-17. Part 1 frozen
    (sha256 `cb671b7f67138e7e…`). F28-F32, D30, D31.
- **For the author:** F30 (the prior is worth less than a day of own data) changes the D22 headline. F28 (the censored
  index wins on only 4 of 10 validation units) limits what the paper can claim for censoring.
- **Next:** NB4 (sensor baselines A4, A4b, A4c: QC, night offset, monthly recalibration).

## 2026-11-19 — NB4: sensor and satellite index sources

- **Asked:** the author approved starting NB4.
- **Done:**
  - Prototyped each step of guide §4.2 on the 1-min data before writing code. Three problems came out: the guide's
    clear-day time-label method has no peak for one sensor (a cloud-transition lag against the fleet replaced it);
    the clear-sky detector's rescaling fails in months with few clear minutes (guards added); the raw BSRN upper
    limit would remove real readings after the drift (moved after calibration). All are in D32.
  - Wrote `src/pvcold/sensor.py` and `tools/make_nb4.py`. The gain fit sums its loss by day, so each donor is fitted
    once for all events (2,516 fits in 68 s); a check in the notebook shows it equals `fleet.fit_gain`.
  - NB4 ran once, without error (nbconvert exit code 0, 149 s); outputs newer than the code, no CR byte, the
    sensor-config hash matches its file, and the NB3 validation numbers are reproduced from the stored index.
  - Findings F33–F37 and decision D32. The draft figure (`fig_sensor_correction`) was checked by eye; it showed a
    dip before the step, which a daily check traced to one anomalous day (13 Feb 2023; F37).
- **For the author:** F35 (the fleet beats every irradiance source at h = 0 on all 10 validation units, and monthly
  recalibration does not help a stable sensor) and F37 (the step is on 14–15 Feb; the frozen boundary of 17 Feb is
  2–3 days late but changes no event's period).
- **Next:** NB5 (LightGBM bank, simple baselines, the hidden-unit test bed), then the development of PVSetFormer.

## 2026-11-20 — NB5a: forecasting development on the validation units

- **Asked:** the author approved starting NB5.
- **Done:**
  - Split NB5: development on the validation units now, the test run after the protocol freeze (D33).
  - Wrote `src/pvcold/forecast.py` (state, issue rules, LightGBM bank, baselines, composition, scores) and
    `tools/make_nb5a.py`. A smoke test of one origin ran in 56 s; fits run in parallel (8 workers).
  - The first run failed in the scoring cell: `x.gt` returned pandas' `DataFrame.gt` method instead of the `gt`
    column. The 15-min cross-validation had to be redone. Before re-running, the later cells were tested on a
    two-unit stand-in that wrote to a scratch folder (deleted afterwards). Bracket access is now used for column
    names.
  - The second run worked, but its bank (guide §5.2, index level) only tied persistence and lost to CLIPER on the
    validation units. Four variants were compared in `NB5a_variants`; the persistence-anchored change target won
    clearly and was adopted (D34). Rule 1 was re-run for it.
  - The re-run showed an exact tie (num_leaves 31 and 63 are the same model on development data), resolved by
    sort order. Rule 1's tie-break was completed (toward the guide's values, then fewer leaves) and NB5a re-run:
    the validation tables are identical and the setting is now 31, 0.05, 200. The variants notebook was made
    independent of NB5a's setting (pinned) and re-run.
  - Findings F38–F42, decisions D33 and D34.
- **For the author:** F39 (with the anchor, LightGBM beats persistence on all 10 units and CLIPER on 8 of 10 at
  1 h, but not at 4–6 h); F40 (intervals too narrow, the conformal layer is needed); F41 (validation histories are
  short, which matters for R1).
- **Next, before the freeze:** the conformal layer (D06), the inputs of the sensor and satellite rows for the same
  learner, PVSetFormer and TimeXer development (NB5c, Colab), the foundation-model settings (NB5b); then freeze
  part 2, the tag and the test run.

## 2026-11-20 — Conformal calibration (D06) on the validation units

- **Asked:** the author: "continue with the conformal calibration".
- **Done:**
  - Added the calibration path to `src/pvcold/forecast.py` (the bank's early-stopping predictions as the
    calibration set, leave-one-out pseudo priors, CQR scores, corrections, quantile scores) and
    `tools/make_nb5a_conformal.py`. A smoke test showed the forecasts unchanged (difference 0.0).
  - The keep rule was written in the notebook before the run. `NB5a_conformal` ran once (nbconvert exit code 0,
    about 8 min). It reproduces NB5a's LightGBM forecasts (6e-8) and raw coverage (exactly).
  - The layer is kept: 80% coverage 0.75–0.80 at every horizon, interval score lower everywhere. D35, F43. The
    draft reliability figure was checked by eye.
- **Next, before the freeze:** the inputs of the sensor and satellite rows (same learner), PVSetFormer and TimeXer
  development (NB5c, Colab GPU) with their own conformal layers, the foundation-model settings (NB5b); then freeze
  part 2, the tag and the test run.

## 2026-11-20 to 21 — PVSetFormer development (rule R1): V1, V2 and the search

- **Asked:** the author: "start PVSetFormer".
- **Done:**
  - Wrote `src/pvcold/setformer.py` (model, training, search fold), `tools/pvsf_dev.py` (one validation round) and
    `tools/pvsf_cv.py` (the LightGBM-budget search). D36 records the protocol.
  - V1, the guide's design, scored 0.1858 at 1 h against LightGBM's 0.1810. V2 added a fleet-summary token and a
    horizon-balanced loss: 0.1864 at 1 h, and better at 15 min (0.1422 → 0.1395), still worse than persistence there
    (0.1338).
  - The search CV2 ran in 84 min and chose d 32, lr 1e-3, weight decay 0.5. Its CV pinball is 0.07003 against
    LightGBM's 0.06855, with the gap at the short horizons (9% at 15 min, 4.4% at 1 h; 2.5% better at 6 h).
  - Every variant is in `docs/pvsetformer_log.md`.
- **V3 ran twice:** the first V3 run was reported stopped when the previous session ended (last log line at 22
  of 30 trainings), but the process outlived the session and finished at 00:23. Not knowing this, I re-ran V3 on
  21 Nov, chained with V4a (a linear path on the index lags, aimed at the short-horizon
  gap) and V4b (auxiliary donor-forecast loss, clipped readings one-sided). Both options default to off. They were
  smoke-tested, and a V1 training retrained with them present reproduced V1 exactly. The re-run finished at
  00:49 and overwrote the first run's folder. The two runs' `scores.csv` are identical (R1 0.18250), a check
  that rounds are deterministic. `log.csv` keeps both rows; the first is marked as the duplicate.
- **Author decision (21 Nov):** R1 compares 5-seed ensembles of both models (D37). Added `tools/r1_score.py`
  (shared scoring, reproduces V1's scores to 1e-16) and `tools/r1_lgb_seeds.py` (LightGBM refitted with 5 seeds; its
  check reproduces NB5a's forecasts to 6e-8). The LightGBM run follows the V3–V4b chain.
- **V4a, V4b, the LightGBM bar (21 Nov):** V4a, the linear path, scored 0.1795 at 1 h, the first variant below the
  single-seed bar. V4b, the auxiliary donor loss, scored 0.1890 and was rejected. LightGBM's 5-seed bar is 0.18130
  (single seeds 0.18090–0.18157). The 5-seed V4a round is running.
- **R2 models coded (21 Nov):** TimeXer (`src/pvcold/timexer.py`, written from the paper and a reading of the
  official code's structure; that repository declares no licence, so no code was copied) and the A6e option
  `summary_only`. D38 records them. Reading the paper showed that D23's "future-exogenous variant (Appendix H.1)" is
  only a qualitative showcase, so D38 corrects D23. Each PVSetFormer variant now has its own decision (D39–D44).
  Queued after V4a's 5 seeds: A6e (1 seed), TimeXer's search CVX, then its round TX1.
- **R1 decided (21 Nov):** the 5-seed V4a round (90 min) gives 0.18001 at 1 h against LightGBM's 0.18130. NB5c
  applied the rule: PVSetFormer becomes the main index forecaster (D45), configuration part 2c written. The margin is
  narrow: 4 of 10 units, Wilcoxon p = 1.0, and 3 of the 5 single seeds score above LightGBM's ensemble. The
  advantage is at 2–6 h; LightGBM leads at 15–30 min (F44, *provisional*). A6e, then TimeXer's search and round,
  follow in the queue.
- **PVSetFormer's conformal layer (21 Nov):** `NB5c_conformal` applies D35's rules unchanged to PVSetFormer's
  5-seed ensemble (D46). Kept: PICP80 at 1 h 0.713 → 0.799, IS80 lower on 8 of 10 units; 0.79–0.83 at every horizon
  (F45). Runtime 110 s.
- **A6e (21 Nov):** PVSetFormer without donor tokens scores 0.18056 at 1 h (single seed), against 0.17949 for V4a
  with the same seed. It is worse at 5 of 6 horizons, but by less than one seed's spread at 1 h. `A6e_5s` (5 seeds)
  is queued after TimeXer's search (CVX, running) and round (TX1), so that it compares with V4a_5s as ensembles.
- **Volatility diagnosis and V5 (21 Nov):** at the index level PVSetFormer's 10–90% width at 15 min goes from 0.32
  to 0.37 between the calmest and the most volatile quartile of the last hour's s.d., LightGBM's from 0.18 to 0.41.
  The calm quartile carries most of the 15-min deficit (F46, `tools/pvsf_vol_diag.py`). New options `vol` and
  `vgate` in `setformer.py` (zero start; V4a reproduces exactly; the features equal LightGBM's `sd_1h` and |`dk`|
  to 2e-7). V5a and V5b (D47, D48) are queued after A6e_5s.
- **TimeXer (21 Nov):** its search CVX chose d 32, lr 3e-3, weight decay 0.01 (CV pinball 0.06800, below
  LightGBM's 0.06855); its round TX1 scores 0.18174 at 1 h with one seed, better than V4a at 15 min and 2 h, worse at
  1, 4 and 6 h (D49). TX1_5s (5 seeds) is queued after V5b, so that the three learned forecasters compare as
  ensembles.
- **A6e with 5 seeds (21 Nov):** 0.17997 at 1 h against V4a_5s's 0.18001; equal at every horizon (below 0.6%),
  Wilcoxon p = 1.0. On validation the donor tokens add nothing over the fleet summary (F47, *strong*). This bears on
  the title and the novelty claim; raised with the author. V5a and V5b run next, then TX1_5s.
- **Author decisions (21 Nov):** keep developing PVSetFormer until the freeze (D50); LightGBM for the sensor rows
  A4 and A4b, with A4c = the main model plus the corrected sensor index (D51). The question wrongly listed A9 among
  the learner rows; the guide defines A9 as persistence of the satellite index, so it stays so (D51 corrected).
- **V5a, V5b, TimeXer with 5 seeds (21 Nov):** V5a makes the spread follow volatility but does not lower the pinball
  (rejected); V5b halves the calm-state gap at 15 min but loses the longer horizons (rejected). TimeXer's 5-seed
  ensemble scores 0.17845 at 1 h, below PVSetFormer (0.18001) and LightGBM (0.18130), none significant (F48). The
  diagnosis tool now also writes how far the median leaves persistence and its bias, by index level in calm states:
  PVSetFormer reverts toward the mean at 15 min (F49).
- **V6 and V7 options (21 Nov):** `hmask`, `hhead`, `donor_id` and `donor_rel` in `setformer.py` (D52–D55),
  zero start. Checks: V4a and TimeXer TX1 reproduce exactly after the static features gained a 7th column (the
  unit index); all four options start at V4a's outputs; a 2-epoch run with all four is finite and sorted. The four
  rounds run in sequence (about 90 min).
- **NB5d code (21 Nov):** `forecast.run_origin_source` (an external index in place of the fleet index; source-only
  features; the fleet's issue and target rules) and `tools/make_nb5d.py` (A4, A4b, A9, A9n on the validation units,
  each paired with fleet LightGBM on the same slots; priors recomputed from NB4's external gains and checked against
  NB4's). Smoke test on SQ567, first origin: 12 s, the same issue counts per horizon as the fleet rows, finite and
  sorted quantiles. Queued after the V6/V7 rounds.
- **A4c option (21 Nov):** `ext=sensor_corr` feeds the corrected sensor index into PVSetFormer's fleet token
  through a zero-start layer (D56). V4a, A6e and TX1 reproduce exactly; the option starts at V4a's outputs. A4c's
  development round is queued after NB5d.
- **V6/V7 results (21 Nov):** V6a rejected; V6b fixes most of the 15-min drift but costs 4–6 h; V7a and V7b are
  within single-seed noise of V4a, V7a better on 9 of 10 units at 1 h (D52–D55, F50; `tools/pvsf_vol_diag.py` for
  each round).
- **NB5d results (21 Nov):** 289 s, nbconvert exit 0. Fleet LightGBM beats the sensor-index LightGBM on all 10 units
  up to 1 h and is level from 2 h; the corrected sensor is worse than the raw one; the CAMS oracle bounds a satellite
  nowcast (F51, results_summary).
- **V8 options (21 Nov):** `hhead_n` in `setformer.py` (the per-horizon readout on the first n horizons; 0 = all).
  V4a and V6b reproduce exactly (a first version changed V6b's addition order and gave 2.4e-7; fixed before use).
  V8a (`hhead_n=1`) and V8b (`donor_id` + `donor_rel`) start at V4a's outputs; queued after A4c (D57, D58).
- **A4c result (21 Nov):** 21 min, exit 0. The corrected sensor index in PVSetFormer's fleet token changes the
  forecast by less than single-seed noise: +0.5% at 1 h (2 of 10 units better), −0.4% at 6 h (D56, F51).
- **V8 results (21 Nov):** V8a keeps V6b's 15-min gain (−2.3%) without its long-horizon loss but is +1.1% at 1 h
  (within the seed spread); 5 seeds queued (V8a_5s). V8b rejected (D57, D58, F50).
- **NB5b foundation models (21 Nov):** sources checked (model cards, READMEs, pyproject files, installed code). Chronos-2
  and TimesFM 2.5 installed in a separate `.venv_fm` (numpy 2, torch 2.15; the main environment untouched; pip first
  picked jax 0.2.22 without jaxlib and pandas 3, fixed and pinned in `requirements-fm.txt`). The weights downloaded
  without the expired stored token. `tools/fm_infer.py` and `tools/make_nb5b.py` (inputs, Colab inference, scoring);
  `NB5b_inputs` executed (37,619 issue times, sha256 manifest). Smoke tests on 30 issue times: Chronos-2 and TimesFM
  write the expected rows. Chronos-2 144 s, TimesFM 409 s without and 296 s with XReg, each writing sorted quantiles for the 6 horizons. The grid needs a GPU: Colab (D04, D59). TabPFN-TS (A6c) waits for the author.
- **NB5b scoring self-test (21 Nov):** `NB5b_foundation`'s cells run on a stand-in setting (LightGBM's 5-seed ensemble
  relabelled) reproduce LightGBM's 0.18130 and PVSetFormer's 0.18001 at 1 h on identical slots; the stand-in differs
  from LightGBM only by float32 rounding (about 1e-9 relative). Outputs removed after the check.
- **V8a with 5 seeds (21 Nov):** not kept. Ensemble vs V4a_5s: 15 min −1.6%, 30 min +1.2%, 1 h +0.3%, 6 h +1.1%;
  the 15-min clear-spell drift moves to 30 min (`tools/pvsf_vol_diag.py --pvsf V8a_5s`). D57, F50. Search CV4 on
  V4a's architecture started (D60; about 85 min).
- **Drift source (21 Nov):** `tools/pvsf_drift_diag.py`: PVSetFormer's 15-min reversion toward the last 4 h's mean is
  0.11–0.16 in every volatility quartile (truth 0.04 → 0.22), and V4a's linear path carries it (F52). Option `vlin`
  (V10a, D61) added and checked; `tools/learn_window.py` (D62) written: at the third origin, the gap to LightGBM
  grows with the origin (confounded with season). Queued after CV4: the matched-history run, then V10a_5s.
- **CV4 (21 Nov):** the D36 search on V4a's architecture chooses d 64, lr 1e-3, wd 0.5 (CV pinball 0.07059; V4a's
  setting 10th, 0.07237). V9_5s (D60's rule) queued after V10a_5s; the matched-history run (D62) started.
- **Matched history and V10a (21 Nov):** `learn_window.py` (39 min): at the third origin, with the first origin's
  amount of history, PVSetFormer trails LightGBM by 7.5% at 1 h; the late-origin gap is the period, not the data
  size; the extra 60 days help PVSetFormer most (F53, D62). V10a_5s (92 min): +0.06% at 1 h against V4a_5s, not kept
  (D61); its reversion slopes follow volatility but the calm-state gap stays. `pvsf_drift_diag.py` gains `--out` and
  a split of the decomposition by level (`decomposition_level`). V9_5s running since 15:16.
- **Level split and V11a (21 Nov):** the decomposition by level (`--out drift_level`, reproduces F52 exactly): in
  calm clear spells the 15-min median change −0.048 = head −0.020 + change terms −0.018 + other linear terms −0.010
  (truth median −0.0045) (F54). Option `vmed` (V11a, D63) added and checked; V11a_5s queued after V9_5s.
- **Author's answers (21 Nov):** LightGBM is a 5-seed ensemble at the test (D64): `tools/lgb_seeds_cal.py` (smoke
  test: 10,120 rows matched, max diff 6e-8) and `make_nb5c_conformal.py --model lgb`, queued after V11a_5s. TabPFN-TS
  waits for the licence (D65). Colab: minimal Drive mirror at `G:/My Drive/pv-cold-start` (16 files, 1.68 MB,
  smoke-tested from a copy) and `tools/fetch_drive_runs.py` for the way back (D66).
- **V9_5s (21 Nov, 154 min):** the CV4 setting lowers PVSetFormer's 1-h ensemble to 0.17848 (V4a 0.18001, LightGBM
  0.18130, TimeXer 0.17845): V9 is the new candidate (D60). Diagnoses `nb5c_diag/V9_5s/`, `drift_V9/` (`--out`):
  short horizons unchanged. V11a_5s running; then LightGBM's 5-seed conformal layer (D64).
- **V11a_5s (21 Nov, 112 min):** not kept (D63): +0.12% at 1 h, +1.6% at 4 h, but −0.9% at 15 min on 9 of 10
  units, calm 15-min gap 40 → 30% (F55). New option `vmed_n` (gate on the first n horizons); V12 = V9 + the gate on
  15 and 30 min (D67), queued after LightGBM's conformal layer. Checks: V11a_5s reproduces exactly, V12 starts at V9, the gate moves 15 and 30 min only.
