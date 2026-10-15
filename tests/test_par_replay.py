"""Story 5.1: the USDC replay with nothing from the observed series fed in."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from depeg_sim.analysis.charts import plot_validation_overlay, validation_comparison
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import load_scenario

sys.path.insert(0, str(Path("scripts").resolve()))

import replay_table  # noqa: E402

S = Path("scenarios")
# content_hash() of each new scenario (AC 1, AC 2)
HASHES = {
    "usdc-2023-par": "7f3d0c583694faf0e37dc8e04582da02425288f8026a999bdc074a809848c21d",
    "usdc-2023-tranches-par": "32a610a514f2a5bc55a0beda895d7aa9a7cc12f87302e79b8262efa1f9bd3712",
    "usdc-2023-ou": "77fc93f2f784983b354075a5d09e4417f6e6a9acbd3931457adc54c501921769",
    "usdc-2023-tranches-ou": "b219b783b6a34363bd4308d3b2a54739829ef44cdde11b3a8dc9c280a385d280",
}
BASE = {
    "usdc-2023-par": "usdc-2023",
    "usdc-2023-ou": "usdc-2023",
    "usdc-2023-tranches-par": "usdc-2023-tranches",
    "usdc-2023-tranches-ou": "usdc-2023-tranches",
}
PAR_ENV = {"base_price": 1.0, "volatility_per_step": 0.0, "mean_reversion_per_step": 0.0}
OU_ENV = {"base_price": 1.0, "volatility_per_step": 3.086e-05, "mean_reversion_per_step": 0.001634}


@pytest.mark.parametrize("name", sorted(HASHES))
def test_scenario_hash_is_pinned(name):
    assert load_scenario(S / f"{name}.yaml").content_hash() == HASHES[name]


@pytest.mark.parametrize("name", sorted(HASHES))
def test_only_name_and_reference_differ_from_the_base(name):
    new = load_scenario(S / f"{name}.yaml").model_dump(mode="json")
    base = load_scenario(S / f"{BASE[name]}.yaml").model_dump(mode="json")
    assert new["name"] == name and new["seed"] == base["seed"] == 42
    env = new["environment"]
    assert env["price_series_path"] is None
    assert env["shocks"] == []
    want = PAR_ENV if name.endswith("-par") else OU_ENV
    assert {k: env[k] for k in want} == want
    for d in (new, base):
        del d["name"], d["environment"]
    assert new == base  # attacker, holder, arbitrageur, defender, capacity, max_steps


def test_ou_values_are_the_calibrated_ou_baseline():
    ou = load_scenario(S / "calibrated-baseline-ou.yaml").environment
    assert (ou.volatility_per_step, ou.mean_reversion_per_step) == (
        OU_ENV["volatility_per_step"],
        OU_ENV["mean_reversion_per_step"],
    )


def _short(name, tmp_path, max_steps=8400):
    cfg = set_path(load_scenario(S / f"{name}.yaml"), "steps.max_steps", max_steps)
    cfg = set_path(cfg, "metrics.checkpoint_every", None)
    return run_scenario(cfg, output_dir=tmp_path, chart=False)


def test_par_reference_is_constant_one(tmp_path):
    ts = pd.read_parquet(_short("usdc-2023-par", tmp_path, 9000).run_dir / "timeseries.parquet")
    assert (ts["reference_price"] == 1.0).all()
    assert (ts["oracle_price"] == 1.0).all()


def test_overlay_with_two_simulated_series(tmp_path):
    observed = _short("usdc-2023", tmp_path)
    par = _short("usdc-2023-par", tmp_path)
    png = plot_validation_overlay(observed.run_dir, par.run_dir)
    assert png == par.run_dir / "validation_overlay.png"
    assert not (observed.run_dir / "validation_overlay.png").exists()
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 1500)
    assert plt.get_fignums() == []
    cmp = validation_comparison(par.run_dir, observed_from=observed.run_dir)
    assert cmp["observed_trough_bps"] == pytest.approx(-1373.3)
    assert cmp["attack_start_h"] == 27.0 and cmp["capacity_change_h"] == 85.0
    with pytest.raises(ValueError, match="no environment.price_series_path"):
        validation_comparison(par.run_dir)


def test_replay_table_smoke_and_deterministic(tmp_path):
    rows = replay_table.build(tmp_path / "a", max_steps=8400)
    assert [r["label"] for r in rows[1:]] == [label for label, _ in replay_table.REPLAYS]
    obs = rows[0]
    assert obs["trough_bps"] == pytest.approx(-1373.3, abs=0.05) and obs["trough_h"] == 31.0
    assert obs["window_h"] == (27.0, 96.0)
    assert all(r["trough_step"] <= 8400 for r in rows[1:])
    again = replay_table.build(tmp_path / "b", max_steps=8400)
    assert rows == again
    text = replay_table.format_table(rows)
    assert text.splitlines()[2].startswith("observed (Bitstamp hourly close)")
    assert len(text.splitlines()) == 2 + 7
