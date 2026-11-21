"""LightGBM's 5-seed ensemble on the validation units: the R1 bar chosen by the author (D37). Development data only.

Usage:  python tools/r1_lgb_seeds.py [--seeds 5] [--check]

NB5a's LightGBM bank (change target, D34; setting of lgb_config_part2a.yaml) refitted with the bagging and
feature-fraction seeds C.SEED + 1 ... C.SEED + n (the seeds PVSetFormer uses), scored like PVSetFormer by
tools/r1_score.py: per seed, and the seed ensemble (mean of the sorted quantiles). --check first refits one task with
NB5a's seed C.SEED and stops unless it reproduces NB5a's forecasts. Writes results/nb5c_variants/LGB_seeds/.
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
import yaml  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import forecast as FC  # noqa: E402


def task(name, S, origin, end, params, seed):
    t0 = time.time()
    rows, diag = FC.run_origin(S, origin, end, {**params, "seed": int(seed)}, models=("LGB",))
    rows.insert(0, "seed", int(seed)); rows.insert(0, "origin", origin); rows.insert(0, "event", name)
    best = [np.mean(d["best_iter"]) for d in diag.values() if "best_iter" in d]
    return rows, {"event": name, "origin": origin, "seed": int(seed), "mean_best_iter": float(np.mean(best)),
                  "runtime_s": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    t0 = time.time()
    ctx = R.load_context()
    cfg_path = C.RESULTS / "nb5a_dev" / "lgb_config_part2a.yaml"
    params = dict(ctx["nb5"]["lgb_params"])
    cfg_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    assert cfg_sha == ctx["nb5"]["lgb_config_sha256"], "lgb_config_part2a.yaml changed since NB5a"
    series = {v: FC.event_series(v, ctx["idx"], ctx["geo15"]) for v in ctx["VAL"]}

    if args.check:                                        # NB5a's seed must give NB5a's forecasts
        v, o, e, _ = R.tasks(ctx, [C.SEED])[0]
        rows, _ = task(v, series[v], o, e, params, C.SEED)
        f5 = ctx["fc5"].query("model == 'LGB'")
        f5 = f5[(f5.event == v) & (pd.to_datetime(f5.origin) == o)]
        m = f5.merge(rows, on=["event", "h", "t"], suffixes=("_o", "_n"))
        diff = float(np.nanmax(np.abs(m[[c + "_o" for c in R.QC]].to_numpy() - m[[c + "_n" for c in R.QC]].to_numpy())))
        print(f"check {v} {o.date()}: rows NB5a {len(f5)}, new {len(rows)}, matched {len(m)}, max |diff| {diff:.2e}", flush=True)
        assert len(m) == len(f5) == len(rows) and diff < 1e-6, "seed C.SEED does not reproduce NB5a"

    seeds = [C.SEED + i for i in range(1, args.seeds + 1)]
    T = R.tasks(ctx, seeds)
    print(f"LGB_seeds: {len(T)} bank fits, params {params}, seeds {seeds}", flush=True)
    res = Parallel(n_jobs=args.jobs, verbose=5)(delayed(task)(v, series[v], o, e, params, sd) for v, o, e, sd in T)
    fc = pd.concat([r[0] for r in res], ignore_index=True)
    meta = pd.DataFrame([r[1] for r in res])
    sc = R.score(fc, ctx)
    per_seed, seed_mean, ensm = R.medians(sc)
    H1 = C.PRIMARY_HORIZON
    lw = ctx["lgb_sc"][ctx["lgb_sc"].window == "full"].set_index(["event", "h"])["nRMSE"]
    w = sc[sc.seed == 0].set_index(["event", "h"])["nRMSE"]
    summary = {"name": "LGB_seeds", "params": params, "lgb_config_sha256": cfg_sha, "seeds": seeds,
               "runtime_s": round(time.time() - t0, 1), "environment": A_.versions(), "check_passed": bool(args.check),
               "R1_bar_single_nb5a": ctx["nb5"]["R1_reference_nRMSE_1h"],
               "R1_bar_ensemble": float(ensm.loc[H1, "nRMSE"]),
               "R1_per_seed": per_seed[per_seed.h == H1].set_index("seed")["nRMSE"].round(5).to_dict(),
               "R1_seed_mean": float(seed_mean.loc[H1, ("nRMSE", "mean")]),
               "R1_seed_sd": float(seed_mean.loc[H1, ("nRMSE", "std")]),
               "units_ensemble_better_than_single_1h": int((w < lw.reindex(w.index)).xs(H1, level="h").sum()),
               "median_nRMSE_by_h": {"ensemble": ensm["nRMSE"].round(5).to_dict(),
                                     "seed_mean": seed_mean[("nRMSE", "mean")].round(5).to_dict()},
               "median_CRPS_by_h": {"ensemble": ensm["CRPS"].round(5).to_dict()},
               "median_PICP80_by_h": {"ensemble": ensm["PICP80"].round(4).to_dict()}}
    (C.RESULTS / "nb5c_variants").mkdir(exist_ok=True)
    A_.write_outputs("nb5c_variants/LGB_seeds", {"scores": sc, "tasks": meta}, summary, parquet={"forecasts": fc})
    tmp_parent = C.RESULTS / ".tmp_nb5c_variants"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    print(json.dumps({k: summary[k] for k in ["R1_bar_single_nb5a", "R1_bar_ensemble", "R1_seed_mean", "R1_seed_sd",
                                              "R1_per_seed", "units_ensemble_better_than_single_1h", "runtime_s"]},
                     default=str))
    print(pd.DataFrame(summary["median_nRMSE_by_h"]).round(4).to_string())


if __name__ == "__main__":
    main()
