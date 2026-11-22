# Paper handoff — the document the writing agent reads first

Skeleton created on 18 Nov 2026. It is filled once results exist (roadmap Phase 9).

## 1. The paper in one paragraph
_To write from the evidence. The planned thesis is in `research_guide.md` §1._

## 2. Suggested storyline
_Empty._

## 3. Corrections to the guide
See `decisions.md`, entries marked **[guide deviation]**: D07 (Morocco scope). Also: the positioning table (guide §1)
must add Longarini et al. (2026) (F19). Additions approved on 18 Nov: D18–D22.

## 4. Status of each contribution
| Contribution | Status |
| --- | --- |
| 1. Causal fleet-factor forecaster | Index forecaster chosen by rule R1 on 21 Nov 2026: PVSetFormer (V4a), 0.18001 vs LightGBM 0.18130 at 1 h on validation (D45, F44) |
| 2. DC/AC gain prior with shrinkage update | Planned (D02) |
| 3. Evaluation protocol: real starts, information set, error budget, sensor ablation; Safi external case | Events and drift boundary fixed (NB2, NB3); sensor and satellite index sources built (NB4, F35); sensor and satellite rows on the validation units (NB5d, F51): the fleet index is better up to 1 h and level from 2 h |

## 5. Evidence for each research question and hypothesis
_Empty._

## 6. Threats to validity
One campus; the donor tokens add nothing over the fleet summary on validation (F47); 13 scored events, 5 of
them drifted; low tilt diversity (0–15°); inverter files stop at 17:55 (F01);
telemetry start instead of grid connection (F06); metadata errors (D01).

## 7. Claims the paper must NOT make
- PVSetFormer as a general-purpose forecaster: describe it only for cold-start PV fleets (guide §6, D25).
- That PVSetFormer beats a model unless rules R1 and R2 show it at the primary horizon (D25).
- That PVSetFormer (or any trained forecaster) beats the zero-shot foundation models: on validation Chronos-2
  is level with all of them at 1 h (0.1776 vs V9 0.1785, LightGBM 0.1813, TimeXer 0.1784) and lower from 2 h,
  by 2–8% (F56).
- That PVSetFormer's 1-h lead over LightGBM on validation will hold at the test: part of it comes from two
  units whose first window LightGBM's setting cannot learn (F59); the test units have far more history.
- That PVSetFormer uses Chronos-2's forecast better than TimeXer or LightGBM, or that it improves on Chronos-2:
  with the same input the three are level (below 3%) at every horizon, and none is below Chronos-2 alone from
  30 min (D72, F60).
- That the foundation models beat the trained forecasters at 1 h: the differences are below 3% (F56); from 2 h
  several exceed it, on validation only so far.
- That PVSetFormer beats TimeXer: on validation the candidate V12 is level with TimeXer at 1 h (0.17782 vs
  0.17845, 4 of 10 units), and the three learned forecasters are level (F48).
- That PVSetFormer beats LightGBM at 1 h: on validation V12 is 1.9% below LightGBM's ensemble, on 6 of 10 units,
  Wilcoxon p = 0.77 (V9: 1.6%, p 0.56; V4a: 0.7%, p 1.0; F44). R1 selects the main model; it is not a result.
  Wait for the test run.
- That V12 improves on V9 beyond 30 min: its 1-h median is lower but 8 of 10 units are higher (D67).
- That censoring clearly improves the index: on validation it won on 4 of 10 units (F28); wait for ablation A2.
- That the nameplate prior is worth many days of data: w0 is below one day (F30).
- The PVSetFormer title if rule R1 keeps LightGBM as the main model: then use the fallback title (D25).
- Any comparison with RMSE values from other countries' papers (guide §6).
- Cross-climate transfer in general; only Safi is measured (guide §1). No tilt-transfer claim.
- Any difference below about 3% (guide §3.10).
- A significant Wilcoxon result in the drifted window (D10, F12).
- That the pyranometer was replaced or recalibrated in February 2023: the data show a step on 14–15 February,
  not its cause (F37).
- That the fleet beats the pyranometer at forecast horizons before the test run: on the validation units fleet
  LightGBM beats the sensor-index LightGBM up to 1 h and is level from 2 h (F51), development data only.
- That a satellite forecast would beat the fleet: A9n is an oracle (the CAMS index at the target time), not a
  forecast (F51).
- That monthly recalibration improves a stable sensor: on the validation units it does not (F35).
- That the forecaster beats CLIPER at 4–6 h: on the validation units it does not (F39); wait for the test run.
- Calibrated intervals on the test events before the test run: so far only the validation units show it
  (conformal 0.75–0.80, raw 0.63–0.71; F40, F43; PVSetFormer 0.79–0.83, F45).
- That PVSetFormer's donor tokens or set attention improve the forecast: with 5 seeds the summary-only model
  A6e equals V4a at every horizon on validation (0.17997 vs 0.18001 at 1 h; F47). Wait for the test run.
- That PVSetFormer learns more from additional history than LightGBM, or that its gap will change on the test
  units with longer histories: one origin and 10 units in a matched-history diagnostic (F53).
- Any validation number as a result of the paper: NB5a is development data (D33).
- "19 real start events" or "two capacity additions": there are 13 scored events and one addition (D08, D27).
- "Real start dates" for the four sensitivity events, whose starts are left-censored (D08, D27).
- "Healthy sensor" for 2021–2022 (D11).
- Any pilot number from the guide (`results_summary.md`).
- Any result on virtual Moroccan fleets (D07).
- That satellite data confirm the HKUST sensor drift, unless the CAMS all-sky check is actually run (D14).

## 8. What is still missing
Before the freeze:
- TabPFN-TS (A6c) waits for the author's licence (D65);
- PVSetFormer rounds toward the target of D68 (lowest of the five forecasters on validation; V13 met its rule, F58; V14 not kept, D71;
  V15 with the Chronos-2 input not kept, D70; its ablation done, D72, F60);
- PVSetFormer design rounds until the freeze (D50; candidate V12_5s since D67's result; V11a not kept; V13 met its
  rule but is above V12 at 1 h; V14 not kept, D71; V15 not kept, D70); at the freeze, R1 (`make_nb5c.py --final`) and PVSetFormer's conformal layer are rerun on the final
  candidate;
- freeze part 2 (2a LightGBM, 2b conformal, 2c R1, 2d foundation models) and the `protocol-freeze` tag.

Done on development data by 21 Nov 2026: NB0–NB4, NB5a and its conformal layer, R1 (NB5c, D45) and PVSetFormer's
conformal layer (D46), LightGBM's 5-seed conformal layer (D64), TimeXer and A6e (R2, F47, F48), the sensor and
satellite rows (NB5d, F51), A4c (D56), and the foundation models A6a and A6b (NB5b, D59, F56).
After the freeze: the test run (NB5) and everything from NB6 on.

## 9. Writing conventions
Roadmap Phase 10: clear academic English, short sentences, active verbs; research questions and hypotheses as one
paragraph; no internal codes in the text; limitations stated where they apply.

## 10. Where things are
See `CLAUDE.md`, "Repository map".
