# Methods — as implemented

This file describes the method exactly as the code implements it, in paper-ready form. It is written step by step as
each notebook is built; until then the plan is in `research_guide.md` §2–§5, as corrected by `decisions.md`.

**Status (18 Nov 2026):** the data audit (NB1) is implemented.

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
