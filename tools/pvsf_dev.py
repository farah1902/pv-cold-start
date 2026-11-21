"""PVSetFormer development round on the validation units (rule R1, D36). Development data only.

Usage:  python tools/pvsf_dev.py --name V1 --seeds 1 [--set d=32 lr=0.003 ...] [--note "text"]

Runs every validation unit and origin (NB5a's protocol) for the given seeds in parallel, scores the forecasts on
exactly the slots NB5a scored (so LightGBM's numbers are directly comparable), and writes
results/nb5c_variants/<name>/ (all-or-nothing) plus one row in results/nb5c_variants/log.csv.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count()))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402


def task(name, Ar, origin, end, cfg, seed):
    r = SF.fit_predict(Ar, origin, end, cfg, seed)
    if r.get("skipped"):
        return name, origin, seed, None, None, r
    meta = {k: r[k] for k in ["seed", "n_train", "n_fc", "best_epoch", "runtime_s"]}
    return name, origin, seed, SF.to_rows(name, origin, Ar, r, "fc"), SF.to_rows(name, origin, Ar, r, "cal", "PVSF_cal"), meta


def parse_set(items):
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        out[k] = type(SF.DEFAULTS[k])(float(v)) if isinstance(SF.DEFAULTS[k], (int, float)) else v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--set", nargs="*")
    ap.add_argument("--note", default="")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    t0 = time.time()
    cfg = {**SF.DEFAULTS, **parse_set(args.set)}
    p = F.load_panel(); del p["targets15_kW"]
    E = p["events"].set_index("event"); U = p["units"]; geo15 = p["geometry15"]
    VAL = E.index[E.set == "validation"].tolist()
    idx = {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time") for k in ["k_cens", "sigma", "c", "n"]}
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    PRIOR = yaml.safe_load((C.RESULTS / "nb3_index" / "frozen_config_part1.yaml").read_text())["prior_variant"]
    ALT = json.loads((C.RESULTS / "nb1_audit" / "summary.json").read_text())["campus_altitude_m"]
    nb5 = json.loads((C.RESULTS / "nb5a_dev" / "summary.json").read_text())
    fc5 = pd.read_parquet(C.RESULTS / "nb5a_dev" / "val_forecasts.parquet")
    lgb_sc = pd.read_csv(C.RESULTS / "nb5a_dev" / "val_scores.csv").query("model == 'LGB'")

    arrays, tasks = {}, []
    for v in VAL:
        s = E.loc[v, "start"]
        S = FC.event_series(v, idx, geo15)
        arrays[v] = SF.event_arrays(v, p, S, gains3[gains3.event == v].set_index("donor")["gain"])
        for d in FC.ORIGIN_DAYS:
            o = s + pd.Timedelta(days=d)
            for seed in range(1, args.seeds + 1):
                tasks.append((v, o, min(o + pd.Timedelta(days=30), s + pd.Timedelta(days=90)), C.SEED + seed))
    print(f"{args.name}: {len(tasks)} trainings, {SF.n_params(cfg)} parameters, cfg {cfg}", flush=True)
    res = Parallel(n_jobs=args.jobs, verbose=5)(delayed(task)(v, arrays[v], o, e, cfg, sd) for v, o, e, sd in tasks)
    fc = pd.concat([r[3] for r in res if r[3] is not None], ignore_index=True)
    cal = pd.concat([r[4] for r in res if r[4] is not None], ignore_index=True)
    meta = pd.DataFrame([{"event": r[0], "origin": r[1], **r[5]} for r in res])

    # Score on NB5a's slots: per seed, and the seed ensemble (mean of the sorted quantiles)
    QC = [f"q{t:.1f}" for t in FC.TAUS]
    lv, gl = FC.member_levels()
    Tcache, srows = {}, []
    ens = fc.groupby(["event", "origin", "h", "t"])[QC].mean().reset_index()
    ens[QC] = np.sort(ens[QC].to_numpy(), axis=1)
    ens["seed"] = 0
    for v in VAL:
        assert E.loc[v, "set"] == "validation"
        a = F.event_arrays(v, p)
        g = gains3[gains3.event == v].set_index("donor")["gain"].reindex(a["dn"])
        pr, _, _, _ = F.event_priors(a, g, U, ALT, Tcache)
        B = np.asarray(pr["B_" + PRIOR]); g_m = FC.gain_members(pr[PRIOR], B / np.median(B), gl)
        f5 = fc5[fc5.event == v].copy()
        f5["target"] = f5["t"] + pd.to_timedelta(15 * f5["h"], unit="min")
        f5["y"] = p["y15"][E.loc[v, "units"]].reindex(f5["target"]).to_numpy()
        good = f5[QC].notna().all(axis=1) & np.isfinite(f5["y"])
        cnt = f5[good].groupby(["h", "t"])["model"].nunique()
        keys = cnt[cnt == f5.model.nunique()].index
        for seed, x in pd.concat([fc[fc.event == v], ens[ens.event == v]]).groupby("seed"):
            x = x.set_index(["h", "t"]).loc[lambda z: z.index.isin(keys)].reset_index()
            for h, xh in x.groupby("h"):
                tgt = xh["t"] + pd.Timedelta(minutes=15 * h)
                y = p["y15"][E.loc[v, "units"]].reindex(tgt).to_numpy()
                gt = geo15["Gt"].reindex(tgt).to_numpy()
                Y = FC.power_members(xh[QC].to_numpy(dtype=float), gt, g_m, lv)
                srows.append({"event": v, "seed": int(seed), "h": h, "n_keys": int(len(keys[keys.get_level_values(0) == h])),
                              **FC.scores(Y, y)})
    sc = pd.DataFrame(srows)
    assert (sc["n"] == sc["n_keys"]).all(), "PVSetFormer is missing some of NB5a's scored slots"
    per_seed = sc[sc.seed > 0].groupby(["seed", "h"])[["nRMSE", "CRPS", "PICP80"]].median().reset_index()
    seed_mean = per_seed.groupby("h")[["nRMSE", "CRPS", "PICP80"]].agg(["mean", "std"])
    ensm = sc[sc.seed == 0].groupby("h")[["nRMSE", "CRPS", "PICP80"]].median()
    lgbm = lgb_sc[lgb_sc.window == "full"].groupby("h")[["nRMSE", "CRPS", "PICP80"]].median()
    w = sc[sc.seed == 0].set_index(["event", "h"])["nRMSE"]
    lw = lgb_sc[lgb_sc.window == "full"].set_index(["event", "h"])["nRMSE"]
    wins = ((w < lw.reindex(w.index)).groupby("h").sum()).astype(int)
    H1 = C.PRIMARY_HORIZON
    r1_mean = float(seed_mean.loc[H1, ("nRMSE", "mean")])
    summary = {"variant": args.name, "note": args.note, "cfg": cfg, "n_params": SF.n_params(cfg), "seeds": args.seeds,
               "runtime_s": round(time.time() - t0, 1), "environment": A_.versions(),
               "R1_bar_lgb": nb5["R1_reference_nRMSE_1h"], "R1_seed_mean": r1_mean,
               "R1_seed_sd": float(seed_mean.loc[H1, ("nRMSE", "std")]) if args.seeds > 1 else None,
               "R1_ensemble": float(ensm.loc[H1, "nRMSE"]), "units_beating_lgb_1h_ensemble": int(wins.loc[H1]),
               "median_nRMSE_by_h": {"seed_mean": seed_mean[("nRMSE", "mean")].round(5).to_dict(),
                                     "ensemble": ensm["nRMSE"].round(5).to_dict(), "lgb": lgbm["nRMSE"].round(5).to_dict()},
               "median_CRPS_by_h": {"ensemble": ensm["CRPS"].round(5).to_dict(), "lgb": lgbm["CRPS"].round(5).to_dict()},
               "median_PICP80_by_h": {"ensemble": ensm["PICP80"].round(4).to_dict(), "lgb": lgbm["PICP80"].round(4).to_dict()},
               "mean_best_epoch": float(meta["best_epoch"].mean()), "mean_task_runtime_s": float(meta["runtime_s"].mean())}
    (C.RESULTS / "nb5c_variants").mkdir(exist_ok=True)
    out = A_.write_outputs(f"nb5c_variants/{args.name}", {"scores": sc, "tasks": meta}, summary,
                           parquet={"forecasts": fc, "calibration": cal})
    tmp_parent = C.RESULTS / ".tmp_nb5c_variants"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    log = C.RESULTS / "nb5c_variants" / "log.csv"
    row = pd.DataFrame([{"variant": args.name, "run_at": summary["environment"]["run_at"], "seeds": args.seeds,
                         "n_params": summary["n_params"], "R1_seed_mean": round(r1_mean, 5),
                         "R1_ensemble": round(summary["R1_ensemble"], 5), "R1_bar_lgb": round(summary["R1_bar_lgb"], 5),
                         "units_beating_lgb_1h": summary["units_beating_lgb_1h_ensemble"],
                         "cfg": json.dumps(cfg, sort_keys=True), "note": args.note,
                         "summary_sha256": hashlib.sha256((out / "summary.json").read_bytes()).hexdigest()[:16]}])
    row.to_csv(log, mode="a", header=not log.exists(), index=False, lineterminator="\n")
    print(json.dumps({k: summary[k] for k in ["variant", "R1_seed_mean", "R1_seed_sd", "R1_ensemble", "R1_bar_lgb",
                                              "units_beating_lgb_1h_ensemble", "runtime_s", "mean_best_epoch"]}, default=str))
    print(pd.DataFrame(summary["median_nRMSE_by_h"]).round(4).to_string())


if __name__ == "__main__":
    main()
