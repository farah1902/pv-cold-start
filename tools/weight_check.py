"""Secondary analysis (D73, D75): per-horizon weighting of each trained forecaster with Chronos-2. Frozen part 2e.

    python tools/weight_check.py            # validation units: choose the weights, write results/nb5c_weights/

Rule, fixed by the author before the freeze (D73) and written here before any blend beyond the 50/50 one was scored:
- pairs: PVSetFormer (V12_5s, the main forecaster of part 2c), TimeXer (TX1_5s) and LightGBM (LGB_seeds), each with
  Chronos-2 at its part-2d setting; every member enters as its 5-seed mean (sorted), as in F57 (`combo_diag.py`);
- blend, quantile by quantile: (1 - w_h) * trained + w_h * Chronos-2, sorted again, with one weight per horizon on the
  grid 0, 0.1, ..., 1 (w = 0: the trained forecaster alone; w = 1: Chronos-2 alone);
- w_h is chosen on the 10 validation units only, by the lowest median nRMSE over the units (the measure of every
  rule in this project); a tie goes to the weight nearest 0.5. The same procedure for the three pairs;
- the 50/50 average (w = 0.5) is reported beside it as a fixed reference;
- raw quantiles (no conformal layer), scored with the NB5a scorer on NB5a's slots (`r1_score.score`);
- at the test the frozen weights are applied unchanged (`blend`); the result goes to the Discussion, never as the
  main model. On validation the chosen weights are scored on the units that chose them (in sample).

Checks: w = 0 reproduces each member alone and w = 0.5 the equal averages of F57 (results/nb5c_diag/combo/), and
w = 1 gives the same Chronos-2 scores in the three pairs.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import combo_diag as CD  # noqa: E402
import r1_score as R  # noqa: E402
from pvcold import audit as A  # noqa: E402

QC = R.QC
GRID = [round(0.1 * i, 1) for i in range(11)]
PAIRS = {"PVSetFormer": "V12_5s", "TimeXer": "TX1_5s", "LightGBM": "LGB_seeds"}
VD = ROOT / "results" / "nb5c_variants"


def blend(trained: np.ndarray, c2: np.ndarray, w: float) -> np.ndarray:
    """Quantile-by-quantile blend (1 - w) * trained + w * Chronos-2, sorted again. Used unchanged at the test."""
    return np.sort((1.0 - w) * np.asarray(trained, dtype=float) + w * np.asarray(c2, dtype=float), axis=1)


def choose(med: pd.Series) -> float:
    """Lowest median nRMSE over units on the grid; a tie goes to the weight nearest 0.5."""
    best = med.min()
    ties = [w for w, v in med.items() if v <= best + 1e-12]
    return min(ties, key=lambda w: (abs(w - 0.5), w))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    t0 = time.time()
    r1 = json.loads((ROOT / "results" / "nb5c_r1" / "summary.json").read_text())
    assert r1["final_variant"] == PAIRS["PVSetFormer"] and r1["pvsf_main"], "part 2c does not name V12_5s"
    ctx = R.load_context()
    M = {n: CD.member(n) for n in ("PVSetFormer", "Chronos-2", "LightGBM", "TimeXer")}
    common = M["PVSetFormer"].index
    for n in M:
        common = common.intersection(M[n].index)
    print({n: len(m) for n, m in M.items()}, "common keys", len(common), flush=True)
    C2 = M["Chronos-2"].loc[common, QC].to_numpy()
    rows = []
    for pair in PAIRS:
        T = M[pair].loc[common, QC].to_numpy()
        parts = []
        for i, w in enumerate(GRID, start=1):
            fc = pd.DataFrame(blend(T, C2, w), columns=QC, index=common).reset_index()
            fc["seed"], fc["model"] = i, pair
            parts.append(fc)
        sc = R.score(pd.concat(parts, ignore_index=True), ctx)
        sc = sc[sc.seed > 0].copy()
        sc["w"] = sc.seed.map(lambda s: GRID[s - 1])
        sc["pair"] = pair
        rows.append(sc.drop(columns="seed"))
        print(pair, "scored", f"{time.time() - t0:.0f} s", flush=True)
    SC = pd.concat(rows, ignore_index=True)
    MED = SC.groupby(["pair", "w", "h"])[["nRMSE", "CRPS", "PICP80"]].median().reset_index()

    # checks against F57's equal averages and the members alone
    combo = pd.read_csv(ROOT / "results" / "nb5c_diag" / "combo" / "medians.csv").pivot(index="h", columns="combo",
                                                                                         values="nRMSE")
    for pair in PAIRS:
        m = MED[MED.pair == pair].pivot(index="h", columns="w", values="nRMSE")
        assert np.allclose(m[0.0], combo[pair].loc[m.index], rtol=0, atol=1e-12), f"{pair}: w = 0 differs from F57"
        assert np.allclose(m[0.5], combo[f"{pair} + Chronos-2"].loc[m.index], rtol=0, atol=1e-9), f"{pair}: 50/50"
        assert np.allclose(m[1.0], combo["Chronos-2"].loc[m.index], rtol=0, atol=1e-12), f"{pair}: w = 1"
    print("checks passed: w = 0, 0.5 and 1 reproduce F57's members, equal averages and Chronos-2", flush=True)

    chosen, wts = [], {}
    for pair in PAIRS:
        m = MED[MED.pair == pair].pivot(index="h", columns="w", values="nRMSE")
        wts[pair] = {}
        for h in m.index:
            w = choose(m.loc[h])
            wts[pair][int(h)] = float(w)
            chosen.append({"pair": pair, "h": int(h), "w": w, "nRMSE_chosen": m.loc[h, w], "nRMSE_5050": m.loc[h, 0.5],
                           "nRMSE_trained": m.loc[h, 0.0], "nRMSE_chronos2": m.loc[h, 1.0]})
    CH = pd.DataFrame(chosen)
    fm_cfg = ROOT / "results" / "nb5b_fm" / "fm_config_part2d.yaml"
    part2e = {"part": "2e", "decision": "D75 (rule: D73)",
              "rule": "per horizon, weight w on Chronos-2 from the grid 0, 0.1, ..., 1; blend (1 - w) * trained + w * "
                      "Chronos-2, quantile by quantile, sorted again; w chosen on the 10 validation units by the lowest "
                      "median nRMSE over units, a tie to the weight nearest 0.5; the same procedure for the three pairs; "
                      "the 50/50 average reported as a fixed reference; raw quantiles; secondary analysis (Discussion)",
              "grid": GRID, "reference_weight": 0.5, "members": dict(PAIRS, **{"Chronos-2": "part 2d chronos2"}),
              "part2c_sha256": r1["part2c_sha256"], "part2d_sha256": sha(fm_cfg),
              "members_summary_sha256": {n: sha(VD / v / "summary.json") for n, v in PAIRS.items()},
              "weights": wts}
    P2E_TEXT = yaml.safe_dump(part2e, sort_keys=True)
    P2E_HASH = hashlib.sha256(P2E_TEXT.encode()).hexdigest()
    summary = {"tool": "weight_check", "decision": "D75", "environment": A.versions(), "common_keys": int(len(common)),
               "weights": wts, "part2e_sha256": P2E_HASH, "runtime_s": round(time.time() - t0, 1)}
    out = A.write_outputs("nb5c_weights", {"scores": SC, "medians": MED, "chosen": CH}, summary,
                          texts={"weight_config_part2e.yaml": P2E_TEXT})
    pd.set_option("display.width", 200)
    print(CH.round(5).to_string(index=False))
    print(MED.pivot_table(index=["pair", "w"], columns="h", values="nRMSE").round(5).to_string())
    print("part 2e sha256:", P2E_HASH)
    print("written to", out, f"| {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
