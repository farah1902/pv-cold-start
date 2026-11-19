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
