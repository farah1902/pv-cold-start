"""Ablation of the Chronos-2 input (D70, D72) on the validation units (development data only).

    python tools/fm_ablation.py [--pvsf V15_5s --base V12_5s --tx TX2_5s --txbase TX1_5s
                                 --lgb LGB_fm_seeds --lgbbase LGB_seeds]

Reads the 5-seed ensembles (seed 0 rows of results/nb5c_variants/<run>/scores.csv) of the three trained forecasters
with and without Chronos-2's forecast as input, and Chronos-2 and TimesFM 2.5 at their part-2d settings
(results/nb5b_fm/, D59). Asserts that every run is scored on the same slots. Per horizon it reports:

- each forecaster's gain from the input (its run with the input against its base: ratio of median nRMSE over units,
  units lower, Wilcoxon p);
- V15's rule (D70, fixed before its run): V15 replaces the candidate if its median nRMSE is lower at 1 h and no more
  than 1% higher at any other horizon;
- D72's rule (fixed before any run with the input): PVSetFormer "uses the input better" at a horizon only if V15 is
  lower than both TimeXer and LightGBM with the input; it "improves on Chronos-2" only where V15 is lower than
  Chronos-2 alone; a difference below 3% is called level (guide §3.10);
- the same comparisons without SQ567 and UG Hall2 2F, the two units whose first window LightGBM's setting cannot
  learn (F59), as the caveat D72 asks for.

Writes results/nb5c_diag/fm_ablation/{table.csv, rules.json} together, or neither.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
VD, FM = ROOT / "results" / "nb5c_variants", ROOT / "results" / "nb5b_fm"
OUT = ROOT / "results" / "nb5c_diag" / "fm_ablation"
KEY = ["event", "h"]
H1 = 4                       # 1 h, the primary horizon
F59_UNITS = ("SQ567", "UG Hall2 2F")
LEVEL = 3.0                  # %, guide §3.10


def ens(name):
    s = pd.read_csv(VD / name / "scores.csv")
    return s[s.seed == 0].set_index(KEY).sort_index()


def fm_model(label):
    chosen = json.loads((FM / "summary.json").read_text())["chosen"]
    f = pd.read_csv(FM / "scores.csv")
    return f[f.setting == chosen[label]].set_index(KEY).sort_index()


def pair(x, y):
    """x against y on the same units: ratio of medians (%), units where x is lower, Wilcoxon p."""
    d = (x - y).to_numpy()
    p = float(wilcoxon(d).pvalue) if np.any(d != 0) else np.nan
    return 100 * (x.median() / y.median() - 1), int((d < 0).sum()), p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pvsf", default="V15_5s")
    ap.add_argument("--base", default="V12_5s")
    ap.add_argument("--tx", default="TX2_5s")
    ap.add_argument("--txbase", default="TX1_5s")
    ap.add_argument("--lgb", default="LGB_fm_seeds")
    ap.add_argument("--lgbbase", default="LGB_seeds")
    ap.add_argument("--out", default=str(OUT), help="output folder (a dry run with stand-in rounds writes elsewhere)")
    a = ap.parse_args()
    out = Path(a.out)

    runs = {"PVSetFormer": (a.pvsf, a.base), "TimeXer": (a.tx, a.txbase), "LightGBM": (a.lgb, a.lgbbase)}
    S = {}
    for lab, (w, wo) in runs.items():
        S[f"{lab} + Chronos-2"], S[lab] = ens(w), ens(wo)
    S["Chronos-2"], S["TimesFM 2.5"] = fm_model("chronos2"), fm_model("timesfm25")
    ref = S["PVSetFormer + Chronos-2"]
    for k, v in S.items():
        assert v.index.equals(ref.index), f"{k}: not the same (unit, horizon) rows"
        assert (v["n"] == ref["n"]).all(), f"{k}: not the same slots"
    hs = sorted(ref.index.get_level_values("h").unique())
    units = sorted(ref.index.get_level_values("event").unique())
    assert len(units) == 10 and set(F59_UNITS) <= set(units)

    rows = []
    for subset, keep in (("10 units", units), ("without SQ567, UG Hall2 2F", [u for u in units if u not in F59_UNITS])):
        for h in hs:
            X = {k: v.xs(h, level="h").loc[keep, "nRMSE"] for k, v in S.items()}
            row = {"units": subset, "h": h}
            for k, x in X.items():
                row[f"{k} nRMSE"] = x.median()
            for lab in runs:                                      # each forecaster's gain from the input
                r, n, p = pair(X[f"{lab} + Chronos-2"], X[lab])
                row.update({f"{lab} gain %": r, f"{lab} gain units": n, f"{lab} gain p": p})
            v = X["PVSetFormer + Chronos-2"]
            for k in ["PVSetFormer", "TimeXer + Chronos-2", "LightGBM + Chronos-2", "Chronos-2", "TimesFM 2.5",
                      "TimeXer", "LightGBM"]:
                r, n, p = pair(v, X[k])
                row.update({f"V15 vs {k} %": r, f"V15 vs {k} units": n, f"V15 vs {k} p": p})
            row["uses input better"] = bool(v.median() < X["TimeXer + Chronos-2"].median()
                                            and v.median() < X["LightGBM + Chronos-2"].median())
            row["improves on Chronos-2"] = bool(v.median() < X["Chronos-2"].median())
            row["lowest of all"] = bool(v.median() < min(x.median() for k, x in X.items()
                                                         if k != "PVSetFormer + Chronos-2"))
            row["level with TX, LGB (+Chronos-2) and Chronos-2"] = bool(
                all(abs(row[f"V15 vs {k} %"]) < LEVEL for k in ["TimeXer + Chronos-2", "LightGBM + Chronos-2",
                                                                "Chronos-2"]))
            rows.append(row)
    T = pd.DataFrame(rows)

    t10 = T[T.units == "10 units"].set_index("h")
    g = t10["PVSetFormer gain %"]
    v15_rule = bool(g[H1] < 0 and all(g[h] <= 1.0 for h in hs if h != H1))
    rules = {
        "runs": runs,
        "V15 rule (D70): replaces the candidate": v15_rule,
        "V15 vs candidate %": {int(h): float(g[h]) for h in hs},
        "D72 uses the input better, by h (10 units)": {int(h): bool(t10.loc[h, "uses input better"]) for h in hs},
        "D72 improves on Chronos-2, by h (10 units)": {int(h): bool(t10.loc[h, "improves on Chronos-2"]) for h in hs},
        "D72 level (< 3%) with TX + C2, LGB + C2 and Chronos-2, by h": {
            int(h): bool(t10.loc[h, "level with TX, LGB (+Chronos-2) and Chronos-2"]) for h in hs},
        "lowest of all seven rows, by h (10 units)": {int(h): bool(t10.loc[h, "lowest of all"]) for h in hs},
    }

    out.mkdir(parents=True, exist_ok=True)
    tmp_t, tmp_r = out / "table.csv.tmp", out / "rules.json.tmp"
    T.to_csv(tmp_t, index=False, lineterminator="\n")
    tmp_r.write_text(json.dumps(rules, indent=1), encoding="utf-8")
    tmp_t.replace(out / "table.csv")
    tmp_r.replace(out / "rules.json")

    pd.set_option("display.width", 250)
    for subset in T.units.unique():
        t = T[T.units == subset].set_index("h")
        print(f"\n== median nRMSE, {subset}")
        print(t[[c for c in t.columns if c.endswith(" nRMSE")]].round(5).to_string())
        print(f"-- gain from the input (with / without, %; units lower of {10 if subset == '10 units' else 8})")
        print(t[[f"{lab} gain {s}" for lab in runs for s in ("%", "units")]].round(2).to_string())
        print("-- V15 against (%)")
        print(t[[c for c in t.columns if c.startswith("V15 vs") and c.endswith("%")]].round(2).to_string())
        print(t[["uses input better", "improves on Chronos-2", "lowest of all",
                 "level with TX, LGB (+Chronos-2) and Chronos-2"]].to_string())
    print("\nrules:", json.dumps(rules, indent=1))
    print("written to", out)


if __name__ == "__main__":
    main()
