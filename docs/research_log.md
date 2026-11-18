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
