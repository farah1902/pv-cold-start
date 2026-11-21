"""Scoreboard of PVSetFormer rounds against the four other forecasters on the validation units (D68; development data).

    python tools/pvsf_vs_all.py V9_5s [V12_5s ...]

For each round (its 5-seed ensemble, seed 0 rows of results/nb5c_variants/<round>/scores.csv) and each horizon: the
median nRMSE and CRPS over the 10 units, and against LightGBM's ensemble (LGB_seeds), TimeXer's (TX1_5s), Chronos-2 and
TimesFM 2.5 (the part-2d settings chosen in results/nb5b_fm/, D59): the ratio of the medians, the units where the round
is lower, and the Wilcoxon p on the paired unit scores. Asserts that every pair is scored on the same slots. Writes
results/nb5c_diag/vs_all/<round>.csv and prints, per horizon, whether the round is the lowest of the five.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
VD, FM = ROOT / "results" / "nb5c_variants", ROOT / "results" / "nb5b_fm"
OUT = ROOT / "results" / "nb5c_diag" / "vs_all"
KEY = ["event", "h"]


def ens(name: str) -> pd.DataFrame:
    s = pd.read_csv(VD / name / "scores.csv")
    return s[s.seed == 0].set_index(KEY)


def others() -> dict:
    chosen = json.loads((FM / "summary.json").read_text())["chosen"]
    fm = pd.read_csv(FM / "scores.csv")
    ref = {"LightGBM": ens("LGB_seeds"), "TimeXer": ens("TX1_5s")}
    for label, model in (("Chronos-2", "chronos2"), ("TimesFM 2.5", "timesfm25")):
        ref[label] = fm[fm.setting == chosen[model]].set_index(KEY)
    return ref


def board(name: str, ref: dict) -> pd.DataFrame:
    a = ens(name)
    rows = []
    for h in sorted(a.index.get_level_values("h").unique()):
        x = a.xs(h, level="h")
        row = {"round": name, "h": h, "nRMSE": x.nRMSE.median(), "CRPS": x.CRPS.median()}
        lows = []
        for n, r in ref.items():
            y = r.xs(h, level="h").reindex(x.index)
            assert (y["n"] == x["n"]).all(), f"{name} and {n}: not the same slots at h={h}"
            d = (x.nRMSE - y.nRMSE).to_numpy()
            row[f"{n} nRMSE"] = y.nRMSE.median()
            row[f"vs {n} %"] = 100 * (x.nRMSE.median() / y.nRMSE.median() - 1)
            row[f"{n} units"] = int((d < 0).sum())
            row[f"{n} p"] = float(wilcoxon(d).pvalue) if np.any(d != 0) else np.nan
            lows.append(y.nRMSE.median())
        row["lowest of five"] = bool(x.nRMSE.median() < min(lows))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    names = sys.argv[1:] or ["V9_5s"]
    ref = others()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        b = board(name, ref)
        b.to_csv(OUT / f"{name}.csv", index=False)
        show = b[["h", "nRMSE"] + [f"vs {n} %" for n in ref] + [f"{n} units" for n in ref] + ["lowest of five"]]
        print(f"\n== {name}: median nRMSE and change against each forecaster (ratio of medians); units lower of 10")
        print(show.round(3).to_string(index=False))
    print("written to", OUT)


if __name__ == "__main__":
    main()
