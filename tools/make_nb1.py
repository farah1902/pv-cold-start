"""Generate notebooks/NB1_hkust_audit.ipynb. Run: python tools/make_nb1.py, then execute the notebook."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
    md("# NB1 — Audit of the HKUST dataset\n\n"
       "Describes the data before any modelling and reproduces, from code, the claims of the review audit of "
       "18 Nov 2026 (F01, F05, F06, F16) and of the sensor audit of 31 Oct 2026 (F09). Nothing is tuned here.\n"
       "Outputs: `results/nb1_audit/` (tables, draft figures, summary.json), written all-or-nothing."),
    code("import sys, time, json\n"
         "from pathlib import Path\n"
         "import numpy as np, pandas as pd\n"
         "ROOT = Path.cwd().resolve()\n"
         "ROOT = ROOT.parent if ROOT.name == 'notebooks' else ROOT\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "from pvcold import config as C, audit as A, io_hkust as io\n"
         "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)\n"
         "t0 = time.time()"),
    md("## 1. Units from the Brick metadata\nAC rating from the inverter model name, DC rating from module count × "
       "watt-peak (D01). Brick azimuth is converted to the pvlib convention (F15)."),
    code("inv, st, inv_map, st_map = A.units()\n"
         "print(f'{len(st)} stations, {len(inv)} inverters; files matched: {len(inv_map)} inverter, {len(st_map)} site')\n"
         "inv[['station', 'inverter', 'inverter_model', 'AC_kW', 'module_models', 'n_modules', 'DC_kWp', 'DC_AC']].round(3)"),
    md("## 2. Inventory of the inverter files (5 min)"),
    code("ii, daily_inv = A.inventory_inverters(inv)\n"
         "print('timestamp formats:', ii.time_format.value_counts().to_dict())\n"
         "print('rows per day (mode):', ii.rows_per_day_mode.value_counts().to_dict(),\n"
         "      '| earliest slot:', ii.earliest_slot.unique(), '| latest slot:', ii.latest_slot.unique())\n"
         "print('duplicated stamps:', ii.duplicated_stamps.sum(), '| negative power values:', ii.negative_P.sum())\n"
         "print('NA share of power: median %.3f, max %.3f' % (ii.na_share_P.median(), ii.na_share_P.max()))\n"
         "print('not producing on the first day:', ii.loc[ii.producing_on_first_day == False, 'file'].tolist())\n"
         "ii.sort_values('first')[['file', 'time_format', 'first', 'last', 'days', 'na_share_P', 'P_p999_kW', 'AC_kW', 'p999_over_AC']]"),
    md("## 3. AC rating vs observed power\nGuide §2: the AC rating matches the 99.9th percentile of power within 2% for "
       "most units; the others are metadata errors or units that never reach their limit."),
    code("mc = A.metadata_check(ii, inv)\n"
         "print('within 2%:', int(mc.within_2pct.sum()), 'of', len(mc))\n"
         "mc.loc[~mc.within_2pct, ['file', 'inverter_model', 'AC_kW', 'DC_kWp', 'DC_AC', 'P_p999_kW', 'P_max_kW', 'p999_over_AC']].round(3)"),
    md("## 4. Site files and weather files"),
    code("ac_station = pd.concat([st.set_index('site_file_15min')['rated_kW_metadata'].dropna(),\n"
         "                        st.set_index('site_file_1h')['rated_kW_metadata'].dropna()])\n"
         "s15, frames15 = A.inventory_sites('15min', ac_station)\n"
         "s1h, _ = A.inventory_sites('1h', ac_station)\n"
         "for lab, s in [('15 min', s15), ('1 h', s1h)]:\n"
         "    print(lab, '| formats:', s.time_format.value_counts().to_dict(), '| not starting on the 1st:',\n"
         "          int((~s.starts_on_1st).sum()), 'of', len(s), '| slots', s.earliest_slot.min(), '-', s.latest_slot.max())\n"
         "wi = A.inventory_weather()\n"
         "wi"),
    md("## 5. Start dates (D08) and the review-audit claims"),
    code("stt = A.start_table(inv, st, ii, s15)\n"
         "stt"),
    code("es, es_sum = A.evening_share(frames15)\n"
         "per_station = {k: v.loc[v.time.dt.hour >= 18, 'E_kWh'].sum() / v.E_kWh.sum() for k, v in frames15.items() if v.E_kWh.sum() > 0}\n"
         "es_sum['median_share_per_station_whole_period'] = float(np.median(list(per_station.values())))\n"
         "es_sum['max_share_per_station_whole_period'] = float(np.max(list(per_station.values())))\n"
         "print(json.dumps(es_sum, indent=1))\n"
         "zd = A.zone_d_ratio(frames15)\n"
         "zd"),
    md("## 6. The pyranometer against CAMS all-sky GHI, Ineichen clear sky and the fleet (F09, D19)\n"
         "Days with a dead sensor (sensor / CAMS below 0.3) are left out of the change-point search. The final drift "
         "boundary is fixed in NB3 on the fleet index (D10); this is the audit-level date."),
    code("altitude = float(np.median(st.altitude_m.dropna()))\n"
         "sd, sm = A.sensor_tables(daily_inv, inv, altitude)\n"
         "dead = sd['ratio_sensor_cams'] < 0.3\n"
         "print('campus altitude used for clear sky: %.0f m | dead-sensor days: %d (%s to %s)' % (\n"
         "      altitude, dead.sum(), sd.index[dead].min().date(), sd.index[dead].max().date()))\n"
         "cp = {k: A.dominant_change(sd.loc[~dead, k]) for k in ['ratio_sensor_cams', 'ratio_sensor_fleet', 'ratio_cams_fleet']}\n"
         "print(json.dumps(cp, indent=1))\n"
         "sd.groupby(sd.index.year)[['ratio_sensor_cams', 'ratio_sensor_fleet', 'ratio_cams_fleet']].median().round(3)"),
    code("sm.round(3)"),
    md("## 7. Draft figures"),
    code("f_sensor = A.fig_sensor(sd.loc[~dead], sm, cp['ratio_sensor_fleet']['date'])\n"
         "f_quirks = A.fig_quirks(frames15, zd)"),
    md("## 8. Outputs (all-or-nothing)"),
    code("summary = {\n"
         "    'notebook': 'NB1_hkust_audit', 'environment': A.versions(), 'runtime_s': round(time.time() - t0, 1),\n"
         "    'n_stations': len(st), 'n_inverters_metadata': len(inv), 'n_inverter_files': len(ii),\n"
         "    'inverter_time_formats': ii.time_format.value_counts().to_dict(),\n"
         "    'site_time_formats_15min': s15.time_format.value_counts().to_dict(),\n"
         "    'site_time_formats_1h': s1h.time_format.value_counts().to_dict(),\n"
         "    'inverter_rows_per_day_mode': ii.rows_per_day_mode.value_counts().to_dict(),\n"
         "    'inverter_slots': [ii.earliest_slot.min(), ii.latest_slot.max()],\n"
         "    'inverter_na_share_median': float(ii.na_share_P.median()), 'inverter_na_share_max': float(ii.na_share_P.max()),\n"
         "    'not_producing_first_day': ii.loc[ii.producing_on_first_day == False, 'file'].tolist(),\n"
         "    'ac_within_2pct': int(mc.within_2pct.sum()), 'ac_checked': int(len(mc)),\n"
         "    'site15_not_on_1st': int((~s15.starts_on_1st).sum()), 'site1h_not_on_1st': int((~s1h.starts_on_1st).sum()),\n"
         "    'evening_share': es_sum, 'campus_altitude_m': altitude,\n"
         "    'dead_sensor_days': int(dead.sum()), 'dead_sensor_first': str(sd.index[dead].min().date()),\n"
         "    'dead_sensor_last': str(sd.index[dead].max().date()), 'sensor_change_points_audit': cp,\n"
         "    'sensor_ratio_yearly_median': sd.groupby(sd.index.year)[['ratio_sensor_cams', 'ratio_sensor_fleet',\n"
         "                                   'ratio_cams_fleet']].median().round(4).to_dict(),\n"
         "    'left_censored_by_rule': stt.loc[stt.left_censored_by_rule, 'station'].tolist(),\n"
         "}\n"
         "tables = {'units_inverters': inv, 'units_stations': st, 'inventory_inverters': ii, 'metadata_check': mc,\n"
         "          'inventory_sites_15min': s15, 'inventory_sites_1h': s1h, 'inventory_weather': wi,\n"
         "          'start_dates': stt, 'evening_share': es, 'zone_d_ratio': zd,\n"
         "          'sensor_daily': sd.reset_index(names='day'), 'sensor_monthly': sm.reset_index(names='month')}\n"
         "out = A.write_outputs('nb1_audit', tables, summary, {'sensor_drift': f_sensor, 'quirks': f_quirks})\n"
         "print('written to', out, '|', sorted(p.name for p in out.iterdir()))"),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, ROOT / "notebooks" / "NB1_hkust_audit.ipynb")
print("wrote notebooks/NB1_hkust_audit.ipynb")
