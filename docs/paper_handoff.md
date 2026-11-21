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
| 3. Evaluation protocol: real starts, information set, error budget, sensor ablation; Safi external case | Events and drift boundary fixed (NB2, NB3); sensor and satellite index sources built, same-time evidence only (NB4, F35) |

## 5. Evidence for each research question and hypothesis
_Empty._

## 6. Threats to validity
One campus; the donor tokens add nothing over the fleet summary on validation (F47); 13 scored events, 5 of
them drifted; low tilt diversity (0–15°); inverter files stop at 17:55 (F01);
telemetry start instead of grid connection (F06); metadata errors (D01).

## 7. Claims the paper must NOT make
- PVSetFormer as a general-purpose forecaster: describe it only for cold-start PV fleets (guide §6, D25).
- That PVSetFormer beats a model unless rules R1 and R2 show it at the primary horizon (D25).
- That PVSetFormer beats LightGBM at 1 h: on validation it passes R1 by 0.7%, on 4 of 10 units, Wilcoxon
  p = 1.0 (F44). R1 selects the main model; it is not a result. Wait for the test run.
- That censoring clearly improves the index: on validation it won on 4 of 10 units (F28); wait for ablation A2.
- That the nameplate prior is worth many days of data: w0 is below one day (F30).
- The PVSetFormer title if rule R1 keeps LightGBM as the main model: then use the fallback title (D25).
- Any comparison with RMSE values from other countries' papers (guide §6).
- Cross-climate transfer in general; only Safi is measured (guide §1). No tilt-transfer claim.
- Any difference below about 3% (guide §3.10).
- A significant Wilcoxon result in the drifted window (D10, F12).
- That the pyranometer was replaced or recalibrated in February 2023: the data show a step on 14–15 February,
  not its cause (F37).
- That the fleet beats the pyranometer at forecast horizons before NB6: so far the evidence is same-time, on
  the validation units (F35).
- That monthly recalibration improves a stable sensor: on the validation units it does not (F35).
- That the forecaster beats CLIPER at 4–6 h: on the validation units it does not (F39); wait for the test run.
- Calibrated intervals on the test events before the test run: so far only the validation units show it
  (conformal 0.75–0.80, raw 0.63–0.71; F40, F43; PVSetFormer 0.79–0.83, F45).
- That PVSetFormer's donor tokens or set attention improve the forecast: with 5 seeds the summary-only model
  A6e equals V4a at every horizon on validation (0.17997 vs 0.18001 at 1 h; F47). Wait for the test run.
- Any validation number as a result of the paper: NB5a is development data (D33).
- "19 real start events" or "two capacity additions": there are 13 scored events and one addition (D08, D27).
- "Real start dates" for the four sensitivity events, whose starts are left-censored (D08, D27).
- "Healthy sensor" for 2021–2022 (D11).
- Any pilot number from the guide (`results_summary.md`).
- Any result on virtual Moroccan fleets (D07).
- That satellite data confirm the HKUST sensor drift, unless the CAMS all-sky check is actually run (D14).

## 8. What is still missing
Before the freeze: the sensor and satellite rows' learner inputs, TimeXer and the ablation A6e (NB5c;
PVSetFormer was chosen by R1 on 21 Nov, D45; its conformal layer is kept, D46), the foundation models (NB5b), freeze part 2 and the tag. After it: the test run (NB5) and
everything from NB6 on. NB0–NB4, NB5a and the conformal layer done by 20 Nov 2026.

## 9. Writing conventions
Roadmap Phase 10: clear academic English, short sentences, active verbs; research questions and hypotheses as one
paragraph; no internal codes in the text; limitations stated where they apply.

## 10. Where things are
See `CLAUDE.md`, "Repository map".
