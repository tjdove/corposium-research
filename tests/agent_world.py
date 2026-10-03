"""Real protocol modules for agent unit tests, with phases invoked by hand.

``World.step(*agents)`` runs one step the way the engine would, in phase order,
without an ``Engine``: price source, oracle, agent observe, decide, route actions
(recording ``ctx.execution_results``), redemption settlement, agent settle, tick.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel_stubs import BASELINE, ScriptedPriceSource

from depeg_sim.kernel.config import ScenarioConfig, load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.interfaces import Action
from depeg_sim.kernel.scheduler import Phase
from depeg_sim.protocol.amm import ConstantProductAMM
from depeg_sim.protocol.oracle import Oracle
from depeg_sim.protocol.redemption import RedemptionModule


def config(
    *, trace: bool = True, max_steps: int = 100, tolerance: float | None = None
) -> ScenarioConfig:
    data = load_scenario(BASELINE).model_dump(mode="json")
    if tolerance is not None:
        data["termination"]["peg_recovered"]["tolerance"] = tolerance
    data["steps"]["max_steps"] = max_steps
    data["metrics"]["trace_decisions"] = trace
    data["metrics"]["checkpoint_every"] = None
    return ScenarioConfig.model_validate(data)


@dataclass
class World:
    ctx: RunContext
    source: ScriptedPriceSource
    oracle: Oracle
    amm: ConstantProductAMM
    redemption: RedemptionModule

    def set_spot(self, price: float, stable: float = 1_000_000.0) -> None:
        """Reset the pool to ``stable`` stable at spot ``price`` (test-only)."""
        self.amm.reserve_stable = stable
        self.amm.reserve_reference = stable * price

    def step(self, *agents) -> list[Action]:
        ctx = self.ctx
        ctx.action_queue.clear()
        ctx.execution_results.clear()
        self.source.on_phase(ctx, Phase.ENVIRONMENT_UPDATE)
        self.oracle.on_phase(ctx, Phase.ORACLE_UPDATE)
        for a in agents:
            a.on_phase(ctx, Phase.STATE_OBSERVATION)
        for a in agents:
            a.on_phase(ctx, Phase.AGENT_DECISION)
            ctx.action_queue.extend(a.decide(ctx))
        for action in ctx.action_queue:
            target = ctx.registry.get(action.target)
            ctx.execution_results.append((action, target.execute(ctx, action)))
        self.redemption.on_phase(ctx, Phase.PROTOCOL_EVENTS)
        for a in agents:
            a.on_phase(ctx, Phase.METRIC_UPDATE)
        actions = list(ctx.action_queue)
        ctx.clock.tick()
        return actions


def world(
    *,
    trace: bool = True,
    prices=(1.0,),
    fee_bps: int = 30,
    reserves: float = 500_000.0,
    spread_bps: int = 10,
    capacity: float = 25_000.0,
    heartbeat: int = 25,
    threshold_pct: float = 0.5,
) -> World:
    ctx = RunContext.from_config(config(trace=trace))
    source = ScriptedPriceSource(list(prices))
    oracle = Oracle(heartbeat_steps=heartbeat, deviation_threshold_pct=threshold_pct, source=source)
    amm = ConstantProductAMM(1_000_000.0, 1_000_000.0, fee_bps=fee_bps)
    red = RedemptionModule(reserves=reserves, spread_bps=spread_bps, capacity_per_step=capacity)
    for sub in (source, oracle, amm, red):
        ctx.registry.register(sub)
    return World(ctx, source, oracle, amm, red)


def decisions(w: World, agent_id: str | None = None):
    return [d for d in w.ctx.decisions.all() if agent_id is None or d.agent_id == agent_id]


def rules(w: World, agent_id: str | None = None) -> list[str]:
    return [d.rule for d in decisions(w, agent_id)]


def events_of(w: World, kind: str):
    return [e for e in w.ctx.events.all() if e.kind == kind]
