"""D80 extension: park the CPU trainings of the main row as a check, out of the test folder (run once, 23 Nov 2026).

    python tools/nb6_cpu_main_park.py

The local CPU run of the main row was stopped at 48 of its 255 trainings when every PVSetFormer-family row moved to the
Colab GPU. The test uses the GPU main row; these 48 CPU trainings are kept only for tools/nb6_cpu_gpu_check.py
(forecasts only, no observations). Moves results/nb6_forecasts/parts/main/ to results/nb6_cpu_main/parts/ (git-ignored)
and writes results/nb6_cpu_main/cpu_parts.csv (committed): every file with its sha256 and each training's meta.
All-or-nothing: every file is copied and checked before anything is removed from the test folder.
"""
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "nb6_forecasts" / "parts" / "main"
DST = ROOT / "results" / "nb6_cpu_main"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (DST / "parts").exists(), f"{DST / 'parts'} exists: already parked"
    metas = sorted(SRC.glob("*__meta.json"))
    files = sorted(p for p in SRC.iterdir() if p.is_file())
    assert metas and len(files) == 3 * len(metas), f"{len(files)} files for {len(metas)} metas"
    rows = []
    for mj in metas:
        m = json.loads(mj.read_text())
        assert "device" not in m and not m["skipped"], f"{mj.name}: not a finished CPU training"
        stem = mj.name[: -len("__meta.json")]
        fc, cal = SRC / f"{stem}.parquet", SRC / f"{stem}__cal.parquet"
        assert fc.exists() and cal.exists(), stem
        rows.append({"tag": stem, **{k: m[k] for k in ["event", "origin", "seed", "n_train", "n_fc", "best_epoch",
                                                       "runtime_s"]},
                     "device": "cpu", "sha256_fc": sha(fc), "sha256_cal": sha(cal), "sha256_meta": sha(mj)})
    tab = pd.DataFrame(rows)
    tmp = DST / ".tmp_parts"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for f in files:
        shutil.copyfile(f, tmp / f.name)
        assert sha(tmp / f.name) == sha(f), f"copy of {f.name} differs"
    tab.to_csv(DST / "cpu_parts.csv", index=False, lineterminator="\n")
    tmp.rename(DST / "parts")
    for f in files:                                  # every copy is in place and checked: empty the test folder
        f.unlink()
    SRC.rmdir()
    print(f"{len(metas)} CPU trainings ({len(files)} files, {tab.runtime_s.sum() / 3600:.1f} CPU-h) -> {DST / 'parts'}")
    print(tab.groupby(["event", "origin"]).seed.count().to_string())


if __name__ == "__main__":
    main()
