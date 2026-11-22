"""Generate notebooks/NB5c_R1_decision.ipynb: rule R1 on the validation units (D25, D36, D37).

Usage:  python tools/make_nb5c.py --final <variant>     (a pvsf_dev.py round run with --seeds 5)

The notebook trains nothing. It reads the final PVSetFormer round and LightGBM's 5-seed round
(results/nb5c_variants/LGB_seeds/), checks that both used the same seeds and were scored on the same slots, applies
the R1 rule fixed in D25 and D37, and writes results/nb5c_r1/ (tables, figure, summary, frozen configuration part 2c).
"""
import argparse
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--final", required=True)
FINAL = ap.parse_args().final

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("# NB5c — rule R1: PVSetFormer or LightGBM as the index forecaster (validation units only)\n\n"
       f"D25, D36, D37. Final PVSetFormer round: **{FINAL}** (`results/nb5c_variants/{FINAL}/`, 5 seeds); LightGBM: "
       "`results/nb5c_variants/LGB_seeds/` (5 seeds). Both were scored by `tools/r1_score.py` on exactly the slots "
       "NB5a scored. No test event is used.\n\n"
       "**Rule, fixed before the final rounds (D25, D37):** PVSetFormer becomes the main index forecaster only if the "
       "median over the 10 validation units of the nRMSE at 1 h of its 5-seed ensemble is lower than that of "
       "LightGBM's 5-seed ensemble (seeds C.SEED + 1 … C.SEED + 5 for both). Otherwise LightGBM stays the main index "
       "forecaster. Since D73 the title no longer depends on R1. The per-seed mean and s.d., the units won and a "
       "paired Wilcoxon signed-rank test over the 10 units are reported beside the rule; they do not change it.\n\n"
       "**Count of design variants (D73):** the PVSetFormer rounds of `log.csv` (names starting with V; a 5-seed "
       "re-run counts as the same variant), not the TimeXer runs (TX), the R2 runs (A6e) or the A4c row; the "
       "hyperparameter searches are counted separately.\n\n"
       "**Caveat (D36):** the design rounds and this comparison use the same 10 validation units, which favours the "
       "model with more rounds (PVSetFormer). The test run is the unbiased check."),
    code("import os, sys, json, time, hashlib\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd, yaml\n"
         "from scipy.stats import wilcoxon\n"
         "ROOT = Path.cwd().resolve()\n"
         "ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "from pvcold import config as C, audit as A, forecast as FC, setformer as SF\n"
         "pd.set_option('display.width', 200)\n"
         f"FINAL = {FINAL!r}\n"
         "t0 = time.time(); H1 = C.PRIMARY_HORIZON\n"
         "VD = C.RESULTS / 'nb5c_variants'\n"
         "sp = json.loads((VD / FINAL / 'summary.json').read_text()); sl = json.loads((VD / 'LGB_seeds' / 'summary.json').read_text())\n"
         "nb5 = json.loads((C.RESULTS / 'nb5a_dev' / 'summary.json').read_text())\n"
         "scp = pd.read_csv(VD / FINAL / 'scores.csv'); scl = pd.read_csv(VD / 'LGB_seeds' / 'scores.csv')\n"
         "seeds_p = sorted(int(s) for s in scp.seed.unique() if s > 0); seeds_l = list(sl['seeds'])\n"
         "assert sp['seeds'] == 5 and seeds_p == seeds_l == [C.SEED + i for i in range(1, 6)], (seeds_p, seeds_l)\n"
         "assert sl['lgb_config_sha256'] == nb5['lgb_config_sha256'] and sl['check_passed']\n"
         "k = ['event', 'seed', 'h']\n"
         "both = scp.merge(scl, on=k, suffixes=('_pvsf', '_lgb'))\n"
         "assert len(both) == len(scp) == len(scl) and (both['n_pvsf'] == both['n_lgb']).all(), 'different slots'\n"
         "log = pd.read_csv(VD / 'log.csv')\n"
         "print('PVSetFormer', FINAL, sp['cfg'], '| parameters', sp['n_params'])\n"
         "print('LightGBM', sl['params'], '| seeds', seeds_l, '| slots per unit and horizon identical')\n"
         "VARIANTS = list(dict.fromkeys(v.removesuffix('_5s') for v in log.variant if v.startswith('V')))   # design rounds, in order (V3 was logged twice, D36)\n"
         "SEARCHES = sorted(p.name for p in VD.glob('CV*') if json.loads((p / 'summary.json').read_text())['base'].get('arch', 'pvsf') == 'pvsf')\n"
         "assert FINAL.removesuffix('_5s') in VARIANTS\n"
         "print('PVSetFormer design variants logged before this decision:', len(VARIANTS), VARIANTS)\n"
         "print('PVSetFormer hyperparameter searches:', SEARCHES)"),
    md("## Medians over the 10 validation units, per horizon"),
    code("MET = ['nRMSE', 'CRPS', 'PICP80']\n"
         "rows = []\n"
         "for model, sc in [('PVSF', scp), ('LGB', scl)]:\n"
         "    ens = sc[sc.seed == 0].groupby('h')[MET].median()\n"
         "    ps = sc[sc.seed > 0].groupby(['seed', 'h'])[MET].median().groupby('h').agg(['mean', 'std', 'min', 'max'])\n"
         "    for h in FC.H:\n"
         "        rows.append({'model': model, 'h': h, **{f'{m}_ens': ens.loc[h, m] for m in MET},\n"
         "                     **{f'{m}_seed_{s}': ps.loc[h, (m, s)] for m in MET for s in ['mean', 'std', 'min', 'max']}})\n"
         "tab = pd.DataFrame(rows)\n"
         "print(tab.pivot(index='h', columns='model', values='nRMSE_ens').round(4).to_string())\n"
         "print(tab.pivot(index='h', columns='model', values='CRPS_ens').round(4).to_string())\n"
         "print(tab[['model', 'h', 'nRMSE_seed_mean', 'nRMSE_seed_std']].round(4).to_string(index=False))"),
    md("## Rule R1 at 1 h"),
    code("e = both[both.seed == 0]\n"
         "u = e[e.h == H1].set_index('event')[['nRMSE_pvsf', 'nRMSE_lgb']]\n"
         "u['diff'] = u.nRMSE_pvsf - u.nRMSE_lgb; u['pct'] = 100 * u['diff'] / u.nRMSE_lgb\n"
         "r_p, r_l = float(u.nRMSE_pvsf.median()), float(u.nRMSE_lgb.median())\n"
         "PVSF_MAIN = bool(r_p < r_l)\n"
         "won = int((u['diff'] < 0).sum())\n"
         "wx = wilcoxon(u.nRMSE_pvsf, u.nRMSE_lgb)\n"
         "won_h = e.assign(w=e.nRMSE_pvsf < e.nRMSE_lgb).groupby('h')['w'].sum().astype(int)\n"
         "print(u.round(4).to_string())\n"
         "print('median nRMSE at 1 h: PVSetFormer ensemble %.5f vs LightGBM ensemble %.5f (%.2f%%) | units won %d of %d | '\n"
         "      'Wilcoxon p = %.3f' % (r_p, r_l, 100 * (r_p / r_l - 1), won, len(u), wx.pvalue))\n"
         "print('units won by horizon:', won_h.to_dict())\n"
         "print('R1: PVSetFormer becomes the main index forecaster:', PVSF_MAIN)"),
    md("## Figure (development record)"),
    code("import matplotlib.pyplot as plt\n"
         "A._style()\n"
         "fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8))\n"
         "x = np.array(FC.H) * 0.25\n"
         "for model, c, mk, lab in [('PVSF', '#1f4e79', 's', 'PVSetFormer'), ('LGB', '#b03a2e', 'o', 'LightGBM')]:\n"
         "    t = tab[tab.model == model].set_index('h').loc[FC.H]\n"
         "    ax[0].fill_between(x, t.nRMSE_seed_min, t.nRMSE_seed_max, color=c, alpha=0.15, lw=0)\n"
         "    ax[0].plot(x, t.nRMSE_ens, marker=mk, ms=3.5, color=c, lw=1, label=lab + ' (5-seed ensemble)')\n"
         "ax[0].set_xscale('log'); ax[0].set_xticks(x); ax[0].set_xticklabels(['0.25', '0.5', '1', '2', '4', '6'])\n"
         "ax[0].set_xlabel('Horizon (h)'); ax[0].set_ylabel('Median nRMSE'); ax[0].legend(frameon=False, fontsize=6)\n"
         "lim = [min(u.min(numeric_only=True)[['nRMSE_pvsf', 'nRMSE_lgb']]) - 0.005, max(u.max(numeric_only=True)[['nRMSE_pvsf', 'nRMSE_lgb']]) + 0.005]\n"
         "ax[1].plot(lim, lim, color='0.6', lw=0.7)\n"
         "ax[1].scatter(u.nRMSE_lgb, u.nRMSE_pvsf, s=10, color='#1f4e79')\n"
         "ax[1].set_xlim(lim); ax[1].set_ylim(lim); ax[1].set_aspect('equal')\n"
         "ax[1].set_xlabel('LightGBM nRMSE at 1 h'); ax[1].set_ylabel('PVSetFormer nRMSE at 1 h')\n"
         "ax[0].set_title('10 validation units; band: range of single seeds', fontsize=7); fig.tight_layout()"),
    md("## Outputs (all-or-nothing); the decision joins the frozen part 2 as part 2c"),
    code("part2c = {'part': '2c', 'rule': 'R1 (D25, D37): median validation nRMSE at 1 h, 5-seed ensembles of both models',\n"
         "          'main_index_forecaster': 'PVSetFormer' if PVSF_MAIN else 'LightGBM',\n"
         "          'seeds': seeds_l, 'ensemble': 'mean of the sorted quantiles across seeds, sorted again',\n"
         "          'pvsetformer_variant': FINAL, 'pvsetformer_cfg': sp['cfg'], 'pvsetformer_n_params': sp['n_params'],\n"
         "          'lgb_config_sha256': nb5['lgb_config_sha256'], 'lgb_params': sl['params'],\n"
         "          'R1_pvsf_ensemble': round(r_p, 6), 'R1_lgb_ensemble': round(r_l, 6),\n"
         "          'variants_before_decision': len(VARIANTS), 'design_variants': VARIANTS,\n"
         "          'searches_before_decision': SEARCHES}\n"
         "P2C_TEXT = yaml.safe_dump(part2c, sort_keys=True)\n"
         "P2C_HASH = hashlib.sha256(P2C_TEXT.encode()).hexdigest()\n"
         "summary = {'notebook': 'NB5c_R1_decision', 'environment': A.versions(), 'runtime_s': round(time.time() - t0, 1),\n"
         "           'final_variant': FINAL, 'pvsf_summary_sha256': hashlib.sha256((VD / FINAL / 'summary.json').read_bytes()).hexdigest(),\n"
         "           'lgb_seeds_summary_sha256': hashlib.sha256((VD / 'LGB_seeds' / 'summary.json').read_bytes()).hexdigest(),\n"
         "           'R1_pvsf_ensemble': r_p, 'R1_lgb_ensemble': r_l, 'R1_rel_diff_pct': 100 * (r_p / r_l - 1),\n"
         "           'R1_pvsf_seed_mean': float(tab.query('model == \"PVSF\" and h == @H1').nRMSE_seed_mean.iloc[0]),\n"
         "           'R1_pvsf_seed_sd': float(tab.query('model == \"PVSF\" and h == @H1').nRMSE_seed_std.iloc[0]),\n"
         "           'R1_lgb_seed_mean': float(tab.query('model == \"LGB\" and h == @H1').nRMSE_seed_mean.iloc[0]),\n"
         "           'R1_lgb_seed_sd': float(tab.query('model == \"LGB\" and h == @H1').nRMSE_seed_std.iloc[0]),\n"
         "           'units_won_1h': won, 'wilcoxon_p_1h': float(wx.pvalue), 'units_won_by_h': won_h.to_dict(),\n"
         "           'pvsf_main': PVSF_MAIN, 'part2c_sha256': P2C_HASH, 'variants_before_decision': len(VARIANTS),\n"
         "           'design_variants': VARIANTS, 'searches_before_decision': SEARCHES}\n"
         "out = A.write_outputs('nb5c_r1', {'r1_medians': tab, 'r1_units_1h': u.reset_index(), 'r1_pairs': both}, summary,\n"
         "                      {'fig_r1': fig}, texts={'r1_config_part2c.yaml': P2C_TEXT})\n"
         "print('part 2c sha256:', P2C_HASH)\n"
         "print('written to', out, '|', sorted(x.name for x in out.iterdir()))"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, ROOT / "notebooks" / "NB5c_R1_decision.ipynb")
print(f"wrote notebooks/NB5c_R1_decision.ipynb (final variant {FINAL})")
