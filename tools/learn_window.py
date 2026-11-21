"""Training history vs model, on development data: is the third origin's gap a matter of data or of season?

On the validation units the origin is confounded with the calendar, because training always starts at the fleet's
start (FC.TRAIN_START): the third origin (s + 60 d) has more history and forecasts later in the summer. This tool
refits each model at the third origin with only as much history as the unit had at its first origin (s - TRAIN_START
days, ending at the origin), and compares with the full-history rounds on the same forecast rows.

    python tools/learn_window.py [--models LGB PVSF TX] [--seeds 5]

Models: LGB = NB5a's bank (part-2a setting, D34) with the seeds of LGB_seeds; PVSF = V4a's setting (V4a_5s); TX =
TimeXer (TX1_5s). History is hidden by setting the index, sigma, c and n to missing before the window, so no pair
before it is issued or trained on (the donor arrays stay; they are read only through issued samples). Scores are at
the index level (pinball over the 9 quantiles and MAE of the median against k(t + h) from NB3), on the rows each
full-history round forecast at that origin. Writes results/nb5c_diag/learning_window/ (all-or-nothing).
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
from pvcold import setformer as SF  # noqa: E402

FULL = {"LGB": "LGB_seeds", "PVSF": "V4a_5s", "TX": "TX1_5s"}
KEY = ["event", "origin", "h", "t"]
HIDE = ["k", "sigma", "c", "n"]


def windowed(S: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    S = S.copy()
    S.loc[S.index < start, HIDE] = np.nan
    return S


def lgb_task(v, S, o, e, params, seed):
    rows, _ = FC.run_origin(S, o, e, {**params, "seed": int(seed)}, models=("LGB",))
    rows.insert(0, "seed", int(seed)); rows.insert(0, "origin", o); rows.insert(0, "event", v)
    return rows.drop(columns="model"), {"event": v, "seed": int(seed)}


def nn_task(v, A, o, e, cfg, seed):
    r = SF.fit_predict(A, o, e, cfg, seed)
    assert not r.get("skipped"), (v, o, seed)
    return SF.to_rows(v, o, A, r, "fc").drop(columns="model"), {"event": v, "seed": int(seed), "n_train": r["n_train"],
                                                                 "best_epoch": r["best_epoch"]}


def ensemble(fc: pd.DataFrame) -> pd.DataFrame:
    e = fc.groupby(KEY)[R.QC].mean().reset_index()
    e[R.QC] = np.sort(e[R.QC].to_numpy(), axis=1)
    return e


def index_scores(fc: pd.DataFrame, k: pd.DataFrame) -> pd.DataFrame:
    g = FC.full_grid()
    taus = np.asarray(FC.TAUS)
    parts = []
    for ev, z in fc.groupby("event"):
        kk = k[ev].reindex(g)
        z = z.copy()
        z["y"] = kk.reindex(z["t"] + pd.to_timedelta(15 * z["h"], unit="min")).to_numpy()
        parts.append(z)
    z = pd.concat(parts, ignore_index=True)
    z = z[np.isfinite(z["y"])]
    d = z["y"].to_numpy()[:, None] - z[R.QC].to_numpy(dtype=float)
    z["pinball"] = np.mean(np.maximum(taus * d, (taus - 1) * d), axis=1)
    z["mae"] = np.abs(d[:, 4])
    return z.groupby(["event", "h"]).agg(pinball=("pinball", "mean"), mae=("mae", "mean"), n=("mae", "size")).reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["LGB", "PVSF", "TX"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    t0 = time.time()
    ctx = R.load_context()
    E, p = ctx["E"], ctx["p"]
    seeds = [C.SEED + i for i in range(1, args.seeds + 1)]
    params = dict(ctx["nb5"]["lgb_params"])
    cfg_path = C.RESULTS / "nb5a_dev" / "lgb_config_part2a.yaml"
    assert hashlib.sha256(cfg_path.read_bytes()).hexdigest() == ctx["nb5"]["lgb_config_sha256"], "part 2a changed"
    cfgs = {m: json.loads((C.RESULTS / "nb5c_variants" / FULL[m] / "summary.json").read_text())["cfg"]
            for m in args.models if m != "LGB"}
    k = pd.read_parquet(C.RESULTS / "nb3_index" / "k_cens.parquet").set_index("time")

    plan, jobs = [], []
    for v in ctx["VAL"]:
        assert E.loc[v, "set"] == "validation", v                         # development data only
        s = E.loc[v, "start"]
        hist = s - FC.TRAIN_START                                        # the unit's history at its first origin
        o = s + pd.Timedelta(days=FC.ORIGIN_DAYS[-1])
        e = min(o + pd.Timedelta(days=30), s + pd.Timedelta(days=90))
        w0 = o - hist
        plan.append({"event": v, "start": s, "origin": o, "end": e, "window_start": w0, "history_days": hist.days,
                     "full_history_days": (o - FC.TRAIN_START).days})
        S = windowed(FC.event_series(v, ctx["idx"], ctx["geo15"]), w0)
        if "LGB" in args.models:
            jobs += [("LGB", delayed(lgb_task)(v, S, o, e, params, sd)) for sd in seeds]
        A = SF.event_arrays(v, p, S, ctx["gains3"][ctx["gains3"].event == v].set_index("donor")["gain"])
        for m in cfgs:
            jobs += [(m, delayed(nn_task)(v, A, o, e, cfgs[m], sd)) for sd in seeds]
    plan = pd.DataFrame(plan)
    print(f"learning_window: {len(jobs)} fits ({args.models}, seeds {seeds})", flush=True)
    res = Parallel(n_jobs=args.jobs, verbose=5)(j for _, j in jobs)

    rows, metas = [], []
    for (m, _), (fc, meta) in zip(jobs, res):
        rows.append(fc.assign(model=m)); metas.append({**meta, "model": m})
    fcw = pd.concat(rows, ignore_index=True)
    scores = []
    for m in args.models:
        win = ensemble(fcw[fcw.model == m])
        full = pd.read_parquet(C.RESULTS / "nb5c_variants" / FULL[m] / "forecasts.parquet")
        full = full[full.seed != 0] if "seed" in full else full
        full["origin"] = pd.to_datetime(full["origin"])
        full = ensemble(full[full.origin.isin(plan.origin) & full.set_index(["event", "origin"]).index.isin(
            plan.set_index(["event", "origin"]).index)])
        a, b = win.set_index(KEY).sort_index(), full.set_index(KEY).sort_index()
        assert a.index.equals(b.index), f"{m}: windowed and full-history rounds forecast different rows"
        for tag, f in (("window", win), ("full", full)):
            scores.append(index_scores(f, k).assign(model=m, history=tag))
    sc = pd.concat(scores, ignore_index=True)
    # The confounded view: full-history rounds at every origin, each model against LightGBM (median over units)
    byo = {}
    for m in args.models:
        f = pd.read_parquet(C.RESULTS / "nb5c_variants" / FULL[m] / "forecasts.parquet")
        f = ensemble(f[f.seed != 0])
        f["rank"] = [int((o - E.loc[v, "start"]).days // 30) for v, o in zip(f["event"], pd.to_datetime(f["origin"]))]
        byo[m] = pd.concat([index_scores(z, k).assign(rank=r) for r, z in f.groupby("rank")]).set_index(
            ["event", "rank", "h"])["pinball"]
    by_origin = []
    for m in [x for x in args.models if x != "LGB"]:
        r = ((byo[m] / byo["LGB"] - 1) * 100).groupby(["rank", "h"]).median().reset_index(name="pinball_change_pct")
        by_origin.append(r.assign(model=m, origin_day=r["rank"] * 30))
    by_origin = pd.concat(by_origin, ignore_index=True).drop(columns="rank") if by_origin else pd.DataFrame()
    T = sc.pivot_table(index=["event", "h"], columns=["model", "history"], values="pinball")
    rel = []
    for m in [x for x in args.models if x != "LGB"]:
        for tag in ("window", "full"):
            r = (T[(m, tag)] / T[("LGB", tag)] - 1) * 100
            rel.append(r.groupby("h").median().rename(f"{m} vs LGB, {tag} history"))
    for m in args.models:
        r = (T[(m, "full")] / T[(m, "window")] - 1) * 100
        rel.append(r.groupby("h").median().rename(f"{m}: full vs window history"))
    rel = pd.DataFrame(rel).round(2)
    summary = {"name": "learning_window", "models": args.models, "seeds": seeds, "full_rounds": FULL,
               "cfgs": cfgs, "lgb_params": params, "origin_rank": len(FC.ORIGIN_DAYS) - 1,
               "history_days": plan.set_index("event")["history_days"].to_dict(),
               "full_history_days": plan.set_index("event")["full_history_days"].to_dict(),
               "median_pinball_change_pct": {i: rel.loc[i].to_dict() for i in rel.index},
               "runtime_s": round(time.time() - t0, 1), "environment": A_.versions()}
    A_.write_outputs("nb5c_diag/learning_window",
                     {"scores": sc, "plan": plan.astype(str), "fits": pd.DataFrame(metas), "medians": rel.reset_index(),
                      "by_origin": by_origin},
                     summary, parquet={"forecasts": fcw})
    tmp_parent = C.RESULTS / ".tmp_nb5c_diag"                   # write_outputs' temp folder parent, now empty
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    print(rel.to_string())
    if len(by_origin):
        print(by_origin.pivot_table(index=["model", "origin_day"], columns="h", values="pinball_change_pct").round(1).to_string())
    print(f"runtime {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
