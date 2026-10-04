"""Story 2.4: the 1992 analogue scenarios (Black Wednesday as ratios)."""

import math
import re
from pathlib import Path

import pytest
import yaml
from test_calibrated_scenarios import D_STAR, leaf_paths

from depeg_sim.experiments.runner import build_world
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine

DEFENDED = "scenarios/soros-1992.yaml"
NO_DEFENSE = "scenarios/soros-1992-no-defense.yaml"
SCENARIOS = (DEFENDED, NO_DEFENSE)
DAY = 7_200
STATUS = re.compile(r"\b(verified|secondary|assumption)\b")


def parts(path):
    cfg = load_scenario(Path(path))
    atk, arb, dfn, _ = cfg.agents
    return cfg, atk, arb, dfn


@pytest.mark.parametrize("path", SCENARIOS)
def test_validates_and_shares_d_star(path):
    cfg, atk, arb, dfn = parts(path)
    assert [a.type for a in cfg.agents] == ["attacker", "arbitrageur", "defender", "holder"]
    assert cfg.amm.reserve_stable == cfg.amm.reserve_reference == D_STAR
    assert cfg.steps.interval_seconds == 12 and cfg.steps.max_steps == 2 * DAY
    assert atk.start_step == 600
    assert cfg.environment.shocks[0].step == atk.start_step - 600
    assert cfg.environment.shocks[0].pct == -1.0
    assert math.isclose((1 - atk.pace) ** DAY, 0.1, rel_tol=1e-3)  # ~90% sold in a day
    assert math.isclose(
        cfg.redemption.capacity_per_step * DAY, cfg.redemption.reserves, rel_tol=1e-6
    )
    assert cfg.termination.reserves_exhausted
    assert atk.start_step < cfg.termination.peg_recovered.for_steps  # ADR-0010


def test_defended_ratios():
    cfg, atk, _, dfn = parts(DEFENDED)
    assert dfn.budget == cfg.redemption.reserves == dfn.max_spend  # 50:50 split
    assert 1.2 <= atk.capital / (dfn.budget + cfg.redemption.reserves) <= 1.5
    assert (dfn.threshold_pct, dfn.spend_pace, dfn.spread_adjust_bps) == (1.0, 0.2, 200)


def test_no_defense_differs_only_in_budget_and_spread():
    a, b = (load_scenario(Path(p)).model_dump(mode="json") for p in SCENARIOS)
    assert b["agents"][2]["budget"] == 1 and b["agents"][2]["spread_adjust_bps"] == 0
    for d in (a, b):
        d.pop("name")
        d["agents"][2].pop("budget")
        d["agents"][2].pop("spread_adjust_bps")
    assert a == b


def test_content_hashes_are_pinned():
    assert [load_scenario(Path(p)).content_hash()[:12] for p in SCENARIOS] == [
        "f4e26ae66440",  # Story 2.6: + holder (329eda7c2118 without it)
        "516edaef4795",  # Story 2.6: + holder (1badaed6cf4a without it)
    ]


@pytest.mark.parametrize("path", SCENARIOS)
def test_short_run_completes(path):
    cfg = set_path(load_scenario(Path(path)), "steps.max_steps", 500)
    cfg = set_path(cfg, "metrics.checkpoint_every", None)
    ctx = RunContext.from_config(cfg)
    build_world(cfg, ctx)
    result = Engine(ctx).run()
    assert result.steps_run == 500  # the attack starts at 600
    assert result.terminated_by == "max_steps"


def header_lines(path):
    header = Path(path).read_text(encoding="utf-8").split("\nversion:")[0]
    return [line for line in header.splitlines() if line.startswith("# - ")]


@pytest.mark.parametrize("path", SCENARIOS)
def test_every_parameter_line_has_a_status(path):
    lines = header_lines(path)
    assert lines
    for line in lines:
        assert STATUS.search(line), line


@pytest.mark.parametrize("path", SCENARIOS)
def test_every_parameter_has_a_header_line(path):
    named = {line[4:].split()[0] for line in header_lines(path)}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    params = [p for p in leaf_paths(data) if p.split(".")[0] not in {"version", "name", "assets"}]
    assert [p for p in params if p not in named] == []
