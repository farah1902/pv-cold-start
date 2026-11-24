# Methods — as implemented

This file describes the method exactly as the code implements it, in paper-ready form. It is written step by step as
each notebook is built; until then the plan is in `research_guide.md` §2–§5, as corrected by `decisions.md`.

**Status (20 Nov 2026):** NB1 to NB4 and the forecasting development NB5a are implemented (audit, preprocessing, fleet index and priors, sensor and satellite index sources, index forecasting on the validation units).

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

**Index forecasting.** At each issue time the fleet state holds the last 16 values of the index (4 h), its 1-h and
2-h means, its 1-h standard deviation and last change, the spread, clipped share and count of the donors, the index
at the target slot one day earlier, and the known sun geometry at the target. Forecasts are issued in daylight when
at least 8 unclipped donors are online, for targets on the same day up to the last slot of the inverter files. A
quantile LightGBM model per horizon and quantile level forecasts the change of the index from its current value;
the current value is added back, and the nine quantiles are sorted. Each model is trained on all earlier pairs from
15 May 2021, with early stopping on the last fifth of the window followed by a refit on the whole window, and is
refitted at the event start and 30 and 60 days later. Its setting was chosen by time-series cross-validation on a
development index from 2021. The index quantiles are turned into 200 power members by pairing stratified index
levels with gain draws from the prior's uncertainty set, capped at the inverter limit. The baselines (climatology,
persistence, their optimal convex combination, nearest-neighbour analogs and a probabilistic persistence ensemble)
go through the same composition.

**Calibrated intervals.** The composition carries the uncertainty of the index forecast and of the gain, but not the
new roof's own deviation from the fleet, so its raw intervals are too narrow. They are recalibrated by split
conformal quantile regression on pseudo cold starts: before each forecast origin, every donor is treated as a new
unit, with a prior and uncertainty set built from the other donors, and its power is forecast from out-of-sample
index forecasts over the most recent part of the training window. For each horizon and each central interval (80,
60, 40 and 20%), the conformity scores of these pseudo forecasts, divided by the normalised clear-sky irradiance,
give the widening applied to the new unit's interval. The median and the point forecast are unchanged.

**Computing.** Development ran on a CPU (one thread per training). At the test, every neural row ran on one GPU, so the ablations are compared with the main model on the same device: the main model, its median-index, sensor-index and fleet-summary variants, TimeXer and the hidden-unit test bed. The device changes no setting. Before these runs, the GPU repeated two validation rounds of five seeds on the 10 validation units: the main model's and TimeXer's. Each round had to be level with its CPU round at every horizon, with ensemble median nRMSE within 3% and per-seed medians within three standard errors (gate results: pending). A GPU run does not reproduce the CPU run of the same seed bit for bit; the CPU path does reproduce the development runs bit for bit. The 48 CPU trainings of the main model made before the switch are compared with the GPU trainings of the same seeds, on forecasts only, as a check.

**Evaluation and statistics.** Every forecaster is scored per event and horizon on the same slots: the issue times at which all baseline forecasters have a forecast and the target is observed. The observation is the event's normalised power: the unit's series for a single inverter, and the event's target series over its AC rating for multi-unit events and site targets. A forecaster that does not cover every slot (the sensor and satellite rows) is compared on the slots both forecasters share. Seed ensembles average the sorted quantiles of the five seeds. The primary test compares the main model with persistence at 1 h by a one-sided exact Wilcoxon signed-rank test on the event-wise nRMSE differences of the 13 scored events. The other horizons are adjusted by Holm. Eight secondary comparisons use two-sided exact Wilcoxon tests at 1 h with Holm across the eight. Effect sizes are Hodges–Lehmann estimates (the median of the Walsh averages) with exact distribution-free 95% intervals. Two forecasters are called level when their medians differ by less than 3% and the adjusted test is not significant. Per event, a Diebold–Mariano test of squared loss (Newey–West variance with lag h − 1, Harvey–Leybourne–Newbold correction) is run at 1 h. Day-block bootstraps (whole days, and 3-day moving blocks; B = 2,000) give each event's interval. A hierarchical bootstrap (events, then days) gives the campus-level interval of the median skill.
