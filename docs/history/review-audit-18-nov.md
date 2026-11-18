# Review of 18 Nov 2026: verified against the HKUST files, decided and applied

All decisions below were approved by the user on 18 Nov 2026 and applied to the methodology document.

## Decisions
- Event list: 14 scored events with observed starts, 3 sensitivity events (left-censored starts), 2 removed.
- Primary horizon: 1 h for every hypothesis test; the other horizons are secondary, with Holm correction.
- Drifted window (about 5 events): effect sizes only (Hodges–Lehmann with day-block bootstrap intervals, events won); significance from per-event Diebold–Mariano tests at 1 h. The drift boundary (PELT) and the event-assignment rule (at least half of the 90 test days after the boundary) are fixed before scoring.
- "Healthy" sensor period renamed "stable".
- Cross-horizon comparisons use the common target window 12:00–17:55; issue times run 06:00 to 17:55 minus the horizon.

## Evidence
1. Daily window: inverter files 06:00–17:55, 144 rows a day; site files 00:00–23:45. Energy after 18:00 is a median 0.17% of the total, up to 0.5% in June. Zone A5 on 21 June 2022: 598 W at 18:00, zero at 18:45.
2. Start dates:
   - Zone J2: site file from 2021-11-13 (mid-month ramp), 1,597 kWh before its inverter file (2021-12-08). Re-dated to 2021-11-13, with the site series as target.
   - Left-censored, moved to the sensitivity set: Zone L2 (site file from 2022-06-01, already producing; 405 kWh before the inverter file), Zone J1 (2022-03-01, connected 113 days earlier), Wong Check She (2021-12-01, connected 92 days earlier).
   - Zone D inverter 1 is not a capacity addition: the station total ran at 1.61–1.70 × inverter 2 from January to October 2022. Zone D is scored as one station-level event from 2022-01-19.
   - Zone A2 inverters 2–3: a confirmed addition.
   - Every inverter file is already producing on its first day.
   - Site files not starting on the 1st of a month: 5 of the 15-min and 23 of the hourly files.
3. CAMS: the first files are McClear only (sky type "Clear"). They must be re-downloaded with "Observed cloud", with Safi running to 2018-12-31. A9 and the HKUST satellite check are dropped if Hong Kong has no all-sky data.
4. Statistics: n = 6 gives a min one-sided p of 1/64, ≥ 0.094 after Holm over 6 horizons; with 5 drifted events the min p is 1/32.
5. Timestamps: 13 inverter files and 10 site files use year/month/day. Pyranometer: LI-COR LI-200R (±5%), so the step is a fault. SQ567: 8 donors only with SQ3 at exactly 14 days, under the rule "a donor started at least 14 full days before the event".

## Scored events (14)
SQ Block S, Zone A5, SQ Block R, Zone A7, Zone A6, Zone J2 (from 2021-11-13), Indoor Sports Centre, Zone D (station level, from 2022-01-19), Library, UG Hall8, UG Hall9, Zone A2 inverters 2–3, SQ Block P, Shaw Auditorium. The drifted window holds the last five.
Sensitivity set: Wong Check She, Zone J1, Zone L2. Removed: Zone D inverter 1, S H Ho.
