"""Build the minimal Google Drive mirror for the Colab run of NB5b (D04, D59, D66): only what NB5b_colab reads.

    python tools/make_drive_mirror.py ["G:/My Drive/pv-cold-start"]

Copies the notebook, tools/fm_infer.py, src/pvcold/*.py, requirements-fm.txt and results/nb5b_inputs/ (1.7 MB; no raw
data, no documents). All-or-nothing: the copy is assembled in a temporary folder next to the destination, checked file
by file (SHA-256), then renamed into place, with MIRROR_MANIFEST.json listing every hash. The destination must not
exist (the local repository is the master copy: to refresh, delete the Drive folder first). The folder name matches
DRIVE_REPO in the notebooks (/content/drive/MyDrive/pv-cold-start). Results come back with tools/fetch_drive_runs.py.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT = "G:/My Drive/pv-cold-start"
FILES = ["notebooks/NB5b_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
         "results/nb5b_inputs/inputs_manifest.json", "results/nb5b_inputs/series.parquet",
         "results/nb5b_inputs/tasks.parquet"] + sorted(
    str(p.relative_to(REPO)).replace("\\", "/") for p in (REPO / "src" / "pvcold").glob("*.py"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
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
