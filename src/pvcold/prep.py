"""NB2: time base, quality control, 15-min panel, start dates, events, donor sets and the hidden-unit test bed.

Guide §2 (preprocessing steps 1-7), D08, D12, D13, D18, D27, D28. Nothing here is tuned on test data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import io_hkust as io

FIRST_DAY, LAST_DAY = "2021-05-01", "2023-12-31"
# QC flag bits (5 min and 15 min)
NIGHT, NEG, FROZEN, OVER, OUTAGE = 1, 2, 4, 8, 16
FLAG_NAMES = {NIGHT: "night", NEG: "negative", FROZEN: "frozen", OVER: "over_limit", OUTAGE: "outage"}

# Metadata errors (F21, guide §2): AC rating corrected; the unit stays out of the DC/AC prior test (G0).
AC_CORRECTIONS = {
    "Indoor Sports Centre_Inverter": (33.3, "station rating 33.3 kW (= SE33_3K); model string STP 10.0 is wrong"),
    "Zone D_Inverter_2": (50.0, "empirical: p99.9 49.9 kW (SE50K size); model string SE25K is wrong"),
}
METADATA_ERROR_UNITS = {"Indoor Sports Centre_Inverter", "Zone D_Inverter_1", "Zone D_Inverter_2"}

# Event definitions: (name, set, start, target) with target = list of inverter stems, or ("site", site stem,
# inverter stems that take over when their file starts). Starts: D08, D27; validation units: guide §2.
EVENTS = [
    ("SQ Block S", "scored", "2021-10-05", ["SQ Block S_Inverter"]),
    ("Zone A5", "scored", "2021-10-05", ["Zone A5_Inverter"]),
    ("SQ Block R", "scored", "2021-10-06", ["SQ Block R_Inverter"]),
    ("Zone A7", "scored", "2021-10-09", ["Zone A7_Inverter"]),
    ("Zone A6", "scored", "2021-10-14", ["Zone A6_Inverter"]),
    ("Zone J2", "scored", "2021-11-13", ("site", "Zone J2", ["Zone J2_Inverter"])),
    ("Indoor Sports Centre", "scored", "2021-11-17", ["Indoor Sports Centre_Inverter"]),
    ("Zone D", "scored", "2022-01-19", ("site", "Zone D", None)),
    ("UG Hall8", "scored", "2023-01-05", ["UG Hall8_Inverter"]),
    ("UG Hall9", "scored", "2023-02-11", ["UG Hall9_Inverter"]),
    ("Zone A2 inverters 2-3", "scored", "2023-05-16", ["Zone A2_Inverter_2", "Zone A2_Inverter_3"]),
    ("SQ Block P", "scored", "2023-06-22", ["SQ Block P_Inverter"]),
    ("Shaw Auditorium", "scored", "2023-07-09", ["Shaw Auditorium_Inverter"]),
    ("Library", "sensitivity", "2022-06-01", ["Library_Inverter_1", "Library_Inverter_2", "Library_Inverter_3"]),
    ("Wong Check She", "sensitivity", "2021-12-01",
     ["Wong Check She Research Centre_Inverter_1", "Wong Check She Research Centre_Inverter_2"]),
    ("Zone J1", "sensitivity", "2022-03-01", ("site", "Zone J1", ["Zone J1_Inverter"])),
    ("Zone L2", "sensitivity", "2022-06-01", ("site", "Zone L2", ["Zone L2_Inverter"])),
] + [(u.replace("_Inverter", "").replace("_", " "), "validation", None, [u]) for u in C.VALIDATION_UNITS]
# Units excluded from the donor set of an event besides its target units (same station, station-level target).
EXTRA_OWN_UNITS = {"Zone D": ["Zone D_Inverter_1", "Zone D_Inverter_2"]}


# --- Time grid and geometry ---------------------------------------------------------------------
def grid(step_min: int) -> pd.DatetimeIndex:
    """Naive Hong Kong timestamps (as recorded) from 06:00 to the last slot of each day."""
    days = pd.date_range(FIRST_DAY, LAST_DAY, freq="D")
    last = 17 * 60 + 55 if step_min == 5 else 17 * 60 + 45
    offs = pd.to_timedelta(np.arange(6 * 60, last + 1, step_min), unit="min")
    return pd.DatetimeIndex((days.values[:, None] + offs.values[None, :]).ravel())


def geometry(stamps: pd.DatetimeIndex, shift_min: float, altitude_m: float) -> pd.DataFrame:
    """Solar geometry and Ineichen clear sky at the effective time stamps + shift (minutes)."""
    import pvlib

    eff = (stamps + pd.Timedelta(minutes=shift_min)).tz_localize(C.TZ)
    loc = pvlib.location.Location(C.SITE_LAT, C.SITE_LON, tz=C.TZ, altitude=altitude_m)
    sp = loc.get_solarposition(eff)
    cs = loc.get_clearsky(eff, model="ineichen", solar_position=sp)["ghi"]
    doy = eff.dayofyear.to_numpy()
    eot = pvlib.solarposition.equation_of_time_spencer71(doy)
    ha = pvlib.solarposition.hour_angle(eff, C.SITE_LON, eot)
    out = pd.DataFrame({"zenith": sp["apparent_zenith"].to_numpy(), "elevation": sp["apparent_elevation"].to_numpy(),
                        "azimuth": sp["azimuth"].to_numpy(), "hour_angle": np.asarray(ha), "doy": doy,
                        "G_cs": cs.to_numpy()}, index=stamps)
    out["Gt"] = out["G_cs"] / 1000.0
    return out


# --- Power ----------------------------------------------------------------------------------------
def load_power_5min(stems) -> pd.DataFrame:
    """Wide frame of 5-min power (W) on the regular grid; NaN where missing or before a unit's first row."""
    g = grid(5)
    files = io.inverter_files()
    cols = {}
    for s in stems:
        df, _ = io.read_inverter(files[s])
        cols[s] = df.set_index("time")["P_W"].reindex(g)
    return pd.DataFrame(cols, index=g)


def load_site_15min(stem: str) -> pd.Series:
    df, _ = io.read_site(io.site_files("15min")[stem])
    return df.set_index("time")["P_W"]


def unit_table(inv: pd.DataFrame, st: pd.DataFrame, mc: pd.DataFrame) -> pd.DataFrame:
    """One row per inverter file: AC used, its source, DC, DC/AC, metadata flags, orientation."""
    t = inv.dropna(subset=["file"]).set_index("file")
    stn = st.set_index("station")
    rows = []
    for f, r in t.iterrows():
        ac, src = r["AC_kW"], "model name"
        if f in AC_CORRECTIONS:
            ac, src = AC_CORRECTIONS[f]
        s = stn.loc[r["station"]]
        rows.append({"unit": f, "station": r["station"], "model": r["inverter_model"], "AC_kW": ac, "AC_source": src,
                     "DC_kWp": r["DC_kWp"], "DC_AC": r["DC_kWp"] / ac, "metadata_error": f in METADATA_ERROR_UNITS,
                     "tilt": s["tilt"], "azimuth_brick": s["azimuth_brick"], "connection_date": str(s["connection_date"])[:10],
                     "p999_over_AC_model": float(mc.set_index("file").loc[f, "p999_over_AC"])})
    u = pd.DataFrame(rows).set_index("unit")
    u["in_prior_test"] = ~u["metadata_error"]
    u["flat"] = (u["tilt"] == "0deg") & (u["azimuth_brick"] == "0deg")
    return u


# --- Time label (guide §2 step 1) ------------------------------------------------------------------
def clear_days(y_fleet: pd.Series, gt_nominal: pd.Series, n_days: int = 30, min_units: pd.Series | None = None) -> list:
    """The n_days days with the highest ratio of fleet normalised energy to clear-sky energy (smooth, clear days)."""
    day = y_fleet.index.normalize()
    ok = y_fleet.notna()
    if min_units is not None:
        ok &= min_units >= 10
    ratio = y_fleet[ok].groupby(day[ok]).sum() / gt_nominal[ok].groupby(day[ok]).sum()
    count = ok.groupby(day).sum()
    ratio = ratio[count.reindex(ratio.index) >= 0.95 * ok.groupby(day).size().max()]
    rough = y_fleet.diff().abs().groupby(day).mean().reindex(ratio.index)
    cand = ratio[rough <= rough.quantile(0.5)]  # smooth half of the days
    return list(cand.sort_values(ascending=False).index[:n_days])


def label_offset(series: pd.Series, days: list, altitude_m: float, shifts=np.arange(-12.5, 12.51, 0.5)) -> pd.DataFrame:
    """Correlation between a normalised power series and clear-sky GHI at stamp + shift, on the given days."""
    m = series.index.normalize().isin(days) & series.notna()
    s = series[m]
    out = []
    for sh in shifts:
        gcs = geometry(s.index, sh, altitude_m)["G_cs"]
        use = gcs > 0
        out.append({"shift_min": float(sh), "corr": float(np.corrcoef(s[use], gcs[use])[0, 1]), "n": int(use.sum())})
    return pd.DataFrame(out)


# --- Quality control (guide §2 step 2) ---------------------------------------------------------------
def qc_5min(P: pd.DataFrame, ac_kw: pd.Series, geo5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Return (cleaned power W, flag bitmask int8, crude fleet index used for outages)."""
    y = P.div(ac_kw * 1000.0, axis=1)
    gt = geo5["Gt"]
    day = gt > 0.1
    k_crude = y[day.to_numpy()].div(gt[day], axis=0).median(axis=1).reindex(P.index)
    flags = pd.DataFrame(0, index=P.index, columns=P.columns, dtype=np.int8)
    night = (geo5["elevation"] < 0).to_numpy()[:, None]
    flags += np.where(night & (P > 0).to_numpy(), NIGHT, 0).astype(np.int8)
    flags += np.where((P < 0).to_numpy(), NEG, 0).astype(np.int8)
    flags += np.where((y > C.OVER_LIMIT).to_numpy(), OVER, 0).astype(np.int8)
    out_mask = (P == 0).to_numpy() & (k_crude > C.OUTAGE_INDEX).to_numpy()[:, None] & (gt > 0.1).to_numpy()[:, None]
    flags += np.where(out_mask, OUTAGE, 0).astype(np.int8)
    n_frozen = int(C.FROZEN_MINUTES / 5)
    dayid = P.index.normalize()
    for c in P.columns:
        v = P[c]
        run = (v.ne(v.shift()) | (dayid != np.roll(dayid, 1))).cumsum()
        size = v.groupby(run).transform("size")
        fr = (size >= n_frozen) & (v > 0) & (gt > 0.05)
        flags.loc[fr.to_numpy(), c] += FROZEN
    clean = P.mask(P < 0).mask(pd.DataFrame(night & np.ones(P.shape, bool), index=P.index, columns=P.columns))
    return clean, flags, k_crude


def aggregate_15(P5: pd.DataFrame, f5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """15-min mean of the three 5-min values (valid if >= 2 present); flags are OR-ed; count of valid values."""
    key = P5.index.floor("15min")
    n = P5.notna().groupby(key).sum()
    P15 = P5.groupby(key).mean().where(n >= 2)
    F15 = sum((f5 & b).groupby(key).max() for b in FLAG_NAMES).astype(np.int8)  # OR of the three values, per bit
    return P15, F15, n


# --- Starts, events, donors ---------------------------------------------------------------------------
def rule_start(P15: pd.Series, ac_kw: float, gt15: pd.Series) -> pd.Timestamp | None:
    """First day d with valid power (> 2% of AC) in >= 70% of daylight slots (Gt > 0.1) on d and d+1."""
    day = gt15 > 0.1
    ok = (P15 > C.VALID_POWER_FRAC * ac_kw * 1000.0)[day]
    share = ok.groupby(ok.index.normalize()).mean()
    both = (share >= C.START_DAYLIGHT_SHARE) & (share.shift(-1) >= C.START_DAYLIGHT_SHARE)
    both &= (share.index.to_series().diff(-1).dt.days == -1).to_numpy()  # d+1 is the next calendar day
    hits = share.index[both.to_numpy()]
    return hits[0] if len(hits) else None


def event_target(ev, P15: pd.DataFrame, site_shift_slots: int) -> pd.Series:
    """Target power (W) at 15 min: inverter sum, or a site series until the inverter file takes over."""
    target = ev[3]
    if isinstance(target, list):
        return P15[target].sum(axis=1, min_count=len(target))
    _, site_stem, invs = target
    s = load_site_15min(site_stem)
    s.index = s.index + pd.Timedelta(minutes=15 * site_shift_slots)
    s = s.reindex(P15.index)
    if invs:
        inv = P15[invs].sum(axis=1, min_count=len(invs))
        first = P15[invs].first_valid_index()
        s = s.where(s.index < first, inv)
    return s


def valid_days(target: pd.Series, start: pd.Timestamp, gt15: pd.Series, flags: pd.Series | None = None) -> int:
    win = (target.index >= start) & (target.index < start + pd.Timedelta(days=90)) & (gt15 > 0.1).to_numpy()
    ok = target[win].notna()
    if flags is not None:
        ok &= (flags[win] & OUTAGE) == 0
    share = ok.groupby(ok.index.normalize()).mean()
    return int((share >= 0.7).sum())


def donors_at(start: pd.Timestamp, units: pd.DataFrame, own: set, P15: pd.DataFrame) -> list:
    """Units started (rule start) at least 14 full days before the event, online in the 7 days before it."""
    out = []
    recent = P15.loc[start - pd.Timedelta(days=7): start - pd.Timedelta(minutes=15)]
    for u, r in units.iterrows():
        if u in own or pd.isna(r["rule_start"]):
            continue
        if (start - r["rule_start"]).days >= C.DONOR_MIN_FULL_DAYS and recent[u].notna().any():
            out.append(u)
    return out


def drifted(start: pd.Timestamp, boundary: pd.Timestamp) -> bool:
    days = pd.date_range(start, periods=90, freq="D")
    return bool((days >= boundary).sum() >= 45)


def pseudo_testbed(units: pd.DataFrame, P15: pd.DataFrame, gt15: pd.Series, event_units: set,
                   dates=("2022-04-01", "2023-04-01"), n_groups: int = 5, seed: int = C.SEED) -> pd.DataFrame:
    """D18: hidden-unit cold starts at one stable and one drifted date (same season), units in station groups."""
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        for u, r in units.iterrows():
            if pd.isna(r["rule_start"]) or (d - r["rule_start"]).days < 90:
                continue  # mature units only: online at least 90 days before the pseudo start
            if u in event_units and pd.notna(r["event_window_end"]) and r["event_window_end"] > d:
                continue  # its real event window is still running
            nv = valid_days(P15[u], d, gt15)
            if nv >= C.MIN_VALID_DAYS_IN_90:
                rows.append({"date": d.date(), "unit": u, "station": r["station"], "valid_days_90": nv})
    tb = pd.DataFrame(rows)
    rng = np.random.default_rng(seed)
    stations = tb.groupby("station")["unit"].nunique()
    order = list(stations.index)
    rng.shuffle(order)
    order = sorted(order, key=lambda s: -stations[s])  # stable sort keeps the shuffled order among ties
    load = [0] * n_groups
    group = {}
    for s in order:
        g = int(np.argmin(load))
        group[s] = g + 1
        load[g] += stations[s]
    tb["group"] = tb["station"].map(group)
    return tb
