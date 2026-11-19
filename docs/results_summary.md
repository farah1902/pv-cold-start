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

## Forecast skill and statistics (NB5, NB6)
_empty_

## Secondary analyses (NB7) and Safi (NB8a)
_empty_
