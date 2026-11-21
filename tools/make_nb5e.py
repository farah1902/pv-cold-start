"""Chronos-2 at every PVSetFormer issue time of the validation units, for the Chronos-2 input of PVSetFormer (D70).

    python tools/make_nb5e.py            # writes results/nb5e_inputs/ and notebooks/NB5e_colab.ipynb

Inputs (all-or-nothing, git-ignored except the manifest):
  series.parquet  a byte copy of results/nb5b_inputs/series.parquet (its hash is asserted equal to NB5b's manifest),
                  so the index, fleet state and geometry are exactly those Chronos-2 was scored on (D59)
  tasks.parquet   event, origin (NaT: an issue time, not a rolling origin), t: every issue time of each validation
                  event that PVSetFormer trains on or forecasts (issue rule, a defined target, at least 16 lags), from
                  the fleet's start to the event's last NB5a slot. Development data only.
NB5e_colab runs tools/fm_infer.py with the part-2d setting of A6a (Chronos-2, 1,344 daylight steps, covariates on),
one part per event (resumable), into results/nb5e_runs/. Chronos-2 forecasts at t use only data up to t, so the same
forecast serves every rolling origin. Back with `python tools/fetch_drive_runs.py --set nb5e`.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import nbformat as nbf
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

SRC, OUT = ROOT / "results" / "nb5b_inputs", ROOT / "results" / "nb5e_inputs"
SETTING = ("chronos2", 1344, "full")                     # A6a's part-2d setting (D59)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_inputs():
    man_b = json.loads((SRC / "inputs_manifest.json").read_text())
    assert sha(SRC / "series.parquet") == man_b["sha256"]["series.parquet"], "NB5b series differs from its manifest"
    p = F.load_panel(); del p["targets15_kW"]
    E = p["events"].set_index("event")
    idx = {k: pd.read_parquet(C.RESULTS / "nb3_index" / f"{k}.parquet").set_index("time") for k in ["k_cens", "sigma", "c", "n"]}
    gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
    old = pd.read_parquet(SRC / "tasks.parquet")
    rows, per, last_t = [], {}, {}
    for v in sorted(old.event.unique()):
        assert E.loc[v, "set"] == "validation", v
        S = FC.event_series(v, idx, p["geometry15"])
        A = SF.event_arrays(v, p, S, gains3[gains3.event == v].set_index("donor")["gain"])
        issue, Y, M = SF.targets(A)
        t = S.index
        last = old.loc[old.event == v, "t"].max()
        pos = np.where(issue & M.any(1) & (np.arange(len(t)) >= SF.L - 1) & (t <= last))[0]
        assert set(old.loc[old.event == v, "t"]) <= set(t[pos]), f"{v}: an NB5a slot is not a task"
        # Development data (D25): the validation units' own NB5a windows, which every row was already scored on (some
        # run to 13 Oct 2021); nothing after an event's last NB5a slot.
        assert t[pos].max() <= last, f"{v}: a task after the last NB5a slot"
        rows.append(pd.DataFrame({"event": v, "origin": pd.NaT, "t": t[pos]}))
        per[v] = int(len(pos))
        last_t[v] = str(t[pos].max())
    tasks = pd.concat(rows, ignore_index=True)
    tmp = OUT.with_name(OUT.name + ".tmp")
    assert not tmp.exists(), f"{tmp} exists"
    try:
        tmp.mkdir(parents=True)
        shutil.copyfile(SRC / "series.parquet", tmp / "series.parquet")
        tasks.to_parquet(tmp / "tasks.parquet")
        man = {"decision": "D70", "series_from": "results/nb5b_inputs/series.parquet (byte copy)",
               "events": sorted(per), "tasks_per_event": per, "last_task_per_event": last_t, "n_tasks": int(len(tasks)),
               "sha256": {f: sha(tmp / f) for f in ["series.parquet", "tasks.parquet"]}}
        assert man["sha256"]["series.parquet"] == man_b["sha256"]["series.parquet"]
        (tmp / "inputs_manifest.json").write_bytes(json.dumps(man, indent=2).encode("utf-8"))
        if OUT.exists():
            shutil.rmtree(OUT)
        tmp.rename(OUT)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"{len(tasks)} tasks, {len(per)} events ->", OUT)
    return man


md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell


def make_notebook(events):
    nb = nbf.v4.new_notebook()
    model, L, cov = SETTING
    nb.cells = [
        md("# NB5e — Chronos-2 at every PVSetFormer issue time (Colab GPU)\n\n"
           "D70. Runs `tools/fm_infer.py` with A6a's part-2d setting (Chronos-2, 1,344 daylight steps, covariates on) on "
           "`results/nb5e_inputs/`, one part per validation event, into `results/nb5e_runs/`. Resumable: a part whose "
           "output exists for the current inputs is skipped. Development data only.\n\n"
           "**On Colab:** open this notebook from the Drive folder `pv-cold-start-nb5e` (made by "
           "`python tools/make_drive_mirror.py --set nb5e`), choose a GPU runtime, run all cells. The last cell unmounts "
           "Drive; then Ctrl+S. Back on the local machine: `python tools/fetch_drive_runs.py --set nb5e`."),
        code("import os, sys, json, hashlib, subprocess, time\n"
             "from pathlib import Path\n"
             "ON_COLAB = 'google.colab' in sys.modules\n"
             "DRIVE_REPO = '/content/drive/MyDrive/pv-cold-start-nb5e'\n"
             "if ON_COLAB:\n"
             "    from google.colab import drive\n"
             "    drive.mount('/content/drive')\n"
             "    ROOT, PY, DEVICE = Path(DRIVE_REPO), sys.executable, 'cuda'\n"
             "    subprocess.run([PY, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements-fm.txt')], check=True)\n"
             "else:\n"
             "    ROOT = Path.cwd().resolve(); ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
             "    PY = str(ROOT / '.venv_fm' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')); DEVICE = 'cpu'\n"
             "INP, RUNS = ROOT / 'results' / 'nb5e_inputs', ROOT / 'results' / 'nb5e_runs'\n"
             "man = json.loads((INP / 'inputs_manifest.json').read_text())\n"
             "for f, h in man['sha256'].items():\n"
             "    assert hashlib.sha256((INP / f).read_bytes()).hexdigest() == h, f'{f} differs from its manifest'\n"
             f"EVENTS = {list(events)!r}\n"
             f"MODEL, CONTEXT, COV = {model!r}, {L}, {cov!r}\n"
             "print('ROOT', ROOT, '| device', DEVICE, '| events', len(EVENTS), '| tasks', man['n_tasks'])"),
        code("log = []\n"
             "for i, v in enumerate(EVENTS):\n"
             "    out = RUNS / f'{MODEL}_c{CONTEXT}_{COV}__e{i:02d}.parquet'\n"
             "    js = out.with_suffix('.json')\n"
             "    if out.exists() and js.exists() and json.loads(js.read_text())['inputs_sha256'] == man['sha256']:\n"
             "        log.append({'part': out.stem, 'event': v, 'status': 'done before'})\n"
             "        continue\n"
             "    t1 = time.time()\n"
             "    r = subprocess.run([PY, str(ROOT / 'tools' / 'fm_infer.py'), '--model', MODEL, '--context', str(CONTEXT),\n"
             "                        '--cov', COV, '--inputs', str(INP), '--out', str(out), '--device', DEVICE,\n"
             "                        '--events', v], cwd=str(ROOT))\n"
             "    assert r.returncode == 0, f'{out.stem} ({v}) failed'\n"
             "    log.append({'part': out.stem, 'event': v, 'status': 'run', 'runtime_s': round(time.time() - t1, 1),\n"
             "                'n_rows': json.loads(js.read_text())['n_rows']})\n"
             "    print(log[-1], flush=True)\n"
             "print(log)"),
        code("if ON_COLAB:\n"
             "    drive.flush_and_unmount()"),
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbf.write(nb, ROOT / "notebooks" / "NB5e_colab.ipynb")
    print("wrote notebooks/NB5e_colab.ipynb")


if __name__ == "__main__":
    m = make_inputs()
    make_notebook(m["events"])
