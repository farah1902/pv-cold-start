"""NB5c: PVSetFormer, a censoring-aware fleet-set transformer for the campus index (guide §5.4, D24, D25, D36).

Interface of guide §3.7 (same issue rules, horizons, quantiles and rolling origins as the LightGBM bank), so its index
quantiles compose with the gain prior and the conformal layer exactly like LightGBM's. It reads the donors themselves:
each donor's implied index kappa_d, its clipping flag (a clipped reading is a lower bound, never a cloud) and its
validity, over the last 4 h in 1-h patches, plus static features. Development uses validation units only (rule R1).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import config as C
from . import forecast as FC

L, PATCH = C.N_LAGS, 4                      # 16 past steps (4 h) in 4 patches of 1 h
NP = L // PATCH
F_PATCH, F_STATIC, F_GEO, F_Q, F_FLEET = 3 * PATCH, 6, 7, 11, 2 * PATCH + 3
KAPPA_MAX = 2.0                              # implied indices above 2 (dawn, tiny clear sky) are capped
F_LIN = 2 * L + 3 + F_Q                      # linear path: index lags (as change from k_t) and flags, sigma, c, n, queries
F_VOL = 6                                    # V5: log s.d. over 1 h and 2 h, log |last change|, each with its flag
VOL_EPS, VOL_REF = 0.01, 0.1                 # log((x + VOL_EPS) / VOL_REF): finite at zero, near 0 for typical values
NO_DECAY = ("lin_w", "vol_w", "vg_w", "vg_b")  # linear and volatility paths: no weight decay
MAX_UNITS = 64                               # V7 donor identity table (the panel has fewer units; checked)
DEFAULTS = {"d": 64, "heads": 4, "n_sky": 4, "n_enc": 2, "n_dec": 2, "dropout": 0.1, "lr": 1e-3, "weight_decay": 1e-2,
            "batch": 256, "max_epochs": 100, "patience": 15, "donor_dropout": 0.1,
            "fleet_token": 0, "balance": 0,   # V2 options (D36): fleet-summary token per patch; horizon-balanced loss
            "lin": 0,                         # V4 option: per-horizon linear path on the index lags (no weight decay)
            "aux": 0.0,                       # V4 option: weight of the auxiliary donor-forecast loss (censored)
            "summary_only": 0,                # A6e (rule R2): fleet-summary tokens only, no donor tokens
            "vol": 0,                         # V5 option: volatility features of the index -> the 9 head outputs
            "vgate": 0,                       # V5 option: volatility gate on the transformer's median shift
            "hmask": 0,                       # V6 option: horizon queries do not attend to one another
            "hhead": 0,                       # V6 option: per-horizon deviation from the shared head
            "donor_id": 0,                    # V7 option: learned identity embedding per donor
            "donor_rel": 0,                   # V7 option: donor deviation from the index, per step
            "ext": "",                         # A4c (D51): external index source added to the fleet token, e.g. sensor_corr
            "arch": "pvsf"}                   # "timexer": TimeXer with the same inputs (rule R2, timexer.py)


# --- Data: donor tokens, geometry, queries, targets on the full 15-min grid -----------------------------------------
def tilt_class(tilt, az) -> list:
    """One-hot (flat, single tilted plane, mixed or multi-plane) from the Brick tilt and azimuth strings."""
    t, a = str(tilt), str(az)
    if "Mixed" in t or "Mixed" in a or "/" in t or "/" in a:
        return [0.0, 0.0, 1.0]
    return [1.0, 0.0, 0.0] if t == "0deg" else [0.0, 1.0, 0.0]


def event_arrays(name: str, p: dict, S: pd.DataFrame, gains: pd.Series) -> dict:
    """Full-grid arrays of one event: donor kappa / clip / valid (T x n), static donor features (n x 6) plus the
    donor's global unit index as a 7th column (read only by the donor_id option), the event's
    index series S (forecast.event_series) and the per-horizon targets. Donor data only; no target power."""
    g = S.index
    dn = list(gains.index)
    Y = p["y15"][dn].reindex(g).to_numpy(dtype=float)
    fl = p["flags15"][dn].reindex(g).to_numpy()
    gt = S["Gt"].to_numpy()
    started = g.to_numpy()[:, None] >= p["units"].loc[dn, "rule_start"].to_numpy()[None, :]
    day = np.nan_to_num(gt) > C.ISSUE_MIN_GTILDE
    valid = (fl == 0) & np.isfinite(Y) & started & day[:, None]
    with np.errstate(all="ignore"):
        kap = Y / (gains.to_numpy()[None, :] * gt[:, None])
    kap = np.where(valid, np.clip(kap, 0, KAPPA_MAX), 0.0)
    clip = np.where(valid, (Y >= C.CLIP_THRESHOLD).astype(float), 0.0)
    U = p["units"].loc[dn]
    meta = U["in_prior_test"].astype(bool).to_numpy()
    r = np.where(meta, U["DC_AC"].to_numpy(dtype=float), 0.0)
    uid = p["units"].index.get_indexer(dn)
    assert (uid >= 0).all() and uid.max() < MAX_UNITS, "donor index outside the identity table"
    static = np.column_stack([gains.to_numpy(), r, meta.astype(float),
                              np.array([tilt_class(a, b) for a, b in zip(U["tilt"], U["azimuth_brick"])]),
                              uid.astype(float)])
    return {"name": name, "dn": dn, "kap": kap.astype(np.float32), "clip": clip.astype(np.float32),
            "valid": valid.astype(np.float32), "started": started, "static": static.astype(np.float32), "S": S}


def samples(A: dict, pos: np.ndarray) -> dict:
    """Model inputs for the issue times at grid positions `pos` (pos >= L - 1)."""
    S = A["S"]
    win = pos[:, None] - np.arange(L - 1, -1, -1)[None, :]                 # oldest -> newest
    kap, clp, val = A["kap"][win], A["clip"][win], A["valid"][win]        # (B, L, n)
    x = np.stack([kap, clp, val], axis=-1)                                # (B, L, n, 3)
    x = x.reshape(len(pos), NP, PATCH, -1, 3).transpose(0, 3, 1, 2, 4).reshape(len(pos), -1, NP, F_PATCH)
    online = (val.sum(axis=1) > 0) & A["started"][pos]                    # (B, n)
    geo_cols = ["cosz", "sin_az", "cos_az", "sin_ha", "cos_ha", "sin_doy", "cos_doy"]
    G = np.nan_to_num(S[geo_cols].to_numpy(dtype=float))
    geo = G[win[:, PATCH - 1::PATCH]]                                     # geometry at each patch's last step
    k = S["k"].to_numpy()
    q = np.zeros((len(pos), len(FC.H), F_Q))
    Gf = np.nan_to_num(S[["Gt"] + geo_cols].to_numpy(dtype=float))
    for j, h in enumerate(FC.H):
        tp = np.minimum(pos + h, len(k) - 1)
        prev = pos + h - FC.SPD
        kp = np.where(prev >= 0, k[np.maximum(prev, 0)], np.nan)
        q[:, j, :8] = Gf[tp]
        q[:, j, 8] = np.nan_to_num(kp)
        q[:, j, 9] = np.isfinite(kp)
        q[:, j, 10] = h / 24.0
    pe = win[:, PATCH - 1::PATCH]                                         # patch ends
    kw = k[win]
    fleet = np.concatenate([np.nan_to_num(kw).reshape(len(pos), NP, PATCH),
                            np.isfinite(kw).reshape(len(pos), NP, PATCH).astype(float),
                            np.nan_to_num(S["sigma"].to_numpy()[pe])[..., None], np.nan_to_num(S["c"].to_numpy()[pe])[..., None],
                            (np.nan_to_num(S["n"].to_numpy()[pe]) / 40.0)[..., None]], axis=-1)
    if "k_ext" in S.columns:                       # A4c: external index values and flags after the F_FLEET columns
        kx = S["k_ext"].to_numpy()[win]
        fleet = np.concatenate([fleet, np.nan_to_num(kx).reshape(len(pos), NP, PATCH),
                                np.isfinite(kx).reshape(len(pos), NP, PATCH).astype(float)], axis=-1)
    # Donor futures for the auxiliary loss: implied index, validity and clipping flag at t + h (B, n, 6)
    T = len(k)
    dy = np.zeros((len(pos), kap.shape[2], len(FC.H)), np.float32)
    dv, dc = np.zeros_like(dy), np.zeros_like(dy)
    for j, h in enumerate(FC.H):
        tp = np.minimum(pos + h, T - 1)
        inside = (pos + h <= T - 1)[:, None]
        dy[:, :, j], dv[:, :, j] = A["kap"][tp], A["valid"][tp] * inside
        dc[:, :, j] = A["clip"][tp] * inside
    return {"x": x.astype(np.float32), "static": A["static"], "online": online, "geo": geo.astype(np.float32),
            "fleet": fleet.astype(np.float32),
            "q": q.astype(np.float32), "anchor": k[pos].astype(np.float32), "dy": dy, "dv": dv, "dc": dc}


def targets(A: dict, origin: pd.Timestamp | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Issue mask (T), targets k(t + h) (T x 6) and target masks (T x 6), with the same rules as the LightGBM bank;
    with an origin, a target counts only if it lies before the origin (training pairs)."""
    S = A["S"]
    t = S.index
    k = S["k"].to_numpy()
    st = FC.state(S)
    issue = S["panel"].to_numpy() & (S["Gt"].to_numpy() > C.ISSUE_MIN_GTILDE) & \
        (S["n"].to_numpy() >= C.ISSUE_MIN_DONORS) & np.isfinite(k)
    after = np.asarray(t >= FC.TRAIN_START)
    Y = np.full((len(t), len(FC.H)), np.nan)
    M = np.zeros((len(t), len(FC.H)), bool)
    for j, h in enumerate(FC.H):
        D = FC.design(S, st, h)                      # D["ok"] = issue rule at t and target rule at t + h
        Y[:, j] = D["y"]
        m = D["ok"] & after
        if origin is not None:
            m = m & np.isfinite(D["y"]) & np.asarray((t + pd.Timedelta(minutes=15 * h)) < origin)
        M[:, j] = m
    return issue, Y, M


# --- Model ----------------------------------------------------------------------------------------------------------
def build_model(cfg: dict):
    if cfg.get("arch", "pvsf") == "timexer":         # rule R2: same inputs, interface and training path
        from .timexer import build_timexer
        return build_timexer(cfg)
    assert cfg.get("arch", "pvsf") == "pvsf", cfg.get("arch")
    import torch
    import torch.nn as nn
    import torch.nn.functional as Fn

    class PVSetFormer(nn.Module):
        def __init__(self, d, heads, n_sky, n_enc, n_dec, dropout, fleet_token, lin=0, aux=0.0, summary_only=0,
                     vol=0, vgate=0, hmask=0, hhead=0, donor_id=0, donor_rel=0, ext=0):
            super().__init__()
            # A6e (rule R2): the fleet summary only, no donor tokens; needs the fleet token, excludes the donor loss
            self.summary_only = bool(summary_only)
            assert not self.summary_only or (fleet_token and aux == 0), "summary_only needs fleet_token=1 and aux=0"
            self.n_sky, self.fleet = (0 if self.summary_only else n_sky), bool(fleet_token)
            self.m = self.n_sky + int(self.fleet)            # tokens per patch
            if not self.summary_only:
                self.patch_in, self.static_in = nn.Linear(F_PATCH, d), nn.Linear(F_STATIC, d)
            self.geo_in, self.q_in = nn.Linear(F_GEO, d), nn.Linear(F_Q, d)
            layer = lambda: nn.TransformerEncoderLayer(d, heads, 2 * d, dropout, batch_first=True, norm_first=True)  # noqa: E731
            if not self.summary_only:
                self.set_layer = layer()
                self.pool_q = nn.Parameter(torch.randn(n_sky, d) * 0.02)
                self.pool = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
            self.temporal = nn.TransformerEncoder(layer(), n_enc, enable_nested_tensor=False)
            self.decoder = nn.TransformerDecoder(
                nn.TransformerDecoderLayer(d, heads, 2 * d, dropout, batch_first=True, norm_first=True), n_dec)
            self.norm, self.head = nn.LayerNorm(d), nn.Linear(d, 9)
            nn.init.zeros_(self.head.weight)
            with torch.no_grad():                    # start at persistence with a narrow spread
                self.head.bias.zero_()
                self.head.bias[1:].fill_(-3.0)
            if self.fleet:                                   # created last: V1's initialisation is unchanged
                self.fleet_in = nn.Linear(F_FLEET, d)
            self.lin, self.aux = bool(lin), aux > 0          # V4 options, created after everything else
            if self.lin:                                     # per-horizon linear map to the 9 head outputs, zero start
                self.lin_w = nn.Parameter(torch.zeros(len(FC.H), F_LIN, 9))
            if self.aux:                                     # donor offset from the aggregate median, per horizon
                self.aux_in = nn.Linear(2 * d, d)
                self.aux_out = nn.Linear(d, 1)
            self.vol, self.vgate = bool(vol), bool(vgate)    # V5 options, created last; zero start = V4a's start
            if self.vol:                                     # per-horizon map of the volatility features
                self.vol_w = nn.Parameter(torch.zeros(len(FC.H), F_VOL, 9))
            if self.vgate:                                   # per-horizon gate 1 + tanh(w . vol + b), 1 at the start
                self.vg_w = nn.Parameter(torch.zeros(len(FC.H), F_VOL))
                self.vg_b = nn.Parameter(torch.zeros(len(FC.H)))
            self.hmask, self.hhead = bool(hmask), bool(hhead)  # V6 options, created last; zero start
            if self.hmask:                                   # each horizon query attends only to itself
                self.register_buffer("hmask_buf", ~torch.eye(len(FC.H), dtype=torch.bool))
            if self.hhead:                                   # per-horizon deviation from the shared head
                self.hh_w = nn.Parameter(torch.zeros(len(FC.H), d, 9))
                self.hh_b = nn.Parameter(torch.zeros(len(FC.H), 9))
            self.donor_id, self.donor_rel = bool(donor_id), bool(donor_rel)   # V7 options, created last
            assert not ((donor_id or donor_rel) and self.summary_only), "V7 options need donor tokens"
            if self.donor_id:                                # learned identity per donor, zero start
                self.id_emb = nn.Parameter(torch.zeros(MAX_UNITS, d))
            if self.donor_rel:                               # donor kappa minus the index, per step, zero start
                self.rel_in = nn.Linear(PATCH, d)
                nn.init.zeros_(self.rel_in.weight)
                nn.init.zeros_(self.rel_in.bias)
            self.ext = bool(ext)                             # A4c, created last; zero start
            assert not self.ext or self.fleet, "ext needs the fleet token"
            if self.ext:
                self.ext_in = nn.Linear(2 * PATCH, d)
                nn.init.zeros_(self.ext_in.weight)
                nn.init.zeros_(self.ext_in.bias)
            causal = torch.triu(torch.ones(NP, NP, dtype=torch.bool), 1)
            self.register_buffer("causal", causal.repeat_interleave(self.m, 0).repeat_interleave(self.m, 1))

        def lin_features(self, q, anchor, fleet):
            """(B, 6, F_LIN): index lags minus k_t (zero where missing), their flags, sigma / c / n at the issue time,
            and the horizon query with the day-earlier index also as a change from k_t."""
            B = q.shape[0]
            kl, kv = fleet[:, :, :PATCH].reshape(B, L), fleet[:, :, PATCH:2 * PATCH].reshape(B, L)
            z = torch.cat([(kl - anchor[:, None]) * kv, kv, fleet[:, -1, 2 * PATCH:F_FLEET]], -1)
            qq = q.clone()
            qq[..., 8] = (q[..., 8] - anchor[:, None]) * q[..., 9]
            return torch.cat([z[:, None].expand(B, q.shape[1], -1), qq], -1)

        def vol_features(self, fleet):
            """(B, F_VOL): recent volatility of the index from its own lags, the scale LightGBM reads from sd_1h and dk.
            Log s.d. over the last 1 h (at least 3 valid lags) and 2 h (at least 4), and log |k_t - k_(t-1)|, each as
            log((x + VOL_EPS) / VOL_REF) times its validity flag, followed by the flag. Inputs only: no gradient."""
            B = fleet.shape[0]
            kl, kv = fleet[:, :, :PATCH].reshape(B, L), fleet[:, :, PATCH:2 * PATCH].reshape(B, L)   # oldest -> newest
            out = []
            for n, need in ((PATCH, 3), (2 * PATCH, 4)):
                xs, vs = kl[:, -n:], kv[:, -n:]
                c = vs.sum(1)
                mu = (xs * vs).sum(1) / c.clamp(min=1)
                sd = (((xs - mu[:, None]) ** 2 * vs).sum(1) / (c - 1).clamp(min=1)).clamp(min=0).sqrt()
                ok = (c >= need).float()
                out += [torch.log((sd + VOL_EPS) / VOL_REF) * ok, ok]
            ok = kv[:, -1] * kv[:, -2]
            out += [torch.log(((kl[:, -1] - kl[:, -2]).abs() + VOL_EPS) / VOL_REF) * ok, ok]
            return torch.stack(out, -1)

        def forward(self, x, static, online, geo, q, anchor, fleet, return_aux=False):
            B, n = x.shape[0], x.shape[1]
            ge = self.geo_in(geo)                                                     # (B, NP, d)
            assert fleet.shape[-1] == F_FLEET + (2 * PATCH if self.ext else 0), "fleet columns do not match ext"
            if self.fleet:                                   # the fleet token (plus the external index, A4c)
                ftok = self.fleet_in(fleet[..., :F_FLEET])
                if self.ext:
                    ftok = ftok + self.ext_in(fleet[..., F_FLEET:])
            if self.summary_only:                            # A6e: one fleet-summary token per patch
                s = ftok[:, :, None]
            else:
                h = self.patch_in(x) + self.static_in(static[..., :F_STATIC])[:, :, None] + ge[:, None]   # (B, n, NP, d)
                if self.donor_id:
                    h = h + self.id_emb[static[0, :, F_STATIC].long()][None, :, None]
                if self.donor_rel:                           # kappa_d - k per step where both are valid
                    kl, kv = fleet[:, :, :PATCH], fleet[:, :, PATCH:2 * PATCH]               # (B, NP, PATCH)
                    rel = (x[..., 0::3] - kl[:, None]) * x[..., 2::3] * kv[:, None]        # (B, n, NP, PATCH)
                    h = h + self.rel_in(rel)
                h = h.transpose(1, 2).reshape(B * NP, n, -1)
                pad = (~online)[:, None, :].expand(B, NP, n).reshape(B * NP, n)
                h = self.set_layer(h, src_key_padding_mask=pad)
                h_last = h.reshape(B, NP, n, -1)[:, -1]                                # donors at the issue patch
                s, _ = self.pool(self.pool_q.expand(B * NP, -1, -1), h, h, key_padding_mask=pad)
                s = s.reshape(B, NP, self.n_sky, -1)
                if self.fleet:                               # the fleet summary as one more token per patch
                    s = torch.cat([s, ftok[:, :, None]], dim=2)
            s = s.reshape(B, NP * self.m, -1) + ge.repeat_interleave(self.m, dim=1)
            enc = self.temporal(s, mask=self.causal)
            dec = self.norm(self.decoder(self.q_in(q), enc,
                                         tgt_mask=self.hmask_buf if self.hmask else None))  # (B, 6, d)
            o = self.head(dec)                                                        # (B, 6, 9)
            if self.hhead:
                o = o + torch.einsum("bhd,hdo->bho", dec, self.hh_w) + self.hh_b
            if self.vol or self.vgate:
                vf = self.vol_features(fleet)                                         # (B, F_VOL)
            if self.vgate:                                   # scales the transformer's median shift only
                g = 1 + torch.tanh(torch.einsum("bf,hf->bh", vf, self.vg_w) + self.vg_b)
                o = torch.cat([o[..., :1] * g[..., None], o[..., 1:]], -1)
            if self.vol:                                     # in the softplus tail: spread ~ volatility ** w
                o = o + torch.einsum("bf,hfo->bho", vf, self.vol_w)
            if self.lin:
                o = o + torch.einsum("bhf,hfo->bho", self.lin_features(q, anchor, fleet), self.lin_w)
            up = Fn.softplus(o[..., 1:5]).cumsum(-1)
            dn = Fn.softplus(o[..., 5:9]).cumsum(-1)
            qs = torch.cat([o[..., :1] - dn.flip(-1), o[..., :1], o[..., :1] + up], -1)
            out = anchor[:, None, None] + qs                                          # change from persistence (D34)
            if not return_aux:
                return out
            hd = torch.cat([h_last[:, :, None].expand(-1, -1, dec.shape[1], -1),
                            dec[:, None].expand(-1, n, -1, -1)], -1)                  # (B, n, 6, 2d)
            off = self.aux_out(Fn.gelu(self.aux_in(hd)))[..., 0]                     # (B, n, 6)
            return out, out[:, None, :, 4] + off                                     # donor medians

    return PVSetFormer(cfg["d"], cfg["heads"], cfg["n_sky"], cfg["n_enc"], cfg["n_dec"], cfg["dropout"],
                       cfg.get("fleet_token", 0), cfg.get("lin", 0), cfg.get("aux", 0.0), cfg.get("summary_only", 0),
                       cfg.get("vol", 0), cfg.get("vgate", 0), cfg.get("hmask", 0), cfg.get("hhead", 0),
                       cfg.get("donor_id", 0), cfg.get("donor_rel", 0), bool(cfg.get("ext", "")))


def n_params(cfg: dict) -> int:
    return int(sum(p.numel() for p in build_model(cfg).parameters()))


# --- Training ---------------------------------------------------------------------------------------------------------
def _tensors(B: dict, rows=None):
    import torch
    sl = slice(None) if rows is None else rows
    st = np.broadcast_to(B["static"], (len(B["anchor"]),) + B["static"].shape)
    return [torch.from_numpy(np.ascontiguousarray(B["x"][sl])), torch.from_numpy(np.ascontiguousarray(st[sl])),
            torch.from_numpy(np.ascontiguousarray(B["online"][sl])), torch.from_numpy(np.ascontiguousarray(B["geo"][sl])),
            torch.from_numpy(np.ascontiguousarray(B["q"][sl])), torch.from_numpy(np.ascontiguousarray(B["anchor"][sl])),
            torch.from_numpy(np.ascontiguousarray(B["fleet"][sl]))]


def _loss(pred, y, m, taus, w=None):
    """Pinball loss over the 9 quantiles, averaged over the valid (issue time, horizon) pairs."""
    import torch
    d = y[:, :, None] - pred
    pb = torch.maximum(taus * d, (taus - 1) * d).mean(-1)
    if w is not None:                                    # horizon weights (balanced loss)
        pb = pb * w[None, :]
    return (pb * m).sum() / m.sum().clamp(min=1)


def _aux_loss(dpred, dy, dm, dc, w=None):
    """Median loss on the donors' own futures. A clipped reading is a lower bound on the donor's implied index, so it
    only penalises forecasts below it (one-sided, the censoring rule of the index, D30)."""
    import torch
    e = dy - dpred
    l = 0.5 * torch.where(dc > 0, torch.relu(e), e.abs())
    if w is not None:
        l = l * w[None, None, :]
    return (l * dm).sum() / dm.sum().clamp(min=1)


def _predict(model, B: dict, batch: int = 1024) -> np.ndarray:
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(B["anchor"]), batch):
            out.append(model(*_tensors(B, slice(i, i + batch))).numpy())
    return np.concatenate(out) if out else np.zeros((0, len(FC.H), len(FC.TAUS)))


def _train(Btr: dict, ytr, mtr, cfg, seed, epochs, Bva=None, yva=None, mva=None, w=None):
    """AdamW on the masked pinball loss; with a validation set, early stopping (returns the best epoch count)."""
    import torch
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = build_model(cfg)
    nowd = [p for n_, p in model.named_parameters() if n_ in NO_DECAY]
    if nowd:                                             # linear and volatility paths are not shrunk
        rest = [p for n_, p in model.named_parameters() if n_ not in NO_DECAY]
        opt = torch.optim.AdamW([{"params": rest}, {"params": nowd, "weight_decay": 0.0}],
                                lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    taus = torch.tensor(FC.TAUS, dtype=torch.float32)
    Ttr = _tensors(Btr)
    ytr_t, mtr_t = torch.from_numpy(np.nan_to_num(ytr).astype(np.float32)), torch.from_numpy(mtr.astype(np.float32))
    lam = float(cfg.get("aux", 0.0))
    if lam > 0:                                          # donor futures, only for training pairs (target before origin)
        Dy = torch.from_numpy(Btr["dy"])
        Dm = torch.from_numpy(Btr["dv"] * mtr.astype(np.float32)[:, None, :])
        Dc = torch.from_numpy(Btr["dc"])
    if Bva is not None:
        Tva = _tensors(Bva)
        yva_t, mva_t = torch.from_numpy(np.nan_to_num(yva).astype(np.float32)), torch.from_numpy(mva.astype(np.float32))
    best, best_ep, wait, hist = np.inf, 0, 0, []
    best_state = None
    for ep in range(1, epochs + 1):
        model.train()
        perm = rng.permutation(len(ytr))
        for i in range(0, len(perm), cfg["batch"]):
            b = torch.from_numpy(perm[i:i + cfg["batch"]])
            xb = [t[b] for t in Ttr]
            if cfg["donor_dropout"] > 0:                 # random donor subsets (guide §5.4)
                keep = torch.rand(xb[2].shape) >= cfg["donor_dropout"]
                on = xb[2] & keep
                on[on.sum(1) == 0] = xb[2][on.sum(1) == 0]
                xb[2] = on
            if lam > 0:
                pred, dpred = model(*xb, return_aux=True)
                dm = Dm[b] * xb[2][:, :, None].float()    # donors in the set this step
                loss = _loss(pred, ytr_t[b], mtr_t[b], taus, w) + lam * _aux_loss(dpred, Dy[b], dm, Dc[b], w)
            else:
                loss = _loss(model(*xb), ytr_t[b], mtr_t[b], taus, w)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        if Bva is None:
            continue
        model.eval()
        with torch.no_grad():
            vl = float(_loss(torch.from_numpy(_predict(model, Bva)), yva_t, mva_t, taus, w))
        hist.append(vl)
        if vl < best - 1e-6:
            best, best_ep, wait = vl, ep, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= cfg["patience"]:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_ep, hist


def fit_predict(A: dict, origin: pd.Timestamp, end: pd.Timestamp, cfg: dict, seed: int) -> dict:
    """One event, origin and seed: early stopping on the last 20% of the training issue times (by time), predictions
    of that early-stopped model on them (conformal calibration set, D35), then a refit on all training issue times
    for the best number of epochs, and its forecasts of the issue times in [origin, end). Index quantiles."""
    import torch
    torch.set_num_threads(1)
    t0 = time.time()
    t = A["S"].index
    issue, Y, M_all = targets(A)
    _, _, M = targets(A, origin)
    tr = np.where(issue & M.any(1) & (np.arange(len(t)) >= L - 1))[0]
    fc = np.where(issue & (t >= origin) & (t < end) & M_all.any(1))[0]
    out = {"seed": seed, "n_train": int(len(tr)), "n_fc": int(len(fc))}
    if len(tr) < 50 or len(fc) == 0:
        out["skipped"] = True
        return out
    cut = int(round(len(tr) * (1 - FC.VALID_FRAC)))
    a, b = tr[:cut], tr[cut:]
    Ba, Bb = samples(A, a), samples(A, b)
    w = None
    if cfg.get("balance", 0):                             # 1 / persistence error per horizon (training pairs)
        k_t = A["S"]["k"].to_numpy()[tr]
        err = np.array([np.nanmean(np.abs(Y[tr, j] - k_t)[M[tr, j]]) for j in range(len(FC.H))])
        w = torch.tensor(1 / err / np.mean(1 / err), dtype=torch.float32)
    m1, best_ep, hist = _train(Ba, Y[a], M[a], cfg, seed, cfg["max_epochs"], Bb, Y[b], M[b], w)
    cal = np.clip(np.sort(_predict(m1, Bb), axis=-1), *C.K_BOUNDS)
    m2, _, _ = _train(samples(A, tr), Y[tr], M[tr], cfg, seed, max(best_ep, 1), w=w)
    fcq = np.clip(np.sort(_predict(m2, samples(A, fc)), axis=-1), *C.K_BOUNDS)
    out.update({"best_epoch": int(best_ep), "val_hist": hist, "fc_pos": fc, "fc_q": fcq.astype(np.float32),
                "fc_mask": M_all[fc], "cal_pos": b, "cal_q": cal.astype(np.float32), "cal_mask": M[b],
                "runtime_s": round(time.time() - t0, 1)})
    return out


def to_rows(name: str, origin, A: dict, res: dict, kind: str = "fc", model: str = "PVSF") -> pd.DataFrame:
    """Long rows (event, origin, model, h, t, q0.1..q0.9) like forecast.run_origin, for the masked horizons."""
    t = A["S"].index
    pos, Q, Mk = res[f"{kind}_pos"], res[f"{kind}_q"], res[f"{kind}_mask"]
    cols = [f"q{tau:.1f}" for tau in FC.TAUS]
    rows = []
    for j, h in enumerate(FC.H):
        m = Mk[:, j]
        f = pd.DataFrame(Q[m, j, :], columns=cols)
        f.insert(0, "t", t[pos[m]]); f.insert(0, "h", h); f.insert(0, "model", model)
        f.insert(0, "seed", res["seed"]); f.insert(0, "origin", origin); f.insert(0, "event", name)
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


# --- Hyperparameter search: same protocol and budget as the LightGBM grid (guide §5.2, R1) -----------------------
PVSF_GRID = [{"d": d, "lr": lr, "weight_decay": wd} for d in (32, 64) for lr in (3e-4, 1e-3, 3e-3) for wd in (0.01, 0.1, 0.5)]


def cv_fold(A: dict, fold_start: pd.Timestamp, fold_end: pd.Timestamp, cfg: dict, seed: int) -> dict:
    """Train on issue times whose targets fall before the fold (early stopping on the last 20%, refit), score the
    index quantiles by the mean pinball loss per horizon on targets inside the fold (as forecast.cv_task)."""
    import torch
    torch.set_num_threads(1)
    t = A["S"].index
    issue, Y, M_all = targets(A)
    _, _, M = targets(A, fold_start)
    tr = np.where(issue & M.any(1) & (np.arange(len(t)) >= L - 1))[0]
    Mv = np.zeros_like(M_all)
    for j, h in enumerate(FC.H):
        tt = np.asarray(t + pd.Timedelta(minutes=15 * h))
        Mv[:, j] = M_all[:, j] & np.isfinite(Y[:, j]) & (tt >= np.datetime64(fold_start)) & (tt < np.datetime64(fold_end))
    va = np.where(issue & Mv.any(1))[0]
    w = None
    if cfg.get("balance", 0):
        k_t = A["S"]["k"].to_numpy()[tr]
        err = np.array([np.nanmean(np.abs(Y[tr, j] - k_t)[M[tr, j]]) for j in range(len(FC.H))])
        w = torch.tensor(1 / err / np.mean(1 / err), dtype=torch.float32)
    cut = int(round(len(tr) * (1 - FC.VALID_FRAC)))
    a, b = tr[:cut], tr[cut:]
    _, best_ep, _ = _train(samples(A, a), Y[a], M[a], cfg, seed, cfg["max_epochs"], samples(A, b), Y[b], M[b], w)
    m2, _, _ = _train(samples(A, tr), Y[tr], M[tr], cfg, seed, max(best_ep, 1), w=w)
    Q = np.clip(np.sort(_predict(m2, samples(A, va)), axis=-1), *C.K_BOUNDS)
    res = {}
    for j, h in enumerate(FC.H):
        m = Mv[va, j]
        res[h] = (float(FC.pinball(Q[m, j, :], Y[va[m], j]).mean()), int(m.sum()), int(best_ep))
    return res
