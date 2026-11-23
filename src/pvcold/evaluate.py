"""NB6: scores and statistics (guide §3.9, §4.4), read from the frozen configuration (D21, D77, D78).

One scorer serves the check on the 10 validation units and the single scoring of the test. It gathers rules that were
fixed before the freeze and changes none of them:
- seed ensembles: the mean of the sorted quantiles across seeds, sorted again (rule R1, D37);
- slots: per event and horizon, the issue times where every NB5a forecaster has a forecast and the target is observed
  (NB5a, rule R1); a row without full coverage (the sensor and satellite rows) is scored on its own slots and every
  comparison with it is paired on the slots both share (NB5d);
- composition: 200 members min(1, g^(m) Q_k(tau^(m)) G~(t + h)), with the event's prior: the frozen variant (G2) for
  a target in the prior test, G0 for a metadata-error target (NB3, NB5c conformal); the sensor and satellite rows use
  their own refitted gains (NB4, NB5d); A3 forces G0;
- the observation is NB5a's unit series for a single inverter target, and NB2's event target (targets15_kW) over the
  event's AC rating otherwise (multi-unit events, site targets), so every event is scored as NB2 defined it; on the
  validation units the two agree to float32 rounding (checked by the tool);
- conformal layer (part 2b): CQR on the donors' pseudo cold starts, per event, origin and horizon (D35, D46, D64);
- weighted pairs (part 2e): (1 - w_h) trained + w_h Chronos-2, quantile by quantile, sorted again (D75).

Statistics (guide §4.4, frozen 'statistics'): exact Wilcoxon signed-rank tests, Holm, Hodges–Lehmann estimates with
exact confidence intervals, the wording classes of §4.4, Diebold–Mariano tests with Newey–West variance and the
Harvey–Leybourne–Newbold correction, and day-block, moving-block and hierarchical bootstraps. A target's power is read
only to score it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from . import config as C
from . import fleet as F
from . import forecast as FC

QC = [f"q{t:.1f}" for t in FC.TAUS]
KEYS = ["event", "origin", "h", "t"]
ALPHA = 0.05
LEVEL_PCT = 3.0            # guide §3.10, frozen statistics 'level'
B_BOOT = 2000              # guide §4.4
BLOCK_DAYS = 3             # moving-block version (Künsch 1989)
FROZEN = C.RESULTS / "freeze" / "frozen_config.yaml"
SLOT_COLS = ["event", "row", "h", "t", "origin", "y", "mean", "med", "lo", "hi", "crps"]


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- Frozen configuration -----------------------------------------------------------------------------------------
def load_frozen(check_files: bool = True) -> tuple[dict, str]:
    """The frozen configuration and its sha256. Every pinned file must still carry its frozen hash."""
    b = FROZEN.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    s = json.loads((FROZEN.parent / "summary.json").read_text())
    assert h == s["frozen_config_sha256"], "frozen_config.yaml differs from its summary"
    cfg = yaml.safe_load(b.decode("utf-8"))
    if check_files:
        for f in cfg["files"].values():
            assert sha256(C.ROOT / f["path"]) == f["sha256"], f"pinned file changed since the freeze: {f['path']}"
    return cfg, h


# --- Ensembles and weighted pairs ---------------------------------------------------------------------------------
def ensemble(fc: pd.DataFrame, seeds: list | None = None) -> pd.DataFrame:
    """Seed ensemble (rule R1, D37): per issue time and horizon, the mean of the sorted quantiles, sorted again.
    With seeds, every key must carry exactly these seeds."""
    fc = fc.copy()
    fc["origin"], fc["t"] = pd.to_datetime(fc["origin"]), pd.to_datetime(fc["t"])
    if seeds is not None:
        assert sorted(int(s) for s in fc["seed"].unique()) == sorted(int(s) for s in seeds), "seeds differ"
        n = fc.groupby(KEYS)["seed"].nunique()
        assert (n == len(seeds)).all(), "a key lacks some seeds"
    m = fc.groupby(KEYS)[QC].mean()
    m[QC] = np.sort(m[QC].to_numpy(), axis=1)
    return m.reset_index()


def blend(trained: np.ndarray, c2: np.ndarray, w: float) -> np.ndarray:
    """Part 2e: (1 - w) * trained + w * Chronos-2, quantile by quantile, sorted again (tools/weight_check.blend)."""
    return np.sort((1.0 - w) * np.asarray(trained, dtype=float) + w * np.asarray(c2, dtype=float), axis=1)


def weighted_pair(trained: pd.DataFrame, c2: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """The weighted pair on the keys both members forecast, with the frozen weight of each horizon."""
    a, b = trained.set_index(KEYS)[QC], c2.set_index(KEYS)[QC]
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    h = common.get_level_values("h").to_numpy()
    out = np.empty((len(common), len(QC)))
    for hh, w in weights.items():
        m = h == int(hh)
        out[m] = blend(a.to_numpy()[m], b.to_numpy()[m], float(w))
    assert set(np.unique(h)) <= {int(x) for x in weights}, "a horizon has no frozen weight"
    return pd.DataFrame(out, columns=QC, index=common).reset_index()


# --- Context: events, observations, priors ------------------------------------------------------------------------
class Context:
    """Panel, events, NB3 gains and priors, and the frozen prior variant. Observations are read only to score."""

    def __init__(self):
        p = F.load_panel()
        self.targets_kW = p.pop("targets15_kW")
        self.p = p
        self.E = p["events"].set_index("event")
        self.U = p["units"]
        self.geo15 = p["geometry15"]
        self.gains3 = pd.read_csv(C.RESULTS / "nb3_index" / "gains.csv")
        self.pri3 = pd.read_csv(C.RESULTS / "nb3_index" / "priors.csv").set_index("event")
        self.PRIOR = yaml.safe_load((C.RESULTS / "nb3_index" / "frozen_config_part1.yaml").read_text())["prior_variant"]
        self.ALT = json.loads((C.RESULTS / "nb1_audit" / "summary.json").read_text())["campus_altitude_m"]
        self.lv, self.gl = FC.member_levels()
        self._T, self._gain, self._y = {}, {}, {}

    def events(self, set_: str) -> list[str]:
        return self.E.index[self.E["set"] == set_].tolist()

    def y_series(self, v: str) -> pd.Series:
        """The event's observed normalised power: NB5a's unit series for a single inverter target (exactly the series
        every development score used), else NB2's event target over the event's AC rating (multi-unit events, site
        targets)."""
        if v not in self._y:
            u = self.E.loc[v, "units"]
            if self.E.loc[v, "target_source"] == "inverter" and u in self.p["y15"].columns:
                self._y[v] = self.p["y15"][u]
            else:
                self._y[v] = self.targets_kW[v] / float(self.E.loc[v, "AC_kW"])
        return self._y[v]

    def y(self, v: str, target: pd.DatetimeIndex | pd.Series) -> np.ndarray:
        """The observation at the target times (y_series)."""
        return self.y_series(v).reindex(pd.DatetimeIndex(target)).to_numpy(dtype=float)

    def gt(self, target) -> np.ndarray:
        return self.geo15["Gt"].reindex(pd.DatetimeIndex(target)).to_numpy(dtype=float)

    def event_gain(self, v: str, force_g0: bool = False) -> dict:
        """Gain members of event v: the frozen variant for a target in the prior test, else G0 (NB5c conformal).
        A3 forces G0. Also the donors' leave-one-out priors (the conformal calibration set)."""
        key = (v, force_g0)
        if key in self._gain:
            return self._gain[key]
        a = F.event_arrays(v, self.p)
        g = self.gains3[self.gains3.event == v].set_index("donor")["gain"].reindex(a["dn"])
        pr, T_don, r_don, meta_ok = F.event_priors(a, g, self.U, self.ALT, self._T)
        variant = "G0" if force_g0 or not pr["target_in_prior_test"] else self.PRIOR
        B = np.asarray(pr["B_" + variant]) if variant != "G0" else g.dropna().to_numpy()
        if not force_g0:
            assert variant == self.pri3.loc[v, "prior_used"], f"{v}: prior variant differs from NB3"
            assert abs(pr[variant] - self.pri3.loc[v, "prior_gain"]) < 1e-9, f"{v}: prior differs from NB3"
        out = {"variant": variant, "prior": float(pr[variant]), "g_m": FC.gain_members(pr[variant], B / np.median(B), self.gl),
               "pseudo": FC.pseudo_priors(g, r_don, T_don, meta_ok, variant), "dn": a["dn"]}
        self._gain[key] = out
        return out

    def source_gain(self, v: str, gx: pd.Series) -> np.ndarray:
        """Gain members of a sensor or satellite row: NB4's gains refitted against the source (NB5d's rule)."""
        a = F.event_arrays(v, self.p)
        gx = gx.reindex(a["dn"])
        assert gx.notna().all(), v
        prx, _, _, _ = F.event_priors(a, gx, self.U, self.ALT, self._T)
        if prx["target_in_prior_test"]:
            g0, Bx = prx[self.PRIOR], np.asarray(prx["B_" + self.PRIOR])
        else:                                   # metadata-error target: G0 = the median donor gain (D32)
            g0, Bx = float(np.nanmedian(gx)), gx.dropna().to_numpy()
        return FC.gain_members(g0, Bx / np.median(Bx), self.gl)


def slot_keys(ref: pd.DataFrame, v: str, ctx: Context) -> pd.MultiIndex:
    """NB5a's scored slots of event v: (h, t) where every NB5a forecaster has a forecast and the target is observed."""
    f5 = ref[ref.event == v].copy()
    f5["target"] = f5["t"] + pd.to_timedelta(15 * f5["h"], unit="min")
    f5["y"] = ctx.y(v, f5["target"])
    good = f5[QC].notna().all(axis=1) & np.isfinite(f5["y"])
    cnt = f5[good].groupby(["h", "t"])["model"].nunique()
    return cnt[cnt == f5.model.nunique()].index


# --- Scoring --------------------------------------------------------------------------------------------------------
def score_event_row(x: pd.DataFrame, v: str, row: str, h: int, g_m: np.ndarray, ctx: Context) -> tuple[dict, pd.DataFrame]:
    """One event, row and horizon: NB5a's scores of the composed forecast (forecast.scores) and its slot table."""
    tgt = x["t"] + pd.Timedelta(minutes=15 * h)
    y, gt = ctx.y(v, tgt), ctx.gt(tgt)
    Y = FC.power_members(x[QC].to_numpy(dtype=float), gt, g_m, ctx.lv)
    sc = {"event": v, "row": row, "h": h, **FC.scores(Y, y)}
    sl = pd.DataFrame({"event": v, "row": row, "h": h, "t": x["t"].to_numpy(), "origin": x["origin"].to_numpy(), "y": y,
                       "mean": Y.mean(1), "med": np.median(Y, axis=1), "lo": np.quantile(Y, 0.1, axis=1),
                       "hi": np.quantile(Y, 0.9, axis=1), "crps": FC.crps_members(Y, y)})
    return sc, sl


def score_row(fc: pd.DataFrame, row: str, keys: dict, ctx: Context, gain=None, full: bool = True
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every event and horizon of one row on NB5a's slots. full: every slot must be forecast (else the row is scored
    on the slots it has, as NB5d). gain: callable v -> gain members (default: the event's prior)."""
    rows, slots = [], []
    for v, kv in keys.items():
        g_m = gain(v) if gain is not None else ctx.event_gain(v)["g_m"]
        f = fc[fc.event == v].set_index(["h", "t"])
        for h in FC.H:
            kh = kv[kv.get_level_values(0) == h]
            x = f.reindex(kh)
            ok = x[QC].notna().all(axis=1).to_numpy()
            if full:
                assert ok.all(), f"{row}, {v}, h {h}: {int((~ok).sum())} of NB5a's slots not forecast"
            if ok.sum() == 0:
                continue
            x = x[ok].reset_index()
            sc, sl = score_event_row(x, v, row, h, g_m, ctx)
            sc["n_keys"] = int(len(kh))
            rows.append(sc)
            slots.append(sl)
    return pd.DataFrame(rows), pd.concat(slots, ignore_index=True)


def conformal_corrections(cal: pd.DataFrame, v: str, ctx: Context) -> pd.DataFrame:
    """D35 rules 1-2 for event v: CQR scores of the donors' pseudo cold starts per origin and horizon, normalised by
    G~(t + h); the correction is the ceil((1 - alpha)(n + 1))-th smallest score (none under 50 scores)."""
    eg = ctx.event_gain(v)
    out = []
    for (o, h), x in cal[cal.event == v].groupby(["origin", "h"]):
        tgt = x["t"] + pd.Timedelta(minutes=15 * h)
        gtt, Qi = ctx.gt(tgt), x[QC].to_numpy(dtype=float)
        Es = []
        for d, (g0, Brel) in eg["pseudo"].items():
            yd = ctx.p["y15"][d].reindex(tgt).to_numpy()
            ok = np.isfinite(yd)
            Y = FC.power_members(Qi[ok], gtt[ok], FC.gain_members(g0, Brel, ctx.gl), ctx.lv)
            Es.append(FC.conformity(FC.power_quantiles(Y), yd[ok], gtt[ok]))
        Eall = np.vstack(Es)
        corr = FC.conformal_correction(Eall)
        out.append({"event": v, "origin": o, "h": h, "variant": eg["variant"], "n_scores": len(Eall),
                    **{f"corr{n}": float(corr[j]) for j, n in enumerate(FC.PAIR_NAMES)}})
    return pd.DataFrame(out)


def conformal_scores(fc: pd.DataFrame, cal: pd.DataFrame, row: str, keys: dict, ctx: Context) -> pd.DataFrame:
    """D35 rules 3: raw and conformal 9-quantile power forecasts of a row on NB5a's slots (forecast.quantile_scores)."""
    rows = []
    for v, kv in keys.items():
        corrs = conformal_corrections(cal, v, ctx).set_index(["origin", "h"])
        g_m = ctx.event_gain(v)["g_m"]
        f = fc[fc.event == v].set_index(["h", "t"])
        for h in FC.H:
            kh = kv[kv.get_level_values(0) == h]
            x = f.reindex(kh).reset_index()
            assert x[QC].notna().all(axis=None), f"{row}, {v}: missing slots"
            x["target"] = x["t"] + pd.Timedelta(minutes=15 * h)
            parts = {"raw": [], "conformal": []}
            ys = []
            for o, xo in x.groupby("origin"):
                gt_ = ctx.gt(xo["target"])
                Qp = FC.power_quantiles(FC.power_members(xo[QC].to_numpy(dtype=float), gt_, g_m, ctx.lv))
                corr = corrs.loc[(o, h), [f"corr{n}" for n in FC.PAIR_NAMES]].to_numpy(dtype=float)
                parts["raw"].append(Qp)
                # As validated (NB5c conformal): G~ is stored as float32 and numpy 1.26 multiplies the float64
                # correction by it in float32 (a scalar does not upcast an array), so the layer is applied that way.
                parts["conformal"].append(FC.apply_conformal(Qp, gt_.astype(np.float32), corr))
                ys.append(ctx.y(v, xo["target"]))
            y_ = np.concatenate(ys)
            for kind, Qs in parts.items():
                rows.append({"event": v, "row": row, "h": h, "kind": kind,
                             **FC.quantile_scores(np.vstack(Qs), y_, ctx.lv)})
    return pd.DataFrame(rows)


def paired(slots: pd.DataFrame, row: str, ref: str, h: int) -> pd.DataFrame:
    """Per event, both forecasters on the slots they share at horizon h: nRMSE, CRPS and the shared count."""
    a = slots[(slots.row == row) & (slots.h == h)].set_index(["event", "t"])
    b = slots[(slots.row == ref) & (slots.h == h)].set_index(["event", "t"])
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    ea, eb = a["y"] - a["mean"], b["y"] - b["mean"]
    g = pd.DataFrame({"sa": ea ** 2, "sb": eb ** 2, "ca": a["crps"], "cb": b["crps"]}).groupby(level="event", observed=True)
    m = g.mean()
    return pd.DataFrame({"nRMSE_row": np.sqrt(m["sa"]), "nRMSE_ref": np.sqrt(m["sb"]), "CRPS_row": m["ca"],
                         "CRPS_ref": m["cb"], "n": g.size()})


# --- Statistics -----------------------------------------------------------------------------------------------------
def signed_rank_null(n: int) -> np.ndarray:
    """Exact null distribution of the Wilcoxon signed-rank statistic T+ for n untied non-zero differences:
    probabilities of T+ = 0, 1, ..., n(n + 1)/2 (each sign equally likely; counts by dynamic programming)."""
    N = n * (n + 1) // 2
    c = np.zeros(N + 1, dtype=np.float64)
    c[0] = 1.0
    for r in range(1, n + 1):
        c[r:] = c[r:] + c[:-r].copy()
    return c / 2.0 ** n


def wilcoxon_p(d: np.ndarray, alternative: str) -> float:
    """Exact Wilcoxon signed-rank p-value of the paired differences d (scipy, method 'exact').
    alternative: 'two-sided', or 'less' (d tends to be negative)."""
    d = np.asarray(d, dtype=float)
    assert np.all(d != 0) and len(np.unique(np.abs(d))) == len(d), "zero or tied differences: the exact test needs none"
    return float(stats.wilcoxon(d, alternative=alternative, method="exact").pvalue)


def hodges_lehmann(d: np.ndarray, conf: float = 0.95) -> dict:
    """Hodges–Lehmann estimate (median of the Walsh averages) with the exact distribution-free confidence interval
    [W_(k), W_(N + 1 - k)], k - 1 the largest c with P(T+ <= c) <= (1 - conf) / 2; also the achieved level."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    i, j = np.triu_indices(n)
    W = np.sort((d[i] + d[j]) / 2.0)
    N = len(W)
    cdf = np.cumsum(signed_rank_null(n))
    a2 = (1.0 - conf) / 2.0
    ok = np.where(cdf <= a2 + 1e-12)[0]
    if len(ok) == 0:
        return {"hl": float(np.median(W)), "hl_lo": np.nan, "hl_hi": np.nan, "hl_conf": np.nan}
    k = int(ok[-1]) + 1                         # c = k - 1
    return {"hl": float(np.median(W)), "hl_lo": float(W[k - 1]), "hl_hi": float(W[N - k]),
            "hl_conf": float(1.0 - 2.0 * cdf[k - 1])}


def holm(p) -> np.ndarray:
    """Holm's step-down adjusted p-values (monotone, capped at 1)."""
    p = np.asarray(p, dtype=float)
    m = len(p)
    o = np.argsort(p, kind="stable")
    adj = np.maximum.accumulate((m - np.arange(m)) * p[o])
    out = np.empty(m)
    out[o] = np.minimum(adj, 1.0)
    return out


def wording(diff_pct: float, p_holm: float, hl: float, row: str, ref: str, classes: dict) -> dict:
    """§4.4's wording classes (frozen 'wording'): below 3% and not significant after Holm, level; below 3% but
    significant, consistently lower by less than 3%; from 3%, the difference named with its p-value. The lower
    forecaster is named from the Hodges–Lehmann sign for the paired test and from the ratio of medians from 3%."""
    if abs(diff_pct) >= LEVEL_PCT:
        cls, lower = classes["from 3%"], row if diff_pct < 0 else ref
    elif p_holm < ALPHA:
        cls, lower = classes["below 3%, significant after Holm"], row if hl < 0 else ref
    else:
        cls, lower = classes["below 3%, not significant after Holm"], None
    return {"class": cls, "lower": lower,
            "sign_conflict": bool(lower is not None and abs(diff_pct) < LEVEL_PCT and np.sign(hl) != np.sign(diff_pct))}


def dm_hln(e1: np.ndarray, e2: np.ndarray, h: int) -> dict:
    """Diebold–Mariano test of equal squared loss (guide §4.4): d_t = e1_t^2 - e2_t^2 in time order, Newey–West
    variance with lag h - 1 (Bartlett weights 1 - k/h), the Harvey–Leybourne–Newbold small-sample factor
    sqrt((T + 1 - 2h + h(h - 1)/T) / T), and a two-sided p from Student's t with T - 1 degrees of freedom.
    Negative statistic: forecaster 1 has the lower loss."""
    d = np.asarray(e1, dtype=float) ** 2 - np.asarray(e2, dtype=float) ** 2
    T = len(d)
    dc = d - d.mean()
    lrv = float(dc @ dc) / T
    for k in range(1, h):
        lrv += 2.0 * (1.0 - k / h) * float(dc[k:] @ dc[:-k]) / T
    dm = d.mean() / np.sqrt(lrv / T)
    hln = dm * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return {"dm": float(dm), "dm_hln": float(hln), "p": float(2 * stats.t.sf(abs(hln), df=T - 1)), "T": int(T),
            "mean_loss_diff": float(d.mean())}


def pair_slots(slots: pd.DataFrame, row: str, ref: str, v: str, h: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The slot tables of two forecasters for event v and horizon h on the issue times both forecast, in time order."""
    a = slots[(slots.row == row) & (slots.event == v) & (slots.h == h)].set_index("t")
    b = slots[(slots.row == ref) & (slots.event == v) & (slots.h == h)].set_index("t")
    common = a.index.intersection(b.index).sort_values()
    return a.loc[common], b.loc[common]


def day_sums(slots: pd.DataFrame, row: str, ref: str, v: str, h: int) -> pd.DataFrame:
    """Per target day of event v: sums of squared errors of two forecasters on their shared slots, and the count."""
    a, b = pair_slots(slots, row, ref, v, h)
    day = (a.index + pd.Timedelta(minutes=15 * h)).normalize()
    z = pd.DataFrame({"sa": ((a["y"] - a["mean"]) ** 2).to_numpy(), "sb": ((b["y"] - b["mean"]) ** 2).to_numpy(),
                      "n": 1.0, "day": day.to_numpy()})
    return z.groupby("day")[["sa", "sb", "n"]].sum().sort_index()


def _draws(D: int, B: int, rng, block: int) -> np.ndarray:
    """B x D day indices: whole days with replacement (block 1), or moving blocks of `block` consecutive days."""
    if block <= 1 or D <= block:
        return rng.integers(0, D, size=(B, D))
    nb = int(np.ceil(D / block))
    st = rng.integers(0, D - block + 1, size=(B, nb))
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :D]


def day_bootstrap(sums: pd.DataFrame, B: int, rng, block: int = 1) -> dict:
    """Day-block bootstrap within one event (guide §4.4): percentile 95% intervals of the forecaster's nRMSE, of the
    reference's, and of the skill 1 - nRMSE / nRMSE_ref."""
    S = sums[["sa", "sb", "n"]].to_numpy()
    idx = _draws(len(S), B, rng, block)
    tot = S[idx].sum(axis=1)
    ra, rb = np.sqrt(tot[:, 0] / tot[:, 2]), np.sqrt(tot[:, 1] / tot[:, 2])
    sk = 1.0 - ra / rb
    q = lambda x: (float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975)))   # noqa: E731
    return {"days": int(len(S)), "nRMSE_lo": q(ra)[0], "nRMSE_hi": q(ra)[1], "ref_lo": q(rb)[0], "ref_hi": q(rb)[1],
            "skill": float(1 - np.sqrt(S[:, 0].sum() / S[:, 2].sum()) / np.sqrt(S[:, 1].sum() / S[:, 2].sum())),
            "skill_lo": q(sk)[0], "skill_hi": q(sk)[1]}


def hierarchical_bootstrap(sums_by_event: dict, B: int, rng) -> dict:
    """Campus level (guide §4.4): resample events with replacement, then whole days within each drawn event (a fresh
    draw for every drawn event); percentile 95% interval of the median skill over events."""
    ev = list(sums_by_event)
    n = len(ev)
    skills = {}
    for e in ev:                                # B * n independent day draws per event
        S = sums_by_event[e][["sa", "sb", "n"]].to_numpy()
        tot = S[rng.integers(0, len(S), size=(B * n, len(S)))].sum(axis=1)
        skills[e] = 1.0 - np.sqrt(tot[:, 0] / tot[:, 2]) / np.sqrt(tot[:, 1] / tot[:, 2])
    pick = rng.integers(0, n, size=(B, n))
    draw = np.arange(B * n).reshape(B, n)
    med = np.median(np.array([[skills[ev[pick[b, j]]][draw[b, j]] for j in range(n)] for b in range(B)]), axis=1)
    point = float(np.median([1 - np.sqrt(sums_by_event[e]["sa"].sum() / sums_by_event[e]["n"].sum())
                             / np.sqrt(sums_by_event[e]["sb"].sum() / sums_by_event[e]["n"].sum()) for e in ev]))
    return {"events": n, "median_skill": point, "lo": float(np.quantile(med, 0.025)), "hi": float(np.quantile(med, 0.975))}


def hl_day_bootstrap(sums_by_event: dict, B: int, rng) -> dict:
    """Drifted window (guide §4.4): the Hodges–Lehmann median of the event-wise nRMSE differences, with a day-block
    bootstrap interval (whole days resampled within each event, the estimate recomputed)."""
    ev = list(sums_by_event)
    D = np.empty((B, len(ev)))
    for j, e in enumerate(ev):
        S = sums_by_event[e][["sa", "sb", "n"]].to_numpy()
        tot = S[rng.integers(0, len(S), size=(B, len(S)))].sum(axis=1)
        D[:, j] = np.sqrt(tot[:, 0] / tot[:, 2]) - np.sqrt(tot[:, 1] / tot[:, 2])
    i, k = np.triu_indices(len(ev))
    hl = np.median((D[:, i] + D[:, k]) / 2.0, axis=1)
    return {"boot_lo": float(np.quantile(hl, 0.025)), "boot_hi": float(np.quantile(hl, 0.975))}


def joint_day_bootstrap(sums_by_unit: dict, B: int, rng) -> dict:
    """Units that share one sky (the hidden-unit test bed, D18): whole target days resampled jointly for every unit
    (the same days for all), each unit's nRMSE difference recomputed, and the median over units; percentile 95%
    interval. A unit without a slot on a drawn day contributes nothing for that day."""
    days = sorted(set().union(*[set(s.index) for s in sums_by_unit.values()]))
    pos = {d: i for i, d in enumerate(days)}
    U = len(sums_by_unit)
    M = np.zeros((len(days), U, 3))
    for j, s in enumerate(sums_by_unit.values()):
        M[[pos[d] for d in s.index], j, :] = s[["sa", "sb", "n"]].to_numpy()
    idx = rng.integers(0, len(days), size=(B, len(days)))
    tot = M[idx].sum(axis=1)                                  # (B, U, 3)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.sqrt(tot[..., 0] / tot[..., 2]) - np.sqrt(tot[..., 1] / tot[..., 2])
    med = np.nanmedian(d, axis=1)
    return {"days": len(days), "boot_lo": float(np.quantile(med, 0.025)), "boot_hi": float(np.quantile(med, 0.975))}


def rng_for(label: str) -> np.random.Generator:
    """One reproducible stream per analysis: C.SEED with the label hashed into the seed sequence."""
    return np.random.default_rng([C.SEED, int(hashlib.sha256(label.encode()).hexdigest()[:8], 16)])
