# Data: sources, licences and layout

None of the files below are committed (about 1.7 GB in total). `MANIFEST_sha256.csv` lists every file with its size
and SHA-256 checksum, as they were on 18 November 2026 (165 files, 1,673.8 MB). Check a copy with
`python tools/make_data_manifest.py --check` from the repository root.

| Folder | What it holds | Source | Licence (status) |
| --- | --- | --- | --- |
| `raw/hkust/Dataset/` | 44 inverter files (5 min), 37 site files with optimizers (15 min), 23 site files without optimizers (1 h), 1-min weather (7 variables, 2021–2023), Brick metadata (`.ttl`) | Lin et al., Dryad, doi:10.5061/dryad.m37pvmd99 (Sept 2024 version, with tilt and azimuth) | Dryad README says "N/A"; reported as CC0 in the research guide — **to confirm before release** |
| `raw/hkust/README.md` | The Dryad README | same | same |
| `raw/hkust/s41597-025-04397-y.pdf` | Data descriptor: Lin et al., *Scientific Data* 12:63 (2025), doi:10.1038/s41597-025-04397-y | Springer Nature | Article under CC BY-NC-ND 4.0 (stated on its p. 13) |
| `raw/safi/` | Safi rooftop raw files: `Electric {a-Si, m-Si, p-Si}.xlsx`, `Tc {a-Si, m-Si, p-Si}.xlsx`, `Weather data.xlsx`, `Preprocessed Data.xlsx` (**never used**: filtered by its authors, research guide §8) | Mendeley Data b2s4ycc2gz, v1; article Id Omar et al., *Data in Brief* 34 (2021) 106756 | CC BY 4.0 per the research guide — **to confirm** |
| `raw/archives/` | `Dataset.zip` (the Dryad download), `b2s4ycc2gz-1.zip` (the Mendeley download) | as above | as above |
| `external/cams/mcclear/` | `HKUSTcsv.csv` (22.3363 N, 114.2634 E, CAMS altitude 144 m, 2021-01-01 to 2023-12-31) and `safi-2016-2018csv.csv` (32.3265 N, 9.2634 W, 2016-06-01 to 2018-08-31): CAMS McClear v3.6, **clear-sky only**, UT, Wh/m² per 1-min step | CAMS radiation service (soda-pro) | **to confirm** |
| `external/open-meteo/` | `open-meteo-32.23N7.95W467m.csv`: Benguerir, hourly temperature, wind and precipitation, 2016-06-01 to 2018-12-31 (follow-up paper, D07) | Open-Meteo archive (ERA5) | **to confirm** |
| `external/pv_density/` | `isprs-archives-XLVIII-4-W17-2025-317-2026.pdf` (source paper of the regional PV map), `digitization/` (grid digitised from its figure by `tools/reconstruct_pv_density.py` on 13 Nov 2026; a visual reconstruction, not the authors' polygons), `pv_clusters_map.png`, `work/` (intermediate images) | ISPRS Archives | **to confirm**; the source paper must be named and cited |

## Where the files came from (moves of 18 November 2026)

| Old path (under `pv paper/`) | New path |
| --- | --- |
| `3year data/Dataset/`, `README.md`, `s41597-025-04397-y.pdf` | `data/raw/hkust/` |
| `3year data/hkust-data-audit.md` | `docs/history/hkust-data-audit.md` |
| `Dataset.zip`, `b2s4ycc2gz-1.zip` | `data/raw/archives/` |
| `Safi Raw Data/*` | `data/raw/safi/` |
| `CAMS solar radiation time-series/*` | `data/external/cams/mcclear/` |
| `open-meteo-32.23N7.95W467m.csv` | `data/external/open-meteo/` |
| `output/isprs-…pdf`, `output/pv_density_digitization/`, `pv_clusters_map.png`, `tmp/pdfs/*` | `data/external/pv_density/` (`digitization/`, `work/`) |
| `tmp/reconstruct_pv_density.py` | `tools/reconstruct_pv_density.py` (paths are arguments) |

## Still to download (D07, D14)

1. CAMS radiation time series with sky type **"Observed cloud"** for Safi, 2016-06-01 to 2018-12-31 → `external/cams/observed/`.
2. The same for HKUST, 2021-01-01 to 2023-12-31, if the service covers Hong Kong; otherwise baseline A9 and the
   satellite check of the HKUST sensor are dropped (D14).

## Colab

Colab reads the data from the Drive mirror of this repository (path set at NB0). Copy `data/` there once and run
`python tools/make_data_manifest.py --check` on Colab before the first run.
