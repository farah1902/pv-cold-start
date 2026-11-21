# PVSetFormer development log (rule R1)

Every PVSetFormer variant tried is listed here, in order, with what changed and its validation result (D25, D36).
Development data only: the 10 validation units and the fleet index before 2021-10-05. The test events are never
used. The number of variants is reported in the paper.

**Protocol (D36).** Each variant runs with `python tools/pvsf_dev.py --name <V> --seeds <n> --set key=value`. The
runner uses NB5a's protocol: the same units, origins (s, s + 30 d, s + 60 d), issue rules and composition with the
prior. Training uses early stopping on the last 20% of the training issue times, then a refit for the best number of
epochs. Scores come from exactly the slots NB5a scored, so the LightGBM numbers compare directly. Outputs:
`results/nb5c_variants/<V>/` (scores, per-training diagnostics, summary; forecasts as git-ignored Parquet) and one
row in `results/nb5c_variants/log.csv`.

**R1 bar:** LightGBM's median validation nRMSE at 1 h = **0.18098** (NB5a, D33, D34). PVSetFormer becomes the main
index forecaster only if its value, computed the same way, is lower before the freeze.

**Caveat:** the design rounds and the final R1 comparison use the same 10 validation units, so the comparison
favours the model that had more rounds (PVSetFormer; LightGBM had 4, D34). The test run is the unbiased check.

| Variant | Date | Change from the previous variant | Parameters | Seeds | nRMSE 1 h (R1) | vs LightGBM, units won at 1 h | nRMSE 15 min / 6 h | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1 | 2026-11-20 | Guide §5.4 design: donor tokens (implied index, clip and validity flags over 4 h in 1-h patches; static gain, DC/AC, metadata flag, tilt class), set attention across donors, attention pooling to 4 sky tokens, causal temporal encoder with sun-geometry positions, 6 horizon queries (future geometry, index one day earlier), monotone 9-quantile head on the change from persistence (D34, zero-initialised). d 64, 2 + 2 layers, dropout 0.1, donor dropout 0.1, AdamW 1e-3, weight decay 0.01 | 221,065 | 1 | 0.1858 | 1 of 10 | 0.1422 / 0.2176 | Worse than LightGBM (0.1810) by 2.7%; worse than persistence at 15 min (0.1338). It sees only donors, not the aggregate index, and the loss is dominated by long horizons |
| V2 | 2026-11-20 | V1 + a fleet-summary token per patch (the index over the patch, its validity, spread, clipped share and donor count) + a horizon-balanced loss (each horizon's pinball divided by persistence's mean error on the training pairs) | 221,833 | 1 | 0.1864 | 2 of 10 | 0.1395 / 0.2168 | No gain at 1 h (within single-seed noise); fixes the short horizons (15 min 0.1422 → 0.1395). Kept as the base of the hyperparameter search |
| CV2 | 2026-11-20 | Hyperparameter search on V2, the LightGBM budget: d ∈ {32, 64} × lr ∈ {3e-4, 1e-3, 3e-3} × weight decay ∈ {0.01, 0.1, 0.5}, 3 monthly folds on the development index (D36) | 57,673 (chosen) | 1 | — | — | — | Chose d 32, lr 1e-3, weight decay 0.5: CV pinball 0.07003 vs LightGBM's 0.06855 (2.1% worse). By horizon: 9.0% worse at 15 min, 4.4% at 1 h, 2.4% at 2 h, even at 4 h, 2.5% better at 6 h. Weight decay barely matters (the three values within 0.001 at lr 1e-3, identical to 4 decimals at lr 3e-4), so the choice says d 32 and lr 1e-3, not "strong shrinkage". Runtime 84 min |
