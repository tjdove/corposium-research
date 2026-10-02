import pydantic
import pytest
from agent_world import config

from depeg_sim.agents.arbitrageur import Arbitrageur
from depeg_sim.agents.attacker import Attacker
from depeg_sim.agents.defender import Defender
from depeg_sim.agents.factory import build_agents
from depeg_sim.kernel.config import ScenarioConfig


def with_agents(agents):
    data = config().model_dump(mode="json")
    data["agents"] = agents
    return ScenarioConfig.model_validate(data)


def test_baseline_builds_three_agents_in_config_order():
    agents = build_agents(config())
    assert [type(a) for a in agents] == [Attacker, Arbitrageur, Defender]
    assert [a.name for a in agents] == ["attacker-1", "arb-1", "defender-1"]
    assert all(a.name == a.agent_id for a in agents)
    atk, arb, dfn = agents
    assert (atk.capital, atk.start_step, atk.pace, atk.stop_below_price) == (300_000, 50, 0.1, None)
    assert (arb.capital, arb.min_profit_bps, arb.latency_steps) == (200_000, 20, 1)
    assert (dfn.budget, dfn.threshold_pct, dfn.spend_pace) == (400_000, 1.0, 0.2)
    assert (dfn.spread_adjust_bps, dfn.max_spend) == (0, None)


def test_order_follows_config_not_type():
    cfg = with_agents(
        [
            {"type": "defender", "id": "d", "budget": 1, "threshold_pct": 1, "spend_pace": 0.5},
            {"type": "attacker", "id": "a", "capital": 1, "start_step": 0, "pace": 0.5},
            {"type": "defender", "id": "d2", "budget": 2, "threshold_pct": 1, "spend_pace": 0.5},
            {"type": "arbitrageur", "id": "r", "capital": 1, "min_profit_bps": 0},
        ]
    )
    assert [a.agent_id for a in build_agents(cfg)] == ["d", "a", "d2", "r"]


def test_peg_price_from_redemption_config():
    data = config().model_dump(mode="json")
    data["redemption"]["peg_price"] = 2.0
    agents = build_agents(ScenarioConfig.model_validate(data))
    assert all(a.peg_price == 2.0 for a in agents)
    assert agents[0].initial_value == 600_000.0


def test_no_agents():
    assert build_agents(with_agents([])) == []


def test_unknown_type_is_impossible_by_config():
    with pytest.raises(pydantic.ValidationError):
        with_agents([{"type": "whale", "id": "w", "capital": 1}])
