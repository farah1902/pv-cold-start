"""NB6 test forecasts: every frozen row on the 17 test events (13 scored, 4 sensitivity), after the protocol freeze.

    python tools/nb6_forecast.py --row ROW [--jobs 8] [--limit N]    # ROW: nb5a, LGB, sources, main, A2, A4c, A6e, A6d
    python tools/nb6_forecast.py --plan                              # tasks and estimated cost per row; runs nothing
    python tools/nb6_forecast.py --manifest                          # assemble the parts, hash them, write the manifest

Every setting is read from the frozen configuration (results/freeze/frozen_config.yaml, tag protocol-freeze) and
checked against the files it pins; nothing is tuned here. The code paths are those of the development runs:
- nb5a: forecast.origin_task (NB5a's forecasters with the part-2a LightGBM setting: LGB, A0, A1, PeEn, CLIPER, A5,
  A7); its slots define what is scored;
- LGB: forecast.cal_task with the bagging seeds of the frozen row (tools/r1_lgb_seeds.py, tools/lgb_seeds_cal.py):
  the 5-seed forecasts and their conformal calibration set (D64);
- sources: forecast.run_origin_source on NB4's raw and corrected sensor index (A4, A4b: LightGBM) and the CAMS index
  (A9: persisted, A9n: same-time oracle), as NB5d;
- main, A2, A4c, A6e, A6d: setformer.fit_predict with the frozen cfg and seeds (tools/pvsf_dev.py's task): forecasts
  and calibration sets. A2 reads NB3's median index; A4c adds NB4's corrected sensor index; A6e is the fleet summary
  only; A6d is TimeXer. A3 is not run: it is the main model's forecasts composed with prior G0 (NB6 scorer);
- A6a and A6b (Chronos-2, TimesFM 2.5) run on a Colab GPU (notebooks/NB6_colab.ipynb, tools/fm_infer.py with the
  frozen weights revisions) from the inputs of --fm-inputs (NB5b_inputs' procedure on the nb5a issue times); their
  outputs come back to results/nb6_forecasts/fm/<setting>.parquet.

    python tools/nb6_forecast.py --fm-inputs                         # after --row nb5a

Origins s, s + 30 d, s + 60 d, each forecasting up to 30 days within the first 90 (guide §5.3). Each (row, event,
origin, seed) task writes its own part file atomically under results/nb6_forecasts/parts/<row>/, so a run can stop and
resume; a finished part is never recomputed. No target power is read: forecasts use the event's index (built from its
donors), the donors' own series and the sun geometry. --manifest concatenates the parts of every row into
results/nb6_forecasts/<file>.parquet and writes manifest.json (sha256 of each file, the frozen hash, the commit), which
is committed before any test score exists (D79).
"""
import argparse
import hashlib
import json
import os
import subprocess
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

from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import evaluate as EV  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

OUT = C.RESULTS / "nb6_forecasts"
PARTS = OUT / "parts"
PVSF_ROWS = {"main": "V12_5s", "A2": None, "A4c": "A4c_V12", "A6e": "A6e_V12_5s", "A6d": "TX1_5s"}
OFF = ("clim", "fm")                       # switches added to the defaults after V12 (V13, V15): off, absent from 2c
SOURCES = {"sensor_raw": ("LGB",), "sensor_corr": ("LGB",), "cams": ("A1", "A7")}
FILES = {"nb5a": "nb5a", "LGB": "LGB", "LGB_cal": "LGB", "sources": "sources", "main": "main", "main_cal": "main",
         "A2": "A2", "A4c": "A4c", "A6e": "A6e", "A6d": "A6d"}          # manifest file -> row whose parts it holds


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def frozen() -> tuple[dict, str, dict]:
    fz, h = EV.load_frozen()
    p2a = yaml.safe_load((ROOT / fz["files"]["part2a_lightgbm"]["path"]).read_text())
    params = dict(p2a["lgb_params"])
    assert params == fz["test_rows"]["LGB"]["params"], "LightGBM setting differs from the frozen row"
    return fz, h, params


def pvsf_cfg(fz: dict, row: str) -> dict:
    """{**defaults, **frozen cfg}, with the off switches off; checked against the validation run of the same setting."""
    r = fz["test_rows"]["main" if row == "A2" else row]
    cfg = {**SF.DEFAULTS, **r["cfg"]}
    assert all(cfg[k] == 0 for k in OFF), "an off switch is on"
    run = PVSF_ROWS.get(row)
    if run:
        s = json.loads((C.RESULTS / "nb5c_variants" / run / "summary.json").read_text())
        ran = {k: v for k, v in s["cfg"].items() if k not in OFF}
        mine = {k: v for k, v in cfg.items() if k not in OFF}
        assert ran == mine, f"{row}: frozen cfg differs from the validation run {run}"
    if row == "main":
        assert SF.n_params(cfg) == r["n_params"], "main: parameter count differs from the frozen row"
    return cfg


class Inputs:
    """Panel (no target series), events, NB3 index and gains, NB4's source index."""

    def __init__(self):
        p = F.load_panel()
        del p["targets15_kW"]                          # forecasts never read the event's own power
        self.p = p
        self.E = p["events"].set_index("event")
        self.geo15 = p["geometry15"]
        self.EVENTS = self.E.index[self.E["set"].isin(["scored", "sensitivity"])].tolist()
        self.idx = {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time")
                    for k in ["k_cens", "k_med", "sigma", "c", "n"]}
        self.gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
        self.K15 = pd.read_parquet(C.RESULTS / "nb4_sensor" / "index15.parquet").set_index("time")

    def origins(self, v):
        s = self.E.loc[v, "start"]
        return [(s + pd.Timedelta(days=d), min(s + pd.Timedelta(days=d + 30), s + pd.Timedelta(days=90)))
                for d in FC.ORIGIN_DAYS]

    def series(self, v, k_key="k_cens"):
        return FC.event_series(v, self.idx, self.geo15, k_key=k_key)


def part_path(row, v, o, seed, kind="fc") -> Path:
    tag = f"{v.replace(' ', '_')}__{o:%Y%m%d}__{seed}"
    return PARTS / row / f"{tag}{'' if kind == 'fc' else '__' + kind}.parquet"


def write_atomic(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


# --- Tasks ----------------------------------------------------------------------------------------------------------
def nb5a_task(v, S, o, e, params):
    _, _, rows, diag = FC.origin_task(v, S, o, e, params)
    assert len(rows), f"{v}, {o}: NB5a's forecasters produced nothing"
    rows.insert(2, "seed", int(C.SEED))
    write_atomic(rows, part_path("nb5a", v, o, C.SEED))
    return {"event": v, "origin": str(o), "seed": int(C.SEED), "rows": len(rows),
            "skipped_h": int(sum(d.get("skipped", False) for d in diag.values()))}


def lgb_task(v, S, o, e, params, seed):
    t0 = time.time()
    _, _, rows, cal = FC.cal_task(v, S, o, e, {**params, "seed": int(seed)})
    for f in (rows, cal):
        if len(f):                                       # cal_task adds event and origin only to non-empty frames
            f.insert(2, "seed", int(seed))
    write_atomic(cal, part_path("LGB", v, o, seed, "cal"))
    write_atomic(rows, part_path("LGB", v, o, seed))
    return {"event": v, "origin": str(o), "seed": int(seed), "rows": len(rows), "cal_rows": len(cal),
            "runtime_s": round(time.time() - t0, 1)}


def source_task(v, Ss, S, src, o, e, params):
    f, d = FC.run_origin_source(Ss, S, o, e, params, SOURCES[src])
    f.insert(0, "origin", o); f.insert(0, "source", src); f.insert(0, "event", v); f.insert(3, "seed", int(C.SEED))
    write_atomic(f, PARTS / "sources" / f"{v.replace(' ', '_')}__{o:%Y%m%d}__{src}.parquet")
    return {"event": v, "origin": str(o), "source": src, "rows": len(f)}


def pvsf_task(row, v, Ar, o, e, cfg, seed):
    r = SF.fit_predict(Ar, o, e, cfg, seed)
    if r.get("skipped"):
        meta = {"event": v, "origin": str(o), "seed": int(seed), "skipped": True, "n_train": r["n_train"]}
    else:
        fc = SF.to_rows(v, o, Ar, r, "fc")                    # event, origin, seed, model, h, t, q0.1..q0.9
        cal = SF.to_rows(v, o, Ar, r, "cal", "PVSF_cal")
        write_atomic(cal, part_path(row, v, o, seed, "cal"))
        write_atomic(fc, part_path(row, v, o, seed))
        meta = {"event": v, "origin": str(o), "seed": int(seed), "skipped": False,
                **{k: r[k] for k in ["n_train", "n_fc", "best_epoch", "runtime_s"]}}
    mp = part_path(row, v, o, seed, "meta").with_suffix(".json")
    mp.write_text(json.dumps(meta))
    return meta


def pvsf_arrays(I: Inputs, row: str, v: str, cfg: dict) -> dict:
    S = I.series(v, "k_med" if row == "A2" else "k_cens")
    if cfg.get("ext"):                                 # A4c (D51): NB4's 15-min index of that source
        S["k_ext"] = I.K15["k_" + cfg["ext"]].reindex(S.index).astype(float).to_numpy()
    return SF.event_arrays(v, I.p, S, I.gains3[I.gains3.event == v].set_index("donor")["gain"])


def cost(I: Inputs, v: str, o) -> float:
    """Relative training cost of a PVSetFormer task: issue times before the origin times donors (the fit of the
    validation runs' run times on this product)."""
    S = I.series(v)
    iss = (S.panel & (S.Gt > C.ISSUE_MIN_GTILDE) & (S.n >= C.ISSUE_MIN_DONORS) & S.k.notna()
           & (S.index >= FC.TRAIN_START) & (S.index < o)).to_numpy()
    return float(iss.sum() * int(I.E.loc[v, "n_donors"]))


GPU_ROWS = ("A4c", "A2")                   # D80: trained on a Colab GPU (tools/nb6_gpu.py); here only with PVSF_CPU_ROWS=1


def run_row(row: str, jobs: int, limit: int | None):
    from joblib import Parallel, delayed
    if row in GPU_ROWS and os.environ.get("PVSF_CPU_ROWS") != "1":
        print(f"{row}: trained on the Colab GPU (D80, tools/nb6_gpu.py); not run here", flush=True)
        return
    fz, fz_hash, params = frozen()
    I = Inputs()
    t0 = time.time()
    if row == "nb5a":
        tasks = [(v, o, e) for v in I.EVENTS for o, e in I.origins(v) if not part_path("nb5a", v, o, C.SEED).exists()]
        tasks = tasks[:limit] if limit else tasks
        S = {v: I.series(v) for v in {t[0] for t in tasks}}
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(nb5a_task)(v, S[v], o, e, params) for v, o, e in tasks)
    elif row == "LGB":
        seeds = fz["test_rows"]["LGB"]["seeds"]
        tasks = [(v, o, e, sd) for v in I.EVENTS for o, e in I.origins(v) for sd in seeds
                 if not part_path("LGB", v, o, sd).exists()]
        tasks = tasks[:limit] if limit else tasks
        S = {v: I.series(v) for v in {t[0] for t in tasks}}
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(lgb_task)(v, S[v], o, e, params, sd) for v, o, e, sd in tasks)
    elif row == "sources":
        tasks = []
        for v in I.EVENTS:
            S = I.series(v)
            for src in SOURCES:
                Ss = S.copy()
                Ss["k"] = I.K15["k_" + src].reindex(S.index).astype(float).to_numpy()
                Ss[["sigma", "c", "n"]] = np.nan
                for o, e in I.origins(v):
                    if not (PARTS / "sources" / f"{v.replace(' ', '_')}__{o:%Y%m%d}__{src}.parquet").exists():
                        tasks.append((v, Ss, S, src, o, e))
        tasks = tasks[:limit] if limit else tasks
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(source_task)(v, Ss, S, src, o, e, params)
                                               for v, Ss, S, src, o, e in tasks)
    else:
        cfg = pvsf_cfg(fz, row)
        seeds = fz["test_rows"]["main" if row == "A2" else row]["seeds"]
        tasks = [(v, o, e, sd) for v in I.EVENTS for o, e in I.origins(v) for sd in seeds
                 if not part_path(row, v, o, sd, "meta").with_suffix(".json").exists()]
        tasks.sort(key=lambda t: -cost(I, t[0], t[1]))      # longest first (shorter makespan)
        tasks = tasks[:limit] if limit else tasks
        arrays = {v: pvsf_arrays(I, row, v, cfg) for v in {t[0] for t in tasks}}
        print(f"{row}: {len(tasks)} trainings to run, {SF.n_params(cfg)} parameters", flush=True)
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(pvsf_task)(row, v, arrays[v], o, e, cfg, sd)
                                               for v, o, e, sd in tasks)
    print(f"{row}: {len(res)} tasks in {time.time() - t0:.0f} s | frozen {fz_hash[:16]}", flush=True)


def plan():
    fz, _, _ = frozen()
    I = Inputs()
    rows = []
    for v in I.EVENTS:
        for o, e in I.origins(v):
            rows.append({"event": v, "origin": o, "cost": cost(I, v, o)})
    P = pd.DataFrame(rows)
    a, b = 8.09962167e-03, 3.01142533e+02          # V12_5s run times on validation ~ a * cost + b (seconds)
    P["est_h_V12"] = (a * P.cost + b) / 3600
    print(P.groupby("event")[["cost", "est_h_V12"]].sum().round(2).to_string())
    n = len(fz["test_rows"]["main"]["seeds"])
    print(f"V12-sized row: {P.est_h_V12.sum() * n:.0f} CPU-hours for {len(P) * n} trainings")
    for row in PVSF_ROWS:
        done = len(list((PARTS / row).glob("*__meta.json"))) if (PARTS / row).exists() else 0
        print(f"  {row}: {done} of {len(P) * n} trainings done")


# --- Foundation-model inputs (A6a, A6b on Colab) ---------------------------------------------------------------------
FM_COLS = ["minute", "k", "sigma", "c", "n", "Gt", "cosz", "sin_az", "cos_az", "sin_ha", "cos_ha", "sin_doy", "cos_doy"]


def fm_inputs():
    """NB5b_inputs' procedure on the test events: the issue times NB5a's forecasters forecast (the nb5a parts) and
    each event's index, fleet state and geometry from the fleet's start to two days after its last issue time.
    Writes results/nb6_forecasts/fm_inputs/ (series.parquet, tasks.parquet, inputs_manifest.json) all-or-nothing."""
    import shutil
    frozen()
    I = Inputs()
    parts = sorted((PARTS / "nb5a").glob("*.parquet"))
    assert len(parts) == 3 * len(I.EVENTS), f"nb5a: {len(parts)} of {3 * len(I.EVENTS)} parts; run --row nb5a first"
    f5 = pd.concat([pd.read_parquet(x, columns=["event", "origin", "t"]) for x in parts], ignore_index=True)
    tasks = f5.drop_duplicates().sort_values(["event", "t"]).reset_index(drop=True)
    assert set(tasks.event) == set(I.EVENTS)
    out_parts, chk = [], []
    for v in I.EVENTS:
        S = I.series(v)
        t_last = tasks.loc[tasks.event == v, "t"].max()
        S = S.loc[FC.TRAIN_START:t_last.normalize() + pd.Timedelta(days=2) - pd.Timedelta(minutes=15)]
        day = (S["minute"] >= 360) & (S["minute"] <= FC.LAST_TARGET_MIN)
        chk.append({"event": v, "rows": len(S), "k_outside_daylight": int(np.isfinite(S.loc[~day, "k"]).sum()),
                    "Gt_missing_in_daylight": int(S.loc[day, "Gt"].isna().sum()), "tasks": int((tasks.event == v).sum())})
        o = S[FM_COLS].copy()
        o.insert(0, "time", S.index)
        o.insert(0, "event", v)
        out_parts.append(o.reset_index(drop=True))
    series = pd.concat(out_parts, ignore_index=True)
    chk = pd.DataFrame(chk)
    print(chk.to_string(index=False))
    assert (chk.k_outside_daylight == 0).all() and (chk.Gt_missing_in_daylight == 0).all()
    dst, tmp = OUT / "fm_inputs", OUT / ".tmp_fm_inputs"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    series.to_parquet(tmp / "series.parquet")
    tasks.to_parquet(tmp / "tasks.parquet")
    man = {"tool": "nb6_forecast --fm-inputs", "decision": "D79", "environment": A_.versions(), "events": I.EVENTS,
           "n_series_rows": len(series), "n_tasks": len(tasks),
           "sha256": {f: EV.sha256(tmp / f) for f in ["series.parquet", "tasks.parquet"]}}
    (tmp / "inputs_manifest.json").write_bytes(json.dumps(man, indent=2, default=str).encode("utf-8"))
    assert not dst.exists(), "fm_inputs exists: the Colab run may already use it"
    tmp.rename(dst)
    print(json.dumps(man["sha256"], indent=1), "| tasks", len(tasks), "| written to", dst)


# --- Manifest -------------------------------------------------------------------------------------------------------
def manifest():
    fz, fz_hash, _ = frozen()
    I = Inputs()
    files, counts = {}, {}
    OUT.mkdir(exist_ok=True)
    for name, row in FILES.items():
        cal = name.endswith("_cal")
        parts = sorted((PARTS / row).glob("*__cal.parquet" if cal else "*.parquet"))
        if not cal:
            parts = [x for x in parts if not x.name.endswith("__cal.parquet")]
        assert parts, f"{name}: no parts"
        df = pd.concat([pd.read_parquet(x) for x in parts], ignore_index=True)
        if row in PVSF_ROWS or row == "LGB":
            seeds = fz["test_rows"]["main" if row == "A2" else row]["seeds"]
            got = df.groupby(["event", "origin"])["seed"].nunique()
            assert sorted(df.seed.unique().tolist()) == sorted(seeds), f"{name}: seeds"
            assert len(got) == 3 * len(I.EVENTS) and (got == len(seeds)).all(), f"{name}: missing (event, origin, seed)"
        assert set(df.event) == set(I.EVENTS), f"{name}: events"
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False)
        files[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": EV.sha256(path), "rows": int(len(df)),
                       "parts": len(parts)}
        counts[name] = len(df)
    files["A6a"] = files["A6b"] = None
    fm = OUT / "fm"
    for name, setting in (("A6a", fz["test_rows"]["A6a"]["setting"]), ("A6b", fz["test_rows"]["A6b"]["setting"])):
        p = fm / f"{setting}.parquet"
        assert p.exists(), f"{name}: the Colab run's file {p.name} is missing"
        files[name] = {"path": p.relative_to(ROOT).as_posix(), "sha256": EV.sha256(p), "rows": int(len(pd.read_parquet(p)))}
    man = {"tool": "nb6_forecast", "decision": "D79", "frozen_config_sha256": fz_hash, "commit": git("rev-parse", "HEAD"),
           "events": I.EVENTS, "environment": A_.versions(), "files": files}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    print(json.dumps({k: (v["sha256"][:16] if v else None) for k, v in files.items()}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", choices=["nb5a", "LGB", "sources", *PVSF_ROWS])
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--limit", type=int)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--fm-inputs", action="store_true")
    a = ap.parse_args()
    git("merge-base", "--is-ancestor", "protocol-freeze", "HEAD")      # never before the freeze
    if a.plan:
        plan()
    elif a.fm_inputs:
        fm_inputs()
    elif a.manifest:
        manifest()
    else:
        assert a.row, "--row, --plan or --manifest"
        run_row(a.row, a.jobs, a.limit)


if __name__ == "__main__":
    main()
