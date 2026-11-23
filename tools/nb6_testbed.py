"""NB6 hidden-unit test bed (D18): long-running inverters forecast as if new, after the protocol freeze.

    python tools/nb6_testbed.py --index                     # pseudo events, index without each group, gains, priors
    python tools/nb6_testbed.py --row nb5a|sources|main [--jobs 6] [--limit N]

D18, fixed before scoring: the mature units of results/nb2_panel/testbed.csv (NB2's prep.pseudo_testbed: 2022-04-01 in
the stable window and 2023-04-01 in the drifted window, 5 groups by station) start "as new" on their date.
- --index: for each date and group, a pseudo event whose donors are NB2's rule (prep.donors_at: started at least
  14 full days before, online in the 7 days before) without every unit of the group's stations. Its index, donor
  gains and fleet state come from NB3's code with the frozen part 1 (fleet.run_event: alternating gain fit before the
  date, censored index, k_min 0.3). Each hidden unit gets its prior from its own nameplate and the group's donor gains
  (fleet.event_priors; G2, or G0 for a metadata-error unit), and the sensor and satellite rows get NB4's refitted
  gains (sensor.external_gains). Writes results/nb6_testbed/ all-or-nothing.
- --row: the forecasts of the comparisons the test bed repeats (guide §4.4): NB5a's forecasters (A1 and the slots),
  the sensor rows A4 and A4b and the satellite row A9 (NB5d's code), and the main model (setformer.fit_predict with
  the frozen cfg and seeds, nb6_forecast.pvsf_task). One index forecast per date and group serves all its units; each
  unit is composed with its own prior at scoring. Parts under results/nb6_forecasts/parts/tb_<row>/, resumable.
No hidden unit's power is read here: the index and the forecasts use the donors only.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count()))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

import nb6_forecast as NF  # noqa: E402
from pvcold import audit as A_  # noqa: E402
from pvcold import config as C  # noqa: E402
from pvcold import fleet as F  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import prep as P  # noqa: E402
from pvcold import sensor as SN  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

TB = C.RESULTS / "nb6_testbed"
PARTS = NF.PARTS
SOURCES = NF.SOURCES


def build_index():
    fz, fz_hash, _ = NF.frozen()
    t0 = time.time()
    p1 = yaml.safe_load((ROOT / fz["files"]["part1_index_gains_prior"]["path"]).read_text())
    K_MIN, PRIOR = float(p1["gain_fit"]["k_min"]), p1["prior_variant"]
    assert p1["index_estimator"] == "censored"
    p = F.load_panel()
    del p["targets15_kW"]
    U = p["units"]
    ALT = json.loads((C.RESULTS / "nb1_audit" / "summary.json").read_text())["campus_altitude_m"]
    P15 = pd.read_parquet(C.RESULTS / "nb2_panel" / "P15_kW.parquet").set_index("time")
    tb = pd.read_csv(ROOT / fz["files"]["hidden_unit_testbed"]["path"])
    ev_rows, dn_rows = [], []
    for (d, g), z in tb.groupby(["date", "group"]):
        d = pd.Timestamp(d)
        own = set(U.index[U.station.isin(set(z.station))])          # every unit of the group's stations
        dn = P.donors_at(d, U, own, P15)
        assert len(dn) >= C.MIN_DONORS and not (set(dn) & own), (d, g)
        gname = f"TB {d.date()} g{g}"
        first = U.loc[z.unit.iloc[0]]
        ev_rows.append({"event": gname, "level": "group", "group": g, "date": d.date(), "set": "testbed", "start": d,
                        "units": "+".join(z.unit), "n_donors": len(dn), "tilt": first.tilt,
                        "azimuth_brick": first.azimuth_brick, "DC_AC": first.DC_AC,
                        "in_prior_test": bool(first.in_prior_test)})
        dn_rows += [{"event": gname, "donor": x} for x in dn]
        for u in z.unit:
            r = U.loc[u]
            uname = f"TB {d.date()} {u}"
            ev_rows.append({"event": uname, "level": "unit", "group": g, "date": d.date(), "set": "testbed", "start": d,
                            "units": u, "n_donors": len(dn), "tilt": r.tilt, "azimuth_brick": r.azimuth_brick,
                            "DC_AC": r.DC_AC, "in_prior_test": bool(r.in_prior_test), "group_event": gname})
            dn_rows += [{"event": uname, "donor": x} for x in dn]
    PE, PD = pd.DataFrame(ev_rows), pd.DataFrame(dn_rows)
    p2 = dict(p)
    p2["events"] = PE.copy()
    p2["donors"] = PD.copy()
    idx = {k: {} for k in ["k_cens", "sigma", "c", "n"]}
    gains, priors, Tcache = [], [], {}
    for gname in PE[PE.level == "group"].event:
        t1 = time.time()
        a = F.event_arrays(gname, p2)
        r = F.run_event(a, K_MIN, censored=True)
        for k in idx:
            idx[k][gname] = pd.Series(r[k], index=a["t"])
        gains += [{"event": gname, "donor": dd, "gain": float(gg)} for dd, gg in r["g"].items()]
        for uname in PE[(PE.level == "unit") & (PE.group_event == gname)].event:
            au = F.event_arrays(uname, p2)
            assert au["dn"] == a["dn"] and au["t"].equals(a["t"])
            pr, _, _, _ = F.event_priors(au, r["g"], U, ALT, Tcache)
            used = PRIOR if pr["target_in_prior_test"] else "G0"
            priors.append({"event": uname, "group_event": gname, "prior_used": used, "prior_gain": pr[used],
                           **{k: pr[k] for k in ["G0", "G1", "G2", "r_new", "T_new", "n_meta_donors"]},
                           "B_q10": float(np.quantile(pr["B_" + PRIOR], 0.1)),
                           "B_q90": float(np.quantile(pr["B_" + PRIOR], 0.9))})
        print(f"{gname}: {len(a['dn'])} donors, index in {time.time() - t1:.0f} s, gain change {r['change']:.2e}", flush=True)
    G, PR = pd.DataFrame(gains), pd.DataFrame(priors)
    K15 = pd.read_parquet(C.RESULTS / "nb4_sensor" / "index15.parquet").set_index("time")
    grp = PE[PE.level == "group"].set_index("event")
    D = PD[PD.event.isin(grp.index)].assign(start=lambda x: x.event.map(grp["start"]))
    ends = D.groupby("donor")["start"].apply(lambda s: sorted(set(s))).to_dict()
    gx = []
    for src in SOURCES:
        g = SN.external_gains(p, K15["k_" + src], K_MIN, ends)
        gx.append(D.merge(g, on=["donor", "start"], how="left").assign(source=src))
    GX = pd.concat(gx, ignore_index=True)[["event", "source", "donor", "gain", "n_points"]]
    full = p["y15"].index
    par = {k: pd.DataFrame(v).reindex(full).reset_index(names="time") for k, v in idx.items()}
    summary = {"tool": "nb6_testbed --index", "decision": "D79 (D18)", "environment": A_.versions(),
               "frozen_config_sha256": fz_hash, "k_min": K_MIN, "prior_variant": PRIOR,
               "groups": int((PE.level == "group").sum()), "units": int((PE.level == "unit").sum()),
               "donors_by_group": grp["n_donors"].to_dict(), "runtime_s": round(time.time() - t0, 1)}
    out = A_.write_outputs("nb6_testbed", {"pseudo_events": PE, "donors": PD, "gains": G, "priors": PR,
                                           "gains_external": GX}, summary, parquet=par)
    print(PR.groupby("prior_used").size().to_dict(), "| written to", out)


class TBInputs(NF.Inputs):
    """The test bed's pseudo events in place of the real ones (group level: one index per date and group)."""

    def __init__(self):
        p = F.load_panel()
        del p["targets15_kW"]
        self.p = p
        pe = pd.read_csv(TB / "pseudo_events.csv", parse_dates=["start"])
        self.E = pe[pe.level == "group"].set_index("event")
        self.EVENTS = self.E.index.tolist()
        self.geo15 = p["geometry15"]
        self.idx = {k: pd.read_parquet(TB / f"{k}.parquet").set_index("time") for k in ["k_cens", "sigma", "c", "n"]}
        self.gains3 = pd.read_csv(TB / "gains.csv")
        self.K15 = pd.read_parquet(C.RESULTS / "nb4_sensor" / "index15.parquet").set_index("time")


def nb5a_task(v, S, o, e, params):
    _, _, rows, _ = FC.origin_task(v, S, o, e, params)
    assert len(rows), f"{v}, {o}: NB5a's forecasters produced nothing"
    rows.insert(2, "seed", int(C.SEED))
    NF.write_atomic(rows, NF.part_path("tb_nb5a", v, o, C.SEED))
    return len(rows)


def source_task(v, Ss, S, src, o, e, params):
    f, _ = FC.run_origin_source(Ss, S, o, e, params, SOURCES[src])
    f.insert(0, "origin", o); f.insert(0, "source", src); f.insert(0, "event", v); f.insert(3, "seed", int(C.SEED))
    NF.write_atomic(f, PARTS / "tb_sources" / f"{v.replace(' ', '_')}__{o:%Y%m%d}__{src}.parquet")
    return len(f)


def run_row(row, jobs, limit):
    from joblib import Parallel, delayed
    if row == "main" and os.environ.get("PVSF_CPU_ROWS") != "1":      # D80: tb_main runs on the Colab GPU
        print("tb_main: trained on the Colab GPU (D80, tools/nb6_gpu.py); not run here", flush=True)
        return
    fz, fz_hash, params = NF.frozen()
    I = TBInputs()
    t0 = time.time()
    if row == "nb5a":
        tasks = [(v, o, e) for v in I.EVENTS for o, e in I.origins(v)
                 if not NF.part_path("tb_nb5a", v, o, C.SEED).exists()][:limit]
        S = {v: I.series(v) for v in {t[0] for t in tasks}}
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(nb5a_task)(v, S[v], o, e, params) for v, o, e in tasks)
    elif row == "sources":
        tasks = []
        for v in I.EVENTS:
            S = I.series(v)
            for src in SOURCES:
                Ss = S.copy()
                Ss["k"] = I.K15["k_" + src].reindex(S.index).astype(float).to_numpy()
                Ss[["sigma", "c", "n"]] = np.nan
                for o, e in I.origins(v):
                    if not (PARTS / "tb_sources" / f"{v.replace(' ', '_')}__{o:%Y%m%d}__{src}.parquet").exists():
                        tasks.append((v, Ss, S, src, o, e))
        tasks = tasks[:limit]
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(source_task)(v, Ss, S, src, o, e, params)
                                               for v, Ss, S, src, o, e in tasks)
    else:
        assert row == "main"
        cfg = NF.pvsf_cfg(fz, "main")
        seeds = fz["test_rows"]["main"]["seeds"]
        tasks = [(v, o, e, sd) for v in I.EVENTS for o, e in I.origins(v) for sd in seeds
                 if not NF.part_path("tb_main", v, o, sd, "meta").with_suffix(".json").exists()]
        tasks.sort(key=lambda t: -NF.cost(I, t[0], t[1]))
        tasks = tasks[:limit]
        arrays = {v: SF.event_arrays(v, I.p, I.series(v), I.gains3[I.gains3.event == v].set_index("donor")["gain"])
                  for v in {t[0] for t in tasks}}
        print(f"tb_main: {len(tasks)} trainings to run", flush=True)
        res = Parallel(n_jobs=jobs, verbose=5)(delayed(NF.pvsf_task)("tb_main", v, arrays[v], o, e, cfg, sd)
                                               for v, o, e, sd in tasks)
    print(f"tb_{row}: {len(res)} tasks in {time.time() - t0:.0f} s | frozen {fz_hash[:16]}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--row", choices=["nb5a", "sources", "main"])
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    NF.git("merge-base", "--is-ancestor", "protocol-freeze", "HEAD")
    if a.index:
        build_index()
    else:
        assert a.row, "--index or --row"
        run_row(a.row, a.jobs, a.limit)


if __name__ == "__main__":
    main()
