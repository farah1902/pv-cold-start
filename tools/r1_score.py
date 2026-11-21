"""Shared scoring for rule R1 (D36, D37): index-quantile forecasts of the validation units, scored on exactly the slots
NB5a scored, after composition with the frozen prior. Development data only.

Input rows: event, origin, seed, h, t, q0.1..q0.9 (one row per issue time and horizon). Seed 0 is reserved for the
seed ensemble (mean of the sorted quantiles across seeds, then sorted again).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count()))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402

QC = [f"q{t:.1f}" for t in FC.TAUS]
METRICS = ["nRMSE", "CRPS", "PICP80"]


def load_context() -> dict:
    """Panel, validation events, NB3 index and gains, frozen prior variant, NB5a forecasts and LightGBM scores."""
    p = F.load_panel()
    del p["targets15_kW"]
    E = p["events"].set_index("event")
    return {"p": p, "E": E, "U": p["units"], "geo15": p["geometry15"],
            "VAL": E.index[E.set == "validation"].tolist(),
            "idx": {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time")
                    for k in ["k_cens", "sigma", "c", "n"]},
            "gains3": pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv"),
            "PRIOR": yaml.safe_load((C.RESULTS / "nb3_index" / "frozen_config_part1.yaml").read_text())["prior_variant"],
            "ALT": json.loads((C.RESULTS / "nb1_audit" / "summary.json").read_text())["campus_altitude_m"],
            "nb5": json.loads((C.RESULTS / "nb5a_dev" / "summary.json").read_text()),
            "fc5": pd.read_parquet(C.RESULTS / "nb5a_dev" / "val_forecasts.parquet"),
            "lgb_sc": pd.read_csv(C.RESULTS / "nb5a_dev" / "val_scores.csv").query("model == 'LGB'")}


def tasks(ctx: dict, seeds) -> list:
    """(event, origin, end, seed) for every validation unit, NB5a origin and seed."""
    out = []
    for v in ctx["VAL"]:
        s = ctx["E"].loc[v, "start"]
        for d in FC.ORIGIN_DAYS:
            o = s + pd.Timedelta(days=d)
            for sd in seeds:
                out.append((v, o, min(o + pd.Timedelta(days=30), s + pd.Timedelta(days=90)), sd))
    return out


def with_ensemble(fc: pd.DataFrame) -> pd.DataFrame:
    ens = fc.groupby(["event", "origin", "h", "t"])[QC].mean().reset_index()
    ens[QC] = np.sort(ens[QC].to_numpy(), axis=1)
    ens["seed"] = 0
    return pd.concat([fc, ens], ignore_index=True)


def score(fc: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    """Per event, seed (0 = ensemble) and horizon: the NB5a scores of the composed power forecast on NB5a's slots."""
    p, E, U, geo15, gains3 = ctx["p"], ctx["E"], ctx["U"], ctx["geo15"], ctx["gains3"]
    fa = with_ensemble(fc)
    lv, gl = FC.member_levels()
    Tcache, rows = {}, []
    for v in ctx["VAL"]:
        assert E.loc[v, "set"] == "validation"
        a = F.event_arrays(v, p)
        g = gains3[gains3.event == v].set_index("donor")["gain"].reindex(a["dn"])
        pr, _, _, _ = F.event_priors(a, g, U, ctx["ALT"], Tcache)
        B = np.asarray(pr["B_" + ctx["PRIOR"]])
        g_m = FC.gain_members(pr[ctx["PRIOR"]], B / np.median(B), gl)
        f5 = ctx["fc5"][ctx["fc5"].event == v].copy()
        f5["target"] = f5["t"] + pd.to_timedelta(15 * f5["h"], unit="min")
        f5["y"] = p["y15"][E.loc[v, "units"]].reindex(f5["target"]).to_numpy()
        good = f5[QC].notna().all(axis=1) & np.isfinite(f5["y"])
        cnt = f5[good].groupby(["h", "t"])["model"].nunique()
        keys = cnt[cnt == f5.model.nunique()].index
        for seed, x in fa[fa.event == v].groupby("seed"):
            x = x.set_index(["h", "t"]).loc[lambda z: z.index.isin(keys)].reset_index()
            for h, xh in x.groupby("h"):
                tgt = xh["t"] + pd.Timedelta(minutes=15 * h)
                y = p["y15"][E.loc[v, "units"]].reindex(tgt).to_numpy()
                gt = geo15["Gt"].reindex(tgt).to_numpy()
                Y = FC.power_members(xh[QC].to_numpy(dtype=float), gt, g_m, lv)
                rows.append({"event": v, "seed": int(seed), "h": h,
                             "n_keys": int(len(keys[keys.get_level_values(0) == h])), **FC.scores(Y, y)})
    sc = pd.DataFrame(rows)
    assert (sc["n"] == sc["n_keys"]).all(), "some of NB5a's scored slots are missing"
    return sc


def medians(sc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Median over units per seed and horizon; mean and s.d. of those across seeds; the ensemble's medians."""
    per_seed = sc[sc.seed > 0].groupby(["seed", "h"])[METRICS].median().reset_index()
    seed_mean = per_seed.groupby("h")[METRICS].agg(["mean", "std"])
    ensm = sc[sc.seed == 0].groupby("h")[METRICS].median()
    return per_seed, seed_mean, ensm
