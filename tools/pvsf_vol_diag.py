"""Index-level diagnosis by recent volatility (development data only): a PVSetFormer round against LightGBM's 5-seed
ensemble, on the validation units' forecast issue times.

For each horizon, issue times are split into quartiles of the index's s.d. over the last hour at the issue time (the
feature sd_1h of the LightGBM bank, known ex ante). Per quartile: the mean pinball loss of the 9 index quantiles, the
MAE of the median, the mean width of the 10-90% interval and its coverage, against k(t + h) from NB3. Index level, before
composition with the gain prior: this explains the R1 scores, it does not replace them.

    python tools/pvsf_vol_diag.py --pvsf V4a_5s [--lgb LGB_seeds]

A round with several seeds is scored as its ensemble (mean of the sorted quantiles, sorted again, D37); a single-seed
round as that seed. Writes results/nb5c_diag/<pvsf>/ (all-or-nothing).
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

import r1_score as R  # noqa: E402
from pvcold import audit as A  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402

KEY = ["event", "origin", "h", "t"]
LABELS = ["v1 calm", "v2", "v3", "v4 volatile"]


def load(name: str) -> tuple[pd.DataFrame, list]:
    x = pd.read_parquet(C.RESULTS / "nb5c_variants" / name / "forecasts.parquet").drop(columns="model")
    seeds = sorted(x.seed.unique().tolist())
    if len(seeds) == 1:
        return x.drop(columns="seed"), seeds
    e = R.with_ensemble(x)
    return e[e.seed == 0].drop(columns="seed").reset_index(drop=True), seeds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pvsf", required=True)
    ap.add_argument("--lgb", default="LGB_seeds")
    a = ap.parse_args()
    t0 = time.time()
    P, sp = load(a.pvsf)
    Lg, sl = load(a.lgb)
    k = pd.read_parquet(C.RESULTS / "nb3_index" / "k_cens.parquet").set_index("time")
    E = F.load_panel()["events"].set_index("event")
    g = FC.full_grid()
    m = P.merge(Lg, on=KEY, suffixes=("_p", "_l"))
    assert len(m) == len(P) == len(Lg), "the two rounds have different forecast rows"
    parts = []
    for ev, z in m.groupby("event"):
        assert E.loc[ev, "set"] == "validation", ev             # development data only
        kk = k[ev].reindex(g)
        sd1 = pd.concat([kk.shift(j) for j in range(4)], axis=1)
        sd1 = sd1.std(axis=1, ddof=1).where(sd1.notna().sum(axis=1) >= 3)        # FC.state's sd_1h
        z = z.copy()
        z["y"] = kk.reindex(z["t"] + pd.to_timedelta(15 * z["h"], unit="min")).to_numpy()
        z["sd1"] = sd1.reindex(z["t"]).to_numpy()
        parts.append(z)
    m = pd.concat(parts, ignore_index=True)
    m = m[np.isfinite(m["y"]) & np.isfinite(m["sd1"])]
    taus = np.asarray(FC.TAUS)
    rows = []
    for tag in ("p", "l"):
        Q = m[[f"{c}_{tag}" for c in R.QC]].to_numpy(dtype=float)
        d = m["y"].to_numpy()[:, None] - Q
        m[f"pin_{tag}"] = np.mean(np.maximum(taus * d, (taus - 1) * d), axis=1)
        m[f"mae_{tag}"] = np.abs(m["y"] - m[f"q0.5_{tag}"])
        m[f"w_{tag}"] = m[f"q0.9_{tag}"] - m[f"q0.1_{tag}"]
        m[f"cov_{tag}"] = ((m["y"] >= m[f"q0.1_{tag}"]) & (m["y"] <= m[f"q0.9_{tag}"])).astype(float)
    for h, z in m.groupby("h"):
        z = z.assign(vol=pd.qcut(z["sd1"], 4, labels=LABELS))
        for lab, w in [("all", z)] + [(q, z[z.vol == q]) for q in LABELS]:
            r = {"h": int(h), "quartile": lab, "n": len(w), "sd1_max": float(w["sd1"].max())}
            for met in ("pin", "mae", "w", "cov"):
                r[f"{met}_pvsf"], r[f"{met}_lgb"] = float(w[f"{met}_p"].mean()), float(w[f"{met}_l"].mean())
            r["pin_rel_pct"] = 100 * (r["pin_pvsf"] / r["pin_lgb"] - 1)
            rows.append(r)
    tab = pd.DataFrame(rows)
    show = tab[tab.h.isin([1, 4, 24])][["h", "quartile", "pin_pvsf", "pin_lgb", "pin_rel_pct", "mae_pvsf", "mae_lgb",
                                         "w_pvsf", "w_lgb", "cov_pvsf", "cov_lgb"]]
    print(show.round(4).to_string(index=False))
    summary = {"tool": "pvsf_vol_diag", "environment": A.versions(), "runtime_s": round(time.time() - t0, 1),
               "pvsf": a.pvsf, "pvsf_seeds": sp, "lgb": a.lgb, "lgb_seeds": sl, "n_rows": int(len(m)),
               "pin_rel_pct_all": tab[tab.quartile == "all"].set_index("h")["pin_rel_pct"].round(2).to_dict(),
               "pin_rel_pct_calm": tab[tab.quartile == "v1 calm"].set_index("h")["pin_rel_pct"].round(2).to_dict(),
               "width_calm_vs_volatile_pvsf": {int(h): [round(float(x), 4) for x in
                                                        tab[(tab.h == h) & tab.quartile.isin([LABELS[0], LABELS[3]])]["w_pvsf"]]
                                               for h in FC.H},
               "width_calm_vs_volatile_lgb": {int(h): [round(float(x), 4) for x in
                                                       tab[(tab.h == h) & tab.quartile.isin([LABELS[0], LABELS[3]])]["w_lgb"]]
                                              for h in FC.H}}
    (C.RESULTS / "nb5c_diag").mkdir(exist_ok=True)
    out = A.write_outputs(f"nb5c_diag/{a.pvsf}", {"vol_regimes": tab}, summary)
    tmp_parent = C.RESULTS / ".tmp_nb5c_diag"                   # write_outputs' temp folder parent, now empty
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    print("written to", out, "| runtime %.0f s" % (time.time() - t0))
    print(json.dumps({k: summary[k] for k in ("pin_rel_pct_all", "pin_rel_pct_calm")}))


if __name__ == "__main__":
    main()
