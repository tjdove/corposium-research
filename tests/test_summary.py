import json

import pandas as pd
import pytest
from test_metrics import cfg_with, run

from depeg_sim import __version__
from depeg_sim.analysis.summary import SUMMARY_KEYS, summarize
from depeg_sim.kernel.config import ScenarioConfig, load_scenario
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION

EXPECTED = [
    "scenario",
    "seed",
    "scenario_hash",
    "steps_run",
    "terminated_by",
    "max_depeg_bps",
    "step_of_max_depeg",
    "final_depeg_bps",
    "steps_to_first_band_entry",
    "steps_to_sustained_recovery",
    "reserves_exhausted",
    "redemption_paid_total",
    "defender_spent",
    "defender_interventions",
    "attacker_pnl",
    "arbitrageur_pnl",
    "defender_bought_stable",
    "holder_bought_stable",
    "holder_pnl",
    "phase_order_version",
    "package_version",
]


def summary_for(cfg):
    ctx, world, result, df = run(cfg)
    return summarize(cfg, result, df, world), world, df


def test_keys_exact_and_values():
    assert list(SUMMARY_KEYS) == EXPECTED
    cfg = cfg_with(max_steps=120)
    s, world, df = summary_for(cfg)
    assert list(s) == EXPECTED
    assert s["scenario"] == "soros-baseline"
    assert s["seed"] == 42
    assert s["scenario_hash"] == cfg.content_hash()
    assert s["steps_run"] == 120
    assert s["terminated_by"] == "max_steps"
    assert s["max_depeg_bps"] < 0
    assert s["max_depeg_bps"] == df["peg_deviation"].min() * 10_000
    assert s["step_of_max_depeg"] == 50
    assert s["final_depeg_bps"] == df["peg_deviation"].iloc[-1] * 10_000
    assert s["reserves_exhausted"] is False
    assert s["redemption_paid_total"] == world["redemption"].paid_total
    assert s["defender_spent"] == world["defender-1"].spent
    assert s["defender_interventions"] == world["defender-1"].interventions
    assert s["attacker_pnl"] == world["attacker-1"].pnl_last
    assert s["arbitrageur_pnl"] == world["arb-1"].pnl_last
    assert s["defender_bought_stable"] == world["defender-1"].bought_stable > 0
    assert s["holder_bought_stable"] is None and s["holder_pnl"] is None  # no holder
    assert s["phase_order_version"] == PHASE_ORDER_VERSION
    assert s["package_version"] == __version__
    json.dumps(s, allow_nan=False)  # strict JSON


def test_first_band_entry_counts_steps_from_trough():
    cfg = cfg_with(max_steps=120)  # tolerance 60 bps
    s, _, df = summary_for(cfg)
    dev = df.set_index("step")["peg_deviation"]
    first = next(st for st in dev.index if st > s["step_of_max_depeg"] and abs(dev[st]) <= 0.006)
    assert s["steps_to_first_band_entry"] == first - s["step_of_max_depeg"]
    assert s["terminated_by"] == "max_steps"
    assert s["steps_to_sustained_recovery"] is None


def test_recovery_null_when_never_within_tolerance():
    data = cfg_with(max_steps=120).model_dump(mode="json")
    data["termination"]["peg_recovered"]["tolerance"] = 1e-9
    cfg = ScenarioConfig.model_validate(data)
    s, _, _ = summary_for(cfg)
    assert s["steps_to_first_band_entry"] is None
    assert s["steps_to_sustained_recovery"] is None


def test_recovery_null_without_peg_recovered():
    data = cfg_with(max_steps=60).model_dump(mode="json")
    data["termination"]["peg_recovered"] = None
    s, _, _ = summary_for(ScenarioConfig.model_validate(data))
    assert s["steps_to_first_band_entry"] is None
    assert s["steps_to_sustained_recovery"] is None


def test_missing_agents_are_null():
    agents = [{"type": "attacker", "id": "a", "capital": 1_000, "start_step": 0, "pace": 0.1}]
    s, _, _ = summary_for(cfg_with(max_steps=10, agents=agents))
    assert s["defender_spent"] is None
    assert s["defender_interventions"] is None
    assert s["arbitrageur_pnl"] is None
    assert s["defender_bought_stable"] is None
    assert s["holder_bought_stable"] is None and s["holder_pnl"] is None
    assert s["attacker_pnl"] is not None


def test_empty_metrics_give_null_depeg():
    cfg = cfg_with(max_steps=5)
    _, world, result, _ = run(cfg)
    empty = pd.DataFrame({"step": [], "peg_deviation": []})
    s = summarize(cfg, result, empty, world)
    assert s["max_depeg_bps"] is None and s["final_depeg_bps"] is None
    assert s["step_of_max_depeg"] is None and s["steps_to_first_band_entry"] is None
    assert s["steps_to_sustained_recovery"] is None


def test_baseline_recovery_metrics():
    # The retuned baseline ends peg_recovered at step 192 (ADR-0013). The trough is at
    # step 50; the step-52 overshoot is the first band entry; the final in-band stretch
    # of for_steps = 100 started at step 92: 192 - 100 - 50 = 42.
    s, _, _ = summary_for(cfg_with(max_steps=5000))
    assert (s["terminated_by"], s["steps_run"], s["step_of_max_depeg"]) == (
        "peg_recovered",
        192,
        50,
    )
    assert s["steps_to_first_band_entry"] == 2
    assert s["steps_to_sustained_recovery"] == 42


# Story 2.7 AC 1: the three absorbed-stable fields -------------------------------------


def test_bought_stable_fields_on_calibrated_baseline():
    data = load_scenario("scenarios/calibrated-baseline.yaml").model_dump(mode="json")
    data["steps"]["max_steps"] = 300
    cfg = ScenarioConfig.model_validate(data)
    ctx, world, result, df = run(cfg)
    s = summarize(cfg, result, df, world)
    holder, defender = world["holder-1"], world["defender-1"]
    assert s["holder_bought_stable"] == holder.bought_stable > 0
    assert isinstance(s["holder_pnl"], float) and s["holder_pnl"] == holder.pnl_last
    # defender_bought_stable is the amount_out of the defender's executed buys
    outs = [
        e.payload["amount_out"]
        for e in result.events
        if e.kind == "swap_executed"
        and e.payload["source"] == "defender-1"
        and e.payload["side"] == "buy_stable"
    ]
    assert outs and s["defender_bought_stable"] == pytest.approx(sum(outs), rel=1e-12)
    assert s["defender_bought_stable"] == defender.bought_stable
    json.dumps(s, allow_nan=False)
