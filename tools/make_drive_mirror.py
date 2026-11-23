"""Build the minimal Google Drive mirror for the Colab run of NB5b (D04, D59, D66): only what NB5b_colab reads.

    python tools/make_drive_mirror.py [--set nb5b|nb5e|nb6|nb6gpu] [DEST]

Sets: nb5b (D66, default destination "G:/My Drive/pv-cold-start"), nb5e (D70, Chronos-2 at every PVSetFormer issue
time, default destination "G:/My Drive/pv-cold-start-nb5e") and nb6 (D79, the test forecasts of rows A6a and A6b,
default destination "G:/My Drive/pv-cold-start-nb6") and nb6gpu (D80, PVSetFormer's test rows A4c, A2 and the test bed's
main on a Colab GPU, with the validation round and its gate; default destination "G:/My Drive/pv-cold-start-nb6gpu";
what tools/nb6_gpu.py reads: its code, the frozen configuration and every file it pins, the panel, NB3's index, NB4's
source index, the test bed, and V12_5s's run with NB5a's validation forecasts for the gate's scorer, about 115 MB;
its code must be committed, and MIRROR_MANIFEST.json records the commit).

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
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC_PY = sorted(str(p.relative_to(REPO)).replace("\\", "/") for p in (REPO / "src" / "pvcold").glob("*.py"))
SETS = {"nb5b": ("G:/My Drive/pv-cold-start", ["notebooks/NB5b_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
                 "results/nb5b_inputs/inputs_manifest.json", "results/nb5b_inputs/series.parquet",
                 "results/nb5b_inputs/tasks.parquet"] + SRC_PY),
        "nb5e": ("G:/My Drive/pv-cold-start-nb5e", ["notebooks/NB5e_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
                 "results/nb5e_inputs/inputs_manifest.json", "results/nb5e_inputs/series.parquet",
                 "results/nb5e_inputs/tasks.parquet"] + SRC_PY),
        "nb6": ("G:/My Drive/pv-cold-start-nb6", ["notebooks/NB6_colab.ipynb", "tools/fm_infer.py", "requirements-fm.txt",
                "results/nb6_forecasts/fm_inputs/inputs_manifest.json", "results/nb6_forecasts/fm_inputs/series.parquet",
                "results/nb6_forecasts/fm_inputs/tasks.parquet"] + SRC_PY),     # D79: the test, rows A6a and A6b
        "nb6gpu": ("G:/My Drive/pv-cold-start-nb6gpu", None)}                  # D80: listed by nb6gpu_files()


def nb6gpu_files() -> list[str]:
    """D80: every file tools/nb6_gpu.py reads on Colab (validation round, gate, rows A4c, A2 and tb_main)."""
    import yaml
    fz = yaml.safe_load((REPO / "results" / "freeze" / "frozen_config.yaml").read_text(encoding="utf-8"))
    R = "results/"
    files = ["notebooks/NB6_gpu.ipynb", "tools/nb6_gpu.py", "tools/nb6_forecast.py", "tools/nb6_testbed.py",
             R + "freeze/frozen_config.yaml", R + "freeze/summary.json", R + "nb1_audit/summary.json",
             R + "nb3_index/gains.csv", R + "nb4_sensor/index15.parquet", R + "nb5a_dev/val_forecasts.parquet",
             R + "nb5c_variants/A4c_V12/summary.json"]
    files += [R + f"nb2_panel/{k}.parquet" for k in ("y15", "flags15", "geometry15", "targets15_kW")]
    files += [R + f"nb3_index/{k}.parquet" for k in ("k_cens", "k_med", "sigma", "c", "n")]
    files += [R + f"nb5c_variants/V12_5s/{k}" for k in ("summary.json", "tasks.csv", "scores.csv", "forecasts.parquet")]
    files += [R + f"nb6_testbed/{k}" for k in ("pseudo_events.csv", "gains.csv", "k_cens.parquet", "sigma.parquet",
                                                 "c.parquet", "n.parquet")]
    files += [f["path"] for f in fz["files"].values()]           # every file the frozen configuration pins
    return sorted(set(files + SRC_PY))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="nb5b")
    ap.add_argument("dest", nargs="?", default=None)
    a = ap.parse_args()
    default, FILES = SETS[a.set]
    FILES = FILES if FILES is not None else nb6gpu_files()
    dest = Path(a.dest or default)
    git = lambda *x: subprocess.run(["git", "-C", str(REPO), *x], capture_output=True, text=True,  # noqa: E731
                                    check=True).stdout.strip()
    if a.set == "nb6gpu":                     # the GPU parts record the code they ran: it must be a commit
        dirty = git("status", "--porcelain", "--", *FILES)
        assert not dirty, "commit these first: " + "; ".join(dirty.splitlines())
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
                                                             "commit": git("rev-parse", "HEAD"), "sha256": man},
                                                            indent=1), encoding="utf-8")
        tmp.rename(dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    for f, h in man.items():
        assert sha(dest / f) == h, f"{f} differs after the rename"
    print(f"{len(man)} files, {sum((dest / f).stat().st_size for f in man) / 1e6:.2f} MB, all hashes match -> {dest}")


if __name__ == "__main__":
    main()
