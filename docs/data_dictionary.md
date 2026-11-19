# Data dictionary

Inputs as found on 18 Nov 2026 (checksums in `data/MANIFEST_sha256.csv`), then every output file and column as it is
created. HKUST paths are relative to `data/raw/hkust/Dataset/`.

## Inputs — HKUST (Dryad)

| File group | Count | Step | Columns | Notes |
| --- | --- | --- | --- | --- |
| `Time series dataset/PV generation dataset/PV stations with panel level optimizer/Inverter level dataset/*_Inverter*.csv` | 44 | 5 min | `Time`, `dcVoltage(V)`, `totalActivePower(W)`, then for L1, L2 and L3: `acCurrent(A)`, `acFrequency(Hz)`, `acVoltage(V)`, `activePower(W)`, `reactivePower(W)` | 06:00–17:55 only (F01); two timestamp formats (F02); NA for missing |
| `…/PV stations with panel level optimizer/Site level dataset/*.csv` | 37 | 15 min | `Time`, `generation(kWh)`, `power(W)` | 00:00–23:45; usually from the 1st of a month (F16) |
| `…/PV stations without panel level optimizer/Site level dataset/*.csv` | 23 | 1 h | `Time`, `generation(kWh)`, `power(W)` | hourly track; includes the thin-film roofs |
| `Time series dataset/Meteorological dataset/Irradiance/Irradiance_{2021,2022,2023}.csv` | 3 | 1 min | `Time`, `Irradiance (W/m2)` | LI-COR LI-200R (F09); 525,598 / 522,524 / 519,670 rows |
| `…/Temperature/`, `…/Relative Humidity/`, `…/Sea Level Pressure/`, `…/Visibility/`, `…/Wind/` | 3 each | 1 min | `Temp (Degree Celsius)`; `RH (%)`; `SLP (hPa)`; `Vis (km)`; `Wind Speed (m/s)`, `Wind Direction (degree)` | timestamps `2022/1/1 0:00` |
| `…/Rainfall/Rainfall_2021.xlsx`, `Rainfall_{2022,2023}.csv` | 3 | 1 min | `Time`, `Rainfall(mm)` | 2021 is an Excel file |
| `Metadata/PV generation system metadata.ttl` | 1 | static | Brick: `PV_Generation_System` (coordinates, location, altitude, connectionDate, contractor, ratedPowerOutput kW, azimuth, tiltAngle) → `Inverter` (brand, module = model name, number) → `PV_Panel` (brand, module model, number, degradation, rated power W, efficiency, type) | 2,421 lines; azimuth counterclockwise from north (F15); coarse coordinates (F10) |

## Inputs — other

| File | Content | Notes |
| --- | --- | --- |
| `data/raw/safi/*.xlsx` | Safi rooftop: electrical, module temperature and weather files for a-Si, m-Si and p-Si; 5 min, 24 h a day | Not yet opened; audited at NB8a. `Preprocessed Data.xlsx` is never used. Zeros can mean inverter failure (F18) |
| `data/external/cams/observed/cams-HKUST-21-23.csv`, `cams-safi-16-18.csv` | Semicolon-separated; `Observation period` (UT), TOA, clear-sky GHI, BHI, DHI, BNI, then all-sky GHI, BHI, DHI, BNI, `Reliability` (share of reliable data in the step, 0–1) | CAMS Radiation Service v4.6; Wh/m² per 1-min step (× 60 → W/m²); HKUST daytime rows with reliability < 1: 8.13% (F17) |
| `data/external/cams/mcclear/HKUSTcsv.csv`, `safi-2016-2018csv.csv` | Semicolon-separated; `Observation period` (ISO 8601 interval, UT), TOA, clear-sky GHI, BHI, DHI, BNI | Wh/m² per 1-min step: × 60 gives the mean W/m² (F08) |
| `data/external/open-meteo/open-meteo-32.23N7.95W467m.csv` | Benguerir (32.232 N, 7.954 W, 467 m), hourly `temperature_2m (°C)`, `wind_speed_10m (km/h)`, `precipitation (mm)`, GMT, 2016-06-01 to 2018-12-31 | Follow-up paper (D07) |
| `data/external/pv_density/digitization/` | Digitised density grid: `pv_density_visual_grid.{csv,geojson,shp}`, georeferenced rasters, `metadata.json`, `README.md` | Visual reconstruction from the ISPRS paper's figure |

## Outputs

| Folder / file | Content |
| --- | --- |
| `results/nb0_setup/summary.json`, `config_snapshot.yaml` | Versions, manifest check, every constant of `config.py` |
| `results/nb1_audit/units_inverters.csv` | One row per inverter in the metadata: station, model, AC_kW (from the model name), module models, n_modules, DC_kWp, DC_AC, file stem |
| `results/nb1_audit/units_stations.csv` | One row per station: metadata rating, connection date, contractor, altitude, tilt, azimuth (Brick and pvlib), file stems |
| `results/nb1_audit/inventory_inverters.csv` | Per inverter file: format, rows, first/last, rows per day, slots, NA share, p99.9 and max power, producing on day 1 |
| `results/nb1_audit/inventory_sites_15min.csv`, `_1h.csv` | Per site file: format, rows, first/last, starts on the 1st, first power, first-day energy, NA share |
| `results/nb1_audit/inventory_weather.csv` | Per weather variable and year: rows, missing rows, NA values, range |
| `results/nb1_audit/metadata_check.csv` | AC rating vs observed p99.9 (within 2% flag) |
| `results/nb1_audit/start_dates.csv` | Per optimizer station: connection date, first inverter day, site-file start, earliest production, D08 left-censoring flag |
| `results/nb1_audit/evening_share.csv` | Share of energy after 18:00 per station and month |
| `results/nb1_audit/zone_d_ratio.csv` | Zone D station / inverter 2 daily energy, monthly median |
| `results/nb1_audit/sensor_daily.csv` | Per day: sensor, CAMS and Ineichen irradiation (Wh/m²), ratios to CAMS and to the fleet proxy |
| `results/nb1_audit/sensor_monthly.csv` | Per month: night offset, noon p95 ratios, BSRN exceedances, maximum |
| `results/nb2_panel/units.csv` | Per inverter: AC used and its source, DC, DC/AC, metadata_error, in_prior_test, flat, first_row, rule_start |
| `results/nb2_panel/events.csv` | Per event (scored, sensitivity, validation): start, target source, AC, DC/AC, prior test, donors, valid days, provisional sensor period, eligibility |
| `results/nb2_panel/donors.csv` | Event, donor (one row per pair) |
| `results/nb2_panel/testbed.csv` | Hidden-unit test bed: date, unit, station, valid days, group |
| `results/nb2_panel/qc_flag_shares.csv` | Per unit: share of daylight 5-min values with each QC flag |
| `results/nb2_panel/label_offset_*.csv` | Correlation with clear-sky GHI against the time shift |
| `results/nb3_index/validation_kmin.csv`, `validation_estimator.csv`, `validation_priors.csv` | Validation units only: oracle gain and same-time nRMSE per k_min, per estimator; prior gains and errors per variant |
| `results/nb3_index/event_periods.csv` | Per event: days after the final drift boundary, sensor period |
| `results/nb3_index/gains.csv` | Event, donor, gain (fitted before the event start, median 1) |
| `results/nb3_index/priors.csv` | Per event: prior used and its gain, G0/G1/G2, beta, r, T, uncertainty-set quantiles, sigma_p^2, s1^2, w0 (days) |
| `results/nb3_index/frozen_config_part1.yaml` | Frozen configuration, part 1 (hash in summary.json) |
| `results/nb3_index/*.parquet` (git-ignored, rebuilt by NB3) | Per event (columns) and 15-min slot: k_med, k_cens, sigma (IQR of the implied indices), c (clipped share), n (unclipped donors) |
| `results/nb4_sensor/lag_scan_sensor.csv`, `lag_scan_cams.csv`, `lag_peaks.csv` | Correlation of within-day 5-min index changes with the fleet index by lag and quarter; peak lags |
| `results/nb4_sensor/clear_day_scan.csv` | The guide's clear-day time-label method applied to the sensor, by year and shift |
| `results/nb4_sensor/calibration_monthly.csv` | Per month: clear minutes used, factor, detector alpha and status, valid, factor applied (causal) and its month, same-month factor |
| `results/nb4_sensor/qc_monthly.csv` | Per month: minutes missing, below the lower limit, above the upper limit (calibrated), on dead days, raw readings above the limit, valid daylight minutes, night offset |
| `results/nb4_sensor/night_offset_daily.csv`, `dead_days.csv` | Daily night offset (window value, carried flag); dead days with their sensor clear-sky index |
| `results/nb4_sensor/coverage.csv` | Share of daylight slots with a value, per source and year |
| `results/nb4_sensor/gains_external.csv`, `priors_external.csv` | Donor gains refitted against each source (event, source, donor, gain, points); priors per event and source |
| `results/nb4_sensor/validation_sources.csv` | Validation units only: oracle gain, prior gain and same-time nRMSE per index source |
| `results/nb4_sensor/agreement_events.csv` | Per event and source: median ratio and correlation with the event's fleet index in its window (no target) |
| `results/nb4_sensor/daily_sensor.csv` | Per day: irradiation per source over the panel slots, ratios to the NB1 fleet yield, sensor clear-sky index, dead flag, night offset, drifted flag |
| `results/nb4_sensor/sensor_config.yaml` | Sensor settings (hash in summary.json); part of the frozen configuration part 2 |
| `results/nb4_sensor/*.parquet` (git-ignored, rebuilt by NB4) | index15: k and G per source (sensor_raw, sensor_corr, sensor_same, cams) and minute counts at the 15-min slots; sensor1min: raw, corrected and same-month GHI, flag bits (1 missing, 2 below, 4 above, 8 dead day), clear minute, CAMS GHI |
| `results/nb2_panel/*.parquet` (git-ignored, rebuilt by NB2) | P15_kW, y15, flags15 (bitmask: 1 night, 2 negative, 4 frozen, 8 over limit, 16 outage), nvalid15, geometry15 (zenith, elevation, azimuth, hour angle, doy, G_cs, Gt), targets15_kW (per event), k_crude5 |
