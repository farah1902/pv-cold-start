"""Generate notebooks/NB5c_conformal.ipynb: the conformal layer of D35 applied to the main index forecaster chosen
by rule R1 (PVSetFormer, D45). Run after NB5c_R1_decision. Development data only (the 10 validation units).

    python tools/make_nb5c_conformal.py               # PVSetFormer's 5-seed ensemble -> NB5c_conformal.ipynb
    python tools/make_nb5c_conformal.py --model lgb   # LightGBM's 5-seed ensemble (D64) -> NB5c_conformal_lgb.ipynb

The LightGBM notebook reads LGB_seeds' forecasts and the calibration set of tools/lgb_seeds_cal.py; every rule and
every cell after the setup is the same, except the reference table, the figure title and the output names."""
import argparse
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
    md("# NB5c conformal — calibrated intervals for PVSetFormer (validation units only)\n\n"
       "D06, D35, D45. Rule R1 chose PVSetFormer as the main index forecaster (`results/nb5c_r1/`, configuration part "
       "2c). The conformal layer of D35 was built for LightGBM; this notebook applies **the same rules, unchanged**, "
       "to PVSetFormer's 5-seed ensemble. Reads `results/nb5c_r1/` and the final variant's folder in "
       "`results/nb5c_variants/`; writes `results/nb5c_conformal/`. No test event is used.\n\n"
       "**Rules (D35, fixed before any number below):**\n"
       "1. *Calibration set*, per event, origin and horizon: pseudo cold starts of the event's donors (clean-metadata "
       "donors for a G1/G2 target, all donors for a G0 target). Their index is forecast by the early-stopped models on "
       "the last 20% of the training issue times (out of sample for those models, targets before the origin), here "
       "the 5-seed ensemble of these predictions, built like the forecasts (mean of the sorted quantiles, sorted "
       "again), and composed with each donor's leave-one-out prior and uncertainty set (200 members).\n"
       "2. *Conformity*: CQR (Romano et al. 2019) per horizon and per central interval (80, 60, 40 and 20%), "
       "normalised by G̃(t + h). The correction is the ⌈(1 − α)(n + 1)⌉-th smallest score; under 50 scores, none.\n"
       "3. *Use*: applied to the main model's 9 power quantiles; the median and the point forecast are unchanged.\n"
       "4. *Keep rule*: the layer is kept if, on the validation units, it brings the median PICP80 at 1 h closer to "
       "0.80 than the raw forecast and does not raise the median IS80 at 1 h."),
    code("import os, sys, time, json, hashlib\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd, yaml\n"
         "ROOT = Path.cwd().resolve()\n"
         "ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'tools'))\n"
         "from pvcold import config as C, audit as A, fleet as F, forecast as FC\n"
         "import r1_score as R                      # the scoring shared by rule R1 (D37)\n"
         "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 40)\n"
         "t0 = time.time()\n"
         "r1 = json.loads((C.RESULTS / 'nb5c_r1' / 'summary.json').read_text())\n"
         "P2C_TEXT = (C.RESULTS / 'nb5c_r1' / 'r1_config_part2c.yaml').read_bytes().decode('utf-8')\n"
         "assert hashlib.sha256(P2C_TEXT.encode()).hexdigest() == r1['part2c_sha256'], 'configuration part 2c changed'\n"
         "P2C = yaml.safe_load(P2C_TEXT)\n"
         "assert P2C['main_index_forecaster'] == 'PVSetFormer' and r1['pvsf_main']\n"
         "VAR = P2C['pvsetformer_variant']; VDIR = C.RESULTS / 'nb5c_variants' / VAR\n"
         "assert hashlib.sha256((VDIR / 'summary.json').read_bytes()).hexdigest() == r1['pvsf_summary_sha256'], 'variant folder changed'\n"
         "ctx = R.load_context()\n"
         "p, E, U, geo15, gains3 = ctx['p'], ctx['E'], ctx['U'], ctx['geo15'], ctx['gains3']\n"
         "PRIOR, ALT, VAL, fc5 = ctx['PRIOR'], ctx['ALT'], ctx['VAL'], ctx['fc5']\n"
         "QC = R.QC\n"
         "lv, gl = FC.member_levels()\n"
         "def ensemble(x):\n"
         "    n = x.groupby(['event', 'origin', 'h', 't'])['seed'].nunique()\n"
         "    assert sorted(x.seed.unique().tolist()) == P2C['seeds'] and (n == len(P2C['seeds'])).all(), 'seeds differ'\n"
         "    e = R.with_ensemble(x.drop(columns='model'))\n"
         "    return e[e.seed == 0].drop(columns='seed').reset_index(drop=True)\n"
         "fc = ensemble(pd.read_parquet(VDIR / 'forecasts.parquet'))\n"
         "cal = ensemble(pd.read_parquet(VDIR / 'calibration.parquet'))\n"
         "print('variant', VAR, '| seeds', P2C['seeds'], '| prior', PRIOR)\n"
         "print('ensemble rows: forecasts %d, calibration %d' % (len(fc), len(cal)))"),
    md("## Conformity scores of the donors' pseudo cold starts, and the corrections"),
    code("Tcache, crow, ev_gain = {}, [], {}\n"
         "for v in VAL:\n"
         "    a = F.event_arrays(v, p)\n"
         "    g = gains3[gains3.event == v].set_index('donor')['gain'].reindex(a['dn'])\n"
         "    pr, T_don, r_don, meta_ok = F.event_priors(a, g, U, ALT, Tcache)\n"
         "    variant = PRIOR if pr['target_in_prior_test'] else 'G0'\n"
         "    B = np.asarray(pr['B_' + variant]) if variant != 'G0' else g.dropna().to_numpy()\n"
         "    ev_gain[v] = FC.gain_members(pr[variant], B / np.median(B), gl)\n"
         "    pp = FC.pseudo_priors(g, r_don, T_don, meta_ok, variant)\n"
         "    for (o, h), x in cal[cal.event == v].groupby(['origin', 'h']):\n"
         "        tgt = x['t'] + pd.Timedelta(minutes=15 * h)\n"
         "        gtt = geo15['Gt'].reindex(tgt).to_numpy(); Qi = x[QC].to_numpy(dtype=float)\n"
         "        Es = []\n"
         "        for d, (g0, Brel) in pp.items():\n"
         "            yd = p['y15'][d].reindex(tgt).to_numpy(); ok = np.isfinite(yd)\n"
         "            Y = FC.power_members(Qi[ok], gtt[ok], FC.gain_members(g0, Brel, gl), lv)\n"
         "            Es.append(FC.conformity(FC.power_quantiles(Y), yd[ok], gtt[ok]))\n"
         "        Eall = np.vstack(Es)\n"
         "        corr = FC.conformal_correction(Eall)\n"
         "        crow.append({'event': v, 'origin': o, 'h': h, 'variant': variant, 'n_donors': len(pp), 'n_scores': len(Eall),\n"
         "                     'cal_days': int(x['t'].dt.normalize().nunique()),\n"
         "                     **{f'raw_cover{n}': float(np.mean(Eall[:, j] <= 0)) for j, n in enumerate(FC.PAIR_NAMES)},\n"
         "                     **{f'corr{n}': float(corr[j]) for j, n in enumerate(FC.PAIR_NAMES)}})\n"
         "corrs = pd.DataFrame(crow)\n"
         "print('variants of the prior:', corrs.groupby('variant').event.nunique().to_dict())\n"
         "print('raw coverage of the pseudo cold starts and corrections (median over units and origins):')\n"
         "print(corrs.groupby('h')[[c for c in corrs.columns if c.startswith(('raw_cover', 'corr', 'n_scores', 'cal_days'))]].median().round(3).to_string())\n"
         "print('groups with fewer than %d scores (no correction): %d of %d' % (FC.MIN_CAL, int((corrs.n_scores < FC.MIN_CAL).sum()), len(corrs)))"),
    md("## Validation units (true cold starts): raw against conformal intervals\n"
       "Same scored slots as NB5a and rule R1 (every NB5a model has a forecast and the observation exists)."),
    code("cidx = corrs.set_index(['event', 'origin', 'h'])\n"
         "srows = []\n"
         "for v in VAL:\n"
         "    assert E.loc[v, 'set'] == 'validation'      # target power is read for validation units only\n"
         "    f5 = fc5[fc5.event == v].copy()\n"
         "    f5['target'] = f5['t'] + pd.to_timedelta(15 * f5['h'], unit='min')\n"
         "    f5['y'] = p['y15'][E.loc[v, 'units']].reindex(f5['target']).to_numpy()\n"
         "    good = f5[QC].notna().all(axis=1) & np.isfinite(f5['y'])\n"
         "    cnt = f5[good].groupby(['h', 't'])['model'].nunique()\n"
         "    keys = cnt[cnt == f5.model.nunique()].index\n"
         "    f = fc[fc.event == v].set_index(['h', 't']).loc[lambda x: x.index.isin(keys)].reset_index()\n"
         "    f['target'] = f['t'] + pd.to_timedelta(15 * f['h'], unit='min')\n"
         "    f['y'] = p['y15'][E.loc[v, 'units']].reindex(f['target']).to_numpy()\n"
         "    f['gt'] = geo15['Gt'].reindex(f['target']).to_numpy()\n"
         "    for h, xh in f.groupby('h'):\n"
         "        assert len(xh) == int((keys.get_level_values(0) == h).sum()), 'missing scored slots'\n"
         "        parts = {'raw': [], 'conformal': []}; ys, tm = [], []\n"
         "        for o, x in xh.groupby('origin'):\n"
         "            gt_ = x['gt'].to_numpy()\n"
         "            Qp = FC.power_quantiles(FC.power_members(x[QC].to_numpy(dtype=float), gt_, ev_gain[v], lv))\n"
         "            corr = cidx.loc[(v, o, h), [f'corr{n}' for n in FC.PAIR_NAMES]].to_numpy(dtype=float)\n"
         "            parts['raw'].append(Qp); parts['conformal'].append(FC.apply_conformal(Qp, gt_, corr))\n"
         "            ys.append(x['y'].to_numpy()); tm.append((x['target'].dt.hour * 60 + x['target'].dt.minute).to_numpy())\n"
         "        y_, tm_ = np.concatenate(ys), np.concatenate(tm)\n"
         "        for kind, Qs in parts.items():\n"
         "            Qa = np.vstack(Qs)\n"
         "            for win, msk in [('full', np.ones(len(y_), bool)), ('common', tm_ >= FC.COMMON_WINDOW_MIN)]:\n"
         "                srows.append({'event': v, 'h': h, 'kind': kind, 'window': win, **FC.quantile_scores(Qa[msk], y_[msk], lv)})\n"
         "vs = pd.DataFrame(srows)\n"
         "r1sc = pd.read_csv(VDIR / 'scores.csv').query('seed == 0').set_index(['event', 'h'])['PICP80']\n"
         "chk = vs[(vs.kind == 'raw') & (vs.window == 'full')].set_index(['event', 'h'])['cover80']\n"
         "CHK = float((chk - r1sc.reindex(chk.index)).abs().max())\n"
         "print('raw PICP80 equals the R1 scores of the ensemble: max |diff| = %.1e' % CHK)\n"
         "assert CHK < 1e-9\n"
         "MET = ['cover80', 'cover60', 'cover40', 'cover20', 'PINAW', 'IS80', 'CRPS_q']\n"
         "vm = vs.groupby(['window', 'kind', 'h'])[MET].median().reset_index()\n"
         "for met in MET:\n"
         "    print(f'median {met}, full window:'); print(vm[vm.window == 'full'].pivot(index='kind', columns='h', values=met).round(4).to_string())"),
    md("## Keep rule (rule 4), and LightGBM's layer for reference\n"
       "LightGBM's numbers are NB5a's single-seed model with its own layer (`results/nb5a_conformal/`), shown for "
       "reference only."),
    code("r1h = vm[(vm.window == 'full') & (vm.h == C.PRIMARY_HORIZON)].set_index('kind')\n"
         "closer = abs(r1h.loc['conformal', 'cover80'] - 0.8) < abs(r1h.loc['raw', 'cover80'] - 0.8)\n"
         "not_worse = r1h.loc['conformal', 'IS80'] <= r1h.loc['raw', 'IS80']\n"
         "KEEP = bool(closer and not_worse)\n"
         "won = vs[(vs.window == 'full') & (vs.h == C.PRIMARY_HORIZON)].pivot(index='event', columns='kind', values='IS80')\n"
         "print('at 1 h: PICP80 raw %.3f -> conformal %.3f | IS80 raw %.4f -> conformal %.4f | units with lower IS80: %d of %d'\n"
         "      % (r1h.loc['raw', 'cover80'], r1h.loc['conformal', 'cover80'], r1h.loc['raw', 'IS80'], r1h.loc['conformal', 'IS80'],\n"
         "         int((won['conformal'] < won['raw']).sum()), len(won)))\n"
         "print('KEEP the conformal layer for PVSetFormer:', KEEP)\n"
         "lgbm = pd.read_csv(C.RESULTS / 'nb5a_conformal' / 'val_conformal_medians.csv').query(\"window == 'full'\")\n"
         "ref = pd.concat({'PVSetFormer': vm[vm.window == 'full'].set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']],\n"
         "                 'LightGBM (NB5a)': lgbm.set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']]}, names=['model'])\n"
         "print(ref.unstack('h').round(4).to_string())"),
    md("## Draft figure: reliability of the central intervals"),
    code("import matplotlib.pyplot as plt\n"
         "A._style()\n"
         "f8, ax = plt.subplots(1, 2, figsize=(7.2, 2.8))\n"
         "nom = np.array([0.2, 0.4, 0.6, 0.8])\n"
         "for kind, c, mk in [('raw', '#b03a2e', 'o'), ('conformal', '#1f4e79', 's')]:\n"
         "    r = vm[(vm.window == 'full') & (vm.kind == kind) & (vm.h == C.PRIMARY_HORIZON)].iloc[0]\n"
         "    ax[0].plot(nom, [r['cover20'], r['cover40'], r['cover60'], r['cover80']], marker=mk, ms=3.5, color=c, lw=1, label=kind)\n"
         "    z = vm[(vm.window == 'full') & (vm.kind == kind)].set_index('h').loc[FC.H, 'cover80']\n"
         "    ax[1].plot(np.array(FC.H) * 0.25, z, marker=mk, ms=3.5, color=c, lw=1, label=kind)\n"
         "ax[0].plot([0, 1], [0, 1], color='0.6', lw=0.7); ax[0].set_xlim(0.1, 0.9); ax[0].set_ylim(0.1, 0.9)\n"
         "ax[0].set_xlabel('Nominal coverage'); ax[0].set_ylabel('Observed coverage (1 h)'); ax[0].legend(frameon=False)\n"
         "ax[1].axhspan(0.75, 0.85, color='0.9', lw=0); ax[1].axhline(0.8, color='0.6', lw=0.7)\n"
         "ax[1].set_xscale('log'); ax[1].set_xticks(np.array(FC.H) * 0.25); ax[1].set_xticklabels(['0.25', '0.5', '1', '2', '4', '6'])\n"
         "ax[1].set_xlabel('Horizon (h)'); ax[1].set_ylabel('PICP of the 80% interval'); ax[1].set_ylim(0.5, 0.95)\n"
         "ax[0].set_title('PVSetFormer, median over the 10 validation units', fontsize=7); f8.tight_layout()"),
    md("## Outputs (all-or-nothing); PVSetFormer's conformal settings join the frozen part 2"),
    code("conf_cfg = {'part': '2b', 'model': 'PVSetFormer', 'part2c_sha256': r1['part2c_sha256'], 'variant': VAR,\n"
         "            'seeds': P2C['seeds'], 'method': 'CQR (Romano et al. 2019), split conformal',\n"
         "            'calibration_set': 'pseudo cold starts of the event donors; 5-seed ensemble of the early-stopped PVSetFormer predictions on the last 20% of the training issue times',\n"
         "            'donors': 'clean metadata (G1/G2 target) or all (G0 target); leave-one-out prior and uncertainty set',\n"
         "            'intervals': FC.PAIR_NAMES, 'normalisation': 'Gt(t + h)', 'per': 'event, origin, horizon',\n"
         "            'min_scores': FC.MIN_CAL, 'power_bounds': list(FC.POWER_BOUNDS), 'median_and_point': 'unchanged',\n"
         "            'keep_rule': 'median PICP80 at 1 h closer to 0.80 and median IS80 at 1 h not higher (validation units)',\n"
         "            'kept': KEEP}\n"
         "CONF_TEXT = yaml.safe_dump(conf_cfg, sort_keys=True)\n"
         "CONF_HASH = hashlib.sha256(CONF_TEXT.encode()).hexdigest()\n"
         "full = vm[vm.window == 'full']\n"
         "summary = {'notebook': 'NB5c_conformal', 'environment': A.versions(), 'runtime_s': round(time.time() - t0, 1),\n"
         "           'part2c_sha256': r1['part2c_sha256'], 'variant': VAR, 'conformal_config_sha256': CONF_HASH, 'kept': KEEP,\n"
         "           'raw_picp80_check_max_abs_diff': CHK, 'groups_without_correction': int((corrs.n_scores < FC.MIN_CAL).sum()),\n"
         "           'n_groups': len(corrs),\n"
         "           'units_lower_is80_1h': int((won['conformal'] < won['raw']).sum()),\n"
         "           'median_corrections_by_h': corrs.groupby('h')[[f'corr{n}' for n in FC.PAIR_NAMES]].median().round(4).to_dict('index'),\n"
         "           'pseudo_raw_cover80_by_h': corrs.groupby('h')['raw_cover80'].median().round(4).to_dict(),\n"
         "           **{f'{kind}_{met}_by_h': full[full.kind == kind].set_index('h')[met].round(4).to_dict()\n"
         "              for kind in ['raw', 'conformal'] for met in ['cover80', 'cover60', 'cover40', 'cover20', 'PINAW', 'IS80', 'CRPS_q']}}\n"
         "out = A.write_outputs('nb5c_conformal', {'corrections': corrs, 'val_conformal_scores': vs, 'val_conformal_medians': vm},\n"
         "                      summary, {'fig_conformal_reliability_pvsf': f8}, parquet={'calibration_quantiles_ens': cal},\n"
         "                      texts={'conformal_config_part2b_pvsf.yaml': CONF_TEXT})\n"
         "print('conformal config (part 2b, PVSetFormer) sha256:', CONF_HASH)\n"
         "print('written to', out, '|', sorted(x.name for x in out.iterdir()))"),
]
LGB_HEADER = "# NB5c conformal (LightGBM) — calibrated intervals for LightGBM's 5-seed ensemble (validation units only)\n\nD06, D35, D46, D64. The author decided on 21 Nov 2026 that LightGBM enters the test as its 5-seed ensemble (`LGB_seeds`, D37). Its conformal layer is therefore rebuilt from that ensemble, with **the rules of D35, unchanged**, exactly as for PVSetFormer (`NB5c_conformal`). Reads `results/nb5c_variants/LGB_seeds/` and `results/nb5c_variants/LGB_seeds_cal/` (`tools/lgb_seeds_cal.py`); writes `results/nb5c_conformal_lgb/`. No test event is used.\n\n**Rules (D35, fixed before any number below):**\n1. *Calibration set*, per event, origin and horizon: pseudo cold starts of the event's donors (clean-metadata donors for a G1/G2 target, all donors for a G0 target). Their index is forecast by the early-stopped models on the last 20% of the training pairs (out of sample for those models, targets before the origin), here the 5-seed ensemble of these predictions, built like the forecasts (mean of the sorted quantiles, sorted again), and composed with each donor's leave-one-out prior and uncertainty set (200 members).\n2. *Conformity*: CQR (Romano et al. 2019) per horizon and per central interval (80, 60, 40 and 20%), normalised by G̃(t + h). The correction is the ⌈(1 − α)(n + 1)⌉-th smallest score; under 50 scores, none.\n3. *Use*: applied to LightGBM's 9 power quantiles; the median and the point forecast are unchanged.\n4. *Keep rule*: the layer is kept if, on the validation units, it brings the median PICP80 at 1 h closer to 0.80 than the raw forecast and does not raise the median IS80 at 1 h."
LGB_SETUP = "import os, sys, time, json, hashlib\nfrom pathlib import Path\nimport numpy as np, pandas as pd, yaml\nROOT = Path.cwd().resolve()\nROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\nsys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'tools'))\nfrom pvcold import config as C, audit as A, fleet as F, forecast as FC\nimport r1_score as R                      # the scoring shared by rule R1 (D37)\npd.set_option('display.width', 200); pd.set_option('display.max_columns', 40)\nt0 = time.time()\nVDIR, CDIR = C.RESULTS / 'nb5c_variants' / 'LGB_seeds', C.RESULTS / 'nb5c_variants' / 'LGB_seeds_cal'\nnb5 = json.loads((C.RESULTS / 'nb5a_dev' / 'summary.json').read_text())\nls_bytes = (VDIR / 'summary.json').read_bytes(); ls = json.loads(ls_bytes)\nlc = json.loads((CDIR / 'summary.json').read_text())\nP2A_SHA = hashlib.sha256((C.RESULTS / 'nb5a_dev' / 'lgb_config_part2a.yaml').read_bytes()).hexdigest()\nassert P2A_SHA == nb5['lgb_config_sha256'] == ls['lgb_config_sha256'] == lc['lgb_config_sha256'], 'configuration part 2a changed'\nassert hashlib.sha256(ls_bytes).hexdigest() == lc['lgb_seeds_summary_sha256'], 'LGB_seeds changed after its calibration run'\nSEEDS = ls['seeds']\nassert lc['seeds'] == SEEDS and lc['forecasts_max_abs_diff'] < 1e-6\nassert lc['calibration_keys_with_all_seeds'] == lc['calibration_keys'], 'a calibration key lacks a seed'\nctx = R.load_context()\np, E, U, geo15, gains3 = ctx['p'], ctx['E'], ctx['U'], ctx['geo15'], ctx['gains3']\nPRIOR, ALT, VAL, fc5 = ctx['PRIOR'], ctx['ALT'], ctx['VAL'], ctx['fc5']\nQC = R.QC\nlv, gl = FC.member_levels()\ndef ensemble(x):\n    x = x[x.seed != 0]\n    n = x.groupby(['event', 'origin', 'h', 't'])['seed'].nunique()\n    assert sorted(x.seed.unique().tolist()) == sorted(SEEDS) and (n == len(SEEDS)).all(), 'seeds differ'\n    e = R.with_ensemble(x.drop(columns='model'))\n    return e[e.seed == 0].drop(columns='seed').reset_index(drop=True)\nfc = ensemble(pd.read_parquet(VDIR / 'forecasts.parquet'))\ncal = ensemble(pd.read_parquet(CDIR / 'calibration.parquet'))\nprint('LightGBM 5-seed ensemble | seeds', SEEDS, '| prior', PRIOR)\nprint('ensemble rows: forecasts %d, calibration %d' % (len(fc), len(cal)))"
ap = argparse.ArgumentParser()
ap.add_argument("--model", choices=["pvsf", "lgb"], default="pvsf")
ap.add_argument("--out", default=str(ROOT / "notebooks"), help="folder for the notebook (default notebooks/)")
MODEL = ap.parse_args().model
NAME = "NB5c_conformal"
if MODEL == "lgb":                                       # D64: LightGBM's 5-seed ensemble, the same rules
    NAME = "NB5c_conformal_lgb"

    def swap(i, pairs):
        src = nb.cells[i].source
        for old, new in pairs:
            assert src.count(old) == 1, (i, old[:60])
            src = src.replace(old, new)
        nb.cells[i] = (md if nb.cells[i].cell_type == "markdown" else code)(src)

    nb.cells[0], nb.cells[1] = md(LGB_HEADER), code(LGB_SETUP)
    swap(6, [("## Keep rule (rule 4), and LightGBM's layer for reference\n"
              "LightGBM's numbers are NB5a's single-seed model with its own layer (`results/nb5a_conformal/`), shown for "
              "reference only.",
              "## Keep rule (rule 4), and the other layers for reference\n"
              "NB5a's single-seed LightGBM with its own layer (`results/nb5a_conformal/`) and PVSetFormer with its layer "
              "(`results/nb5c_conformal/`), shown for reference only.")])
    swap(7, [("print('KEEP the conformal layer for PVSetFormer:', KEEP)\n",
              "print('KEEP the conformal layer for LightGBM (5 seeds):', KEEP)\n"),
             ("lgbm = pd.read_csv(C.RESULTS / 'nb5a_conformal' / 'val_conformal_medians.csv').query(\"window == 'full'\")\n"
              "ref = pd.concat({'PVSetFormer': vm[vm.window == 'full'].set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']],\n"
              "                 'LightGBM (NB5a)': lgbm.set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']]}, names=['model'])\n",
              "lgb1 = pd.read_csv(C.RESULTS / 'nb5a_conformal' / 'val_conformal_medians.csv').query(\"window == 'full'\")\n"
              "pvsf = pd.read_csv(C.RESULTS / 'nb5c_conformal' / 'val_conformal_medians.csv').query(\"window == 'full'\")\n"
              "ref = pd.concat({'LightGBM, 5 seeds': vm[vm.window == 'full'].set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']],\n"
              "                 'LightGBM (NB5a, 1 seed)': lgb1.set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']],\n"
              "                 'PVSetFormer (NB5c)': pvsf.set_index(['kind', 'h'])[['cover80', 'IS80', 'CRPS_q']]}, names=['model'])\n")])
    swap(9, [("'PVSetFormer, median over the 10 validation units'", "'LightGBM (5 seeds), median over the 10 validation units'")])
    swap(10, [("PVSetFormer's conformal settings join the frozen part 2", "LightGBM's 5-seed conformal settings join the frozen part 2")])
    swap(11, [("conf_cfg = {'part': '2b', 'model': 'PVSetFormer', 'part2c_sha256': r1['part2c_sha256'], 'variant': VAR,\n"
               "            'seeds': P2C['seeds'], ",
               "conf_cfg = {'part': '2b', 'model': 'LightGBM, 5-seed ensemble', 'lgb_config': P2A_SHA,\n"
               "            'seeds': SEEDS, "),
              ("5-seed ensemble of the early-stopped PVSetFormer predictions on the last 20% of the training issue times",
               "5-seed ensemble of the early-stopped LightGBM predictions on the last 20% of the training pairs"),
              ("summary = {'notebook': 'NB5c_conformal', ", "summary = {'notebook': 'NB5c_conformal_lgb', 'decision': 'D64', "),
              ("           'part2c_sha256': r1['part2c_sha256'], 'variant': VAR, 'conformal_config_sha256'",
               "           'lgb_config_sha256': P2A_SHA, 'lgb_seeds_summary_sha256': lc['lgb_seeds_summary_sha256'], 'seeds': SEEDS,\n"
               "           'conformal_config_sha256'"),
              ("A.write_outputs('nb5c_conformal', ", "A.write_outputs('nb5c_conformal_lgb', "),
              ("{'fig_conformal_reliability_pvsf': f8}", "{'fig_conformal_reliability_lgb5': f8}"),
              ("texts={'conformal_config_part2b_pvsf.yaml': CONF_TEXT}", "texts={'conformal_config_part2b_lgb5.yaml': CONF_TEXT}"),
              ("print('conformal config (part 2b, PVSetFormer) sha256:', CONF_HASH)",
               "print('conformal config (part 2b, LightGBM 5 seeds) sha256:', CONF_HASH)")])
    for c in nb.cells:                                   # only the reference row may still name PVSetFormer
        left = c.cell_type == "code" and "PVSetFormer" in c.source.replace("'PVSetFormer (NB5c)'", "")
        assert not left, "a PVSetFormer-only line is left"
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, Path(ap.parse_args().out) / f"{NAME}.ipynb")
print(f"wrote {NAME}.ipynb")
