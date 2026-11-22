"""Generate notebooks/NB6_colab.ipynb: the test forecasts of rows A6a (Chronos-2) and A6b (TimesFM 2.5) on a Colab GPU
(D04, D79). Run after `python tools/nb6_forecast.py --fm-inputs`; mirror with `python tools/make_drive_mirror.py --set
nb6`; fetch back with `python tools/fetch_drive_runs.py --set nb6`.

The two settings and the weights revisions are those of the frozen configuration (part 2d; test_rows A6a, A6b),
written into the notebook here and passed to tools/fm_infer.py with --revision, so the test uses exactly the weights
the development run used. Nothing is chosen on Colab."""
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import evaluate as EV  # noqa: E402

fz, FZ_HASH = EV.load_frozen()
tr = fz["test_rows"]
RUNS = []
for row in ("A6a", "A6b"):
    model, ctx, cov = tr[row]["setting"].split("_")
    RUNS.append((row, model, int(ctx.lstrip("c")), cov, tr[row]["revision"]))
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb = nbf.v4.new_notebook()
nb.cells = [
    md("# NB6 (Colab) — test forecasts of the foundation-model rows A6a and A6b\n\n"
       f"D79, after the protocol freeze (frozen configuration `{FZ_HASH[:16]}…`). Runs `tools/fm_infer.py` for the two "
       "frozen settings with their pinned weights revisions on the 17 test events, from `results/nb6_forecasts/fm_inputs/` "
       "(`python tools/nb6_forecast.py --fm-inputs`), and writes `results/nb6_forecasts/fm/<setting>.parquet` with a JSON "
       "record. Resumable: a setting whose output exists for the current inputs is skipped. No score is computed here.\n\n"
       "**On Colab:** the Drive mirror (`python tools/make_drive_mirror.py --set nb6`) holds the notebook, "
       "`tools/fm_infer.py`, `src/pvcold/`, `requirements-fm.txt` and the inputs. Choose a GPU runtime, run all cells, "
       "end with `drive.flush_and_unmount()` (last cell) and Ctrl+S, then `python tools/fetch_drive_runs.py --set nb6`."),
    code("import os, sys, json, hashlib, subprocess, time\n"
         "from pathlib import Path\n"
         "ON_COLAB = 'google.colab' in sys.modules\n"
         "DRIVE_REPO = '/content/drive/MyDrive/pv-cold-start-nb6'\n"
         "if ON_COLAB:\n"
         "    from google.colab import drive\n"
         "    drive.mount('/content/drive')\n"
         "    ROOT, PY, DEVICE = Path(DRIVE_REPO), sys.executable, 'cuda'\n"
         "    subprocess.run([PY, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements-fm.txt')], check=True)\n"
         "else:\n"
         "    ROOT = Path.cwd().resolve(); ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "    PY = str(ROOT / '.venv_fm' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')); DEVICE = 'cpu'\n"
         "os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'\n"
         "INP, RUNS = ROOT / 'results' / 'nb6_forecasts' / 'fm_inputs', ROOT / 'results' / 'nb6_forecasts' / 'fm'\n"
         "man = json.loads((INP / 'inputs_manifest.json').read_text())\n"
         "for f, h in man['sha256'].items():\n"
         "    assert hashlib.sha256((INP / f).read_bytes()).hexdigest() == h, f'{f} differs from its manifest'\n"
         f"FROZEN_RUNS = {RUNS!r}   # (row, model, context, covariates, weights revision) from the frozen configuration\n"
         "print('ROOT', ROOT, '| device', DEVICE, '| events', len(man['events']), '| tasks', man['n_tasks'])"),
    code("log = []\n"
         "for row, model, L, cov, rev in FROZEN_RUNS:\n"
         "    out = RUNS / f'{model}_c{L}_{cov}.parquet'\n"
         "    js = out.with_suffix('.json')\n"
         "    if out.exists() and js.exists() and json.loads(js.read_text())['inputs_sha256'] == man['sha256']:\n"
         "        log.append({'row': row, 'setting': out.stem, 'status': 'done before'})\n"
         "        continue\n"
         "    t1 = time.time()\n"
         "    r = subprocess.run([PY, str(ROOT / 'tools' / 'fm_infer.py'), '--model', model, '--context', str(L), '--cov', cov,\n"
         "                        '--inputs', str(INP), '--out', str(out), '--device', DEVICE, '--revision', rev], cwd=str(ROOT))\n"
         "    assert r.returncode == 0, f'{out.stem} failed'\n"
         "    info = json.loads(js.read_text())\n"
         "    assert info['revision'] == rev and info['revision_pinned'], 'weights revision differs from the frozen one'\n"
         "    log.append({'row': row, 'setting': out.stem, 'status': 'run', 'runtime_s': round(time.time() - t1, 1),\n"
         "                'n_rows': info['n_rows'], 'revision': info['revision']})\n"
         "    print(log[-1], flush=True)\n"
         "print(log)"),
    code("if ON_COLAB:\n"
         "    drive.flush_and_unmount()"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, ROOT / "notebooks" / "NB6_colab.ipynb")
print("wrote notebooks/NB6_colab.ipynb |", RUNS)
