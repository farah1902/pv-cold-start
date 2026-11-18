"""NB1: audit of the HKUST dataset. Every function returns tables; write_outputs() stores them all-or-nothing.

Nothing here is tuned: the audit describes the data and reproduces the claims of the review audit of 18 Nov 2026
(F01, F05, F06, F16) and of the sensor audit of 31 Oct 2026 (F09) from code.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from . import io_hkust as io

LONG_RUNNING = [  # units online before 2021-05-22, used for the crude fleet proxy of the audit only
    "SQ1_Inverter", "SQ2_Inverter", "SQ3_Inverter", "SQ4_Inverter", "UG Hall3_Inverter", "UG Hall4_Inverter",
    "UG Hall6_Inverter", "UG Hall7_Inverter", "LSK North_Inverter", "LSK South_Inverter",
]


# --- Units ------------------------------------------------------------------------------------
def units() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Inverter and station tables with the file stem of each inverter and station attached."""
    nodes = io.parse_ttl()
    inv, st = io.unit_tables(nodes)
    inv_map = io.match_names(io.inverter_files(), inv["inverter"])
    st15 = io.match_names(io.site_files("15min"), st["station"])
    st1h = io.match_names(io.site_files("1h"), st["station"])
    inv["file"] = inv["inverter"].map({v: k for k, v in inv_map.items()})
    st["site_file_15min"] = st["station"].map({v: k for k, v in st15.items()})
    st["site_file_1h"] = st["station"].map({v: k for k, v in st1h.items()})
    return inv, st, inv_map, {**st15, **st1h}


# --- Inventory --------------------------------------------------------------------------------
def inventory_inverters(inv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per inverter file, plus the daily energy (06:00-17:55) of every inverter (kWh, wide frame)."""
    rows, daily = [], {}
    ac = inv.set_index("file")["AC_kW"]
    for stem, path in io.inverter_files().items():
        df, fmt = io.read_inverter(path)
        t = df["time"]
        day = t.dt.normalize()
        per_day = day.value_counts()
        tod = t.dt.strftime("%H:%M")
        p = df["P_W"]
        first_day = day.iloc[0]
        p_day1 = p[day == first_day]
        a = ac.get(stem, np.nan)
        rows.append({
            "file": stem, "time_format": fmt, "rows": len(df), "first": t.iloc[0], "last": t.iloc[-1],
            "days": int(per_day.size), "rows_per_day_mode": int(per_day.mode().iloc[0]),
            "rows_per_day_min": int(per_day.min()), "earliest_slot": tod.min(), "latest_slot": tod.max(),
            "duplicated_stamps": int(t.duplicated().sum()), "na_share_P": float(p.isna().mean()),
            "negative_P": int((p < 0).sum()), "P_p999_kW": float(p.quantile(0.999) / 1000.0),
            "P_max_kW": float(p.max() / 1000.0), "AC_kW": a,
            "p999_over_AC": float(p.quantile(0.999) / 1000.0 / a) if a == a else np.nan,
            "producing_on_first_day": bool((p_day1 > C.VALID_POWER_FRAC * a * 1000.0).any()) if a == a else None,
            "first_day_P_max_kW": float(p_day1.max() / 1000.0),
        })
        e = (p.clip(lower=0) * 5.0 / 60.0 / 1000.0).groupby(day).sum(min_count=1)
        valid = p.notna().groupby(day).mean()
        daily[stem] = e.where(valid >= 0.9)
    return pd.DataFrame(rows), pd.DataFrame(daily)


def inventory_sites(step: str, ac_station: pd.Series) -> tuple[pd.DataFrame, dict]:
    """One row per site file; also returns the parsed frames (15-min only, for the evening and Zone D checks)."""
    rows, frames = [], {}
    for stem, path in io.site_files(step).items():
        df, fmt = io.read_site(path)
        t = df["time"]
        p = df["P_W"]
        pos = p > 0
        first_power = t[pos].iloc[0] if pos.any() else pd.NaT
        day1 = t.dt.normalize().iloc[0]
        e_day1 = float(df.loc[t.dt.normalize() == day1, "E_kWh"].sum())
        rows.append({
            "file": stem, "step": step, "time_format": fmt, "rows": len(df), "first": t.iloc[0], "last": t.iloc[-1],
            "starts_on_1st": bool(t.iloc[0].day == 1), "first_power": first_power,
            "first_day_kWh": e_day1, "producing_on_first_day": bool(e_day1 > 0),
            "na_share_P": float(p.isna().mean()), "duplicated_stamps": int(t.duplicated().sum()),
            "earliest_slot": t.dt.strftime("%H:%M").min(), "latest_slot": t.dt.strftime("%H:%M").max(),
            "P_p999_kW": float(p.quantile(0.999) / 1000.0), "rated_kW_metadata": ac_station.get(stem, np.nan),
        })
        if step == "15min":
            frames[stem] = df
    return pd.DataFrame(rows), frames


def inventory_weather() -> pd.DataFrame:
    rows = []
    for var in io.WEATHER:
        df, formats = io.read_weather(var)
        t = df["time"]
        for year in (2021, 2022, 2023):
            m = t.dt.year == year
            expected = 366 * 1440 if year % 4 == 0 else 365 * 1440
            rows.append({"variable": var, "year": year, "time_format": formats[year], "rows": int(m.sum()),
                         "expected_rows": expected, "missing_rows": expected - int(m.sum()),
                         "na_values": int(df.loc[m, "value"].isna().sum()),
                         "duplicated_stamps": int(t[m].duplicated().sum()),
                         "min": float(df.loc[m, "value"].min()), "max": float(df.loc[m, "value"].max())})
    return pd.DataFrame(rows)


# --- Reproductions of the 18 Nov audit ----------------------------------------------------------
def evening_share(frames15: dict) -> tuple[pd.DataFrame, dict]:
    """Share of station energy after 18:00 (15-min site files), per station and month (months with >= 20 days)."""
    rows = []
    for stem, df in frames15.items():
        d = df.dropna(subset=["E_kWh"]).copy()
        d["month"] = d["time"].dt.to_period("M")
        d["evening"] = d["time"].dt.hour >= 18
        g = d.groupby("month")
        days = g["time"].apply(lambda s: s.dt.normalize().nunique())
        tot = g["E_kWh"].sum()
        eve = d[d["evening"]].groupby("month")["E_kWh"].sum().reindex(tot.index, fill_value=0.0)
        for m in tot.index:
            if days[m] >= 20 and tot[m] > 0:
                rows.append({"file": stem, "month": str(m), "cal_month": m.month, "share": eve[m] / tot[m]})
    es = pd.DataFrame(rows)
    by_cal = es.groupby("cal_month")["share"].median()
    return es, {"median_share_all_station_months": float(es["share"].median()),
                "max_calendar_month_median": float(by_cal.max()), "argmax_calendar_month": int(by_cal.idxmax()),
                "max_station_month": float(es["share"].max()), "n_station_months": int(len(es))}


def zone_d_ratio(frames15: dict) -> pd.DataFrame:
    """Daily energy of the Zone D station over 06:00-17:55 divided by Zone D inverter 2, monthly medians."""
    site = frames15["Zone D"].copy()
    tod = site["time"].dt.strftime("%H:%M")
    site = site[(tod >= C.INVERTER_FIRST_SLOT) & (tod <= C.INVERTER_LAST_SLOT)]
    e_site = site.groupby(site["time"].dt.normalize())["E_kWh"].sum(min_count=1)
    inv2, _ = io.read_inverter(io.inverter_files()["Zone D_Inverter_2"])
    inv1, _ = io.read_inverter(io.inverter_files()["Zone D_Inverter_1"])
    e2 = (inv2["P_W"].clip(lower=0) * 5 / 60 / 1000).groupby(inv2["time"].dt.normalize()).sum(min_count=1)
    e1 = (inv1["P_W"].clip(lower=0) * 5 / 60 / 1000).groupby(inv1["time"].dt.normalize()).sum(min_count=1)
    d = pd.DataFrame({"site_kWh": e_site, "inv2_kWh": e2, "inv1_kWh": e1}).dropna(subset=["site_kWh", "inv2_kWh"])
    d = d[d["inv2_kWh"] > 5]
    d["ratio_site_inv2"] = d["site_kWh"] / d["inv2_kWh"]
    d["month"] = d.index.to_period("M").astype(str)
    return d.groupby("month").agg(days=("ratio_site_inv2", "size"), median_ratio=("ratio_site_inv2", "median"),
                                  inv1_days=("inv1_kWh", lambda s: int(s.notna().sum()))).reset_index()


def start_table(inv: pd.DataFrame, st: pd.DataFrame, inv_inventory: pd.DataFrame,
                site15: pd.DataFrame) -> pd.DataFrame:
    """Per station with optimizers: connection date, first inverter row, site-file start, and the D08 start flag."""
    first_inv = inv_inventory.set_index("file")["first"]
    s15 = site15.set_index("file")
    rows = []
    for _, s in st.dropna(subset=["site_file_15min"]).iterrows():
        files = inv.loc[inv["station"] == s["station"], "file"].dropna().tolist()
        inv_first = min(first_inv[f] for f in files).normalize()
        site = s15.loc[s["site_file_15min"]]
        site_first_row = site["first"].normalize()
        site_first_power = site["first_power"].normalize()
        conn = pd.to_datetime(str(s["connection_date"])[:10])
        earliest = min(inv_first, site_first_power)
        source = "site" if site_first_power < inv_first else ("inverter" if inv_first < site_first_power else "both")
        # D08 rule: left-censored if the earliest file begins on the 1st of a month while already producing.
        if source == "site":
            censored = bool(site_first_row == site_first_power and site_first_row.day == 1)
        elif source == "inverter":
            censored = bool(inv_first.day == 1)  # every inverter file produces on its first day (F06)
        else:
            censored = bool(earliest.day == 1)
        rows.append({"station": s["station"], "site_file": s["site_file_15min"], "n_inverter_files": len(files),
                     "connection_date": conn.date(), "first_inverter_day": inv_first.date(),
                     "site_first_row": site_first_row.date(), "site_first_power_day": site_first_power.date(),
                     "earliest_production_day": earliest.date(), "earliest_source": source,
                     "left_censored_by_rule": censored,
                     "days_connection_to_earliest": int((earliest - conn).days),
                     "days_site_before_inverter": int((inv_first - site_first_power).days)})
    return pd.DataFrame(rows).sort_values("earliest_production_day").reset_index(drop=True)


# --- Sensor ---------------------------------------------------------------------------------------
def sensor_tables(daily_inv: pd.DataFrame, inv: pd.DataFrame, altitude_m: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily and monthly checks of the pyranometer against CAMS all-sky GHI, Ineichen clear sky and a fleet proxy."""
    import pvlib

    ghi, _ = io.read_weather("ghi")
    s = pd.Series(ghi["value"].to_numpy(), index=pd.DatetimeIndex(ghi["time"]).tz_localize(C.TZ)).tz_convert("UTC")
    s = s[~s.index.duplicated()]
    cams = io.read_cams(C.CAMS_HKUST)
    idx = cams.index
    df = pd.DataFrame({"sensor": s.reindex(idx), "cams_ghi": cams["GHI"], "cams_cs": cams["Clear sky GHI"],
                       "rel": cams["Reliability"]}, index=idx)
    loc = pvlib.location.Location(C.SITE_LAT, C.SITE_LON, tz=C.TZ, altitude=altitude_m)
    sp = loc.get_solarposition(idx)
    df["elev"] = sp["apparent_elevation"].to_numpy()
    df["ineichen"] = loc.get_clearsky(idx, model="ineichen", solar_position=sp)["ghi"].to_numpy()
    s0 = pvlib.irradiance.get_extra_radiation(idx).to_numpy()
    mu = np.clip(np.cos(np.radians(sp["apparent_zenith"].to_numpy())), 0, None)
    df["bsrn_upper"] = 1.2 * s0 * mu ** 1.2 + 50.0
    local = idx.tz_convert(C.TZ)
    df["day"] = local.tz_localize(None).normalize()
    df["hhmm"] = local.strftime("%H:%M")

    day = df["elev"] > 10
    ok = day & df["sensor"].notna() & (df["rel"] >= 1)
    g = df[ok].groupby("day")
    daily = pd.DataFrame({"sensor_Wh": g["sensor"].sum() / 60, "cams_Wh": g["cams_ghi"].sum() / 60,
                          "ineichen_Wh": g["ineichen"].sum() / 60, "minutes": g.size()})
    daily = daily[daily["minutes"] >= 300]
    daily["ratio_sensor_cams"] = daily["sensor_Wh"] / daily["cams_Wh"]
    # Fleet proxy: sensor irradiation over the inverter window divided by the median normalised yield.
    win = (df["hhmm"] >= C.INVERTER_FIRST_SLOT) & (df["hhmm"] <= "17:59") & df["sensor"].notna()
    sens_win = df[win].groupby("day")["sensor"].sum() / 60 / 1000          # kWh/m2
    cams_win = df[win & (df["rel"] >= 1)].groupby("day")["cams_ghi"].sum() / 60 / 1000
    ac = inv.set_index("file")["AC_kW"]
    lr = [u for u in LONG_RUNNING if u in daily_inv.columns]
    yields = daily_inv[lr].div(ac[lr], axis=1)                              # h
    fleet = yields.median(axis=1, skipna=True).where(yields.notna().sum(axis=1) >= 6)
    daily["fleet_yield_h"] = fleet.reindex(daily.index)
    daily["ratio_sensor_fleet"] = sens_win.reindex(daily.index) / daily["fleet_yield_h"]
    daily["ratio_cams_fleet"] = cams_win.reindex(daily.index) / daily["fleet_yield_h"]

    night = df["elev"] < -6
    df["month"] = df["day"].dt.to_period("M")
    noon = (df["hhmm"] >= "11:30") & (df["hhmm"] <= "13:00") & df["sensor"].notna() & (df["ineichen"] > 0)
    monthly = pd.DataFrame({
        "night_offset_median": df[night].groupby("month")["sensor"].median(),
        "noon_p95_sensor_over_ineichen": (df.loc[noon, "sensor"] / df.loc[noon, "ineichen"]).groupby(
            df.loc[noon, "month"]).quantile(0.95),
        "noon_p95_cams_over_ineichen": (df.loc[noon, "cams_ghi"] / df.loc[noon, "ineichen"]).groupby(
            df.loc[noon, "month"]).quantile(0.95),
        "spikes_above_bsrn": (df["sensor"] > df["bsrn_upper"]).groupby(df["month"]).sum(),
        "below_minus2": (df["sensor"] < -2).groupby(df["month"]).sum(),
        "sensor_max": df.groupby("month")["sensor"].max(),
    })
    monthly.index = monthly.index.astype(str)
    return daily, monthly


def change_points(series: pd.Series, min_size: int = 30) -> dict:
    """PELT (L2 cost) on a daily log-ratio. Penalty 2 sigma^2 log(n), sigma from the MAD of first differences."""
    import ruptures as rpt

    x = np.log(series.dropna())
    x = x[np.isfinite(x)]
    sigma = np.median(np.abs(np.diff(x.to_numpy()))) / (0.6745 * np.sqrt(2))
    pen = 2 * sigma ** 2 * np.log(len(x))
    bk = rpt.Pelt(model="l2", min_size=min_size).fit(x.to_numpy().reshape(-1, 1)).predict(pen=pen)
    dates = [x.index[b].date().isoformat() for b in bk[:-1]]
    edges = [0] + bk
    segs = [{"start": x.index[a].date().isoformat(), "end": x.index[b - 1].date().isoformat(),
             "median_ratio": float(np.exp(np.median(x.iloc[a:b])))} for a, b in zip(edges[:-1], edges[1:])]
    return {"n_days": int(len(x)), "sigma": float(sigma), "penalty": float(pen), "change_dates": dates,
            "segments": segs}


# --- Outputs --------------------------------------------------------------------------------------
def write_outputs(name: str, tables: dict[str, pd.DataFrame], summary: dict, figures: dict | None = None,
                  parquet: dict[str, pd.DataFrame] | None = None) -> Path:
    """Write every table, figure and summary.json to results/<name>/ all-or-nothing (temp folder, then rename)."""
    final = C.RESULTS / name
    tmp = C.RESULTS / f".tmp_{name}"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "figures").mkdir(parents=True)
    for key, df in tables.items():
        df.to_csv(tmp / f"{key}.csv", index=False)
    for key, df in (parquet or {}).items():
        df.astype({c: "float32" for c in df.columns if df[c].dtype == "float64"}).to_parquet(tmp / f"{key}.parquet")
    for key, fig in (figures or {}).items():
        fig.savefig(tmp / "figures" / f"{key}.png", dpi=150)
        fig.savefig(tmp / "figures" / f"{key}.pdf")
    (tmp / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    if final.exists():
        shutil.rmtree(final)
    tmp.rename(final)
    return final


def versions() -> dict:
    import importlib
    import platform
    import sys
    out = {"python": sys.version.split()[0], "platform": platform.platform(), "executable": sys.executable,
           "run_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    for m in ["numpy", "pandas", "scipy", "sklearn", "statsmodels", "lightgbm", "pvlib", "ruptures", "matplotlib",
              "torch", "openpyxl", "pyarrow", "yaml"]:
        try:
            out[m] = importlib.import_module(m).__version__
        except Exception as e:  # noqa: BLE001
            out[m] = f"not installed ({type(e).__name__})"
    return out


def dominant_change(series: pd.Series, min_size: int = 30) -> dict:
    """The single break that best splits a daily log-ratio (binary segmentation, one break), for the audit only.

    The final drift boundary is fixed in NB3 on the fleet index (D10); this gives the audit-level date.
    """
    import ruptures as rpt

    x = np.log(series.dropna())
    x = x[np.isfinite(x)]
    b = rpt.Binseg(model="l2", min_size=min_size).fit(x.to_numpy().reshape(-1, 1)).predict(n_bkps=1)[0]
    return {"date": x.index[b].date().isoformat(), "before": float(np.exp(np.median(x.iloc[:b]))),
            "after": float(np.exp(np.median(x.iloc[b:]))), "n_days": int(len(x))}


def metadata_check(ii: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    """AC rating from the model name vs the observed 99.9th percentile of 5-min power (guide §2: match within 2%)."""
    t = inv.dropna(subset=["file"]).merge(ii[["file", "P_p999_kW", "P_max_kW", "first"]], on="file")
    t["p999_over_AC"] = t["P_p999_kW"] / t["AC_kW"]
    t["within_2pct"] = (t["p999_over_AC"] - 1).abs() <= 0.02
    t["clips_at_AC"] = t["p999_over_AC"] >= 0.98
    return t.sort_values("p999_over_AC")


def _style():
    import matplotlib as mpl
    mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 7, "axes.labelsize": 7,
                         "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
                         "axes.spines.top": False, "axes.spines.right": False})


def fig_sensor(daily: pd.DataFrame, monthly: pd.DataFrame, change_date: str):
    """Draft of Fig. 2: the sensor against CAMS and against the fleet, and the noon clear-sky ratios."""
    import matplotlib.pyplot as plt
    _style()
    fig, ax = plt.subplots(3, 1, figsize=(7.2, 5.4), sharex=True)
    cd = pd.Timestamp(change_date)
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"))
    r = daily["ratio_sensor_cams"]
    ax[0].plot(r.index, r, ".", ms=1.5, color="0.6", label="daily")
    ax[0].plot(r.rolling("30D", center=True, min_periods=10).median(), color="#1f4e79", lw=1.2, label="30-day median")
    ax[0].set_ylabel("Sensor / CAMS\ndaily irradiation")
    ax[0].set_ylim(0, 2)
    for col, lab, c in [("ratio_sensor_fleet", "sensor / fleet", "#b03a2e"), ("ratio_cams_fleet", "CAMS / fleet", "#1f4e79")]:
        s = daily[col] / daily.loc[: "2022-12-31", col].median()
        ax[1].plot(s.rolling("30D", center=True, min_periods=10).median(), color=c, lw=1.2, label=lab)
    ax[1].set_ylabel("Ratio to fleet yield\n(2021-22 median = 1)")
    ax[1].legend(frameon=False, loc="upper left")
    mi = pd.PeriodIndex(monthly.index, freq="M").to_timestamp() + pd.Timedelta(days=14)
    ax[2].plot(mi, monthly["noon_p95_sensor_over_ineichen"], "o-", ms=2.5, color="#b03a2e", lw=1, label="sensor")
    ax[2].plot(mi, monthly["noon_p95_cams_over_ineichen"], "s-", ms=2.5, color="#1f4e79", lw=1, label="CAMS")
    ax[2].axhline(1, color="0.5", lw=0.6)
    ax[2].set_ylabel("Noon p95 of GHI /\nIneichen clear sky")
    ax[2].legend(frameon=False, loc="upper left")
    for a in ax:
        a.axvline(cd, color="0.2", ls="--", lw=0.8)
    ax[0].legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def fig_quirks(frames15: dict, zd: pd.DataFrame):
    """Raw traces: the 17:55 cut (Zone A5), Zone J2 producing before its inverter file, Zone D station vs inverter 2."""
    import matplotlib.pyplot as plt
    _style()
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.3))
    day = pd.Timestamp("2022-06-21")
    inv, _ = io.read_inverter(io.inverter_files()["Zone A5_Inverter"])
    a = inv[inv["time"].dt.normalize() == day]
    s = frames15["Zone A5"]
    s = s[s["time"].dt.normalize() == day]
    ax[0].plot(a["time"].dt.hour + a["time"].dt.minute / 60, a["P_W"] / 1000, color="#b03a2e", lw=0.9, label="inverter (5 min)")
    ax[0].plot(s["time"].dt.hour + s["time"].dt.minute / 60, s["P_W"] / 1000, color="#1f4e79", lw=0.9, label="site (15 min)")
    ax[0].axvline(18, color="0.4", ls="--", lw=0.7)
    ax[0].set_xlim(4, 21)
    ax[0].set_xlabel("Hour, 21 Jun 2022 (Zone A5)")
    ax[0].set_ylabel("Power (kW)")
    ax[0].legend(frameon=False, loc="upper right")
    j = frames15["Zone J2"]
    e = j.groupby(j["time"].dt.normalize())["E_kWh"].sum()
    e = e["2021-11-01":"2021-12-31"]
    ji, _ = io.read_inverter(io.inverter_files()["Zone J2_Inverter"])
    ei = (ji["P_W"].clip(lower=0) * 5 / 60 / 1000).groupby(ji["time"].dt.normalize()).sum()["2021-11-01":"2021-12-31"]
    ax[1].bar(e.index, e, width=0.8, color="#1f4e79", label="site file")
    ax[1].plot(ei.index, ei, "o", ms=2, color="#b03a2e", label="inverter file")
    ax[1].set_ylabel("Daily energy (kWh)")
    ax[1].set_xlabel("Zone J2, Nov-Dec 2021")
    ax[1].legend(frameon=False, loc="upper right")
    ax[1].tick_params(axis="x", rotation=45)
    m = pd.to_datetime(zd["month"])
    ax[2].plot(m, zd["median_ratio"], "o-", ms=2.5, lw=1, color="#1f4e79")
    ax[2].axvline(pd.Timestamp("2022-12-03"), color="#b03a2e", ls="--", lw=0.8)
    ax[2].set_ylabel("Station / inverter 2\n(daily energy, median)")
    ax[2].set_xlabel("Zone D, month")
    ax[2].tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig
