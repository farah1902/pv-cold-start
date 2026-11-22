"""Validation runs of rows A6e and A4c with V12's setting, before the freeze (D78; development data only).

    python tools/freeze_rows_val.py

- A6e_V12_5s (V12 on the fleet summary only, 5 R1 seeds) against V12_5s: the 5-seed ensembles (seed-0 rows), and
  each single seed against V12's run at the same seed (as F47 did with V4a).
- A4c_V12 (V12 plus the corrected sensor index, 1 seed) against V12_5s's run at the same seed (as D56 did with V4a).
- A6e's ensemble against LightGBM's 5-seed ensemble (LGB_seeds), as F47 reported.

Per horizon: median nRMSE and CRPS over the 10 validation units, ratio of medians, units where the row is lower,
two-sided exact Wilcoxon p on the paired unit scores; "level" when the medians differ by less than 3% (guide §3.10).
Every pair is checked to be scored on the same slots. Writes results/nb5c_rows_v12/ (table.csv, seeds.csv,
summary.json) all-or-nothing. Descriptive only: development is closed (D73), no design change follows.

Rule for the guide's row A6e (the author, D78, fixed and committed before A6e_V12_5s had finished): at 1 h, A6e's
5-seed ensemble against V12's (ratio of median nRMSE over the 10 units).
- Below 3% in either direction: the row keeps "adds nothing measurable" and cites the new finding.
- 3% or more worse: the row says the donor set adds information with V12, and a new finding records it.
- 3% or more lower: the row says that with V12 the fleet summary alone forecasts better than the donor set, and a new
  finding records it.
Exactly 3% counts as a named difference, as in guide §4.4 ("from 3%"). No outcome changes V12, the main model or any
frozen setting.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import audit as A  # noqa: E402

VD = ROOT / "results" / "nb5c_variants"
KEY = ["event", "h"]
HORIZONS = {1: "15 min", 2: "30 min", 4: "1 h", 8: "2 h", 16: "4 h", 24: "6 h"}
SEEDS = [20261119 + i for i in range(5)]   # C.SEED + 1 ... + 5, the R1 seeds (D37)
LEVEL = 3.0                                 # %, guide §3.10
RUNS = {"A6e": "A6e_V12_5s", "A4c": "A4c_V12", "main": "V12_5s", "LGB": "LGB_seeds"}
A6E_PAIR = "A6e_V12_5s vs V12_5s (5-seed ensembles)"


def a6e_rule(diff_pct: float) -> str:
    """D78's rule for row A6e at 1 h (see the module docstring); diff_pct = 100 (A6e / V12 - 1)."""
    if abs(diff_pct) < LEVEL:
        return "level: the row keeps 'adds nothing measurable' and cites the new finding"
    if diff_pct >= LEVEL:
        return "worse: the row says the donor set adds information with V12; a new finding records it"
    return ("lower: the row says that with V12 the fleet summary alone forecasts better than the donor set; "
            "a new finding records it; V12 stays main, no design change")


def scores(run: str, seed: int) -> pd.DataFrame:
    s = pd.read_csv(VD / run / "scores.csv")
    s = s[s.seed == seed].set_index(KEY).sort_index()
    assert len(s) == 10 * len(HORIZONS), (run, seed, len(s))
    return s


def compare(label: str, x: pd.DataFrame, y: pd.DataFrame) -> list[dict]:
    assert x.index.equals(y.index), label
    assert (x["n"] == y["n"]).all() and (x["n_keys"] == y["n_keys"]).all(), f"{label}: different slots"
    rows = []
    for h, name in HORIZONS.items():
        a, b = x.xs(h, level="h"), y.xs(h, level="h")
        d = (a["nRMSE"] - b["nRMSE"]).to_numpy()
        p = float(wilcoxon(d, alternative="two-sided", method="exact").pvalue) if np.any(d != 0) else np.nan
        diff = 100 * (a["nRMSE"].median() / b["nRMSE"].median() - 1)
        rows.append({"comparison": label, "h": h, "horizon": name,
                     "nRMSE_row": a["nRMSE"].median(), "nRMSE_ref": b["nRMSE"].median(), "diff_pct": diff,
                     "units_lower": int((d < 0).sum()), "n_units": len(d), "wilcoxon_p": p,
                     "max_abs_unit_diff_pct": float(100 * np.abs(a["nRMSE"] / b["nRMSE"] - 1).max()),
                     "CRPS_row": a["CRPS"].median(), "CRPS_ref": b["CRPS"].median(),
                     "CRPS_diff_pct": 100 * (a["CRPS"].median() / b["CRPS"].median() - 1),
                     "PICP80_row": a["PICP80"].median(), "PICP80_ref": b["PICP80"].median(),
                     "level": bool(abs(diff) < LEVEL)})
    return rows


def py(v):
    """numpy scalar -> plain Python, so summary.json keeps numbers and booleans (not their strings)."""
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    return v


def main():
    s6 = json.loads((VD / RUNS["A6e"] / "summary.json").read_text())
    s4 = json.loads((VD / RUNS["A4c"] / "summary.json").read_text())
    assert s6["seeds"] == 5 and s6["cfg"]["summary_only"] == 1 and s6["cfg"]["d"] == 64 and s6["cfg"]["vmed_n"] == 2
    assert s4["seeds"] == 1 and s4["cfg"]["ext"] == "sensor_corr" and s4["cfg"]["d"] == 64 and s4["cfg"]["vmed_n"] == 2
    rows = compare(A6E_PAIR, scores(RUNS["A6e"], 0), scores(RUNS["main"], 0))
    rows += compare("A4c_V12 vs V12_5s (seed 20261119)", scores(RUNS["A4c"], SEEDS[0]), scores(RUNS["main"], SEEDS[0]))
    rows += compare("A6e_V12_5s vs LGB_seeds (5-seed ensembles)", scores(RUNS["A6e"], 0), scores(RUNS["LGB"], 0))
    T = pd.DataFrame(rows)

    seed_rows = []                       # single seeds at every horizon, paired by seed
    for sd in SEEDS:
        for r in compare(f"seed {sd}", scores(RUNS["A6e"], sd), scores(RUNS["main"], sd)):
            seed_rows.append({"seed": sd, **{k: r[k] for k in ("h", "horizon", "nRMSE_row", "nRMSE_ref", "diff_pct",
                                                                  "units_lower")}})
    S = pd.DataFrame(seed_rows)
    s1 = S[S.h == 4]

    head = T[T.h == 4].set_index("comparison")
    d1 = float(head.loc[A6E_PAIR, "diff_pct"])
    summary = {"tool": "freeze_rows_val", "decision": "D78", "environment": A.versions(),
               "a6e_rule": {"diff_pct_1h": d1, "outcome": a6e_rule(d1)},
               "runs": {k: {"run": v, "summary_sha256": hashlib.sha256((VD / v / "summary.json").read_bytes()).hexdigest()}
                        for k, v in RUNS.items()},
               "n_params": {"A6e": s6["n_params"], "A4c": s4["n_params"]},
               "runtime_min": {"A6e": round(s6["runtime_s"] / 60), "A4c": round(s4["runtime_s"] / 60)},
               "at_1h": {c: {k: py(head.loc[c, k]) for k in ["nRMSE_row", "nRMSE_ref", "diff_pct", "units_lower",
                                                             "wilcoxon_p", "level"]} for c in head.index},
               "single_seeds_1h": {"A6e": [float(v) for v in s1.nRMSE_row], "V12": [float(v) for v in s1.nRMSE_ref],
                                   "diff": [float(a - b) for a, b in zip(s1.nRMSE_row, s1.nRMSE_ref)]},
               "level_at_every_horizon": {c: bool(T[T.comparison == c].level.all()) for c in T.comparison.unique()}}
    out = A.write_outputs("nb5c_rows_v12", {"table": T, "seeds": S}, summary)
    pd.set_option("display.width", 200)
    print(T[["comparison", "horizon", "nRMSE_row", "nRMSE_ref", "diff_pct", "units_lower", "wilcoxon_p",
             "max_abs_unit_diff_pct", "CRPS_diff_pct", "level"]].round(5).to_string(index=False))
    print(S.pivot(index="seed", columns="horizon", values="diff_pct").round(2).to_string())
    print(f"row A6e (D78 rule): {d1:+.2f}% at 1 h -> {a6e_rule(d1)}")
    print("written to", out)


if __name__ == "__main__":
    main()
