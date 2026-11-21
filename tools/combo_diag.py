"""Diagnostic (development data): is there value in combining PVSetFormer with Chronos-2? (D70)

    python tools/combo_diag.py

Equal-weight quantile averages of forecasters already run on the validation units, scored on NB5a's slots with the
same composition and scorer as every row (`r1_score.score`). Members: PVSetFormer's candidate ensemble (V12_5s),
LightGBM's ensemble (LGB_seeds), TimeXer's (TX1_5s) and Chronos-2 (part-2d setting, results/nb5b_runs/). Each member
enters as its 5-seed mean (sorted), the combination is the mean of the members' quantiles, sorted again. Only keys
forecast by every member enter. No weight is fitted, so nothing is tuned on the scored slots; the result says whether
the forecasters carry complementary information, not which combination to use. Writes results/nb5c_diag/combo/.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import r1_score as R  # noqa: E402
from pvcold import audit as A  # noqa: E402

VD, OUT = ROOT / "results" / "nb5c_variants", ROOT / "results" / "nb5c_diag" / "combo"
KEYS = ["event", "origin", "h", "t"]
QC = R.QC


def member(name: str) -> pd.DataFrame:
    if name == "Chronos-2":
        s = json.loads((ROOT / "results" / "nb5b_fm" / "summary.json").read_text())["chosen"]["chronos2"]
        f = pd.read_parquet(ROOT / "results" / "nb5b_runs" / f"{s}.parquet")
    else:
        f = pd.read_parquet(VD / {"PVSetFormer": "V12_5s", "LightGBM": "LGB_seeds", "TimeXer": "TX1_5s"}[name] / "forecasts.parquet")
    f["origin"], f["t"] = pd.to_datetime(f["origin"]), pd.to_datetime(f["t"])
    m = f.groupby(KEYS)[QC].mean()
    m[QC] = np.sort(m[QC].to_numpy(), axis=1)
    return m


COMBOS = [("PVSetFormer",), ("Chronos-2",), ("LightGBM",), ("TimeXer",),
          ("PVSetFormer", "Chronos-2"), ("LightGBM", "Chronos-2"), ("TimeXer", "Chronos-2"),
          ("PVSetFormer", "LightGBM"), ("PVSetFormer", "LightGBM", "Chronos-2")]


def main():
    t0 = time.time()
    ctx = R.load_context()
    M = {n: member(n) for n in ("PVSetFormer", "Chronos-2", "LightGBM", "TimeXer")}
    common = M["PVSetFormer"].index
    for n in M:
        common = common.intersection(M[n].index)
    print({n: len(m) for n, m in M.items()}, "common keys", len(common), flush=True)
    rows = []
    for combo in COMBOS:
        q = np.mean([M[n].loc[common, QC].to_numpy() for n in combo], axis=0)
        fc = pd.DataFrame(np.sort(q, axis=1), columns=QC, index=common).reset_index()
        fc["seed"], fc["model"] = 1, "+".join(combo)
        sc = R.score(fc, ctx)                          # asserts every NB5a slot is forecast
        sc = sc[sc.seed == 1].assign(combo=" + ".join(combo))
        rows.append(sc)
        print(" + ".join(combo), sc.groupby("h").nRMSE.median().round(4).to_dict(), flush=True)
    SC = pd.concat(rows, ignore_index=True)
    MED = SC.groupby(["combo", "h"])[["nRMSE", "CRPS", "PICP80"]].median().reset_index()
    summary = {"tool": "combo_diag", "decision": "D70", "environment": A.versions(), "members": {
        "PVSetFormer": "V12_5s", "LightGBM": "LGB_seeds", "TimeXer": "TX1_5s",
        "Chronos-2": json.loads((ROOT / "results" / "nb5b_fm" / "summary.json").read_text())["chosen"]["chronos2"]},
        "common_keys": int(len(common)), "runtime_s": round(time.time() - t0, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    SC.to_csv(OUT / "scores.csv", index=False)
    MED.to_csv(OUT / "medians.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(MED.pivot_table(index="combo", columns="h", values="nRMSE").round(4).to_string())
    print("written to", OUT, f"| {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
