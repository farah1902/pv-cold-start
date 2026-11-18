# Findings

One entry per empirical result, numbered F01, F02, … and never renumbered. Confidence: *solid* (checked in the files
or in the primary source), *strong*, *provisional* (reported in an audit, still to be reproduced by code in this
repository). Paths are relative to `data/raw/hkust/Dataset/Time series dataset/` unless stated.

### F01 — Inverter files cover 06:00–17:55 only (144 rows a day); site files cover 00:00–23:45 — *solid* (window); *provisional* (energy shares)
- **Evidence:** all 44 inverter files end at 17:55 on 2023-12-31. Zone A5 has 117,780 rows: 817 days of 144 rows and
  its first day of 132 rows (it starts at 07:00). On 2022-06-21, Zone A5's site file still shows 598 W at 18:00,
  285 W at 18:15, 51 W at 18:30 and zero from 18:45. The review audit of 18 Nov reports evening energy after 18:00 at
  a median 0.17% of the total, at most 0.5% in June (to be reproduced in NB1).
- **Reading:** the fleet index cannot be computed after 17:55, and a 6-h forecast can only be issued until 11:55.
- **Paper:** Data §3.5; protocol (D12); threats to validity.

### F02 — Two timestamp formats — *solid* (inverter files, weather files); *provisional* (site-file count)
- **Evidence:** 13 inverter files write `2021/6/2 6:00` (SQ567, Zone A7, SQ Apartment 1-12, 25-36 and 37-48, UG Hall2
  RF, UG Hall3, UG Hall4, UG Hall7, Zone J1, Zone J2, Zone L2, LSK South); the other 31 write `2021-05-07 07:00:00`.
  The weather files write `2022/1/1 0:00`. The audit counts 10 site files in year/month/day form.
- **Paper:** not in the text; D13 (code).

### F03 — Zone J2 produced for 25 days before its inverter file begins — *solid*
- **Evidence:** its site file starts on 2021-11-13 (188.8 kWh that day) and holds 1,597 kWh before 2021-12-08, the
  first day of its inverter file. Metadata connection date: 2021-12-01.
- **Reading:** the event is re-dated to 2021-11-13, with the site series as target (D08).

### F04 — Zone L2's start is left-censored — *solid*
- **Evidence:** its site file starts on 2022-06-01 and already produces 40.4 kWh that day; 405 kWh before its inverter
  file begins on 2022-08-02. Metadata connection date: 2022-07-30.
- **Reading:** an operator had site-level history before the inverter file; moved to the sensitivity set (D08).

### F05 — Zone D inverter 1 is not a capacity addition — *provisional*
- **Evidence:** the review audit of 18 Nov reports that the Zone D station total ran at 1.6–1.7 × inverter 2 from
  January to October 2022, so inverter 1 was producing before its file starts on 2022-12-03 (to be reproduced in NB1).
- **Reading:** Zone D is scored as one station-level event from 2022-01-19 (D08).

### F06 — Telemetry starts and connection dates disagree, in both directions — *solid* (checked rows); *provisional* (audit counts)
- **Evidence:** the 19 start dates of the guide's first event list equal the first rows of the inverter files. Metadata
  connection dates (Brick `.ttl`): Library 2022-05-31 (telemetry 2022-06-01), SQ Block P 2023-07-21 (telemetry
  2023-06-22), Shaw Auditorium 2023-07-29 (telemetry 2023-07-09), Zone J2 2021-12-01, Zone L2 2022-07-30. The audit
  reports that every inverter file already produces on its first day, and connection 113 days before telemetry for
  Zone J1 and 92 days for Wong Check She.
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

### F09 — The pyranometer is a LI-COR LI-200R (±3% typical, ±5% maximum) — *solid* (sensor); *provisional* (drift size)
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

### F16 — Not every site file starts on the 1st of a month — *solid* (4 checked); *provisional* (full count)
- **Evidence:** among the 18 site files of the first event list, Indoor Sports Centre (2021-12-02), Zone J2
  (2021-11-13), Zone D (2022-01-20) and UG Hall9 (2023-02-11) start mid-month. The audit counts 5 of the 15-min and
  23 of the hourly site files.
