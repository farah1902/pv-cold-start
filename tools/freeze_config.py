"""The frozen configuration of the protocol (D21, D77, D78): one YAML that pins every setting the test run uses.

    python tools/freeze_config.py

Collects parts 1 and 2a-2e, the sensor settings, the event table and the hidden-unit test bed, the data manifest and
the research guide, each by path and sha256, and checks each against the hash its own notebook recorded. It also
writes out the settings of the test rows that are derived from part 2c (the main model, A6e, A4c, TimeXer), checks
that the validation runs of A6e and A4c with V12's setting (D78) used exactly those settings, and states the primary
test and the family of secondary tests (guide 4.4). Every pinned file must be tracked by git with no uncommitted
change, so the hashes describe committed content. Writes results/freeze/ (frozen_config.yaml, summary.json)
all-or-nothing; the sha256 of frozen_config.yaml is the frozen configuration hash that the tag `protocol-freeze`
carries. Development data only; no test event is read.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pvcold import audit as A  # noqa: E402

R = ROOT / "results"
FILES = {   # label: (path, decision)
    "part1_index_gains_prior": ("results/nb3_index/frozen_config_part1.yaml", "D31"),
    "sensor_and_satellite_sources": ("results/nb4_sensor/sensor_config.yaml", "D32"),
    "part2a_lightgbm": ("results/nb5a_dev/lgb_config_part2a.yaml", "D33, D34"),
    "part2b_conformal_rules_lightgbm_single": ("results/nb5a_conformal/conformal_config_part2b.yaml", "D35"),
    "part2b_conformal_lightgbm_5_seeds": ("results/nb5c_conformal_lgb/conformal_config_part2b_lgb5.yaml", "D64"),
    "part2b_conformal_pvsetformer": ("results/nb5c_conformal/conformal_config_part2b_pvsf.yaml", "D46, D74"),
    "part2c_rule_r1": ("results/nb5c_r1/r1_config_part2c.yaml", "D45, D74"),
    "part2d_foundation_models": ("results/nb5b_fm/fm_config_part2d.yaml", "D59"),
    "part2e_weighting_check": ("results/nb5c_weights/weight_config_part2e.yaml", "D73, D75"),
    "config_snapshot_nb0": ("results/nb0_setup/config_snapshot.yaml", "NB0"),
    "events": ("results/nb2_panel/events.csv", "D12-D14, D27"),
    "units": ("results/nb2_panel/units.csv", "NB2"),
    "donors": ("results/nb2_panel/donors.csv", "NB2"),
    "hidden_unit_testbed": ("results/nb2_panel/testbed.csv", "D18"),
    "data_manifest": ("data/MANIFEST_sha256.csv", "D15"),
    "research_guide": ("docs/research_guide.md", "D76"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def committed(rel: str):
    assert git("ls-files", rel) == rel, f"{rel} is not tracked by git"
    assert git("status", "--porcelain", "--", rel) == "", f"{rel} has uncommitted changes"


OFF = ("clim", "fm")   # switches added to the defaults after V12 (V13, V15); 0 = off, absent from part 2c


def validation_run(name: str, cfg: dict) -> dict:
    """A validation run of a test row (D78): its setting must be the row's, up to the switches that are off."""
    rel = f"results/nb5c_variants/{name}/summary.json"
    committed(rel)
    s = json.loads((ROOT / rel).read_text())
    run_cfg = {k: v for k, v in s["cfg"].items() if not (k in OFF and v == 0)}
    assert run_cfg == cfg, f"{name}: setting differs from the frozen row"
    return {"run": name, "n_seeds": s["seeds"], "summary_sha256": sha(ROOT / rel), "decision": "D78",
            "role": "validation check of the setting only; the test row uses the row's own seeds and ensemble"}


def main():
    assert Path(git("rev-parse", "--show-toplevel")).resolve() == ROOT.resolve(), "not the paper repository"
    pinned = {}
    for label, (rel, dec) in FILES.items():
        p = ROOT / rel
        assert p.exists(), rel
        committed(rel)
        pinned[label] = {"path": rel, "sha256": sha(p), "decision": dec}
    h = {k: v["sha256"] for k, v in pinned.items()}

    # each part against the hash its notebook or tool recorded
    assert h["part1_index_gains_prior"] == "cb671b7f67138e7e82eeece27241e60a37284fd124946ac72d42e9a2daa80252"  # D31
    assert h["part2a_lightgbm"] == json.loads((R / "nb5a_dev" / "summary.json").read_text())["lgb_config_sha256"]
    r1 = json.loads((R / "nb5c_r1" / "summary.json").read_text())
    assert h["part2c_rule_r1"] == r1["part2c_sha256"] and r1["pvsf_main"] and r1["final_variant"] == "V12_5s"
    cp = json.loads((R / "nb5c_conformal" / "summary.json").read_text())
    assert h["part2b_conformal_pvsetformer"] == cp["conformal_config_sha256"] and cp["part2c_sha256"] == h["part2c_rule_r1"]
    assert cp["kept"] is True
    cl = json.loads((R / "nb5c_conformal_lgb" / "summary.json").read_text())
    assert h["part2b_conformal_lightgbm_5_seeds"] == cl["conformal_config_sha256"]
    wc = json.loads((R / "nb5c_weights" / "summary.json").read_text())
    assert h["part2e_weighting_check"] == wc["part2e_sha256"]
    p2e = yaml.safe_load((ROOT / FILES["part2e_weighting_check"][0]).read_text(encoding="utf-8"))
    assert p2e["part2c_sha256"] == h["part2c_rule_r1"] and p2e["part2d_sha256"] == h["part2d_foundation_models"]
    p2c = yaml.safe_load((ROOT / FILES["part2c_rule_r1"][0]).read_text(encoding="utf-8"))
    p2d = yaml.safe_load((ROOT / FILES["part2d_foundation_models"][0]).read_text(encoding="utf-8"))
    tx = json.loads((R / "nb5c_variants" / "TX1_5s" / "summary.json").read_text())

    main_cfg = dict(p2c["pvsetformer_cfg"])
    SEEDS, ENS = list(p2c["seeds"]), p2c["ensemble"]   # part 2c: 5 seeds, mean of the sorted quantiles, sorted again
    assert len(SEEDS) == 5 and "sorted again" in ENS

    def pvsf_row(model: str, cfg: dict, **extra) -> dict:
        """A row built on the main model: part 2c's seeds and ensembling, written out explicitly (D78)."""
        return {"model": model, "cfg": cfg, "seeds": SEEDS, "ensemble": ENS, **extra}

    rows = {
        "main": {"model": "PVSetFormer", "variant": p2c["pvsetformer_variant"], "cfg": main_cfg,
                 "n_params": p2c["pvsetformer_n_params"], "seeds": SEEDS, "ensemble": ENS,
                 "intervals": "part2b_conformal_pvsetformer"},
        "LGB": {"model": "quantile LightGBM, 5-seed ensemble (D64)", "params": p2c["lgb_params"],
                "seeds": p2c["seeds"], "intervals": "part2b_conformal_lightgbm_5_seeds"},
        "A2": pvsf_row("main model with the median index (part 1 estimator 'median')", main_cfg),
        "A3": pvsf_row("main model with prior G0 (g = 1)", main_cfg),
        "A4": "LightGBM (part 2a) on the raw pyranometer index (D50, D51)",
        "A4b": "LightGBM (part 2a) on the corrected pyranometer index (D50, D51)",
        "A4c": pvsf_row("main model plus the corrected sensor index (D51, D56)", dict(main_cfg, ext="sensor_corr"),
                        validation_check=validation_run("A4c_V12", dict(main_cfg, ext="sensor_corr"))),
        "A6a": {"model": "Chronos-2, zero-shot", "setting": p2d["models"]["chronos2"]["setting"],
                "revision": p2d["models"]["chronos2"]["revision"]},
        "A6b": {"model": "TimesFM 2.5, zero-shot", "setting": p2d["models"]["timesfm25"]["setting"],
                "revision": p2d["models"]["timesfm25"]["revision"]},
        "A6c": "dropped before the freeze (TabPFN-TS, D73)",
        "A6d": {"model": "TimeXer, CVX setting (D49)", "cfg": tx["cfg"], "seeds": SEEDS, "ensemble": ENS},
        "A6e": pvsf_row("main model on the fleet summary only (rule R2)", dict(main_cfg, summary_only=1),
                        validation_check=validation_run("A6e_V12_5s", dict(main_cfg, summary_only=1))),
        "A9": "satellite (CAMS) clear-sky index persisted forward x prior gain (D51)",
        "weighting_check": {"rule": p2e["rule"], "weights": p2e["weights"], "reference_weight": p2e["reference_weight"]},
    }
    statistics = {   # guide 4.4 (the guide itself is pinned above); the family of secondary tests is D78's
        "primary": {"comparison": ["main", "A1"], "horizon_steps": 4,
                    "test": "one-sided exact Wilcoxon signed-rank on event-wise nRMSE differences, 13 scored events, "
                            "p < 0.05; the other five horizons secondary, with Holm"},
        "secondary_family": {
            "test": "two-sided exact Wilcoxon signed-rank at 1 h on the 13 scored events, Holm across the family; "
                    "Hodges-Lehmann effect sizes",
            "level": "two forecasters are level when their medians differ by less than 3% (guide 3.10)",
            "wording": {"below 3%, not significant after Holm": "level",
                        "below 3%, significant after Holm": "consistently lower, by less than 3%",
                        "from 3%": "the difference is named with its p-value"},
            "comparisons": [["LGB", "main"], ["A6a", "main"], ["A6b", "main"], ["A6d", "main"], ["A6e", "main"],
                            ["weighted PVSetFormer + Chronos-2", "A6a"], ["weighted TimeXer + Chronos-2", "A6a"],
                            ["weighted LightGBM + Chronos-2", "A6a"]]},
    }
    assert len(statistics["secondary_family"]["comparisons"]) == 8
    frozen = {"protocol": "protocol-freeze (D21, D77, D78)", "commit_parent": git("rev-parse", "HEAD"),
              "primary_horizon_steps": 4, "statistics": statistics, "files": pinned, "test_rows": rows}
    class NoAlias(yaml.SafeDumper):           # write repeated lists out in full, no anchors
        def ignore_aliases(self, data):
            return True
    TEXT = yaml.dump(frozen, Dumper=NoAlias, sort_keys=False, allow_unicode=True, width=120)
    HASH = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()
    summary = {"tool": "freeze_config", "decision": "D77, D78", "environment": A.versions(), "frozen_config_sha256": HASH,
               "n_files": len(pinned), "commit_parent": frozen["commit_parent"]}
    out = A.write_outputs("freeze", {}, summary, texts={"frozen_config.yaml": TEXT})
    print(TEXT)
    print("frozen configuration sha256:", HASH)
    print("written to", out)


if __name__ == "__main__":
    main()
