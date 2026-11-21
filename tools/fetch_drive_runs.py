"""Bring the Colab foundation-model runs (NB5b_colab) back from the Google Drive mirror into the local repository (D66).

    python tools/fetch_drive_runs.py ["G:/My Drive/pv-cold-start"]

For every run record results/nb5b_runs/<setting>.json on the mirror: its inputs_sha256 must equal the local
results/nb5b_inputs/inputs_manifest.json (the inputs the local scoring uses), it must not be a smoke test (limit 0),
its parquet must exist and hold n_rows rows with the 9 quantiles sorted. A setting already in the repository is kept
if its files are identical and refused if they differ. All-or-nothing: nothing is copied unless every new record
passes; the files are staged in a temporary folder, then moved. Prints which of the 8 grid settings are present.
Then execute notebooks/NB5b_foundation.ipynb.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DEFAULT = "G:/My Drive/pv-cold-start"
GRID = [f"{m}_c{c}_{cov}" for m in ("chronos2", "timesfm25") for c in (336, 1344) for cov in ("full", "none")]
QC = [f"q{t:.1f}" for t in np.round(np.arange(0.1, 1.0, 0.1), 1)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    mirror = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
    src, dst = mirror / "results" / "nb5b_runs", REPO / "results" / "nb5b_runs"
    assert src.exists(), f"{src} not found: has the Colab run written anything, and has Drive synced?"
    man = json.loads((REPO / "results" / "nb5b_inputs" / "inputs_manifest.json").read_text())["sha256"]
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
    print("grid:", {g: g in have for g in GRID})
    print("all 8 settings present" if all(g in have for g in GRID) else "settings still missing: rerun NB5b_colab")


if __name__ == "__main__":
    main()
