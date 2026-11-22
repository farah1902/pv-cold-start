"""Zero-shot foundation-model forecasts of the campus index for NB5b (D23; guide §5.4, rows A6a-A6c).

Runs in the separate environment `.venv_fm` (`requirements-fm.txt`) or on Colab, never in the main environment:
its torch and transformers differ, and the main environment must keep reproducing the PVSetFormer rounds exactly.
NB5b writes the inputs with the main environment; this script forecasts; NB5b scores with the main environment.

Inputs (`results/nb5b_fm/inputs/`, git-ignored, sha256 in inputs_manifest.json):
  series.parquet  event, time, minute, k, sigma, c, n and the sun geometry on the full 15-min grid of each event (NaN
                  before the fleet's start, so no model sees more history than LightGBM's training window)
  tasks.parquet   event, origin, t: the issue times NB5a forecast on the validation units
Output: parquet with event, origin, seed (1: the models are deterministic), h, t, q0.1..q0.9 (index quantiles,
sorted, bounded to C.K_BOUNDS), only for targets inside the issue day; plus <out>.json (versions, settings, time).

Grid: the daylight slots 06:00-17:45 (48 a day). The index exists only there (inverter files, D12), so the night
would only cost compute (Chronos-2) or be filled with invented values (TimesFM interpolates gaps). On this grid,
step h after an issue time is t + 15 h for every target inside the issue day, which are the only scored targets.

Information set (guide §5.4): the past index as target; the fleet state (sigma, c, n) as past-only covariates; the
sun geometry u as known covariates over context and horizon.
  - Chronos-2 takes all of them (`--cov full`) or none (`--cov none`).
  - TimesFM 2.5 has no past-only covariates: its XReg mode fits, per issue time, a linear model of the index on
    covariates known over context and horizon. `--cov full` gives it the within-day geometry (Gt, cos z, azimuth and
    hour angle as sin and cos; the day of year is constant over a window); the fleet state cannot enter.
Inference is local: the weights are downloaded once from the Hugging Face hub without a token
(HF_HUB_DISABLE_IMPLICIT_TOKEN), and no data leave the machine.

    python tools/fm_infer.py --model chronos2 --context 1344 --cov full --inputs DIR --out FILE [--device cuda]
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")      # public weights: never send a stored token
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pvcold import config as C  # noqa: E402
from pvcold import forecast as FC  # noqa: E402

PAST = ["sigma", "c", "n"]                                          # fleet state, past only
GEO = ["Gt", "cosz", "sin_az", "cos_az", "sin_ha", "cos_ha", "sin_doy", "cos_doy"]   # u(t + h), known
GEO_DAY = ["Gt", "cosz", "sin_az", "cos_az", "sin_ha", "cos_ha"]  # TimesFM XReg: within-day geometry
DAY_FIRST, DAY_LAST = 6 * 60, FC.LAST_TARGET_MIN                    # 06:00 and 17:45 (D12)
PL = max(FC.H)                                                      # 24 steps = 6 h
QC = [f"q{t:.1f}" for t in FC.TAUS]
WEIGHTS = {"chronos2": "amazon/chronos-2", "timesfm25": "google/timesfm-2.5-200m-pytorch"}
PACKAGES = {"chronos2": ["chronos-forecasting", "transformers"], "timesfm25": ["timesfm", "jax", "scikit-learn"]}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weights_path(repo: str, rev: str | None) -> str:
    """The weights to load: the repository name (latest cached), or with --revision the snapshot of exactly that
    commit (NB6: the revisions frozen in part 2d and the frozen configuration)."""
    if not rev:
        return repo
    from huggingface_hub import snapshot_download
    path = snapshot_download(repo, revision=rev)
    assert Path(path).name == rev, f"{repo}: snapshot {Path(path).name} is not the pinned revision {rev}"
    return path


def revision(repo: str) -> str | None:
    """The commit of the weights in the local Hugging Face cache (the snapshot folder's name)."""
    from huggingface_hub import try_to_load_from_cache
    p = try_to_load_from_cache(repo, "config.json")
    return Path(p).parent.name if isinstance(p, str) else None


def fill(x: np.ndarray) -> np.ndarray:
    """Linear interpolation over missing values, nearest value at the edges (TimesFM XReg needs finite targets)."""
    ok = np.isfinite(x)
    if ok.all() or not ok.any():
        return np.nan_to_num(x)
    i = np.arange(len(x))
    return np.interp(i, i[ok], x[ok])


class Chronos2:
    def __init__(self, a):
        from chronos import Chronos2Pipeline
        self.pipe = Chronos2Pipeline.from_pretrained(weights_path(WEIGHTS["chronos2"], a.revision), device_map=a.device)
        own = {round(float(q), 4) for q in self.pipe.quantiles}
        self.meta = {"revision": a.revision or revision(WEIGHTS["chronos2"]), "revision_pinned": bool(a.revision),
                     "max_context": int(self.pipe.model.chronos_config.context_length),
                     "native_quantiles": all(round(float(t), 4) in own for t in FC.TAUS)}   # else interpolated
        self.cov = a.cov

    def __call__(self, D: dict, pos: np.ndarray, L: int) -> np.ndarray:
        inputs = []
        for p in pos:
            lo, hi = max(0, p - L + 1), p + 1
            d = {"target": D["k"][lo:hi]}
            if self.cov == "full":
                d["past_covariates"] = {c: D[c][lo:hi] for c in PAST + GEO}
                d["future_covariates"] = {c: D[c][hi:hi + PL] for c in GEO}
            inputs.append(d)
        q, _ = self.pipe.predict_quantiles(inputs, prediction_length=PL, quantile_levels=list(map(float, FC.TAUS)),
                                           batch_size=256)
        return np.stack([x[0].float().cpu().numpy() for x in q])          # (B, PL, 9)


class TimesFM25:
    def __init__(self, a):
        import timesfm
        self.m = timesfm.TimesFM_2p5_200M_torch.from_pretrained(weights_path(WEIGHTS["timesfm25"], a.revision),
                                                                 torch_compile=False)
        self.fc = dict(max_context=int(np.ceil(a.context / 32) * 32), max_horizon=PL, normalize_inputs=True,
                       use_continuous_quantile_head=True, force_flip_invariance=True, infer_is_positive=True,
                       fix_quantile_crossing=True, return_backcast=a.cov == "full", per_core_batch_size=a.batch)
        self.m.compile(timesfm.ForecastConfig(**self.fc))
        self.meta = {"revision": a.revision or revision(WEIGHTS["timesfm25"]), "revision_pinned": bool(a.revision),
                     "forecast_config": self.fc,
                     "native_quantiles": True,                                  # 10 outputs: mean, q0.1 .. q0.9
                     "xreg": {"mode": "xreg + timesfm", "covariates": GEO_DAY, "ridge": 0.0} if a.cov == "full" else None}
        self.cov = a.cov

    def __call__(self, D: dict, pos: np.ndarray, L: int) -> np.ndarray:
        ctx = [D["k"][max(0, p - L + 1):p + 1] for p in pos]
        if self.cov == "none":
            _, q = self.m.forecast(horizon=PL, inputs=[x.copy() for x in ctx])
            return np.asarray(q)[:, :PL, 1:10]
        dyn = {c: [np.nan_to_num(D[c][max(0, p - L + 1):p + 1 + PL]) for p in pos] for c in GEO_DAY}
        _, q = self.m.forecast_with_covariates(inputs=[fill(x) for x in ctx], dynamic_numerical_covariates=dyn,
                                               xreg_mode="xreg + timesfm", ridge=0.0, force_on_cpu=True)
        return np.stack([np.asarray(x)[:PL, 1:10] for x in q])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(WEIGHTS))
    ap.add_argument("--context", type=int, required=True, help="context length in daylight steps (48 a day)")
    ap.add_argument("--cov", choices=["full", "none"], default="full")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--batch", type=int, default=64, help="issue times per call")
    ap.add_argument("--limit", type=int, default=0, help="smoke test: first N tasks of each event")
    ap.add_argument("--events", nargs="*", default=None, help="only these events (D70: one part per event)")
    ap.add_argument("--revision", default=None, help="load exactly this commit of the weights (NB6, frozen)")
    a = ap.parse_args()

    import torch
    torch.set_num_threads(a.threads)
    t0 = time.time()
    inp = Path(a.inputs)
    man = json.loads((inp / "inputs_manifest.json").read_text())
    for f, h in man["sha256"].items():
        assert sha256(inp / f) == h, f"{f} differs from the manifest"
    series = pd.read_parquet(inp / "series.parquet")
    tasks = pd.read_parquet(inp / "tasks.parquet").sort_values(["event", "t"]).reset_index(drop=True)
    if a.events is not None:
        assert set(a.events) <= set(tasks.event), f"unknown events: {set(a.events) - set(tasks.event)}"
        tasks = tasks[tasks.event.isin(a.events)].reset_index(drop=True)
    if a.limit:
        tasks = tasks.groupby("event", sort=False).head(a.limit)
    model = {"chronos2": Chronos2, "timesfm25": TimesFM25}[a.model](a)

    steps = np.array(FC.H) - 1
    rows = []
    for v, tv in tasks.groupby("event", sort=False):
        S = series[series.event == v].set_index("time").sort_index()
        ns = S.index.as_unit("ns").asi8
        assert (np.diff(ns) == 15 * 60 * 10**9).all(), f"{v}: not a 15-min grid"
        day = S[(S["minute"] >= DAY_FIRST) & (S["minute"] <= DAY_LAST)]
        assert not np.isfinite(S.loc[~S.index.isin(day.index), "k"]).any(), f"{v}: index outside 06:00-17:45"
        D = {c: day[c].to_numpy(dtype=float) for c in ["k"] + PAST + GEO}
        pos = day.index.get_indexer(pd.DatetimeIndex(tv["t"]))
        assert (pos >= 0).all() and np.isfinite(D["k"][pos]).all(), f"{v}: issue time missing or without index"
        assert pos.max() + PL < len(day), f"{v}: the series ends within 6 h of an issue time"
        for i in range(0, len(tv), a.batch):
            sl = slice(i, i + a.batch)
            Q = model(D, pos[sl], a.context)[:, steps, :]                     # (B, 6, 9)
            Q = np.clip(np.sort(Q, axis=-1), *C.K_BOUNDS)
            B = len(Q)
            f = pd.DataFrame(Q.reshape(B * len(steps), len(QC)), columns=QC)
            f.insert(0, "t", np.repeat(tv["t"].to_numpy()[sl], len(steps)))
            f.insert(0, "h", np.tile(FC.H, B))
            f.insert(0, "seed", 1)
            f.insert(0, "origin", np.repeat(tv["origin"].to_numpy()[sl], len(steps)))
            f.insert(0, "event", v)
            rows.append(f)
        print(f"{v}: {len(tv)} issue times, {time.time() - t0:.0f} s", flush=True)
    fc = pd.concat(rows, ignore_index=True)
    minute = pd.DatetimeIndex(fc["t"]).hour * 60 + pd.DatetimeIndex(fc["t"]).minute
    fc = fc[(minute + 15 * fc["h"]).to_numpy() <= DAY_LAST].reset_index(drop=True)   # targets inside the issue day
    assert np.isfinite(fc[QC].to_numpy()).all(), "non-finite forecast"
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".tmp.parquet")
    fc.to_parquet(tmp)
    import importlib.metadata as md

    def ver(p):
        try:
            return md.version(p)
        except md.PackageNotFoundError:
            return None
    info = {"model": a.model, "weights": WEIGHTS[a.model], **model.meta, "context": a.context, "cov": a.cov,
            "grid": "daylight 06:00-17:45", "prediction_length": PL, "device": a.device, "threads": a.threads,
            "batch": a.batch, "limit": a.limit, "events": a.events, "inputs_sha256": man["sha256"], "n_tasks": len(tasks),
            "n_rows": len(fc),
            "runtime_s": round(time.time() - t0, 1),
            "versions": {p: ver(p) for p in ["torch", "numpy", "pandas", *PACKAGES[a.model]]},
            "python": sys.version.split()[0], "run_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    out.with_suffix(".json").write_bytes(json.dumps(info, indent=2, default=str).encode("utf-8"))
    tmp.replace(out)
    print(json.dumps({k: info[k] for k in ["model", "context", "cov", "n_tasks", "n_rows", "runtime_s"]}), flush=True)


if __name__ == "__main__":
    main()
