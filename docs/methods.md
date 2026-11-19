# Methods — as implemented

This file describes the method exactly as the code implements it, in paper-ready form. It is written step by step as
each notebook is built; until then the plan is in `research_guide.md` §2–§5, as corrected by `decisions.md`.

**Status (19 Nov 2026):** NB1 to NB4 are implemented (audit, preprocessing, fleet index and priors, sensor and satellite index sources).

**Data audit.** Timestamps are kept as recorded (Hong Kong time) and parsed with two explicit formats; any failure stops the run. AC ratings come from the inverter model names (an explicit table), DC ratings from module counts and watt-peak. The pyranometer is compared at 1-min resolution with CAMS all-sky GHI (steps with reliability below 1 excluded) on minutes with solar elevation above 10°, and with pvlib's Ineichen clear sky at the campus coordinate (altitude 124 m). A fleet proxy, the median normalised daily yield of the 10 units online before 22 May 2021, gives a third reference. Drift dates come from a one-break binary segmentation of the daily log-ratios, after removing days with a dead sensor.

**Preprocessing.** The 5-min inverter values are means over the interval that starts at their stamp (shift +3.0 min
estimated by correlation with clear sky on 30 clear days). Solar geometry and Ineichen clear sky are computed at the
effective time (slot + 8 min for 15-min slots). Quality flags mark night power, negative power, values frozen for an
hour or more in daylight, normalised power above 1.05 and outages (zero power while a crude fleet index exceeds
0.3); negative and night values are removed, the others are kept and flagged. Each 15-min value is the mean of three
5-min values (at least two present). Power is normalised by the AC rating from the inverter model name, corrected for
two metadata errors. A unit starts on the first day d with valid power (above 2% of AC) in at least 70% of daylight
slots on d and d+1. Events start on their approved observed start; donors are units started at least 14 full days
earlier and online in the week before.

**Fleet index, gains and priors.** For each event, a donor's implied index is its normalised power divided by its gain
and the normalised clear-sky irradiance; flagged slots are excluded. The median index is the median over unclipped
donors. The censored index minimises a Huber loss (delta = 0.05) of the donors' power against the inverter-limited
model min(1, g k G̃) over all online donors, so a clipped donor bounds the index from below. Donor gains are fitted
by the same loss against a leave-one-out median index, on slots with G̃ > 0.2 and index above 0.3. The fit
alternates five times, renormalising to a median gain of 1. The prior gain of a new unit is beta r T, where beta is
the median of g / (r T) over clean-metadata donors and T a clear-sky Perez transposition factor. The prior's weight
against the unit's own data is w0 = s1^2 / sigma_p^2 days, from the donors' leave-one-out prior errors and one-day
gain estimates. The k_min threshold, the estimator and the prior variant were chosen on the 10 validation units by
rules fixed in advance.

**Sensor and satellite index sources (baselines only).** The pyranometer and the satellite enter only the baselines.
Both are first aligned to the inverter clock by the lag that maximises the correlation of their within-day 5-min
changes with those of the fleet index (3 min for the pyranometer, 5 min for CAMS). The pyranometer is then cleaned
and recalibrated with information available at the time. Readings below −2 W/m² are removed. A night offset, the
median reading at solar elevation below −6° over the previous 7 days, is subtracted. Days with less than 3% of
clear-sky irradiation count as sensor failures. Clear minutes are detected each month with the method of Reno and
Hansen (pvlib), and the median ratio of clear-sky to measured irradiance over the clear minutes with zenith below 70°
of the latest valid earlier month (at least 120 minutes, factor between 0.5 and 2) rescales the current month. The
BSRN upper limit is applied to the calibrated value. Each source gives a 15-min clear-sky index at the panel slots (the
mean of at least 10 minutes over the same Ineichen clear sky as the fleet index). Donor gains are refitted against
each source with the fleet's gain-fit rule, without renormalisation, and the new unit's prior follows from them as
for the fleet.
