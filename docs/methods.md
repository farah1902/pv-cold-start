# Methods — as implemented

This file describes the method exactly as the code implements it, in paper-ready form. It is written step by step as
each notebook is built; until then the plan is in `research_guide.md` §2–§5, as corrected by `decisions.md`.

**Status (18 Nov 2026):** the data audit (NB1) is implemented.

**Data audit.** Timestamps are kept as recorded (Hong Kong time) and parsed with two explicit formats; any failure stops the run. AC ratings come from the inverter model names (an explicit table), DC ratings from module counts and watt-peak. The pyranometer is compared at 1-min resolution with CAMS all-sky GHI (steps with reliability below 1 excluded) on minutes with solar elevation above 10°, and with pvlib's Ineichen clear sky at the campus coordinate (altitude 124 m). A fleet proxy, the median normalised daily yield of the 10 units online before 22 May 2021, gives a third reference. Drift dates come from a one-break binary segmentation of the daily log-ratios, after removing days with a dead sensor.
