"""Generate notebooks/NB6_gpu.ipynb (D80 and its extension): every PVSetFormer-family test row on one Colab GPU (main,
A2, A4c, A6e, A6d, the test bed's main), after two validation rounds and their gates. Mirror with
`python tools/make_drive_mirror.py --set nb6gpu` (after committing); fetch back with
`python tools/fetch_drive_runs.py --set nb6gpu`, then re-run `python tools/nb6_gpu.py --gate --ref V12_5s` and
`--ref TX1_5s` locally.

The notebook copies the mirror to the Colab disk (every file checked against MIRROR_MANIFEST.json), keeps its outputs
on Drive (results/nb6_forecasts/parts and results/nb6_gpu_val are links to the mirror, so a disconnect loses only the
trainings in flight), and runs tools/nb6_gpu.py with PVSF_DEVICE=cuda: --validate for V12_5s and TX1_5s, --gate for
both (V12's failure stops the notebook; TimeXer's failure keeps A6d on the CPU), the projected GPU hours, then --row
main, A2, A4c, A6e, A6d (only if TimeXer passed), tb_main. Resumable: run all cells again after a disconnect; finished
trainings are skipped, and a gate already passed for the same code is re-checked from its parts in minutes.
Nothing is chosen on Colab: the settings and seeds come from the frozen configuration."""
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import evaluate as EV  # noqa: E402

fz, FZ_HASH = EV.load_frozen()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb = nbf.v4.new_notebook()
nb.cells = [
    md("# NB6 (Colab GPU) — every PVSetFormer-family test row on one GPU\n\n"
       f"D80 and its extension, after the protocol freeze (frozen configuration `{FZ_HASH[:16]}…`). Rows, in this "
       "order: main, A2, A4c, A6e, A6d (TimeXer), the test bed's main. All of them run on the same GPU, so the "
       "ablations are compared with the main row on one device. Same model, inputs, settings and seeds as the CPU "
       "development runs; only the device differs.\n\n"
       "First two validation rounds on the 10 validation units with the 5 frozen seeds (150 trainings each): V12 "
       "(the main model's setting) and TX1 (TimeXer, A6d's setting). Each gate: the GPU ensemble level with the CPU "
       "one (under 3% at every horizon) and the per-seed medians within 3 standard errors. If V12 fails, the notebook "
       "stops (every row stays on the CPU). If only TimeXer fails, A6d is skipped here (it then runs on the laptop's "
       "CPU). The gates print the projected GPU hours of every row.\n\n"
       "**How to run:** Runtime > Change runtime type > a GPU. Then Runtime > Run all. Keep the tab open. If Colab "
       "disconnects, reconnect and Run all again: finished trainings are kept on Drive and skipped. The last cell "
       "unmounts Drive. Then, on the laptop: `python tools/fetch_drive_runs.py --set nb6gpu`."),
    code("import os, sys, json, hashlib, shutil, subprocess, time\n"
         "from pathlib import Path\n"
         "from google.colab import drive\n"
         "drive.mount('/content/drive')\n"
         "DRIVE_REPO = Path('/content/drive/MyDrive/pv-cold-start-nb6gpu')\n"
         "ROOT = Path('/content/repo')\n"
         "man = json.loads((DRIVE_REPO / 'MIRROR_MANIFEST.json').read_text())\n"
         "if ROOT.exists():\n"
         "    shutil.rmtree(ROOT)          # links are removed, not followed: Drive keeps the outputs\n"
         "for f, h in man['sha256'].items():\n"
         "    if f.startswith('notebooks/'):\n"
         "        continue                 # this open notebook: Colab saves it to Drive itself; nothing runs from it\n"
         "    d = ROOT / f\n"
         "    d.parent.mkdir(parents=True, exist_ok=True)\n"
         "    shutil.copyfile(DRIVE_REPO / f, d)\n"
         "    assert hashlib.sha256(d.read_bytes()).hexdigest() == h, f'{f} differs from the mirror manifest'\n"
         "shutil.copyfile(DRIVE_REPO / 'MIRROR_MANIFEST.json', ROOT / 'MIRROR_MANIFEST.json')\n"
         "for rel in ['results/nb6_forecasts/parts', 'results/nb6_gpu_val']:   # outputs live on Drive\n"
         "    (DRIVE_REPO / rel).mkdir(parents=True, exist_ok=True)\n"
         "    (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)\n"
         "    os.symlink(DRIVE_REPO / rel, ROOT / rel)\n"
         "subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'pvlib==0.16.1'], check=True)   # the gate's priors\n"
         "import torch, numpy, pandas\n"
         "assert torch.cuda.is_available(), 'no GPU: Runtime > Change runtime type > a GPU'\n"
         "ENV = {**os.environ, 'PVSF_DEVICE': 'cuda', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8', 'PYTHONUNBUFFERED': '1'}\n"
         "PROCS = max(1, min(4, os.cpu_count()))   # trainings at once on the GPU (one CPU each)\n"
         "print('mirror commit', man['commit'], '| files', len(man['sha256']), '| GPU', torch.cuda.get_device_name(0),\n"
         "      '| CPUs', os.cpu_count(), '| processes', PROCS, '| torch', torch.__version__, '| numpy', numpy.__version__,\n"
         "      '| pandas', pandas.__version__)\n"
         "\n"
         "def step(*args, check=True):\n"
         "    t = time.time()\n"
         "    p = subprocess.Popen([sys.executable, '-u', 'tools/nb6_gpu.py', *args], cwd=ROOT, env=ENV,\n"
         "                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
         "    for line in p.stdout:\n"
         "        print(line, end='', flush=True)\n"
         "    rc = p.wait()\n"
         "    assert rc == 0 or not check, f'{args} failed (see above)'\n"
         "    print(f'--- {\" \".join(args)} done in {(time.time() - t) / 60:.1f} min (exit {rc})', flush=True)\n"
         "    return rc\n"
         "\n"
         "def gate_passed(ref):\n"
         "    g = ROOT / 'results' / 'nb6_gpu_val' / ref / 'GATE.json'\n"
         "    return g.exists() and json.loads(g.read_text())['passed']"),
    md("Validation rounds (150 trainings each), then the gates. V12's gate stops the notebook if the GPU is not level "
       "with the CPU; TimeXer's gate decides only where A6d runs."),
    code("step('--validate', '--ref', 'V12_5s', '--procs', str(PROCS))\n"
         "step('--validate', '--ref', 'TX1_5s', '--procs', str(PROCS))\n"
         "step('--gate', '--ref', 'V12_5s')                  # stops here if it fails\n"
         "step('--gate', '--ref', 'TX1_5s', check=False)\n"
         "TX1_OK = gate_passed('TX1_5s')\n"
         "print('V12 gate passed:', gate_passed('V12_5s'), '| TimeXer gate passed:', TX1_OK)"),
    md("Projected GPU time of every row, from the validation trainings' GPU run times (the gates' projection)."),
    code("import pandas as pd\n"
         "G = [ROOT / 'results' / 'nb6_gpu_val' / r / 'GATE.json' for r in ['V12_5s', 'TX1_5s']]\n"
         "P = pd.concat([pd.DataFrame(json.loads(g.read_text())['projection']) for g in G if g.exists()], ignore_index=True)\n"
         "rows_here = ['main', 'A2', 'A4c', 'A6e'] + (['A6d'] if TX1_OK else []) + ['tb_main']\n"
         "P = P.set_index('row').loc[rows_here]\n"
         "print(P[['trainings', 'gpu_training_hours', 'processes', 'wall_hours', 'longest_training_h']].to_string())\n"
         "print(f'expected GPU wall time for these rows: {P.wall_hours.sum():.1f} h')"),
    md("The test rows, longest trainings first, in the author's order. Each row prints its mean training time."),
    code("for row in ['main', 'A2', 'A4c', 'A6e', 'A6d', 'tb_main']:\n"
         "    if row == 'A6d' and not TX1_OK:\n"
         "        print('A6d: the TimeXer gate did not pass, so A6d runs on the laptop CPU (not here)')\n"
         "        continue\n"
         "    step('--row', row, '--procs', str(PROCS))"),
    code("drive.flush_and_unmount()\n"
         "print('done: on the laptop run python tools/fetch_drive_runs.py --set nb6gpu')"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["accelerator"] = "GPU"
nbf.write(nb, ROOT / "notebooks" / "NB6_gpu.ipynb")
print("wrote notebooks/NB6_gpu.ipynb")
