# Results summary — the single source of truth for numbers

Every number the paper cites must appear here, with the result file it comes from. Values are stored unrounded in
the result files; this page prints them with half-up rounding from the unrounded values (roadmap Part 6).

**Status (18 Nov 2026): data audit (NB1) done; no forecasting results yet.**

**Not citable:** the pilot figures in the research guide (Status section and §3.5) come from an earlier, simplified
pilot run outside this repository (Haurwitz clear sky, scikit-learn boosting, the earlier 19-event list). They cannot
be reproduced from this repository and must never be cited. NB3, NB5 and NB6 replace them.

## Data inventory (NB1)
Source: `results/nb1_audit/summary.json` and the CSV files beside it (run of 18 Nov 2026, 252 s).

| Quantity | Value | Source file |
| --- | --- | --- |
| Stations, inverters (metadata) | 60, 67 | units_stations.csv, units_inverters.csv |
| Inverter files; timestamp formats (iso / year-month-day) | 44; 31 / 13 | inventory_inverters.csv |
| 15-min site files; formats | 37; 34 / 3 | inventory_sites_15min.csv |
| Hourly site files; formats | 23; 16 / 7 | inventory_sites_1h.csv |
| Inverter slots per day (mode); first and last slot | 144; 06:00, 17:55 | inventory_inverters.csv |
| NA share of inverter power: median, max | 0.062, 0.129 (Zone A7) | inventory_inverters.csv |
| AC rating within 2% of observed p99.9 | 33 of 44 | metadata_check.csv |
| Site files not starting on the 1st (15 min; 1 h) | 5 of 37; 23 of 23 | inventory_sites_*.csv |
| Evening energy after 18:00: median per station (whole period); June calendar-month median | 0.19%; 0.54% | evening_share.csv |
| Zone D station / inverter 2, Jan–Oct 2022 monthly medians | 1.67–1.73 | zone_d_ratio.csv |
| Inverter files producing on day 1 | 43 of 44 | inventory_inverters.csv |
| Sensor drift date: vs CAMS; vs fleet proxy (one-break segmentation) | 2023-02-14; 2023-02-17 | summary.json |
| Sensor / CAMS daily irradiation, yearly median 2021 / 2022 / 2023 | 0.721 / 0.762 / 1.126 | sensor_daily.csv |
| Dead-sensor days (sensor / CAMS < 0.3) | 77 (2021-03-02 to 2022-05-23) | summary.json |
| Maximum 1-min GHI reading | 3,608.6 W/m² (Feb 2023) | sensor_monthly.csv |

## Events (NB2)
Source: `results/nb2_panel/summary.json`, `events.csv`, `units.csv`, `qc_flag_shares.csv` (run of 18 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| Time-label shift: inverter files; site files | +3.0 min; +11.0 min (same 15-min slots) | label_offset_*.csv |
| Valid share of daylight 15-min slots after each unit starts | 0.961 | NB2 notebook output |
| Clipped share (y ≥ 0.97): median, max per unit | 0.0025, 0.033 | NB2 notebook output |
| Outage share of daylight 5-min values: median, max | 0.0002, 0.0599 (Indoor Sports Centre) | qc_flag_shares.csv |
| Events: scored / sensitivity / validation; all eligible | 13 / 4 / 10; yes | events.csv |
| Donors at start: scored minimum; validation minimum | 20; 8 (SQ567) | events.csv |
| Scored events by provisional sensor period | 8 stable, 5 drifted | events.csv |
| Hidden-unit test bed units (stations) | 31 (29) on 2022-04-01; 38 (33) on 2023-04-01 | testbed.csv |

## Index, gains and prior (NB3)
Source: `results/nb3_index/summary.json` and the CSV files beside it (validation units only for every selection).

| Quantity | Value | Source file |
| --- | --- | --- |
| Validation nRMSE (same time, oracle gain) by k_min 0.3 / 0.5 / 0.7 | 0.08127 / 0.08135 / 0.08149 | validation_kmin.csv |
| Validation nRMSE, censored vs median index; censored wins | 0.0797 vs 0.0813; 4 of 10 | validation_estimator.csv |
| Validation median abs. gain error G0 / G1 / G2 | 0.1125 / 0.0438 / 0.0401 | validation_priors.csv |
| Validation nRMSE with prior gain G0 / G1 / G2 | 0.0909 / 0.0868 / 0.0870 | validation_priors.csv |
| Selected: k_min, estimator, prior | 0.3, censored, G2 | summary.json |
| Drift boundary: fleet; CAMS | 2023-02-17; 2023-02-14 | summary.json |
| Scored events stable / drifted | 8 / 5 | event_periods.csv |
| w0 (days): scored median (range); validation median | 0.43 (0.24-1.14); 0.29 | priors.csv |
| Frozen configuration part 1, sha256 | `cb671b7f67138e7e…` | frozen_config_part1.yaml |

## Sensor and satellite index sources (NB4)
Source: `results/nb4_sensor/summary.json` and the CSV files beside it (run of 19 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| Lag behind the inverter clock: sensor; CAMS (peak, whole minutes) | 3.32 min, 3; 5.02 min, 5 | lag_peaks.csv |
| Quarterly lag range: sensor; CAMS | 2.67–3.88 min; 0.74–5.71 min | lag_peaks.csv |
| Clear-day method, correlation over ±6 min (2022) | 0.9725 to 0.9833, no interior peak | clear_day_scan.csv |
| Dead days (sensor-only rule) | 53: 52 from 2021-03-03 to 2021-05-13, plus 2021-10-08 | dead_days.csv |
| Night offset, range of monthly medians 2021 (from May) / 2022 / 2023 | 0.8–6.1 / 0.9–19.8 / 0.0–29.7 W/m² | qc_monthly.csv |
| Calibration months valid; rejected | 29 of 36; 2021-03 to 2021-06, 2023-06 to 2023-08 | calibration_monthly.csv |
| Valid factor c before / after the boundary month | 1.187–1.285 / 0.730–0.885 | summary.json |
| Minutes above the BSRN upper limit: raw readings / calibrated values | 2,341 / 1,214 | summary.json |
| Daylight slots with a value 2021 / 2022 / 2023: raw; corrected; CAMS | 1.000 / 0.996 / 0.988; 0.940 / 0.996 / 0.983; 0.970 / 0.961 / 0.965 | coverage.csv |
| Validation nRMSE, h = 0, oracle gain: fleet / raw / corrected / same-month / CAMS | 0.0794 / 0.1051 / 0.1080 / 0.1046 / 0.1352 | validation_sources.csv |
| Same, cold-start prior gain | 0.0869 / 0.1217 / 0.1306 / 0.1280 / 0.1391 | validation_sources.csv |
| Daily ratio to fleet yield after the boundary (stable median = 1): raw / corrected / same-month / CAMS | 1.70 / 1.07 / 1.09 / 1.09 | summary.json |
| Input ratio to the event's fleet index, stable vs drifted (median over 17 events): raw; corrected; CAMS | 0.90 vs 1.61; 1.09 vs 1.14; 1.20 vs 1.27 | agreement_events.csv |
| Sensor configuration sha256 | `4c47bfac9fa359fe…` | sensor_config.yaml |

## Forecasting development on the validation units (NB5a)
Source: `results/nb5a_dev/summary.json`, `val_medians.csv`, `val_skill.csv`, `cv_summary.csv`, and
`results/nb5a_variants/` (development data only; run of 20 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| LightGBM setting (rule 1, change target): num_leaves, learning rate, min_data_in_leaf | 31, 0.05, 200 | summary.json |
| CV mean pinball: chosen; guide starting point | 0.068554; 0.068835 | cv_summary.csv |
| **R1 bar: LightGBM median validation nRMSE at 1 h** | **0.18098** | summary.json |
| Median nRMSE at 15 min / 1 h / 2 h / 6 h: LightGBM | 0.1292 / 0.1810 / 0.2106 / 0.2183 | val_medians.csv |
| Same: CLIPER | 0.1318 / 0.1857 / 0.2127 / 0.2106 | val_medians.csv |
| Same: persistence (A1) | 0.1338 / 0.1962 / 0.2352 / 0.2392 | val_medians.csv |
| Same: analogs (A5) | 0.1533 / 0.1909 / 0.2215 / 0.2250 | val_medians.csv |
| Same: climatology (A0) | 0.2342 / 0.2422 / 0.2523 / 0.2313 | val_medians.csv |
| Same: same-time index (oracle A7) | 0.0879 / 0.0909 / 0.0933 / 0.0831 | val_medians.csv |
| Skill of LightGBM at 1 h vs persistence / CLIPER / A5 (units won of 10) | 0.078 (10) / 0.022 (8) / 0.057 (9) | val_skill.csv |
| CRPS skill vs PeEn at 15 min / 1 h / 6 h | 0.501 / 0.313 / 0.082 | summary.json |
| PICP80 of LightGBM, range over horizons | 0.629–0.714 | val_medians.csv |
| Variants at 1 h (pinned setting 15, 0.03, 200): level / change / change pooled / level pooled | 0.1913 / 0.1815 / 0.1873 / 0.2032 | nb5a_variants/variant_medians.csv |
| History to the first origin: validation units; scored events | 18–61 days (median 37); 143–785 days (median 186) | events.csv |
| LightGBM configuration part 2a, sha256 | `d03bb0b86827009e…` | lgb_config_part2a.yaml |

## Conformal calibration on the validation units (NB5a conformal)
Source: `results/nb5a_conformal/summary.json`, `val_conformal_medians.csv`, `corrections.csv` (development data;
run of 20 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| Median PICP80 at 15 min / 1 h / 2 h / 6 h, raw | 0.685 / 0.714 / 0.662 / 0.649 | val_conformal_medians.csv |
| Same, conformal | 0.786 / 0.797 / 0.753 / 0.778 | val_conformal_medians.csv |
| Coverage of the 60 / 40 / 20% intervals at 1 h: raw; conformal | 0.511 / 0.325 / 0.145; 0.618 / 0.398 / 0.190 | val_conformal_medians.csv |
| Median IS80 at 1 h: raw; conformal (units improved) | 0.5739; 0.5716 (8 of 10) | val_conformal_medians.csv |
| Median CRPS (9 quantiles) at 1 h: raw; conformal | 0.0940; 0.0932 | val_conformal_medians.csv |
| Raw PICP80 of the donors' pseudo cold starts at 1 h | 0.714 | corrections.csv |
| Median correction at 1 h, 80 / 60 / 40 / 20% (units of G̃) | 0.047 / 0.032 / 0.019 / 0.011 | corrections.csv |
| Keep rule met; conformal configuration part 2b, sha256 | yes; `c68d5a3aa17a6806…` | conformal_config_part2b.yaml |

## PVSetFormer development and rule R1 (NB5c)
Source: `results/nb5c_r1/summary.json`, `r1_medians.csv`, `r1_units_1h.csv`, `r1_config_part2c.yaml`, and
`results/nb5c_variants/` (development data; 5-seed ensembles, D37; run of 21 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| **R1: median validation nRMSE at 1 h, PVSetFormer (V4a) vs LightGBM, 5-seed ensembles** | **0.18001 vs 0.18130 (−0.71%)** | nb5c_r1/summary.json |
| Units won by PVSetFormer at 1 h; Wilcoxon p across units | 4 of 10; 1.0 | nb5c_r1/summary.json |
| Single seeds at 1 h, PVSetFormer: range; mean (s.d.) | 0.17949–0.18281; 0.18104 (0.0014) | nb5c_r1/r1_medians.csv |
| Same, LightGBM | 0.18090–0.18157; 0.18123 (0.00025) | nb5c_r1/r1_medians.csv |
| Median nRMSE at 15 min / 30 min / 2 h / 4 h / 6 h: PVSetFormer | 0.1329 / 0.1566 / 0.2093 / 0.2334 / 0.2068 | nb5c_r1/r1_medians.csv |
| Same: LightGBM | 0.1291 / 0.1562 / 0.2103 / 0.2368 / 0.2180 | nb5c_r1/r1_medians.csv |
| Units won by PVSetFormer at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 3 / 3 / 4 / 8 / 10 / 9 | nb5c_r1/summary.json |
| Median CRPS at 15 min / 1 h / 6 h: PVSetFormer; LightGBM | 0.0651 / 0.0948 / 0.1095; 0.0617 / 0.0937 / 0.1167 | nb5c_r1/r1_medians.csv |
| Raw PICP80 over horizons: PVSetFormer; LightGBM | 0.654–0.713; 0.631–0.709 | nb5c_r1/r1_medians.csv |
| Variants before the decision; PVSetFormer parameters | 6; 60,157 | nb5c_r1/summary.json, r1_config_part2c.yaml |
| Single-seed rounds at 1 h: V1 / V2 / V3 / V4a / V4b (bar 0.18098) | 0.1858 / 0.1864 / 0.1825 / 0.1795 / 0.1890 | nb5c_variants/log.csv |
| CV pinball of the search CV2: PVSetFormer (d 32, lr 1e-3, wd 0.5); LightGBM | 0.07003; 0.06855 | nb5c_variants/CV2/summary.json |
| Configuration part 2c, sha256 | `d6a24ddb931d0b88…` | nb5c_r1/r1_config_part2c.yaml |
| TimeXer (R2) 5-seed ensemble, median nRMSE at 15 min / 1 h / 6 h | 0.1301 / 0.17845 / 0.2091 | nb5c_variants/TX1_5s/scores.csv |
| TimeXer single seeds at 1 h: range; mean (s.d.) | 0.17961–0.18208; 0.18109 (0.0011) | nb5c_variants/TX1_5s/scores.csv |
| TimeXer search CVX: chosen d, lr, weight decay; CV pinball | 32, 3e-3, 0.01; 0.06800 | nb5c_variants/CVX/summary.json |
| Search CV4 on V4a's architecture: chosen d, lr, weight decay; CV pinball; V4a's setting (rank of 18) | 64, 1e-3, 0.5; 0.07059; 0.07237 (10th) | nb5c_variants/CV4/summary.json, cv_summary.csv |
| Single-seed rounds at 1 h: V5a / V5b / TX1 | 0.17950 / 0.18263 / 0.18174 | nb5c_variants/log.csv |
| A6e (no donor tokens) vs V4a, 5-seed ensembles, median nRMSE at 15 min / 1 h / 6 h | 0.1331 / 0.17997 / 0.2069 vs 0.1329 / 0.18001 / 0.2068 | nb5c_variants/A6e_5s/scores.csv, V4a_5s/scores.csv |
| Single-seed rounds at 1 h: V6a / V6b / V7a / V7b (V4a at the same seed 0.17949) | 0.18053 / 0.18024 / 0.17938 / 0.17927 | nb5c_variants/log.csv |
| Median nRMSE at 15 min / 6 h, same seed: V6b; V4a | 0.1311 / 0.2204; 0.1339 / 0.2073 | nb5c_variants/V6b/scores.csv, V4a/scores.csv |
| 15-min clear spells (calmest quartile, k(t) > 0.9), median move from k(t) and bias: V4a; V6b; LightGBM | 0.048, −0.031; 0.031, −0.013; 0.010, +0.009 | nb5c_diag/V4a, V6b/calm_by_level.csv |
| V8a 5-seed ensemble vs V4a_5s, median nRMSE at 15 min / 30 min / 1 h / 6 h | 0.1309 / 0.1585 / 0.18061 / 0.2090 vs 0.1329 / 0.1566 / 0.18001 / 0.2068 | nb5c_variants/V8a_5s/scores.csv, V4a_5s/scores.csv |
| V8a single seeds at 1 h: range; mean (s.d.) | 0.17935–0.18482; 0.18215 (0.0025) | nb5c_variants/V8a_5s/scores.csv |
| Clear spells (calmest quartile, k(t) > 0.9), median move and bias at 15 min; 30 min: V8a_5s; V4a_5s | 0.028, −0.011; 0.082, −0.044 vs 0.047, −0.029; 0.067, −0.030 | nb5c_diag/V8a_5s, V4a_5s/calm_by_level.csv |
| Slope of the 15-min median change on (4-h mean − k(t)), calmest → most volatile quartile: truth; LightGBM; TimeXer; V4a | 0.039 → 0.217; 0.026 → 0.098; 0.078 → 0.138; 0.112 → 0.158 | nb5c_diag/drift/reversion.csv |
| Same at 30 min: truth; LightGBM; V4a | 0.112 → 0.364; 0.065 → 0.177; 0.192 → 0.279 | nb5c_diag/drift/reversion.csv |
| V4a decomposition (3 tasks, 1 seed), 15-min slope by quartile: linear path; transformer head | 0.147 → 0.197; −0.011 to −0.031 | nb5c_diag/drift/decomposition.csv |
| V10a 5-seed ensemble vs V4a_5s, median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 0.13242 / 0.15694 / 0.18011 / 0.21032 / 0.23336 / 0.20637 vs 0.13294 / 0.15661 / 0.18001 / 0.20926 / 0.23336 / 0.20679 | nb5c_variants/V10a_5s/scores.csv, V4a_5s/scores.csv |
| V10a single seeds at 1 h: range; mean (s.d.) | 0.17908–0.18331; 0.18114 (0.0018) | nb5c_variants/V10a_5s/scores.csv |
| V9 (CV4 setting) 5-seed ensemble, median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 0.13320 / 0.15717 / 0.17848 / 0.20754 / 0.23241 / 0.20607 | nb5c_variants/V9_5s/scores.csv |
| V9 vs V4a_5s ensembles, 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | +0.19 / +0.36 / −0.85 / −0.82 / −0.41 / −0.35% | nb5c_variants/V9_5s, V4a_5s/scores.csv |
| V9 vs LightGBM's ensemble (LGB_seeds), same horizons; units better at 1 h (p) | +3.16 / +0.63 / −1.56 / −1.32 / −1.84 / −5.46%; 6 of 10 (0.56) | nb5c_variants/V9_5s, LGB_seeds/scores.csv |
| V9 single seeds at 1 h: range; mean (s.d.) | 0.17772–0.18475; 0.18072 (0.0028) | nb5c_variants/V9_5s/scores.csv |
| V9 vs LightGBM, 15-min pinball in the calmest quartile; clear-spell bias at 15 min | +40.4%; −0.030 | nb5c_diag/V9_5s/summary.json, calm_by_level.csv |
| V11a (V4a + median-change gate, D63) 5-seed ensemble, median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 0.13176 / 0.15741 / 0.18022 / 0.21101 / 0.23715 / 0.20976 | nb5c_variants/V11a_5s/scores.csv |
| V11a vs V4a_5s ensembles, same horizons; units better at 15 min (p) | −0.88 / +0.51 / +0.12 / +0.84 / +1.63 / +1.44%; 9 of 10 (0.084) | nb5c_variants/V11a_5s, V4a_5s/scores.csv |
| V11a vs LightGBM's ensemble, same horizons | +2.05 / +0.78 / −0.59 / +0.33 / +0.17 / −3.77% | nb5c_variants/V11a_5s, LGB_seeds/scores.csv |
| V11a single seeds at 1 h: range; mean (s.d.) | 0.17870–0.18507; 0.18135 (0.0023) | nb5c_variants/V11a_5s/scores.csv |
| V11a s.d. over seeds of the per-seed median nRMSE at 15 min / 4 h / 6 h (V4a_5s) | 0.0011 / 0.0058 / 0.0064 (0.0013 / 0.0012 / 0.0018) | nb5c_variants/V11a_5s, V4a_5s/scores.csv |
| V11a vs LightGBM, calmest-quartile pinball at 15 / 30 min; clear-spell bias at 15 min; calm 15-min reversion slope (V4a_5s) | +30.4 / +16.3%; −0.021; 0.098 (+40.1 / +21.1%; −0.029; 0.112) | nb5c_diag/V11a_5s/summary.json, calm_by_level.csv; drift_V11a/reversion.csv |
| V10a 15-min reversion slope, calmest → most volatile quartile; 30 min | 0.094 / 0.099 / 0.134 / 0.183; 0.152 → 0.320 | nb5c_diag/drift_V10a/reversion.csv |
| V10a vs LightGBM, 15-min pinball in the calmest quartile; clear-spell bias at 15 min (V4a_5s) | +39.3% (+40.1%); −0.028 (−0.029) | nb5c_diag/V10a_5s, V4a_5s/summary.json, calm_by_level.csv |
| Index-level pinball gap to LightGBM by origin (s, s + 30 d, s + 60 d) at 1 h: V4a_5s; TX1_5s | −1.6 / +2.4 / +6.5%; −1.2 / +2.0 / +3.5% | nb5c_diag/learning_window/by_origin.csv |
| Same for V4a_5s at 15 min; 6 h | +7.5 / +8.2 / +8.1%; −6.9 / −8.9 / −2.7% | nb5c_diag/learning_window/by_origin.csv |
| Third origin, matched history (18–61 d): gap to LightGBM at 15 min / 1 h / 6 h, PVSetFormer; TimeXer | +11.6 / +7.5 / +7.2%; +2.6 / +2.6 / +6.3% | nb5c_diag/learning_window/medians.csv |
| Third origin, full vs matched history, own pinball at 15 min / 1 h / 6 h: LightGBM; PVSetFormer; TimeXer | −3.1 / −3.5 / +2.4%; −6.2 / −4.4 / −4.5%; −0.4 / −2.4 / −3.2% | nb5c_diag/learning_window/medians.csv |
| V4a level split (3 tasks, 1 seed), calmest quartile, mean 15-min median change at k(t) > 0.9: total; head; linear change terms; other linear terms; truth median | −0.048; −0.020; −0.018; −0.010; −0.0045 | nb5c_diag/drift_level/decomposition_level.csv |
| Same at k(t) ≤ 0.3 | +0.028; +0.037; +0.007; −0.015; +0.0065 | nb5c_diag/drift_level/decomposition_level.csv |

## Conformal calibration of PVSetFormer (NB5c conformal)
Source: `results/nb5c_conformal/summary.json`, `val_conformal_medians.csv`, `corrections.csv` (development data;
PVSetFormer's 5-seed ensemble; run of 21 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| Median PICP80 at 15 min / 1 h / 2 h / 6 h, raw | 0.705 / 0.713 / 0.691 / 0.673 | val_conformal_medians.csv |
| Same, conformal | 0.792 / 0.799 / 0.804 / 0.825 | val_conformal_medians.csv |
| Coverage of the 60 / 40 / 20% intervals at 1 h: raw; conformal | 0.542 / 0.347 / 0.158; 0.623 / 0.424 / 0.206 | val_conformal_medians.csv |
| Median IS80 at 1 h: raw; conformal (units improved) | 0.5937; 0.5897 (8 of 10) | val_conformal_medians.csv, summary.json |
| Median IS80 at 6 h: raw; conformal | 0.6608; 0.6292 | val_conformal_medians.csv |
| Median CRPS (9 quantiles) at 1 h: raw; conformal | 0.0948; 0.0941 | val_conformal_medians.csv |
| Raw PICP80 of the donors' pseudo cold starts at 15 min / 1 h / 6 h | 0.720 / 0.684 / 0.615 | corrections.csv |
| Median 80% correction at 15 min / 1 h / 6 h (units of G̃) | 0.038 / 0.063 / 0.106 | corrections.csv |
| Keep rule met; conformal configuration part 2b (PVSetFormer), sha256 | yes; `cc1b10eb80f3afc8…` | conformal_config_part2b_pvsf.yaml |

## Conformal calibration of LightGBM's 5-seed ensemble (NB5c conformal, LightGBM)
Source: `results/nb5c_conformal_lgb/summary.json`, `val_conformal_medians.csv`, `corrections.csv`, and
`results/nb5c_variants/LGB_seeds_cal/summary.json` (development data; `LGB_seeds`, D64; run of 21 Nov 2026).

| Quantity | Value | Source file |
| --- | --- | --- |
| Calibration refit: forecast rows matched to LGB_seeds; max difference; calibration rows | 919,910; 6.0·10⁻⁸; 411,365 | LGB_seeds_cal/summary.json |
| Median PICP80 at 15 min / 1 h / 2 h / 6 h, raw | 0.683 / 0.709 / 0.665 / 0.657 | val_conformal_medians.csv |
| Same, conformal | 0.783 / 0.795 / 0.756 / 0.775 | val_conformal_medians.csv |
| Coverage of the 60 / 40 / 20% intervals at 1 h: raw; conformal | 0.516 / 0.328 / 0.147; 0.621 / 0.403 / 0.205 | val_conformal_medians.csv |
| Median IS80 at 1 h: raw; conformal (units improved) | 0.5756; 0.5705 (9 of 10) | val_conformal_medians.csv, summary.json |
| Median IS80 at 6 h: raw; conformal | 0.7014; 0.6603 | val_conformal_medians.csv |
| Median CRPS (9 quantiles) at 1 h: raw; conformal | 0.0939; 0.0930 | val_conformal_medians.csv |
| Raw PICP80 of the donors' pseudo cold starts at 15 min / 1 h / 6 h | 0.719 / 0.704 / 0.659 | corrections.csv |
| Median 80% correction at 15 min / 1 h / 6 h (units of G̃) | 0.027 / 0.050 / 0.076 | corrections.csv |
| Keep rule met; conformal configuration part 2b (LightGBM, 5 seeds), sha256 | yes; `feb062a2dda885a5…` | conformal_config_part2b_lgb5.yaml |

## Sensor and satellite rows on the validation units (NB5d)
Source: `results/nb5d_sources/summary.json`, `medians.csv`, `prior_check.csv` (development data; LightGBM part-2a
setting for A4 and A4b, D51; each row against fleet LightGBM on the same slots; run of 21 Nov 2026, 289 s).

| Quantity | Value | Source file |
| --- | --- | --- |
| Median nRMSE at 15 min / 1 h / 6 h: A4 (raw sensor, LightGBM); fleet LightGBM on the same slots | 0.1414 / 0.1839 / 0.2177; 0.1292 / 0.1810 / 0.2183 | medians.csv |
| Median change vs fleet LightGBM at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h: A4 | +8.8 / +3.4 / +1.7 / +0.5 / +0.2 / 0.0% | medians.csv |
| Same: A4b (corrected sensor, LightGBM) | +13.1 / +6.6 / +3.5 / +2.0 / +0.9 / +1.2% | medians.csv |
| Same: A9 (CAMS index persisted × prior) | +16.3 / +6.8 / +4.2 / +3.9 / +8.8 / +9.2% | medians.csv |
| Same: A9n (oracle, CAMS index at the target time × prior) | +9.9 / −7.8 / −20.0 / −28.7 / −34.8 / −32.6% | medians.csv |
| Units better than fleet LightGBM at 1 h: A4 / A4b / A9 / A9n; Wilcoxon p | 0 / 0 / 1 / 10; 0.002 / 0.002 / 0.004 / 0.002 | medians.csv |
| Median slot coverage at 1 h: A4, A4b; A9; A9n | 1.00; 0.972; 0.945 | summary.json |
| Priors recomputed from NB4's external gains: largest difference | 4.4e-16 | summary.json |
| A4c (V4a + corrected sensor index, 1 seed) vs V4a at the same seed, median nRMSE at 15 min / 1 h / 6 h | 0.1349 / 0.18038 / 0.2065 vs 0.1339 / 0.17949 / 0.2073 | nb5c_variants/A4c/scores.csv, V4a/scores.csv |

## Foundation models on the validation units (NB5b)
Source: `results/nb5b_fm/summary.json`, `medians.csv`, `comparison.csv`, `fm_config_part2d.yaml`, and
`results/nb5b_runs/*.json` (development data; Colab GPU run of 21 Nov 2026, scored locally in 415 s; D59).

| Quantity | Value | Source file |
| --- | --- | --- |
| Median nRMSE at 1 h, Chronos-2: 28 d covariates / 28 d none / 7 d covariates / 7 d none | 0.1776 / 0.1783 / 0.1795 / 0.1817 | medians.csv |
| Same, TimesFM 2.5: 28 d none / 7 d XReg / 7 d none / 28 d XReg | 0.1790 / 0.1801 / 0.1806 / 0.1806 | medians.csv |
| Chosen settings (part 2d), sha256 of the configuration | chronos2_c1344_full, timesfm25_c1344_none; `d637d1b05e16aac8…` | summary.json, fm_config_part2d.yaml |
| Chronos-2 (chosen), median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 0.1297 / 0.1542 / 0.1776 / 0.2031 / 0.2192 / 0.2000 | medians.csv |
| TimesFM 2.5 (chosen), same horizons | 0.1291 / 0.1546 / 0.1790 / 0.2047 / 0.2220 / 0.2045 | medians.csv |
| Chronos-2 vs LightGBM's ensemble, same horizons (ratio of medians); units lower at 1 h (p) | +0.5 / −1.3 / −2.1 / −3.4 / −7.4 / −8.2%; 9 of 10 (0.004) | comparison.csv |
| Chronos-2 vs PVSetFormer V9_5s; units lower at 1 h (p) | −2.6 / −1.9 / −0.5 / −2.1 / −5.7 / −2.9%; 8 of 10 (0.43) | comparison.csv |
| Chronos-2 vs TimeXer TX1_5s; units lower at 1 h (p) | −0.3 / −1.0 / −0.5 / −3.5 / −6.8 / −4.3%; 8 of 10 (0.16) | comparison.csv |
| TimesFM 2.5 vs LightGBM's ensemble; units lower at 1 h (p) | −0.0 / −1.0 / −1.3 / −2.7 / −6.2 / −6.2%; 9 of 10 (0.020) | comparison.csv |
| TimesFM 2.5 vs PVSetFormer V9_5s; units lower at 1 h (p) | −3.1 / −1.6 / +0.3 / −1.4 / −4.5 / −0.8%; 7 of 10 (0.49) | comparison.csv |
| Chronos-2 vs LightGBM at 15 min: units lower (p) | 1 of 10 (0.049) | comparison.csv |
| Raw PICP80 at 1 h: Chronos-2; TimesFM 2.5 | 0.691; 0.731 | medians.csv |
| V9_5s against the four others (ratio of medians), 15 min / 30 min / 1 h / 2 h / 4 h / 6 h: Chronos-2 | +2.7 / +1.9 / +0.5 / +2.2 / +6.0 / +3.0% | nb5c_diag/vs_all/V9_5s.csv |
| Same: TimesFM 2.5; TimeXer; LightGBM | +3.2 / +1.6 / −0.3 / +1.4 / +4.7 / +0.8%; +2.3 / +0.9 / +0.0 / −1.4 / −1.2 / −1.4%; +3.2 / +0.6 / −1.6 / −1.3 / −1.8 / −5.5% | nb5c_diag/vs_all/V9_5s.csv |
| V12 (V9 + median-change gate at 15 and 30 min, D67) 5-seed ensemble, median nRMSE at 15 min / 30 min / 1 h / 2 h / 4 h / 6 h | 0.13290 / 0.15667 / 0.17782 / 0.20719 / 0.23154 / 0.20555 | nb5c_variants/V12_5s/scores.csv |
| V12 vs V9_5s: median over units; mean over units; units lower | −0.22 / −0.32 / −0.37 / −0.17 / −0.38 / −0.25%; −0.35 / −0.33 / +0.21 / +0.23 / +0.09 / +0.39%; 8 / 7 / 2 / 3 / 8 / 4 of 10 | nb5c_variants/V12_5s, V9_5s/scores.csv |
| V12 single seeds at 1 h: range; mean; s.d. over seeds at 1 h / 6 h (V9) | 0.17800–0.18644; 0.18090; 0.0035 / 0.0077 (0.0028 / 0.0031) | nb5c_variants/V12_5s/scores.csv |
| V12 vs Chronos-2 / TimesFM 2.5 / TimeXer / LightGBM at 1 h (ratio of medians); vs Chronos-2 at 15 min / 4 h | +0.15 / −0.67 / −0.35 / −1.92%; +2.4 / +5.6% | nb5c_diag/vs_all/V12_5s.csv |
| V12 vs LightGBM, calmest-quartile pinball at 15 / 30 min / 1 h; clear-spell bias at 15 min (V9) | +31.7 / +16.8 / +10.2%; −0.022 (+40.4 / +21.2 / +7.7%; −0.030) | nb5c_diag/V12_5s, V9_5s/summary.json, calm_by_level.csv |

## Forecast skill and statistics (NB5, NB6)
_empty_

## Secondary analyses (NB7) and Safi (NB8a)
_empty_
