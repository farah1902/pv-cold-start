"""TimeXer as an index forecaster with the same per-donor inputs as PVSetFormer (rule R2, D25, D38).

TimeXer: Y. Wang, H. Wu, J. Dong, G. Qin, H. Zhang, Y. Liu, Y. Qiu, J. Wang, M. Long, "TimeXer: Empowering
Transformers for Time Series Forecasting with Exogenous Variables", arXiv:2402.19072 (v4, 11 Nov 2024; doi
10.48550/arXiv.2402.19072). Re-implemented here from the paper (Section 3, Eqs. 2-8) and from a reading of the
official code's structure (github.com/thuml/TimeXer, read 21 Nov 2026; the repository declares no licence, so no code
was copied). Kept from TimeXer:
  - the endogenous series cut into non-overlapping patches, each linearly embedded (no bias) plus a fixed sinusoidal
    position embedding, and one learnable global token (standard-normal start) appended after the patches;
  - one token per exogenous variable, a linear map of its whole look-back window, with no position embedding;
    time-mark channels become further variate tokens;
  - each block: self-attention over [patches, global] (residual, LayerNorm), cross-attention with the global token
    as the only query and the exogenous tokens as keys and values (residual, LayerNorm), then a position-wise
    feed-forward network on all endogenous tokens (residual, LayerNorm); a final LayerNorm;
  - a flatten head: one linear map from all endogenous tokens to the outputs.
Adapted to the common interface of guide §3.7 (the same for every learned index forecaster):
  - endogenous = the campus index k over the last 4 h, in 4 patches of 1 h, each patch's values and validity flags;
  - exogenous variate tokens = the donors (each donor's implied index, clip and validity flags over 4 h, and its
    static features: the inputs PVSetFormer receives), with offline donors masked, plus the fleet-summary channels
    (sigma, c, n) and the 7 sun-geometry channels at the patch ends;
  - the output is 9 monotone quantiles per horizon on the change from persistence (D34), from the flatten head plus
    a per-horizon linear map of the horizon query (future geometry, index one day earlier), zero-initialised so that
    training starts at persistence. TimeXer's instance normalisation is replaced by this persistence anchor (the
    index is already a normalised quantity), and the output dropout is dropped (it would perturb the quantiles).
Training, early stopping, the refit and the calibration predictions are setformer's (same code path).
"""
from __future__ import annotations

import math

from . import forecast as FC
from .setformer import F_CLIM, F_FLEET, F_FM, F_GEO, F_PATCH, F_Q, F_STATIC, NP, PATCH

N_MARK = 3 + F_GEO                                  # sigma, c, n and 7 geometry channels as variate tokens
F_DONOR = NP * F_PATCH + F_STATIC                   # a donor's whole look-back window and its static features


def build_timexer(cfg: dict):
    import torch
    import torch.nn as nn
    import torch.nn.functional as Fn

    class Block(nn.Module):
        def __init__(self, d, heads, dropout):
            super().__init__()
            self.sa = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
            self.ca = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
            self.ff1, self.ff2 = nn.Linear(d, 2 * d), nn.Linear(2 * d, d)
            self.n1, self.n2, self.n3 = nn.LayerNorm(d), nn.LayerNorm(d), nn.LayerNorm(d)
            self.drop = nn.Dropout(dropout)

        def forward(self, x, exo, exo_pad):
            x = self.n1(x + self.drop(self.sa(x, x, x, need_weights=False)[0]))
            g = x[:, -1:]                                            # the global token is the only query
            g = self.n2(g + self.drop(self.ca(g, exo, exo, key_padding_mask=exo_pad, need_weights=False)[0]))
            x = torch.cat([x[:, :-1], g], 1)
            y = self.drop(self.ff2(self.drop(Fn.gelu(self.ff1(x)))))
            return self.n3(x + y)

    class TimeXer(nn.Module):
        def __init__(self, d, heads, n_enc, dropout, fm=0):
            super().__init__()
            self.lin = False                                         # PVSetFormer's option flag, off here
            self.fm = bool(fm)                                       # D72 ablation: Chronos-2's quantiles at t + h
            self.patch_in = nn.Linear(2 * PATCH, d, bias=False)      # patch values and validity flags
            pe = torch.zeros(NP, d)
            pos = torch.arange(NP, dtype=torch.float32)[:, None]
            div = torch.exp(torch.arange(0, d, 2, dtype=torch.float32) * (-math.log(10000.0) / d))
            pe[:, 0::2], pe[:, 1::2] = torch.sin(pos * div), torch.cos(pos * div)
            self.register_buffer("pe", pe)
            self.glb = nn.Parameter(torch.randn(1, 1, d))
            self.donor_in = nn.Linear(F_DONOR, d)                    # one variate token per donor
            self.mark_in = nn.Linear(NP, d)                          # one variate token per summary / geometry channel
            self.drop = nn.Dropout(dropout)
            self.blocks = nn.ModuleList([Block(d, heads, dropout) for _ in range(n_enc)])
            self.norm = nn.LayerNorm(d)
            self.head = nn.Linear(d * (NP + 1), len(FC.H) * 9)
            self.q_w = nn.Parameter(torch.zeros(len(FC.H), F_Q, 9))
            if self.fm:                                              # the same F_FM features as PVSetFormer's V15 rows
                self.fm_w = nn.Parameter(torch.zeros(len(FC.H), F_FM, 9))   # zero start, no weight decay (NO_DECAY)
            nn.init.zeros_(self.head.weight)
            with torch.no_grad():                                    # start at persistence with a narrow spread
                b = torch.zeros(len(FC.H), 9)
                b[:, 1:] = -3.0
                self.head.bias.copy_(b.reshape(-1))

        def forward(self, x, static, online, geo, q, anchor, fleet, return_aux=False):
            assert not return_aux, "TimeXer has no auxiliary output"
            B, n = x.shape[0], x.shape[1]
            en = self.patch_in(fleet[:, :, :2 * PATCH]) + self.pe[None]                     # (B, NP, d)
            en = self.drop(torch.cat([en, self.glb.expand(B, -1, -1)], 1))                 # (B, NP + 1, d)
            don = self.donor_in(torch.cat([x.reshape(B, n, -1), static[..., :F_STATIC]], -1))  # (B, n, d)
            marks = torch.cat([fleet[:, :, 2 * PATCH:F_FLEET], geo], -1).transpose(1, 2)   # (B, N_MARK, NP)
            exo = self.drop(torch.cat([don, self.mark_in(marks)], 1))
            pad = torch.cat([~online, torch.zeros(B, N_MARK, dtype=torch.bool, device=online.device)], 1)   # D80 ext.
            for blk in self.blocks:
                en = blk(en, exo, pad)
            o = self.head(self.norm(en).reshape(B, -1)).reshape(B, len(FC.H), 9)
            o = o + torch.einsum("bhf,hfo->bho", q[..., :F_Q], self.q_w)   # base query columns (V13's are extra)
            if self.fm:                                              # as PVSetFormer's lin_features: changes from k_t
                f0 = F_Q + F_CLIM
                ok = q[..., f0 + 9:f0 + 10]
                lf = torch.cat([(q[..., f0:f0 + 9] - anchor[:, None, None]) * ok, ok], -1)
                o = o + torch.einsum("bhf,hfo->bho", lf, self.fm_w)
            up =Fn.softplus(o[..., 1:5]).cumsum(-1)
            dn = Fn.softplus(o[..., 5:9]).cumsum(-1)
            qs = torch.cat([o[..., :1] - dn.flip(-1), o[..., :1], o[..., :1] + up], -1)
            return anchor[:, None, None] + qs                                              # change from persistence

    for k in ("lin", "aux", "summary_only", "vol", "vgate", "hmask", "hhead", "donor_id", "donor_rel", "ext", "vmed",
              "clim"):
        assert not cfg.get(k, 0), f"option {k} is PVSetFormer's, not TimeXer's"
    assert F_FLEET == 2 * PATCH + 3
    return TimeXer(cfg["d"], cfg["heads"], cfg["n_enc"], cfg["dropout"], cfg.get("fm", 0))
