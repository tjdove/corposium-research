"""Build agents from scenario config, in config order.

The config's discriminated union guarantees every entry is one of the four types,
so an unknown ``type`` cannot reach this function. Each agent's ``name`` is its
``id``; all are valued at ``redemption.peg_price``.
"""

from __future__ import annotations

from depeg_sim.agents.arbitrageur import Arbitrageur
from depeg_sim.agents.attacker import Attacker
from depeg_sim.agents.base import Agent
from depeg_sim.agents.defender import Defender
from depeg_sim.agents.holder import Holder
from depeg_sim.kernel.config import (
    ArbitrageurConfig,
    AttackerConfig,
    DefenderConfig,
    HolderConfig,
    ScenarioConfig,
)


def build_agents(config: ScenarioConfig) -> list[Agent]:
    peg = config.redemption.peg_price
    agents: list[Agent] = []
    for cfg in config.agents:
        match cfg:
            case AttackerConfig():
                agents.append(Attacker.from_config(cfg, peg_price=peg))
            case ArbitrageurConfig():
                agents.append(Arbitrageur.from_config(cfg, peg_price=peg))
            case DefenderConfig():
                agents.append(Defender.from_config(cfg, peg_price=peg))
            case HolderConfig():
                agents.append(Holder.from_config(cfg, peg_price=peg))
    return agents
