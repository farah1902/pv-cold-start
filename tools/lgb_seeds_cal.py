"""Calibration predictions of LightGBM's 5-seed ensemble, for its conformal layer at the test (D64). Development data only.

Usage:  python tools/lgb_seeds_cal.py [--jobs 8] [--limit N]

The author decided on 21 Nov 2026 that LightGBM enters the test as its 5-seed ensemble (LGB_seeds, D37). Its conformal
layer (D35) must then be built from that ensemble's calibration set, which tools/r1_lgb_seeds.py did not save. This
tool refits the same bank (part-2a setting, D34) with the same seeds through forecast.cal_task, the code path of
NB5a_conformal, which returns both the forecasts and the early-stopped models' predictions on the last 20% of the
training pairs. The forecasts must equal LGB_seeds' rows exactly, seed by seed (asserted), so the calibration set
belongs to the forecasts that were scored. --limit N runs only the first N (unit, origin, seed) tasks and writes
nothing (a smoke test). Writes results/nb5c_variants/LGB_seeds_cal/ (calibration.parquet, tasks.csv, summary.json;
all-or-nothing); the conformal notebook is tools/make_nb5c_conformal.py --model lgb.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r1_score as R  # noqa: E402  (sets sys.path, PYTHONPATH and LOKY_MAX_CPU_COUNT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import forecast as FC  # noqa: E402

KEY = ["event", "origin", "seed", "h", "t"]


def task(name, S, origin, end, params, seed):
    t0 = time.time()
    _, _, rows, cal = FC.cal_task(name, S, origin, end, {**params, "seed": int(seed)})
    for f in (rows, cal):
        if len(f):                                       # cal_task adds event and origin only to non-empty frames
            f.insert(2, "seed", int(seed))
            if "model" not in f:
                f.insert(3, "model", "LGB")
    return rows, cal, {"event": name, "origin": origin, "seed": int(seed), "n_fc": len(rows), "n_cal": len(cal),
                       "runtime_s": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    t0 = time.time()
    ctx = R.load_context()
    VDIR = C.RESULTS / "nb5c_variants" / "LGB_seeds"
    ls_bytes = (VDIR / "summary.json").read_bytes()
    ls = json.loads(ls_bytes)
    cfg_sha = hashlib.sha256((C.RESULTS / "nb5a_dev" / "lgb_config_part2a.yaml").read_bytes()).hexdigest()
    assert cfg_sha == ctx["nb5"]["lgb_config_sha256"] == ls["lgb_config_sha256"], "configuration part 2a changed"
    params = dict(ctx["nb5"]["lgb_params"])
    assert params == ls["params"], "LGB_seeds was run with another setting"
    seeds = ls["seeds"]
    series = {v: FC.event_series(v, ctx["idx"], ctx["geo15"]) for v in ctx["VAL"]}
    T = R.tasks(ctx, seeds)
    if args.limit:
        T = T[:args.limit]
    print(f"LGB_seeds_cal: {len(T)} bank fits, seeds {seeds}", flush=True)
    res = Parallel(n_jobs=args.jobs, verbose=5)(delayed(task)(v, series[v], o, e, params, sd) for v, o, e, sd in T)
    fc = pd.concat([r[0] for r in res], ignore_index=True)
    cal = pd.concat([r[1] for r in res], ignore_index=True)
    meta = pd.DataFrame([r[2] for r in res])

    old = pd.read_parquet(VDIR / "forecasts.parquet")
    old = old[old.seed != 0]
    old["origin"], fc["origin"] = pd.to_datetime(old["origin"]), pd.to_datetime(fc["origin"])
    if args.limit:
        old = old.merge(fc[["event", "origin", "seed"]].drop_duplicates(), on=["event", "origin", "seed"])
    m = old.merge(fc, on=KEY, suffixes=("_o", "_n"), how="outer", indicator=True)
    both = m["_merge"] == "both"
    diff = float(np.abs(m.loc[both, [c + "_o" for c in R.QC]].to_numpy()
                        - m.loc[both, [c + "_n" for c in R.QC]].to_numpy()).max())
    print(f"forecast rows: LGB_seeds {len(old)}, refit {len(fc)}, matched {int(both.sum())}, max |diff| {diff:.2e} | "
          f"calibration rows {len(cal)}", flush=True)
    assert both.all() and len(old) == len(fc) and diff < 1e-6, "the refit does not reproduce LGB_seeds"
    assert sorted(cal.seed.unique().tolist()) == sorted({sd for *_, sd in T}), "calibration seeds differ"
    if args.limit:
        print(f"smoke test passed ({len(T)} tasks, {time.time() - t0:.0f} s); nothing written")
        return
    n = cal.groupby(["event", "origin", "h", "t"])["seed"].nunique()
    summary = {"name": "LGB_seeds_cal", "decision": "D64", "params": params, "lgb_config_sha256": cfg_sha,
               "seeds": seeds, "lgb_seeds_summary_sha256": hashlib.sha256(ls_bytes).hexdigest(),
               "forecasts_matched": int(both.sum()), "forecasts_max_abs_diff": diff, "calibration_rows": len(cal),
               "calibration_keys_with_all_seeds": int((n == len(seeds)).sum()), "calibration_keys": len(n),
               "runtime_s": round(time.time() - t0, 1), "environment": A_.versions()}
    A_.write_outputs("nb5c_variants/LGB_seeds_cal", {"tasks": meta}, summary, parquet={"calibration": cal})
    tmp_parent = C.RESULTS / ".tmp_nb5c_variants"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    print(json.dumps({k: summary[k] for k in ["forecasts_matched", "forecasts_max_abs_diff", "calibration_rows",
                                              "calibration_keys_with_all_seeds", "calibration_keys", "runtime_s"]}))


if __name__ == "__main__":
    main()
