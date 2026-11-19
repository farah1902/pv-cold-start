# PVSetFormer: forecasting new rooftop PV inverters from day one, without history or a pyranometer

Research code for a paper in preparation (target: *Solar Energy*). A newly installed rooftop PV inverter is forecast
from its first day, with no power history of its own and no irradiance sensor:

- a **campus clear-sky index** is estimated causally from the inverters already online (clipping treated as
  censoring) and forecast probabilistically from 15 min to 6 h by **PVSetFormer**, a censoring-aware set
  transformer over the peer inverters (or by quantile LightGBM, whichever wins on the validation units);
- a **gain prior** for the new inverter comes from its nameplate DC/AC ratio and is updated by shrinkage as its own
  data arrive;
- the evaluation uses **real telemetry start dates** on the HKUST campus (13 scored events, 2021–2023), a frozen
  configuration, an exact error budget and a sensor ablation across the 2023 pyranometer drift, plus an external case
  on a rooftop in Safi, Morocco.

Status (19 November 2026): notebooks NB0–NB4 are done (audit, preprocessing, fleet index and priors with part 1 of the
frozen configuration, sensor and satellite index sources); no forecast has been scored yet. The plan is in
`docs/research_guide.md`; the numbers are in `docs/results_summary.md`.

## Data

The input data are not in this repository. `data/README.md` says where to get each dataset and where to put it, and
`data/MANIFEST_sha256.csv` lets you check your copy:

```bash
pip install -r requirements.txt
python tools/make_data_manifest.py --check
```

## Licence

To be set at release: MIT for the code, CC BY 4.0 for derived data (planned, research guide §4.5).
