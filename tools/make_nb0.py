"""Generate notebooks/NB0_setup_config.ipynb. Run: python tools/make_nb0.py, then execute the notebook."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
    md("# NB0 — Environment, paths and configuration\n\n"
       "Checks the environment, verifies the data against `data/MANIFEST_sha256.csv`, and writes "
       "`results/nb0_setup/` (config snapshot, environment, summary). Runs locally or on Colab.\n\n"
       "On Colab: set `DRIVE_REPO` below to the Drive mirror of the repository before running."),
    code("import os, sys, json, time, subprocess, importlib\n"
         "from pathlib import Path\n"
         "ON_COLAB = 'google.colab' in sys.modules\n"
         "DRIVE_REPO = '/content/drive/MyDrive/pv-cold-start'\n"
         "if ON_COLAB:\n"
         "    from google.colab import drive\n"
         "    drive.mount('/content/drive')\n"
         "    os.environ['PVCOLD_ROOT'] = DRIVE_REPO\n"
         "    ROOT = Path(DRIVE_REPO)\n"
         "else:\n"
         "    ROOT = Path.cwd().resolve()\n"
         "    ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "from pvcold import config as C, audit as A\n"
         "t0 = time.time()\n"
         "print('ROOT =', C.ROOT, '| on Colab:', ON_COLAB)"),
    md("## Versions\nLightGBM must be 4.6.0 (4.7.0 crashed on the author's Windows machine). The foundation-model "
       "packages are only needed on Colab (NB5b)."),
    code("env = A.versions()\n"
         "env['on_colab'] = ON_COLAB\n"
         "for pkg in ['chronos-forecasting', 'timesfm', 'tabpfn-time-series', 'tabpfn']:\n"
         "    try:\n"
         "        from importlib.metadata import version, metadata\n"
         "        env[pkg] = {'version': version(pkg), 'license': metadata(pkg).get('License')}\n"
         "    except Exception as e:\n"
         "        env[pkg] = f'not installed ({type(e).__name__})'\n"
         "try:\n"
         "    import torch\n"
         "    env['cuda'] = torch.cuda.is_available()\n"
         "    env['gpu'] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None\n"
         "except Exception:\n"
         "    env['cuda'] = False\n"
         "assert env['lightgbm'] == '4.6.0', f\"lightgbm {env['lightgbm']} (expected 4.6.0)\"\n"
         "for k, v in env.items():\n"
         "    print(f'{k:22s} {v}')"),
    md("## Data integrity\nEvery input file is compared with the committed SHA-256 manifest (D15)."),
    code("res = subprocess.run([sys.executable, str(C.ROOT / 'tools' / 'make_data_manifest.py'), '--check'],\n"
         "                     capture_output=True, text=True)\n"
         "print(res.stdout[-2000:], res.stderr[-2000:])\n"
         "manifest_ok = res.returncode == 0\n"
         "assert manifest_ok, 'the data on disk differ from data/MANIFEST_sha256.csv'"),
    md("## Configuration snapshot\nAll constants of `src/pvcold/config.py` (guide §2–§3, D08–D12). Tuned values are "
       "added later to the frozen configuration (D21)."),
    code("import yaml\n"
         "cfg = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(C).items()\n"
         "       if k.isupper() and not k.startswith('_')}\n"
         "cfg = {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}\n"
         "text = yaml.safe_dump(cfg, sort_keys=True, allow_unicode=True)\n"
         "print(text[:1500])"),
    code("summary = {'notebook': 'NB0_setup_config', 'environment': env, 'manifest_ok': manifest_ok,\n"
         "           'seed': C.SEED, 'runtime_s': round(time.time() - t0, 1)}\n"
         "out = C.RESULTS / '.tmp_nb0_setup'\n"
         "import shutil\n"
         "if out.exists(): shutil.rmtree(out)\n"
         "out.mkdir(parents=True)\n"
         "(out / 'config_snapshot.yaml').write_text(text, encoding='utf-8')\n"
         "(out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')\n"
         "final = C.RESULTS / 'nb0_setup'\n"
         "if final.exists(): shutil.rmtree(final)\n"
         "out.rename(final)\n"
         "print('written:', sorted(p.name for p in final.iterdir()))\n"
         "if ON_COLAB:\n"
         "    drive.flush_and_unmount()"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
(ROOT / "notebooks").mkdir(exist_ok=True)
nbf.write(nb, ROOT / "notebooks" / "NB0_setup_config.ipynb")
print("wrote notebooks/NB0_setup_config.ipynb")
