"""Bring the Colab foundation-model runs (NB5b_colab) back from the Google Drive mirror into the local repository (D66).

    python tools/fetch_drive_runs.py [--set nb5b|nb5e] [MIRROR]

Sets: nb5b (D66; runs results/nb5b_runs/, inputs results/nb5b_inputs/, the 8 grid settings) and nb5e (D70; runs
results/nb5e_runs/, inputs results/nb5e_inputs/, one part per validation event of Chronos-2 c1344 full).

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
        "nb5e": ("G:/My Drive/pv-cold-start-nb5e", "nb5e_runs", "nb5e_inputs")}
QC = [f"q{t:.1f}" for t in np.round(np.arange(0.1, 1.0, 0.1), 1)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="nb5b")
    ap.add_argument("mirror", nargs="?", default=None)
    a = ap.parse_args()
    default, runs, inputs = SETS[a.set]
    mirror = Path(a.mirror or default)
    src, dst = mirror / "results" / runs, REPO / "results" / runs
    assert src.exists(), f"{src} not found: has the Colab run written anything, and has Drive synced?"
    man_all = json.loads((REPO / "results" / inputs / "inputs_manifest.json").read_text())
    man = man_all["sha256"]
    expect = GRID if a.set == "nb5b" else [f"chronos2_c1344_full__e{i:02d}" for i in range(len(man_all["events"]))]
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
