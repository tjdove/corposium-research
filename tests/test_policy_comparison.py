"""Story 3.2: policy scenarios, the sweep's base axis, the policy chart."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import yaml

from depeg_sim.analysis.charts import _price_paid, plot_policy_comparison
from depeg_sim.experiments.mc import aggregate_mc
from depeg_sim.experiments.sweep import (
    SweepSpec,
    SweepSpecError,
    expand,
    load_sweep,
    run_sweep,
    sweep_spec_hash,
)
from depeg_sim.kernel.config import load_scenario

CALIBRATED = "scenarios/calibrated-baseline.yaml"
SPEC = "sweeps/policy-comparison-mc.yaml"
ATK = "agents[type=attacker].capital"
POLICIES = {
    "early-aggressive": {"threshold_pct": 0.5, "spend_pace": 0.5},
    "late-conservative": {"threshold_pct": 2.0, "spend_pace": 0.1},
    "spread-only": {"buy": False, "spread_adjust_bps": 200, "threshold_pct": 1.0},
}


# AC 2: policy files differ from the calibrated baseline only in name + defender ------


def _without_defender(cfg) -> dict:
    d = cfg.model_dump(mode="json")
    d.pop("name")
    defender = [a for a in d["agents"] if a["type"] == "defender"]
    d["agents"] = [a for a in d["agents"] if a["type"] != "defender"]
    return d, defender


@pytest.mark.parametrize("policy", [*POLICIES, "no-defense"])
def test_policy_file_differs_only_in_the_defender_block(policy):
    base, (base_def,) = _without_defender(load_scenario(Path(CALIBRATED)))
    path = Path(f"scenarios/policies/{policy}.yaml")
    cfg = load_scenario(path)
    rest, defender = _without_defender(cfg)
    assert rest == base
    assert cfg.name == f"policy-{policy}"
    if policy == "no-defense":
        assert defender == []
    else:
        (d,) = defender
        changed = {k: v for k, v in d.items() if v != base_def[k]}
        assert changed == {k: v for k, v in POLICIES[policy].items() if v != base_def[k]}
    first = path.read_text().splitlines()[0]
    assert first.startswith(f"# Policy {policy}:")


# AC 3: the base axis ------------------------------------------------------------------


def test_policy_spec_expands_policy_first():
    spec = load_sweep(Path(SPEC))
    cells = expand(spec)
    assert len(cells) == 5 * 3 * 16
    labels = list(spec.base_axis.bases)
    assert labels == ["calibrated", *POLICIES, "no-defense"]
    for c in cells:
        pol = labels[c.index // 48]
        assert list(c.axis_values) == ["policy", ATK]
        assert c.axis_values["policy"] == pol
        assert c.config.termination.peg_recovered.reference == "oracle"
        assert c.config.steps.max_steps == 18000
        assert c.config.name == f"policy-comparison-mc/{c.index:04d}"
    nd = [c for c in cells if c.axis_values["policy"] == "no-defense"]
    assert all(not any(a.type == "defender" for a in c.config.agents) for c in nd)
    ratios = sorted({c.axis_values[ATK] / 179_454_391 for c in cells})
    assert ratios == pytest.approx([0.5, 0.7, 1.0], abs=1e-8)


def _spec(tmp_path, bases, **kw):
    data = {
        "version": 1,
        "name": "b",
        "base": "scenarios/soros-baseline.yaml",
        "base_axis": {"name": "policy", "bases": bases},
        "seeds": [42],
        "max_steps": 60,
    } | kw
    return SweepSpec.model_validate(data)


def test_base_must_be_one_of_the_bases_and_name_unique(tmp_path):
    with pytest.raises(SweepSpecError, match="must be one of base_axis.bases"):
        expand(_spec(tmp_path, {"v": "scenarios/soros-volatile.yaml"}))
    both = {"a": "scenarios/soros-baseline.yaml", "v": "scenarios/soros-volatile.yaml"}
    with pytest.raises(SweepSpecError, match="repeats"):
        expand(_spec(tmp_path, both, axes={"policy": [1]}))


def test_base_axis_run_manifest_and_mc(tmp_path):
    bases = {"a": "scenarios/soros-baseline.yaml", "v": "scenarios/soros-volatile.yaml"}
    s = _spec(tmp_path, bases, axes={ATK: [100_000, 300_000]})
    sweep_dir = run_sweep(s, tmp_path / "out", workers=1)
    df = pd.read_parquet(sweep_dir / "sweep.parquet")
    assert list(df.columns[:4]) == ["index", "seed", "policy", ATK]
    assert df["policy"].tolist() == ["a", "a", "v", "v"]
    hashes = {k: load_scenario(Path(v)).content_hash() for k, v in bases.items()}
    assert df.groupby("policy")["scenario_hash"].nunique().tolist() == [2, 2]
    m = json.loads((sweep_dir / "manifest.json").read_text())
    assert m["axes"][0] == {"name": "policy", "paths": [], "values": ["a", "v"], "bases": bases}
    assert m["base_hashes"] == hashes
    assert m["base_scenario_hash"] == hashes["a"]
    mc = pd.read_parquet(aggregate_mc(sweep_dir))
    assert list(mc.columns[:3]) == ["policy", ATK, "n"]
    assert len(mc) == 4


def test_spec_hash_follows_every_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("scenarios").mkdir()
    for f in ("soros-baseline.yaml", "soros-volatile.yaml"):
        Path("scenarios", f).write_text(
            (Path(__file__).parent.parent / "scenarios" / f).read_text()
        )
    data = {
        "version": 1,
        "name": "b",
        "base": "scenarios/soros-baseline.yaml",
        "base_axis": {"name": "p", "bases": {"a": "scenarios/soros-baseline.yaml",
                                             "v": "scenarios/soros-volatile.yaml"}},
        "seeds": [42],
    }  # fmt: skip
    Path("s.yaml").write_text(yaml.safe_dump(data))
    h0 = sweep_spec_hash(Path("s.yaml"))
    v = Path("scenarios/soros-volatile.yaml")
    v.write_text(v.read_text().replace("seed: ", "seed: 1", 1))
    assert sweep_spec_hash(Path("s.yaml")) != h0


# AC 4: chart from a synthetic mc.parquet + manifest ---------------------------------


def _synthetic(sweep_dir: Path) -> None:
    spec = load_sweep(Path(SPEC))
    base = load_scenario(Path(CALIBRATED)).model_copy()
    base_cfg = base.model_dump(mode="json")
    base_cfg["termination"]["peg_recovered"]["reference"] = "oracle"
    m = {
        "sweep_name": "policy-comparison-mc",
        "spec_hash": "0" * 64,
        "base_scenario_hash": base.content_hash(),
        "base_config": base_cfg,
        "axes": spec.manifest_axes(),
        "seeds": list(range(1000, 1016)),
        "max_steps": 18000,
    }
    (sweep_dir / "manifest.json").write_text(json.dumps(m))
    rows = []
    for i, pol in enumerate(spec.base_axis.bases):
        for j, cap in enumerate(spec.axes[ATK]):
            none = pol == "no-defense"
            entry_n = 4 if pol == "spread-only" and j == 2 else 16  # "never"
            rows.append({
                "policy": pol, ATK: cap, "n": 16,
                "step_of_max_depeg_p05": 50.0, "step_of_max_depeg_p50": 50.0,
                "step_of_max_depeg_p95": 50.0, "step_of_max_depeg_std": 0.0,
                "steps_to_first_band_entry_p50": 2000.0 * (i + 1) + 500 * j,
                "steps_to_first_band_entry_n": entry_n,
                "defender_spent_mean": np.nan if none else 4e7,
                "defender_spent_p05": np.nan if none else 3.9e7,
                "defender_spent_p95": np.nan if none else 4.1e7,
                "p_peg_recovered": 1.0 - 0.25 * j if i == 0 else 0.0,
            })  # fmt: skip
    pd.DataFrame(rows).to_parquet(sweep_dir / "mc.parquet", index=False)
    runs = []
    for i, pol in enumerate(spec.base_axis.bases):
        for cap in spec.axes[ATK]:
            for seed in m["seeds"]:
                spent = {"no-defense": np.nan, "spread-only": 0.0}.get(pol, 4e7)
                bought = {"no-defense": np.nan, "spread-only": 0.0}.get(pol, 1e8 / (i + 1))
                runs.append({"policy": pol, ATK: cap, "seed": seed, "defender_spent": spent,
                             "defender_bought_stable": bought})  # fmt: skip
    pd.DataFrame(runs).to_parquet(sweep_dir / "sweep.parquet", index=False)


def test_price_paid_per_run_and_never_buyers_have_none(tmp_path):
    _synthetic(tmp_path)
    paid = _price_paid(tmp_path, ["policy", ATK]).set_index("policy")
    assert paid.loc["calibrated", "paid_mean"].tolist() == [0.4] * 3
    assert paid.loc["early-aggressive", "paid_p95"].tolist() == pytest.approx([0.8] * 3)
    assert paid.loc[["spread-only", "no-defense"], "paid_mean"].isna().all()


def test_policy_comparison_png(tmp_path):
    _synthetic(tmp_path)
    png = plot_policy_comparison(tmp_path)
    assert png == tmp_path / "policy_comparison.png"
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (840, 2250)  # 15 x 5.6 in at 150 dpi
    assert plt.get_fignums() == []


def test_policy_comparison_needs_a_base_axis(tmp_path):
    _synthetic(tmp_path)
    m = json.loads((tmp_path / "manifest.json").read_text())
    m["axes"] = m["axes"][1:]
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="no base axis"):
        plot_policy_comparison(tmp_path)
