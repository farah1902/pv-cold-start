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

### F38 — On the validation units, forecasting the index, not the gain, dominates the error — *strong*
- **Evidence:** `results/nb5a_dev/val_medians.csv` (development data, full window). Median nRMSE of the same-time index
  with the cold-start prior (oracle A7): 0.083 to 0.095 at every horizon. LightGBM: 0.129 at 15 min, 0.181 at 1 h,
  0.237 at 4 h.
- **Reading:** beyond 15 min most of the error is the cloud forecast, as in the guide's pilot. The gain prior sets
  the floor; the index forecaster sets the level.

### F39 — With a persistence anchor, LightGBM beats persistence on all 10 validation units and CLIPER up to 2 h — *strong*
- **Evidence:** `results/nb5a_dev/val_medians.csv`, `val_skill.csv` (development data; 10 units, June–October 2021).
  - Median nRMSE at 1 h: LightGBM 0.1810, CLIPER 0.1857, A5 0.1909, persistence 0.1962, climatology 0.2422.
  - Median skill at 1 h: vs persistence 0.078 (10 of 10 units), vs CLIPER 0.022 (8 of 10), vs A5 0.057
    (9 of 10).
  - At 4 h and 6 h CLIPER is better (skill −0.013 and −0.036; LightGBM better on 1 of 10 units).
  - CRPS skill vs PeEn: 0.501 at 15 min, 0.313 at 1 h, 0.082 at 6 h; LightGBM has the lowest CRPS at every
    horizon.
  - Without the anchor (`results/nb5a_variants/`), the same bank gives 0.1913 at 1 h and beats CLIPER on 2 of 10
    units.
- **Reading:** the anchor (D34) is what makes boosting competitive when the history is short. With 1–4 months of
  history, nothing beats CLIPER's climatology blend at 4–6 h; the test events have more history (F41). Development
  evidence only: the test run decides.

### F40 — The 80% intervals are too narrow: coverage 0.63–0.71 — *strong*
- **Evidence:** `results/nb5a_dev/val_medians.csv`. Median PICP80 of LightGBM: 0.685 (15 min), 0.698, 0.714 (1 h),
  0.662, 0.629, 0.649 (6 h); PeEn 0.66–0.68; climatology 0.67–0.69.
- **Reading:** the pre-registered target (75–85%) is missed without calibration. The conformal layer of D06 must be
  built and frozen before the tag.

### F41 — The validation units have far less history than the test events — *solid*
- **Evidence:** `results/nb2_panel/events.csv`, `results/nb5a_dev/val_diag.csv`. History from 15 May 2021 to the first
  origin: validation units 18–61 days (median 37), at most 121 days at the third origin; scored events 143–785 days
  (median 186). Training pairs at 1 h per validation origin: 437–4,848 (median 2,338).
- **Reading:** R1 is decided in a data-poor regime. A data-hungry model (PVSetFormer, TimeXer) meets its hardest
  case there, and LightGBM may gain more history on the test events than the validation shows. The rule stays as
  approved (D25); the design of PVSetFormer should plan for short histories.

### F42 — Tuning barely matters; the formulation does — *solid*
- **Evidence:** `results/nb5a_dev/cv_summary.csv`, `cv_grid.csv`. Mean pinball of the chosen setting (31, 0.05,
  200) 0.068554 vs the guide's starting point 0.068835 (0.4%). num_leaves 31 and 63 are the same model on the
  development data (min_data_in_leaf 200 caps the tree size); num_leaves 15 differs by 3.8e-5. The most
  regularised settings (min_data_in_leaf 200) lead.
- **Reading:** the persistence anchor changes the 1-h error by 5% (F39); the whole grid changes the pinball loss by
  0.4%. Development time is better spent on the formulation and the calibration than on the grid.

### F43 — Conformal calibration on pseudo cold starts brings the intervals to their nominal coverage — *strong*
- **Evidence:** `results/nb5a_conformal/val_conformal_medians.csv`, `corrections.csv` (development data; the 10
  validation units are true cold starts, never in their own donor set).
  - Median PICP80, raw → conformal: 0.685 → 0.786 (15 min), 0.714 → 0.797 (1 h), 0.649 → 0.778 (6 h); all horizons
    0.753–0.803 after calibration.
  - At 1 h, the 60, 40 and 20% intervals cover 0.618, 0.398 and 0.190 (raw 0.511, 0.325, 0.145).
  - IS80 falls at every horizon (1 h: 0.5739 → 0.5716, lower on 8 of 10 units; 6 h: 0.7024 → 0.6664). The CRPS of the
    9-quantile distribution is lower from 30 min on (1 h: 0.0940 → 0.0932) and unchanged at 15 min (0.0619 vs 0.0620).
  - The donors' pseudo cold starts under-cover like the true cold starts (raw 80% coverage 0.714 vs 0.714 at 1 h,
    0.722 vs 0.685 at 15 min). Median
    corrections at 1 h: 0.047 (80%), 0.032 (60%), 0.019 (40%), 0.011 (20%), in units of G̃.
- **Reading:** the composition misses the target roof's own deviation from the fleet; the pseudo cold starts measure
  it, and the calibration closes the gap at every level, not only at 80%. The pre-registered coverage target
  (75–85%) is met on development data; the test run decides.

### F44 — PVSetFormer passes rule R1 by 0.7% at 1 h; it leads from 2 h, LightGBM leads at 15–30 min — *provisional*
- **Evidence:** `results/nb5c_r1/summary.json`, `r1_medians.csv`, `r1_units_1h.csv` (development data: the 10
  validation units; 5-seed ensembles of both models, D37).
  - Median nRMSE, PVSetFormer vs LightGBM: 15 min 0.1329 vs 0.1291 (+3.0%); 30 min 0.1566 vs 0.1562 (+0.3%);
    1 h 0.1800 vs 0.1813 (−0.7%); 2 h 0.2093 vs 0.2103 (−0.5%); 4 h 0.2334 vs 0.2368 (−1.4%); 6 h 0.2068 vs 0.2180
    (−5.1%). Units won by PVSetFormer: 3, 3, 4, 8, 10 and 9 of 10.
  - At 1 h the Wilcoxon signed-rank test across units gives p = 1.0 (rank sums 28 and 27): PVSetFormer's four wins
    include the two largest differences (UG Hall2 2F −6.4%, Zone A2 1 −5.3%; also SQ567 −1.5%, UG Hall2 RF −1.2%);
    its six losses are +0.5% to +2.1%, four of them on the SQ Apartment roofs.
  - Median CRPS: LightGBM is better up to 1 h (15 min +5.5%, 30 min +5.4%, 1 h +1.2% for PVSetFormer); PVSetFormer
    is better from 2 h (−2.1%, −3.1%, −6.2%). Raw 80% coverage: PVSetFormer 0.654–0.713, LightGBM 0.631–0.709.
  - Seeds: PVSetFormer's single seeds give 0.17949–0.18281 at 1 h (mean 0.18104, s.d. 0.0014), LightGBM's
    0.18090–0.18157 (s.d. 0.00025), a 5.7-fold spread. Ensembling lowers PVSetFormer's value by 0.0010 and leaves
    LightGBM's unchanged. Two of PVSetFormer's five single seeds beat LightGBM's ensemble. The single-seed round V4a
    happened to use the best of the five (0.17949).
- **Reading:** the pre-registered rule selects PVSetFormer, but at 1 h the two models are level within the spread
  of PVSetFormer's seeds. The difference grows with the horizon: from 2 h on, where persistence fails, the set of
  donors and the sun geometry pay off. At 15–30 min, persistence-type information dominates and the gradient-boosted
  trees use it better. The selection used the same 10 units on which six PVSetFormer variants were developed, which
  favours PVSetFormer. The test run is the unbiased check.

### F45 — The conformal layer calibrates PVSetFormer's intervals as well as LightGBM's — *strong*
- **Evidence:** `results/nb5c_conformal/summary.json`, `val_conformal_medians.csv` (development data: the 10
  validation units; PVSetFormer's 5-seed ensemble, D46).
  - Median PICP80, raw → conformal: 0.705 → 0.792 (15 min), 0.713 → 0.799 (1 h), 0.691 → 0.804 (2 h), 0.673 →
    0.825 (6 h). At every horizon the calibrated value is between 0.79 and 0.83.
  - At 1 h the 60, 40 and 20% intervals cover 0.623, 0.424 and 0.206 (raw 0.542, 0.347, 0.158).
  - IS80 falls at every horizon (1 h: 0.5937 → 0.5897, lower on 8 of 10 units; 6 h: 0.6608 → 0.6292); the
    9-quantile CRPS falls too (1 h: 0.0948 → 0.0941).
  - Raw 80% coverage of the donors' pseudo cold starts: 0.720 at 15 min, 0.684 at 1 h, 0.615 at 6 h. The median
    80% corrections, in units of G̃, are 0.038, 0.063 and 0.106.
  - Against LightGBM's layer (NB5a, single seed), after calibration: IS80 at 1 h 0.5897 vs 0.5716, at 6 h 0.6292
    vs 0.6664; CRPS at 1 h 0.0941 vs 0.0932, at 6 h 0.1083 vs 0.1156. This is the same split as for the point error
    (F44): LightGBM ahead up to 1 h, PVSetFormer ahead from 2 h.
- **Reading:** the layer works whichever index forecaster feeds it, because it corrects what neither forecaster
  sees: the new roof's own deviation from the fleet. PVSetFormer's raw intervals cover slightly more than
  LightGBM's on the validation units (raw PICP80 0.654–0.713 vs 0.631–0.709) but are still too narrow. Its
  corrections are larger (80% at 1 h: 0.063 vs 0.047), because its calibration predictions cover the donors less
  well (0.684 vs 0.714 at 1 h). The coverage target (75–85%) is met on development data; the test run decides.

### F46 — PVSetFormer's intervals barely widen with recent volatility; LightGBM's do — *strong*
- **Evidence:** `results/nb5c_diag/V4a_5s/vol_regimes.csv`, `summary.json` (`python tools/pvsf_vol_diag.py --pvsf
  V4a_5s`; development data: the validation units' forecast issue times, both models as 5-seed ensembles, index
  level before composition with the gain).
  - The issue times are split into quartiles of the index's s.d. over the last hour, known at the issue time (the
    LightGBM feature `sd_1h`).
  - At 15 min, the mean width of PVSetFormer's 10–90% interval goes from 0.323 (calmest quartile) to 0.366 (most
    volatile). LightGBM's goes from 0.175 to 0.410. Coverage of that interval: PVSetFormer 0.947 → 0.676, LightGBM
    0.847 → 0.755.
  - In the calmest quartile at 15 min, PVSetFormer's pinball loss is 40% higher than LightGBM's (0.0243 vs 0.0173),
    and its median is also worse (MAE 0.0529 vs 0.0400). In the other quartiles the gap is 3.8–6.3%. Over all issue
    times: +8.4% at 15 min, +2.3% at 1 h, −6.4% at 6 h.
  - At 1 h the same pattern is weaker: widths 0.462 → 0.522 against 0.367 → 0.587, a calm-quartile gap of 7.3%. At
    6 h PVSetFormer is better in every quartile (−3.7% to −8.9%).
- **Reading:** LightGBM reads the recent volatility directly (`sd_1h`, `dk`) and scales its quantiles with it.
  PVSetFormer's quantile spread comes from softplus increments whose inputs are linear in the lags, so it cannot form
  a scale such as |Δk| or a s.d. Its short-horizon deficit (F44) is a heteroscedasticity deficit, concentrated in
  calm conditions. This motivates V5 (D47, D48).

### F47 — Without its donor tokens, PVSetFormer forecasts as well: the fleet summary carries the information — *strong*
- **Evidence:** `results/nb5c_variants/A6e_5s/scores.csv` against `V4a_5s/scores.csv` (development data: the 10
  validation units; both 5-seed ensembles with the same seeds, setting and protocol; rule R2, D38).
  - A6e is V4a without donor tokens, set attention and pooling: one fleet-summary token per patch (index values,
    validity, σ, c, n), 46,621 parameters against 60,157.
  - Median nRMSE, A6e vs V4a: 15 min 0.1331 vs 0.1329, 30 min 0.1574 vs 0.1566, 1 h 0.1800 vs 0.1800 (0.17997 vs
    0.18001), 2 h 0.2089 vs 0.2093, 4 h 0.2331 vs 0.2334, 6 h 0.2069 vs 0.2068. Every difference is below 0.6%, and
    the CRPS differences below 1%.
  - Per unit, A6e is better on 4, 4, 3, 4, 6 and 5 of 10 units at the six horizons; no unit differs by more than
    3%. At 1 h the Wilcoxon p across units is 1.0.
  - Single seeds at 1 h: A6e 0.17935–0.18233 (mean 0.18041, s.d. 0.0012), V4a 0.17949–0.18281 (mean 0.18104,
    s.d. 0.0014). Seed by seed, the differences go both ways (−0.0027 to +0.0026).
  - A6e's ensemble is also below LightGBM's at 1 h (0.17997 vs 0.18130).
- **Reading:** on this campus the per-donor tokens add nothing that the causal fleet index and its spread do not
  already carry. The censored index is close to a sufficient statistic of the donors for forecasting the index.
  PVSetFormer's advantage over LightGBM (F44) comes from the neural model of the fleet summary with the linear path,
  not from attention over donors. This supports contribution 1 (the causal fleet index) and weakens the set-
  attention part of PVSetFormer's novelty. It may differ on the test events (longer histories, other donor sets)
  or with spatially spread fleets, which this campus cannot test.

### F48 — The three learned index forecasters are level at 1 h; TimeXer's ensemble is lowest — *provisional*
- **Evidence:** `results/nb5c_variants/TX1_5s/`, `V4a_5s/`, `LGB_seeds/` scores (development data: the 10 validation
  units; 5-seed ensembles with the same seeds; TimeXer with PVSetFormer's per-donor inputs, rule R2, D49).
  - Median nRMSE, TimeXer vs PVSetFormer vs LightGBM: 15 min 0.1301 / 0.1329 / 0.1291; 30 min 0.1558 / 0.1566 /
    0.1562; 1 h 0.1784 / 0.1800 / 0.1813; 2 h 0.2105 / 0.2093 / 0.2103; 4 h 0.2353 / 0.2334 / 0.2368; 6 h 0.2091 /
    0.2068 / 0.2180.
  - TimeXer against PVSetFormer: −2.1% at 15 min, −0.9% at 1 h, +1.1% at 6 h; units won 8, 6 and 4 of 10; Wilcoxon
    p 0.43, 0.56 and 0.23. Against LightGBM: +0.8%, −1.6%, −4.1%; p 0.49, 0.38 and 0.32.
  - Median CRPS: TimeXer 0.0619 / 0.0931 / 0.1108 at 15 min / 1 h / 6 h; PVSetFormer 0.0651 / 0.0948 / 0.1095;
    LightGBM 0.0617 / 0.0937 / 0.1167.
  - Single seeds at 1 h: TimeXer mean 0.18109 (s.d. 0.0011), PVSetFormer 0.18104 (0.0014), LightGBM 0.18123
    (0.00025). TimeXer gains most from the ensemble (−0.0026, against −0.0010 and +0.0001).
- **Reading:** on validation the three learned forecasters differ by less than 1% at 1 h and by less than the guide's
  3% at most horizons; LightGBM falls behind the two transformers only at 4–6 h. A TimeXer that receives the same
  per-donor inputs is at least as good as PVSetFormer up to 1 h. The paper cannot rank PVSetFormer above TimeXer on
  this evidence.

### F49 — In calm states PVSetFormer's median leaves persistence and reverts toward the mean — *strong*
- **Evidence:** `results/nb5c_diag/<round>/vol_regimes.csv` and `calm_by_level.csv` (`tools/pvsf_vol_diag.py`;
  development data, index level, 15 min; calmest quartile of the last hour's s.d.).
  - Persistence is the best median there: MAE 0.0400, equal to LightGBM's. LightGBM's median moves 0.015 from k(t)
    on average, TimeXer's 0.023, PVSetFormer's (V4a, 5 seeds) 0.036.
  - By index level within the calm quartile: on clear spells (k(t) > 0.9; 1,817 issue times) PVSetFormer's median
    moves 0.047 and is biased −0.029 (LightGBM 0.010 and +0.009; TimeXer 0.029 and −0.010), MAE 0.053 against
    0.030 for LightGBM and 0.029 for persistence. On dark spells (k(t) ≤ 0.3; 3,769) it is biased +0.017 (LightGBM
    +0.002), MAE 0.042 against 0.032.
  - V5a makes the spread follow volatility but leaves this median error (clear spells: move 0.055, bias −0.037).
    V5b's gate reduces it (move 0.040, bias −0.021) and halves the calm pinball gap.
- **Reading:** PVSetFormer pulls the 15-min median toward the mean, which is right at 6 h but wrong in calm states
  at 15 min. A likely cause is the decoder, whose horizon queries attend to one another and share one output head,
  so short horizons inherit the long horizons' mean reversion. TimeXer reads each horizon out with its own weights.

### F50 — A per-horizon readout removes most of the 15-min drift but over-fits the long horizons; the horizons' mutual attention is not the cause — *provisional*
- **Evidence:** `results/nb5c_variants/{V6a,V6b,V7a,V7b}/` and `results/nb5c_diag/<round>/` (development data;
  1 seed, 20261119, each paired with V4a's round at the same seed; all start at V4a's outputs).
  - V6a (horizon queries kept apart in the decoder): 15 min 0.1333 vs 0.1339, 1 h 0.18053 vs 0.17949, 6 h 0.2112
    vs 0.2073. In the calmest quartile at 15 min the median moves 0.037 from k(t) (V4a 0.034); on clear spells
    (k(t) > 0.9) its bias is −0.035 (V4a −0.031).
  - V6b (per-horizon readout added to the shared head): 15 min 0.1311 (−2.1%, better on 8 of 10 units); pinball gap
    to LightGBM at 15 min +6.2% (V4a +9.5%), calmest quartile +30% (V4a +41%). On clear spells: move 0.031 (V4a
    0.048), bias −0.013 (V4a −0.031), MAE 0.042 (V4a 0.054; LightGBM 0.030; persistence 0.029). But 1 h +0.4%,
    4 h +5.2%, 6 h +6.3%; mean best epoch 14 (V4a 17).
  - V7a (learned donor identity): within 0.11% of V4a at every horizon; better at 1 h on 9 of 10 units.
  - V7b (each donor's deviation from the index): 1 h −0.1%, 2 h −0.5%, 6 h −0.7%; CRPS −0.4% at 1 h, −0.9% at 6 h;
    better at 1 h on 5 of 10 units.
  - V8a (the readout at 15 min only): 15 min 0.1308 (−2.3%), 6 h +0.8%, but 30 min +1.4% and 1 h +1.1%.
    V8b (V7a + V7b): within ±0.8% of V4a at every horizon.
- **Reading:** F49's drift comes from the shared output head, not from the horizons attending to one another: a
  separate readout lets the 15-min median stay near persistence. Separate readouts at every horizon over-fit the
  long ones, which have fewer training pairs and noisier targets. The two donor options move the forecast by less
  than one seed's spread; V7a's consistency across units hints at a small real effect, but V8b, which combines
  them, gains nothing. Same-seed pairing does not remove the seed spread (the paths diverge in training; V4a's
  single seeds at 1 h have s.d. 0.0014, about 0.8%), so only differences of about 2% or more are visible in a
  one-seed round. Single seed: provisional; V8a is checked with 5 seeds.

### F51 — On the validation units the fleet index forecasts a new inverter better than the pyranometer index up to 1 h, and as well from 2 h — *strong*
- **Evidence:** `results/nb5d_sources/medians.csv`, `summary.json` (NB5d, 21 Nov 2026; development data, 10
  validation units; the sensor rows use LightGBM with the part-2a setting and features from the source alone (D51);
  each row is scored against fleet LightGBM on the same slots; priors recomputed from NB4's external gains, largest
  difference from NB4's 4.4e-16).
  - A4 (raw sensor index): median change in nRMSE against fleet LightGBM +8.8% at 15 min, +3.4% at 30 min, +1.7% at
    1 h (0 of 10 units better at each; Wilcoxon p = 0.002), then +0.5%, +0.2% and 0.0% at 2, 4 and 6 h (p 0.23,
    0.28, 0.70). Median nRMSE at 1 h 0.1839 vs 0.1810.
  - A4b (corrected sensor index): +13.1%, +6.6%, +3.5% up to 1 h (0 of 10 units better, p = 0.002), +2.0%, +0.9%,
    +1.2% at 2–6 h. Worse than the raw sensor at every horizon.
  - A9 (CAMS index persisted, × prior gain): +16.3% at 15 min, +4.2% at 1 h, +9.2% at 6 h; better on 1 of 10 units
    up to 1 h and on none from 2 h. Slot coverage 0.97 at 1 h.
  - A9n (oracle: the CAMS index at the target time): −20.0% at 1 h and −32.6% at 6 h (10 and 9 of 10 units better),
    but +9.9% at 15 min.
  - A4c (PVSetFormer V4a plus the corrected sensor index in its fleet token, 1 seed, `results/nb5c_variants/A4c/`):
    against V4a at the same seed +0.8% at 15 min, +0.5% at 1 h (better on 2 of 10 units), −0.4% at 6 h.
- **Reading:** with the learner held fixed, a co-located pyranometer gives a new inverter no forecasting advantage
  over the index of the inverters already online: it is worse up to 1 h, where the forecast leans on the current
  state and the fleet tracks the inverter better (F35), and level from 2 h. The monthly correction does not help on
  these stable-period units (as at the same time, F35). Given the fleet index, the sensor adds nothing either
  (A4c, within single-seed noise). A9n is an oracle, not a forecast: it bounds what a perfect
  satellite nowcast of the target time could add from 30 min on. Development data; the paper's numbers come from the
  test run.

### F16 — Not every site file starts on the 1st of a month — *solid*
- **Evidence:** among the 18 site files of the first event list, Indoor Sports Centre (2021-12-02), Zone J2
  (2021-11-13), Zone D (2022-01-20) and UG Hall9 (2023-02-11) start mid-month. The audit counts 5 of the 15-min and
  23 of the hourly site files. NB1 reproduces both counts: 5 of 37 and 23 of 23.
