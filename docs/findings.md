# Findings

One entry per empirical result, numbered F01, F02, … and never renumbered. Confidence: *solid* (checked in the files
or in the primary source), *strong*, *provisional* (reported in an audit, still to be reproduced by code in this
repository). Paths are relative to `data/raw/hkust/Dataset/Time series dataset/` unless stated.

### F01 — Inverter files cover 06:00–17:55 only (144 rows a day); site files cover 00:00–23:45 — *solid*
- **Evidence:** all 44 inverter files end at 17:55 on 2023-12-31. Zone A5 has 117,780 rows: 817 days of 144 rows and
  its first day of 132 rows (it starts at 07:00). On 2022-06-21, Zone A5's site file still shows 598 W at 18:00,
  285 W at 18:15, 51 W at 18:30 and zero from 18:45. The review audit of 18 Nov reports evening energy after 18:00 at
  a median 0.17% of the total, at most 0.5% in June (to be reproduced in NB1).
- **NB1 (18 Nov 2026):** all 44 inverter files have 144 rows a day as their mode, slots 06:00–17:55. Energy after 18:00 (15-min site files, `results/nb1_audit/evening_share.csv`): the median calendar-month share across stations peaks in June at 0.54%; per station over the whole period the median is 0.19% (max 0.27%), close to the audit's 0.17%; the median over 949 station-months is 0.06% (definitions differ).
- **Reading:** the fleet index cannot be computed after 17:55, and a 6-h forecast can only be issued until 11:55.
- **Paper:** Data §3.5; protocol (D12); threats to validity.

### F02 — Two timestamp formats — *solid*
- **Evidence:** 13 inverter files write `2021/6/2 6:00` (SQ567, Zone A7, SQ Apartment 1-12, 25-36 and 37-48, UG Hall2
  RF, UG Hall3, UG Hall4, UG Hall7, Zone J1, Zone J2, Zone L2, LSK South); the other 31 write `2021-05-07 07:00:00`.
  The weather files write `2022/1/1 0:00`. NB1: 3 of the 37 15-min site files and 7 of the 23 hourly files use year/month/day (10, as in the audit); the 2021 rainfall file holds Excel date-times. No file mixes formats.
- **Paper:** not in the text; D13 (code).

### F03 — Zone J2 produced for 25 days before its inverter file begins — *solid*
- **Evidence:** its site file starts on 2021-11-13 (188.8 kWh that day) and holds 1,597 kWh before 2021-12-08, the
  first day of its inverter file. Metadata connection date: 2021-12-01.
- **Reading:** the event is re-dated to 2021-11-13, with the site series as target (D08).

### F04 — Zone L2's start is left-censored — *solid*
- **Evidence:** its site file starts on 2022-06-01 and already produces 40.4 kWh that day; 405 kWh before its inverter
  file begins on 2022-08-02. Metadata connection date: 2022-07-30.
- **Reading:** an operator had site-level history before the inverter file; moved to the sensitivity set (D08).

### F05 — Zone D inverter 1 is not a capacity addition — *solid*
- **Evidence:** the review audit of 18 Nov reports that the Zone D station total ran at 1.6–1.7 × inverter 2 from
  January to October 2022, so inverter 1 was producing before its file starts on 2022-12-03. NB1 reproduces it (`results/nb1_audit/zone_d_ratio.csv`, daily energy 06:00–17:55, monthly medians): 1.67–1.73 from January to October 2022, 1.03 in November 2022 (inverter 1 down), 1.69–1.86 from December 2022, when its file exists.
- **Reading:** Zone D is scored as one station-level event from 2022-01-19 (D08).

### F06 — Telemetry starts and connection dates disagree, in both directions — *solid* (checked rows); *provisional* (audit counts)
- **Evidence:** the 19 start dates of the guide's first event list equal the first rows of the inverter files. Metadata
  connection dates (Brick `.ttl`): Library 2022-05-31 (telemetry 2022-06-01), SQ Block P 2023-07-21 (telemetry
  2023-06-22), Shaw Auditorium 2023-07-29 (telemetry 2023-07-09), Zone J2 2021-12-01, Zone L2 2022-07-30. The audit
  reports that every inverter file already produces on its first day, and connection 113 days before telemetry for
  Zone J1 and 92 days for Wong Check She.
- **NB1:** 43 of 44 inverter files produce on their first day; the exception is Zone A2 inverter 2 (first row 2023-05-16 11:35, zero output that day), an observed commissioning. Full table in `results/nb1_audit/start_dates.csv` (F22).
- **Reading:** neither the connection date nor the first inverter row proves commissioning; hence the observed-start
  rule (D08).

### F07 — The 10 validation units start between 2 June and 15 July 2021; SQ567 has exactly 8 donors — *solid*
- **Evidence:** first inverter rows: SQ567 2021-06-02, UG Hall2 2F 06-03, UG Hall2 RF 06-09, Zone A1 06-11, Zone A4
  06-11, Zone A2 inverter 1 07-01, SQ Apartment 1-12 07-08, 13-24 07-11, 37-48 07-11, 25-36 07-15. Units started at
  least 14 days before 2021-06-02: LSK South (05-01), LSK North (05-04), SQ1 (05-07), UG Hall6 (05-11), SQ2 (05-12),
  SQ4 (05-12), UG Hall7 (05-17), SQ3 (05-19, exactly 14 days) = 8.
- **Reading:** SQ567 meets the 8-donor rule only with SQ3; any start-date rule that moves SQ3 by one day drops it.

### F08 — The CAMS files received are McClear clear-sky only — *solid*
- **Evidence:** headers of `data/external/cams/mcclear/*.csv`: "CAMS McClear v3.6 model of clear-sky irradiation";
  columns TOA, clear-sky GHI, BHI, DHI and BNI; unit Wh/m² per 1-min step; Universal time. HKUST: 2021-01-01 to
  2023-12-31 (CAMS altitude 144 m). Safi: 2016-06-01 to 2018-08-31.
- **Reading:** no all-sky irradiance, so no satellite check of the sensor and no baseline A9 yet; Safi misses
  September–December 2018 (D14).

### F09 — The pyranometer is a LI-COR LI-200R (±3% typical, ±5% maximum) — *solid* (drift reproduced in F23)
- **Evidence:** data paper, Table 3 (400–1100 nm). The audit of 31 Oct (`docs/history/hkust-data-audit.md`) reports
  measured / clear-sky GHI at noon (p95) of about 0.8 in 2021–2022 and 1.35 in 2023, a night offset rising to about
  30 W/m², and spikes up to 3,600 W/m² (to be reproduced in NB1).
- **Reading:** a shift of that size is far outside the specification: a fault, not scatter. The 0.8 level may partly
  come from the clear-sky model; McClear can test this (D14).

### F10 — The site coordinate is 22.3363 N, 114.2634 E; two other coordinates exist — *solid*
- **Evidence:** data paper, Methods (22.3363 N, 114.2634 E), but its Usage Notes say 22.3964 N, 114.1095 E. Brick
  metadata: 22.28 N, 114.17 E for every station (coarse).
- **Paper:** Data §3.1 (use the Methods coordinate).

### F11 — Metadata cross-checks of the DC/AC ratio — *solid*
- **Evidence:** Zone A5: inverter SolarEdge SE17K, 52 × JinkoSolar JKM390M (390 W) = 20.28 kWp, rated 17.0 kW, DC/AC
  1.19; connection 2021-10-02. Indoor Sports Centre (data paper, Fig. 5): rated 33.3 kWp, inverter "Sunny Tripower STP
  10.0", 120 × 365 W = 43.8 kWp, DC/AC 1.31. Both match the guide's event table.

### F12 — Statistical power of the event-wise tests — *solid* (arithmetic)
- **Evidence:** exact one-sided Wilcoxon signed-rank: smallest p = 1/2^n. n = 14 gives 6.1 × 10⁻⁵; n = 6 gives 1/64
  (0.0156), which Holm over 6 horizons raises to at least 0.094; n = 5 gives 1/32 (0.031); n = 4 gives 1/16 (0.0625).
- **Reading:** the drifted window can only be reported by effect sizes and per-event tests (D10).

### F13 — Missing data and site-vs-inverter agreement, as reported by the data paper — *solid* (as published)
- **Evidence:** data paper, Table 4: three-year missing rate 6.644% for the inverter files, 0.789% for the 15-min site
  files, 1.852% for the hourly files, 0.571–0.610% for the weather variables. Fig. 7: daily energy from site and
  inverter files differs by 0.34 kWh on average (median 0.02 kWh), by less than 1 kWh on more than 92% of days, with a
  mean relative error of 0.32%.
- **Reading:** the site files can fill gaps and serve as a cross-check of inverter sums.

### F14 — The published series were resampled, not cleaned — *solid*
- **Evidence:** data paper, "Data curation": missing values written as NA, timestamps aligned with the pandas
  `resample` function, no filling and no outlier detection.
- **Reading:** the interval-labelling convention is not documented; the lag-correlation step of the guide (§2,
  preprocessing step 1) fixes it.

### F15 — The Brick azimuth runs counterclockwise from north (east = −90°, west = 90°) — *solid* (definition)
- **Evidence:** data paper, p. 6. Two-direction roofs use slash notation; curved roofs are "Mixed".
- **Reading:** pvlib measures azimuth clockwise (east = 90°), so the transposition factor of prior G2 needs
  az_pvlib = (360° − az_Brick) mod 360°. The values themselves are checked in NB1.

### F17 — CAMS all-sky irradiance exists for HKUST and Safi — *solid*
- **Evidence:** `data/external/cams/observed/`: "CAMS Radiation Service v4.6 all-sky irradiation (derived from
  satellite data)". HKUST: 2021-01-01 to 2023-12-31, 1,576,800 rows (1,095 days × 1,440 minutes), CAMS altitude 144 m;
  daytime rows (TOA > 0) with reliability < 1: 64,134 of 788,774 (8.13%). Safi: 2016-06-01 to 2018-12-31, 1,359,360
  rows (944 days × 1,440), altitude 0 m as requested. Columns: TOA, clear-sky GHI/BHI/DHI/BNI, all-sky
  GHI/BHI/DHI/BNI, reliability; Wh/m² per 1-min step; UT.
- **Reading:** baseline A9 and the satellite check of the HKUST sensor stay (D17). Steps with reliability < 1 are
  flagged in any satellite-based score.

### F18 — Safi: module ratings are in W, the companion article is SETA 2021, zeros can be failures, and the three series barely overlap — *solid* (article); *provisional* (dates, to check on the raw files)
- **Evidence:** Id Omar et al., *Data in Brief* 34 (2021) 106756 (`data/raw/safi/`):
  - m-Si and p-Si subarrays of 8 modules of "255 kWp" each, a-Si of two strings of 6 modules of "155 kWp", total
    5.94 kWp. 8 × 255 + 8 × 255 + 12 × 155 = 5,940 W, so the ratings are W (the article's "kWp" is a typo).
  - Tilt 32°, south; three identical inverters; plane-of-array irradiance from a calibrated crystalline-silicon
    reference cell (uncertainty < 2.3%); Pt100 ambient and module back-side temperatures (±0.1 °C); 5 min, 24 h a day.
  - The plant details are in Table 2 of Id Omar et al., *Sustainable Energy Technologies and Assessments* 43 (2021)
    100915. The research guide's "Energy Reports 2020" is wrong.
  - Gaps: grid cut-offs stop the acquisition; when an inverter fails, its records are set to 0 until it is fixed;
    burned fuses give null or wrong values.
  - Preprocessed data: m-Si and a-Si from 18 June 2016 to 15 July 2018, p-Si from 25 May to 30 December 2018.
  - Screenshot of the SETA article page (`data/raw/safi/`, 18 Nov 2026): "eight mono-crystalline (m-Si) panels of
    255 Wp each connected in series cumulating a maximum power of 2.04 kWp"; the inverter details are cut off.
    Safi therefore uses the empirical AC limit (D01 rule).
- **Reading:** zeros are not trusted as production in the Safi QC. If the raw files follow the preprocessed dates, all
  three inverters overlap only from 25 May to 15 July 2018 (about 7 weeks). Most of the period has a one-donor fleet,
  and p-Si has donors only in that overlap. Safi is therefore a 1–2-donor case, to be compared with the HKUST
  fleet-size curve at 1–2 donors.

### F19 — The closest competitor: Longarini et al. (2026), cold-start PV forecasting with foundation models — *strong* (read via the arXiv HTML on 18 Nov 2026; re-read in full before citing)
- **Evidence:** arXiv:2606.07457, "Time series Foundation Models based on Physics-Informed Synthetic Histories for
  Cold-Start Photovoltaic Forecasting", to appear at the 2nd ICML Workshop on Foundation Models for Structured Data.
  A synthetic production history from plant metadata (physics model, pvlib solar position) and ERA5 covariates (via
  Open-Meteo) is given as context to five foundation models (Chronos-2, Moirai 2.0, TimesFM 2.5, TiRex, TabPFN-TS).
  The target is daily specific yield; horizon covariates are observations with perfect foresight, which the authors
  call optimistic. There are 440 sites (Ausgrid, DKASC, UK-PV, PVDAQ), with the most recent year held out; no real
  commissioning dates and no code link.
- **Reading:** it must enter the positioning table (guide §1) and the related work. Our differences: intraday 15 min
  to 6 h instead of daily; no weather input at all, where theirs needs irradiance with perfect foresight; causal
  information set; real start dates.

### F20 — Closest neural work on PV and irradiance networks, and the gap a fleet-set transformer can fill — *strong* (arXiv abstract pages read on 18 Nov 2026; full texts before citing)
- **Evidence:**
  - Simeunović et al., IEEE TSTE (doi:10.1109/TSTE.2021.3125200; arXiv 2107.13875): graph-convolutional LSTM and
    transformer over 304 real Swiss PV systems, production data only, deterministic. They beat multi-site methods at
    6 h and NWP-based single-site methods up to 4 h.
  - Schubnel et al., SolarCrossFormer, IEEE TSTE 2025 (doi:10.1109/TSTE.2025.3624044; arXiv 2509.15827): forecasts
    **irradiance**, not PV power, from satellite images and ground meteorological stations, with graph neural
    networks. Probabilistic, 15 min up to 24 h; forecasts sites without data from their coordinates.
  - Fan et al., Solar-VLM (arXiv 2604.04145, 2026): time series, satellite images and text, with a graph over 8
    stations.
  - TimeXer (arXiv 2402.19072): exogenous inputs over the look-back only in its core setup, L2 loss.
  - Name checks of 18 Nov: no model named KappaFormer, HelioSet, SkyFleet or FleetFormer was found (not exhaustive;
    re-check before submission).
- **Reading:** no work found forecasts **PV power** for a unit with no history **and** no coordinates, satellite or
  weather input. None treats inverter clipping as censoring, or composes an index forecast with a nameplate gain
  prior. That is the room for the author's model (D24).

### F21 — Metadata: AC ratings, errata and two corrections to the guide — *solid*
- **Evidence:** `results/nb1_audit/units_inverters.csv`, `metadata_check.csv`. 60 stations, 67 inverters, 74 module
  blocks; 23 inverter model strings mapped to AC ratings by an explicit table. The observed 99.9th percentile of 5-min
  power is within 2% of the AC rating for 33 of 44 inverters (as in the guide). The 11 others:
  - two metadata errors: Zone D inverter 2 is listed as SE25K but peaks at 49.9 kW (about 50 kW), and Indoor Sports
    Centre is listed as STP 10.0 but clips at 33.4 kW;
  - six never reach their limit: UG Hall2 2F (0.77 of AC, DC/AC 0.94), SQ567 (0.83, DC/AC 0.87), Zone J2 (0.92,
    DC/AC 1.28, mixed orientation), SQ Block S (0.95), Zone L2 (0.97), SQ2 (0.975);
  - three exceed the nameplate: SQ Apartment37-48 (1.049), UG Hall2 RF (1.052), Zone A7 (1.061).
- **Corrections to the guide:**
  - Zone A2 inverters 2 and 3 have complete metadata: SE55K and SE50K with JKM410N modules, DC/AC 1.33 each, both
    within 2% of their rating. The guide's "metadata missing" and "Zone A2 has no module blocks" are wrong, so the
    DC/AC prior can be tested on the only capacity addition.
  - Zone A2 inverter 1 is an SE82_8K (82.8 kW, two module blocks).
  - Six hourly-track SMA inverters (SQ8, SQ11, SQ12, SQ14, SQ15, SQ19) have no model name; the station rating stands in.
  - The metadata spell Indoor Sports Centre as `Indoor_Sport_Center`.
  - DC/AC over the 44 inverter-file units runs from 0.87 to 4.38 (median 1.20); the extremes are metadata errors.

### F22 — The observed-start rule applied to every optimizer station — *solid*
- **Evidence:** `results/nb1_audit/start_dates.csv`. The rule of D08 (earliest file begins on the 1st of a month while
  already producing) flags LSK South, Zone A2 (its first inverter, 2021), S H Ho Sports Hall, Wong Check She, Zone J1,
  Library and Zone L2. Earliest production precedes the metadata connection date by up to 59 days (Zone L2) and
  follows it by up to 113 days (Zone J1); UG Hall8 produced 55 days before its connection date. The Zone A2 connection
  date (2023-05-31) is that of the 2023 addition.
- **Reading:** the flags agree with D08 for every event except **Library**: both of its files begin on 2022-06-01 and
  produce that day, so the written rule calls it left-censored, while D08 scores it ("connected the day before").
  The author must decide (open question of 18 Nov 2026).

### F23 — The sensor drift is a step in mid-February 2023, found by two independent references — *solid*
- **Evidence:** `results/nb1_audit/sensor_daily.csv`, `sensor_monthly.csv`, `summary.json`.
  - One-break segmentation of the daily log-ratios (dead-sensor days excluded): sensor / CAMS all-sky steps on
    2023-02-14 from 0.756 to 1.166; sensor / fleet proxy steps on 2023-02-17 from 0.901 to 1.531. CAMS / fleet shows
    only a small step, on 2023-03-14, from 1.171 to 1.265.
  - Yearly medians of sensor / CAMS: 0.721 (2021), 0.762 (2022), 1.126 (2023).
  - Noon 95th percentile of GHI over Ineichen clear sky (campus altitude 124 m, the median station altitude): sensor
    0.82–0.96 from May 2021 to January 2023, then 1.22–1.59; CAMS 0.93–1.08 in every month. The 2021–2022 level of
    about 0.8–0.9 therefore comes from the sensor, not from the clear-sky model (answers D19).
  - The sensor was dead (sensor / CAMS below 0.3) on 77 days between 2021-03-02 and 2022-05-23, mostly March and
    April 2021 (maximum 32 W/m² in April 2021). Neither the data paper nor the earlier audits mention it.
  - Night offset (monthly median at solar elevation below −6°): 0.7–5.3 W/m² in 2021, 8–20 W/m² from May 2022 to
    January 2023, 25–30 W/m² from April to August 2023, 0 in November–December 2023.
  - Readings above the BSRN "extremely rare" limit appear from February 2023 (26), peak in July and September 2023
    (734 and 1,096); the maximum is 3,608.6 W/m² (February 2023).
  - PELT with the penalty 2σ² log n finds 17–19 breaks, mostly seasonal structure, so the final boundary rule of D10
    needs a calibrated penalty or a one-break segmentation, fixed in NB3 before scoring.
- **Reading:** with this boundary, UG Hall8 (2023-01-05) has 48 of its 90 test days after mid-February and stays in
  the drifted window, so the drifted window keeps its five events. The final boundary comes from NB3.
- **Update (NB4):** the failure itself runs from early March to about 15 May 2021; four of the 77 CAMS-based
  dead days are overcast days (F34).

### F24 — Weather files: missing rows, not NA values — *solid*
- **Evidence:** `results/nb1_audit/inventory_weather.csv`. Irradiance has 2, 3,076 and 5,930 missing 1-min rows in
  2021, 2022 and 2023, and no NA values: the gaps are absent rows, unlike the PV files, which write NA.

### F25 — The station "rated power" field is mostly the DC capacity, not the AC rating — *solid*
- **Evidence:** `results/nb1_audit/units_stations.csv` vs the module sums: the field equals the DC capacity for most
  stations (Library 170.2, Shaw Auditorium 88.48, Zone A7 12.78, SQ Block S 32.85, …). It does not for Indoor Sports
  Centre (33.3, against 43.8 kWp DC) or Zone D (68.62, the DC of one module block). The data paper's total of
  2,230.8 kWp is consistent with DC; the October audit's reading of the field as AC was wrong.
- **Reading:** AC ratings come from the inverter model names (D01), never from this field. The exception is Indoor
  Sports Centre, where 33.3 kW agrees with the standard SE33_3K rating and the observed clip (D29).

### F26 — Time labels: inverter values are interval means labelled at the interval start; site files use the same slots — *strong*
- **Evidence:** `results/nb2_panel/label_offset_inverter.csv`, `label_offset_site.csv`. On the 30 clearest, smoothest
  days (31 flat units), the correlation of fleet power with Ineichen clear-sky GHI peaks at a shift of +3.0 min for
  the 5-min inverter values (correlation 0.990; theory for start-labelled means: +2.5) and at +11.0 min for the 15-min
  site values (theory: +7.5). Site stamp to inverter slot: +3.0 min, i.e. 0 slots.
- **Reading:** geometry is computed at stamp + 3 min (5 min) and slot + 8 min (15 min); site series need no relabelling.
  The peak is broad, so the shift is known to about ±1–2 min. The guide's pilot "lead of about 5 min" is not
  confirmed.

### F27 — The 15-min panel is clean, and every event is eligible — *solid*
- **Evidence:** `results/nb2_panel/qc_flag_shares.csv`, `events.csv`, `units.csv`, `testbed.csv`.
  - Over daylight 5-min values there are no frozen, negative or night-power values. Over-limit (y > 1.05) appears
    only in units running above their nameplate (Zone A7 1.15%, UG Hall2 RF 0.25%). Outages are a median 0.02% per
    unit; maximum 6.0% for Indoor Sports Centre, then Zone A2 inverters 2 (2.3%) and 3 (1.3%).
  - After each unit starts, 96.1% of daylight 15-min slots are valid; the clipped share (y ≥ 0.97) is a median
    0.25% per unit, maximum 3.3%.
  - The 70% start rule agrees with the first row for 39 of 44 units and lags it by 1 day for 4 units. Zone A2
    inverter 2 lags by 8 days (first row 2023-05-16, rule start 2023-05-24): a real commissioning ramp inside a
    scored event.
  - All 13 scored, 4 sensitivity and 10 validation events are eligible: at least 8 donors (scored minimum 20;
    SQ567 exactly 8) and at least 30 valid days in their first 90 (minimum 73 for the scored events; Zone L2 41).
    With the provisional boundary (2023-02-17) the scored events split 8 stable and 5 drifted.
  - Hidden-unit test bed: 31 units (29 stations) on 1 April 2022, 38 units (33 stations) on 1 April 2023, in 5
    groups of 5–8 units.

### F28 — On the validation units the censored index beats the median index only narrowly — *strong*
- **Evidence:** `results/nb3_index/validation_estimator.csv`. Same-time reconstruction error (oracle 90-day gain,
  fraction of AC), median over the 10 validation units: censored 0.0797, median 0.0813; the censored
  index is lower for 4 of 10 units. Clipping is rare in 2021: the mean clipped donor share over a
  validation window is at most 1.4%.
- **Reading:** rule 2 keeps the censored estimator, but the evidence is weak; the median-index ablation (A2) on the test
  events decides whether the paper can say more. The gain-fit threshold barely matters: k_min 0.3 / 0.5 / 0.7 give
  0.08127 / 0.08135 / 0.08149.

### F29 — The DC/AC prior cuts the gain error by more than half on the validation units — *strong*
- **Evidence:** `results/nb3_index/validation_priors.csv`. Median absolute error against the oracle gain: G0
  0.1125, G1 0.0438, G2 0.0401. Same-time reconstruction error with the prior gain: G0 0.0909,
  G1 0.0868, G2 0.0870. The transposition factor is close to 1 for almost every unit (tilts of 0-15°, most
  flat or "Mixed"), so G2 and G1 differ little.
- **Reading:** contribution 2 holds on development data. G2 is kept by rule 3 on gain error, although its reconstruction
  error is not lower than G1's.

### F30 — The nameplate prior is worth less than one day of the inverter's own data — *provisional*
- **Evidence:** `results/nb3_index/priors.csv`. w0 = s1^2 / sigma_p^2 (D22): scored events median 0.43 days
  (range 0.24-1.14); validation units median 0.29 days. One-day gain estimates
  of mature donors (last 60 days) scatter less (s1^2 about 0.001-0.006) than the prior misses (sigma_p^2 about 0.003-0.028).
- **Reading:** after about one clear day of its own data a new inverter's gain is better known locally than from its
  nameplate, so the prior mainly serves the first day. This weakens the planned headline of D22 and moves the
  weight of contribution 2 to day-one accuracy. Provisional: s1^2 comes from mature donors, and new units in their
  first days (commissioning ramps, F27) may scatter more; NB7 measures it on the events after the freeze.

### F31 — Final drift boundary: 2023-02-17 — *solid*
- **Evidence:** `results/nb3_index/summary.json`, `event_periods.csv`. PELT with the penalty raised until one change point
  remains: sensor / fleet proxy 2023-02-17 (0.901 to 1.531); sensor / CAMS 2023-02-14
  (0.756 to 1.166). With the 45-of-90-days rule the scored events split 8 stable and 5
  drifted (UG Hall8, UG Hall9, Zone A2 inverters 2-3, SQ Block P, Shaw Auditorium).

### F32 — Donor gains follow the DC/AC ratio — *strong*
- **Evidence:** `results/nb3_index/gains.csv`, Fig. 4 draft. Over the clean-metadata donors of the last scored event
  (Shaw Auditorium, 43 donors), corr(r, gain) = 0.635 and the median ratio gain / r is 0.86 (beta of G1). The donor
  gains range from 0.30 to 1.23 across all events.
- **Reading:** beta is the fleet's effective performance ratio on the index scale, as the guide expected (about 0.94 in
  the pilot; 0.85-0.89 here).

### F33 — The pyranometer's clock runs about 3 min behind the inverters; CAMS about 5 min — *strong*
- **Evidence:** `results/nb4_sensor/lag_peaks.csv`, `lag_scan_sensor.csv`, `lag_scan_cams.csv`, `clear_day_scan.csv`.
  The correlation of within-day 5-min changes of the clear-sky index with those of the NB2 fleet index peaks at a
  lag of −3.32 min for the sensor (peak correlation 0.393; quarterly peaks −3.88 to −2.67) and −5.02 min for CAMS
  (0.166; quarterly peaks −5.71 to −0.74, larger in the wet seasons). The guide's clear-day method has no interior
  peak within ±6 min: the correlation rises monotonically (2022: 0.9725 to 0.9833).
- **Reading:** a sensor value labelled t belongs to about t + 3 min on the inverter clock; NB4 aligns it by 3 min
  (D32). The sensor lag drifts by about 1 min over 2.5 years, so whole-minute alignment is good to ±1 min. The
  CAMS lag changes with the season; satellite scan time and cloud parallax could explain it (not tested).
  Unaligned, a 15-min sensor value would be shifted by a fifth of a slot against the fleet.

### F34 — Monthly calibration: 29 of 36 months valid, none in June–August 2023 — *solid*
- **Evidence:** `results/nb4_sensor/calibration_monthly.csv`, `qc_monthly.csv`, `dead_days.csv`, `summary.json`.
  - Valid factors: 1.187–1.285 before the boundary (the sensor reads about 0.8 of Ineichen clear sky) and
    0.730–0.885 from March 2023.
  - Rejected months: March–June 2021 (dead sensor and recovery; the detector's rescaling locked onto dead or
    overcast stretches: c = 44.9, none, 2.34, 2.56) and June–August 2023 (60, 0 and 11 clear minutes). June–August
    2023 therefore apply May 2023's factor (0.730), and July 2021 applies February 2021's (1.187).
  - February 2023 gives 0.785, the post-step level, so the causal correction catches up on 1 March 2023: the lag is
    the rest of the boundary month (about two weeks).
  - Readings above the BSRN upper limit: 2,341 raw readings (2,305 in May–October 2023) against 1,214 calibrated
    values (1,120 in February 2023, the lag month).
  - Dead days by the sensor-only rule: 53, that is 52 from 3 March to 13 May 2021 and 8 October 2021, a very dark
    day (CAMS clear-sky index 0.068) that no sensor-only rule can tell from a failure. The partly dead edges
    (14–15 May 2021, and part-days in March 2021) pass the rule. The corrected sensor has no value on
    8 October 2021, inside the windows of SQ Block S, Zone A5 and SQ Block R.
- **Reading:** recalibration against a clear-sky model needs clear minutes, and Hong Kong's 2023 wet season gave
  three months with almost none. The failure ended on about 15 May 2021, months before the first test event. This
  refines F23: the CAMS-based count of 77 dead days includes four overcast days of 2021–2022 on which CAMS reads high.

### F35 — On the validation units the fleet reconstructs a new inverter better than any irradiance source — *strong*
- **Evidence:** `results/nb4_sensor/validation_sources.csv` (development data, same time, h = 0, common slots,
  median 3,849 slots per unit). Median nRMSE with the oracle 90-day gain: fleet 0.0794, raw sensor 0.1051,
  corrected sensor 0.1080, same-month correction 0.1046, CAMS 0.1352. With the cold-start prior gain: 0.0869,
  0.1217, 0.1306, 0.1280, 0.1391. The fleet is lowest on all 10 units with either gain; the corrected sensor is worse
  than the raw sensor on all 10.
- **Reading:** in the stable period, 40 inverters are a better virtual pyranometer than the campus pyranometer (by
  about a quarter of the same-time error) or one satellite pixel. Monthly recalibration does not help while the
  sensor is stable: its factor changes from month to month (1.187 in July 2021, 1.285 in August), and a single
  gain cannot absorb these steps. Same-time evidence on development data only; the sensor table comes from the
  forecasts (NB5, NB6).

### F36 — After the step, the corrected sensor agrees with CAMS; the raw sensor reads about 1.7 times higher and keeps changing — *strong*
- **Evidence:** `results/nb4_sensor/daily_sensor.csv`, `agreement_events.csv`, `fig_sensor_correction`. Daily
  irradiation over fleet yield, scaled to 1 at its stable-period median; median after the boundary: raw 1.70,
  corrected 1.07, same-month 1.09, CAMS 1.09. The raw ratio's 30-day median peaks at 1.90 (10 April 2023) and falls
  to 1.50 by mid-December 2023. Input agreement in the windows of the scored and sensitivity events (median over
  events; each source against the event's fleet index; no target used): ratio raw 0.90 stable vs 1.61 drifted,
  corrected 1.09 vs 1.14, CAMS 1.20 vs 1.27; correlation corrected 0.925 vs 0.905, CAMS 0.869 vs 0.728.
- **Reading:** the causal recalibration removes the step after its two-week lag. The remaining rise of about 7–9% is
  shared by two independent references (corrected sensor and CAMS), so it points to the fleet proxy producing less
  per unit of irradiance in 2023 (as the CAMS / fleet step of F23), not to the sensor. The raw sensor kept changing
  through 2023, so a single correction factor would not have fixed it either.

### F37 — The step happens on 14–15 February 2023; the frozen boundary is 2–3 days late, without effect on the event split — *solid*
- **Evidence:** `results/nb4_sensor/daily_sensor.csv`, `results/nb3_index/event_periods.csv`. Daily ratio of sensor
  irradiation to fleet yield (stable median = 1): 0.85–0.88 on the overcast days of 9–12 February, 0.52 on
  13 February, 1.34 on 14 February, 1.73 on 15 February, then about 1.6–1.8. With 14 February as the boundary,
  UG Hall8 would have 50 instead of 47 days after it; no event changes period.
- **Reading:** the anomalous 13 February and the part-day of 14 February fit an intervention on the sensor, but no
  source in hand documents one; the paper describes the step, not its cause. The frozen boundary stays (D31).

### F16 — Not every site file starts on the 1st of a month — *solid*
- **Evidence:** among the 18 site files of the first event list, Indoor Sports Centre (2021-12-02), Zone J2
  (2021-11-13), Zone D (2022-01-20) and UG Hall9 (2023-02-11) start mid-month. The audit counts 5 of the 15-min and
  23 of the hourly site files. NB1 reproduces both counts: 5 of 37 and 23 of 23.
