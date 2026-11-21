"""Build the minimal Google Drive mirror for the Colab run of NB5b (D04, D59, D66): only what NB5b_colab reads.

    python tools/make_drive_mirror.py [--set nb5b|nb5e] [DEST]

Sets: nb5b (D66, default destination "G:/My Drive/pv-cold-start") and nb5e (D70, Chronos-2 at every PVSetFormer issue
time, default destination "G:/My Drive/pv-cold-start-nb5e").

Copies the notebook, tools/fm_infer.py, src/pvcold/*.py, requirements-fm.txt and results/nb5b_inputs/ (1.7 MB; no raw
data, no documents). All-or-nothing: the copy is assembled in a temporary folder next to the destination, checked file
by file (SHA-256), then renamed into place, with MIRROR_MANIFEST.json listing every hash. The destination must not
exist (the local repository is the master copy: to refresh, delete the Drive folder first). The folder name matches
DRIVE_REPO in the notebooks (/content/drive/MyDrive/pv-cold-start). Results come back with tools/fetch_drive_runs.py.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC_PY = sorted(str(p.relative_to(REPO)).replace("\\", "/") for p in (REPO / "src" / "pvcold").glob("*.py"))
SETS = {"nb5b": ("G:/My Drive/pv-cold-start", ["notebooks/NB5b_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
                 "results/nb5b_inputs/inputs_manifest.json", "results/nb5b_inputs/series.parquet",
                 "results/nb5b_inputs/tasks.parquet"] + SRC_PY),
        "nb5e": ("G:/My Drive/pv-cold-start-nb5e", ["notebooks/NB5e_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
                 "results/nb5e_inputs/inputs_manifest.json", "results/nb5e_inputs/series.parquet",
                 "results/nb5e_inputs/tasks.parquet"] + SRC_PY)}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="nb5b")
    ap.add_argument("dest", nargs="?", default=None)
    a = ap.parse_args()
    default, FILES = SETS[a.set]
    dest = Path(a.dest or default)
    assert dest.parent.exists(), f"{dest.parent} not found (is Google Drive for desktop running?)"
    assert not dest.exists(), f"{dest} exists: delete it first (the local repository is the master copy)"
    tmp = dest.with_name(dest.name + ".tmp")
    assert not tmp.exists(), f"{tmp} exists"
    man = {}
    try:
        for f in FILES:
            s, d = REPO / f, tmp / f
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, d)
            man[f] = sha(s)
            assert sha(d) == man[f], f"copy of {f} differs"
        (tmp / "MIRROR_MANIFEST.json").write_text(json.dumps({"source": "local repository (master copy)",
                                                             "sha256": man}, indent=1), encoding="utf-8")
        tmp.rename(dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    for f, h in man.items():
        assert sha(dest / f) == h, f"{f} differs after the rename"
    print(f"{len(man)} files, {sum((dest / f).stat().st_size for f in man) / 1e6:.2f} MB, all hashes match -> {dest}")


if __name__ == "__main__":
    main()
