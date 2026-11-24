"""D80 extension: the 48 CPU trainings of the main row against the GPU main row's trainings of the same event, origin
and seed. Forecasts only: no observation and no score (the panel is never read). A check, not a test row: the test
uses the GPU main row. The metrics below were fixed on 23 Nov 2026, before any GPU forecast existed.

    python tools/nb6_cpu_gpu_check.py              # after the GPU main row is fetched (fetch_drive_runs.py --set nb6gpu)
    python tools/nb6_cpu_gpu_check.py --dry-run    # code check: the CPU parts stand in for the GPU ones (zero
                                                   # differences expected); prints, writes nothing

CPU side: results/nb6_cpu_main/parts/ (parked by tools/nb6_cpu_main_park.py; every file checked against
cpu_parts.csv). GPU side: results/nb6_forecasts/parts/main/ (every file checked against its meta; device cuda).
Per training (event, origin, seed), on the index quantiles q0.1..q0.9:
- the issue times and horizons must be identical;
- GPU - CPU differences: mean absolute of the median (q0.5) and of all nine quantiles; RMS, maximum absolute and mean
  signed difference of the median;
- the mean width of the central 80% interval (q0.9 - q0.1) on each device;
- the best epochs on each device;
- the scale without observations: the same-device seed-to-seed difference of the median (mean absolute difference
  between this seed and each other seed of the same event and origin; on the GPU over its 5 seeds, on the CPU over the
  seeds it has), and the ratio of the device difference to the GPU seed-to-seed difference.
Per (event, origin) with all 5 CPU seeds: the two devices' 5-seed ensembles (mean of the sorted quantiles, sorted
again, as the test rows) compared by the mean absolute difference of q0.1, q0.5 and q0.9.
Writes results/nb6_cpu_gpu_check/ (tasks.csv, groups.csv, summary.json), all-or-nothing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import audit as A_  # noqa: E402

CPU = ROOT / "results" / "nb6_cpu_main"
GPU = ROOT / "results" / "nb6_forecasts" / "parts" / "main"
QC = [f"q{t:.1f}" for t in np.round(np.arange(0.1, 1.0, 0.1), 1)]
SEEDS = [20261119, 20261120, 20261121, 20261122, 20261123]      # the frozen seeds of the main row (checked below)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path) -> pd.DataFrame:
    return pd.read_parquet(p).sort_values(["h", "t"]).reset_index(drop=True)


def same_keys(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return len(a) == len(b) and (a["h"].to_numpy() == b["h"].to_numpy()).all() and \
        (pd.to_datetime(a["t"]).to_numpy() == pd.to_datetime(b["t"]).to_numpy()).all()


def mad(a: pd.DataFrame, b: pd.DataFrame, q: str = "q0.5") -> float:
    assert same_keys(a, b), "issue times or horizons differ"
    return float(np.mean(np.abs(b[q].to_numpy(float) - a[q].to_numpy(float))))


def ensemble(fs: list[pd.DataFrame]) -> pd.DataFrame:
    for f in fs[1:]:
        assert same_keys(fs[0], f), "issue times or horizons differ between seeds"
    q = np.sort(np.mean([f[QC].to_numpy(float) for f in fs], axis=0), axis=1)
    out = fs[0][["h", "t"]].copy()
    out[QC] = q
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fz = __import__("yaml").safe_load((ROOT / "results" / "freeze" / "frozen_config.yaml").read_text(encoding="utf-8"))
    assert fz["test_rows"]["main"]["seeds"] == SEEDS, "frozen seeds differ"
    tab = pd.read_csv(CPU / "cpu_parts.csv")
    cpu, gpu, gmeta = {}, {}, {}
    for r in tab.itertuples():                             # the parked CPU files are unchanged
        f = CPU / "parts" / f"{r.tag}.parquet"
        assert sha(f) == r.sha256_fc, f"{f.name}: differs from cpu_parts.csv"
        cpu[r.tag] = load(f)
    gdir = CPU / "parts" if a.dry_run else GPU
    groups = tab.assign(stem=tab.tag.str.rsplit("__", n=1).str[0]).groupby("stem")
    for stem, g in groups:
        for sd in SEEDS:
            tag = f"{stem}__{sd}"
            f, mj = gdir / f"{tag}.parquet", gdir / f"{tag}__meta.json"
            if a.dry_run and not f.exists():
                continue
            m = json.loads(mj.read_text())
            if not a.dry_run:
                assert str(m.get("device", "")).startswith("cuda"), f"{mj.name}: not a GPU training"
                assert sha(f) == m["sha256"]["fc"], f"{f.name}: differs from its meta"
            gpu[tag], gmeta[tag] = load(f), m
    rows = []
    for r in tab.itertuples():
        stem = r.tag.rsplit("__", 1)[0]
        c, g = cpu[r.tag], gpu[r.tag]
        assert same_keys(c, g), f"{r.tag}: issue times or horizons differ between CPU and GPU"
        dq = g[QC].to_numpy(float) - c[QC].to_numpy(float)
        dm = dq[:, QC.index("q0.5")]
        g_other = [gpu[f"{stem}__{s}"] for s in SEEDS if s != r.seed and f"{stem}__{s}" in gpu]
        c_other = [cpu[f"{stem}__{s}"] for s in SEEDS if s != r.seed and f"{stem}__{s}" in cpu]
        seed_gpu = float(np.mean([mad(g, x) for x in g_other])) if g_other else np.nan
        seed_cpu = float(np.mean([mad(c, x) for x in c_other])) if c_other else np.nan
        rows.append({"event": r.event, "origin": r.origin, "seed": r.seed, "n_fc": len(c),
                     "mad_median": float(np.abs(dm).mean()), "mad_all_q": float(np.abs(dq).mean()),
                     "rms_median": float(np.sqrt((dm ** 2).mean())), "max_abs_median": float(np.abs(dm).max()),
                     "mean_diff_median": float(dm.mean()),
                     "width80_cpu": float((c["q0.9"] - c["q0.1"]).mean()), "width80_gpu": float((g["q0.9"] - g["q0.1"]).mean()),
                     "best_epoch_cpu": int(r.best_epoch), "best_epoch_gpu": int(gmeta[r.tag].get("best_epoch", -1)),
                     "seed_mad_gpu": seed_gpu, "seed_mad_cpu": seed_cpu, "n_seeds_cpu_other": len(c_other),
                     "device_over_seed_gpu": float(np.abs(dm).mean()) / seed_gpu if seed_gpu else np.nan})
    T = pd.DataFrame(rows)
    grows = []
    for stem, g in groups:
        if len(g) < len(SEEDS) or not all(f"{stem}__{s}" in gpu for s in SEEDS):
            continue
        ec = ensemble([cpu[f"{stem}__{s}"] for s in SEEDS])
        eg = ensemble([gpu[f"{stem}__{s}"] for s in SEEDS])
        grows.append({"event": g.event.iloc[0], "origin": g.origin.iloc[0], "n_fc": len(ec),
                      **{f"ens_mad_{q}": mad(ec, eg, q) for q in ("q0.1", "q0.5", "q0.9")}})
    Gt = pd.DataFrame(grows)
    med = lambda s: float(np.nanmedian(s))  # noqa: E731
    summary = {"tool": "nb6_cpu_gpu_check", "decision": "D80 (extension)", "environment": A_.versions(),
               "dry_run": a.dry_run, "trainings": len(T), "ensemble_groups": len(Gt),
               "observations_read": False,
               "median_over_trainings": {k: med(T[k]) for k in ["mad_median", "mad_all_q", "rms_median",
                                                                 "max_abs_median", "mean_diff_median", "seed_mad_gpu",
                                                                 "seed_mad_cpu", "device_over_seed_gpu"]},
               "width80_mean": {"cpu": float(T.width80_cpu.mean()), "gpu": float(T.width80_gpu.mean())},
               "best_epoch_mean": {"cpu": float(T.best_epoch_cpu.mean()), "gpu": float(T.best_epoch_gpu.mean())},
               "ensemble_mad_median": {q: med(Gt[f"ens_mad_{q}"]) for q in ("q0.1", "q0.5", "q0.9")} if len(Gt) else None,
               "cpu_parts_sha256": sha(CPU / "cpu_parts.csv")}
    pd.set_option("display.width", 200)
    print(T.round(4).to_string(index=False))
    print(Gt.round(5).to_string(index=False))
    print(json.dumps({k: summary[k] for k in ["median_over_trainings", "width80_mean", "ensemble_mad_median"]}, indent=1))
    if a.dry_run:
        print("dry run: nothing written")
        return
    print("written to", A_.write_outputs("nb6_cpu_gpu_check", {"tasks": T, "groups": Gt}, summary))


if __name__ == "__main__":
    main()
