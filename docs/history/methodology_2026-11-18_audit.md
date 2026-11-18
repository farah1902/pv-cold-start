# Cold-start PV forecasting without a pyranometer — full methodology

Nov 2, 2026 · @farah

## Status

The pilot passes the go/no-go test: fleet-based forecasts cut climatology's error by more than half up to 1 h ahead (and by about a fifth at 6 h), and the drifted pyranometer adds about 74% error at 15 min for events after November 2022.

This document is the full design of the paper: data, method, equations, models, statistics, release and plan. Everything below is a proposal until you confirm the open decisions in the last section. Equations marked as tunable are frozen on the validation events before any test event is scored.

Pilot results (simplified: point forecasts, Haurwitz clear-sky, scikit-learn boosting; median daylight nRMSE across the 19 events of the earlier event list, fraction of AC rating):

| Model | 15 min | 1 h | 2 h | 6 h |
| --- | --- | --- | --- | --- |
| A0 climatological fleet index | 0.216 | 0.223 | 0.230 | 0.197 |
| A1 persisted fleet index | 0.092 | 0.126 | 0.164 | 0.209 |
| Boosting on the fleet state | 0.097 | 0.122 | 0.142 | 0.154 |
| A4 persisted raw pyranometer | 0.123 | 0.147 | 0.181 | 0.193 |
| A7 same-time fleet index (oracle) | 0.075 | 0.078 | 0.081 | 0.063 |

The DC/AC gain prior, tested on the 15 events with clean metadata, halves the gain error (median 0.059 to 0.032, leave-one-out).

## 1. Global vision

**Thesis.** A newly installed rooftop PV inverter can be forecast from its first day, with no history of its own and no pyranometer. Two ingredients do it: a campus clear-sky index estimated causally from the inverters already online, and a gain prior taken from the new inverter's nameplate DC/AC ratio.

### The problem

Rooftop PV is installed faster than forecasting models can be trained for it. A new system has no power history, so learned forecasters cannot be fitted for weeks or months. The usual fix transfers an irradiance-to-power model, which assumes a trustworthy irradiance input. On rooftops that assumption often fails: the HKUST pyranometer reads about 0.8 of clear-sky in 2021–2022 and about 1.35 in 2023. It is a LI-COR LI-200R with ±5% maximum error, so this step is a fault, not scatter.

Most cold-start papers also simulate the cold start by hiding a station that was already running. HKUST offers something rarer: 14 telemetry start events with an observed start at 15-min resolution, one of them a capacity addition, plus a documented sensor failure.

### Three contributions (no more)

1. **A causal fleet-factor forecaster.** The campus clear-sky index k(t) is estimated from peers up to the issue time only, with clipping treated as censoring, then forecast probabilistically for 15 min to 6 h. The new inverter needs no history and no irradiance sensor. A distance-weighted local index extends the idea from a campus to a region (Section 8).
2. **A physical gain prior.** Each inverter's gain is predicted from its DC/AC ratio, with uncertainty from the donor fleet, then updated by Bayesian shrinkage as its own data arrive. This tells an operator when to retire the cold-start model.
3. **An honest evaluation protocol.** Real telemetry start dates, a formal information set, an exact error budget (index vs gain vs residual), and a sensor ablation showing that irradiance-based transfer works while the sensor is stable and fails after its step drift, even after recalibration (to be confirmed by A4b). An external case study on a Moroccan rooftop in Safi then measures how much adaptation a new country needs.

### Positioning against prior work

Read from abstracts and earlier notes; every cell is verified in the full texts during writing.

| Work | Needs own history | Needs irradiance or weather input | Causal forecast | Real start dates | Probabilistic |
| --- | --- | --- | --- | --- | --- |
| Engerer & Mills 2014, KPV ([doi](https://doi.org/10.1016/j.solener.2014.04.019)) | No | Clear-sky PV model with tilt/azimuth | No, same-time estimate | No | No |
| Killinger et al. 2017, upscaling | No | Reference plants with loss factors | No, same-time nowcast | No | No |
| Smart persistence (Pedro & Coimbra 2012 and others) | Yes | Clear-sky model | Yes | Not applicable | Usually no |
| Bottieau et al. 2022, cross-learning | No | Weather and clear-sky irradiance | Yes | Simulated | To verify |
| AutoPV (Meisenbacher et al. 2022) | No, peak power only | Weather forecasts | Yes | Simulated | No |
| PhysTrans (IJCAI 2026) | No | Satellite cloud information | Yes | Simulated | To verify |
| **This paper** | **No** | **None; DC/AC from nameplate** | **Yes** | **Yes, 14 events** | **Yes** |

The sentence that must survive a reviewer who knows Engerer: *we take the PV clear-sky index used for same-time upscaling and turn it into a causal, probabilistic cold-start forecast that needs no local pyranometer, then test it on real start dates, including the year the sensor drifted.*

### Scope limits, stated up front

- Main statistical claims on one campus (about 60 ha), one humid subtropical climate, tilts of 0–15°. Morocco adds one real external case (Safi, 3 inverters) and two semi-synthetic fleets.
- All 15-min units are mono-Si; thin-film appears only in the hourly track.
- Horizons of 15 min to 6 h, issued in daylight. Day-ahead is out of scope. The inverter files cover 06:00–17:55 only, so forecasts are issued between 06:00 and 17:55 minus the horizon.
- Cross-climate transfer is measured only on Safi and the semi-synthetic Moroccan fleets, never claimed in general. No tilt-transfer claim and no new deep architecture.

### Pre-registered success criteria

- The main model beats A1 on median event-wise nRMSE at the primary horizon of 1 h, chosen before scoring (one-sided Wilcoxon, n = 14, p < 0.05). Other horizons are secondary, with Holm correction.
- In the drifted window (about 5 events, too few for a significant Wilcoxon test), it beats A4 and A4b by effect size, with per-event Diebold–Mariano tests at 1 h. In the stable window it stays within 5% of A4b.
- The 80% interval covers 75–85% of observations (PICP).
- If the main model only ties A1, the paper becomes the sensor-correction note instead.
- The virtual Moroccan fleets are used in the main results only if the simulation, run at Safi with CAMS irradiance, reproduces Safi's measured daily energy within ±10% and its 15-min power with a correlation of at least 0.9. Otherwise they move to the supplement.

## 2. Data and methodology of work

The unit of analysis is the inverter (44 units, 5-min telemetry aggregated to 15 min). The 23 hourly stations form a secondary track, and the pyranometer is used only in the sensor baselines.

### Data inventory

| Source | Content | Resolution | Role in the paper |
| --- | --- | --- | --- |
| Inverter files (44) | AC power, DC voltage, per-phase values | 5 min | Main target and fleet, aggregated to 15 min |
| Site files, optimizer stations (37) | Station energy and power | 15 min | Cross-check of inverter sums only |
| Site files, no optimizer (23) | Station energy and power, incl. 9 with thin-film | 1 h | Secondary hourly track |
| Weather station | GHI, temperature, RH, rain, pressure, visibility, wind | 1 min | Sensor baselines A4 and A4b; optional past-weather ablation |
| Brick metadata (.ttl) | Inverter and module models, module counts, tilt, azimuth, connection dates | Static | AC rating, DC/AC ratio, tilt class, start-date checks |
| Safi rooftop (Mendeley b2s4ycc2gz) | 3 inverters: AC and DC power, reference cell, GHI, temperatures | 5 min, 2016–2018 | Real Moroccan case; validates the virtual fleets |
| CAMS solar radiation (time series and 0.1° grid) | All-sky and clear-sky GHI at HKUST, at Safi and over Marrakesh-Safi | 1 to 15 min | Independent check of the HKUST sensor; baseline A9; irradiance for the virtual fleets |
| Open-Meteo archive (ERA5) | Air temperature, wind and rain at 9 Moroccan points | 1 h | Cell temperature and soiling resets in the simulation |
| Benguerir building footprints | 29,225 buildings with area and confidence | Static | Roofs for the town-scale virtual fleet |
| PV density grid and province areas (regional PV maps) | 19,760 cells of relative PV density; 1.39 km² of detected PV | Static, 0.01° | Where the regional virtual fleet goes, and its total size |

### Units, capacities and errata

- **AC rating** P\_AC,u comes from the inverter model name (SE25K = 25 kW, SE82\_8K = 82.8 kW). It is cross-checked against the 99.9th percentile of observed power, which matches within 2% for 33 of 44 inverters. Of the other 11, two are metadata errors, several never reach their limit because their DC capacity is below or close to the AC rating (SQ567, UG Hall 2 2F, SQ Block S), and three exceed the nameplate by 5–6% (Zone A7, UG Hall 2 RF, SQ Apartment37-48).
- **DC rating** P\_DC,u = number of modules × module watt-peak (JKM390M = 390 Wp), from the module block linked to each inverter.
- **Errata to publish:** Indoor Sports Centre is listed as STP 10.0 but clips at 33.4 kW; the Zone D module blocks are swapped between its two inverters; Zone A2 has no module blocks; SQ Apartment37-48 Flexible PV is rated 3.72 kW but peaks at 6.7 kW (hourly track).
- Units with a metadata error keep the empirical AC limit and are left out of the DC/AC-prior test, but stay in the forecasting test with the g = 1 prior.

### Start dates and events

Three dates exist per unit: the metadata connection date, the first inverter telemetry, and the first site-file row (usually the 1st of a month; 5 of the 15-min and 23 of the hourly site files start mid-month). The paper uses **the first day of telemetry**, defined as the first day d on which the unit delivers valid power (P > 2% of P\_AC) in at least 70% of daylight slots on days d and d+1. The connection date is reported beside it, and gaps above 30 days are flagged.

**Observed vs left-censored starts.** Every inverter file is already producing on its first day, so an inverter file alone cannot prove commissioning. An event starts at the earliest production in any file, site or inverter. The start counts as observed only if that file begins before the unit produces: a mid-month first day with a morning ramp, or a file that precedes the others. If the earliest file begins on the 1st of a month with production already under way, the start is left-censored and the event moves to the sensitivity set. An operator could also have had history from the site meter before the inverter file began, which is why the site files are checked.

An **event** is one unit, or several units of the same station starting within 7 days. An event is eligible if at least 8 donor units have 14 days or more of history at its start, it has 30 or more valid daylight days in its first 90 days, and its AC rating is known.

**Test events (14 scored at 15 min).** "Stable" and "drifted" use a provisional sensor boundary of November 2022. The final boundary comes from change-point detection on the daily ratio of sensor to fleet index.

| # | Event | Observed start | AC (kW) | DC/AC | Type and notes | Sensor period |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | SQ Block S | 2021-10-05 | 33.3 | 1.04 | New station; connected 48 days earlier | Stable |
| 2 | Zone A5 | 2021-10-05 | 17.0 | 1.19 | New station | Stable |
| 3 | SQ Block R | 2021-10-06 | 33.3 | 1.14 | New station; connected 49 days earlier | Stable |
| 4 | Zone A7 | 2021-10-09 | 10.0 | 1.21 | New station, 10° east-west | Stable |
| 5 | Zone A6 | 2021-10-14 | 50.0 | 1.29 | New station; connected 75 days earlier | Stable |
| 6 | Zone J2 | 2021-11-13 | 50.0 | 1.39 | New station, mixed orientation; re-dated from the site file, which serves as target until the inverter file starts on 2021-12-08 | Stable |
| 7 | Indoor Sports Centre | 2021-11-17 | 33.3 | 1.31 | New station; inverter model in metadata wrong | Stable |
| 8 | Zone D (both inverters, station level) | 2022-01-19 | About 83 (observed peaks) | Metadata error | New station; site series as target, because inverter 1's file is missing until December 2022 | Stable |
| 9 | Library (3 inverters) | 2022-06-01 | 150.0 | 1.13 | New station; connected the day before | Stable |
| 10 | UG Hall 8 | 2023-01-05 | 25.0 | 1.04 | New station | Drifted |
| 11 | UG Hall 9 | 2023-02-11 | 25.0 | 1.08 | New station | Drifted |
| 12 | Zone A2 inverters 2 and 3 | 2023-05-16 | 105.0 | Metadata missing | Capacity addition, confirmed by the station total | Drifted |
| 13 | SQ Block P | 2023-06-22 | 33.3 | 1.12 | New station | Drifted |
| 14 | Shaw Auditorium | 2023-07-09 | 66.6 | 1.33 | New station, mixed orientation | Drifted |

**Sensitivity set, left-censored starts (3):** Wong Check She (both files start on 2021-12-01, already producing; connected 92 days earlier), Zone J1 (site file starts on 2022-03-01, already producing; connected 113 days earlier), Zone L2 (site file starts on 2022-06-01, already producing, with 405 kWh before its inverter file begins on 2022-08-02).

**Removed (2):** Zone D inverter 1, because the station total ran at 1.6–1.7 × inverter 2 from January to October 2022, so its file starting on 2022-12-03 marks the end of an outage, not a new unit. S H Ho Sports Hall, because its first months are anomalous and its start is also left-censored.

**Validation events (tuning only, never scored in the paper's main tables):** the 10 units that started between 2 June and 15 July 2021 (SQ567, UG Hall 2 2F and RF, Zone A1, Zone A4, Zone A2 inverter 1, the four SQ Apartment blocks). They have 8 or more donors and lie before every test event. A donor must have started at least 14 full days before the event; SQ567 reaches 8 donors only because SQ3 started exactly 14 days before it. Every threshold, hyperparameter and prior weight is frozen on them.

**Hourly track:** about 8 more events (Tower A, SQ18, SQ Block Q and Q phase 2, and the four flexible thin-film roofs), run with the same code at 1-h resolution.

### Preprocessing, in order

1. **Time base.** All timestamps in Hong Kong time (UTC+8, no daylight saving). Two formats occur: 13 inverter files and 10 site files write year/month/day (2021/6/2 6:00); both formats are parsed explicitly, and any timestamp that fails stops the run. Inverter files cover 06:00–17:55 (144 rows a day); the site files show that energy after 18:00 is a median 0.17% of the total and at most 0.5% in June. The interval-labelling convention (start or end of interval) is fixed by maximizing the correlation between fleet power and clear-sky irradiance over shifts of −7.5 to +7.5 min; the pilot found a lead of about 5 min.
2. **Quality control per inverter.** Remove negative values and night power. Flag frozen values (constant for 1 h or more in daylight), values above 1.05 P\_AC, and outages (zero power while the fleet index exceeds 0.3). Flagged slots are excluded from gain fitting; scoring keeps them, with an outage-excluded sensitivity.
3. **Aggregation.** The 15-min mean of the three 5-min values, valid if at least 2 are present.
4. **Clear-sky and geometry.** pvlib solar position (NREL SPA) at the interval midpoint and Ineichen–Perez clear-sky GHI with pvlib's monthly Linke turbidity, at 22.3363° N, 114.2634° E. The coarse metadata coordinates are not used.
5. **Normalization.** y\_u(t) = P\_u(t) / P\_AC,u, and G̃(t) = G\_cs(t) / 1000.
6. **Clipping flag.** A slot is censored when y\_u(t) ≥ 0.97.
7. **Units, start dates and events,** as defined above.
8. **Sensor processing** (for A4 and A4b only): BSRN-style physical limits, night-offset removal, spike removal, monthly clear-sky recalibration, and change-point detection of the drift (Section 4).
9. **Hourly track:** the same steps at 1 h, with station-level ratings.

&#91;embedded content: data processing · 3 sources, 7 steps, 3 outputs\]

Only the fleet panel feeds the main model. The sensor index exists only for the sensor baselines, so the drifting pyranometer can never leak into the method.

### Information set and leakage controls

A forecast issued at time t for target t + h may use only what an operator would have at t.

| Item | Allowed | Reason |
| --- | --- | --- |
| Donor power up to and including t | Yes | Observed at issue time |
| Donor power after t | No | Using it makes the result a nowcast (oracle A7 only) |
| Clear-sky geometry at t + h | Yes | Deterministic, known in advance |
| AC rating, module count, module model of the new unit | Yes | Nameplate, known at commissioning |
| Gains of donors fitted on data before the event start | Yes | Past data |
| Any power of the new unit before or at the forecast issue | No in cold-start mode; yes only in the 90-day update curve | That is the point of cold start |
| Measured GHI | Only in A4, A4b, A4c | The tested hypothesis |
| Past non-irradiance weather (temperature, RH, visibility) | Optional ablation only | Causal, but not needed |
| Scalers, thresholds, hyperparameters fitted on test events | No | Frozen on validation events |

Five traps are checked and reported: same-time peer power, random site hold-out, normalization with the unit's own future maximum, gains fitted on windows that include the test period, and k labels that contain the test unit.

## 3. Algorithms and equations

Each inverter's normalized power is modelled as one shared campus index times one slow inverter gain, capped at the inverter limit. Everything else in the method follows from that factorization.

&#91;embedded content: method architecture · index branch, gain branch, 90-day update\]

The index branch (top row) is the same for every new inverter. Only the gain branch (middle row) uses the new inverter's nameplate, and its own power enters only through the 90-day update.

### 3.1 Notation

| Symbol | Meaning |
| --- | --- |
| u, e, s\_e | Inverter unit; event; first telemetry day of event e |
| D\_e | Donor set: units online at least 14 days before s\_e, excluding the event's own units |
| t, h | Issue time; horizon in 15-min steps, h ∈ {1, 2, 4, 8, 16, 24} (15 min to 6 h) |
| P\_u(t), P\_AC,u, P\_DC,u | Mean AC power; AC rating; DC rating (modules × Wp) |
| r\_u = P\_DC,u / P\_AC,u | DC/AC ratio from nameplate |
| y\_u(t) = P\_u(t) / P\_AC,u | Normalized power, between 0 and about 1 |
| G\_cs(t), G̃(t) = G\_cs(t)/1000 | Clear-sky GHI (Ineichen–Perez); its normalized value |
| k(t), g\_u | Campus clear-sky index (shared); inverter gain (slow) |
| τ, K = 9, M = 200 | Quantile level 0.1 to 0.9; number of quantiles; ensemble members |

### 3.2 Factor model

```latex
y_u(t) = \min\{1,\; g_u\, k(t)\, \tilde G(t)\} + \varepsilon_u(t)
```

Physically, y\_u ≈ r\_u × PR\_u × T\_u(t) × k\_GHI(t) × G̃(t), where PR is the system performance ratio and T = POA/GHI the transposition ratio. The gain therefore collects the DC/AC ratio, system losses, orientation, shading and soiling. The min{1, ·} is the inverter limit.

**Identifiability.** (g, k) and (c g, k/c) give the same fit, so the scale is fixed by median ĝ\_d = 1 over the donors. This is why the donor-median prior is always about 1.0 and carries no information about a new unit.

The residual ε holds cloud differences across the 60 ha campus, the diurnal shape left by tilt and shading, and measurement noise.

### 3.3 Estimating k(t) from the donors

Each unclipped donor gives an implied index:

```latex
\kappa_d(t) = \frac{y_d(t)}{\hat g_d\, \tilde G(t)}, \qquad d \in U_t = \{d \in D_e \text{ online at } t:\ y_d(t) < 0.97\}
```

**Estimator (a), robust median** (baseline A2): k̂(t) = median of κ\_d(t) over U\_t, clipped to \[0, 1.5\].

**Estimator (b), censored Huber**, using all online donors O\_t, clipped ones included:

```latex
\hat k(t) = \arg\min_{k \in [0,\,1.5]} \sum_{d \in O_t} \rho_\delta\!\left(y_d(t) - \min\{1,\; \hat g_d\, k\, \tilde G(t)\}\right)
```

```latex
\rho_\delta(r) = \begin{cases} r^2/2 & |r| \le \delta \\ \delta\,(|r| - \delta/2) & |r| > \delta \end{cases}, \qquad \delta = 0.05
```

A clipped donor costs nothing as long as ĝ\_d k G̃ ≥ 1, so it acts as a lower bound k ≥ 1/(ĝ\_d G̃) instead of being thrown away. The fit is a 1-D grid search (step 0.005) refined by golden section, run only when G̃ > 0.05.

Alongside k̂(t), three fleet-state descriptors are kept: σ(t), the IQR of κ\_d(t); c(t), the share of donors clipped; and n(t) = |U\_t|. Estimator (b) is kept only if it beats (a) on the validation events. Otherwise "censored" leaves the title.

### 3.4 Estimating donor gains (alternating fit)

1. Start with ĝ\_d = 1 for every donor.
2. Compute k̂(t) with the current gains.
3. For each donor d, recompute the leave-one-out index k̂^(−d)(t) without d, so a gain is never fitted against an index that contains its own unit.
4. Fit each gain on its valid window V\_d = {s\_d ≤ t < s\_e, G̃ > 0.2, k̂^(−d) > 0.5, slot not flagged}:

```latex
\hat g_d = \arg\min_{g \in [0.3,\,1.5]} \sum_{t \in V_d} \rho_\delta\!\left(y_d(t) - \min\{1,\; g\, \hat k^{(-d)}(t)\, \tilde G(t)\}\right)
```

5. Renormalize so that the median gain is 1.
6. Repeat steps 2–5 five times (the pilot converged in three).

The condition k̂ > 0.5 keeps clear and near-clear slots, where differences in cloud edges between roofs are smallest. It is tunable on the validation events.

### 3.5 DC/AC gain prior

```latex
\hat g^{\,prior}_{new} = \hat\beta_e\, r_{new}\, T_{new}, \qquad \hat\beta_e = \operatorname*{median}_{d \in D_e^{meta}} \frac{\hat g_d}{r_d\, T_d}
```

- r = P\_DC/P\_AC comes from the nameplate. D\_e^meta is the set of donors with clean metadata.
- T\_u is the transposition factor, Σ POA\_cs,u / Σ GHI\_cs over the target month (pvlib, Perez model, albedo 0.2) for units with a known tilt and azimuth. T = 1 for flat and "Mixed" units.
- Three prior variants are tested: G0 (g = 1, the donor median), G1 (β r) and G2 (β r T). G2 is kept only if it beats G1 on the validation events.
- **Uncertainty:** the empirical set B\_e = {ĝ\_d / (r\_d T\_d)} over the donors. Ensemble member m draws b^(m) from B\_e and uses g^(m) = b^(m) r\_new T\_new.
- **Meaning of β:** the fleet's effective performance ratio on the k scale (about 0.94 in the pilot).
- **Free diagnostic:** since the prior scales with r, the model also predicts how often the new inverter will clip. Predicted and observed clipping shares are compared over the first 90 days.
- **Pilot evidence:** correlation 0.64 between r and the true gain. The median gain error falls from 0.059 to 0.032 and the mean from 0.105 to 0.064 (15 clean events, leave-one-out β). Library, Zone L2 and Zone J2 sit below the prediction, which suggests mixed orientation or shading and is a reason to test G2.

### 3.6 Gain update over days 1–90

After n days, the local gain ĝ\_loc(n) is the same Huber fit on the new unit's own data from s\_e to s\_e + n, against the donor index. Prior and local estimate are combined by normal–normal shrinkage:

```latex
\hat g(n) = \frac{\hat g^{\,prior}/\sigma_p^2 + \hat g_{loc}(n)/\sigma_{loc}^2(n)}{1/\sigma_p^2 + 1/\sigma_{loc}^2(n)}, \qquad \sigma_{loc}^2(n) = \frac{s_1^2}{n_{eff}(n)}
```

Equivalently, ĝ(n) = (w0 ĝ\_prior + n\_eff ĝ\_loc) / (w0 + n\_eff), with w0 = s\_1² / σ\_p² in days.

- **Empirical Bayes, not a guess:** σ\_p² is the robust (MAD-based) variance of the leave-one-out prior errors among donors, and s\_1² is the variance of one-day local gain estimates among donors. Both come from donor data before s\_e, so w0 is computed, not chosen.
- n\_eff = the number of valid days with at least 8 unclipped slots where G̃ > 0.2.
- **Retirement day n\*** per event: the first day on which a local-only model (smart persistence or LightGBM on the unit's own history) has a 7-day rolling nRMSE at or below the cold-start model's. The day when the prior's weight w0/(w0 + n\_eff) falls under 0.1 is reported beside it.

### 3.7 Forecasting k(t + h)

State at issue time t (L = 16 lags = 4 h):

```latex
\mathbf{s}_t = \big(k_t, \ldots, k_{t-L+1},\ \bar k_{1h},\ \bar k_{2h},\ \mathrm{sd}_{1h}(k),\ \Delta k_t,\ \sigma_t,\ c_t,\ n_t,\ k_{t+h-96}\big)
```

Here k\_(t+h−96) is the index at the target slot one day earlier, known at t because h ≤ 24.

Known future geometry:

```latex
\mathbf{u}_{t+h} = \big(\tilde G(t+h),\ \cos z(t+h),\ \sin\alpha(t+h),\ \cos\alpha(t+h),\ \sin\omega(t+h),\ \cos\omega(t+h),\ \sin\tfrac{2\pi\, doy}{365},\ \cos\tfrac{2\pi\, doy}{365}\big)
```

where z is the solar zenith, α the solar azimuth and ω the hour angle. Direct models, one per horizon and quantile, are trained with the pinball loss:

```latex
\hat k^{(\tau)}_{t+h} = f_{h,\tau}(\mathbf{s}_t, \mathbf{u}_{t+h}), \qquad \ell_\tau(k, \hat k) = \max\{\tau (k - \hat k),\ (\tau - 1)(k - \hat k)\}
```

The 9 outputs are sorted so quantiles never cross (monotone rearrangement, Chernozhukov et al. 2010). Forecasts are issued in daylight (G̃(t) > 0.05, n\_t ≥ 8) and scored when G̃(t + h) > 0.02. Horizons that cross the night are not issued. Because the files stop at 17:55, issue times run from 06:00 to 17:55 minus the horizon: a 6-h forecast is issued no later than 11:55, so each horizon covers a different part of the day. Comparisons across horizons therefore use the common target window 12:00–17:55, which every horizon reaches; full-window scores per horizon are secondary.

### 3.8 From index quantiles to the power distribution

The quantile function Q\_k is linear between the 9 quantiles, with linear tails bounded to \[0, 1.5\]. Members use stratified levels τ^(m) = (m − 0.5)/M, which cuts Monte Carlo noise compared with random draws. Gain draws g^(m) come from Section 3.5, independent of k.

```latex
P^{(m)}(t+h) = P_{AC}\, \min\{1,\; g^{(m)}\, Q_k(\tau^{(m)})\, \tilde G(t+h)\}, \qquad m = 1, \ldots, 200
```

Power quantiles are the empirical quantiles of the members. The point forecast is the member mean when scoring RMSE and the member median when scoring MAE, because each score is minimized by a different summary (Gneiting 2011).

### 3.9 Metrics

Scoring set S = daylight targets (G̃(t + h) > 0.02) with a valid observation. Every error is normalized by P\_AC, never by mean power.

```latex
\mathrm{nMAE} = \frac{1}{|S|\,P_{AC}} \sum_{S} |P - \hat P|, \quad \mathrm{nRMSE} = \frac{1}{P_{AC}}\sqrt{\frac{1}{|S|}\sum_{S} (P - \hat P)^2}, \quad \mathrm{nMBE} = \frac{1}{|S|\,P_{AC}} \sum_{S} (P - \hat P)
```

```latex
\mathrm{SS} = 1 - \frac{\mathrm{nRMSE}}{\mathrm{nRMSE}_{ref}}, \qquad \hat k^{\,CLIPER}_{t+h} = w_h\, k_t + (1 - w_h)\, \bar k^{\,clim}_{t+h}
```

The main reference is A1 (persisted fleet index). The stronger reference that reviewers expect is the optimal convex combination of climatology and persistence (Yang 2019), with w\_h fitted on training data.

**Probabilistic scores.** The CRPS from members, normalized by P\_AC:

```latex
\mathrm{CRPS} = \frac{1}{M}\sum_{m} |x_m - y| - \frac{1}{2M^2}\sum_{m}\sum_{m'} |x_m - x_{m'}|
```

```latex
\mathrm{PICP}_{80} = \frac{1}{|S|}\sum_S \mathbf{1}\{q_{0.1} \le y \le q_{0.9}\}, \quad \mathrm{PINAW} = \frac{1}{|S|\,P_{AC}} \sum_S (q_{0.9} - q_{0.1}), \quad \mathrm{ACE} = \mathrm{PICP}_{80} - 0.8
```

```latex
\mathrm{IS}_\alpha = (U - L) + \frac{2}{\alpha}(L - y)\,\mathbf{1}\{y < L\} + \frac{2}{\alpha}(y - U)\,\mathbf{1}\{y > U\}, \qquad \alpha = 0.2
```

The interval score (Winkler) is proper and rewards narrow intervals only when they still cover. The CRPS skill is measured against a probabilistic persistence ensemble (PeEn): the fleet index at the same slot over the last 20 days, times the prior gain. Reliability is shown with PIT histograms and per-quantile reliability diagrams.

**Aggregation.** Each metric is computed per event and horizon, then reported as the median and IQR across events. Pooled values weighted by capacity are secondary.

**Conditional verification** by sky class of the fleet index at the target (clear > 0.8, mixed 0.4–0.8, overcast < 0.4), by season (dry October–March, wet April–September) and by clipping status.

### 3.10 Catalogue of error sources and pitfalls

| Source | Effect | Detection | Treatment |
| --- | --- | --- | --- |
| Pyranometer step drift in 2023 | Irradiance-based models biased | Change point in the daily sensor/fleet ratio | Never an input; used only in A4, A4b, A4c |
| Night offset up to about 30 W/m² | Low-irradiance values inflated | Median at solar elevation below −6° | Subtracted in A4b |
| Spikes up to 3,600 W/m² | Outliers | BSRN physical limits | Removed |
| Interval-label convention | Phase error inflates 15-min error | Lag correlation with clear-sky | One fixed shift |
| Inverter clipping | Index pulled down at noon | y ≥ 0.97 | Censored estimator; clipped slots scored separately |
| Cloud differences within 60 ha | Irreducible error at 15 min | Oracle A7 error | Reported in the error budget |
| Orientation and shading | Gain varies over the day | Residual by hour of day | Transposition factor (G2); shape residual reported |
| Soiling and rain cleaning | Slow gain drift | Trend in ĝ\_loc | 90-day update |
| Metadata errors | Wrong prior | Observed peak vs rating | Errata; empirical AC; left out of the prior test |
| Ambiguous start dates | Wrong event start | Three dates compared | First-telemetry definition |
| Capacity expansions | Wrong normalization | Inverter units | One event per added inverter group |
| Missing data and outages | Biased scores | QC flags | Outage-excluded sensitivity |
| Only 14 scored events, 5 of them drifted | Low power for small gains | Not applicable | Event-wise tests, effect sizes, no claims under about 3% |
| Leakage traps | Inflated skill | Information set | Leakage-inflation table (Section 6) |
| Daily window 06:00–17:55 in the inverter files | Evening energy missing (at most 0.5% in June); each horizon covers a different part of the day | File inspection; site files run 00:00–23:45 | Issue window 06:00 to 17:55 minus the horizon; common target window 12:00–17:55 |
| Left-censored starts | False cold starts | Site vs inverter files, connection dates | Observed-start rule; 3 events moved to the sensitivity set |
| Two timestamp formats | Silent parsing errors | Format check per file | Explicit two-format parser that stops on any failure |

## 4. Error budget, sensor baseline, capacity additions, statistics and release

These five pieces turn a forecasting result into a defensible paper: each answers a question a reviewer will ask.

&#91;embedded content: analysis flow · freeze, event loop, scoring, three analyses\]

The event × model × horizon table is the single source of every test, budget and figure, so no number in the paper is computed outside it.

### 4.1 Error budget: index vs gain vs residual

Four runs share the same code and differ only in what is replaced by its true value:

| Run | Index k(t + h) | Gain g |
| --- | --- | --- |
| F (full model) | Forecast | Prior |
| O\_k | True future fleet index | Prior |
| O\_g | Forecast | True gain g\* |
| O\_kg | True future fleet index | True gain g\* |

The true gain g\* is fitted after the fact on the new unit's own 90-day window, for the oracles only. With MSE(·) the event's mean squared normalized error, the two-factor Shapley split is exact:

```latex
E_{res} = \mathrm{MSE}(O_{kg})
```

```latex
E_k = \tfrac{1}{2}\big[(\mathrm{MSE}(F) - \mathrm{MSE}(O_k)) + (\mathrm{MSE}(O_g) - \mathrm{MSE}(O_{kg}))\big]
```

```latex
E_g = \tfrac{1}{2}\big[(\mathrm{MSE}(F) - \mathrm{MSE}(O_g)) + (\mathrm{MSE}(O_k) - \mathrm{MSE}(O_{kg}))\big], \qquad E_k + E_g + E_{res} = \mathrm{MSE}(F)
```

The shares are reported per horizon as stacked bars, and the same split is repeated with the CRPS. The pilot already points to the story: the gain dominates at 15 min (the true gain cuts nRMSE from 0.097 to 0.081), while the index forecast dominates beyond 1 h (at 6 h the true gain changes almost nothing). This tells an operator what to improve first: nameplate data for very short horizons, cloud forecasting for longer ones.

### 4.2 Corrected-sensor baseline A4b

A4b answers the reviewer who says "just recalibrate the sensor". It uses the pyranometer alone, never the fleet, and every step is causal.

1. **Physical limits.** Remove GHI above 1.2 S0 cos(z)^1.2 + 50 W/m² or below −2 W/m² (BSRN "extremely rare" limits, Long & Shi 2008).
2. **Night offset.** o(d) = median of measured GHI at solar elevation below −6° over the trailing 7 days; G' = G − o(d).
3. **Clear-sky detection on the sensor itself** (pvlib detect\_clearsky, Reno & Hansen 2016) on the 1-min data.
4. **Monthly calibration from the previous month:** c\_(m−1) = median of G\_cs / G' over its detected clear minutes with zenith below 70°; G\_corr = c\_(m−1) G'. A same-month (non-causal) calibration is a sensitivity run.
5. **Same learner, different index.** A4b is the main model with k\_sens = G\_corr / G\_cs in place of the fleet index, and donor gains refitted against k\_sens. This isolates the value of the index source.

Two related runs complete the ablation. **A4c** gives the main model both the fleet index and the corrected sensor index. The **drift change point**, found by PELT on the daily log-ratio of measured GHI to the fleet proxy k̂ G\_cs, only defines the stable and drifted periods used in reporting; it is never an input.

The open question that A4b settles: can a one-month calibration lag follow a step change, or does the fleet remain better even against a recalibrated sensor?

### 4.3 Capacity additions as events

- **Zone A2 inverters 2 and 3** (first telemetry 2023-05-16) are the only confirmed capacity addition: the station total equals inverter 1 alone until May 2023.
- **Zone D inverter 1 is not an addition.** The station total ran at 1.6–1.7 × inverter 2 from January to October 2022, so inverter 1 was producing from the start; its file starting on 2022-12-03 marks the end of an outage. Zone D is scored as one station-level event from 2022-01-19.
- The existing inverter on the same roof stays in the donor set. A sensitivity run without same-roof donors shows that results are not flattered by the nearest neighbour.
- **Operator baseline A8, same-roof scaling:** the new inverters are forecast with the existing inverter's normalized forecast. This is what an operator would do without our method.
- **Station-level view:** during the expansion month, the station forecast is the old inverter's own-history forecast plus the cold-start forecast of the new ones. It is compared with scaling the old forecast by the capacity ratio.
- Zone A2 has no module metadata, so the DC/AC prior cannot be tested on it. It uses G0 and is flagged in the event table.

### 4.4 Statistics

- **Primary horizon, fixed before scoring: 1 h.** Every hypothesis test is run at 1 h; the other five horizons are secondary, with Holm correction.
- **Primary test:** a one-sided Wilcoxon signed-rank test on event-wise differences Δ\_e = nRMSE\_main − nRMSE\_ref at 1 h, with n = 14 scored events and exact p-values.
- **Effect size:** the Hodges–Lehmann median difference with its 95% confidence interval, plus the share of events won. Wording in the paper follows effect sizes, not only p-values.
- **Comparisons:** main model vs A1 (primary), vs CLIPER, and vs A4 and A4b split by sensor period.
- **Drifted window: effect sizes only.** It holds about 5 events, so the smallest one-sided exact Wilcoxon p is 1/32 ≈ 0.031 (1/16 if only 4 remain), and no Holm-corrected test can reach significance. The paper reports Hodges–Lehmann differences with day-block bootstrap intervals and the number of events won. Significance comes from per-event Diebold–Mariano tests at 1 h, with Holm across the drifted events.
- **Drift boundary, fixed before scoring:** PELT on the daily log-ratio of measured GHI to the fleet proxy. An event belongs to the drifted window if at least half of its 90 test days fall after the boundary.
- **Day-block bootstrap within each event:** resample whole days with replacement, B = 2,000, giving the confidence interval of each event's metric and skill. A 3-day moving-block version (Künsch 1989) covers multi-day weather regimes.
- **Hierarchical bootstrap for campus-level claims:** resample events, then days within each event, for the 95% interval of the median skill.
- **Diebold–Mariano test per event:** squared loss, Newey–West variance with lag h − 1, Harvey–Leybourne–Newbold small-sample correction, reported for every event at 1 h.
- **Power check before writing claims:** the minimum detectable difference is simulated from the pilot's event-wise spread. No claim is made below it.

### 4.5 Release: code, event table and sensor flags

| Item | Content |
| --- | --- |
| Code repository (GitHub, archived on Zenodo with a DOI) | Data preparation, estimators, priors, models, evaluation, statistics; one script per table and figure; one command reproduces everything |
| Frozen configuration | Hyperparameters and thresholds as YAML, with the hash of the validation run that fixed them |
| Event table | event\_id, station, units, AC\_kW, DC\_kWp, dcac, tilt\_class, connection\_date, first\_telemetry, first\_site\_row, gap\_days, n\_donors, valid\_days\_90, sensor\_period, exclusion\_flag, note |
| Unit table and errata | AC from the model name, DC from modules, observed peak, the four metadata errors |
| Sensor package | QC flags, night offset, corrected GHI (A4b), drift change points |
| Environment | Pinned package versions and random seeds |
| Moroccan package | Safi audit, CAMS processing, the virtual-fleet generator with all its assumptions, the 8 PV clusters |

Licences: MIT for the code and CC BY 4.0 for the derived data. The original Dryad licence (reported as CC0) is confirmed before release.

## 5. Models

The main model is quantile LightGBM on the fleet state (9 quantiles × 6 horizons = 54 models per training origin), with the censored index and the DC/AC prior. Every other model removes exactly one claim, so each row of the results table tests one sentence of the paper.

### 5.1 All models

| ID | Model | Claim it tests |
| --- | --- | --- |
| **Main** | Censored index + DC/AC prior + quantile LightGBM | The full method |
| A0 | Climatological index (slot median over the last 60 days) × prior gain; probabilistic version from the same 60 days | Cloud dynamics matter |
| A1 | Persisted fleet index × prior gain; PeEn ensemble for probabilistic scores | Learning beats persistence |
| CLIPER | Optimal convex combination of A0 and A1 (Yang 2019) | Learning beats the strongest simple reference |
| A2 | Main model with the median index (no censoring) | The censored estimator is needed |
| A3 | Main model with g = 1 (prior G0) | The DC/AC prior is needed |
| A4 | Same learner on the raw pyranometer index | The sensor fails after the drift |
| A4b | Same learner on the corrected pyranometer index | The fleet beats even a recalibrated sensor |
| A4c | Main model plus the corrected sensor index | Adding the sensor helps or hurts |
| A5 | k-nearest-neighbour analogs in the fleet-state space (K = 50), quantiles of their future index | Boosting beats analog forecasting (a cross-learning style baseline) |
| A6 | TCN on the same inputs | A neural model adds nothing (or something) |
| A7 | Same-time fleet index (oracle, labelled as not a forecast) | Upper bound; virtual metering |
| A8 | Same-roof scaling (capacity additions only) | Beats what an operator would do |
| L1, L2 | Smart persistence and LightGBM on the unit's own history (90-day curve only) | When to retire the cold-start model |
| A9 | Satellite (CAMS) clear-sky index persisted forward × prior gain | The fleet beats satellite irradiance without a local sensor (optimistic about data latency) |

&#91;embedded content: model family · 3 parts of the main model, 15 swaps\]

Every comparison changes one part and keeps the other two equal to the main model, so a difference in skill can be traced to that part alone.

### 5.2 Quantile LightGBM

| Setting | Value |
| --- | --- |
| Objective | quantile, alpha = τ ∈ {0.1, …, 0.9} |
| Models per origin | 54 (one per horizon and quantile) |
| num\_leaves | 31 |
| learning\_rate | 0.03 |
| n\_estimators | up to 2,000, early stopping after 100 rounds on the last 20% of the training window (by time) |
| min\_data\_in\_leaf | 100 |
| feature\_fraction, bagging\_fraction | 0.8, 0.8 (bagging every iteration) |
| lambda\_l2 | 1.0 |
| Seed | Fixed, reported |

The values above are starting points. They are tuned once on a small grid (num\_leaves 15/31/63, learning rate 0.03/0.05, min\_data\_in\_leaf 50/100/200), by time-series cross-validation on the fleet index from May to September 2021, then frozen.

**Pooled-horizon variant (ablation):** one model per quantile with h as a feature (9 models). It shares data across horizons and is often more data-efficient.

### 5.3 Rolling origin, event by event

1. For event e, the index series k^(−e) is built only from its donor set D\_e, so it never contains the event's own units.
2. Origins are o ∈ {s\_e, s\_e + 30 days, s\_e + 60 days}. At each origin the model is trained on every pair (t, t + h) with t + h < o, from the fleet's start (15 May 2021): an expanding window. It forecasts \[o, o + 30 days).
3. Gains and the prior stay fixed at s\_e in cold-start mode. They change only in the 90-day update curve.
4. Size: 17 events (14 scored, 3 sensitivity) × 3 origins × 54 models = 2,754 LightGBM fits. Each takes seconds, so the full run should fit in a few hours on a laptop (estimate).
5. Stability ablation: a single origin at s\_e, with no refit.

### 5.4 TCN ablation

- **Input:** the last 32 steps (8 h) of \[k, σ, c, n, G̃, cos z\], night steps masked, plus the future geometry u\_(t+h) for each of the 6 horizons.
- **Encoder:** 3 residual blocks of causal dilated 1-D convolutions, kernel 3, dilations 1, 2 and 4, 32 channels, dropout 0.1, weight normalization.
- **Head:** the encoder's last step concatenated with u\_(t+h), then an MLP of 64 units to 54 outputs (6 horizons × 9 quantiles), sorted per horizon.
- **Training:** mean pinball loss, Adam (learning rate 1e-3), batch 256, early stopping (patience 10) on a time-ordered validation split, same rolling origins as LightGBM. Five seeds; mean and standard deviation reported.
- **Rule:** if it does not beat LightGBM on the validation events, it appears once in the ablation table and nowhere in the title or abstract.

&#91;embedded content: forecaster architectures · LightGBM bank (main) and TCN (ablation)\]

Because both forecasters share inputs, outputs and training windows, the TCN ablation measures only the value of a learned sequence encoder.

### 5.5 Results tables the models feed

1. Main table: models × horizons, median event-wise nRMSE with IQR, plus a dot per event in a figure.
2. Probabilistic table: CRPS, PICP80, PINAW and interval score, with CRPS skill vs PeEn.
3. Sensor table: A4, A4b and A4c vs main, split into stable and drifted events.
4. Prior table: G0, G1 and G2 gain errors and their effect on nRMSE at 15 min and 1 h.
5. Estimator table: median vs censored index.
6. Leakage-inflation table (Section 6).
7. Hourly track table, including the thin-film roofs.

Metrics and tests are defined once, in Sections 3.9 and 4.4.

### 5.6 Software

Python 3.11 with pandas, pvlib, lightgbm, PyTorch (TCN only), ruptures (change points), scipy and statsmodels (tests). The final runs go on your computer or Google Colab, because my workspace cannot install pvlib or LightGBM.

### 5.7 Notebooks

The study runs in 13 notebooks backed by one small Python package (`pvcold/`) that holds every function. Each notebook stays short, reads the previous notebooks' saved outputs (parquet files) and writes its own, so any notebook can be rerun alone. Nothing after NB3 may change the frozen configuration.

| Notebook | What it does | Main outputs | Paper exhibits |
| --- | --- | --- | --- |
| NB0\_setup\_config | Checks the environment (pvlib, LightGBM, PyTorch), sets paths and seeds, writes the config file | config.yaml, environment lock | — |
| NB1\_hkust\_audit | Inventory, metadata parsing, errata, sensor drift checks, drift change point, CAMS check of the HKUST sensor | Unit table draft, errata, sensor flags | Fig. 2, errata appendix |
| NB2\_preprocessing\_events | QC, 15-min aggregation, clear-sky, normalization, clipping flags, start dates, test and validation events | Fleet panel, event table | Fig. 1, event table |
| NB3\_index\_gains\_prior | Median vs censored index, donor gains, DC/AC priors G0/G1/G2, tuning on validation events, then the freeze | Index series per event, gains, frozen config hash | Figs. 3–4, prior and estimator tables |
| NB4\_sensor\_baselines | Sensor QC, night offset, monthly recalibration for A4, A4b, A4c | Corrected sensor index | Sensor table inputs |
| NB5\_forecasting | Main LightGBM bank plus A0, A1, CLIPER, A2, A3, A5, A7, A8; rolling origin; 200-member composition | Forecast store (event × model × horizon) | — |
| NB5b\_tcn\_ablation | TCN, 5 seeds, on a GPU or Colab | TCN forecasts | Ablation row |
| NB6\_evaluation\_statistics | Scores, Wilcoxon with Holm, Hodges–Lehmann, bootstraps, Diebold–Mariano, error budget, conditional verification, leakage table | Score table, statistics tables | Main tables, Figs. 5–8 |
| NB7\_secondary\_analyses | 90-day gain update and retirement day, capacity additions, fleet size, hourly track | Secondary tables | Fig. 9, Fig. S1 |
| NB8a\_morocco\_safi | Safi audit (time base, raw files, ratings) and the T0, T1, T2 transfer experiments | Safi results | Paper §6.10 |
| NB8b\_virtual\_fleets | Simulates the Benguerir and regional fleets from CAMS and Open-Meteo, then validates the simulation against Safi | Virtual-fleet power series, Safi validation table | Fig. 12, supplement |
| NB8c\_regional\_radius | Local fleet index and the donor-radius test on the regional fleet | Skill vs radius and donor count | Fig. 11, paper §6.11 |
| NB9\_final\_figures\_tables | Every figure and table, drawn only from saved outputs in one style | PDF and SVG figures, LaTeX tables | All |

The released kit (Section 8) is the same package with NB2 to NB6 run on a new site's files.

&#91;embedded content: notebook flow · 13 notebooks, one freeze point\]

Everything above the dashed line may be tuned; everything below runs once with the frozen configuration, including the Moroccan test.

## 6. Improvements and tricks for a Q1 / IEEE-level paper

Q1 reviewers in solar forecasting reject on protocol before they reject on accuracy. Most of what follows makes the protocol impossible to attack, then makes the physics and the operator value visible.

### Make the claim hard to attack

1. **Freeze, then test.** Every threshold, hyperparameter and prior weight is fixed on the 2021 validation events, and the configuration hash is reported before any test event is scored. The paper says so in one sentence.
2. **Leakage-inflation table.** Rerun the main model under four leaky protocols: same-time peers, random site hold-out, gains fitted on windows that include the test period, and normalization by the unit's own future peak. Report how much each inflates skill. It is cheap, it makes the protocol a contribution, and it is the table other authors will cite.
3. **Strong references only.** Skill is reported against CLIPER and PeEn, not only against climatology. Point forecasts use the right summary for each score (mean for RMSE, median for MAE).
4. **Event-wise evidence.** A dot per event in every main figure, Hodges–Lehmann effect sizes, Holm-corrected Wilcoxon tests and hierarchical bootstrap intervals.
5. **A threats-to-validity paragraph:** one campus, 14 scored events, low tilt diversity, telemetry start vs grid connection, metadata errors.

### Make the physics visible

6. **Gain vs DC/AC scatter** with the β line, and the predicted vs observed clipping share of each new inverter.
7. **Error-budget stacked bars** by horizon (Section 4.1).
8. **Conditional verification** by sky class and season. Ramp events (the 5% largest changes of the index at the target) are an optional extra.

### Show operator value (the IEEE TSTE angle)

9. **Fleet-size sensitivity:** subsample the donors (3, 5, 8, 15, all) and answer "how many reference inverters does a campus need?". This is the most quotable practical result.
10. **Retirement day n\*:** a simple rule for when to switch from the cold-start model to a local one.
11. **Capacity-addition scenario** at station level, against capacity scaling.
12. **Use of the intervals:** energy-weighted errors in kWh, and the 80% interval as an input to reserve or curtailment planning.
13. **Computation cost table:** training and inference time per event on a laptop, to show the method is deployable.

### Optional upgrades (each needs your yes)

14. **Conformal cold-start intervals.** Calibrate the quantiles by split conformal prediction (CQR, Romano et al. 2019) on pseudo cold-starts, where each donor is treated as new before s\_e and scored with its prior gain. This gives a coverage guarantee if units are exchangeable, and fixes intervals that are too narrow when gain uncertainty is underestimated. It is a modern, citable addition.
15. **Past non-irradiance weather** (temperature, RH, visibility) as an ablation: does the weather station still add anything once the pyranometer is gone?
16. **Free weather-forecast baseline** for 2–6 h, if you can download historical Open-Meteo forecasts for Hong Kong.

### Paper outline

1. Introduction: the problem and its context, a one-paragraph gap statement, three contributions.
2. Related work (state of the art): forecasting reviews, clear-sky index and reference forecasts, upscaling and virtual metering, PV networks as sensors, cold-start and transfer, probabilistic verification, irradiance sensor quality. It ends with the gap table.
3. Data: HKUST fleet, inverter units, telemetry start events, the sensor audit.
4. Method: factor model, index estimators, gains, DC/AC prior, gain update, forecaster, probabilistic composition.
5. Experimental protocol: information set, rolling origin, baselines, metrics, statistics.
6. Results: main skill, probabilistic scores, error budget, sensor ablation, prior and estimator ablations, 90-day curve, capacity additions, fleet size, hourly track.
7. Discussion: operator guidance, limitations, threats to validity.
8. Future work: day-ahead forecasting, larger and steeper fleets, online gains and soiling, and the Moroccan transfer (Section 8 of this document).
9. Conclusion.
10. Appendices: leakage-inflation table, random site hold-out, hyperparameters, metadata errata.

### Figures

| # | Figure | Message |
| --- | --- | --- |
| 1 | Timeline of inverter start dates over the sensor periods | 14 observed starts span the sensor drift |
| 2 | Sensor drift, two independent checks | The pyranometer is not a stable reference |
| 3 | Fleet index vs sensor index vs clear-sky on a variable day | The fleet tracks clouds; clipping is handled |
| 4 | Gain vs DC/AC ratio | The prior is physical and predictive |
| 5 | Skill vs horizon for main, A1, CLIPER and A4b, with intervals | Where learning pays off |
| 6 | Event-wise nRMSE, one dot per event | The gain is consistent, not driven by one event |
| 7 | Error budget by horizon | Gain dominates short horizons, clouds long ones |
| 8 | Reliability diagram and interval width vs fleet dispersion | Intervals are calibrated and widen when peers disagree |
| 9 | 90-day gain-update curve with the retirement day | When to retire the cold-start model |
| S1 | Fleet-size sensitivity (supplement) | How many reference inverters a campus needs |
| 10 | Safi transfer results for T0, T1 and T2 | How much adaptation a Moroccan site needs |
| 11 | Skill vs donor radius in Marrakesh-Safi | How dense a reference network must be |
| 12 | Map of the Moroccan tests: Benguerir roofs, the 8 PV clusters, Safi | Where each Moroccan test sits |

### Venue

Check each journal's current quartile and scope page before submitting.

| Venue | Fit | What it needs from us |
| --- | --- | --- |
| Solar Energy (Elsevier, ISES) | Best fit: PV forecasting, method and protocol | The plan as written |
| Renewable Energy (Elsevier) | Good alternative | The same paper, broader framing |
| IEEE Transactions on Sustainable Energy | Possible if the operator angle is strong | Items 9–13 above, grid-operation framing, IEEE format and length limits |
| Applied Energy | Stretch for a single campus | A wider energy-system impact story |
| IEEE Journal of Photovoltaics | Weaker fit, more device- and system-oriented | Not recommended for this paper |

### Writing rules

- Never "a novel architecture". The method is a causal reformulation of the PV clear-sky index plus a physical prior and a protocol.
- Every number comes with its interval and its event count.
- No comparison with RMSE values from other countries' papers.
- Highlights (5 lines of at most 85 characters each) and a graphical abstract follow the journal's guide.

## 7. Paper blueprint

Each section of the paper has one job, a fixed list of subsections, and named exhibits produced by one part of the code. With Related work added, the paper's Data, Method, Protocol and Results become sections 3 to 6.

&#91;embedded content: paper structure · 3 contributions, where each is built and proven\]

If a results subsection cannot be traced back to one contribution, it moves to the supplement.

**Order of work.** Code and write Data and Method first, then freeze the Protocol before any test event is scored, then Results. Related work, Discussion, Future work and the Introduction come next, and the Abstract last. The code is one package with five parts: prep (QC, units, events, clear-sky), fleet (index, gains, prior), forecast (LightGBM, TCN, baselines, composition), evaluate (metrics, statistics, error budget) and report (tables, figures).

### Paper §2 — Related work (state of the art)

Job: show that each ingredient exists separately and that no work combines them causally, without a pyranometer, on real start dates. Every reference below is a candidate, checked in the full text before it is cited.

| Subsection | What it covers | Candidate references |
| --- | --- | --- |
| 2.1 PV power forecasting | Reviews, horizons, methods | Antonanzas et al. 2016; Yang et al. 2018 |
| 2.2 Clear-sky index and reference forecasts | Clear-sky models, smart persistence, CLIPER | Ineichen & Perez 2002; Pedro & Coimbra 2012; Yang 2019 |
| 2.3 Upscaling and virtual metering | Same-time estimation from reference plants | Lorenz et al. 2011; Engerer & Mills 2014; Killinger et al. 2017 |
| 2.4 PV networks as sensors | Forecasting from neighbouring systems | Lonij et al. 2013; Elsinga & van Sark 2017 |
| 2.5 Cold start and transfer | New sites without history | Bottieau et al. 2022; AutoPV; SolNet; PhysTrans 2026; time-series foundation models |
| 2.6 Probabilistic forecasting and verification | Proper scores, reliability | Gneiting & Raftery 2007; Gneiting 2011; Lauret et al. 2019 |
| 2.7 Irradiance sensor quality | QC limits, clear-sky detection, PV-derived irradiance | Long & Shi 2008; Reno & Hansen 2016 |
| 2.8 The gap | The comparison table of Section 1 | — |

### Paper §3 — Data

Job: make the reader trust the units, the events and the sensor diagnosis before any model appears.

| Subsection | Content | Exhibit | Code |
| --- | --- | --- | --- |
| 3.1 Site and fleet | Campus, 60 stations, 44 inverters, 2021–2023, climate | Fleet summary table | prep |
| 3.2 Inverter units and metadata | AC from the model name, DC from modules, DC/AC ratios, the four errata | Unit table (appendix), errata list | prep |
| 3.3 Telemetry start events | Observed-start rule, 14 scored and 3 sensitivity events, validation events | Event table; Fig. 1 timeline of starts over the sensor periods | prep |
| 3.4 Weather station and sensor audit | Drift, offset and spikes; change point | Fig. 2 sensor drift, two checks | prep |
| 3.5 Preprocessing and quality control | Time base, QC rules, aggregation, clear-sky, normalization, clipping | Data-processing diagram (Section 2 of this document) | prep |
| 3.6 Moroccan data | Safi rooftop, CAMS, Open-Meteo, Benguerir footprints, PV density grid | Fig. 12 map, Moroccan data table | prep (NB8a, NB8b) |

### Paper §4 — Method

Job: one equation per idea, each tied to a physical reason. Text follows Section 3 of this document.

| Subsection | Content | Exhibit |
| --- | --- | --- |
| 4.1 Factor model | min{1, g k G̃}, identifiability, physical reading | Method architecture diagram |
| 4.2 Fleet index estimators | Median and censored Huber, fleet-state descriptors | Fig. 3 index on a variable day |
| 4.3 Donor gains | Alternating leave-one-out fit | — |
| 4.4 DC/AC gain prior | β, transposition factor, uncertainty set | Equation box |
| 4.5 Gain update | Empirical-Bayes shrinkage, retirement day | — |
| 4.6 Index forecaster | State, geometry, quantile LightGBM, rearrangement | Forecaster architecture diagram |
| 4.7 Probabilistic composition | 200 members, point summaries | — |

### Paper §5 — Experimental protocol

Job: make leakage impossible and comparisons fair. This section is frozen before the test events are scored.

| Subsection | Content | Exhibit |
| --- | --- | --- |
| 5.1 Information set | What is allowed at issue time | Information-set table |
| 5.2 Events, validation and rolling origin | Leave-unit-out, origins at 0, 30 and 60 days | Analysis-flow diagram |
| 5.3 Baselines and ablations | A0 to A8, CLIPER, local models | Model-family diagram and table |
| 5.4 Metrics | Deterministic, probabilistic, conditional | Equations |
| 5.5 Statistics | Wilcoxon with Holm, Hodges–Lehmann, bootstraps, Diebold–Mariano | — |
| 5.6 Implementation | Software, frozen configuration, run time | Computation-cost table |

### Paper §6 — Results

Job: answer one question per subsection, in the order of the contributions. The expected findings are hypotheses from the pilot, not results.

| Subsection | Question | Exhibit | Expected finding |
| --- | --- | --- | --- |
| 6.1 Main skill | Does the method beat A1 and CLIPER, from day one? | Main table; Fig. 5 skill vs horizon; Fig. 6 event dots | Ties A1 at 15 min, wins from 30–60 min on |
| 6.2 Probabilistic scores | Are the intervals calibrated and sharp? | Probabilistic table; Fig. 8 reliability | PICP close to 80%, width grows with fleet dispersion |
| 6.3 Error budget | Where does the error come from? | Fig. 7 stacked bars | Gain dominates at 15 min, index beyond 1 h |
| 6.4 Sensor ablation | Does measured GHI help or hurt? | Sensor table, stable vs drifted | Helps or ties while stable, hurts after the drift |
| 6.5 Prior and estimator ablations | Are the DC/AC prior and the censored index needed? | Fig. 4 gain vs DC/AC; prior and estimator tables | Prior halves the gain error; censoring to be tested |
| 6.6 90-day curve | When should the cold-start model be retired? | Fig. 9 gain update and retirement day | To be measured |
| 6.7 Capacity additions | Does it work when a roof grows? | Station-level table vs A8 | To be measured |
| 6.8 Fleet size | How many reference inverters are needed? | Fig. S1 | To be measured |
| 6.9 Hourly track | Does it hold at 1 h, with thin-film? | Hourly table | To be measured |
| 6.10 External case: Safi, Morocco | Does it transfer to a Moroccan roof? | Safi table and figure (Section 8 of this document) | To be measured |
| 6.11 Regional reference network (Morocco, virtual) | How far away can reference inverters be? | Skill vs donor radius and donor count | To be measured |

### Paper §7 — Discussion

- **Operator guidance:** minimum donor count, retirement day, what nameplate data to collect at commissioning.
- **Why the fleet beats the sensor:** a shared index averages many roofs, and a single instrument has no redundancy.
- **Limitations:** one campus, low tilt diversity, 14 scored events, telemetry start instead of grid connection.
- **Threats to validity and the leakage lesson:** how much leaky protocols inflate skill.

### Paper §8 — Future work

1. **Transfer to Morocco:** the external Safi check, the link to satellite-detected rooftops in Marrakesh-Safi, and a regional follow-up study (Section 8 of this document).
2. **Day-ahead forecasting** with numerical weather prediction or satellite-derived irradiance as inputs to the index forecaster.
3. **Larger and steeper fleets,** where tilt diversity allows a real orientation transfer.
4. **Systems without nameplate data,** sized from aerial or satellite imagery.
5. **Online gains:** detecting soiling, faults and degradation from the gain drift.
6. **Hierarchical forecasts,** reconciled from inverter to station to feeder.
7. **Coverage guarantees** with conformal prediction, and time-series foundation models as index forecasters.

## 8. Morocco: how it enters the story

Morocco can enter this paper with real data. A public rooftop dataset from Safi, inside your Marrakesh-Safi region, can serve as an external case study, while the full Moroccan study becomes a follow-up paper. The main claims stay on HKUST, where the 14 scored events give statistical power.

### Why Morocco needs exactly this method

- **A wave of new systems with no history.** The implementing decree of Law 82-21 on self-production was published in March 2026 and took effect in June 2026. Owners can sell surplus up to 20% of their annual production, and one study estimates up to 28.6 GW of distributed solar potential ([pv magazine, 20 March 2026](https://www.pv-magazine.com/2026/03/20/morocco-finally-unlocks-solar-self%E2%80%91consumption/)). Every new roof starts with nameplate data and no history: the cold-start case.
- **Few reliable irradiance sensors on rooftops,** and dust that soils them, which is the sensor problem this paper documents.
- **Your first paper already maps where the panels are.** This paper forecasts what they produce from day one.

&#91;embedded content: Morocco chain · paper 1, this paper, kit, Safi check, follow-up\]

The gain prior of this paper is what lets a roof seen only from space receive a forecast; the Safi check and the kit make the Moroccan follow-up a data task.

### The bridge equation: systems seen from space

A roof detected by segmentation has a panel area A but no nameplate. Its DC capacity follows from the area, and its unknown DC/AC ratio is drawn from the fleet's distribution, which widens the prior honestly:

```latex
P_{DC} \approx A_{seg}\, \eta_{mod} \times 1\ \mathrm{kW/m^2}, \qquad g^{(m)} = b^{(m)}\, r^{(m)}\, T, \quad r^{(m)} \sim \{r_d\}_{d \in \text{fleet}}
```

Here η\_mod is about 0.20 for current mono-Si modules, b^(m) is drawn from the donor set B\_e, and the HKUST DC/AC ratios run from 1.02 to 1.39. This links paper 1 (where and how big) to paper 2 (how much power, from the first day).

### The Safi rooftop dataset (external case study)

| Item | Value |
| --- | --- |
| Site | Rooftop of the National School of Applied Sciences, Safi (32.3265° N, 9.2634° W), hot semi-arid climate |
| System | 5.94 kWp, three inverters: mono-Si, poly-Si and amorphous Si subarrays |
| Orientation | 32° tilt, facing south |
| Measurements | Inverter AC and DC power, plane-of-array irradiance (reference cell), GHI, ambient and module temperatures |
| Resolution and period | 5 min; June 2016 to July 2018 (mono-Si, amorphous Si), May to December 2018 (poly-Si) |
| Source | Id Omar et al., Data in Brief 34 (2021) 106756 ([article](https://pmc.ncbi.nlm.nih.gov/articles/PMC7843394)); data on [Mendeley](https://data.mendeley.com/datasets/b2s4ycc2gz), CC BY 4.0 |

**What it can test:**

1. **A new climate, tilt and technology.** Hot semi-arid with dust, 32° instead of 0–15°, and amorphous Si beside crystalline Si. Here the transposition factor of the G2 prior matters.
2. **The small-fleet limit.** The index from two inverters forecasts the third, which can be compared with the HKUST fleet-size curve at 2–3 donors.
3. **Fleet vs a calibrated on-site sensor,** a fair version of A4, since Safi has its own reference cell.
4. **A possible real staggered start:** the poly-Si series begins in May 2018, while the others run from 2016. The audit checks whether this is commissioning or a data gap.

**What it cannot test:** campus-scale cloud averaging (all three share one roof and one sky), and statistical claims (one to three events). It is reported as an external case study, never pooled with HKUST.

**Before using it:** download the files, run the same audit as for HKUST, and note that the article states module ratings as "255 kWp", most likely meaning 255 Wp.

### Transfer to Morocco without heavy domain adaptation

No classical domain adaptation is needed (adversarial training, feature alignment, deep fine-tuning), because the method is normalized by physics: power is divided by the AC rating, irradiance is replaced by a clear-sky index computed for each site's own sun and atmosphere, and the gain comes from the nameplate. Five parts still carry Hong Kong information and are checked one by one.

| Part | Hong Kong assumption | What differs in Safi | Adjustment |
| --- | --- | --- | --- |
| Time base | Hong Kong time, no daylight saving | Morocco used summer time in 2016–2018, suspended during Ramadan, then permanent UTC+1 from October 2018 | Align every day on solar noon before anything else |
| Clear-sky model | Hong Kong atmosphere | Dust, aerosols, coastal haze | Site turbidity climatology; McClear clear-sky as a check |
| Gain prior | Flat roofs, regular cleaning | 32° tilt, hot modules, array not cleaned regularly, amorphous Si | Transposition factor T for 32°; β from the Safi inverters, shrunk toward the HKUST β |
| Index forecaster | Hong Kong clouds, humid and convective | Mostly clear skies, dust events, marine clouds | Three transfer levels (below) |
| Intervals | Calibrated in Hong Kong | Different error spread | Conformal recalibration on Safi pseudo cold starts |

The shrunk β is a two-level (hierarchical) estimate. With n Safi inverters, it weights the Safi median against the HKUST value:

```latex
\hat\beta_{Safi} = \frac{n\, \tilde\beta_{Safi} / s^2_{Safi} + \hat\beta_{HKUST} / \tau^2}{n / s^2_{Safi} + 1 / \tau^2}
```

Here s² is the spread of the Safi gain ratios and τ² the expected difference between sites, set from the spread of β across HKUST stations.

**Three transfer levels, each adding one thing:**

1. **T0, zero-shot:** the HKUST index forecaster and the HKUST β, with only Safi's nameplate and clear-sky. A pure transfer test.
2. **T1, physics adaptation:** add the Safi atmosphere, the 32° transposition and the shrunk β. Still no learning on Safi data.
3. **T2, local learning:** the index forecaster is retrained on Safi's own index history before the test start. Only the new inverter is in cold start; the site's other inverters have history.

Every level is compared with smart persistence and with Safi's own calibrated reference cell (a fair sensor baseline). The finding is **how much adaptation a new country needs**, a result the Moroccan follow-up builds on.

**Extra value from Safi:**

- The array was not cleaned regularly, so the 90-day gain update can show soiling drift, which links to future work on online gains.
- Amorphous Si beside crystalline Si tests whether the gain stays constant across seasons (temperature and spectral effects).
- The 32° tilt is the first real test of the transposition factor in prior G2.

**Events and limits.** Each of the three inverters is treated as new in turn, with the other two as the fleet: these are pseudo cold starts, and the poly-Si series beginning in May 2018 may be a real start. Use the **raw** files only, because the "Preprocessed" file was filtered with box-plot rules and by removing points far from a linear model, which would flatter any forecaster. The inverter AC ratings are in the companion Energy Reports 2020 article (Table 2).

&#91;embedded content: transfer ladder · T0, T1, T2 on the Safi rooftop\]

If T1 already closes most of the gap to T2, a new Moroccan site needs physics, not data, to be forecast from day one.

### A Morocco-ready validation kit

The released code takes one input schema: inverter power with timestamps and time zone, AC rating, module count and watt-peak, tilt and azimuth if known, site coordinates and altitude, and start dates. It runs the same QC, events, models, metrics and statistics, and prints the same tables. Any Moroccan installer, utility or laboratory with inverter data from new Law 82-21 systems can then validate the method without writing code. That makes the follow-up paper a data-collection task, not a research restart.

### Options for you

| Option | What enters this paper | Effort | Value |
| --- | --- | --- | --- |
| M1. Future work only | One subsection of paper §8 and the bridge equation | Very low | Low |
| M2. Safi external case study (recommended) | Paper §6.10: one table and one figure, framed as external validation | Medium: one more audit, same code | High: real Moroccan data from Marrakesh-Safi, new climate, tilt and technology |
| M3. Validation kit and bridge equation (recommended) | The release, plus a paper §8 subsection | Low | Medium: makes the Moroccan follow-up ready |
| M4. Semi-synthetic Marrakech fleet | A supplement stress test built from satellite irradiance (CAMS, you download it) | Medium to high | Low to medium: the fleet would be simulated |

Decision (13 November 2026): M2 + M3 are adopted, so the paper tests on Morocco; M1's text comes with them, and M4 is skipped.

**The follow-up paper this sets up:** regional cold-start forecasting for satellite-detected rooftops in Marrakesh-Safi, validated on Moroccan inverter data collected through the kit.

### Other Moroccan data (search of 13 November 2026)

The Safi rooftop is the only open Moroccan dataset with separate inverter data. One 14-inverter plant could be requested from its authors.

| Source | What it holds | Usable here? |
| --- | --- | --- |
| Safi rooftop ([Mendeley](https://data.mendeley.com/datasets/b2s4ycc2gz/1)) | 3 inverters, 5 min, 2016–2018, CC BY 4.0 | Yes: the external case study; you are downloading it |
| El Jadida factory plant ([Eddahbi et al., Energies 2023](https://mdpi.com/1996-1073/16/21/7414)) | 1,001 kWp, 14 Huawei SUN2000-60KTL inverters, full-year monitoring in 2022 | Not public. A data request to the authors could give a real 14-inverter Moroccan fleet, enough for a true fleet index |
| [Zenodo 15386590](https://zenodo.org/records/15386590) | Rural Moroccan grid topology and time series for planning | No: not measured inverter power |
| [Zenodo 17775544](https://zenodo.org/records/17775544) | Three PV racks with inverter data | No: the site is in Cyprus |
| [Mendeley yhdc2rv422](https://data.mendeley.com/datasets/yhdc2rv422/1), [Mendeley 2mwxrj5pkz](https://data.mendeley.com/datasets/2mwxrj5pkz/1) | Short or hourly PV series | No: location not Moroccan or not stated |

No Moroccan systems were found in PVOutput's public listings. The next step that would add most value is the El Jadida data request.

### Moroccan test plan without contacting anyone (decided 13 November 2026)

The Moroccan test has two parts: the real Safi rooftop, and a virtual fleet on real Benguerir rooftops, which is also in the Marrakesh-Safi region (Rehamna province). Alice Springs (DKASC) is not used now; it stays in reserve in case reviewers ask for a second real fleet.

**Building the Benguerir virtual fleet (semi-synthetic: real weather, simulated inverters):**

1. **Rooftops:** the Benguerir building-footprint layer: 29,225 buildings over 6 × 5 km, detected in 2022–2023, with roof areas from 3 to 13,356 m². These are all buildings, not PV detections, so virtual PV goes on a sample of the 8,268 roofs of 100 m² or more: a Law 82-21 adoption scenario. Where paper 1's detector finds existing PV on these roofs, those roofs are used first.
2. **Nameplate:** P\_DC = A\_PV × 0.20 × 1 kW/m², where A\_PV is 40–60% of the roof area; the AC rating is P\_DC / r, with r drawn from the HKUST DC/AC ratios (1.02–1.39). Tilt is flat to 10° or about 30° south, with the shares stated as an assumption.
3. **Irradiance:** CAMS 15-min all-sky and clear-sky GHI on a small grid of points over the town; each roof takes its nearest point.
4. **Simulation with pvlib:** Perez transposition, cell temperature from hourly air temperature and wind (Open-Meteo archive), DC/AC clipping, system losses with a ±5% spread across roofs, soiling that builds up and is reset by rain, and 2% measurement noise.
5. **Staggered starts:** virtual commissioning dates spread over the period, giving cold-start events like those at HKUST.
6. **Validation against reality:** the same simulation runs for the Safi site with CAMS irradiance and is compared with Safi's real inverters. That error tells the reader how far the virtual fleet can be trusted.

**Limits, stated in the paper:** a satellite pixel of 3–5 km smooths small clouds, and the inverters are simulated. Virtual-fleet results are reported separately and never pooled with real ones.

**CAMS at HKUST, as a bonus:** CAMS covers Hong Kong through the Himawari satellite. It gives an independent irradiance reference for the sensor audit, so the drift finding no longer rests on our clear-sky model alone. It also adds a baseline **A9, the satellite clear-sky index persisted forward**. A9 is optimistic about data latency, and the paper says so.

### Data to download

| # | Source | Location | Period | Step | Settings |
| --- | --- | --- | --- | --- | --- |
| 1 | CAMS gridded solar radiation | Marrakesh-Safi box: north 32.8, south 30.7, west −9.9, east −7.0 | June 2016 to December 2018 (monthly files) | 15 min, 0.1° grid | Observed cloud and clear-sky, netCDF; select the sub-area if the form allows it |
| 2 | CAMS solar radiation time-series | Safi rooftop, 32.3265° N, 9.2634° W | 2016-06-01 to 2018-12-31 | 1 min | Observed cloud, Universal time, CSV |
| 3 | CAMS solar radiation time-series | HKUST, 22.3363° N, 114.2634° E | 2021-01-01 to 2023-12-31 | 1 min (15 min if refused) | Same |
| 4 | CAMS solar radiation time-series, only if row 1 cannot be cut to the region | The 8 cluster centres C1–C8 and Benguerir P1 (32.2413° N, 7.9521° W), one request each | 2016-06-01 to 2018-12-31 | 15 min | Same |
| 5 | Open-Meteo historical weather (ERA5) | Benguerir and the 8 cluster centres, in one link | 2016-06-01 to 2018-12-31 | 1 h | Air temperature, wind speed, precipitation, CSV |

Row 5 downloads as a CSV by opening this link in a browser:

```
https://archive-api.open-meteo.com/v1/archive?latitude=32.2413,31.562,31.388,32.167,31.772,32.149,32.277,31.765,31.298&longitude=-7.9521,-7.973,-8.486,-7.386,-7.409,-7.989,-8.876,-9.155,-9.412&start_date=2016-06-01&end_date=2018-12-31&hourly=temperature_2m,wind_speed_10m,precipitation&timezone=GMT&format=csv
```

**CAMS files received on 18 November 2026:** they contain McClear clear-sky values only, because the requests used sky type "Clear". All-sky irradiance needs sky type **"Observed cloud"**, which also returns the clear-sky columns, so rows 1–4 must be downloaded again, with Safi running to 2018-12-31 (the first Safi file stops in August 2018). If CAMS has no all-sky data for Hong Kong, the HKUST satellite check and baseline A9 are dropped. McClear stays useful as a second clear-sky model: it tests whether the 2021–22 sensor level of 0.8 reflects the sensor or our clear-sky model, and it handles Moroccan dust better.

The NREL satellite database (NSRDB, Meteosat v4) is kept as an optional second irradiance source for a robustness check; it needs a free NREL API key.

### Using the regional PV maps (source paper to confirm)

The regional segmentation results give 1.39 km² of detected PV panels in Marrakesh-Safi, roughly 210–290 MWp of capacity with no metered history. Areas are read from the province bar chart (rounded to 0.01 km²); capacity assumes 150–210 W per m² of panel.

| Province | Detected PV area (km²) | Capacity range (MWp) |
| --- | --- | --- |
| El Kelaa des Sraghna | 0.34 | 51–71 |
| Marrakech | 0.30 | 45–63 |
| Al Haouz | 0.19 | 29–40 |
| Rehamna (includes Benguerir) | 0.17 | 26–36 |
| Chichaoua | 0.16 | 24–34 |
| Safi | 0.14 | 21–29 |
| Essaouira | 0.06 | 9–13 |
| Youssoufia | 0.03 | 5–6 |
| **Total** | **1.39** | **209–292** |

Three uses in the paper:

1. **Introduction:** a motivating figure: in one Moroccan region, about 210–290 MWp of PV is visible from space but invisible to any forecasting history.
2. **Benguerir scenario size:** Rehamna's 0.17 km² bounds a realistic adoption share for the virtual fleet.
3. **Discussion:** with the fleet-size result (§6.8), estimate how many metered reference inverters each province would need for cold-start forecasts of its detected PV.

**Caveat:** the dense rural clusters (El Kelaa des Sraghna, Rehamna plains) are probably solar water-pumping systems, which are often off-grid and have no grid inverter. The numbers are therefore "detected PV", not "grid-connected PV", and the paper says so.

### Regional virtual fleet and the donor-radius test

The PV density grid lets the Moroccan test span the whole region, which answers the one question HKUST cannot: how far away can the reference inverters be?

**What the files are.** 19,760 cells of 0.01° (about 1 km) digitised from the density figure, with values from 0 to 40.79 and three classes (10,887 low, 2,846 medium, 6,027 high). They give the relative density of detected PV, not panel positions or sizes. Weighted clustering finds 8 PV clusters, 44 to 214 km apart:

| Cluster | Area | Latitude | Longitude | Share of density |
| --- | --- | --- | --- | --- |
| C1 | Marrakech plain, north | 31.562 | −7.973 | 23.6% |
| C2 | West of Marrakech | 31.388 | −8.486 | 16.9% |
| C3 | El Kelaa des Sraghna, north | 32.167 | −7.386 | 13.2% |
| C4 | El Kelaa des Sraghna, south | 31.772 | −7.409 | 13.1% |
| C5 | Benguerir and Rehamna | 32.149 | −7.989 | 11.7% |
| C6 | Inland of Safi | 32.277 | −8.876 | 11.3% |
| C7 | East of Essaouira | 31.765 | −9.155 | 6.9% |
| C8 | South-east of Essaouira | 31.298 | −9.412 | 3.4% |

**Building the regional fleet (semi-synthetic):**

1. Sample 120 virtual PV systems across the cells, with probability proportional to the relative density.
2. Scale their capacities so the total matches the detected area (209–292 MWp).
3. Mount them at about 30° south, with the same nameplate, loss, soiling and noise rules as Benguerir.
4. Give each system the CAMS irradiance of the 0.1° cell it falls in. This brings real cloud differences across about 230 km.
5. Spread commissioning dates over the period to create cold-start events.

**Method extension: a local fleet index.** At regional scale the sky is no longer shared, so the index for a new system at location x uses only donors within a radius R, weighted by distance:

```latex
\hat k_R(t;\, x) = \operatorname*{wmedian}_{d:\ \mathrm{dist}(d,\,x) \le R} \big\{\kappa_d(t);\ w_d = e^{-\mathrm{dist}(d,\,x)/L}\big\}, \qquad L = R/2
```

**Donor-radius test.** R ∈ {10, 25, 50, 100, 250 km}, with skill plotted against R and against the donor count. The resulting curve tells a Moroccan operator how dense a network of metered reference inverters must be. It extends contribution 1 from a campus to a region.

&#91;embedded content: spatial scales · campus (real), town and region (virtual), Safi check\]

The campus carries the statistical claims; the town and the region carry the Moroccan transfer, and Safi keeps both virtual fleets honest.

**Limits.** Systems in the same 0.1° cell share one irradiance series; variability within a cell is added as noise. The fleet is semi-synthetic, and its results are reported separately from the real ones.

## 9. Gates and open decisions

Two gates control the work: a go/no-go test right after the baselines, and an independent review before submission.

Gate 1 decides the paper: if the main model does not beat the persisted fleet index from 30 min on, we switch to the sensor-correction note.

### Decisions for you

- [ ] **D1.** Accept the data corrections: inverter units, AC rating from the model name, "first day of telemetry", and the errata.
- [ ] **D2.** Accept the DC/AC prior as contribution 2, and test the transposition variant G2.
- [ ] **D3.** For 2–6 h horizons: fleet-only with the limitation stated, or add a historical Open-Meteo forecast baseline (you download it; I provide the script).
- [ ] **D4.** Final runs on your computer or Google Colab, with code I write and you run.
- [ ] **D5.** Journal: *Solar Energy* (recommended), or *IEEE Transactions on Sustainable Energy* with a stronger operator framing.
- [ ] **D6.** Optional upgrades: conformal intervals (item 14) and the past-weather ablation (item 15).
- [ ] **D7.** Morocco: M2 + M3, the Safi external case study plus the validation kit (recommended), M1 only, or M4 (Section 8).

Once D1–D4 are settled, the first step is the data pipeline (NB0 to NB2), written as a small package you run in one command.

### Data readiness (13 November 2026)

The HKUST work (NB0 to NB7) can start as soon as D1, D2 and D4 are settled; the Moroccan data are needed only from NB8a on.

| Dataset | Status |
| --- | --- |
| HKUST rooftop PV (Dryad) | In hand, audited |
| Benguerir building footprints | In hand, checked |
| PV density grid and province areas | In hand; the source paper still has to be named and cited |
| Safi rooftop (Mendeley) | Waiting for your upload |
| CAMS: Marrakesh-Safi grid, Safi 1-min, HKUST 1-min | Re-download with sky type "Observed cloud": the first files were McClear only, and Safi stopped in August 2018 |
| Open-Meteo, 9 Moroccan points | To download (link in Section 8) |
