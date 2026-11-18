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
| 1. Causal fleet-factor forecaster | Planned |
| 2. DC/AC gain prior with shrinkage update | Planned (D02) |
| 3. Evaluation protocol: real starts, information set, error budget, sensor ablation; Safi external case | Planned |

## 5. Evidence for each research question and hypothesis
_Empty._

## 6. Threats to validity
One campus; 13 scored events, 5 of them drifted; low tilt diversity (0–15°); inverter files stop at 17:55 (F01);
telemetry start instead of grid connection (F06); metadata errors (D01).

## 7. Claims the paper must NOT make
- PVSetFormer as a general-purpose forecaster: describe it only for cold-start PV fleets (guide §6, D25).
- That PVSetFormer beats a model unless rules R1 and R2 show it at the primary horizon (D25).
- The PVSetFormer title if rule R1 keeps LightGBM as the main model: then use the fallback title (D25).
- Any comparison with RMSE values from other countries' papers (guide §6).
- Cross-climate transfer in general; only Safi is measured (guide §1). No tilt-transfer claim.
- Any difference below about 3% (guide §3.10).
- A significant Wilcoxon result in the drifted window (D10, F12).
- "19 real start events" or "two capacity additions": there are 13 scored events and one addition (D08, D27).
- "Real start dates" for the four sensitivity events, whose starts are left-censored (D08, D27).
- "Healthy sensor" for 2021–2022 (D11).
- Any pilot number from the guide (`results_summary.md`).
- Any result on virtual Moroccan fleets (D07).
- That satellite data confirm the HKUST sensor drift, unless the CAMS all-sky check is actually run (D14).

## 8. What is still missing
Everything from NB3 on (NB0–NB2 done on 18 Nov 2026).

## 9. Writing conventions
Roadmap Phase 10: clear academic English, short sentences, active verbs; research questions and hypotheses as one
paragraph; no internal codes in the text; limitations stated where they apply.

## 10. Where things are
See `CLAUDE.md`, "Repository map".
