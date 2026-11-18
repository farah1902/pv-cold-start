"""Readers for the HKUST dataset and the CAMS files, and the parser of the Brick metadata.

Timestamps are kept as recorded (naive Hong Kong time) so that clock problems stay visible; they are localised only
where a computation needs UTC. Two timestamp formats occur (F02); both are parsed explicitly and any failure raises
(D13).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

FMT_ISO = "%Y-%m-%d %H:%M:%S"
FMT_YMD = "%Y/%m/%d %H:%M"


# --- Timestamps --------------------------------------------------------------------------------
def parse_time(values: pd.Series) -> tuple[pd.Series, str]:
    """Parse a column of timestamps written as 2021-05-07 07:00:00 or 2021/6/2 6:00. Raises on any failure.

    Returns the parsed series and the format label: 'iso', 'ymd' or 'mixed'.
    """
    s = values.astype(str).str.strip()
    iso = s.str.contains("-", regex=False).to_numpy()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if iso.any():
        out[iso] = pd.to_datetime(s[iso], format=FMT_ISO, errors="raise")
    if (~iso).any():
        out[~iso] = pd.to_datetime(s[~iso], format=FMT_YMD, errors="raise")
    if out.isna().any():
        raise ValueError(f"{int(out.isna().sum())} timestamps could not be parsed")
    label = "iso" if iso.all() else ("ymd" if (~iso).all() else "mixed")
    return out, label


# --- Files ------------------------------------------------------------------------------------
def inverter_files() -> dict[str, Path]:
    files = sorted(C.INV_DIR.glob("*.csv"))
    assert len(files) == 44, f"expected 44 inverter files, found {len(files)}"
    return {f.stem: f for f in files}


def site_files(step: str) -> dict[str, Path]:
    d = {"15min": C.SITE15_DIR, "1h": C.SITE1H_DIR}[step]
    files = sorted(d.glob("*.csv"))
    expected = {"15min": 37, "1h": 23}[step]
    assert len(files) == expected, f"expected {expected} {step} site files, found {len(files)}"
    return {f.stem: f for f in files}


def read_inverter(path: Path, full: bool = False) -> tuple[pd.DataFrame, str]:
    """Return (frame with time and P_W [and Vdc_V], timestamp format). full=True keeps every column."""
    usecols = None if full else ["Time", "dcVoltage(V)", "totalActivePower(W)"]
    df = pd.read_csv(path, usecols=usecols, na_values=["NA"])
    t, fmt = parse_time(df.pop("Time"))
    df = df.rename(columns={"totalActivePower(W)": "P_W", "dcVoltage(V)": "Vdc_V"})
    df.insert(0, "time", t.to_numpy())
    return df, fmt


def read_site(path: Path) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(path, na_values=["NA"])
    t, fmt = parse_time(df.pop("Time"))
    df = df.rename(columns={"generation(kWh)": "E_kWh", "power(W)": "P_W"})
    df.insert(0, "time", t.to_numpy())
    return df, fmt


WEATHER = {  # folder, file stem, value column
    "ghi": ("Irradiance", "Irradiance", "Irradiance (W/m2)"),
    "temp": ("Temperature", "Temperature", "Temp (Degree Celsius)"),
    "rh": ("Relative Humidity", "Relative Humidity", "RH (%)"),
    "slp": ("Sea Level Pressure", "Sea Level Pressure", "SLP (hPa)"),
    "vis": ("Visibility", "Visibility", "Vis (km)"),
    "wind": ("Wind", "Wind", "Wind Speed (m/s)"),
    "rain": ("Rainfall", "Rainfall", "Rainfall(mm)"),
}


def read_weather(var: str) -> tuple[pd.DataFrame, dict]:
    """1-min weather series for 2021-2023 as (frame with time and value, formats per year)."""
    folder, stem, col = WEATHER[var]
    frames, formats = [], {}
    for year in (2021, 2022, 2023):
        csv = C.MET_DIR / folder / f"{stem}_{year}.csv"
        xlsx = C.MET_DIR / folder / f"{stem}_{year}.xlsx"
        if csv.exists():
            df = pd.read_csv(csv, na_values=["NA"])
            t, fmt = parse_time(df["Time"])
        else:
            df = pd.read_excel(xlsx)
            t, fmt = pd.to_datetime(df["Time"], errors="raise"), "excel-datetime"
        frames.append(pd.DataFrame({"time": t.to_numpy(), "value": pd.to_numeric(df[col], errors="coerce")}))
        formats[year] = fmt
    return pd.concat(frames, ignore_index=True), formats


def read_cams(path: Path) -> pd.DataFrame:
    """CAMS radiation time series (all-sky or McClear) in W/m2, indexed by the UTC start of each 1-min step."""
    header = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# Observation period;"):
                header = line[2:].strip().split(";")
                break
    assert header, "CAMS header line not found"
    df = pd.read_csv(path, comment="#", sep=";", header=None, names=header)
    start = pd.to_datetime(df["Observation period"].str.slice(0, 19), format="%Y-%m-%dT%H:%M:%S", errors="raise")
    out = df.drop(columns=["Observation period"])
    for c in out.columns:
        if c != "Reliability":
            out[c] = out[c] * C.CAMS_WH_PER_STEP_TO_W
    out.index = pd.DatetimeIndex(start).tz_localize("UTC")
    return out


# --- Brick metadata ---------------------------------------------------------------------------
# AC rating from the inverter model name (D01). An explicit table, so that every value can be checked by eye.
AC_KW = {
    "SolarEdge SE17K": 17.0, "SolarEdge SE25K": 25.0, "SolarEdge SE50K": 50.0,
    "SolarEdge_SE8K": 8.0, "SolarEdge_SE10K": 10.0, "SolarEdge_SE12_5K": 12.5, "SolarEdge_SE17K": 17.0,
    "SolarEdge_SE25K": 25.0, "SolarEdge_SE27_6K": 27.6, "SolarEdge_SE33_3K": 33.3, "SolarEdge_SE50K": 50.0,
    "SolarEdge_SE50K_": 50.0, "SolarEdge_SE55K": 55.0, "SolarEdge_SE55K_": 55.0, "SolarEdge_SE66_6K": 66.6,
    "SolarEdge_SE82_8K_": 82.8,
    "Sunny_Tripower_STP5_0_3AV_40": 5.0, "Sunny_Tripower_STP_10_0": 10.0, "Sunny_Tripower_15000TL_30": 15.0,
    "Sunny_Tripower_20000TL_30": 20.0, "Sunny_Tripower_25000TL_30": 25.0, "Sunny_Tripower_25000TL_JP_30": 25.0,
    "Sunny_Tripower_Core1_STP_50_40_": 50.0,
}


def _clean(raw: str):
    v = raw.strip()
    v = re.sub(r"\^\^xsd:\w+$", "", v).strip().strip('"')
    try:
        return float(v)
    except ValueError:
        return v


def parse_ttl(path: Path = C.TTL_PATH) -> dict[str, dict]:
    """Parse the Brick .ttl into {name: {class, parts, props, units, lat, lon}}."""
    text = Path(path).read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(r"^pvsystem:\S+ a brick:\w+", text, re.M)]
    nodes = {}
    for i, s in enumerate(starts):
        block = text[s: starts[i + 1] if i + 1 < len(starts) else len(text)]
        block = block.split("\n\n")[0]
        name, cls = re.match(r"pvsystem:(\S+) a brick:(\w+)", block).groups()
        parts = []
        hp = re.search(r"brick:hasPart(.*?)(?: ;\n| \.\s*$)", block, re.S)
        if hp:
            parts = re.findall(r"pvsystem:([^\s,;]+)", hp.group(1))
        props, units = {}, {}
        for prop, unit, raw in re.findall(r"ext:(\w+) \[ (?:brick:hasUnit unit:(\w+) ;\s*)?brick:value ([^\]]*?) \]",
                                          block, re.S):
            props[prop] = _clean(raw)
            if unit:
                units[prop] = unit
        lat = re.search(r"brick:latitude ([\d.\-]+)", block)
        lon = re.search(r"brick:longitude ([\d.\-]+)", block)
        assert name not in nodes, f"duplicate node {name}"
        nodes[name] = {"class": cls, "parts": parts, "props": props, "units": units,
                       "lat": float(lat.group(1)) if lat else np.nan, "lon": float(lon.group(1)) if lon else np.nan}
    return nodes


# File names that differ from the metadata names by more than spaces and punctuation (checked by hand).
NAME_ALIASES = {"Indoor Sports Centre": "Indoor_Sport_Center"}


def norm(name: str) -> str:
    for file_name, ttl_name in NAME_ALIASES.items():
        name = name.replace(file_name, ttl_name)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _azimuth_pvlib(az_brick):
    """Brick azimuth is counterclockwise from north (east = -90); pvlib is clockwise (east = 90) (F15).

    Returns one value for a single direction, a list for slash notation, or the string itself ('Mixed').
    """
    if not isinstance(az_brick, str):
        return az_brick
    if az_brick == "Mixed":
        return "Mixed"
    vals = [float(v) for v in az_brick.replace("deg", "").split("/")]
    conv = [(360.0 - v) % 360.0 for v in vals]
    return conv[0] if len(conv) == 1 else conv


def unit_tables(nodes: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (inverter table, station table) from the metadata, with AC from the model name and DC from modules."""
    nodes = nodes or parse_ttl()
    models = {n["props"].get("module") for n in nodes.values() if n["class"] == "Inverter"} - {None}
    missing = models - set(AC_KW)
    assert not missing, f"inverter models without an AC rating in AC_KW: {missing}"
    # Six SMA inverters of the hourly track have no model name (F21): their AC rating stays NaN here and the station
    # rating is used for them.
    inv_rows, st_rows = [], []
    for sname, st in nodes.items():
        if st["class"] != "PV_Generation_System":
            continue
        p = st["props"]
        st_rows.append({"station": sname, "rated_kW_metadata": p.get("ratedPowerOutput"),
                        "rated_unit": st["units"].get("ratedPowerOutput"), "connection_date": p.get("connectionDate"),
                        "contractor": p.get("contractor"), "altitude_m": p.get("altitude"),
                        "tilt": p.get("tiltAngle"), "azimuth_brick": p.get("azimuth"),
                        "azimuth_pvlib": _azimuth_pvlib(p.get("azimuth")), "lat": st["lat"], "lon": st["lon"],
                        "n_inverters": len(st["parts"])})
        for iname in st["parts"]:
            inv = nodes[iname]
            mods = [nodes[m] for m in inv["parts"]]
            dc_w = sum(m["props"]["number"] * m["props"]["ratedPowerOutput"] for m in mods)
            model = inv["props"].get("module")
            ac = AC_KW[model] * inv["props"].get("number", 1) if model else np.nan
            inv_rows.append({"station": sname, "inverter": iname, "inverter_model": model,
                             "inverter_brand": inv["props"].get("brand"), "inverter_count": inv["props"].get("number"),
                             "AC_kW": ac,
                             "module_models": "+".join(m["props"]["module"] for m in mods),
                             "module_types": "+".join(str(m["props"].get("specificType")) for m in mods),
                             "n_modules": sum(m["props"]["number"] for m in mods),
                             "DC_kWp": dc_w / 1000.0, "n_module_blocks": len(mods)})
    inv = pd.DataFrame(inv_rows)
    inv["DC_AC"] = inv["DC_kWp"] / inv["AC_kW"]
    return inv, pd.DataFrame(st_rows)


def match_names(file_stems, ttl_names) -> dict[str, str]:
    """Map file stems to metadata names by normalised name; every file must match exactly one name."""
    by_norm = {}
    for n in ttl_names:
        by_norm.setdefault(norm(n), []).append(n)
    out, bad = {}, []
    for stem in file_stems:
        hits = by_norm.get(norm(stem), [])
        if len(hits) == 1:
            out[stem] = hits[0]
        else:
            bad.append((stem, hits))
    if bad:
        raise KeyError(f"unmatched or ambiguous names: {bad}")
    return out
