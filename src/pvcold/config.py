"""Paths, constants and settings shared by every notebook.

Every number here comes from docs/research_guide.md or docs/decisions.md (the D-number is given). Values that are
tuned later are NOT here: they are fixed on the validation units and written to the frozen configuration (D21).
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -------------------------------------------------------------------------------------
# The repository root is two levels above this file (src/pvcold/config.py). On Colab, set PVCOLD_ROOT to the Drive
# mirror of the repository (for example /content/drive/MyDrive/pv-cold-start).
ROOT = Path(os.environ.get("PVCOLD_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
RAW_HKUST = DATA / "raw" / "hkust" / "Dataset"
TS_DIR = RAW_HKUST / "Time series dataset"
PV_DIR = TS_DIR / "PV generation dataset"
INV_DIR = PV_DIR / "PV stations with panel level optimizer" / "Inverter level dataset"
SITE15_DIR = PV_DIR / "PV stations with panel level optimizer" / "Site level dataset"
SITE1H_DIR = PV_DIR / "PV stations without panel level optimizer" / "Site level dataset"
MET_DIR = TS_DIR / "Meteorological dataset"
TTL_PATH = RAW_HKUST / "Metadata" / "PV generation system metadata.ttl"
CAMS_HKUST = DATA / "external" / "cams" / "observed" / "cams-HKUST-21-23.csv"
CAMS_SAFI = DATA / "external" / "cams" / "observed" / "cams-safi-16-18.csv"
MCCLEAR_HKUST = DATA / "external" / "cams" / "mcclear" / "HKUSTcsv.csv"
RESULTS = ROOT / "results"

# --- Site and time (guide §2, F10) ----------------------------------------------------------------
SITE_LAT = 22.3363
SITE_LON = 114.2634
TZ = "Asia/Hong_Kong"          # UTC+8, no daylight saving in 2021-2023
CAMS_WH_PER_STEP_TO_W = 60.0   # CAMS gives Wh/m2 per 1-min step (F08, F17)

# --- Daily window of the inverter files (F01, D12) ------------------------------------------------
INVERTER_FIRST_SLOT = "06:00"
INVERTER_LAST_SLOT = "17:55"
COMMON_TARGET_WINDOW = ("12:00", "17:55")

# --- Units, starts and events (guide §2, D01, D08) ------------------------------------------------
VALID_POWER_FRAC = 0.02        # valid power: P > 2% of P_AC
START_DAYLIGHT_SHARE = 0.70    # first day d with valid power in >= 70% of daylight slots on d and d+1
DONOR_MIN_FULL_DAYS = 14       # a donor started at least 14 full days before the event
MIN_DONORS = 8
MIN_VALID_DAYS_IN_90 = 30
CONNECTION_GAP_FLAG_DAYS = 30
DRIFT_PROVISIONAL_BOUNDARY = "2022-11-01"   # replaced by the PELT boundary (D10)

VALIDATION_UNITS = [  # guide §2: the 10 units started 2 June - 15 July 2021 (F07)
    "SQ567_Inverter", "UG Hall2 2F_Inverter", "UG Hall2 RF_Inverter", "Zone A1_Inverter", "Zone A4_Inverter",
    "Zone A2_Inverter_1", "SQ Apartment1-12_Inverter", "SQ Apartment13-24_Inverter",
    "SQ Apartment25-36_Inverter", "SQ Apartment37-48_Inverter",
]
SCORED_EVENTS = [  # D08, D27: (event name, observed start); 13 events
    ("SQ Block S", "2021-10-05"), ("Zone A5", "2021-10-05"), ("SQ Block R", "2021-10-06"),
    ("Zone A7", "2021-10-09"), ("Zone A6", "2021-10-14"), ("Zone J2", "2021-11-13"),
    ("Indoor Sports Centre", "2021-11-17"), ("Zone D", "2022-01-19"),
    ("UG Hall8", "2023-01-05"), ("UG Hall9", "2023-02-11"), ("Zone A2 inverters 2-3", "2023-05-16"),
    ("SQ Block P", "2023-06-22"), ("Shaw Auditorium", "2023-07-09"),
]
SENSITIVITY_EVENTS = [  # D08, D27: left-censored starts
    ("Library", "2022-06-01"), ("Wong Check She Research Centre", "2021-12-01"), ("Zone J1", "2022-03-01"),
    ("Zone L2", "2022-06-01"),
]
REMOVED_EVENTS = ["Zone D inverter 1", "S H Ho Sports Hall"]
FIRST_TEST_DAY = "2021-10-05"  # development data end the day before (D25, rule R1)

# --- Preprocessing and model constants (guide §2-§3) ---------------------------------------------
CLIP_THRESHOLD = 0.97          # y >= 0.97 is censored
OVER_LIMIT = 1.05              # y > 1.05 is flagged
FROZEN_MINUTES = 60            # constant power for >= 1 h in daylight is flagged
OUTAGE_INDEX = 0.30            # zero power while the fleet index > 0.3 is an outage
HUBER_DELTA = 0.05
K_BOUNDS = (0.0, 1.5)
GAIN_BOUNDS = (0.3, 1.5)
GAIN_FIT_MIN_GTILDE = 0.2
GAIN_FIT_MIN_K = 0.5
ISSUE_MIN_GTILDE = 0.05
ISSUE_MIN_DONORS = 8
SCORE_MIN_GTILDE = 0.02
HORIZONS = [1, 2, 4, 8, 16, 24]     # 15-min steps: 15 min to 6 h
PRIMARY_HORIZON = 4                 # 1 h (D09)
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
N_LAGS = 16
N_MEMBERS = 200

# --- Reproducibility ------------------------------------------------------------------------------
SEED = 20261118
