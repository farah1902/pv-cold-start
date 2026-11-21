"""NB5: index forecasting (quantile LightGBM bank and simple baselines), composition with the gain prior, and scores.

Guide §3.7-§3.9, §5.1-§5.3, D09, D12, D25 (R1), D33. Shared by the development run on the validation units and the
test run after the protocol freeze (D21). A forecast uses only the event's own index (built from its donors in NB3),
the known sun geometry and the event's prior. A target's power is read only to score it.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import config as C

warnings.filterwarnings("ignore", message="All-NaN slice encountered")
warnings.filterwarnings("ignore", message="Mean of empty slice")
warnings.filterwarnings("ignore", message="Degrees of freedom <= 0")

SPD = 96                                    # 15-min steps per day
FIRST_DAY, LAST_DAY = "2021-05-01", "2023-12-31"
TRAIN_START = pd.Timestamp("2021-05-15")    # guide §5.3: the fleet's start
ORIGIN_DAYS = (0, 30, 60)                   # guide §5.3: origins s_e, s_e + 30 d, s_e + 60 d; each forecasts 30 days
LAST_TARGET_MIN = 17 * 60 + 45              # last 15-min slot of the inverter files (D12)
COMMON_WINDOW_MIN = 12 * 60                 # common target window 12:00-17:55 (D12)
TAUS = np.array(C.QUANTILES)
M = C.N_MEMBERS
H = C.HORIZONS

LGB_DEFAULT = {"num_leaves": 31, "learning_rate": 0.03, "min_data_in_leaf": 100}       # guide §5.2
LGB_GRID = [{"num_leaves": nl, "learning_rate": lr, "min_data_in_leaf": md}
            for nl in (15, 31, 63) for lr in (0.03, 0.05) for md in (50, 100, 200)]   # guide §5.2: 18 settings
LGB_FIXED = {"objective": "quantile", "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
             "lambda_l2": 1.0, "seed": C.SEED, "deterministic": True, "force_col_wise": True, "num_threads": 1,
             "verbose": -1}
MAX_ROUNDS, EARLY_STOP, VALID_FRAC = 2000, 100, 0.2                                     # guide §5.2
KNN_K = 50                                                                              # guide §5.1 (A5)
CLIM_DAYS, PEEN_DAYS, MIN_HIST = 60, 20, 10                                             # guide §5.1, §3.9; D33

LAGS = [f"k_lag{j}" for j in range(C.N_LAGS)]
STATE = LAGS + ["kbar_1h", "kbar_2h", "sd_1h", "dk", "sigma", "c", "n"]
FUTURE = ["k_prev_day", "Gt_f", "cosz_f", "sin_az_f", "cos_az_f", "sin_ha_f", "cos_ha_f", "sin_doy_f", "cos_doy_f"]
FEATURES = STATE + FUTURE


# --- Series on the full 15-min grid (night included, so lags never jump across the night) -------------------------
def full_grid() -> pd.DatetimeIndex:
    return pd.date_range(FIRST_DAY, pd.Timestamp(LAST_DAY) + pd.Timedelta(hours=23, minutes=45), freq="15min")


def event_series(name: str, idx: dict, geo15: pd.DataFrame, k_key: str = "k_cens") -> pd.DataFrame:
    """Index (k), fleet state (sigma, c, n) and sun geometry of one event on the full grid; NaN outside daylight."""
    g = full_grid()
    out = pd.DataFrame(index=g)
    out["k"] = idx[k_key][name].reindex(g).astype(float)
    for col in ["sigma", "c", "n"]:
        out[col] = idx[col][name].reindex(g).astype(float)
    geo = geo15.reindex(g)
    out["Gt"] = geo["Gt"]
    out["cosz"] = np.cos(np.radians(geo["zenith"]))
    az, ha = np.radians(geo["azimuth"]), np.radians(geo["hour_angle"])
    out["sin_az"], out["cos_az"] = np.sin(az), np.cos(az)
    out["sin_ha"], out["cos_ha"] = np.sin(ha), np.cos(ha)
    doy = g.dayofyear.to_numpy()
    out["sin_doy"], out["cos_doy"] = np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365)
    out["panel"] = geo["Gt"].notna().to_numpy()
    out["minute"] = g.hour * 60 + g.minute
    return out


def state(S: pd.DataFrame) -> pd.DataFrame:
    """Fleet state at each issue time t (guide §3.7): 16 lags, 1-h and 2-h means, 1-h s.d., last change, sigma, c, n."""
    k = S["k"]
    st = pd.DataFrame({f"k_lag{j}": k.shift(j) for j in range(C.N_LAGS)}, index=S.index)
    L = st[LAGS].to_numpy()
    with np.errstate(all="ignore"):
        n4, n8 = np.isfinite(L[:, :4]).sum(1), np.isfinite(L[:, :8]).sum(1)
        st["kbar_1h"] = np.where(n4 >= 2, np.nanmean(L[:, :4], axis=1), np.nan)
        st["kbar_2h"] = np.where(n8 >= 4, np.nanmean(L[:, :8], axis=1), np.nan)
        st["sd_1h"] = np.where(n4 >= 3, np.nanstd(L[:, :4], axis=1, ddof=1), np.nan)
    st["dk"] = st["k_lag0"] - st["k_lag1"]
    for col in ["sigma", "c", "n"]:
        st[col] = S[col]
    return st


def design(S: pd.DataFrame, st: pd.DataFrame, h: int) -> dict:
    """Features, target index and masks for horizon h at every grid time t (rows of the full grid)."""
    X = st.copy()
    X["k_prev_day"] = S["k"].shift(SPD - h)                 # k(t + h - 96): the target slot one day earlier
    for col in ["Gt", "cosz", "sin_az", "cos_az", "sin_ha", "cos_ha", "sin_doy", "cos_doy"]:
        X[col + "_f"] = S[col].shift(-h)                     # known future geometry u(t + h)
    y = S["k"].shift(-h).to_numpy()
    gt_f = X["Gt_f"].to_numpy()
    issue = S["panel"].to_numpy() & (S["Gt"].to_numpy() > C.ISSUE_MIN_GTILDE) & \
        (S["n"].to_numpy() >= C.ISSUE_MIN_DONORS) & np.isfinite(S["k"].to_numpy())
    target = (S["minute"].to_numpy() + 15 * h <= LAST_TARGET_MIN) & np.nan_to_num(gt_f > C.SCORE_MIN_GTILDE)
    return {"X": X[FEATURES], "y": y, "ok": issue & target, "t": S.index, "h": h}


# --- Quantile LightGBM bank (guide §5.2) --------------------------------------------------------------------------
def fit_bank(X: np.ndarray, y: np.ndarray, params: dict, return_cal: bool = False):
    """Nine quantile models: early stopping on the last 20% of the window (by time), then a refit on the whole window
    with the best number of rounds (D33). With return_cal, also the early-stopped models' predictions on that last
    20% (out of sample for them) and the index of its first row: the conformal calibration set (D35)."""
    import lightgbm as lgb

    cut = int(round(len(y) * (1 - VALID_FRAC)))
    dtr = lgb.Dataset(X[:cut], y[:cut], free_raw_data=False)
    dva = lgb.Dataset(X[cut:], y[cut:], reference=dtr, free_raw_data=False)
    dall = lgb.Dataset(X, y, free_raw_data=False)
    models, best, cal = [], [], []
    for tau in TAUS:
        p = {**LGB_FIXED, **params, "alpha": float(tau)}
        b = lgb.train(p, dtr, MAX_ROUNDS, valid_sets=[dva], callbacks=[lgb.early_stopping(EARLY_STOP, verbose=False)])
        it = int(b.best_iteration) if b.best_iteration else MAX_ROUNDS
        if return_cal:
            cal.append(b.predict(X[cut:], num_iteration=it))
        models.append(lgb.train(p, dall, it))
        best.append(it)
    if return_cal:
        return models, best, np.column_stack(cal), cut
    return models, best


def predict_bank(models: list, X: np.ndarray, anchor: np.ndarray | None = None) -> np.ndarray:
    """(N x 9) index quantiles, sorted (monotone rearrangement) and bounded to [0, 1.5]. With an anchor, the models
    forecast the change from it (k(t), D34) and the anchor is added back."""
    Q = np.column_stack([m.predict(X) for m in models])
    if anchor is not None:
        Q = Q + np.asarray(anchor)[:, None]
    return np.clip(np.sort(Q, axis=1), *C.K_BOUNDS)


def pinball(Q: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Mean pinball loss over the 9 quantiles, per row."""
    d = y[:, None] - Q
    return np.mean(np.maximum(TAUS[None, :] * d, (TAUS[None, :] - 1) * d), axis=1)


# --- Simple baselines (guide §5.1) ----------------------------------------------------------------------------------
def slot_history(k: np.ndarray, pos_target: np.ndarray, days: int) -> np.ndarray:
    """Index at the target's slot on each of the `days` days before the issue day: (N x days)."""
    pos = pos_target[:, None] - SPD * np.arange(1, days + 1)[None, :]
    out = np.full(pos.shape, np.nan)
    ok = pos >= 0
    out[ok] = k[pos[ok]]
    return out


def empirical_quantiles(V: np.ndarray, min_count: int = MIN_HIST) -> np.ndarray:
    with np.errstate(all="ignore"):
        Q = np.nanquantile(V, TAUS, axis=1).T
    Q[np.isfinite(V).sum(1) < min_count] = np.nan
    return Q


def point(v: np.ndarray) -> np.ndarray:
    return np.repeat(np.clip(v, *C.K_BOUNDS)[:, None], len(TAUS), axis=1)


def cliper_weight(k_t: np.ndarray, clim: np.ndarray, y: np.ndarray) -> float:
    """Least-squares weight of persistence in w k_t + (1 - w) clim on training pairs, bounded to [0, 1] (Yang 2019)."""
    m = np.isfinite(k_t) & np.isfinite(clim) & np.isfinite(y)
    a, b = k_t[m] - clim[m], y[m] - clim[m]
    den = float(np.sum(a * a))
    return float(np.clip(np.sum(a * b) / den, 0, 1)) if den > 0 else 0.5


def knn_quantiles(Xtr: np.ndarray, ytr: np.ndarray, Xf: np.ndarray, k: int = KNN_K) -> np.ndarray:
    """A5: the 9 empirical quantiles of the future index of the K nearest training states (standardised features,
    missing values at the training mean)."""
    from sklearn.neighbors import NearestNeighbors

    mu = np.nanmean(Xtr, axis=0)
    sd = np.nanstd(Xtr, axis=0)
    sd[~np.isfinite(sd) | (sd == 0)] = 1.0
    mu[~np.isfinite(mu)] = 0.0
    Z = np.nan_to_num((Xtr - mu) / sd)
    Zf = np.nan_to_num((Xf - mu) / sd)
    nn = NearestNeighbors(n_neighbors=min(k, len(Z))).fit(Z)
    _, ind = nn.kneighbors(Zf)
    return np.quantile(ytr[ind], TAUS, axis=1).T


# --- One event and one origin: every index forecaster ----------------------------------------------------------
def run_origin(S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict,
               models=("LGB", "A0", "A1", "PeEn", "CLIPER", "A5", "A7")) -> tuple[pd.DataFrame, dict]:
    """Train on pairs with target before the origin (from TRAIN_START, issue rules applied), forecast the issue times
    in [origin, end). Returns long rows (model, h, t, q0.1..q0.9) and diagnostics. Index level only."""
    st = state(S)
    k = S["k"].to_numpy()
    t = S.index
    rows, diag = [], {}
    for h in H:
        D = design(S, st, h)
        X = D["X"].to_numpy(dtype=float)
        tgt_time = t + pd.Timedelta(minutes=15 * h)
        tr = D["ok"] & np.isfinite(D["y"]) & (t >= TRAIN_START) & (tgt_time < origin)
        fc = D["ok"] & (t >= origin) & (t < end)
        if fc.sum() == 0 or tr.sum() < 50:
            diag[h] = {"n_train": int(tr.sum()), "n_fc": int(fc.sum()), "skipped": True}
            continue
        pos_f = np.where(fc)[0] + h
        pos_tr = np.where(tr)[0] + h
        out = {}
        if "LGB" in models:
            bank, best = fit_bank(X[tr], D["y"][tr] - k[tr], params)        # change from persistence (D34)
            out["LGB"] = predict_bank(bank, X[fc], anchor=k[fc])
            diag[h] = {"best_iter": best}
        clim_f = slot_history(k, pos_f, CLIM_DAYS)
        if "A0" in models:
            out["A0"] = empirical_quantiles(clim_f)
        if "A1" in models:
            out["A1"] = point(k[fc])
        if "PeEn" in models:
            out["PeEn"] = empirical_quantiles(slot_history(k, pos_f, PEEN_DAYS))
        if "CLIPER" in models:
            with np.errstate(all="ignore"):
                clim_tr = np.nanmedian(slot_history(k, pos_tr, CLIM_DAYS), axis=1)
                clim_pt = np.nanmedian(clim_f, axis=1)
            w = cliper_weight(k[tr], clim_tr, D["y"][tr])
            out["CLIPER"] = point(np.where(np.isfinite(clim_pt), w * k[fc] + (1 - w) * clim_pt, np.nan))
            diag.setdefault(h, {})["cliper_w"] = w
        if "A5" in models:
            out["A5"] = knn_quantiles(X[tr], D["y"][tr], X[fc])
        if "A7" in models:
            out["A7"] = point(D["y"][fc])           # oracle: the same-time index at the target (not a forecast)
        d = diag.setdefault(h, {})
        d.update({"n_train": int(tr.sum()), "n_fc": int(fc.sum())})
        for m, Q in out.items():
            f = pd.DataFrame(Q, columns=[f"q{tau:.1f}" for tau in TAUS])
            f.insert(0, "t", t[fc])
            f.insert(0, "h", h)
            f.insert(0, "model", m)
            rows.append(f)
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), diag


def run_origin_source(S_src: pd.DataFrame, S_fleet: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp,
                      params: dict, models=("LGB", "A1", "A7")) -> tuple[pd.DataFrame, dict]:
    """Rows with an external index in place of the fleet index (guide §4.2, D51): A4 and A4b are the LightGBM bank on
    the raw and the corrected pyranometer index; A9 is the persisted satellite index (A1 on it) and A9n its same-time
    value (A7, oracle). Features and targets come from the source alone: the fleet fields sigma, c and n are left
    empty, so no fleet information enters a forecast. The issue and target rules are the fleet's, so these rows are
    scored on the fleet models' slots; the source's own index must also exist at the issue time."""
    st = state(S_src)
    st[["sigma", "c", "n"]] = np.nan
    st_f = state(S_fleet)
    k = S_src["k"].to_numpy()
    t = S_src.index
    rows, diag = [], {}
    for h in H:
        D = design(S_src, st, h)
        ok = design(S_fleet, st_f, h)["ok"] & np.isfinite(k)
        X = D["X"].to_numpy(dtype=float)
        tgt_time = t + pd.Timedelta(minutes=15 * h)
        tr = ok & np.isfinite(D["y"]) & (t >= TRAIN_START) & (tgt_time < origin)
        fc = ok & (t >= origin) & (t < end)
        if fc.sum() == 0 or tr.sum() < 50:
            diag[h] = {"n_train": int(tr.sum()), "n_fc": int(fc.sum()), "skipped": True}
            continue
        out = {}
        if "LGB" in models:
            bank, best = fit_bank(X[tr], D["y"][tr] - k[tr], params)        # change from persistence (D34)
            out["LGB"] = predict_bank(bank, X[fc], anchor=k[fc])
            diag[h] = {"best_iter": best}
        if "A1" in models:
            out["A1"] = point(k[fc])
        if "A7" in models:
            out["A7"] = point(D["y"][fc])           # oracle: the source's same-time index at the target
        d = diag.setdefault(h, {})
        d.update({"n_train": int(tr.sum()), "n_fc": int(fc.sum())})
        for m, Q in out.items():
            f = pd.DataFrame(Q, columns=[f"q{tau:.1f}" for tau in TAUS])
            f.insert(0, "t", t[fc])
            f.insert(0, "h", h)
            f.insert(0, "model", m)
            rows.append(f)
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), diag


def lgb_variant(S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict, target: str = "level",
                pooled: bool = False) -> tuple[pd.DataFrame, dict]:
    """Development variants of the LightGBM bank (D34), same issue rows as run_origin.

    target 'level' forecasts k(t + h); 'change' forecasts k(t + h) - k(t) and adds k(t) back (persistence anchor).
    pooled: one model per quantile over all horizons, with h as a feature (guide §5.2 ablation).
    """
    st = state(S)
    t = S.index
    kt = S["k"].to_numpy()
    parts = {}
    for h in H:
        D = design(S, st, h)
        X = D["X"].copy()
        if pooled:
            X["h"] = h                                       # only the pooled model sees the horizon
        tgt_time = t + pd.Timedelta(minutes=15 * h)
        tr = D["ok"] & np.isfinite(D["y"]) & (t >= TRAIN_START) & (tgt_time < origin)
        fc = D["ok"] & (t >= origin) & (t < end)
        yy = D["y"] - kt if target == "change" else D["y"]
        parts[h] = (X.to_numpy(dtype=float), yy, tr, fc)
    label = "LGB_" + target + ("_pooled" if pooled else "")
    rows, diag = [], {}
    cols = [f"q{tau:.1f}" for tau in TAUS]

    def emit(h, Q):
        fc = parts[h][3]
        if target == "change":
            Q = Q + kt[fc][:, None]
        Q = np.clip(np.sort(Q, axis=1), *C.K_BOUNDS)
        f = pd.DataFrame(Q, columns=cols)
        f.insert(0, "t", t[fc]); f.insert(0, "h", h); f.insert(0, "model", label)
        rows.append(f)

    if pooled:
        order = np.argsort(np.concatenate([t[parts[h][2]].asi8 for h in H]), kind="stable")   # time order for early stopping
        Xtr = np.vstack([parts[h][0][parts[h][2]] for h in H])[order]
        ytr = np.concatenate([parts[h][1][parts[h][2]] for h in H])[order]
        models, best = fit_bank(Xtr, ytr, params)
        diag["pooled"] = {"n_train": int(len(ytr)), "best_iter": best}
        for h in H:
            if parts[h][3].any():
                emit(h, np.column_stack([m.predict(parts[h][0][parts[h][3]]) for m in models]))
    else:
        for h in H:
            X, yy, tr, fc = parts[h]
            if fc.sum() == 0 or tr.sum() < 50:
                continue
            models, best = fit_bank(X[tr], yy[tr], params)
            diag[h] = {"n_train": int(tr.sum()), "best_iter": best}
            emit(h, np.column_stack([m.predict(X[fc]) for m in models]))
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), diag


def variant_task(name: str, S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict, target: str,
                 pooled: bool) -> tuple:
    rows, diag = lgb_variant(S, origin, end, params, target, pooled)
    if len(rows):
        rows.insert(0, "origin", origin)
        rows.insert(0, "event", name)
    return name, origin, rows, diag


def origin_task(name: str, S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict) -> tuple:
    """One (event, origin) unit of work for joblib: every index forecaster, labelled with the event and origin."""
    rows, diag = run_origin(S, origin, end, params)
    if len(rows):
        rows.insert(0, "origin", origin)
        rows.insert(0, "event", name)
    return name, origin, rows, diag


def cv_task(S: pd.DataFrame, params: dict, fold_start: pd.Timestamp, fold_end: pd.Timestamp) -> dict:
    """Time-series CV (guide §5.2): train on targets before the fold, score the index quantiles of the LightGBM bank
    by the mean pinball loss on targets inside the fold. Returns {h: (mean pinball, n, best rounds)}."""
    st = state(S)
    t = S.index
    res = {}
    for h in H:
        D = design(S, st, h)
        X = D["X"].to_numpy(dtype=float)
        tgt_time = t + pd.Timedelta(minutes=15 * h)
        good = D["ok"] & np.isfinite(D["y"]) & (t >= TRAIN_START)
        tr = good & (tgt_time < fold_start)
        va = good & (tgt_time >= fold_start) & (tgt_time < fold_end)
        kt = S["k"].to_numpy()
        bank, best = fit_bank(X[tr], D["y"][tr] - kt[tr], params)       # change from persistence (D34)
        res[h] = (float(pinball(predict_bank(bank, X[va], anchor=kt[va]), D["y"][va]).mean()), int(va.sum()), best)
    return res


# --- Composition with the gain prior (guide §3.8) ------------------------------------------------------------------
def member_levels(seed: int = C.SEED) -> tuple[np.ndarray, np.ndarray]:
    """Stratified index levels (m - 0.5) / M, and the same levels in a fixed random order for the gain draws, so the
    index and gain draws are independent while each marginal stays stratified (D33)."""
    lv = (np.arange(1, M + 1) - 0.5) / M
    return lv, np.random.default_rng(seed).permutation(lv)


def index_members(Q: np.ndarray, levels: np.ndarray, bounds: tuple = C.K_BOUNDS) -> np.ndarray:
    """Quantile function linear between the 9 quantiles, with linear tails, bounded (index: [0, 1.5]): (N x M)."""
    lo = Q[:, [0]] + (levels[None, :] - TAUS[0]) * (Q[:, [1]] - Q[:, [0]]) / (TAUS[1] - TAUS[0])
    hi = Q[:, [-1]] + (levels[None, :] - TAUS[-1]) * (Q[:, [-1]] - Q[:, [-2]]) / (TAUS[-1] - TAUS[-2])
    j = np.clip(np.searchsorted(TAUS, levels) - 1, 0, len(TAUS) - 2)
    w = (levels - TAUS[j]) / (TAUS[j + 1] - TAUS[j])
    mid = Q[:, j] * (1 - w)[None, :] + Q[:, j + 1] * w[None, :]
    out = np.where(levels[None, :] < TAUS[0], lo, np.where(levels[None, :] > TAUS[-1], hi, mid))
    return np.clip(out, *bounds)


def gain_members(prior: float, B_rel: np.ndarray, gain_levels: np.ndarray) -> np.ndarray:
    """g^(m) = prior x the empirical quantile of the relative uncertainty set at the member's gain level (guide §3.5)."""
    return prior * np.quantile(np.asarray(B_rel, dtype=float), gain_levels)


def power_members(Q: np.ndarray, gt_target: np.ndarray, g_m: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Normalised power members min(1, g^(m) Q_k(tau^(m)) Gt(t + h)): (N x M)."""
    return np.minimum(1.0, g_m[None, :] * index_members(Q, levels) * gt_target[:, None])


# --- Scores (guide §3.9), normalised by the AC rating -------------------------------------------------------------
def scores(Y: np.ndarray, y: np.ndarray) -> dict:
    """Point and probabilistic scores of member forecasts Y (N x M) against observations y (N), all finite."""
    n, m = Y.shape
    if n == 0:
        return {"n": 0}
    mean, med = Y.mean(1), np.median(Y, axis=1)
    crps = crps_members(Y, y)
    lo, hi = np.quantile(Y, 0.1, axis=1), np.quantile(Y, 0.9, axis=1)
    a = 0.2
    iscore = (hi - lo) + 2 / a * (lo - y) * (y < lo) + 2 / a * (y - hi) * (y > hi)
    return {"n": int(n), "nRMSE": float(np.sqrt(np.mean((y - mean) ** 2))), "nMAE": float(np.mean(np.abs(y - med))),
            "nMBE": float(np.mean(y - mean)), "CRPS": float(crps.mean()), "PICP80": float(np.mean((y >= lo) & (y <= hi))),
            "PINAW": float(np.mean(hi - lo)), "IS80": float(iscore.mean())}


def crps_members(Y: np.ndarray, y: np.ndarray) -> np.ndarray:
    """CRPS of an ensemble per row: mean |x - y| - (1 / 2M^2) sum |x_i - x_j|, via the sorted members."""
    m = Y.shape[1]
    Ys = np.sort(Y, axis=1)
    return np.abs(Y - y[:, None]).mean(1) - (Ys * (2 * np.arange(1, m + 1) - m - 1)[None, :]).sum(1) / m ** 2


# --- Conformal calibration on pseudo cold starts (D06, guide §6 item 14, D35) ----------------------------------------
PAIRS = [(0, 8), (1, 7), (2, 6), (3, 5)]          # q0.1-q0.9 (80%), q0.2-q0.8 (60%), q0.3-q0.7 (40%), q0.4-q0.6 (20%)
PAIR_ALPHA = np.array([0.2, 0.4, 0.6, 0.8])
PAIR_NAMES = ["80", "60", "40", "20"]
MIN_CAL = 50                                       # fewer conformity scores: no correction (D35)
POWER_BOUNDS = (0.0, C.OVER_LIMIT)                 # normalised power can exceed 1 slightly (QC over-limit 1.05)


def lgb_with_cal(S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict) -> tuple:
    """The LightGBM forecasts of run_origin (same rows and values), plus the calibration set: the early-stopped models'
    index quantiles on the last 20% of each horizon's training pairs (targets before the origin)."""
    st = state(S)
    k = S["k"].to_numpy()
    t = S.index
    cols = [f"q{tau:.1f}" for tau in TAUS]
    rows, cal = [], []

    def frame(model, h, times, Q):
        f = pd.DataFrame(Q, columns=cols)
        f.insert(0, "t", times); f.insert(0, "h", h); f.insert(0, "model", model)
        return f

    for h in H:
        D = design(S, st, h)
        X = D["X"].to_numpy(dtype=float)
        tgt_time = t + pd.Timedelta(minutes=15 * h)
        tr = D["ok"] & np.isfinite(D["y"]) & (t >= TRAIN_START) & (tgt_time < origin)
        fc = D["ok"] & (t >= origin) & (t < end)
        if fc.sum() == 0 or tr.sum() < 50:
            continue
        models, _, qcal, cut = fit_bank(X[tr], D["y"][tr] - k[tr], params, return_cal=True)
        rows.append(frame("LGB", h, t[fc], predict_bank(models, X[fc], anchor=k[fc])))
        pos = np.where(tr)[0][cut:]
        cal.append(frame("LGB_cal", h, t[pos], np.clip(np.sort(qcal + k[pos][:, None], axis=1), *C.K_BOUNDS)))
    cat = lambda x: pd.concat(x, ignore_index=True) if x else pd.DataFrame()   # noqa: E731
    return cat(rows), cat(cal)


def cal_task(name: str, S: pd.DataFrame, origin: pd.Timestamp, end: pd.Timestamp, params: dict) -> tuple:
    rows, cal = lgb_with_cal(S, origin, end, params)
    for f in (rows, cal):
        if len(f):
            f.insert(0, "origin", origin)
            f.insert(0, "event", name)
    return name, origin, rows, cal


def pseudo_priors(g_don: pd.Series, r_don: pd.Series, T_don: pd.Series, meta_ok: pd.Series, variant: str) -> dict:
    """Each donor treated as new: its prior and relative uncertainty set from the other donors only (leave-one-out),
    for the event's prior variant. G2 / G1: clean-metadata donors, beta from the others times r T (T = 1 for G1).
    G0 (metadata-error targets): the median of the other donors' gains, all donors with a gain."""
    out = {}
    if variant == "G0":
        g = g_don.dropna()
        for d in g.index:
            o = g.drop(d).to_numpy()
            out[d] = (float(np.median(o)), o / np.median(o))
        return out
    rT = r_don * (T_don if variant == "G2" else 1.0)
    ok = meta_ok & g_don.notna() & r_don.notna()
    b = (g_don / rT)[ok]
    for d in b.index:
        o = b.drop(d).to_numpy()
        out[d] = (float(np.median(o) * rT[d]), o / np.median(o))
    return out


def power_quantiles(Y: np.ndarray) -> np.ndarray:
    """The 9 quantiles (q0.1-q0.9) of the power members: (N x 9)."""
    return np.quantile(Y, TAUS, axis=1).T


def conformity(Qp: np.ndarray, y: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """CQR scores (Romano et al. 2019) for the four central intervals, normalised by Gt(t + h): (N x 4)."""
    lo = Qp[:, [a for a, _ in PAIRS]]
    hi = Qp[:, [b for _, b in PAIRS]]
    return np.maximum(lo - y[:, None], y[:, None] - hi) / gt[:, None]


def conformal_correction(E: np.ndarray) -> np.ndarray:
    """Per interval: the ceil((1 - alpha)(n + 1))-th smallest score (split-conformal quantile); 0 under MIN_CAL."""
    n = len(E)
    if n < MIN_CAL:
        return np.zeros(len(PAIRS))
    k = np.minimum(np.ceil((1 - PAIR_ALPHA) * (n + 1)).astype(int), n)
    Es = np.sort(E, axis=0)
    return Es[k - 1, np.arange(len(PAIRS))]


def apply_conformal(Qp: np.ndarray, gt: np.ndarray, corr: np.ndarray) -> np.ndarray:
    """Widen (or narrow) each central interval by corr x Gt(t + h); the median is unchanged; sorted and bounded."""
    Q = Qp.copy()
    for j, (a, b) in enumerate(PAIRS):
        Q[:, a] -= corr[j] * gt
        Q[:, b] += corr[j] * gt
    return np.clip(np.sort(Q, axis=1), *POWER_BOUNDS)


def quantile_scores(Qp: np.ndarray, y: np.ndarray, levels: np.ndarray) -> dict:
    """Probabilistic scores of a 9-quantile power forecast: coverage of the four central intervals, PINAW and IS of
    the 80% interval, and the CRPS of the distribution rebuilt from the 9 quantiles (as for the index, D33)."""
    if len(y) == 0:
        return {"n": 0}
    out = {"n": int(len(y))}
    for j, (a, b) in enumerate(PAIRS):
        out[f"cover{PAIR_NAMES[j]}"] = float(np.mean((y >= Qp[:, a]) & (y <= Qp[:, b])))
    lo, hi, al = Qp[:, 0], Qp[:, 8], 0.2
    out["PINAW"] = float(np.mean(hi - lo))
    out["IS80"] = float(np.mean((hi - lo) + 2 / al * (lo - y) * (y < lo) + 2 / al * (y - hi) * (y > hi)))
    out["CRPS_q"] = float(crps_members(index_members(Qp, levels, POWER_BOUNDS), y).mean())
    return out
