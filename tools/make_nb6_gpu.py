"""Generate notebooks/NB6_gpu.ipynb (D80): PVSetFormer's test rows A4c, A2 and the test bed's main on a Colab GPU,
after a validation round and its gate. Mirror with `python tools/make_drive_mirror.py --set nb6gpu` (after committing);
fetch back with `python tools/fetch_drive_runs.py --set nb6gpu`, then re-run `python tools/nb6_gpu.py --gate` locally.

The notebook copies the mirror to the Colab disk (every file checked against MIRROR_MANIFEST.json), keeps its outputs
on Drive (results/nb6_forecasts/parts and results/nb6_gpu_val are links to the mirror, so a disconnect loses only the
trainings in flight), and runs tools/nb6_gpu.py with PVSF_DEVICE=cuda: --validate, --gate (stops if it fails),
then --row A4c, A2, tb_main. Resumable: run all cells again after a disconnect; finished trainings are skipped.
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
    md("# NB6 (Colab GPU) — PVSetFormer's test rows A4c, A2 and the test bed's main\n\n"
       f"D80, after the protocol freeze (frozen configuration `{FZ_HASH[:16]}…`). The laptop's 4 cores would need about "
       "6 days for these rows; the main row, A6e and A6d stay on its CPU. Same model, inputs, settings and seeds; only "
       "the device differs. First a validation round (V12 on the 10 validation units, the 5 frozen seeds) and its gate: "
       "the GPU ensemble must be level with the CPU one (under 3% at every horizon) and the per-seed medians within "
       "3 standard errors. Only then the test rows.\n\n"
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
         "def step(*args):\n"
         "    t = time.time()\n"
         "    p = subprocess.Popen([sys.executable, '-u', 'tools/nb6_gpu.py', *args], cwd=ROOT, env=ENV,\n"
         "                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\n"
         "    for line in p.stdout:\n"
         "        print(line, end='', flush=True)\n"
         "    assert p.wait() == 0, f'{args} failed (see above)'\n"
         "    print(f'--- {\" \".join(args)} done in {(time.time() - t) / 60:.1f} min', flush=True)"),
    md("Validation round (150 trainings), then the gate. The gate stops the notebook if the GPU is not level with "
       "the CPU."),
    code("step('--validate', '--procs', str(PROCS))\n"
         "step('--gate')"),
    md("The test rows, longest trainings first. Each row prints its mean training time."),
    code("for row in ['A4c', 'A2', 'tb_main']:\n"
         "    step('--row', row, '--procs', str(PROCS))"),
    code("drive.flush_and_unmount()\n"
         "print('done: on the laptop run python tools/fetch_drive_runs.py --set nb6gpu')"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["accelerator"] = "GPU"
nbf.write(nb, ROOT / "notebooks" / "NB6_gpu.ipynb")
print("wrote notebooks/NB6_gpu.ipynb")
