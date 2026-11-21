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
| A6e (no donor tokens) vs V4a, 5-seed ensembles, median nRMSE at 15 min / 1 h / 6 h | 0.1331 / 0.17997 / 0.2069 vs 0.1329 / 0.18001 / 0.2068 | nb5c_variants/A6e_5s/scores.csv, V4a_5s/scores.csv |

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

## Forecast skill and statistics (NB5, NB6)
_empty_

## Secondary analyses (NB7) and Safi (NB8a)
_empty_
