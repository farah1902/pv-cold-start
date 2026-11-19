"""NB4: pyranometer and satellite index sources for the sensor baselines (A4, A4b, A4c) and the satellite rows (A9, A9n).

Guide §2 step 8, §4.2, D10, D19, D20, D32. The pyranometer and the satellite never feed the main model: this module
only builds the alternative index sources, their QC and calibration, and the donor gains refitted against them. It
reads the sensor, CAMS, donor power and the power of the 10 validation units; it never reads a test-event target.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import config as C
from . import fleet as F
from . import io_hkust as io

FIRST, LAST = "2021-01-01 00:00", "2023-12-31 23:59"
MARGIN_MIN = 30                    # the geometry grid extends 30 min beyond both ends, so it can be shifted by a lag

# --- Settings (guide §4.2 unless a D-number is given) -------------------------------------------------------
BSRN_LOWER = -2.0                  # W/m2, step 1 (Long & Shi 2008, "extremely rare" limits)
NIGHT_ELEVATION = -6.0             # deg, step 2
NIGHT_WINDOW_DAYS = 7              # step 2: the 7 days before day d (causal)
NIGHT_MIN_MINUTES = 360            # D32: fewer night minutes in the window -> the last valid offset is kept
DEAD_KT = 0.03                     # D32: daily sensor irradiation < 3% of clear sky (elevation > 10 deg) = dead day
DEAD_MIN_MINUTES = 300             # D32: the dead-day test needs >= 300 sensor minutes at elevation > 10 deg
DEAD_MIN_ELEVATION = 10.0
CAL_MAX_ZENITH = 70.0              # step 4
CAL_MIN_CLEAR = 120                # D32: a month's factor needs >= 120 detected clear minutes (zenith < 70 deg)
CAL_BOUNDS = (0.5, 2.0)            # D32: a factor outside this range is a failed clear-sky detection
SLOT_MIN_MINUTES = 10              # D32: a 15-min value needs >= 10 valid minutes of 15
EXT_GAIN_GRID = np.arange(0.3, 3.0 + 1e-9, 0.005)   # D32: gains against an external index carry its calibration
LAG_SCAN = range(-15, 16)          # min
LAG_MIN_CS = 200.0                 # W/m2: the lag scan uses minutes with clear-sky GHI above this

# 1-min flag bits of the sensor
F_MISSING, F_BELOW, F_ABOVE, F_DEAD = 1, 2, 4, 8
FLAG_NAMES = {F_MISSING: "missing", F_BELOW: "below_lower_limit", F_ABOVE: "above_upper_limit", F_DEAD: "dead_day"}

SOURCES = {  # index source -> (baseline rows, description)
    "sensor_raw": ("A4", "raw pyranometer, time-aligned only"),
    "sensor_corr": ("A4b, A4c", "QC, night offset, previous-month clear-sky calibration (causal)"),
    "sensor_same": ("A4b sensitivity", "as sensor_corr with the same-month calibration (not causal)"),
    "cams": ("A9, A9n", "CAMS all-sky GHI, reliability = 1, time-aligned"),
}


# --- Grids and loading ----------------------------------------------------------------------------------------
def minute_grid(margin_min: int = 0) -> pd.DatetimeIndex:
    m = pd.Timedelta(minutes=margin_min)
    return pd.date_range(pd.Timestamp(FIRST) - m, pd.Timestamp(LAST) + m, freq="1min")


def load_sensor(grid: pd.DatetimeIndex) -> pd.Series:
    """1-min pyranometer GHI (W/m2) on the regular grid, naive Hong Kong labels; NaN for absent rows (F24)."""
    g, _ = io.read_weather("ghi")
    s = g.set_index("time")["value"]
    assert s.index.is_unique, "duplicate sensor time stamps"
    return s.reindex(grid)


def load_cams(grid: pd.DatetimeIndex) -> pd.DataFrame:
    """CAMS all-sky GHI (W/m2) and reliability on the same grid (labels: start of each minute, Hong Kong time)."""
    c = io.read_cams(C.CAMS_HKUST)
    c.index = c.index.tz_convert(C.TZ).tz_localize(None)
    return c[["GHI", "Reliability"]].reindex(grid)


def minute_geometry(stamps: pd.DatetimeIndex, eff_shift_min: float, altitude_m: float) -> pd.DataFrame:
    """Solar zenith and elevation, Ineichen clear-sky GHI and the BSRN upper limit at stamps + eff_shift_min."""
    import pvlib

    eff = (stamps + pd.Timedelta(minutes=eff_shift_min)).tz_localize(C.TZ)
    loc = pvlib.location.Location(C.SITE_LAT, C.SITE_LON, tz=C.TZ, altitude=altitude_m)
    sp = loc.get_solarposition(eff)
    cs = loc.get_clearsky(eff, model="ineichen", solar_position=sp)["ghi"].to_numpy()
    z = sp["apparent_zenith"].to_numpy()
    s0 = pvlib.irradiance.get_extra_radiation(eff).to_numpy()
    mu = np.clip(np.cos(np.radians(z)), 0, None)
    return pd.DataFrame({"zenith": z, "elevation": sp["apparent_elevation"].to_numpy(), "G_cs": cs,
                         "bsrn_upper": 1.2 * s0 * mu ** 1.2 + 50.0}, index=stamps)


def shifted_geometry(geo_ext: pd.DataFrame, grid: pd.DatetimeIndex, lag_min: int) -> pd.DataFrame:
    """Geometry of a source whose label tau corresponds to panel time tau - lag: rows of geo_ext at tau - lag.

    geo_ext holds the geometry at label + 0.5 min on an extended regular grid, so this is exact (no interpolation).
    """
    out = geo_ext.reindex(grid - pd.Timedelta(minutes=lag_min))
    assert out.notna().all().all(), "geometry grid too short for this lag"
    out.index = grid
    return out


# --- Time base (D32) -------------------------------------------------------------------------------------------
def lag_scan(G1: pd.Series, G_cs1: pd.Series, k5: pd.Series, lags=LAG_SCAN) -> pd.DataFrame:
    """Correlation of within-day 5-min changes of a source's clear-sky index with those of the NB2 5-min fleet index.

    For lag L (min), the fleet value stamped s is paired with the mean of the source's minutes labelled
    [s + L, s + L + 5). The peak lag aligns the source with the panel clock; cloud transitions time it directly,
    without the clear-day geometry, whose correlation is too flat for a sensor (D32).
    """
    k1 = G1 / G_cs1.where(G_cs1 > LAG_MIN_CS)
    rows = []
    for L in lags:
        w = k1.shift(-L).rolling(5, min_periods=4).mean().shift(-4).reindex(k5.index)
        a = pd.DataFrame({"s": w, "f": k5}).dropna()
        d = a.groupby(a.index.normalize()).diff().dropna()
        rows.append({"lag": L, "period": "all", "corr": float(np.corrcoef(d["s"], d["f"])[0, 1]), "n": len(d)})
        for q, x in d.groupby(d.index.to_period("Q")):
            rows.append({"lag": L, "period": str(q), "corr": float(np.corrcoef(x["s"], x["f"])[0, 1]), "n": len(x)})
    return pd.DataFrame(rows)


def peak_lag(scan: pd.DataFrame, period: str = "all") -> float:
    """Lag of the correlation peak, refined by a parabola through the peak and its two neighbours."""
    c = scan[scan["period"] == period].set_index("lag")["corr"].sort_index()
    L = int(c.idxmax())
    if L - 1 in c.index and L + 1 in c.index:
        y0, y1, y2 = c[L - 1], c[L], c[L + 1]
        den = y0 - 2 * y1 + y2
        return float(L + 0.5 * (y0 - y2) / den) if den != 0 else float(L)
    return float(L)


def clear_day_scan(G1: pd.Series, geo: pd.DataFrame, altitude_m: float, n_days: int = 10,
                   shifts=np.arange(-6.0, 6.01, 1.0)) -> pd.DataFrame:
    """The guide's time-label method (§2 step 1) applied to the sensor: correlation with clear-sky GHI at
    label + shift on the n_days clearest smooth days of each year (days chosen with the nominal geometry `geo` on
    G1's grid). Reported to show how flat it is (D32)."""
    grid = G1.index
    day = grid.normalize()
    m10 = (geo["elevation"] > DEAD_MIN_ELEVATION).to_numpy()
    g = G1.to_numpy()
    kt = pd.Series(np.where(m10, g, np.nan)).groupby(day).sum(min_count=1) / \
        pd.Series(np.where(m10 & np.isfinite(g), geo["G_cs"], np.nan)).groupby(day).sum(min_count=1)
    rough = pd.Series(np.abs(np.diff(g, prepend=np.nan)) * m10).groupby(day).mean()
    full_cnt = pd.Series(np.isfinite(g) & m10).groupby(day).sum() >= 0.98 * pd.Series(m10).groupby(day).sum()
    rows = []
    for yr in sorted(set(grid.year)):
        k = kt[(kt.index.year == yr) & full_cnt.reindex(kt.index).to_numpy()].dropna()
        r = rough.reindex(k.index)
        days = list(k[r <= r.quantile(0.5)].sort_values(ascending=False).index[:n_days])
        sel = day.isin(days) & m10 & np.isfinite(g)
        for sh in shifts:
            cs = minute_geometry(grid[sel], float(sh), altitude_m)["G_cs"].to_numpy()
            rows.append({"year": int(yr), "shift_min": float(sh), "corr": float(np.corrcoef(g[sel], cs)[0, 1]),
                         "days": len(days)})
    return pd.DataFrame(rows)


# --- Sensor QC and calibration (guide §4.2 steps 1-4, D32) --------------------------------------------------------
def dead_days(G1: pd.Series, geo: pd.DataFrame) -> pd.DataFrame:
    """Daily sensor clear-sky index over minutes at elevation > 10 deg; a day is dead if it is below DEAD_KT."""
    day = G1.index.normalize()
    m = (geo["elevation"] > DEAD_MIN_ELEVATION).to_numpy() & np.isfinite(G1.to_numpy())
    sens = pd.Series(np.where(m, G1.to_numpy(), 0.0)).groupby(day).sum()
    clr = pd.Series(np.where(m, geo["G_cs"].to_numpy(), 0.0)).groupby(day).sum()
    n = pd.Series(m).groupby(day).sum()
    out = pd.DataFrame({"kt_sensor": (sens / clr.where(clr > 0)), "minutes_el10": n})
    out["dead"] = (out["kt_sensor"] < DEAD_KT) & (out["minutes_el10"] >= DEAD_MIN_MINUTES)
    return out


def night_offset(G1: pd.Series, geo: pd.DataFrame) -> pd.DataFrame:
    """o(d): median sensor value at elevation < -6 deg over the 7 days before d, using night minutes within the BSRN
    band (-2 to 50 W/m2 at night). Fewer than 360 such minutes: the last valid offset is kept; before any: 0."""
    g = G1.to_numpy()
    m = (geo["elevation"] < NIGHT_ELEVATION).to_numpy() & np.isfinite(g) & (g >= BSRN_LOWER) & \
        (g <= geo["bsrn_upper"].to_numpy())
    nv = pd.Series(g[m], index=G1.index[m])
    byday = {d: v.to_numpy() for d, v in nv.groupby(nv.index.normalize())}
    days = pd.date_range(G1.index[0].normalize(), G1.index[-1].normalize(), freq="D")
    rows = []
    for d in days:
        parts = [byday[x] for x in pd.date_range(d - pd.Timedelta(days=NIGHT_WINDOW_DAYS), periods=NIGHT_WINDOW_DAYS)
                 if x in byday]
        a = np.concatenate(parts) if parts else np.array([])
        rows.append({"day": d, "n_night_minutes": int(a.size),
                     "offset_window": float(np.median(a)) if a.size >= NIGHT_MIN_MINUTES else np.nan})
    out = pd.DataFrame(rows).set_index("day")
    out["offset_carried"] = out["offset_window"].isna()
    out["offset"] = out["offset_window"].ffill().fillna(0.0)
    return out


def detect_clear(Gp: pd.Series, geo: pd.DataFrame, eff_shift_min: float) -> tuple[np.ndarray, pd.DataFrame]:
    """pvlib detect_clearsky (Reno & Hansen 2016, pvlib defaults) on the offset-corrected 1-min sensor, one calendar
    month per call, so its clear-sky rescaling factor alpha is fitted per month and uses no later data."""
    import pvlib

    clear = np.zeros(len(Gp), dtype=bool)
    eff = (Gp.index + pd.Timedelta(minutes=eff_shift_min)).tz_localize(C.TZ)
    pos = pd.Series(np.arange(len(Gp)), index=Gp.index)
    info = []
    for per, idx in pos.groupby(Gp.index.to_period("M")):
        sl = idx.to_numpy()
        meas = pd.Series(Gp.to_numpy()[sl], index=eff[sl])
        ref = pd.Series(geo["G_cs"].to_numpy()[sl], index=eff[sl])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                cl, _, alpha = pvlib.clearsky.detect_clearsky(meas, ref, return_components=True)
                status = "no convergence" if any("converge" in str(x.message) for x in w) else "ok"
                clear[sl] = cl.to_numpy()
            except Exception as e:  # noqa: BLE001
                alpha, status = np.nan, f"error: {type(e).__name__}"
        info.append({"month": str(per), "alpha": float(alpha), "status": status, "n_clear": int(clear[sl].sum())})
    return clear, pd.DataFrame(info)


def monthly_calibration(Gp: pd.Series, geo: pd.DataFrame, clear: np.ndarray, info: pd.DataFrame) -> pd.DataFrame:
    """Step 4: c_m = median of G_cs / G' over the month's detected clear minutes with zenith < 70 deg and G' > 0.

    A month is valid with >= 120 such minutes and c_m within CAL_BOUNDS. Month m applies the latest valid factor of
    an earlier month (causal); the same-month sensitivity applies c_m when valid, otherwise the causal factor.
    """
    g = Gp.to_numpy()
    use = clear & (geo["zenith"].to_numpy() < CAL_MAX_ZENITH) & np.isfinite(g) & (g > 0)
    ratio = np.where(use, geo["G_cs"].to_numpy() / np.where(use, g, 1.0), np.nan)
    mon = Gp.index.to_period("M")
    t = pd.DataFrame({"n_cal": pd.Series(use).groupby(mon).sum(),
                      "c_month": pd.Series(ratio).groupby(mon).median()})
    t.index = t.index.astype(str)
    t = t.join(info.set_index("month"))
    t["valid"] = (t["n_cal"] >= CAL_MIN_CLEAR) & t["c_month"].between(*CAL_BOUNDS)
    c_ok = t["c_month"].where(t["valid"])
    src = pd.Series(np.where(t["valid"], t.index, None), index=t.index)
    t["c_applied"] = c_ok.shift(1).ffill()
    t["c_applied_from"] = src.shift(1).ffill()
    t["c_same"] = c_ok.fillna(t["c_applied"])
    return t


def corrected(G1: pd.Series, offset: pd.Series, cal: pd.DataFrame, dead: pd.Series, geo: pd.DataFrame,
              column: str) -> tuple[pd.Series, pd.Series]:
    """G_corr = c (G - o): NaN where the raw reading is missing or below -2 W/m2, the day is dead, or the calibrated
    value exceeds the BSRN upper limit (applied after calibration, D32). Returns (G_corr, flag bits)."""
    g = G1.to_numpy()
    day = G1.index.normalize()
    o = offset.reindex(day).to_numpy()
    c = pd.Series(G1.index.to_period("M").astype(str)).map(cal[column]).to_numpy()
    gc = c * (g - o)
    flag = np.zeros(len(g), dtype=np.int8)
    flag |= np.where(~np.isfinite(g), F_MISSING, 0).astype(np.int8)
    flag |= np.where(np.isfinite(g) & (g < BSRN_LOWER), F_BELOW, 0).astype(np.int8)
    flag |= np.where(np.isfinite(gc) & (gc > geo["bsrn_upper"].to_numpy()), F_ABOVE, 0).astype(np.int8)
    flag |= np.where(dead.reindex(day).fillna(False).to_numpy(), F_DEAD, 0).astype(np.int8)
    gc = np.where((flag == 0) & np.isfinite(c), gc, np.nan)
    return pd.Series(gc, index=G1.index), pd.Series(flag, index=G1.index)


# --- 15-min index series --------------------------------------------------------------------------------------------
def to_slots(G1: pd.Series, slots: pd.DatetimeIndex, lag_min: int) -> pd.DataFrame:
    """15-min mean for each panel slot t of the source minutes labelled [t + lag, t + lag + 15); valid if >= 10."""
    x = G1.shift(-lag_min)                         # value at tau is G1(tau + lag); the grid is regular 1-min
    key = x.index.floor("15min")
    out = pd.DataFrame({"mean": x.groupby(key).mean(), "n": x.notna().groupby(key).sum()}).reindex(slots)
    out["mean"] = out["mean"].where(out["n"] >= SLOT_MIN_MINUTES)
    return out


def index_15(G15: pd.Series, geo15: pd.DataFrame, clip: bool) -> pd.Series:
    """k = G / G_cs at the panel slots (Ineichen at slot + 8 min, as the fleet index); NaN where Gt <= 0.05."""
    k = G15 / geo15["G_cs"]
    k = k.where(geo15["Gt"] > C.ISSUE_MIN_GTILDE)
    return k.clip(*C.K_BOUNDS) if clip else k


# --- Donor gains against an external index (guide §4.2 step 5) ---------------------------------------------------
def gain_curves(y: np.ndarray, k: np.ndarray, gt: np.ndarray, mask: np.ndarray, day_id: np.ndarray, n_days: int,
                grid: np.ndarray = EXT_GAIN_GRID, chunk: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative daily sums of the censored Huber gain loss huber(y - min(1, g k Gt)) over the grid, and of the
    point counts, for one donor. A window of whole days then gives exactly fit_gain's objective (summed by day)."""
    m = mask & np.isfinite(y) & np.isfinite(k)
    loss = np.zeros((n_days, len(grid)))
    cnt = np.zeros(n_days)
    idx = np.where(m)[0]                           # time order, so day_id[idx] never decreases
    for i in range(0, len(idx), chunk):
        r = idx[i:i + chunk]
        a = (k[r] * gt[r])[:, None]
        L = F.huber(y[r][:, None] - np.minimum(1.0, a * grid[None, :]))
        dr = day_id[r]
        first = np.r_[0, np.where(np.diff(dr) != 0)[0] + 1]   # first point of each day in the chunk
        loss[dr[first]] += np.add.reduceat(L, first, axis=0)
        cnt[dr[first]] += np.diff(np.r_[first, len(r)])
    return np.cumsum(loss, axis=0), np.cumsum(cnt)


def gain_window(cum_loss: np.ndarray, cum_cnt: np.ndarray, end_day: int, grid: np.ndarray = EXT_GAIN_GRID):
    """Gain fitted on all days before end_day (day index); NaN under 20 points, as fit_gain."""
    if end_day <= 0:
        return np.nan, 0
    n = int(cum_cnt[end_day - 1])
    if n < 20:
        return np.nan, n
    return float(grid[np.argmin(cum_loss[end_day - 1])]), n


def external_gains(p: dict, k_src: pd.Series, k_min: float, ends: dict[str, list]) -> pd.DataFrame:
    """Gains of every donor needed by `ends` = {donor: [event start dates]}, fitted against k_src with the fleet's
    gain-fit mask (QC-clean slot, Gt > 0.2, after the donor's rule start, index > k_min) from its rule start to each
    event start. No renormalisation: the gain absorbs the source's calibration (guide §4.2 step 5)."""
    t = p["y15"].index
    days = t.normalize()
    uniq = days.unique()
    day_id = np.searchsorted(uniq.to_numpy(), days.to_numpy())
    gt = p["geometry15"]["Gt"].to_numpy()
    k = k_src.reindex(t).to_numpy()
    rows = []
    for d, starts in ends.items():
        y = p["y15"][d].to_numpy()
        mask = (p["flags15"][d].to_numpy() == 0) & (gt > C.GAIN_FIT_MIN_GTILDE) & (k > k_min) & \
            (t >= p["units"].loc[d, "rule_start"]) & (t < max(pd.Timestamp(s) for s in starts))
        cl, cc = gain_curves(y, k, gt, mask, day_id, len(uniq))
        for s in starts:
            g, n = gain_window(cl, cc, int(np.searchsorted(uniq.to_numpy(), np.datetime64(pd.Timestamp(s)))))
            rows.append({"donor": d, "start": pd.Timestamp(s), "gain": g, "n_points": n})
    return pd.DataFrame(rows)


def external_priors(a: dict, g: pd.Series, units: pd.DataFrame, altitude_m: float, cache: dict, variant: str) -> dict:
    """Priors of the event's target from donor gains refitted against an external index. G1 and G2 as for the fleet;
    G0 is the median donor gain, the analogue of the fleet's g = 1 (there the median donor gain is 1 by definition)."""
    pr, _, _, _ = F.event_priors(a, g, units, altitude_m, cache)
    pr["G0"] = float(np.nanmedian(g.to_numpy()))
    used = variant if pr["target_in_prior_test"] else "G0"
    return {"prior_used": used, "prior_gain": pr[used], **{k: pr[k] for k in ["G0", "G1", "G2", "beta_G1", "beta_G2",
                                                                              "r_new", "T_new", "n_meta_donors"]}}


# --- Diagnostics on validation units only ----------------------------------------------------------------------------
def validation_by_source(a: dict, p: dict, ks: dict[str, np.ndarray], priors: dict[str, float], k_min: float) -> list:
    """VALIDATION UNITS ONLY: same-time reconstruction nRMSE (h = 0) of the unit from each index source, with its
    oracle 90-day gain and with the cold-start prior, on the slots where every source has a value."""
    assert a["ev"]["set"] == "validation", "target power may only be read for validation units in NB4"
    u = a["ev"]["units"]
    y = p["y15"].loc[a["t"], u].to_numpy()
    fv = (p["flags15"].loc[a["t"], u].to_numpy() == 0) & np.isfinite(y)
    common = a["window"] & (a["gt"] > C.SCORE_MIN_GTILDE) & np.isfinite(y)
    for k in ks.values():
        common &= np.isfinite(k)
    rows = []
    for src, k in ks.items():
        grid = np.arange(C.GAIN_BOUNDS[0], C.GAIN_BOUNDS[1] + 1e-9, 0.005) if src == "fleet" else EXT_GAIN_GRID
        m_fit = a["window"] & fv & (a["gt"] > C.GAIN_FIT_MIN_GTILDE) & (k > k_min)
        g_star, n_fit = F.fit_gain(y, k, a["gt"], m_fit, grid)
        rows.append({"event": a["name"], "source": src, "g_star": g_star, "prior_gain": priors[src], "n_fit": n_fit,
                     "n_slots": int(common.sum()),
                     "nrmse0_oracle": F.nrmse(y, F.recon(g_star, k, a["gt"]), common),
                     "nrmse0_prior": F.nrmse(y, F.recon(priors[src], k, a["gt"]), common)})
    return rows


def agreement(k_src: np.ndarray, k_fleet: np.ndarray, gt: np.ndarray, rows: np.ndarray) -> dict:
    """Input agreement in an event window (no target used): median ratio and correlation with the fleet index."""
    m = rows & (gt > C.GAIN_FIT_MIN_GTILDE) & np.isfinite(k_src) & np.isfinite(k_fleet) & (k_fleet > 0.05)
    if m.sum() < 20:
        return {"n": int(m.sum()), "median_ratio": np.nan, "corr": np.nan}
    return {"n": int(m.sum()), "median_ratio": float(np.median(k_src[m] / k_fleet[m])),
            "corr": float(np.corrcoef(k_src[m], k_fleet[m])[0, 1])}
