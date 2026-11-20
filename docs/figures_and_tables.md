# Figures and tables

Every figure and table, the code that draws it and its role in the paper. The plan is in `research_guide.md` §5.5
(tables) and §6 (figures); this file records what exists.

**Status (20 Nov 2026):** draft figures from NB1 to NB5a (not in submission form).

| File | Content | Code | Role |
| --- | --- | --- | --- |
| `results/nb1_audit/figures/sensor_drift.{png,pdf}` | Sensor vs CAMS, sensor and CAMS vs fleet, noon clear-sky ratios | `audit.fig_sensor` (NB1) | Draft of Fig. 2 |
| `results/nb2_panel/figures/fig1_timeline.{png,pdf}` | Starts and 90-day windows of all events, drifted window shaded (provisional boundary) | NB2 | Draft of Fig. 1 |
| `results/nb2_panel/figures/label_offset.{png,pdf}` | Correlation with clear sky against the time shift | NB2 | Supplement |
| `results/nb3_index/figures/fig3_index_day.{png,pdf}` | Median and censored fleet index, pyranometer and CAMS indices, and the clipped share on a variable development day | NB3 | Draft of Fig. 3 |
| `results/nb3_index/figures/fig4_gain_dcac.{png,pdf}` | Donor gain vs DC/AC ratio with the beta line (donor set of Shaw Auditorium; two metadata-error donors fall outside the axis range) | NB3 | Draft of Fig. 4 |
| `results/nb4_sensor/figures/fig_sensor_correction.{png,pdf}` | Daily irradiation over fleet yield for the raw, corrected and same-month sensor and CAMS (30-day medians); monthly calibration factors; daily zoom on January–April 2023 | NB4 | Sensor section or supplement (could join Fig. 2) |
| `results/nb5a_dev/figures/fig_validation_horizon.{png,pdf}` | Median nRMSE and CRPS against horizon on the validation units, every model and the oracle | NB5a | Development record (the paper's Fig. 5 comes from the test run) |
| `results/nb5a_conformal/figures/fig_conformal_reliability.{png,pdf}` | Observed vs nominal coverage of the central intervals at 1 h, and PICP80 against horizon, raw and conformal (validation units) | NB5a conformal | Development record (the paper's reliability figure comes from the test run) |
| `results/nb1_audit/figures/quirks.{png,pdf}` | 17:55 cut (Zone A5), Zone J2 before its inverter file, Zone D station / inverter 2 | `audit.fig_quirks` (NB1) | Data section or supplement |

Changes to the planned list:
- Figs. 11 (skill vs donor radius) and 12 (map of the Moroccan virtual fleets) move to the follow-up paper (D07).
- Fig. 1 shows the 14 observed starts and marks the 3 left-censored ones (D08).
