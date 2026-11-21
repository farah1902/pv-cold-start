"""Generate the three NB5b notebooks: zero-shot foundation models on the validation units (development; D23, D59).

  NB5b_inputs.ipynb      local, main environment: the index series and NB5a's issue times -> results/nb5b_inputs/
  NB5b_colab.ipynb       Colab GPU (or locally with .venv_fm): the settings grid -> results/nb5b_runs/
  NB5b_foundation.ipynb  local, main environment: scores on NB5a's slots, the setting per model, the comparison
                         with the 5-seed ensembles of LightGBM, PVSetFormer (the candidate V9, D60) and TimeXer
                         -> results/nb5b_fm/

    python tools/make_nb5b.py [--only NB5b_foundation ...]   (default: all three)
"""
import argparse
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
KERNEL = {"name": "python3", "display_name": "Python 3", "language": "python"}
# The settings grid, fixed before any foundation-model forecast is scored (D59): context in daylight steps (48 a day,
# so 7 and 28 days) x covariates (the guide's interface, or none as a check of what the covariates add).
GRID = [(m, c, cov) for m in ("chronos2", "timesfm25") for c in (336, 1344) for cov in ("full", "none")]

SETUP = ("import os, sys, time, json, hashlib\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd\n"
         "ROOT = Path.cwd().resolve()\n"
         "ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'tools'))\n"
         "from pvcold import config as C, audit as A, forecast as FC\n"
         "import r1_score as R                      # NB5a context and slots (D37)\n"
         "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 40)\n"
         "t0 = time.time()\n")

# --- 1. inputs ----------------------------------------------------------------------------------------------------
nb1 = nbf.v4.new_notebook()
nb1.cells = [
    md("# NB5b (1/3) — inputs for the foundation models (development)\n\n"
       "D23, D59; guide §5.4 rows A6a–A6c. The 10 validation units and the issue times NB5a forecast. For each unit: the "
       "event's index k, the fleet state (σ, c, n) and the sun geometry u on the 15-min grid, from the fleet's start "
       "(2021-05-15, LightGBM's first training day) to two days after the last issue time. Writes "
       "`results/nb5b_inputs/` (series.parquet and tasks.parquet, git-ignored; inputs_manifest.json with their sha256, "
       "tracked). The foundation models read only these files."),
    code(SETUP +
         "ctx = R.load_context()\n"
         "VAL, fc5, idx, geo15, E = ctx['VAL'], ctx['fc5'], ctx['idx'], ctx['geo15'], ctx['E']\n"
         "COLS = ['minute', 'k', 'sigma', 'c', 'n', 'Gt', 'cosz', 'sin_az', 'cos_az', 'sin_ha', 'cos_ha', 'sin_doy', 'cos_doy']\n"
         "tasks = fc5[['event', 'origin', 't']].drop_duplicates().sort_values(['event', 't']).reset_index(drop=True)\n"
         "assert set(tasks.event) == set(VAL) and all(E.loc[v, 'set'] == 'validation' for v in VAL)\n"
         "parts, chk = [], []\n"
         "for v in VAL:\n"
         "    S = FC.event_series(v, idx, geo15)\n"
         "    t_last = tasks.loc[tasks.event == v, 't'].max()\n"
         "    S = S.loc[FC.TRAIN_START:t_last.normalize() + pd.Timedelta(days=2) - pd.Timedelta(minutes=15)]\n"
         "    day = (S['minute'] >= 360) & (S['minute'] <= FC.LAST_TARGET_MIN)\n"
         "    chk.append({'event': v, 'rows': len(S), 'k_outside_daylight': int(np.isfinite(S.loc[~day, 'k']).sum()),\n"
         "                'Gt_missing_in_daylight': int(S.loc[day, 'Gt'].isna().sum()), 'tasks': int((tasks.event == v).sum())})\n"
         "    out = S[COLS].copy(); out.insert(0, 'time', S.index); out.insert(0, 'event', v)\n"
         "    parts.append(out.reset_index(drop=True))\n"
         "series = pd.concat(parts, ignore_index=True)\n"
         "chk = pd.DataFrame(chk); print(chk.to_string(index=False))\n"
         "assert (chk.k_outside_daylight == 0).all() and (chk.Gt_missing_in_daylight == 0).all()\n"
         "print('series', series.shape, '| tasks', len(tasks))"),
    code("OUT = C.RESULTS / 'nb5b_inputs'; TMP = C.RESULTS / '.tmp_nb5b_inputs'\n"
         "import shutil\n"
         "if TMP.exists(): shutil.rmtree(TMP)\n"
         "TMP.mkdir(parents=True)\n"
         "series.to_parquet(TMP / 'series.parquet'); tasks.to_parquet(TMP / 'tasks.parquet')\n"
         "man = {'notebook': 'NB5b_inputs', 'environment': A.versions(), 'runtime_s': round(time.time() - t0, 1),\n"
         "       'events': VAL, 'n_series_rows': len(series), 'n_tasks': len(tasks),\n"
         "       'sha256': {f: hashlib.sha256((TMP / f).read_bytes()).hexdigest() for f in ['series.parquet', 'tasks.parquet']}}\n"
         "(TMP / 'inputs_manifest.json').write_bytes(json.dumps(man, indent=2, default=str).encode('utf-8'))\n"
         "if OUT.exists(): shutil.rmtree(OUT)\n"
         "TMP.rename(OUT)\n"
         "print(json.dumps(man['sha256'], indent=1)); print('written to', OUT)"),
]

# --- 2. inference (Colab or local) -------------------------------------------------------------------------------
nb2 = nbf.v4.new_notebook()
nb2.cells = [
    md("# NB5b (2/3) — foundation-model forecasts (Colab GPU, or locally with `.venv_fm`)\n\n"
       "D23, D59. Runs `tools/fm_infer.py` for each setting of the grid and writes `results/nb5b_runs/<model>_c<context>_"
       "<covariates>.parquet` with a JSON record (versions, weights revision, input hashes, run time). Resumable: a "
       "setting whose output exists for the current inputs is skipped.\n\n"
       "**On Colab:** the Drive mirror of the repository must hold `tools/fm_infer.py`, `src/pvcold/` , "
       "`requirements-fm.txt` and `results/nb5b_inputs/` (from NB5b_inputs). Choose a GPU runtime, set `DRIVE_REPO`, run "
       "all cells, then copy `results/nb5b_runs/` back to the local repository (the master copy). End with "
       "`drive.flush_and_unmount()` (last cell) and Ctrl+S.\n\n"
       "**Locally:** the separate environment `.venv_fm` (`requirements-fm.txt`) runs on the CPU; slow (Chronos-2 about "
       "0.3 issue times per second under load)."),
    code("import os, sys, json, hashlib, subprocess, time\n"
         "from pathlib import Path\n"
         "ON_COLAB = 'google.colab' in sys.modules\n"
         "DRIVE_REPO = '/content/drive/MyDrive/pv-cold-start'\n"
         "if ON_COLAB:\n"
         "    from google.colab import drive\n"
         "    drive.mount('/content/drive')\n"
         "    ROOT, PY, DEVICE = Path(DRIVE_REPO), sys.executable, 'cuda'\n"
         "    subprocess.run([PY, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements-fm.txt')], check=True)\n"
         "else:\n"
         "    ROOT = Path.cwd().resolve(); ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "    PY = str(ROOT / '.venv_fm' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')); DEVICE = 'cpu'\n"
         "INP, RUNS = ROOT / 'results' / 'nb5b_inputs', ROOT / 'results' / 'nb5b_runs'\n"
         "man = json.loads((INP / 'inputs_manifest.json').read_text())\n"
         "for f, h in man['sha256'].items():\n"
         "    assert hashlib.sha256((INP / f).read_bytes()).hexdigest() == h, f'{f} differs from its manifest'\n"
         f"GRID = {GRID!r}\n"
         "print('ROOT', ROOT, '| device', DEVICE, '| settings', len(GRID))"),
    code("log = []\n"
         "for model, L, cov in GRID:\n"
         "    out = RUNS / f'{model}_c{L}_{cov}.parquet'\n"
         "    js = out.with_suffix('.json')\n"
         "    if out.exists() and js.exists() and json.loads(js.read_text())['inputs_sha256'] == man['sha256']:\n"
         "        log.append({'setting': out.stem, 'status': 'done before', **{k: json.loads(js.read_text())[k] for k in ('runtime_s', 'n_rows')}})\n"
         "        continue\n"
         "    t1 = time.time()\n"
         "    r = subprocess.run([PY, str(ROOT / 'tools' / 'fm_infer.py'), '--model', model, '--context', str(L), '--cov', cov,\n"
         "                        '--inputs', str(INP), '--out', str(out), '--device', DEVICE], cwd=str(ROOT))\n"
         "    assert r.returncode == 0, f'{out.stem} failed'\n"
         "    log.append({'setting': out.stem, 'status': 'run', 'runtime_s': round(time.time() - t1, 1),\n"
         "                'n_rows': json.loads(js.read_text())['n_rows']})\n"
         "    print(log[-1], flush=True)\n"
         "print(log)"),
    code("if ON_COLAB:\n"
         "    drive.flush_and_unmount()"),
]

# --- 3. scores and the choice of setting ---------------------------------------------------------------------------
nb3 = nbf.v4.new_notebook()
nb3.cells = [
    md("# NB5b (3/3) — foundation models on the validation units: scores and settings (development)\n\n"
       "D23, D59; guide §5.4 rows A6a (Chronos-2) and A6b (TimesFM 2.5). Each run of the grid is composed with the "
       "frozen prior and scored on exactly NB5a's slots (`r1_score.score`). **Setting per model (rule fixed before any "
       "score, D59):** the lowest median nRMSE at 1 h over the 10 units. The chosen settings are compared with the "
       "5-seed ensembles of LightGBM, PVSetFormer (the candidate V9, D60) and TimeXer on the same slots (paired by unit). Writes "
       "`results/nb5b_fm/` with `fm_config_part2d.yaml`."),
    code(SETUP +
         "from scipy.stats import wilcoxon\n"
         "import yaml\n"
         "ctx = R.load_context()\n"
         "INP, RUNS, VD = C.RESULTS / 'nb5b_inputs', C.RESULTS / 'nb5b_runs', C.RESULTS / 'nb5c_variants'\n"
         "man = json.loads((INP / 'inputs_manifest.json').read_text())\n"
         f"GRID = {GRID!r}\n"
         "REFS = {'LightGBM': 'LGB_seeds', 'PVSetFormer': 'V9_5s', 'TimeXer': 'TX1_5s'}\n"
         "info = {}\n"
         "for model, L, cov in GRID:\n"
         "    s = f'{model}_c{L}_{cov}'\n"
         "    info[s] = json.loads((RUNS / f'{s}.json').read_text())\n"
         "    assert info[s]['inputs_sha256'] == man['sha256'], f'{s} was run on other inputs'\n"
         "    assert info[s]['limit'] == 0, f'{s} is a smoke test'\n"
         "print(pd.DataFrame({s: {k: i[k] for k in ('model', 'context', 'cov', 'device', 'runtime_s', 'n_rows')} for s, i in info.items()}).T)"),
    md("## Scores of every setting on NB5a's slots"),
    code("rows = []\n"
         "for s, i in info.items():\n"
         "    fc = pd.read_parquet(RUNS / f'{s}.parquet')\n"
         "    sc = R.score(fc, ctx)                       # asserts every NB5a slot is forecast\n"
         "    sc = sc[sc.seed == 1].assign(setting=s, model=i['model'], context=i['context'], cov=i['cov'])\n"
         "    rows.append(sc)\n"
         "SC = pd.concat(rows, ignore_index=True)\n"
         "MED = SC.groupby(['setting', 'model', 'context', 'cov', 'h'])[R.METRICS].median().reset_index()\n"
         "print(MED.pivot_table(index=['model', 'context', 'cov'], columns='h', values='nRMSE').round(4))"),
    md("## The setting per model (lowest median nRMSE at 1 h)"),
    code("H1 = C.PRIMARY_HORIZON\n"
         "m1 = MED[MED.h == H1].sort_values('nRMSE')\n"
         "CHOSEN = {m: g.iloc[0]['setting'] for m, g in m1.groupby('model')}\n"
         "print(m1[['setting', 'nRMSE', 'CRPS', 'PICP80']].to_string(index=False)); print('chosen:', CHOSEN)"),
    md("## Chosen settings against the 5-seed ensembles, paired by unit on the same slots"),
    code("ref = {n: pd.read_csv(VD / d / 'scores.csv').query('seed == 0') for n, d in REFS.items()}\n"
         "cmp = []\n"
         "for m, s in CHOSEN.items():\n"
         "    a = SC[SC.setting == s].set_index(['event', 'h'])\n"
         "    for n, r in ref.items():\n"
         "        b = r.set_index(['event', 'h']).reindex(a.index)\n"
         "        assert (b['n'] == a['n']).all(), 'not the same slots'\n"
         "        for h in FC.H:\n"
         "            x, y = a.xs(h, level='h'), b.xs(h, level='h')\n"
         "            d = (x.nRMSE - y.nRMSE).to_numpy()\n"
         "            cmp.append({'fm': m, 'setting': s, 'reference': n, 'h': h, 'nRMSE_fm': x.nRMSE.median(),\n"
         "                        'nRMSE_ref': y.nRMSE.median(), 'rel_pct': 100 * float(np.median(x.nRMSE / y.nRMSE - 1)),\n"
         "                        'units_fm_better': int((d < 0).sum()), 'CRPS_fm': x.CRPS.median(), 'CRPS_ref': y.CRPS.median(),\n"
         "                        'wilcoxon_p': float(wilcoxon(d).pvalue) if np.any(d != 0) else np.nan})\n"
         "CMP = pd.DataFrame(cmp)\n"
         "print(CMP[CMP.h.isin([1, 4, 24])].round(4).to_string(index=False))"),
    md("## Draft figure"),
    code("import matplotlib.pyplot as plt\n"
         "A._style()\n"
         "fig, ax = plt.subplots(1, 1, figsize=(3.6, 2.8))\n"
         "hx = np.array(FC.H) * 0.25\n"
         "sty = {'LightGBM': ('0.2', 'o'), 'PVSetFormer': ('#1f4e79', 's'), 'TimeXer': ('#7d6608', '^')}\n"
         "for n, (c, mk) in sty.items():\n"
         "    z = ref[n].groupby('h').nRMSE.median().reindex(FC.H)\n"
         "    ax.plot(hx, z, color=c, marker=mk, ms=3, lw=1, label=n + ' (5 seeds)')\n"
         "for (m, s), (c, mk) in zip(CHOSEN.items(), [('#b03a2e', 'D'), ('#5b2c6f', 'v')]):\n"
         "    z = MED[MED.setting == s].set_index('h').nRMSE.reindex(FC.H)\n"
         "    ax.plot(hx, z, color=c, marker=mk, ms=3, lw=1, label=s)\n"
         "ax.set_xscale('log'); ax.set_xticks(hx); ax.set_xticklabels(['0.25', '0.5', '1', '2', '4', '6'])\n"
         "ax.set_xlabel('Horizon (h)'); ax.set_ylabel('Median nRMSE'); ax.legend(frameon=False, fontsize=6)\n"
         "ax.set_title('10 validation units', fontsize=7); fig.tight_layout()"),
    md("## Outputs (all-or-nothing): scores, medians, comparison, configuration part 2d"),
    code("cfg = {'part': '2d', 'decision': 'D59', 'rule': 'lowest median validation nRMSE at 1 h per model',\n"
         "       'inputs_sha256': man['sha256'],\n"
         "       'models': {m: {k: info[s][k] for k in ('weights', 'context', 'cov', 'grid', 'prediction_length', 'versions')}\n"
         "                  | {'setting': s, 'revision': info[s].get('revision'), 'forecast_config': info[s].get('forecast_config'),\n"
         "                     'xreg': info[s].get('xreg')} for m, s in CHOSEN.items()}}\n"
         "CFG_TEXT = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)\n"
         "summary = {'notebook': 'NB5b_foundation', 'environment': A.versions(), 'runtime_s': round(time.time() - t0, 1),\n"
         "           'grid': [s for s in info], 'chosen': CHOSEN,\n"
         "           'fm_config_sha256': hashlib.sha256(CFG_TEXT.encode()).hexdigest(),\n"
         "           'median_nRMSE_1h': m1.set_index('setting')['nRMSE'].round(5).to_dict(),\n"
         "           'vs_refs_1h': CMP[CMP.h == H1].set_index(['fm', 'reference'])[['rel_pct', 'units_fm_better', 'wilcoxon_p']]\n"
         "                         .round(4).reset_index().to_dict('records'),\n"
         "           'run_info': info}\n"
         "out = A.write_outputs('nb5b_fm', {'scores': SC, 'medians': MED, 'comparison': CMP}, summary, {'fig_fm': fig},\n"
         "                      texts={'fm_config_part2d.yaml': CFG_TEXT})\n"
         "print(json.dumps({k: summary[k] for k in ('chosen', 'median_nRMSE_1h')}, indent=1))\n"
         "print('written to', out, '|', sorted(x.name for x in out.iterdir()))"),
]

NAMES = ["NB5b_inputs", "NB5b_colab", "NB5b_foundation"]
ap = argparse.ArgumentParser()
ap.add_argument("--only", nargs="*", choices=NAMES, default=NAMES, help="notebooks to write (the others keep outputs)")
ONLY = ap.parse_args().only
for nb, name in zip([nb1, nb2, nb3], NAMES):
    if name not in ONLY:
        continue
    nb.metadata["kernelspec"] = KERNEL
    nbf.write(nb, ROOT / "notebooks" / f"{name}.ipynb")
    print(f"wrote notebooks/{name}.ipynb")
