"""PVSetFormer hyperparameter search (rule R1: the same budget as LightGBM, 18 settings x 3 folds; D36).

Usage:  python tools/pvsf_cv.py --name CV2 [--set fleet_token=1 balance=1]
Same development index, folds and criterion as NB5a's rule 1 (mean pinball over 9 quantiles, 6 horizons, 3 folds).
Ties within 1e-6 go toward the defaults (d 64, lr 1e-3, weight decay 0.01), then toward fewer parameters.
Writes results/nb5c_variants/<name>/ and prints the chosen setting.
"""
import argparse
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
from joblib import Parallel, delayed  # noqa: E402

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from pvsf_dev import parse_set  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--set", nargs="*")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    t0 = time.time()
    base = {**SF.DEFAULTS, **parse_set(args.set)}
    p = F.load_panel(); del p["targets15_kW"]
    E = p["events"].set_index("event")
    VAL = E.index[E.set == "validation"].tolist()
    DEV = E.loc[VAL].sort_values(["n_donors", "start"]).index[-1]           # as NB5a
    idx = {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time") for k in ["k_cens", "sigma", "c", "n"]}
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    S = FC.event_series(DEV, idx, p["geometry15"])
    cut = S.index >= pd.Timestamp(C.FIRST_TEST_DAY)
    S.loc[cut, ["k", "sigma", "c", "n"]] = np.nan                          # development data only
    Adev = SF.event_arrays(DEV, p, S, gains3[gains3.event == DEV].set_index("donor")["gain"])
    for key in ["kap", "clip", "valid"]:
        Adev[key][cut] = 0.0
    FOLDS = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in [("2021-07-01", "2021-08-01"), ("2021-08-01", "2021-09-01"), ("2021-09-01", "2021-10-01")]]
    tasks = [(i, {**base, **g}, f, fs, fe) for i, g in enumerate(SF.PVSF_GRID) for f, (fs, fe) in enumerate(FOLDS)]
    print(f"{args.name}: {len(tasks)} trainings on {DEV}; base {base}", flush=True)
    out = Parallel(n_jobs=args.jobs, verbose=5)(delayed(SF.cv_fold)(Adev, fs, fe, cfg, C.SEED + 1) for _, cfg, _, fs, fe in tasks)
    rows = []
    for (i, cfg, f, fs, fe), res in zip(tasks, out):
        for h, (pb, n, be) in res.items():
            rows.append({"config": i, "d": cfg["d"], "lr": cfg["lr"], "weight_decay": cfg["weight_decay"], "fold": f + 1, "h": h,
                         "pinball": pb, "n_valid": n, "best_epoch": be, "n_params": SF.n_params(cfg)})
    cv = pd.DataFrame(rows)
    cvs = cv.groupby(["config", "d", "lr", "weight_decay", "n_params"])["pinball"].mean().reset_index().sort_values("pinball")
    tied = cvs[cvs.pinball <= cvs.pinball.min() + 1e-6].copy()
    tied["pref"] = list(zip(tied.d != base["d"], tied.lr != base["lr"], tied.weight_decay != base["weight_decay"], tied.n_params))
    best = tied.sort_values("pref").iloc[0]
    chosen = {"d": int(best.d), "lr": float(best.lr), "weight_decay": float(best.weight_decay)}
    lgb = json.loads((C.RESULTS / "nb5a_dev" / "summary.json").read_text())["cv_best_pinball"]
    summary = {"name": args.name, "base": base, "dev_index": DEV, "chosen": chosen, "best_pinball": float(best.pinball),
               "lgb_best_pinball": lgb, "runtime_s": round(time.time() - t0, 1), "environment": A_.versions(),
               "grid": SF.PVSF_GRID, "seed": C.SEED + 1}
    (C.RESULTS / "nb5c_variants").mkdir(exist_ok=True)
    A_.write_outputs(f"nb5c_variants/{args.name}", {"cv_grid": cv, "cv_summary": cvs}, summary)
    tmp_parent = C.RESULTS / ".tmp_nb5c_variants"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()
    print(cvs.round(6).to_string(index=False))
    print("chosen:", chosen, "| pinball %.6f (LightGBM CV best %.6f)" % (best.pinball, lgb))


if __name__ == "__main__":
    main()
