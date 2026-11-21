"""Where PVSetFormer's short-horizon median drift comes from (development data: validation units only; F52).

1. Reversion by volatility (every validation forecast of the given rounds, 5-seed ensembles as in D37): per horizon
   and quartile of the index's s.d. over the last hour (LightGBM's sd_1h), the least-squares slope of the median's
   change q0.5 - k(t) on (a) the day-earlier index at the target slot minus k(t) and (b) the last 4 h's mean minus
   k(t), with an intercept; the same for LightGBM's ensemble and for the truth k(t + h) - k(t).
2. Decomposition (one seed, a few tasks): the given round's setting is refitted on each task with the round's own
   training path; its median change is split into the transformer head's part and the linear path's part, and each
   is regressed on (b) per volatility quartile. The linear part is also split into its change terms (the lags and the
   day-earlier index minus k(t), SF.LIN_CHANGE) and the rest, and the mean of each part is tabulated per volatility
   quartile and level of k(t) (table decomposition_level: where the calm-state bias of F49 comes from).

    python tools/pvsf_drift_diag.py --rounds V4a_5s TX1_5s --decomp V4a "UG Hall2 RF:0" "SQ Apartment1-12:30" ...

Tasks are "event:origin day" (0, 30 or 60). Writes results/nb5c_diag/<out>/ (default drift; all-or-nothing).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402
from pvsf_vol_diag import KEY, load  # noqa: E402

QL = ["v1 calm", "v2", "v3", "v4 volatile"]


def slopes(X: np.ndarray, Y: dict) -> dict:
    X1 = np.column_stack([np.ones(len(X))] + [X[:, j] for j in range(X.shape[1])])
    return {k: np.linalg.lstsq(X1, v, rcond=None)[0] for k, v in Y.items()}


def reversion(names: list, k: pd.DataFrame, E: pd.DataFrame) -> pd.DataFrame:
    g = FC.full_grid()
    Lg, _ = load("LGB_seeds")
    out = []
    for name in names:
        P, _ = load(name)
        m = P.merge(Lg, on=KEY, suffixes=("_p", "_l"))
        assert len(m) == len(P) == len(Lg), f"{name}: rows differ from LightGBM's"
        parts = []
        for ev, z in m.groupby("event"):
            assert E.loc[ev, "set"] == "validation", ev
            kk = k[ev].reindex(g)
            w16 = pd.concat([kk.shift(j) for j in range(SF.L)], axis=1)
            w4 = pd.concat([kk.shift(j) for j in range(4)], axis=1)
            sd1 = w4.std(axis=1, ddof=1).where(w4.notna().sum(axis=1) >= 3)
            z = z.copy()
            tt = z["t"] + pd.to_timedelta(15 * z["h"], unit="min")
            z["y"], z["k0"] = kk.reindex(tt).to_numpy(), kk.reindex(z["t"]).to_numpy()
            z["kday"] = kk.reindex(tt - pd.Timedelta(days=1)).to_numpy()
            z["m4"], z["sd1"] = w16.mean(axis=1).reindex(z["t"]).to_numpy(), sd1.reindex(z["t"]).to_numpy()
            parts.append(z)
        m = pd.concat(parts, ignore_index=True)
        m = m[np.isfinite(m[["y", "k0", "kday", "m4", "sd1"]]).all(axis=1)]
        for h, z in m.groupby("h"):
            vq = pd.qcut(z["sd1"].rank(method="first"), 4, labels=QL)
            for q, zz in z.groupby(vq, observed=True):
                X = np.column_stack([zz.kday - zz.k0, zz.m4 - zz.k0])
                b = slopes(X, {"truth": (zz.y - zz.k0).to_numpy(), "model": (zz["q0.5_p"] - zz.k0).to_numpy(),
                               "lgb": (zz["q0.5_l"] - zz.k0).to_numpy()})
                for who, c in b.items():
                    out.append({"round": name, "h": h, "quartile": q, "who": who, "n": len(zz),
                                "intercept": c[0], "b_day": c[1], "b_m4": c[2]})
    return pd.DataFrame(out)


def decomposition(rnd: str, tasks: list, p: dict, E: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    import torch
    torch.set_num_threads(1)
    cfg = {**SF.DEFAULTS, **json.loads((C.RESULTS / "nb5c_variants" / rnd / "summary.json").read_text())["cfg"]}
    assert cfg.get("lin") and not any(cfg.get(o) for o in ("vol", "vgate", "hhead", "vlin")), "head + linear path only"
    idx = {c: pd.read_parquet(C.RESULTS / "nb3_index" / f"{c}.parquet").set_index("time") for c in ["k_cens", "sigma", "c", "n"]}
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    rows, meta = [], []
    for v, d in tasks:
        assert E.loc[v, "set"] == "validation", v
        s = E.loc[v, "start"]
        o = s + pd.Timedelta(days=d)
        end = min(o + pd.Timedelta(days=30), s + pd.Timedelta(days=90))
        A = SF.event_arrays(v, p, FC.event_series(v, idx, p["geometry15"]), gains3[gains3.event == v].set_index("donor")["gain"])
        t = A["S"].index
        issue, Y, M_all = SF.targets(A)
        _, _, M = SF.targets(A, o)
        tr = np.where(issue & M.any(1) & (np.arange(len(t)) >= SF.L - 1))[0]
        fc = np.where(issue & (t >= o) & (t < end) & M_all.any(1))[0]
        cut = int(round(len(tr) * (1 - FC.VALID_FRAC)))
        a, b = tr[:cut], tr[cut:]
        kt = A["S"]["k"].to_numpy()
        err = np.array([np.nanmean(np.abs(Y[tr, j] - kt[tr])[M[tr, j]]) for j in range(len(FC.H))])
        w = torch.tensor(1 / err / np.mean(1 / err), dtype=torch.float32) if cfg.get("balance") else None
        seed = C.SEED + 1
        _, best, _ = SF._train(SF.samples(A, a), Y[a], M[a], cfg, seed, cfg["max_epochs"], SF.samples(A, b), Y[b], M[b], w)
        mdl, _, _ = SF._train(SF.samples(A, tr), Y[tr], M[tr], cfg, seed, max(best, 1), w=w)
        mdl.eval()
        T = SF._tensors(SF.samples(A, fc))
        got = {}
        hk = mdl.head.register_forward_hook(lambda mod, i, out_: got.__setitem__("head", out_.detach()))
        with torch.no_grad():
            full = mdl(*T)
            lf = mdl.lin_features(T[4], T[5], T[6])
            lin = torch.einsum("bhf,hfo->bho", lf, mdl.lin_w)
            linch = torch.einsum("bhf,hf->bh", lf[..., SF.LIN_CHANGE], mdl.lin_w[:, SF.LIN_CHANGE, 0])
        hk.remove()
        head, lin, linch = got["head"][..., 0].numpy(), lin[..., 0].numpy(), linch.numpy()
        tot = full[..., 4].numpy() - kt[fc][:, None]
        assert np.allclose(tot, head + lin, atol=1e-5), "median change is not head + linear path"
        win = fc[:, None] - np.arange(SF.L - 1, -1, -1)[None, :]
        m4 = np.nanmean(kt[win], axis=1)
        w4 = kt[win[:, -4:]]
        sd1 = np.where(np.isfinite(w4).sum(1) >= 3, np.nanstd(w4, axis=1, ddof=1), np.nan)
        for j, h in enumerate(FC.H):
            ok = M_all[fc, j] & np.isfinite(Y[fc, j]) & np.isfinite(m4) & np.isfinite(sd1)
            rows.append(pd.DataFrame({"task": f"{v}:{d}", "h": h, "x": (m4 - kt[fc])[ok], "sd1": sd1[ok],
                                      "truth": (Y[fc, j] - kt[fc])[ok], "total": tot[ok, j], "head": head[ok, j],
                                      "lin": lin[ok, j], "lin_ch": linch[ok, j], "k0": kt[fc][ok]}))
        meta.append({"task": f"{v}:{d}", "n_train": len(tr), "n_fc": len(fc), "best_epoch": best, "seed": seed})
        print(f"decomposition {v}:{d} n_train {len(tr)} best_epoch {best}", flush=True)
    R = pd.concat(rows, ignore_index=True)
    out = []
    for h, z in R.groupby("h"):
        vq = pd.qcut(z["sd1"].rank(method="first"), 4, labels=QL)
        for q, zz in z.groupby(vq, observed=True):
            b = slopes(zz[["x"]].to_numpy(), {c: zz[c].to_numpy() for c in ("truth", "total", "head", "lin")})
            out.append({"round": rnd, "h": h, "quartile": q, "n": len(zz), **{f"b_{c}": v[1] for c, v in b.items()},
                        "sd_head": zz["head"].std(), "sd_lin": zz["lin"].std()})
    lev = []
    R["lin_rest"] = R["lin"] - R["lin_ch"]
    for h, z in R.groupby("h"):
        vq = pd.qcut(z["sd1"].rank(method="first"), 4, labels=QL)
        kb = pd.cut(z["k0"], [-np.inf, 0.3, 0.6, 0.9, np.inf])
        for (q, b), zz in z.groupby([vq, kb], observed=True):
            lev.append({"round": rnd, "h": h, "quartile": q, "k0_bin": str(b), "n": len(zz),
                        **{f"mean_{c}": zz[c].mean() for c in ("truth", "total", "head", "lin_ch", "lin_rest")},
                        "median_truth": zz["truth"].median()})
    return pd.DataFrame(out), pd.DataFrame(meta), pd.DataFrame(lev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", nargs="*", default=["V4a_5s", "TX1_5s"])
    ap.add_argument("--decomp", nargs="*", default=[], help="round, then tasks 'event:day'")
    ap.add_argument("--out", default="drift", help="output folder under results/nb5c_diag/")
    a = ap.parse_args()
    t0 = time.time()
    p = F.load_panel(); del p["targets15_kW"]
    E = p["events"].set_index("event")
    k = pd.read_parquet(C.RESULTS / "nb3_index" / "k_cens.parquet").set_index("time")
    tables = {"reversion": reversion(a.rounds, k, E)}
    summary = {"name": "drift", "rounds": a.rounds, "environment": A_.versions()}
    if a.decomp:
        tasks = [(x.rsplit(":", 1)[0], int(x.rsplit(":", 1)[1])) for x in a.decomp[1:]]
        dec = decomposition(a.decomp[0], tasks, p, E)
        tables["decomposition"], tables["decomposition_tasks"], tables["decomposition_level"] = dec
        summary.update({"decomp_round": a.decomp[0], "decomp_tasks": a.decomp[1:]})
    summary["runtime_s"] = round(time.time() - t0, 1)
    A_.write_outputs(f"nb5c_diag/{a.out}", tables, summary)
    tmp_parent = C.RESULTS / ".tmp_nb5c_diag"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    r = tables["reversion"]
    print(r[r.h.isin([1, 2, 4])].pivot_table(index=["round", "h", "quartile"], columns="who", values="b_m4",
                                             observed=True).round(3).to_string())
    if a.decomp:
        print(tables["decomposition"].round(3).to_string(index=False))
        lv = tables["decomposition_level"]
        print(lv[lv.h.isin([1, 2, 4]) & (lv.quartile == QL[0])].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
