"""Story 5.3: the gradual-attack policy sweep, its figure, table and trigger table."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import yaml

from depeg_sim.analysis.charts import plot_policy_comparison, policy_cells
from depeg_sim.experiments.sweep import expand, load_sweep, run_sweep, sweep_spec_hash

sys.path.insert(0, str(Path("scripts").resolve()))

import policy_table  # noqa: E402
import trigger_table  # noqa: E402

SPEC = Path("sweeps/policy-comparison-gradual-mc.yaml")
SPEC_HASH = "712e3cd96851a2c5636877a30bb92f4a80f22a1ec8e3fdd107c2c2cb7bd7d4a9"
ATK, PACE = "agents[type=attacker].capital", "agents[type=attacker].pace"
PACES = [0.1, 0.02, 0.01]


def test_spec_hash_is_pinned():
    assert sweep_spec_hash(SPEC) == SPEC_HASH


def test_spec_is_the_policy_sweep_plus_attacker_pace():
    gradual = yaml.safe_load(SPEC.read_text())
    original = yaml.safe_load(Path("sweeps/policy-comparison-mc.yaml").read_text())
    pace = gradual["axes"].pop(PACE)
    assert pace == PACES
    assert gradual.pop("name") == "policy-comparison-gradual-mc"
    original.pop("name")
    assert gradual == original
    cells = expand(load_sweep(SPEC))
    assert len(cells) == 5 * 3 * 3 * 16 == 720
    assert {c.axis_values[PACE] for c in cells} == set(PACES)


# figure from a synthetic sweep ---------------------------------------------------------


def _synthetic(sweep_dir: Path) -> None:
    """mc.parquet + sweep.parquet + manifest for the gradual spec; the trough step varies
    by seed at the slow paces, as it can under a gradual attack."""
    from depeg_sim.kernel.config import load_scenario

    spec = load_sweep(SPEC)
    base = load_scenario(Path("scenarios/calibrated-baseline.yaml"))
    base_cfg = base.model_dump(mode="json")
    base_cfg["termination"]["peg_recovered"]["reference"] = "oracle"
    seeds = list(range(1000, 1016))
    m = {
        "sweep_name": spec.name, "spec_hash": "0" * 64,
        "base_scenario_hash": base.content_hash(), "base_config": base_cfg,
        "axes": spec.manifest_axes(), "seeds": seeds, "max_steps": 18000,
    }  # fmt: skip
    (sweep_dir / "manifest.json").write_text(json.dumps(m))
    cells, runs = [], []
    for i, pol in enumerate(spec.base_axis.bases):
        for j, cap in enumerate(spec.axes[ATK]):
            for pace in PACES:
                none = pol in ("no-defense", "spread-only")
                cells.append({
                    "policy": pol, ATK: cap, PACE: pace, "n": 16,
                    "p_peg_recovered": 1.0 if pace == 0.1 and i == 2 else 0.0,
                    "discount_bps_hours_mean": 1e5 * (j + 1) / pace / 50,
                    "discount_bps_hours_p05": 0.9e5 * (j + 1) / pace / 50,
                    "discount_bps_hours_p95": 1.1e5 * (j + 1) / pace / 50,
                })  # fmt: skip
                for k, seed in enumerate(seeds):
                    runs.append({
                        "policy": pol, ATK: cap, PACE: pace, "seed": seed,
                        "step_of_max_depeg": 50 if pace == 0.1 else 300 + k,
                        "steps_to_first_band_entry": 3000.0 * (i + 1) if pace == 0.1 else np.nan,
                        "defender_spent": np.nan if none else 4e7,
                        "defender_bought_stable": np.nan if none else 1e8 * pace * 10,
                    })  # fmt: skip
    pd.DataFrame(cells).to_parquet(sweep_dir / "mc.parquet", index=False)
    pd.DataFrame(runs).to_parquet(sweep_dir / "sweep.parquet", index=False)


def test_policy_cells_per_run_median_and_never(tmp_path):
    _synthetic(tmp_path)
    cells = policy_cells(tmp_path, ["policy", ATK, PACE], 12)
    cells = cells.set_index(["policy", PACE]).sort_index()
    fast = cells.loc[("calibrated", 0.1)]
    assert fast["ttp_h"].tolist() == pytest.approx([(50 + 3000) * 12 / 3600] * 3)
    assert cells.loc[("calibrated", 0.01), "ttp_h"].isna().all()  # 0 of 16 re-enter
    assert (cells["n"] == 16).all()


def test_gradual_png_has_a_row_per_pace(tmp_path):
    _synthetic(tmp_path)
    png = plot_policy_comparison(tmp_path)
    assert png == tmp_path / "policy_comparison_gradual.png"
    assert png.stat().st_size > 50_000
    assert plt.imread(png).shape[:2] == (2250, 3000)  # 20 x (3 x 4.6 + 1.2) in at 150 dpi
    assert plt.get_fignums() == []


# table ---------------------------------------------------------------------------------


def test_winners_name_both_minimisers_and_whether_they_agree():
    df = pd.DataFrame(
        {
            "attacker_pace": [0.01] * 3 + [0.1] * 3,
            "ratio": [1.0] * 6,
            "policy": ["a", "b", "c"] * 2,
            "disc_bps_h": [3.0, 1.0, 2.0, 5.0, 4.0, 4.0],
            "ttp_h": [np.nan, np.nan, np.nan, 1.0, 2.0, 3.0],
        }
    )
    w = policy_table.winners(df).set_index("attacker_pace")
    assert w.loc[0.01, "min_discount"] == "b" and w.loc[0.01, "min_time_to_parity"] == "none"
    assert w.loc[0.01, "agree"] == "-"
    assert w.loc[0.1, "min_discount"] == "b=c" and w.loc[0.1, "min_time_to_parity"] == "a"
    assert w.loc[0.1, "agree"] == "no"


def test_policy_table_groups_by_pace(tmp_path):
    _synthetic(tmp_path)
    runs = pd.read_parquet(tmp_path / "sweep.parquet")
    runs = runs.assign(
        terminated_by="max_steps", holder_bought_stable=1.0, redemption_paid_total=2.0,
        arbitrageur_redeemed=2.0, discount_bps_hours=runs[PACE] * 1e3,
    )  # fmt: skip
    runs.to_parquet(tmp_path / "sweep.parquet", index=False)
    df = policy_table.table(tmp_path)
    assert len(df) == 45 and set(df["attacker_pace"]) == set(PACES)
    assert df.loc[df["attacker_pace"] == 0.01, "disc_bps_h"].tolist() == pytest.approx([10.0] * 15)
    row = df[(df["policy"] == "calibrated") & (df["attacker_pace"] == 0.1)].iloc[0]
    assert row["price_paid"] == pytest.approx(0.4)


# trigger table on a small real sweep -------------------------------------------------


def test_trigger_table_on_a_short_slow_sweep(tmp_path):
    data = yaml.safe_load(SPEC.read_text())
    data["axes"] = {ATK: [179454391], PACE: [0.01]}
    data["seeds"] = [1000]
    data["max_steps"] = 120
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(data))
    out = tmp_path / "output"
    run_sweep(load_sweep(spec_path), out, workers=1)
    ratio, rows = trigger_table.build(out, 0.01, 1.0, 1000, spec_path=spec_path)
    assert ratio == pytest.approx(1.0)
    by = {r["policy"]: r for r in rows}
    assert by["no-defense"]["binds_step"] is None and by["no-defense"]["trigger_pct"] is None
    assert by["spread-only"]["act"] == "spread"
    for pol in ("calibrated", "early-aggressive", "late-conservative"):
        r = by[pol]
        assert r["act"] == "buy" and r["binds_step"] == r["first_past_trigger"] == 51
        assert r["attacker_sold"] == pytest.approx(0.01)
    text = trigger_table.format_table(ratio, 0.01, 1000, rows)
    assert text.splitlines()[0] == "attacker pace 0.01, ratio 1, seed 1000"
