"""Bring the Colab foundation-model runs (NB5b_colab) back from the Google Drive mirror into the local repository (D66).

    python tools/fetch_drive_runs.py [--set nb5b|nb5e|nb6|nb6gpu] [MIRROR]

Sets: nb5b (D66; runs results/nb5b_runs/, inputs results/nb5b_inputs/, the 8 grid settings), nb5e (D70; runs
results/nb5e_runs/, inputs results/nb5e_inputs/, one part per validation event of Chronos-2 c1344 full) and nb6 (D79;
runs results/nb6_forecasts/fm/, inputs results/nb6_forecasts/fm_inputs/, the two frozen settings on the test events),
and nb6gpu (D80 and its extension; every PVSetFormer-family GPU training, see fetch_nb6gpu).

For every run record results/nb5b_runs/<setting>.json on the mirror: its inputs_sha256 must equal the local
results/nb5b_inputs/inputs_manifest.json (the inputs the local scoring uses), it must not be a smoke test (limit 0),
its parquet must exist and hold n_rows rows with the 9 quantiles sorted. A setting already in the repository is kept
if its files are identical and refused if they differ. All-or-nothing: nothing is copied unless every new record
passes; the files are staged in a temporary folder, then moved. Prints which of the 8 grid settings are present.
Then execute notebooks/NB5b_foundation.ipynb.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
GRID = [f"{m}_c{c}_{cov}" for m in ("chronos2", "timesfm25") for c in (336, 1344) for cov in ("full", "none")]
SETS = {"nb5b": ("G:/My Drive/pv-cold-start", "nb5b_runs", "nb5b_inputs"),
        "nb5e": ("G:/My Drive/pv-cold-start-nb5e", "nb5e_runs", "nb5e_inputs"),
        "nb6": ("G:/My Drive/pv-cold-start-nb6", "nb6_forecasts/fm", "nb6_forecasts/fm_inputs"),   # D79: the test
        "nb6gpu": ("G:/My Drive/pv-cold-start-nb6gpu", None, None)}      # D80: fetch_nb6gpu
NB6_SETTINGS = ["chronos2_c1344_full", "timesfm25_c1344_none"]       # frozen rows A6a, A6b (part 2d)
QC = [f"q{t:.1f}" for t in np.round(np.arange(0.1, 1.0, 0.1), 1)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fetch_nb6gpu(mirror: Path):
    """D80 and its extension: the GPU trainings (validation rounds V12_5s and TX1_5s, the test rows main, A2, A4c, A6e,
    A6d, tb_main) back into the repository. A training is
    copied only when its meta, forecast and calibration files are on the mirror, the two hashes equal those its meta
    records, it ran on a GPU with this repository's code (tools/nb6_gpu.py's code_sha256), was not skipped and has a
    frozen seed; one already here must be identical. Trainings still syncing are left for the next fetch. Staged in a
    temporary folder; forecast and calibration files are moved in before any meta, so the local chain (which skips a
    training whose meta exists) never sees a meta without its files."""
    import sys
    import yaml
    sys.path.insert(0, str(REPO / "tools"))
    import nb6_gpu as G
    fz = yaml.safe_load((REPO / "results" / "freeze" / "frozen_config.yaml").read_text(encoding="utf-8"))
    seeds = {int(s) for r in G.GPU_ROWS for s in fz["test_rows"][G.SEEDS_ROW[r]]["seeds"]}
    code = G.code_sha()
    folders = ([f"results/nb6_gpu_val/{ref}/parts" for ref in G.REFS]
               + [f"results/nb6_forecasts/parts/{r}" for r in G.GPU_ROWS])
    plan, pending, same = [], [], {}
    for rel in folders:
        src, dst = mirror / rel, REPO / rel
        same[rel] = 0
        if not src.exists():
            continue
        for mj in sorted(src.glob("*__meta.json")):
            try:
                m = json.loads(mj.read_text())
            except json.JSONDecodeError:
                pending.append(f"{rel}/{mj.name}")
                continue
            assert str(m.get("device", "")).startswith("cuda"), f"{rel}/{mj.name}: not a GPU run"
            assert m["code_sha256"] == code, f"{rel}/{mj.name}: ran other code than this repository's"
            assert not m["skipped"] and int(m["seed"]) in seeds, f"{rel}/{mj.name}: skipped or not a frozen seed"
            stem = mj.name[:-len("__meta.json")]
            data = [src / f"{stem}.parquet", src / f"{stem}__cal.parquet"]
            if not all(f.exists() for f in data) or [sha(f) for f in data] != [m["sha256"]["fc"], m["sha256"]["cal"]]:
                pending.append(f"{rel}/{stem}")
                continue
            trio = data + [mj]
            if (dst / mj.name).exists():
                assert all((dst / f.name).exists() and sha(dst / f.name) == sha(f) for f in trio), \
                    f"{rel}/{stem}: differs from the copy already in the repository"
                same[rel] += 1
                continue
            for f in data:                     # a half-finished earlier fetch is fine if identical
                assert not (dst / f.name).exists() or sha(dst / f.name) == sha(f), f"{rel}/{f.name}: differs here"
            plan.append((rel, trio))
    tmp = REPO / "results" / ".tmp_fetch_nb6gpu"
    assert not tmp.exists(), f"{tmp} exists"
    try:
        for rel, trio in plan:
            (tmp / rel).mkdir(parents=True, exist_ok=True)
            for f in trio:
                shutil.copyfile(f, tmp / rel / f.name)
                assert sha(tmp / rel / f.name) == sha(f), f"copy of {f.name} differs"
        for rel, trio in plan:                 # forecast and calibration files first
            (REPO / rel).mkdir(parents=True, exist_ok=True)
            for f in trio[:2]:
                (tmp / rel / f.name).replace(REPO / rel / f.name)
        for rel, trio in plan:                 # then the metas
            (tmp / rel / trio[2].name).replace(REPO / rel / trio[2].name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for rel in folders:
        n_new = sum(1 for r, _ in plan if r == rel)
        have = len(list((REPO / rel).glob("*__meta.json"))) if (REPO / rel).exists() else 0
        print(f"{rel}: {n_new} copied, {same[rel]} already here and identical, {have} here in all")
    print(f"{len(pending)} still syncing (fetch again later)" if pending else "nothing pending")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="nb5b")
    ap.add_argument("mirror", nargs="?", default=None)
    a = ap.parse_args()
    if a.set == "nb6gpu":
        return fetch_nb6gpu(Path(a.mirror or SETS["nb6gpu"][0]))
    default, runs, inputs = SETS[a.set]
    mirror = Path(a.mirror or default)
    src, dst = mirror / "results" / runs, REPO / "results" / runs
    assert src.exists(), f"{src} not found: has the Colab run written anything, and has Drive synced?"
    man_all = json.loads((REPO / "results" / inputs / "inputs_manifest.json").read_text())
    man = man_all["sha256"]
    expect = (GRID if a.set == "nb5b" else NB6_SETTINGS if a.set == "nb6"
              else [f"chronos2_c1344_full__e{i:02d}" for i in range(len(man_all["events"]))])
    new, same = [], []
    for js in sorted(src.glob("*.json")):
        rec = json.loads(js.read_text())
        pq = js.with_suffix(".parquet")
        assert rec["inputs_sha256"] == man, f"{js.name}: made from other inputs than the local manifest"
        assert not rec.get("limit"), f"{js.name}: a smoke test (limit {rec['limit']})"
        assert pq.exists(), f"{pq.name} missing"
        f = pd.read_parquet(pq)
        assert len(f) == rec["n_rows"], f"{pq.name}: {len(f)} rows, record says {rec['n_rows']}"
        q = f[QC].to_numpy(dtype=float)
        assert np.isfinite(q).all() and (np.diff(q, axis=1) >= -1e-6).all(), f"{pq.name}: quantiles not finite or sorted"
        pair = [(js, dst / js.name), (pq, dst / pq.name)]
        if all(d.exists() for _, d in pair):
            assert all(sha(s) == sha(d) for s, d in pair), f"{js.stem}: differs from the copy already in the repository"
            same.append(js.stem)
        else:
            assert not any(d.exists() for _, d in pair), f"{js.stem}: only half of it is in the repository"
            new.append(pair)
    tmp = dst.with_name(dst.name + ".tmp_fetch")
    assert not tmp.exists(), f"{tmp} exists"
    try:
        tmp.mkdir(parents=True)
        for pair in new:
            for s, d in pair:
                shutil.copyfile(s, tmp / d.name)
                assert sha(tmp / d.name) == sha(s), f"copy of {s.name} differs"
        dst.mkdir(exist_ok=True)
        for pair in new:
            for _, d in pair:
                (tmp / d.name).replace(d)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    have = {p.stem for p in dst.glob("*.json")}
    print(f"copied {len(new)} settings, {len(same)} already present and identical")
    print("expected:", {g: g in have for g in expect})
    print(f"all {len(expect)} present" if all(g in have for g in expect) else "still missing: rerun the Colab notebook")


if __name__ == "__main__":
    main()
