"""NB6 on a GPU (D80): PVSetFormer's test rows A4c, A2 and the test bed's main on a Colab GPU, with the frozen cfg and
seeds. The main row, A6e and A6d stay on the local CPU (the author's choice, 23 Nov 2026). Execution only: the steps
are nb6_forecast.pvsf_task's (setformer.fit_predict, to_rows, atomic parts, meta last) with PVSF_DEVICE=cuda; the
inputs are nb6_forecast's and nb6_testbed's.

    python tools/nb6_gpu.py --cpu-check                 # local: setformer.py on the CPU reproduces V12_5s bit for bit
    python tools/nb6_gpu.py --validate [--procs 2]      # Colab: V12 on the 10 validation units with the 5 frozen seeds
    python tools/nb6_gpu.py --gate [--val DIR]          # Colab, then local again: scored as tools/pvsf_dev.py; the gate
    python tools/nb6_gpu.py --row A4c|A2|tb_main [--procs 2]    # Colab, once the gate has passed

The gate, fixed before any GPU run (D80): on the validation units, (i) the GPU 5-seed ensemble is level with the CPU
ensemble of V12_5s at every horizon (|difference| below 3% of the median nRMSE, the level line of guide §4.4), and
(ii) the mean over seeds of the per-seed median nRMSE differs from the CPU one by less than 3 standard errors at every
horizon. The gate's scorer is first checked to rebuild V12_5s's stored scores from its stored forecasts (so the Colab
environment scores as the local one). --gate writes results/nb6_gpu_gate/ and GATE.json next to the parts folder
(on Colab: in the Drive mirror); --row refuses to start unless GATE.json says passed for the same code. After the
Colab run, the validation parts are fetched and the gate re-run locally: that run's results/nb6_gpu_gate/ is the
committed record.

Every part's meta adds to pvsf_task's keys the device, the GPU, the torch, CUDA, numpy and pandas versions, the
sha256 of its forecast and calibration files, and the sha256 of the code files it ran (CODE), which
tools/fetch_drive_runs.py --set nb6gpu checks against the local repository before copying anything.
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
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
os.environ["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "tools"), os.environ.get("PYTHONPATH", "")])
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")      # deterministic cuBLAS (D80); set before CUDA starts
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count()))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

import nb6_forecast as NF  # noqa: E402
from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

VAL_RUN = "V12_5s"                                   # the CPU validation run of the main row's setting (part 2c)
VAL_PARTS = C.RESULTS / "nb6_gpu_val" / "parts"
GPU_ROWS = ("A4c", "A2", "tb_main")
CODE =["src/pvcold/config.py", "src/pvcold/fleet.py", "src/pvcold/forecast.py", "src/pvcold/setformer.py",
        "tools/nb6_forecast.py", "tools/nb6_testbed.py", "tools/nb6_gpu.py"]
GATE_LEVEL_PCT, GATE_Z = 3.0, 3.0
QC = [f"q{t:.1f}" for t in FC.TAUS]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_sha(root: Path = ROOT) -> str:
    return hashlib.sha256(json.dumps({f: sha(root / f) for f in CODE}, sort_keys=True).encode()).hexdigest()


def commit() -> str:
    """The local commit, or on Colab the commit the Drive mirror was built from (MIRROR_MANIFEST.json)."""
    mm = ROOT / "MIRROR_MANIFEST.json"
    if mm.exists():
        return f"{json.loads(mm.read_text())['commit']} (mirror)"
    return NF.git("rev-parse", "HEAD")


def device_info() -> dict:
    import torch
    dev = SF._device()
    out = {"device": dev, "torch": torch.__version__, "numpy": np.__version__, "pandas": pd.__version__}
    if dev.startswith("cuda"):
        out.update({"gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda})
    return out


def paths(kind: str, row: str, v: str, o, seed) -> tuple[Path, Path, Path]:
    """Forecast, calibration and meta files of one training: the test layout (nb6_forecast.part_path) or, for the
    validation round, the same names under results/nb6_gpu_val/parts/."""
    if kind == "val":
        tag = f"{v.replace(' ', '_')}__{o:%Y%m%d}__{seed}"
        return VAL_PARTS / f"{tag}.parquet", VAL_PARTS / f"{tag}__cal.parquet", VAL_PARTS / f"{tag}__meta.json"
    return (NF.part_path(row, v, o, seed), NF.part_path(row, v, o, seed, "cal"),
            NF.part_path(row, v, o, seed, "meta").with_suffix(".json"))


def gpu_task(kind, row, v, Ar, o, e, cfg, seed, code):
    """nb6_forecast.pvsf_task's steps, with the device record in the meta (written last, atomically)."""
    fcp, calp, mp = paths(kind, row, v, o, seed)
    r = SF.fit_predict(Ar, o, e, cfg, seed)
    meta = {"event": v, "origin": str(o), "seed": int(seed), "skipped": bool(r.get("skipped", False)),
            "n_train": r["n_train"]}
    if not meta["skipped"]:
        NF.write_atomic(SF.to_rows(v, o, Ar, r, "cal", "PVSF_cal"), calp)
        NF.write_atomic(SF.to_rows(v, o, Ar, r, "fc"), fcp)
        meta.update({k: r[k] for k in ["n_fc", "best_epoch", "runtime_s"]})
        meta["sha256"] = {"fc": sha(fcp), "cal": sha(calp)}
    meta.update(device_info())
    meta["code_sha256"] = code
    mp.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta))
    os.replace(tmp, mp)
    return meta


def run(kind, row, tasks, arrays, cfg, procs):
    from joblib import Parallel, delayed
    dev = SF._device()
    if dev != "cpu":
        import torch
        assert torch.cuda.is_available(), f"PVSF_DEVICE={dev} but torch sees no GPU"
    code = code_sha()
    print(f"{row}: {len(tasks)} trainings on {dev} with {procs} processes, {SF.n_params(cfg)} parameters, "
          f"code {code[:12]}", flush=True)
    t0 = time.time()
    res = Parallel(n_jobs=procs, verbose=5)(delayed(gpu_task)(kind, row, v, arrays[v], o, e, cfg, sd, code)
                                            for v, o, e, sd in tasks)
    rt = [m["runtime_s"] for m in res if not m["skipped"]]
    print(f"{row}: {len(res)} trainings in {time.time() - t0:.0f} s (mean training {np.mean(rt) if rt else 0:.0f} s), "
          f"{sum(m['skipped'] for m in res)} skipped", flush=True)
    return res


# --- Validation inputs: tools/pvsf_dev.py's construction ----------------------------------------------------------
def val_setup():
    s = json.loads((C.RESULTS / "nb5c_variants" / VAL_RUN / "summary.json").read_text())
    cfg = {**SF.DEFAULTS, **s["cfg"]}
    fz, _, _ = NF.frozen()
    assert cfg == NF.pvsf_cfg(fz, "main"), f"{VAL_RUN}'s cfg differs from the frozen main row"
    p = F.load_panel(); del p["targets15_kW"]
    E = p["events"].set_index("event"); geo15 = p["geometry15"]
    VAL = E.index[E.set == "validation"].tolist()
    idx = {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time")
           for k in ["k_cens", "sigma", "c", "n"]}
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    arrays = {v: SF.event_arrays(v, p, FC.event_series(v, idx, geo15), gains3[gains3.event == v].set_index("donor")["gain"])
              for v in VAL}
    tasks = []
    for v in VAL:
        st = E.loc[v, "start"]
        for d in FC.ORIGIN_DAYS:
            o = st + pd.Timedelta(days=d)
            for k in range(1, s["seeds"] + 1):
                tasks.append((v, o, min(o + pd.Timedelta(days=30), st + pd.Timedelta(days=90)), C.SEED + k))
    assert sorted({t[3] for t in tasks}) == sorted(fz["test_rows"]["main"]["seeds"]), "validation seeds differ"
    return cfg, arrays, tasks, p, E, VAL


def cpu_check():
    """The shortest V12_5s training, re-run on the CPU with the current setformer.py: forecasts and calibration set
    identical to the stored ones, bit for bit, and the same best epoch."""
    assert SF._device() == "cpu", "run the CPU check without PVSF_DEVICE"
    t0 = time.time()
    cfg, arrays, tasks, _, _, _ = val_setup()
    tk = pd.read_csv(C.RESULTS / "nb5c_variants" / VAL_RUN / "tasks.csv", parse_dates=["origin"])
    t = tk.sort_values("runtime_s").iloc[0]
    v, o, seed = t["event"], pd.Timestamp(t["origin"]), int(t["seed"])
    e = [x[2] for x in tasks if x[0] == v and x[1] == o and x[3] == seed][0]
    r = SF.fit_predict(arrays[v], o, e, cfg, seed)
    mine = {"forecasts": SF.to_rows(v, o, arrays[v], r, "fc"), "calibration": SF.to_rows(v, o, arrays[v], r, "cal", "PVSF_cal")}
    rows = []
    for name, a in mine.items():
        ref = pd.read_parquet(C.RESULTS / "nb5c_variants" / VAL_RUN / f"{name}.parquet")
        ref = ref[(ref["event"] == v) & (pd.to_datetime(ref["origin"]) == o) & (ref["seed"] == seed)]
        a = a.sort_values(["h", "t"]).reset_index(drop=True)
        b = ref.sort_values(["h", "t"]).reset_index(drop=True)
        keys = len(a) == len(b) and (a["h"].to_numpy() == b["h"].to_numpy()).all() and \
            (pd.to_datetime(a["t"]).to_numpy() == pd.to_datetime(b["t"]).to_numpy()).all()
        qa, qb = a[QC].to_numpy(), b[QC].to_numpy()
        same = bool(keys and qa.dtype == qb.dtype and np.array_equal(qa, qb))
        rows.append({"file": name, "rows_new": len(a), "rows_stored": len(b), "keys_equal": bool(keys),
                     "dtype_new": str(qa.dtype), "dtype_stored": str(qb.dtype), "bitwise_equal": same,
                     "max_abs_diff": float(np.abs(qa.astype(float) - qb.astype(float)).max()) if keys else None})
    ck = pd.DataFrame(rows)
    best_ok = int(r["best_epoch"]) == int(t["best_epoch"])
    passed = bool(ck["bitwise_equal"].all() and best_ok)
    print(ck.to_string(index=False))
    print(f"best epoch {r['best_epoch']} (stored {t['best_epoch']}); CPU check {'PASSED' if passed else 'FAILED'}")
    summary = {"tool": "nb6_gpu --cpu-check", "decision": "D80", "environment": A_.versions(), "device": SF._device(),
               "reference_run": VAL_RUN, "task": {"event": v, "origin": str(o), "seed": seed},
               "best_epoch": int(r["best_epoch"]), "best_epoch_stored": int(t["best_epoch"]), "passed": passed,
               "setformer_sha256": sha(ROOT / "src" / "pvcold" / "setformer.py"), "commit": NF.git("rev-parse", "HEAD"),
               "runtime_s": round(time.time() - t0, 1)}
    out = A_.write_outputs("nb6_gpu_cpu_check", {"comparison": ck}, summary)
    print("written to", out)
    assert passed, "the CPU path no longer reproduces V12_5s"


def validate(procs):
    cfg, arrays, tasks, _, _, _ = val_setup()
    todo = [t for t in tasks if not paths("val", "val", t[0], t[1], t[3])[2].exists()]
    print(f"validation round: {len(tasks)} trainings, {len(tasks) - len(todo)} done before", flush=True)
    if todo:
        run("val", "val", todo, arrays, cfg, procs)


# --- The gate (local) ------------------------------------------------------------------------------------------------
def score_val(fc: pd.DataFrame, p, E, VAL) -> pd.DataFrame:
    """tools/pvsf_dev.py's scoring, unchanged: per seed and for the seed ensemble (mean of the sorted quantiles, sorted
    again), on exactly the slots NB5a scored, composed with each unit's prior."""
    U, geo15 = p["units"], p["geometry15"]
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    PRIOR = yaml.safe_load((C.RESULTS / "nb3_index" / "frozen_config_part1.yaml").read_text())["prior_variant"]
    ALT = json.loads((C.RESULTS / "nb1_audit" / "summary.json").read_text())["campus_altitude_m"]
    fc5 = pd.read_parquet(C.RESULTS / "nb5a_dev" / "val_forecasts.parquet")
    lv, gl = FC.member_levels()
    Tcache, srows = {}, []
    ens = fc.groupby(["event", "origin", "h", "t"])[QC].mean().reset_index()
    ens[QC] = np.sort(ens[QC].to_numpy(), axis=1)
    ens["seed"] = 0
    for v in VAL:
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
                srows.append({"event": v, "seed": int(seed), "h": h,
                              "n_keys": int(len(keys[keys.get_level_values(0) == h])), **FC.scores(Y, y)})
    sc = pd.DataFrame(srows)
    assert (sc["n"] == sc["n_keys"]).all(), "missing some of NB5a's scored slots"
    return sc


def gate(val_dir: Path):
    t0 = time.time()
    _, _, tasks, p, E, VAL = val_setup()
    metas = [json.loads(x.read_text()) for x in sorted(val_dir.glob("*__meta.json"))]
    assert len(metas) == len(tasks), f"{len(metas)} of {len(tasks)} validation trainings in {val_dir}"
    assert not any(m["skipped"] for m in metas), "a validation training was skipped"
    assert all(m["device"].startswith("cuda") for m in metas), "a validation training did not run on the GPU"
    assert all(m["code_sha256"] == code_sha() for m in metas), "the GPU run used other code than this repository's"
    fcs = []
    for m in metas:
        fcp, _, _ = paths("val", "val", m["event"], pd.Timestamp(m["origin"]), m["seed"])
        f = val_dir / fcp.name
        assert sha(f) == m["sha256"]["fc"], f"{f.name}: hash differs from its meta"
        fcs.append(pd.read_parquet(f))
    fc_gpu = pd.concat(fcs, ignore_index=True)
    ref_dir = C.RESULTS / "nb5c_variants" / VAL_RUN
    sc_cpu = pd.read_csv(ref_dir / "scores.csv")
    rebuilt = score_val(pd.read_parquet(ref_dir / "forecasts.parquet"), p, E, VAL)   # the gate's scorer, checked
    num = ["nRMSE", "nMAE", "nMBE", "CRPS", "PICP80", "PINAW", "IS80"]
    k = ["event", "seed", "h"]
    a, b = rebuilt.sort_values(k).reset_index(drop=True), sc_cpu.sort_values(k).reset_index(drop=True)
    assert (a[k].to_numpy() == b[k].to_numpy()).all(), "rebuilt scores have other keys"
    self_diff = float(np.nanmax(np.abs(a[num].to_numpy(float) - b[num].to_numpy(float))))
    assert self_diff <= 1e-8, f"the gate's scorer does not rebuild {VAL_RUN}'s scores ({self_diff:.2e})"
    sc_gpu = score_val(fc_gpu, p, E, VAL)
    rows = []
    for h in FC.H:
        c = sc_cpu[(sc_cpu.seed > 0) & (sc_cpu.h == h)].groupby("seed")["nRMSE"].median()
        g = sc_gpu[(sc_gpu.seed > 0) & (sc_gpu.h == h)].groupby("seed")["nRMSE"].median()
        se = float(np.sqrt(c.var(ddof=1) / len(c) + g.var(ddof=1) / len(g)))
        z = float((g.mean() - c.mean()) / se)
        ec = float(sc_cpu[(sc_cpu.seed == 0) & (sc_cpu.h == h)]["nRMSE"].median())
        eg = float(sc_gpu[(sc_gpu.seed == 0) & (sc_gpu.h == h)]["nRMSE"].median())
        d = 100 * (eg - ec) / ec
        rows.append({"h": h, "cpu_seed_mean": float(c.mean()), "cpu_seed_sd": float(c.std(ddof=1)),
                     "gpu_seed_mean": float(g.mean()), "gpu_seed_sd": float(g.std(ddof=1)), "z": z,
                     "ens_cpu": ec, "ens_gpu": eg, "ens_diff_pct": d,
                     "pass_level": abs(d) < GATE_LEVEL_PCT, "pass_z": abs(z) < GATE_Z})
    G = pd.DataFrame(rows)
    G["pass"] = G["pass_level"] & G["pass_z"]
    passed = bool(G["pass"].all())
    pd.set_option("display.width", 200)
    print(G.round(5).to_string(index=False))
    rt = pd.Series([m["runtime_s"] for m in metas])
    dev = {k_: sorted({str(m.get(k_)) for m in metas}) for k_ in ["gpu", "torch", "cuda", "numpy", "pandas"]}
    summary = {"tool": "nb6_gpu --gate", "decision": "D80", "environment": A_.versions(), "reference_run": VAL_RUN,
               "rule": {"ensemble_level_pct": GATE_LEVEL_PCT, "seed_mean_z": GATE_Z}, "passed": passed,
               "scorer_rebuilds_reference_max_abs_diff": self_diff, "gpu_environment": dev,
               "gpu_training_runtime_s": {"mean": float(rt.mean()), "max": float(rt.max()), "sum": float(rt.sum())},
               "cpu_training_runtime_s_reference": float(pd.read_csv(ref_dir / "tasks.csv")["runtime_s"].mean()),
               "code_sha256": code_sha(), "commit": commit(), "runtime_s": round(time.time() - t0, 1)}
    out = A_.write_outputs("nb6_gpu_gate", {"gate": G, "scores_gpu": sc_gpu, "tasks_gpu": pd.DataFrame(metas)}, summary,
                           parquet={"forecasts_gpu": fc_gpu})
    print("written to", out)
    gp = val_dir.parent / "GATE.json"
    tmp = gp.with_suffix(".tmp")
    tmp.write_text(json.dumps({"passed": passed, "gate": rows, "commit": summary["commit"], "code_sha256": code_sha(),
                               "summary_sha256": sha(out / "summary.json")}, indent=1, default=str))
    os.replace(tmp, gp)
    print(f"GATE {'PASSED' if passed else 'FAILED'} -> {gp}")
    if not passed:
        raise SystemExit("the GPU validation run is not level with the CPU one: the test rows stay on the CPU")


# --- Test rows (Colab) -----------------------------------------------------------------------------------------------
def run_row(row, procs):
    assert row in GPU_ROWS, row
    gp = VAL_PARTS.parent / "GATE.json"
    assert gp.exists() and json.loads(gp.read_text())["passed"], "the validation gate has not passed"
    assert json.loads(gp.read_text())["code_sha256"] == code_sha(), "the gate was passed with other code"
    fz, fz_hash, _ = NF.frozen()
    if row == "tb_main":
        import nb6_testbed as TBT
        I = TBT.TBInputs()
        cfg = NF.pvsf_cfg(fz, "main")
        seeds = fz["test_rows"]["main"]["seeds"]

        def mk(v):
            return SF.event_arrays(v, I.p, I.series(v), I.gains3[I.gains3.event == v].set_index("donor")["gain"])
    else:
        I = NF.Inputs()
        cfg = NF.pvsf_cfg(fz, row)
        seeds = fz["test_rows"]["main" if row == "A2" else row]["seeds"]

        def mk(v):
            return NF.pvsf_arrays(I, row, v, cfg)
    tasks = [(v, o, e, sd) for v in I.EVENTS for o, e in I.origins(v) for sd in seeds
             if not paths("test", row, v, o, sd)[2].exists()]
    tasks.sort(key=lambda t: -NF.cost(I, t[0], t[1]))                # longest first
    arrays = {v: mk(v) for v in {t[0] for t in tasks}}
    print(f"{row}: frozen {fz_hash[:16]}, {len(I.EVENTS) * 3 * len(seeds)} trainings in all", flush=True)
    if tasks:
        run("test", row, tasks, arrays, cfg, procs)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cpu-check", action="store_true")
    g.add_argument("--validate", action="store_true")
    g.add_argument("--gate", action="store_true")
    g.add_argument("--row", choices=GPU_ROWS)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--val", default=str(VAL_PARTS))
    a = ap.parse_args()
    if a.cpu_check:
        cpu_check()
    elif a.validate:
        validate(a.procs)
    elif a.gate:
        gate(Path(a.val))
    else:
        run_row(a.row, a.procs)


if __name__ == "__main__":
    main()
