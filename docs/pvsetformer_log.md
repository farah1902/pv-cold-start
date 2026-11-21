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

**R1 bar:** LightGBM's median validation nRMSE at 1 h = **0.18098** (NB5a, D33, D34), the reference for the
single-seed rounds below. The decision itself compares 5-seed ensembles of both models (D37, the author's choice):
PVSetFormer becomes the main index forecaster only if its ensemble's value is lower than LightGBM's ensemble's
(`results/nb5c_variants/LGB_seeds/`) before the freeze.

**LightGBM's 5-seed bar (21 Nov 2026):** ensemble **0.18130** at 1 h; the five seeds alone give 0.18090–0.18157 (mean 0.18123, s.d. 0.00025). Seed averaging barely moves LightGBM: its ensemble is better than NB5a's single seed on 7 of 10 units at 1 h, but its median is 0.0003 higher. Runtime 8.6 min; the reproduction check passed.

**Caveat:** the design rounds and the final R1 comparison use the same 10 validation units, so the comparison
favours the model that had more rounds (PVSetFormer; LightGBM had 4, D34). The test run is the unbiased check.

| Variant | Date | Change from the previous variant | Parameters | Seeds | nRMSE 1 h (R1) | vs LightGBM, units won at 1 h | nRMSE 15 min / 6 h | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1 | 2026-11-20 | Guide §5.4 design: donor tokens (implied index, clip and validity flags over 4 h in 1-h patches; static gain, DC/AC, metadata flag, tilt class), set attention across donors, attention pooling to 4 sky tokens, causal temporal encoder with sun-geometry positions, 6 horizon queries (future geometry, index one day earlier), monotone 9-quantile head on the change from persistence (D34, zero-initialised). d 64, 2 + 2 layers, dropout 0.1, donor dropout 0.1, AdamW 1e-3, weight decay 0.01 | 221,065 | 1 | 0.1858 | 1 of 10 | 0.1422 / 0.2176 | Worse than LightGBM (0.1810) by 2.7%; worse than persistence at 15 min (0.1338). It sees only donors, not the aggregate index, and the loss is dominated by long horizons |
| V2 | 2026-11-20 | V1 + a fleet-summary token per patch (the index over the patch, its validity, spread, clipped share and donor count) + a horizon-balanced loss (each horizon's pinball divided by persistence's mean error on the training pairs) | 221,833 | 1 | 0.1864 | 2 of 10 | 0.1395 / 0.2168 | No gain at 1 h (within single-seed noise); fixes the short horizons (15 min 0.1422 → 0.1395). Kept as the base of the hyperparameter search |
| CV2 | 2026-11-20 | Hyperparameter search on V2, the LightGBM budget: d ∈ {32, 64} × lr ∈ {3e-4, 1e-3, 3e-3} × weight decay ∈ {0.01, 0.1, 0.5}, 3 monthly folds on the development index (D36) | 57,673 (chosen) | 1 | — | — | — | Chose d 32, lr 1e-3, weight decay 0.5: CV pinball 0.07003 vs LightGBM's 0.06855 (2.1% worse). By horizon: 9.0% worse at 15 min, 4.4% at 1 h, 2.4% at 2 h, even at 4 h, 2.5% better at 6 h. Weight decay barely matters (the three values within 0.001 at lr 1e-3, identical to 4 decimals at lr 3e-4), so the choice says d 32 and lr 1e-3, not "strong shrinkage". Runtime 84 min |
| V3 | 2026-11-21 | V2 with the CV2 setting: d 32, lr 1e-3, weight decay 0.5 (2 + 2 layers, 4 heads unchanged) | 57,673 | 1 | 0.1825 | 1 of 10 | 0.1372 / 0.2138 | Best so far: the gap at 1 h falls from 2.7% (V1) to 0.8%, but LightGBM is still better on 9 of 10 units, and at 15 min the model is still worse than persistence (0.1338). CRPS behind LightGBM at every horizon except 6 h (0.1142 vs 0.1174). Mean best epoch 24; 35 min. Base of V4a and V4b |
| V4a | 2026-11-21 | V3 + a linear path: per horizon, a linear map (zero start, no weight decay) from the index lags as change from k(t), their flags, σ, c, n and the horizon query to the 9 head outputs, added to the transformer's | 60,157 | 1 | 0.1795 | 4 of 10 | 0.1339 / 0.2073 | First variant below the single-seed bar (0.8% better), within single-seed noise (about ±0.003). Better than LightGBM in nRMSE at 1, 2, 4 and 6 h, equal at 30 min, behind at 15 min (0.1292; now level with persistence). CRPS better from 2 h on, slightly behind up to 1 h (1 h: 0.0944 vs 0.0939). Mean best epoch 17; 21 min |
| V4b | 2026-11-21 | V3 + an auxiliary loss on the donors' own futures (weight 0.5): each donor's implied index at t + h is forecast as the aggregate median plus a donor offset (from the donor's token at the issue patch and the horizon's decoder output); median loss, one-sided for clipped readings | 59,786 | 1 | 0.1890 | 1 of 10 | 0.1435 / 0.2227 | Rejected: worse than V3 at every horizon (1 h +3.6%, 15 min 0.1372 → 0.1435), CRPS worse too. The donor targets, coupled to the aggregate median, pull it toward donor-level noise. Not combined with V4a. Mean best epoch 30; 37 min |
| V4a_5s | 2026-11-21 | V4a with the 5 R1 seeds (D37); ensemble = the mean of the sorted quantiles across the seeds, sorted again | 60,157 | 5 | 0.18001 (ensemble; single seeds 0.17949–0.18281, mean 0.18104, s.d. 0.0014) | 4 of 10 against LightGBM's ensemble (0.18130) | 0.1329 / 0.2068 | **R1 met (D45): PVSetFormer becomes the main index forecaster.** Narrow at 1 h: Wilcoxon p = 1.0 across units; 2 of the 5 single seeds beat LightGBM's ensemble. Clear from 2 h (8, 10 and 9 units of 10 at 2, 4 and 6 h); LightGBM keeps 15–30 min (F44). 90 min |

**R1 decision (21 Nov 2026, D45):** `notebooks/NB5c_R1_decision.ipynb` compared the 5-seed ensembles at 1 h:
PVSetFormer (V4a) 0.18001, LightGBM 0.18130. PVSetFormer becomes the main index forecaster, with 6 variants tried
before the decision. The margin is within the spread of PVSetFormer's single seeds (F44). Configuration part 2c:
`results/nb5c_r1/r1_config_part2c.yaml`.

**Rule R2 runs (not design variants, D38).** A6e is the final variant (V4a) without donor tokens, set attention or
pooling: one fleet-summary token per patch. Same setting, no search.

| Run | Date | What | Parameters | Seeds | nRMSE 1 h | Units won at 1 h | nRMSE 15 min / 6 h | Reading |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A6e | 2026-11-21 | V4a with `summary_only=1` | 46,621 | 1 | 0.18056 | 3 of 10 vs LightGBM (0.18098); 3 of 10 vs V4a at the same seed | 0.1356 / 0.2108 | Against V4a at the same seed (20261119): worse at 5 of 6 horizons, by 0.4–1.7% in nRMSE (1 h +0.6%, 15 min +1.3%, 6 h +1.7%), level at 2 h; CRPS worse at every horizon (+0.3% to +2.5%). The donor tokens help a little, but at 1 h the gap is within one seed's spread (s.d. 0.0014). A 5-seed run (A6e_5s) is queued. 5 min |

**Design round V5 (21 Nov 2026).** The volatility diagnosis F46 (`tools/pvsf_vol_diag.py`) locates the 15-min
deficit: PVSetFormer's interval width hardly reacts to recent volatility. V5a (D47) adds the index's own volatility
features to the head; V5b (D48) also gates the transformer's median shift by them. Both start exactly at V4a and
are queued (1 seed each, paired with V4a's single-seed round).
