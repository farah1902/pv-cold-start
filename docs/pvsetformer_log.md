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
| V5a | 2026-11-21 | V4a + volatility features of the index (log s.d. over 1 h and 2 h, log \|Δk\|, with flags) → the 9 head outputs, zero start, no weight decay (D47) | 60,481 | 1 | 0.17950 | 3 of 10 | 0.1344 / 0.2134 | Rejected: the spread now follows volatility (15 min width 0.233 → 0.451, as LightGBM's) but the pinball does not improve, and 15 min, 4 h and 6 h are worse. The calm-state deficit is in the median (F49). 22 min |
| V5b | 2026-11-21 | V5a + a volatility gate 1 + tanh(w · vol + b) on the transformer's median shift, zero start (D48) | 60,523 | 1 | 0.18263 | 3 of 10 | 0.1335 / 0.2136 | Rejected: worse at every horizon except 15 min; halves the calm-state pinball gap at 15 min (41% → 22%) but costs the longer horizons. 25 min |
| V6a | 2026-11-21 | V4a + a diagonal self-attention mask in the decoder: each horizon query attends only to itself and the encoder (D52) | 60,157 | 1 | 0.18053 | 4 of 10 | 0.1333 / 0.2112 | Rejected: worse than V4a at 1 h (+0.6%) and 6 h (+1.9%), and the calm-state 15-min drift is not reduced (move 0.037 vs 0.034). The horizons' mutual attention is not the cause of F49 (F50). 22 min |
| V6b | 2026-11-21 | V4a + a per-horizon linear readout of the decoder output, added to the shared head, zero start (D53) | 61,939 | 1 | 0.18024 | 5 of 10 | 0.1311 / 0.2204 | Not kept as is: best 15 min so far (−2.1% vs V4a, 8 of 10 units; clear-spell bias −0.031 → −0.013), but 4 h +5.2% and 6 h +6.3%. Led to V8a (the readout at 15 min only). 20 min |
| V7a | 2026-11-21 | V4a + a learned identity embedding per donor, zero start (D54) | 62,205 | 1 | 0.17938 | 4 of 10 | 0.1337 / 0.2075 | Within 0.11% of V4a at every horizon, but better at 1 h on 9 of 10 units (same seed). Kept for the combination V8b. 22 min |
| V7b | 2026-11-21 | V4a + each donor's implied index minus the campus index, per step, into the donor token, zero start (D55) | 60,317 | 1 | 0.17927 | 4 of 10 | 0.1337 / 0.2058 | Lowest single-seed 1 h so far (−0.1%); 2 h −0.5%, 6 h −0.7%, CRPS at 1 h −0.4%; better at 1 h on 5 of 10 units. Within single-seed noise; kept for V8b. 21 min |
| V8a | 2026-11-21 | V4a + the per-horizon readout of V6b on the 15-min horizon only (`hhead_n=1`, D57) | 60,454 | 1 | 0.18138 | 4 of 10 | 0.1308 / 0.2089 | Best 15 min so far (−2.3% vs V4a, 7 of 10 units) and the long horizons kept (6 h +0.8%), but 30 min +1.4%, 1 h +1.1% (2 of 10 units better). Within the single-seed spread at 1 h: checked with 5 seeds (V8a_5s). 24 min |
| V8b | 2026-11-21 | V4a + donor identity and donor deviation together (V7a + V7b, D58) | 62,365 | 1 | 0.18000 | 4 of 10 | 0.1337 / 0.2060 | Rejected: within ±0.8% of V4a at every horizon; no better than V7a or V7b alone. The donor tokens still add nothing measurable (F47). 29 min |
| V8a_5s | 2026-11-21 | V8a with the 5 R1 seeds (D37) | 60,454 | 5 | 0.18061 (ensemble; single seeds 0.17935–0.18482, mean 0.18215, s.d. 0.0025) | 4 of 10 vs LightGBM; 2 of 10 vs V4a_5s | 0.1309 / 0.2090 | Not kept: against V4a_5s, 15 min −1.6% (7 of 10 units, p 0.28) but 30 min +1.2% (1 of 10), 1 h +0.3%, 6 h +1.1%. The 15-min drift is removed but moves to 30 min (F50). 96 min |
| CV4 | 2026-11-21 | The D36 search (18 settings × 3 folds, development index) on V4a's own architecture (D60) | 224,317 (chosen) | 1 | — | — | — | Chose d 64, lr 1e-3, wd 0.5: CV pinball 0.07059; V4a's setting 10th of 18 (0.07237). The linear path does not lower the CV pinball (CV2 on V2: 0.07003). V9 = V4a with this setting runs with 5 seeds. 85 min |
| V10a_5s | 2026-11-21 | V4a + a volatility gate exp(u · vol + b) per horizon on the median coefficients of the linear path's change terms (D61), 5 R1 seeds | 60,199 | 5 | 0.18011 (ensemble; single seeds 0.17908–0.18331, mean 0.18114, s.d. 0.0018) | 4 of 10 vs LightGBM; 7 of 10 vs V4a_5s | 0.1324 / 0.2064 | Not kept (rule: lower at 1 h): +0.06% at 1 h, −0.4% at 15 min, +0.5% at 2 h, every p ≥ 0.27. The reversion now follows volatility (15-min slope 0.094 → 0.183), but the calm-state pinball gap (39%) and the clear-spell bias (−0.028) stay: the reversion is not the cause. 92 min |

**R1 decision (21 Nov 2026, D45):** `notebooks/NB5c_R1_decision.ipynb` compared the 5-seed ensembles at 1 h:
PVSetFormer (V4a) 0.18001, LightGBM 0.18130. PVSetFormer becomes the main index forecaster, with 6 variants tried
before the decision. The margin is within the spread of PVSetFormer's single seeds (F44). Configuration part 2c:
`results/nb5c_r1/r1_config_part2c.yaml`.

**Rule R2 runs (not design variants, D38).** A6e is the final variant (V4a) without donor tokens, set attention or
pooling: one fleet-summary token per patch. Same setting, no search.

| Run | Date | What | Parameters | Seeds | nRMSE 1 h | Units won at 1 h | nRMSE 15 min / 6 h | Reading |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A6e | 2026-11-21 | V4a with `summary_only=1` | 46,621 | 1 | 0.18056 | 3 of 10 vs LightGBM (0.18098); 3 of 10 vs V4a at the same seed | 0.1356 / 0.2108 | Against V4a at the same seed (20261119): worse at 5 of 6 horizons, by 0.4–1.7% in nRMSE (1 h +0.6%, 15 min +1.3%, 6 h +1.7%), level at 2 h; CRPS worse at every horizon (+0.3% to +2.5%). The donor tokens help a little, but at 1 h the gap is within one seed's spread (s.d. 0.0014). A 5-seed run (A6e_5s) is queued. 5 min |
| CVX | 2026-11-21 | TimeXer search (D38), the shared 18 settings × 3 folds | 37,224 (chosen) | 1 | — | — | — | Chose d 32, lr 3e-3 (the grid's largest), weight decay 0.01: CV pinball 0.06800, below LightGBM's 0.06855 and PVSetFormer's CV2 0.07003 (searched on V2). 17 min |
| TX1 | 2026-11-21 | TimeXer with the CVX setting (D49) | 37,224 | 1 | 0.18174 | 3 of 10 vs LightGBM (0.18098); 4 of 10 vs V4a at the same seed | 0.1318 / 0.2123 | Against V4a at the same seed: better at 15 min (nRMSE −1.5%, CRPS −4.4%) and 2 h, worse at 1, 4 and 6 h (+1.3% to +2.4%). Close to both learned baselines; 5 seeds queued (TX1_5s). 4.5 min |
| A6e_5s | 2026-11-21 | A6e with the 5 R1 seeds (D37) | 46,621 | 5 | 0.17997 (ensemble; single seeds 0.17935–0.18233, mean 0.18041, s.d. 0.0012) | 5 of 10 vs LightGBM's ensemble (0.18130); 3 of 10 vs V4a_5s | 0.1331 / 0.2069 | **Equal to V4a_5s at every horizon** (differences below 0.6% in nRMSE, below 1% in CRPS; Wilcoxon p = 1.0 at 1 h): the donor tokens add nothing measurable on validation (F47). 20 min |
| TX1_5s | 2026-11-21 | TimeXer (CVX setting) with the 5 R1 seeds | 37,224 | 5 | 0.17845 (ensemble; single seeds 0.17961–0.18208, mean 0.18109, s.d. 0.0011) | 5 of 10 vs LightGBM's ensemble; 6 of 10 vs V4a_5s | 0.1301 / 0.2091 | Lowest ensemble at 1 h, but level with PVSetFormer and LightGBM (Wilcoxon p ≥ 0.23 at every reported horizon; F48). Better than PVSetFormer up to 1 h, worse at 2–6 h. 21 min |

**Design round V5 (21 Nov 2026).** The volatility diagnosis F46 (`tools/pvsf_vol_diag.py`) locates the 15-min
deficit: PVSetFormer's interval width hardly reacts to recent volatility. V5a (D47) adds the index's own volatility
features to the head; V5b (D48) also gates the transformer's median shift by them. Both start exactly at V4a and
are queued (1 seed each, paired with V4a's single-seed round).

**Author decision after A6e (D50):** keep developing until the freeze, aiming to make the donors useful and to close
the short-horizon gap; the main model and the title are decided at the freeze.

**Design rounds V6 and V7 (21 Nov 2026, D50).** V6a (D52) and V6b (D53) address the short-horizon median (F49):
horizons kept apart in the decoder, and a per-horizon readout. V7a (D54) and V7b (D55) try to make the donors
useful (F47): a learned identity per donor, and each donor's deviation from the index. All four start exactly at V4a
(checked) and run with one seed, paired with V4a's single-seed round.

**Sensor ablation A4c (D51, D56; not a design variant).** V4a plus the corrected sensor index in the fleet token,
zero start, 60,445 parameters, 1 seed: 1 h 0.18038 (V4a 0.17949 at the same seed; better on 2 of 10 units),
15 min / 6 h 0.1349 / 0.2065 (V4a 0.1339 / 0.2073). The sensor does not help (F51). 21 min.

**Design round V8 (21 Nov 2026, D50).** From F50: V8a (D57) keeps V6b's own readout for the 15-min horizon only,
where it removed most of the drift, and leaves the other horizons on the shared head. V8b (D58) combines the two
donor options V7a and V7b. Both start exactly at V4a (checked) and run with one seed after A4c.

**Noise in single-seed rounds (21 Nov 2026, F50).** A round with one seed is paired with V4a at the same seed, but
the training paths diverge, so the pairing does not remove the seed spread: V4a's single seeds at 1 h have s.d.
0.0014 (about 0.8%). Differences below about 2% in one round are not evidence either way; candidates that matter go
to 5 seeds (D37). V8a_5s is the first such check.

**V8a with 5 seeds, and search CV4 (21 Nov 2026).** V8a_5s keeps the 15-min gain (−1.6%) but loses at 30 min and
1 h, and its seeds spread more: not kept (D57). The diagnosis shows the drift moving from 15 to 30 min, so a readout
per horizon only shifts the problem (F50). Next, CV4 (D60) repeats the shared search on V4a's own architecture,
because CV2 ran before the linear path existed.

**Source of the drift, and V10a (21 Nov 2026).** The regression of each median change on the last 4 hours' mean
(F52) shows that PVSetFormer's reversion at 15 and 30 min is nearly the same in calm and volatile states, while the
data's rises steeply with volatility. Refitting V4a on three tasks and splitting its median change shows that the
linear path carries this reversion, not the transformer. V10a (D61) lets a volatility gate scale the linear path's
median coefficients on the change terms; it runs directly with 5 seeds after CV4 and the matched-history
diagnostic (D62).

**V10a and the matched-history check (21 Nov 2026).** V10a (D61) makes the linear path's reversion follow
volatility as the data's does, yet its scores equal V4a's and the calm-state deficit stays: the reversion toward the
4-h mean is not what costs the short horizons. The matched-history check (D62, F53) shows that PVSetFormer's growing
gap at later origins comes from the period, not from the amount of history, and that the extra history helps it
more than LightGBM. Next: where the level-dependent calm-state bias comes from (head or linear path), with V9_5s
(the CV4 setting) running.
