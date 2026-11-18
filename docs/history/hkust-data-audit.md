# HKUST rooftop PV dataset — data audit (31 Oct 2026)

Dataset: Lin et al., Dryad doi:10.5061/dryad.m37pvmd99 (Sept 2024 version, with tilt/azimuth). Topic chosen by the user: cold-start PV forecasting.

## Structure and resolution
- 60 stations, 2,231 kW total (rated kW appears to be the AC/inverter rating; DC is larger, e.g. SQ1 = 88 x 390 W = 34.3 kWp vs 27.6 kW).
- 37 stations with optimizers: 5-min inverter files (44 inverters) + 15-min site files.
- 23 stations without optimizers: hourly site files only (README says 5-min for all; not true).
- Weather: 1-min irradiance (single GHI sensor), temperature, RH, rain (2021 in .xlsx), pressure, visibility, wind; ~99% complete.

## Orientation (key for the original idea)
- ~33 stations flat (0 deg), ~14 at 10 deg (east-west or north-south pairs), 13 "Mixed" (unknown), max 15 deg.
- Orientation diversity is weak, so a tilt/azimuth-based transfer idea cannot be the main contribution.

## Real cold-start events
- About 20 stations came online after Oct 2021 (e.g. Zone A5/A6/A7, SQ Block R/S, Wong Check She, Zone J2, Zone D, Zone J1, Tower A, Library, SQ18, Zone L2, SQ Block Q, UG Hall8/9, Zone A2 inv 2-3, SQ Block P, Shaw Auditorium).

## Irradiance sensor problem (major)
- Measured / clear-sky GHI at noon (p95): about 0.8 in 2021-2022, about 1.35 in 2023 (step change in early 2023).
- Night offset rises from about 3 to about 30 W/m2 (2022Q2-2023Q3); spikes up to 3,600 W/m2 in 2023Q2-Q3.
- Confirmed by six long-running stations: daily yield / irradiation ratio falls together from about 1.2 (2021) to about 0.6 (2023).
- Implication: models trained on 2021-22 and tested on 2023 with this sensor are biased.

## Peers vs. sensor
- 15-min normalized power: median correlation with the peer-fleet median is 0.96-0.97 vs. 0.91-0.94 with the sensor; peers beat the sensor for 93% of inverters.

## Other notes
- Inverter clipping is visible (p99 power = rated kW for many stations).
- Metadata coordinates are coarse (22.28-22.33 N, 114.17-114.18 E), so use the campus coordinate 22.3363 N, 114.2634 E.
- SQ_Apartment37_48 Flexible PV peaks at 6.7 kW vs. 3.72 kW rated (metadata inconsistency).
- S H Ho Sports Hall behaves abnormally in 2021 (correlation about 0.2-0.4).
- 5 thin-film flexible stations (SMF310M) alongside mono-Si stations.

## Proposed adjusted idea (awaiting the user's decision)
"Fleet-as-a-sensor" cold-start forecasting: forecast a new station from the normalized output of the stations already running, plus clear-sky geometry and its capacity. No history and no pyranometer are needed, and it is robust to sensor drift. Evaluate on the ~20 real staggered starts.
