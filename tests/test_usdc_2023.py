"""Story 2.5: the USDC March-2023 replay scenario and its validation overlay."""

import hashlib
import json
from pathlib import Path

import pytest
from test_calibrated_scenarios import D_STAR

from depeg_sim.analysis.charts import plot_validation_overlay, validation_comparison
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import load_scenario

SCENARIO = Path("scenarios/usdc-2023.yaml")
SERIES = Path("data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv").resolve()
UNIX_0 = 1_678_406_400  # 2023-03-10 00:00 UTC, first row of the series


def step_at(unix: int) -> int:
    return (unix - UNIX_0) // 12


def test_validates_with_the_normative_timestamps():
    cfg = load_scenario(SCENARIO)
    atk, _, dfn = cfg.agents
    assert cfg.environment.price_series_path == SERIES
    assert cfg.environment.volatility_per_step == 0 and cfg.environment.shocks == []
    assert atk.start_step == step_at(1_678_503_600) == 8100  # 2023-03-10 22:00 ET
    sched = cfg.redemption.capacity_schedule
    assert [c.step for c in sched] == [step_at(1_678_712_400)] == [25500]  # 13 Mar 09:00 ET
    assert sched[0].capacity_per_step * 7200 == pytest.approx(cfg.redemption.reserves, rel=1e-6)
    assert cfg.steps.max_steps == step_at(1_678_809_600) == 33600  # 14 Mar 12:00 ET
    assert cfg.amm.reserve_stable == cfg.amm.reserve_reference == D_STAR
    assert (
        atk.capital == load_scenario(Path("scenarios/calibrated-baseline.yaml")).agents[0].capital
    )
    assert atk.pace == 0.002  # fitted by sweeps/usdc-2023-pace.yaml
    assert dfn.threshold_pct == 99.0  # defender never acts
    assert cfg.termination.peg_recovered is None


def test_hash_includes_the_csv():
    cfg = load_scenario(SCENARIO)
    assert cfg.environment.price_series_sha256 == hashlib.sha256(SERIES.read_bytes()).hexdigest()
    assert cfg.content_hash()[:12] == "73db527c8ddf"


def tiny(tmp_path, max_steps=500):
    cfg = set_path(load_scenario(SCENARIO), "steps.max_steps", max_steps)
    cfg = set_path(cfg, "metrics.checkpoint_every", None)
    return run_scenario(cfg, output_dir=tmp_path, chart=False)


def test_short_run_completes(tmp_path):
    art = tiny(tmp_path)
    assert art.summary["steps_run"] == 500 and art.summary["terminated_by"] == "max_steps"
    m = json.loads((art.run_dir / "manifest.json").read_text())
    assert m["config"]["environment"]["price_series_path"] == str(SERIES)
    assert m["price_series_sha256"] == hashlib.sha256(SERIES.read_bytes()).hexdigest()


def test_overlay_png_on_a_tiny_run(tmp_path):
    art = tiny(tmp_path, max_steps=8400)  # past the attack start at 8100
    png = plot_validation_overlay(art.run_dir)
    assert png == art.run_dir / "validation_overlay.png"
    assert png.stat().st_size > 20_000
    cmp = validation_comparison(art.run_dir)
    assert cmp["observed_trough_bps"] == pytest.approx(-1373.3)
    assert cmp["observed_trough_h"] == 31.0
    assert cmp["attack_start_h"] == 27.0 and cmp["capacity_change_h"] == 85.0
