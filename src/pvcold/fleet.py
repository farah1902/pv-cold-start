"""NB3: fleet index (median and censored Huber), donor gains, DC/AC priors, empirical-Bayes weights, drift boundary.

Guide §3.3-§3.6, D02, D10, D28. Test events: only their donors and nameplates are used here, never their own power.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import config as C

warnings.filterwarnings("ignore", message="All-NaN slice encountered")
warnings.filterwarnings("ignore", message="Mean of empty slice")


def load_panel() -> dict:
    d = C.RESULTS / "nb2_panel"
    out = {k: pd.read_parquet(d / f"{k}.parquet").set_index("time") for k in
           ["y15", "flags15", "geometry15", "targets15_kW"]}
    out["units"] = pd.read_csv(d / "units.csv", parse_dates=["first_row", "rule_start"]).set_index("unit")
    out["events"] = pd.read_csv(d / "events.csv", parse_dates=["start"])
    out["donors"] = pd.read_csv(d / "donors.csv")
    return out


def huber(r, delta=C.HUBER_DELTA):
    a = np.abs(r)
    return np.where(a <= delta, 0.5 * r * r, delta * (a - 0.5 * delta))


# --- Index estimators (guide §3.3) ----------------------------------------------------------------
def kappa(Y: np.ndarray, valid: np.ndarray, g: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """Implied index of unclipped valid donors; NaN elsewhere."""
    with np.errstate(divide="ignore", invalid="ignore"):
        K = Y / (g[None, :] * gt[:, None])
    K[~valid | (Y >= C.CLIP_THRESHOLD)] = np.nan
    return K


def median_index(Y, valid, g, gt):
    """Robust median index, its IQR (sigma), clipped share (c) and unclipped donor count (n)."""
    K = kappa(Y, valid, g, gt)
    n = np.sum(~np.isnan(K), axis=1)
    with np.errstate(all="ignore"):
        k = np.clip(np.nanmedian(K, axis=1), *C.K_BOUNDS)
        q75, q25 = np.nanpercentile(K, [75, 25], axis=1)
    online = valid.sum(axis=1)
    c = np.where(online > 0, (valid & (Y >= C.CLIP_THRESHOLD)).sum(axis=1) / np.maximum(online, 1), np.nan)
    k[(gt <= C.ISSUE_MIN_GTILDE) | (online == 0)] = np.nan
    return k, q75 - q25, c, n


def censored_index(Y, valid, g, gt, chunk=400, step=0.005, fine=0.0005):
    """argmin over k in [0, 1.5] of sum_d huber(y_d - min(1, g_d k Gt)) over all online donors, clipped included.

    Coarse grid (step 0.005), then a local grid of +-0.005 at 0.0005 (stands for the golden-section refinement).
    """
    grid = np.arange(C.K_BOUNDS[0], C.K_BOUNDS[1] + 1e-9, step, dtype=np.float32)
    out = np.full(len(gt), np.nan)
    rows = np.where((gt > C.ISSUE_MIN_GTILDE) & (valid.sum(axis=1) > 0))[0]
    for i in range(0, len(rows), chunk):
        r = rows[i:i + chunk]
        Yc = np.nan_to_num(Y[r].astype(np.float32))
        V = valid[r]
        A = (g[None, :] * gt[r, None]).astype(np.float32)
        loss = (huber(Yc[:, :, None] - np.minimum(1.0, A[:, :, None] * grid[None, None, :])) * V[:, :, None]).sum(axis=1)
        k0 = grid[np.argmin(loss, axis=1)]
        loc = k0[:, None] + np.arange(-step, step + 1e-9, fine, dtype=np.float32)[None, :]
        loc = np.clip(loc, *C.K_BOUNDS)
        l2 = (huber(Yc[:, :, None] - np.minimum(1.0, A[:, :, None] * loc[:, None, :])) * V[:, :, None]).sum(axis=1)
        out[r] = loc[np.arange(len(r)), np.argmin(l2, axis=1)]
    return out


# --- Gains (guide §3.4) --------------------------------------------------------------------------------
def fit_gain(y, k_ref, gt, mask, grid=np.arange(C.GAIN_BOUNDS[0], C.GAIN_BOUNDS[1] + 1e-9, 0.005)):
    """Censored Huber fit of one gain: argmin_g sum huber(y - min(1, g k_ref Gt)) over the mask. NaN if < 20 points."""
    m = mask & np.isfinite(y) & np.isfinite(k_ref)
    if m.sum() < 20:
        return np.nan, int(m.sum())
    a = (k_ref[m] * gt[m])[:, None]
    loss = huber(y[m][:, None] - np.minimum(1.0, a * grid[None, :])).sum(axis=0)
    return float(grid[np.argmin(loss)]), int(m.sum())


def loo_median(K: np.ndarray) -> np.ndarray:
    """Exact leave-one-out median of each column's row-mates (NaN ignored), vectorised: one sort per call."""
    T, n = K.shape
    order = np.argsort(np.where(np.isnan(K), np.inf, K), axis=1)
    S = np.take_along_axis(K, order, axis=1)                 # sorted, NaN last
    rank = np.empty_like(order)
    np.put_along_axis(rank, order, np.arange(n)[None, :].repeat(T, 0), axis=1)
    m = np.sum(~np.isnan(K), axis=1)                         # valid count per row
    out = np.full((T, n), np.nan)
    rows = np.arange(T)
    for d in range(n):
        own = ~np.isnan(K[:, d])
        M = m - own.astype(int)                              # size of the remaining set
        j1, j2 = (M - 1) // 2, M // 2
        r = np.where(own, rank[:, d], n + 1)                 # position of d in the sorted row (none if NaN)
        i1 = np.clip(j1 + (j1 >= r), 0, n - 1)
        i2 = np.clip(j2 + (j2 >= r), 0, n - 1)
        val = 0.5 * (S[rows, i1] + S[rows, i2])
        out[:, d] = np.where(M > 0, val, np.nan)
    return out


def fit_donor_gains(Y, valid, gt, before, starts_ok, k_min, n_iter=5):
    """Alternating fit: gains against the leave-one-out median index, renormalised to median 1 (guide §3.4).

    Y, valid: (T x n) over the fitting period; before: bool (T) for t < s_e; starts_ok: bool (T x n) for t >= s_d.
    The leave-one-out index uses the median estimator for every variant, so both estimators share the gains (D30).
    """
    n = Y.shape[1]
    g = np.ones(n)
    base = before & (gt > C.GAIN_FIT_MIN_GTILDE)
    Yb, Vb, gtb, Sb = Y[base], valid[base], gt[base], starts_ok[base]
    history = []
    for _ in range(n_iter):
        K = kappa(Yb, Vb, g, gtb)
        L = loo_median(K)
        new = np.full(n, np.nan)
        for d in range(n):
            mask = Vb[:, d] & Sb[:, d] & (L[:, d] > k_min)
            new[d], _ = fit_gain(Yb[:, d], L[:, d], gtb, mask)
        new = np.where(np.isnan(new), 1.0, new)
        g = new / np.median(new)
        history.append(g.copy())
    change = float(np.max(np.abs(history[-1] - history[-2]))) if len(history) > 1 else np.nan
    return g, change


# --- Transposition and priors (guide §3.5) ----------------------------------------------------------
def planes(tilt: str, az_brick: str):
    """List of (tilt, azimuth_pvlib) planes with equal module shares; None for flat or 'Mixed' units (T = 1)."""
    if not isinstance(tilt, str) or "Mixed" in tilt or "Mixed" in str(az_brick):
        return None
    tilts = [float(v) for v in tilt.replace("deg", "").split("/")]
    azs = [(360.0 - float(v)) % 360.0 for v in str(az_brick).replace("deg", "").split("/")]
    if len(tilts) == 1:
        tilts = tilts * len(azs)
    if all(t == 0 for t in tilts):
        return None
    return list(zip(tilts, azs))


def transposition(pl, times: pd.DatetimeIndex, altitude_m: float) -> float:
    """Sum of clear-sky POA over sum of clear-sky GHI (Perez, albedo 0.2) over the given 15-min effective times."""
    import pvlib
    if pl is None:
        return 1.0
    eff = (times + pd.Timedelta(minutes=8)).tz_localize(C.TZ)
    loc = pvlib.location.Location(C.SITE_LAT, C.SITE_LON, tz=C.TZ, altitude=altitude_m)
    sp = loc.get_solarposition(eff)
    cs = loc.get_clearsky(eff, model="ineichen", solar_position=sp)
    dni_extra = pvlib.irradiance.get_extra_radiation(eff)
    am = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"])
    poa = 0.0
    for t, a in pl:
        irr = pvlib.irradiance.get_total_irradiance(t, a, sp["apparent_zenith"], sp["azimuth"], cs["dni"], cs["ghi"],
                                                    cs["dhi"], dni_extra=dni_extra, airmass=am, model="perez",
                                                    albedo=0.2)
        poa = poa + irr["poa_global"].fillna(0).clip(lower=0)
    return float((poa / len(pl)).sum() / cs["ghi"].sum())


def priors(g_don: pd.Series, r_don: pd.Series, T_don: pd.Series, meta_ok: pd.Series, r_new: float, T_new: float) -> dict:
    """G0, G1, G2 priors and their donor uncertainty sets (guide §3.5)."""
    ok = meta_ok & g_don.notna() & r_don.notna()
    b1 = (g_don / r_don)[ok]
    b2 = (g_don / (r_don * T_don))[ok]
    return {"G0": 1.0, "G1": float(b1.median() * r_new), "G2": float(b2.median() * r_new * T_new),
            "beta_G1": float(b1.median()), "beta_G2": float(b2.median()), "n_meta_donors": int(ok.sum()),
            "B_G1": b1.round(4).tolist(), "B_G2": b2.round(4).tolist()}


def eb_weights(g_don, r_don, T_don, meta_ok, daily_gains: pd.DataFrame, variant: str) -> dict:
    """sigma_p^2 (robust variance of leave-one-out prior errors among donors), s_1^2 (variance of one-day gain
    estimates around each donor's gain, pooled) and w0 = s_1^2 / sigma_p^2 in days (guide §3.6, D22)."""
    ok = (meta_ok & g_don.notna()).to_numpy()
    rT = (r_don * (T_don if variant == "G2" else 1.0)).to_numpy()
    b = g_don.to_numpy() / rT
    errs = []
    for i in np.where(ok)[0]:
        others = np.delete(np.where(ok)[0], np.where(np.where(ok)[0] == i)[0])
        errs.append(g_don.iloc[i] - np.median(b[others]) * rT[i])
    errs = np.asarray(errs)
    sp2 = float((1.4826 * np.median(np.abs(errs - np.median(errs)))) ** 2)
    dev = (daily_gains - g_don.reindex(daily_gains.columns)).stack()
    s12 = float((1.4826 * np.median(np.abs(dev - np.median(dev)))) ** 2)
    return {"sigma_p2": sp2, "s1_2": s12, "w0_days": s12 / sp2 if sp2 > 0 else np.nan, "n_daily": int(dev.size)}


def daily_gain_estimates(Y, valid, gt, Kref, times, mask_rows, names):
    """One-day gain estimates per donor (days with >= 8 unclipped slots where Gt > 0.2), against Kref[:, d]."""
    out = {}
    day = times.normalize()
    for d in range(Y.shape[1]):
        m = mask_rows & valid[:, d] & (gt > C.GAIN_FIT_MIN_GTILDE) & (Y[:, d] < C.CLIP_THRESHOLD) & np.isfinite(Kref[:, d])
        res = {}
        for dd in np.unique(day[m]):
            md = m & np.asarray(day == dd)
            if md.sum() >= 8:
                res[dd], _ = fit_gain(Y[:, d], Kref[:, d], gt, md)
        out[names[d]] = pd.Series(res, dtype=float)
    return pd.DataFrame(out)


# --- Evaluation on validation units only ------------------------------------------------------------
def nrmse(y, yhat, mask):
    m = mask & np.isfinite(y) & np.isfinite(yhat)
    return float(np.sqrt(np.mean((y[m] - yhat[m]) ** 2))) if m.sum() else np.nan


def recon(g, k, gt):
    return np.minimum(1.0, g * k * gt)


# --- Drift boundary (D10, D30) ---------------------------------------------------------------------------
def single_break_pelt(series: pd.Series, min_size: int = 30) -> dict:
    """PELT (L2) with the penalty raised geometrically until exactly one change point remains: the dominant step."""
    import ruptures as rpt
    x = np.log(series.dropna())
    x = x[np.isfinite(x)]
    algo = rpt.Pelt(model="l2", min_size=min_size).fit(x.to_numpy().reshape(-1, 1))
    pen = float(np.var(np.diff(x.to_numpy())))
    for _ in range(200):
        bk = algo.predict(pen=pen)
        if len(bk) - 1 <= 1:
            break
        pen *= 1.25
    if len(bk) - 1 == 0:
        return {"date": None, "penalty": pen}
    b = bk[0]
    return {"date": x.index[b].date().isoformat(), "penalty": pen, "before": float(np.exp(np.median(x.iloc[:b]))),
            "after": float(np.exp(np.median(x.iloc[b:]))), "n_days": int(len(x))}


# --- Event driver ------------------------------------------------------------------------------------
def event_arrays(name: str, p: dict) -> dict:
    """Donor matrices of one event from the fleet start to its start + 90 days (donor data only)."""
    ev = p["events"].set_index("event").loc[name]
    s = ev["start"]
    dn = p["donors"].loc[p["donors"]["event"] == name, "donor"].tolist()
    rng = np.asarray(p["y15"].index < s + pd.Timedelta(days=90))
    t = p["y15"].index[rng]
    Y = p["y15"].loc[rng, dn].to_numpy()
    V = (p["flags15"].loc[rng, dn].to_numpy() == 0) & np.isfinite(Y)
    gt = p["geometry15"]["Gt"].to_numpy()[rng]
    starts_ok = t.to_numpy()[:, None] >= p["units"].loc[dn, "rule_start"].to_numpy()[None, :]
    return {"name": name, "ev": ev, "s": s, "dn": dn, "t": t, "Y": Y, "V": V, "gt": gt,
            "before": np.asarray(t < s), "window": np.asarray(t >= s), "starts_ok": starts_ok}


def run_event(a: dict, k_min: float, censored: bool = True) -> dict:
    g, chg = fit_donor_gains(a["Y"], a["V"], a["gt"], a["before"], a["starts_ok"], k_min)
    km, sig, c, n = median_index(a["Y"], a["V"], g, a["gt"])
    kc = censored_index(a["Y"], a["V"], g, a["gt"]) if censored else None
    return {"g": pd.Series(g, index=a["dn"]), "change": chg, "k_med": km, "k_cens": kc, "sigma": sig, "c": c, "n": n}


def validation_scores(a: dict, k: np.ndarray, p: dict, k_min: float) -> dict:
    """VALIDATION UNITS ONLY: oracle gain over the first 90 days and same-time reconstruction nRMSE (h = 0)."""
    assert a["ev"]["set"] == "validation", "target power may only be read for validation units in NB3"
    u = a["ev"]["units"]
    y = p["y15"].loc[a["t"], u].to_numpy()
    fv = (p["flags15"].loc[a["t"], u].to_numpy() == 0) & np.isfinite(y)
    m_fit = a["window"] & fv & (a["gt"] > C.GAIN_FIT_MIN_GTILDE) & (k > k_min)
    g_star, n_fit = fit_gain(y, k, a["gt"], m_fit)
    score = a["window"] & (a["gt"] > C.SCORE_MIN_GTILDE)
    return {"g_star": g_star, "n_fit": n_fit, "nrmse0": nrmse(y, recon(g_star, k, a["gt"]), score), "y": y,
            "score_mask": score}


def event_priors(a: dict, g: pd.Series, units: pd.DataFrame, altitude_m: float, cache: dict) -> dict:
    """Priors G0/G1/G2 for the event's target from its nameplate and its donors' gains (no target power)."""
    win_times = a["t"][a["window"]]
    key_w = (a["name"],)

    def T_of(tilt, az):
        pl = planes(tilt, az)
        key = (tuple(pl) if pl else None,) + key_w
        if key not in cache:
            cache[key] = transposition(pl, win_times, altitude_m)
        return cache[key]

    dn = a["dn"]
    T_don = pd.Series([T_of(units.loc[d, "tilt"], units.loc[d, "azimuth_brick"]) for d in dn], index=dn)
    r_don = units.loc[dn, "DC_AC"]
    meta_ok = units.loc[dn, "in_prior_test"].astype(bool)
    ev = a["ev"]
    T_new = T_of(ev["tilt"], ev["azimuth_brick"])
    pr = priors(g, r_don, T_don, meta_ok, float(ev["DC_AC"]), T_new)
    pr.update({"T_new": T_new, "r_new": float(ev["DC_AC"]), "target_in_prior_test": bool(ev["in_prior_test"])})
    return pr, T_don, r_don, meta_ok


def event_eb(a: dict, g: pd.Series, T_don, r_don, meta_ok, variant: str, days: int = 60) -> dict:
    """Empirical-Bayes prior weight from donor data in the last `days` days before the event start."""
    rows = a["before"] & np.asarray(a["t"] >= a["s"] - pd.Timedelta(days=days))
    K = kappa(a["Y"][rows], a["V"][rows], g.to_numpy(), a["gt"][rows])
    L = loo_median(K)
    daily = daily_gain_estimates(a["Y"][rows], a["V"][rows], a["gt"][rows], L, a["t"][rows],
                                 np.ones(rows.sum(), bool), a["dn"])
    return eb_weights(g, r_don, T_don, meta_ok, daily, variant)
