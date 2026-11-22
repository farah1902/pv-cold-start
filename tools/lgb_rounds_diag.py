"""LightGBM's boosting rounds on the validation units (diagnostic, F59). Development data only.

    python tools/lgb_rounds_diag.py [--gap-only] [--pvsf V12_5s]

1. Refits NB5a's bank (part-2a setting, NB5a's seed C.SEED) at every validation task and records, per horizon, the
   training pairs and the early-stopped number of rounds of each of the 9 quantile models (1 = nothing learned: the
   forecast is k(t) plus constant offsets). Writes results/nb5c_diag/lgb_rounds/best_iter.csv (about 12 min).
2. Per unit, origin and horizon: index-level pinball (9 quantiles, against k(t + h) from NB3, as F53) of a
   PVSetFormer round's 5-seed ensemble and of LGB_seeds' ensemble on their common rows, and the ratio. Writes
   by_origin_units.csv, and prints the median ratio by origin with and without the units whose bank stops at round 1.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import r1_score as R  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import forecast as FC  # noqa: E402


QC = [f"q{t:.1f}" for t in FC.TAUS]
OUT = ROOT / "results" / "nb5c_diag" / "lgb_rounds"


def ensemble(name: str) -> pd.DataFrame:
    f = pd.read_parquet(ROOT / "results" / "nb5c_variants" / name / "forecasts.parquet",
                        columns=["event", "origin", "seed", "h", "t"] + QC)
    e = f.groupby(["event", "origin", "h", "t"])[QC].mean().reset_index()
    e[QC] = np.sort(e[QC].to_numpy(), axis=1)
    e["origin"] = pd.to_datetime(e["origin"])
    return e


def gap(ctx: dict, pvsf: str) -> pd.DataFrame:
    E = ctx["E"]
    a, b = ensemble(pvsf), ensemble("LGB_seeds")
    m = a.merge(b, on=["event", "origin", "h", "t"], suffixes=("_p", "_l"))
    rows = []
    for v, x in m.groupby("event"):
        assert E.loc[v, "set"] == "validation"
        k = FC.event_series(v, ctx["idx"], ctx["geo15"])["k"]
        y = k.reindex(x["t"] + pd.to_timedelta(15 * x["h"], unit="min")).to_numpy()
        ok = np.isfinite(y)
        x = x[ok].assign(y=y[ok])
        x["pb_p"] = FC.pinball(x[[c + "_p" for c in QC]].to_numpy(), x["y"].to_numpy())
        x["pb_l"] = FC.pinball(x[[c + "_l" for c in QC]].to_numpy(), x["y"].to_numpy())
        x["origin_no"] = ((x["origin"] - E.loc[v, "start"]).dt.days / 30).round().astype(int)
        g = x.groupby(["origin_no", "h"]).agg(n=("y", "size"), pb_pvsf=("pb_p", "mean"), pb_lgb=("pb_l", "mean"))
        rows.append(g.reset_index().assign(event=v))
    out = pd.concat(rows, ignore_index=True)
    out["ratio_pct"] = 100 * (out["pb_pvsf"] / out["pb_lgb"] - 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap-only", action="store_true")
    ap.add_argument("--pvsf", default="V12_5s")
    args = ap.parse_args()
    ctx = R.load_context()
    if not args.gap_only:
        rounds(ctx)
    bi = pd.read_csv(OUT / "best_iter.csv")
    stuck = sorted(bi[(bi.origin_no == 0)].groupby("event")["n_q_at_1"].sum().loc[lambda s: s == 54].index)
    gp = gap(ctx, args.pvsf)
    gp.to_csv(OUT / "by_origin_units.csv", index=False, lineterminator="\n")
    print(f"{args.pvsf} against LGB_seeds, index pinball, median over units of the ratio (%); "
          f"units whose bank stops at round 1 at origin 0: {stuck}")
    for lab, sub in (("all 10", gp), ("without them", gp[~gp.event.isin(stuck)])):
        print(lab)
        print(sub.pivot_table(index="origin_no", columns="h", values="ratio_pct", aggfunc="median").round(2).to_string())
    print("the stuck units at origin 0:")
    print(gp[(gp.origin_no == 0) & gp.event.isin(stuck)].pivot_table(index="event", columns="h", values="ratio_pct")
          .round(1).to_string())
    # the paper's measure: median nRMSE over units (5-seed ensembles, all origins), with and without the stuck units
    VD = ROOT / "results" / "nb5c_variants"
    sc = {n: pd.read_csv(VD / n / "scores.csv").query("seed == 0").set_index(["event", "h"])["nRMSE"]
          for n in (args.pvsf, "TX1_5s", "LGB_seeds")}
    nr = []
    for n in (args.pvsf, "TX1_5s"):
        for lab, drop in (("all", []), ("without_round1_units", stuck)):
            a = sc[n][~sc[n].index.get_level_values(0).isin(drop)]
            r = 100 * (a.groupby("h").median() / sc["LGB_seeds"].reindex(a.index).groupby("h").median() - 1)
            nr += [{"model": n, "units": lab, "n_units": a.index.get_level_values(0).nunique(), "h": h,
                    "ratio_of_medians_vs_lgb_pct": float(x)} for h, x in r.items()]
    nr = pd.DataFrame(nr)
    nr.to_csv(OUT / "nrmse_vs_lgb_units.csv", index=False, lineterminator="\n")
    print(nr.pivot_table(index=["model", "units"], columns="h", values="ratio_of_medians_vs_lgb_pct").round(2).to_string())


def rounds(ctx: dict):
    params = dict(ctx["nb5"]["lgb_params"])
    E = ctx["E"]
    rows = []
    for v, o, e, _ in R.tasks(ctx, [C.SEED]):
        assert E.loc[v, "set"] == "validation"
        S = FC.event_series(v, ctx["idx"], ctx["geo15"])
        _, d = FC.run_origin(S, o, e, {**params, "seed": C.SEED}, models=("LGB",))
        k = int(round((o - E.loc[v, "start"]).days / 30))
        for h in FC.H:
            b = np.array(d[h]["best_iter"])
            rows.append({"event": v, "origin_no": k, "days_hist": (o - FC.TRAIN_START).days, "h": h,
                         "n_train": d[h]["n_train"], "best_min": int(b.min()), "best_med": float(np.median(b)),
                         "n_q_at_1": int((b == 1).sum())})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "best_iter.csv", index=False, lineterminator="\n")
    g = df.groupby(["origin_no", "event"]).agg(days=("days_hist", "first"),
                                               n_train_1h=("n_train", lambda x: int(x.iloc[2])),
                                               q_at_1=("n_q_at_1", "sum"), med_best=("best_med", "median"))
    print(g.to_string())
    print("quantile models at round 1 (of 54 per task), by origin:", df.groupby("origin_no")["n_q_at_1"].sum().to_dict())


if __name__ == "__main__":
    main()
