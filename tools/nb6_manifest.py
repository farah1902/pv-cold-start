"""NB6: the manifest of every test forecast, committed before any test score exists (D79).

    python tools/nb6_manifest.py            # assemble the parts, hash every file, write results/nb6_forecasts/manifest.json

Replaces `nb6_forecast.py --manifest` (which predates the hidden-unit test bed): it covers the 17 events' rows, the
test bed's rows and inputs, and the Colab files of A6a and A6b. For every row it checks the frozen seeds and that each
(event, origin, seed) has its part, concatenates the parts into results/nb6_forecasts/<name>.parquet, and records
path, sha256, rows and parts. It also records the sha256 of the inputs the forecasts were made from (the test bed's
index and gains, the foundation-model inputs), and the device of every PVSetFormer-family row (D80 extension: one
device per row; main, A2, A4c, A6e and tb_main on one device, the GPU only with a passed V12_5s gate; A6d on the GPU
only if the TX1_5s gate passed too). The scorer reads only files whose hashes match this manifest, and only
once the manifest is committed. All-or-nothing: the parquet files and the manifest are written only if every check
passes.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import pandas as pd  # noqa: E402

import nb6_forecast as NF  # noqa: E402
from pvcold import audit as A_  # noqa: E402
from pvcold import evaluate as EV  # noqa: E402

OUT, PARTS = NF.OUT, NF.PARTS
TBD = ROOT / "results" / "nb6_testbed"
# manifest name -> (part folder, calibration parts?, seeds row in the frozen configuration or None, event set)
ROWS = {"nb5a": ("nb5a", False, None, "events"), "LGB": ("LGB", False, "LGB", "events"),
        "LGB_cal": ("LGB", True, "LGB", "events"), "sources": ("sources", False, None, "events"),
        "main": ("main", False, "main", "events"), "main_cal": ("main", True, "main", "events"),
        "A2": ("A2", False, "main", "events"), "A4c": ("A4c", False, "A4c", "events"),
        "A6e": ("A6e", False, "A6e", "events"), "A6d": ("A6d", False, "A6d", "events"),
        "tb_nb5a": ("tb_nb5a", False, None, "testbed"), "tb_sources": ("tb_sources", False, None, "testbed"),
        "tb_main": ("tb_main", False, "main", "testbed"), "tb_main_cal": ("tb_main", True, "main", "testbed")}


def main():
    fz, fz_hash, _ = NF.frozen()
    NF.git("merge-base", "--is-ancestor", "protocol-freeze", "HEAD")
    E = NF.Inputs().EVENTS
    pe = pd.read_csv(TBD / "pseudo_events.csv")
    TBE = pe.loc[pe.level == "group", "event"].tolist()
    sets = {"events": E, "testbed": TBE}
    tmp = OUT / ".tmp_manifest"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    files, device = {}, {}
    for name, (folder, cal, seeds_row, evset) in ROWS.items():
        parts = sorted((PARTS / folder).glob("*.parquet"))
        parts = [x for x in parts if x.name.endswith("__cal.parquet") == cal]
        assert parts, f"{name}: no parts in {folder}"
        df = pd.concat([pd.read_parquet(x) for x in parts], ignore_index=True)
        evs = sets[evset]
        assert set(df.event) == set(evs), f"{name}: events differ ({set(evs) - set(df.event)} missing)"
        if seeds_row:
            seeds = fz["test_rows"][seeds_row]["seeds"]
            assert sorted(df.seed.unique().tolist()) == sorted(seeds), f"{name}: seeds"
            got = df.groupby(["event", "origin"])["seed"].nunique()
            assert len(got) == 3 * len(evs) and (got == len(seeds)).all(), f"{name}: missing (event, origin, seed)"
        if folder in NF.PVSF_ROWS or folder == "tb_main":     # every training finished (none skipped)
            metas = [json.loads(x.read_text()) for x in (PARTS / folder).glob("*__meta.json")]
            assert len(metas) == 3 * len(evs) * len(fz["test_rows"][seeds_row]["seeds"]), f"{name}: trainings"
            assert not any(m["skipped"] for m in metas), f"{name}: a training was skipped"
            devs = sorted({str(m.get("device", "cpu")) for m in metas})   # the CPU runner's metas name no device
            assert len(devs) == 1, f"{name}: trainings on more than one device {devs}"
            device[folder] = {"device": devs[0], "gpu": sorted({str(m["gpu"]) for m in metas if "gpu" in m}),
                              "code_sha256": sorted({m["code_sha256"] for m in metas if "code_sha256" in m})}
        path = tmp / f"{name}.parquet"
        df.to_parquet(path, index=False)
        files[name] = {"path": f"results/nb6_forecasts/{name}.parquet", "sha256": EV.sha256(path), "rows": int(len(df)),
                       "parts": len(parts)}
        print(f"{name}: {len(df)} rows from {len(parts)} parts", flush=True)
    # D80 extension: one device for the main model's rows; A6d on the GPU only if both gates passed (committed records)
    gates = {}
    for ref in ("V12_5s", "TX1_5s"):
        s = ROOT / "results" / f"nb6_gpu_gate_{ref}" / "summary.json"
        gates[ref] = json.loads(s.read_text())["passed"] if s.exists() else None
    fam = ["main", "A2", "A4c", "A6e", "tb_main"]
    fam_dev = {device[r]["device"] for r in fam}
    assert len(fam_dev) == 1, f"the main model's rows ran on different devices: { {r: device[r]['device'] for r in fam} }"
    on_gpu = fam_dev.pop().startswith("cuda")
    assert not on_gpu or gates["V12_5s"] is True, "GPU rows without a passed V12_5s gate in results/nb6_gpu_gate_V12_5s"
    assert on_gpu or gates["V12_5s"] is not True, "the V12_5s gate passed, yet the main model's rows ran on the CPU"
    a6d_gpu = on_gpu and gates["TX1_5s"] is True
    assert device["A6d"]["device"].startswith("cuda") == a6d_gpu, \
        f"A6d ran on {device['A6d']['device']}; the gates say {'GPU' if a6d_gpu else 'CPU'}"
    gpu_codes = {c for d in device.values() for c in d["code_sha256"]}
    assert len(gpu_codes) <= 1, f"the GPU rows ran more than one version of the code: {gpu_codes}"
    for row in ("A6a", "A6b"):                                 # the Colab files, checked as fetch_drive_runs did
        p = OUT / "fm" / f"{fz['test_rows'][row]['setting']}.parquet"
        assert p.exists(), f"{row}: {p.name} missing (run NB6_colab, then fetch_drive_runs.py --set nb6)"
        rec = json.loads(p.with_suffix(".json").read_text())
        assert rec["revision"] == fz["test_rows"][row]["revision"] and rec.get("revision_pinned"), f"{row}: revision"
        man_in = json.loads((OUT / "fm_inputs" / "inputs_manifest.json").read_text())["sha256"]
        assert rec["inputs_sha256"] == man_in and not rec.get("limit"), f"{row}: inputs or a smoke test"
        f = pd.read_parquet(p)
        assert set(f.event) == set(E) and len(f) == rec["n_rows"], f"{row}: events or rows"
        files[row] = {"path": p.relative_to(ROOT).as_posix(), "sha256": EV.sha256(p), "rows": int(len(f)),
                      "record_sha256": EV.sha256(p.with_suffix(".json"))}
    inputs = {x.relative_to(ROOT).as_posix(): EV.sha256(x) for x in
              sorted(TBD.glob("*.parquet")) + sorted(TBD.glob("*.csv")) + sorted((OUT / "fm_inputs").glob("*"))}
    man = {"tool": "nb6_manifest", "decision": "D79", "frozen_config_sha256": fz_hash, "commit": NF.git("rev-parse", "HEAD"),
           "events": E, "testbed_events": TBE, "environment": A_.versions(), "files": files, "inputs": inputs,
           "devices": device, "gpu_gates_passed": gates}
    for name in ROWS:                                          # all checks passed: move into place
        (tmp / f"{name}.parquet").replace(OUT / f"{name}.parquet")
        assert EV.sha256(OUT / f"{name}.parquet") == files[name]["sha256"]
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    shutil.rmtree(tmp)
    print(json.dumps({k: v["sha256"][:16] for k, v in files.items()}, indent=1))
    print("manifest written: commit results/nb6_forecasts/manifest.json before scoring")


if __name__ == "__main__":
    main()
