"""NB6 scoring and statistics (guide §3.9, §4.4), read from the frozen configuration (D21, D77, D78).

    python tools/nb6_score.py --set validation   # the check on development data: must reproduce the known numbers
    python tools/nb6_score.py --set test         # once, after the test forecasts' hashes are committed

Both modes run the same code (src/pvcold/evaluate.py) on the same frozen rules:
- score table: every row on NB5a's slots, per event and horizon (forecast.scores), raw and, for the main model and
  LightGBM, conformal intervals (part 2b); A3 is the main model's forecasts with prior G0; the weighted pairs are
  built from the 5-seed ensembles with the frozen weights (part 2e);
- primary test (frozen 'statistics.primary'): main vs A1 at 1 h, one-sided exact Wilcoxon on the event-wise nRMSE
  differences, p < 0.05; the other five horizons secondary, with Holm; Hodges–Lehmann effect size and its exact 95%
  interval; events won;
- secondary family (frozen 'statistics.secondary_family'): eight two-sided exact Wilcoxon tests at 1 h, Holm across
  the family, Hodges–Lehmann, and §4.4's wording classes (ratio of medians against the 3% line);
- comparisons of §4.4 outside the family, reported by effect size: main vs CLIPER, A4, A4b and A9, on the slots each
  pair shares, overall and by sensor period; in the drifted window a day-block bootstrap interval of the
  Hodges–Lehmann difference;
- Diebold–Mariano per event at 1 h (squared loss, Newey–West lag h - 1, HLN correction) for main vs A1, CLIPER, A4
  and A4b, with Holm across the drifted events for A4 and A4b;
- bootstraps (B = 2,000): day-block and 3-day moving-block intervals of each event's nRMSE and skill (vs A1 and
  CLIPER), and the hierarchical (events, then days) interval of the median skill.

Validation mode pairs over the 10 validation units (n = 10, not 13), so its p-values are not the test's. It asserts
that every score it rebuilds equals the stored development scores, that the statistics functions agree with
independent implementations, and that the known validation comparisons come out unchanged (results_summary.md).
Writes results/nb6_validation/ (all-or-nothing). Test mode refuses to run before the forecast manifest is committed,
and refuses to overwrite results/nb6_test/ (the test is scored once).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import audit as A  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import evaluate as EV  # noqa: E402
from pvcold import forecast as FC  # noqa: E402

QC = EV.QC
H1 = C.PRIMARY_HORIZON
VD = C.RESULTS / "nb5c_variants"
NB5A_MODELS = ["LGB", "A0", "A1", "PeEn", "CLIPER", "A5", "A7"]
SOURCE_ROWS = {"A4": ("sensor_raw", "LGB"), "A4b": ("sensor_corr", "LGB"), "A9": ("cams", "A1"), "A9n": ("cams", "A7")}
WEIGHTED = {"weighted PVSetFormer + Chronos-2": ("main", "PVSetFormer"), "weighted TimeXer + Chronos-2": ("A6d", "TimeXer"),
            "weighted LightGBM + Chronos-2": ("LGB", "LightGBM")}
DESCRIPTIVE = ["CLIPER", "A4", "A4b", "A9"]                 # guide §4.4 comparisons outside the family
DM_REFS = ["A1", "CLIPER", "A4", "A4b"]
SKILL_REFS = ["A1", "CLIPER"]
# Reproduction tolerance where the development scorer worked on float64 forecasts in memory and wrote them at
# float32 (LGB_seeds, NB5a, NB5d): the stored file cannot give back its scores closer than float32 rounding.
# PVSetFormer, TimeXer and the foundation models are float32 throughout and must match to 1e-12.
F64_SCORED = 1e-08


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def py(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    return v


# --- Sources --------------------------------------------------------------------------------------------------------
def validation_sources(fz: dict) -> dict:
    """The stored development forecasts of each frozen row (index quantiles; seeds as frozen where frozen)."""
    tr = fz["test_rows"]
    seeds = tr["main"]["seeds"]
    rd = lambda p: pd.read_parquet(p)                                           # noqa: E731
    out = {"main": EV.ensemble(rd(VD / "V12_5s" / "forecasts.parquet"), seeds),
           "LGB": EV.ensemble(rd(VD / "LGB_seeds" / "forecasts.parquet"), tr["LGB"]["seeds"]),
           "A6d": EV.ensemble(rd(VD / "TX1_5s" / "forecasts.parquet"), tr["A6d"]["seeds"]),
           "A6e": EV.ensemble(rd(VD / "A6e_V12_5s" / "forecasts.parquet"), tr["A6e"]["seeds"]),
           "A6a": EV.ensemble(rd(C.RESULTS / "nb5b_runs" / f"{tr['A6a']['setting']}.parquet")),
           "A6b": EV.ensemble(rd(C.RESULTS / "nb5b_runs" / f"{tr['A6b']['setting']}.parquet"))}
    v12 = rd(VD / "V12_5s" / "forecasts.parquet")
    a4c = rd(VD / "A4c_V12" / "forecasts.parquet")
    s0 = tr["A4c"]["seeds"][0]
    out["A4c_check"] = EV.ensemble(a4c[a4c.seed == s0], [s0])                   # 1-seed validation check (D78)
    out["main_seed1"] = EV.ensemble(v12[v12.seed == s0], [s0])
    fc5 = rd(C.RESULTS / "nb5a_dev" / "val_forecasts.parquet")
    fc5["origin"], fc5["t"] = pd.to_datetime(fc5["origin"]), pd.to_datetime(fc5["t"])
    for m in NB5A_MODELS:
        out[m if m != "LGB" else "LGB_1seed"] = fc5[fc5.model == m].drop(columns="model").reset_index(drop=True)
    fx = rd(C.RESULTS / "nb5d_sources" / "forecasts.parquet")
    fx["origin"], fx["t"] = pd.to_datetime(fx["origin"]), pd.to_datetime(fx["t"])
    for r, (src, m) in SOURCE_ROWS.items():
        out[r] = fx[(fx.source == src) & (fx.model == m)].drop(columns=["source", "model"]).reset_index(drop=True)
    cal = {"main": EV.ensemble(rd(VD / "V12_5s" / "calibration.parquet"), seeds),
           "LGB": EV.ensemble(rd(VD / "LGB_seeds_cal" / "calibration.parquet"), tr["LGB"]["seeds"])}
    return {"rows": out, "cal": cal, "ref": fc5}


def test_sources(fz: dict) -> dict:
    """The test forecasts listed in results/nb6_forecasts/manifest.json, each checked against its committed hash."""
    man_p = C.RESULTS / "nb6_forecasts" / "manifest.json"
    assert man_p.exists(), "no test forecast manifest: generate the test forecasts first"
    rel = man_p.relative_to(ROOT).as_posix()
    assert git("ls-files", rel) == rel and git("status", "--porcelain", "--", rel) == "", "manifest not committed"
    git("merge-base", "--is-ancestor", "protocol-freeze", "HEAD")
    man = json.loads(man_p.read_text())
    assert man["frozen_config_sha256"] == EV.load_frozen()[1], "the manifest was built on another frozen configuration"
    files = {}
    for name, f in man["files"].items():
        p = ROOT / f["path"]
        assert EV.sha256(p) == f["sha256"], f"{name}: forecast file differs from the committed manifest"
        files[name] = pd.read_parquet(p)
    tr = fz["test_rows"]
    out = {r: EV.ensemble(files[r], tr[r]["seeds"]) for r in ("main", "LGB", "A2", "A4c", "A6d", "A6e")}
    out["A6a"], out["A6b"] = EV.ensemble(files["A6a"]), EV.ensemble(files["A6b"])
    ref = files["nb5a"]
    ref["origin"], ref["t"] = pd.to_datetime(ref["origin"]), pd.to_datetime(ref["t"])
    for m in NB5A_MODELS:
        out[m if m != "LGB" else "LGB_1seed"] = ref[ref.model == m].drop(columns="model").reset_index(drop=True)
    fx = files["sources"]
    fx["origin"], fx["t"] = pd.to_datetime(fx["origin"]), pd.to_datetime(fx["t"])
    for r, (src, m) in SOURCE_ROWS.items():
        out[r] = fx[(fx.source == src) & (fx.model == m)].drop(columns=["source", "model"]).reset_index(drop=True)
    cal = {"main": EV.ensemble(files["main_cal"], tr["main"]["seeds"]), "LGB": EV.ensemble(files["LGB_cal"], tr["LGB"]["seeds"])}
    return {"rows": out, "cal": cal, "ref": ref, "manifest_sha256": EV.sha256(man_p)}


# --- Scoring --------------------------------------------------------------------------------------------------------
def score_all(src: dict, events: list, fz: dict, ctx: EV.Context, gx: pd.DataFrame) -> tuple:
    rows = src["rows"]
    keys = {v: EV.slot_keys(src["ref"], v, ctx) for v in events}
    tr = fz["test_rows"]
    wts = tr["weighting_check"]["weights"]
    for name, (member, wkey) in WEIGHTED.items():
        rows[name] = EV.weighted_pair(rows[member], rows["A6a"], wts[wkey])
    SC, SL = [], []
    full_rows = [r for r in rows if r not in SOURCE_ROWS]
    for r in full_rows:
        sc, sl = EV.score_row(rows[r], r, keys, ctx)
        SC.append(sc), SL.append(sl)
        print(f"  scored {r}", flush=True)
    sc, sl = EV.score_row(rows["main"], "A3", keys, ctx, gain=lambda v: ctx.event_gain(v, force_g0=True)["g_m"])
    SC.append(sc), SL.append(sl)
    for r, (s, _) in SOURCE_ROWS.items():
        gsrc = lambda v, s=s: ctx.source_gain(v, gx[(gx.event == v) & (gx.source == s)].set_index("donor")["gain"])  # noqa: E731
        sc, sl = EV.score_row(rows[r], r, keys, ctx, gain=gsrc, full=False)
        SC.append(sc), SL.append(sl)
    print("  scored A3 and the source rows", flush=True)
    CF = pd.concat([EV.conformal_scores(rows[r], src["cal"][r], r, keys, ctx) for r in ("main", "LGB")], ignore_index=True)
    SL = pd.concat(SL, ignore_index=True)
    for c in ("event", "row"):                    # categorical: the many row filters of the statistics stay fast
        SL[c] = SL[c].astype("category")
    return pd.concat(SC, ignore_index=True), SL, CF, keys


# --- Statistics -----------------------------------------------------------------------------------------------------
def table(SC: pd.DataFrame, row: str, ref: str, h: int, events: list) -> pd.DataFrame:
    a = SC[(SC.row == row) & (SC.h == h)].set_index("event").loc[events]
    b = SC[(SC.row == ref) & (SC.h == h)].set_index("event").loc[events]
    assert (a["n"] == b["n"]).all(), f"{row} vs {ref}: different slots"
    return pd.DataFrame({"row": a["nRMSE"], "ref": b["nRMSE"]})


def compare(x: pd.DataFrame, alternative: str) -> dict:
    d = (x["row"] - x["ref"]).to_numpy()
    return {"n": len(d), "median_row": float(x["row"].median()), "median_ref": float(x["ref"].median()),
            "diff_pct": 100 * float(x["row"].median() / x["ref"].median() - 1), "events_row_lower": int((d < 0).sum()),
            "p": EV.wilcoxon_p(d, alternative), **EV.hodges_lehmann(d)}


def primary(SC, events, fz) -> pd.DataFrame:
    row, ref = fz["statistics"]["primary"]["comparison"]
    out = [{"h": h, "comparison": f"{row} vs {ref}", **compare(table(SC, row, ref, h, events), "less")} for h in FC.H]
    P = pd.DataFrame(out)
    other = P.h != H1
    P["p_holm_other_horizons"] = np.nan
    P.loc[other, "p_holm_other_horizons"] = EV.holm(P.loc[other, "p"])
    P["primary"] = P.h == H1
    P["significant"] = np.where(P.primary, P.p < EV.ALPHA, P.p_holm_other_horizons < EV.ALPHA)
    return P


def secondary(SC, events, fz) -> pd.DataFrame:
    fam = fz["statistics"]["secondary_family"]
    out = []
    for row, ref in fam["comparisons"]:
        out.append({"row": row, "ref": ref, **compare(table(SC, row, ref, H1, events), "two-sided")})
    S = pd.DataFrame(out)
    S["p_holm"] = EV.holm(S["p"])
    w = [EV.wording(r.diff_pct, r.p_holm, r.hl, r.row, r.ref, fam["wording"]) for r in S.itertuples()]
    S["wording"] = [x["class"] for x in w]
    S["lower"] = [x["lower"] for x in w]
    S["sign_conflict"] = [x["sign_conflict"] for x in w]
    return S


def descriptive(SL, events, periods) -> pd.DataFrame:
    out = []
    for ref in DESCRIPTIVE:
        for h in FC.H:
            pr = EV.paired(SL, "main", ref, h)
            pr = pr.loc[[e for e in events if e in pr.index]]
            for per in ["all", "stable", "drifted"]:
                ev = [e for e in pr.index if per == "all" or periods.get(e) == per]
                if len(ev) < 2:
                    continue
                x = pr.loc[ev].rename(columns={"nRMSE_row": "row", "nRMSE_ref": "ref"})
                d = (x["row"] - x["ref"]).to_numpy()
                out.append({"comparison": f"main vs {ref}", "h": h, "period": per, "n": len(ev),
                            "median_main": float(x["row"].median()), "median_ref": float(x["ref"].median()),
                            "diff_pct": 100 * float(x["row"].median() / x["ref"].median() - 1),
                            "events_main_lower": int((d < 0).sum()), "p_two_sided": EV.wilcoxon_p(d, "two-sided"),
                            **EV.hodges_lehmann(d)})
    return pd.DataFrame(out)


def dm_table(SL, events, periods) -> pd.DataFrame:
    out = []
    for ref in DM_REFS:
        for v in events:
            a, b = EV.pair_slots(SL, "main", ref, v, H1)
            if len(a) < 10:
                continue
            out.append({"comparison": f"main vs {ref}", "event": v, "period": periods.get(v),
                        **EV.dm_hln((a["y"] - a["mean"]).to_numpy(), (b["y"] - b["mean"]).to_numpy(), H1)})
    D = pd.DataFrame(out)
    D["p_holm_drifted"] = np.nan
    for ref in ("A4", "A4b"):
        m = (D.comparison == f"main vs {ref}") & (D.period == "drifted")
        if m.any():
            D.loc[m, "p_holm_drifted"] = EV.holm(D.loc[m, "p"])
    return D


def bootstraps(SL, events, periods) -> tuple[pd.DataFrame, pd.DataFrame]:
    ev_rows, camp = [], []
    for ref in SKILL_REFS:
        for h in FC.H:
            sums = {v: EV.day_sums(SL, "main", ref, v, h) for v in events}
            for v in events:
                for block in (1, EV.BLOCK_DAYS):
                    r = EV.day_bootstrap(sums[v], EV.B_BOOT, EV.rng_for(f"day {ref} {h} {v} {block}"), block)
                    ev_rows.append({"ref": ref, "h": h, "event": v, "block_days": block, **r})
            camp.append({"ref": ref, "h": h, "period": "all",
                         **EV.hierarchical_bootstrap(sums, EV.B_BOOT, EV.rng_for(f"hier {ref} {h}"))})
    for ref in ("A4", "A4b"):        # by sensor period (guide §4.4: the drifted window by effect size only)
        for per in ("stable", "drifted"):
            evs = [v for v in events if periods.get(v) == per]
            if len(evs) < 2:
                continue
            sums = {v: EV.day_sums(SL, "main", ref, v, H1) for v in evs}
            d = np.array([np.sqrt(s.sa.sum() / s.n.sum()) - np.sqrt(s.sb.sum() / s.n.sum()) for s in sums.values()])
            camp.append({"ref": ref, "h": H1, "period": per, "events": len(evs), "events_main_lower": int((d < 0).sum()),
                         **EV.hodges_lehmann(d), **EV.hl_day_bootstrap(sums, EV.B_BOOT, EV.rng_for(f"hl {per} {ref}"))})
    return pd.DataFrame(ev_rows), pd.DataFrame(camp)


# --- Checks of the validation mode ---------------------------------------------------------------------------------
def close(a, b, tol, label, checks):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert a.shape == b.shape, f"{label}: shapes {a.shape} {b.shape}"
    err = float(np.nanmax(np.abs(a - b))) if a.size else 0.0
    ok = bool(err <= tol and np.array_equal(np.isnan(a), np.isnan(b)))
    checks.append({"check": label, "max_abs_diff": err, "tolerance": tol, "passed": ok})
    assert ok, f"{label}: max |diff| {err:.3e} > {tol:.0e}"


def check_statistics(checks):
    """The statistics functions against independent implementations."""
    from scipy import stats
    from statsmodels.stats.multitest import multipletests
    import statsmodels.api as sm
    rng = np.random.default_rng(1)
    for n in (10, 13):
        for _ in range(20):
            d = rng.normal(0.002, 0.01, n)
            T = float(np.sum(stats.rankdata(np.abs(d))[d > 0]))
            pmf = EV.signed_rank_null(n)
            p_dp = float(pmf[: int(round(T)) + 1].sum())
            close(p_dp, EV.wilcoxon_p(d, "less"), 1e-12, f"signed-rank null vs scipy, n {n}", checks)
            i, j = np.triu_indices(n)
            close(np.median((d[i] + d[j]) / 2), EV.hodges_lehmann(d)["hl"], 1e-15, f"HL vs Walsh averages, n {n}", checks)
    cdf = np.cumsum(EV.signed_rank_null(13))
    checks.append({"check": "n 13: P(T+ <= 17) <= 0.025 < P(T+ <= 18) (table critical value 17)",
                   "max_abs_diff": float(cdf[17]), "tolerance": 0.025, "passed": bool(cdf[17] <= 0.025 < cdf[18])})
    assert checks[-1]["passed"]
    p = rng.uniform(0, 0.2, 8)
    close(EV.holm(p), multipletests(p, method="holm")[1], 1e-15, "Holm vs statsmodels", checks)
    e1, e2 = rng.normal(0, 0.1, 500), rng.normal(0, 0.1, 500)
    e1 = np.convolve(e1, np.ones(4) / 2, mode="same")
    d = e1 ** 2 - e2 ** 2
    fit = sm.OLS(d, np.ones_like(d)).fit(cov_type="HAC", cov_kwds={"maxlags": H1 - 1, "use_correction": False})
    r = EV.dm_hln(e1, e2, H1)
    close(r["dm"], d.mean() / fit.bse[0], 1e-10, "DM Newey-West vs statsmodels HAC (lag h - 1)", checks)


def check_reproduction(SC, CF, src, ctx, keys, checks):
    """Every rebuilt score equals the stored development score; the observation equals NB5a's unit series."""
    for v in keys:                              # validation units only: the two representations of the observation
        u = ctx.E.loc[v, "units"]
        a, b = ctx.targets_kW[v] / float(ctx.E.loc[v, "AC_kW"]), ctx.p["y15"][u]
        close(a.reindex(b.index).to_numpy(), b.to_numpy(), 1e-6, f"observation {v}: event target / AC = y15 (float32)",
              checks)
        assert ctx.y_series(v) is ctx.p["y15"][u] or ctx.y_series(v).equals(b), f"{v}: not scored on NB5a's series"
    M = ["nRMSE", "CRPS", "PICP80"]

    def against(row, path, seed, label, extra=None, tol=1e-12):
        s = pd.read_csv(path)
        if seed is not None:
            s = s[s.seed == seed]
        if extra:
            for k, val in extra.items():
                s = s[s[k] == val]
        s = s.set_index(["event", "h"]).sort_index()
        mine = SC[SC.row == row].set_index(["event", "h"]).sort_index()
        assert mine.index.equals(s.index), f"{label}: different events or horizons"
        close(mine["n"], s["n"], 0, f"{label}: slots", checks)
        close(mine[M], s[M], tol, f"{label}: nRMSE, CRPS, PICP80", checks)

    against("main", VD / "V12_5s" / "scores.csv", 0, "main = V12_5s ensemble")
    against("LGB", VD / "LGB_seeds" / "scores.csv", 0, "LGB = LGB_seeds ensemble (scored before the float32 write)",
            tol=F64_SCORED)
    against("A6d", VD / "TX1_5s" / "scores.csv", 0, "A6d = TX1_5s ensemble")
    against("A6e", VD / "A6e_V12_5s" / "scores.csv", 0, "A6e = A6e_V12_5s ensemble")
    s0 = 20261119
    against("A4c_check", VD / "A4c_V12" / "scores.csv", s0, "A4c_V12 at seed 20261119")
    against("main_seed1", VD / "V12_5s" / "scores.csv", s0, "V12_5s at seed 20261119")
    fz = EV.load_frozen()[0]["test_rows"]
    for r in ("A6a", "A6b"):
        against(r, C.RESULTS / "nb5b_fm" / "scores.csv", None, f"{r} = {fz[r]['setting']}", {"setting": fz[r]["setting"]})
    for m in NB5A_MODELS:
        r = m if m != "LGB" else "LGB_1seed"
        against(r, C.RESULTS / "nb5a_dev" / "val_scores.csv", None, f"{m} = NB5a (scored before the float32 write)",
                {"model": m, "window": "full"}, tol=F64_SCORED)
    wts = fz["weighting_check"]["weights"]
    ws = pd.read_csv(C.RESULTS / "nb5c_weights" / "scores.csv")
    for name, (_, pair) in WEIGHTED.items():
        s = pd.concat([ws[(ws.pair == pair) & (ws.h == int(h)) & np.isclose(ws.w, w)] for h, w in wts[pair].items()])
        s = s.set_index(["event", "h"]).sort_index()
        mine = SC[SC.row == name].set_index(["event", "h"]).sort_index()
        close(mine[M], s[M], 1e-12, f"{name} = part 2e scores at the frozen weights", checks)
    nd = pd.read_csv(C.RESULTS / "nb5d_sources" / "scores.csv").set_index(["row", "event", "h"]).sort_index()
    for r in SOURCE_ROWS:
        mine = SC[SC.row == r].set_index(["event", "h"]).sort_index()
        ref = nd.loc[r].sort_index()
        close(mine["n"], ref["n_row"], 0, f"{r}: slots = NB5d", checks)
        close(mine[M], ref[[f"{k}_row" for k in M]], F64_SCORED, f"{r} = NB5d (scored before the float32 write)", checks)
    for r, folder in (("main", "nb5c_conformal"), ("LGB", "nb5c_conformal_lgb")):
        s = pd.read_csv(C.RESULTS / folder / "val_conformal_scores.csv").query("window == 'full'")
        s = s.set_index(["event", "h", "kind"]).sort_index()
        mine = CF[CF.row == r].set_index(["event", "h", "kind"]).sort_index()
        cols = ["cover80", "cover60", "cover40", "cover20", "PINAW", "IS80", "CRPS_q"]
        close(mine[cols], s[cols], 1e-12, f"{r}: raw and conformal intervals = {folder}", checks)


def check_known(P, S, SC, checks):
    """Known validation comparisons (results_summary.md) from their own result files."""
    r1 = json.loads((C.RESULTS / "nb5c_r1" / "summary.json").read_text())
    lg = S[(S.row == "LGB") & (S.ref == "main")].iloc[0]
    close(lg.median_ref, r1["R1_pvsf_ensemble"], 1e-12, "R1 at the freeze: V12_5s at 1 h (D74)", checks)
    close(lg.median_row, r1["R1_lgb_ensemble"], F64_SCORED, "R1 at the freeze: LGB_seeds at 1 h (D74)", checks)
    close(lg.p, r1["wilcoxon_p_1h"], 1e-12, "R1 at the freeze: Wilcoxon p (D74)", checks)
    close(10 - lg.events_row_lower, r1["units_won_1h"], 0, "R1 at the freeze: units won by V12 (D74)", checks)
    va = pd.read_csv(C.RESULTS / "nb5c_diag" / "vs_all" / "V12_5s.csv").set_index("h").loc[H1]
    for row, lab in (("A6a", "Chronos-2"), ("A6b", "TimesFM 2.5"), ("A6d", "TimeXer"), ("LGB", "LightGBM")):
        x = S[(S.row == row) & (S.ref == "main")].iloc[0]
        close(x.median_row, va[f"{lab} nRMSE"], 1e-9, f"{row} median at 1 h = vs_all (F56, D74)", checks)
        close(x.p, va[f"{lab} p"], 1e-9, f"{row} vs main, Wilcoxon p at 1 h = vs_all", checks)
    t = pd.read_csv(C.RESULTS / "nb5c_rows_v12" / "table.csv")
    t = t[(t.comparison == "A6e_V12_5s vs V12_5s (5-seed ensembles)") & (t.h == H1)].iloc[0]
    x = S[(S.row == "A6e") & (S.ref == "main")].iloc[0]
    close(x.diff_pct, t.diff_pct, 1e-9, "A6e vs main at 1 h = F62", checks)
    close(x.p, t.wilcoxon_p, 1e-12, "A6e vs main, Wilcoxon p = F62", checks)
    ch = pd.read_csv(C.RESULTS / "nb5c_weights" / "chosen.csv")
    for name, (_, pair) in WEIGHTED.items():
        x = S[S.row == name].iloc[0]
        c = ch[(ch.pair == pair) & (ch.h == H1)].iloc[0]
        close(x.median_row, c.nRMSE_chosen, 1e-12, f"{name} median at 1 h = part 2e (F61)", checks)
        close(x.median_ref, c.nRMSE_chronos2, 1e-12, f"Chronos-2 median at 1 h in the {pair} pair (F61)", checks)
    nb5 = json.loads((C.RESULTS / "nb5a_dev" / "summary.json").read_text())
    a1 = SC[(SC.row == "A1") & (SC.h == H1)]["nRMSE"].median()
    close(a1, nb5["median_nRMSE_full"]["A1"][str(H1)], 5e-6, "A1 median at 1 h = NB5a (rounded to 5 decimals)", checks)


# --- Main -----------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["validation", "test"], required=True)
    args = ap.parse_args()
    t0 = time.time()
    fz, fz_hash = EV.load_frozen()
    out_name = "nb6_validation" if args.set == "validation" else "nb6_test"
    if args.set == "test":
        assert not (C.RESULTS / out_name).exists(), "results/nb6_test exists: the test is scored once"
    ctx = EV.Context()
    gx = pd.read_csv(C.RESULTS / "nb4_sensor" / "gains_external.csv")
    if args.set == "validation":
        events = ctx.events("validation")
        src = validation_sources(fz)
        periods = {v: "stable" for v in events}           # June-July 2021, before any drift boundary
    else:
        events_scored, events_sens = ctx.events("scored"), ctx.events("sensitivity")
        events = events_scored
        src = test_sources(fz)
        per = pd.read_csv(C.RESULTS / "nb3_index" / "event_periods.csv").set_index("event")["sensor_period"]
        periods = per.to_dict()
    print(f"{args.set}: {len(events)} events; frozen configuration {fz_hash[:16]}", flush=True)
    all_events = events if args.set == "validation" else events_scored + events_sens
    SC, SL, CF, keys = score_all(src, all_events, fz, ctx, gx)
    print(f"scored in {time.time() - t0:.0f} s", flush=True)

    checks = []
    P = primary(SC, events, fz)                         # the primary test first
    p1 = P[P.primary].iloc[0]
    print(f"PRIMARY ({args.set}): main vs A1 at 1 h: median {p1.median_row:.5f} vs {p1.median_ref:.5f} "
          f"({p1.diff_pct:+.2f}%), main lower on {p1.events_row_lower} of {p1.n}, one-sided exact p = {p1.p:.5f}, "
          f"HL {p1.hl:+.5f} [{p1.hl_lo:+.5f}, {p1.hl_hi:+.5f}]", flush=True)
    S = secondary(SC, events, fz)
    DS = descriptive(SL, events, periods)
    DM = dm_table(SL, events, periods)
    BE, BC = bootstraps(SL, events, periods)
    if args.set == "validation":
        check_statistics(checks)
        check_reproduction(SC, CF, src, ctx, keys, checks)
        check_known(P, S, SC, checks)
        print(f"checks passed: {len(checks)}", flush=True)
    CK = pd.DataFrame(checks)

    pd.set_option("display.width", 220)
    print(P[["h", "median_row", "median_ref", "diff_pct", "events_row_lower", "p", "p_holm_other_horizons", "hl", "hl_lo",
             "hl_hi"]].round(5).to_string(index=False))
    print(S[["row", "ref", "median_row", "median_ref", "diff_pct", "events_row_lower", "p", "p_holm", "hl", "hl_lo",
             "hl_hi", "wording", "lower"]].round(5).to_string(index=False))
    summary = {"tool": "nb6_score", "set": args.set, "decision": "D79", "environment": A.versions(),
               "frozen_config_sha256": fz_hash, "commit": git("rev-parse", "HEAD"), "events": all_events,
               "n_paired": len(events), "runtime_s": round(time.time() - t0, 1),
               "primary": {k: py(p1[k]) for k in ["median_row", "median_ref", "diff_pct", "events_row_lower", "n", "p",
                                                  "hl", "hl_lo", "hl_hi", "hl_conf", "significant"]},
               "secondary": [{k: py(r[k]) for k in ["row", "ref", "diff_pct", "events_row_lower", "p", "p_holm", "hl",
                                                     "wording", "lower"]} for _, r in S.iterrows()],
               "n_checks": len(checks), "checks_passed": bool(CK["passed"].all()) if len(CK) else None}
    if args.set == "test":
        summary["manifest_sha256"] = src["manifest_sha256"]
    tables = {"scores": SC, "conformal": CF, "primary": P, "secondary": S, "descriptive": DS, "dm": DM,
              "bootstrap_events": BE, "bootstrap_campus": BC}
    if len(CK):
        tables["checks"] = CK
    out = A.write_outputs(out_name, tables, summary, parquet={"slots": SL})
    print("written to", out, f"| {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
