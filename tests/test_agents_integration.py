"""AC 10: the baseline scenario's modules and three agents in a real Engine, 300 steps.

Pinned to the pre-retune ``peg_recovered.tolerance`` of 0.001 (10 bps). Story 1.8
retuned the baseline YAML to 0.006 (ADR-0010 option 1); this test keeps the original
setting so it continues to document the ADR-0010 dead zone.

Registration order (the order Story 1.8 will use): environment, oracle, amm,
redemption, then agents in config order.
"""

from collections import Counter

from agent_world import config

from depeg_sim.agents.factory import build_agents
from depeg_sim.environment.price_process import ReferencePrice
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.scheduler import Phase
from depeg_sim.protocol.amm import ConstantProductAMM
from depeg_sim.protocol.oracle import Oracle
from depeg_sim.protocol.redemption import RedemptionModule

STEPS = 300
PRE_RETUNE_TOLERANCE = 0.001  # ADR-0010: inside the 50 bps arbitrage band


def build():
    cfg = config(max_steps=STEPS, tolerance=PRE_RETUNE_TOLERANCE)
    assert cfg.termination.reserves_exhausted and cfg.termination.peg_recovered is not None
    ctx = RunContext.from_config(cfg)
    env = ReferencePrice.from_config(cfg.environment)
    oracle = Oracle.from_config(cfg.oracle, source=env)
    amm = ConstantProductAMM.from_config(cfg.amm, peg_price=cfg.redemption.peg_price)
    red = RedemptionModule.from_config(cfg.redemption)
    agents = build_agents(cfg)
    for sub in (env, oracle, amm, red, *agents):
        ctx.registry.register(sub)
    return ctx, amm, red, {a.agent_id: a for a in agents}


def test_baseline_300_steps():
    ctx, amm, red, agents = build()
    atk, arb, dfn = agents["attacker-1"], agents["arb-1"], agents["defender-1"]
    stable_by_step = {}

    class Watch:
        """Records the attacker's settled stable balance each step (after METRIC_UPDATE)."""

        name = "watch"
        phases = frozenset({Phase.PERSISTENCE})

        def on_phase(self, ctx, phase):
            stable_by_step[ctx.clock.step_index] = atk.balances["stable"]

        def snapshot(self):
            return {}

    ctx.registry.register(Watch())
    result = Engine(ctx).run()

    # Which termination fires by step 300?
    #
    # reserves_exhausted: needs reserves gone with redemptions still queued. Only the
    #   arbitrageur redeems, and only stable it bought on the AMM below the band. It can
    #   only buy while spot < oracle * 0.995, and each buy lifts spot back up. So what it
    #   can buy, and then redeem, is roughly bounded by the stable the attacker dumps that the
    #   defender doesn't absorb first: at most the attacker's 300k. Paying that out costs
    #   at most 300k * 0.999 < 500k reserves. Not possible.
    # peg_recovered: needs |peg_deviation| <= 0.1% for 100 consecutive steps. Before the
    #   attack (steps 0-49) the pool sits at peg, but that is only 50 steps. After it, the
    #   attacker's first dump (30k into a 1M/1M pool) takes spot to ~0.943. The defender
    #   (1% threshold) and the arbitrageur (band = fee 30 + min profit 20 = 50 bps vs the
    #   oracle at 1.0) buy it back. The attacker's sells decay as 0.9^n, so by about step
    #   120 they are tiny. Then neither restoring force acts inside the band: the defender
    #   only acts below -1%, and the arbitrageur only below -0.5%. Nothing pulls spot from
    #   ~-0.2% to within the 0.1% tolerance. The run ends parked at ~0.998, outside it.
    # max_steps: therefore the 300-step cap fires.
    assert result.terminated_by == "max_steps"
    assert result.steps_run == STEPS
    assert not red.reserves_exhausted
    assert -0.005 < amm.peg_deviation < -0.001  # parked inside the arb band, outside tolerance

    start = atk.start_step
    assert all(stable_by_step[s] == atk.capital for s in range(start))
    after = [stable_by_step[s] for s in range(start, STEPS)]
    assert all(b < a for a, b in zip([atk.capital, *after], after, strict=False))

    by_rule = Counter((d.agent_id, d.rule) for d in result.decisions)
    assert by_rule[("defender-1", "defend_buy")] >= 1
    arb_active = {"arb_buy_amm", "arb_sell_amm", "arb_redeem"}
    assert (
        sum(n for (aid, rule), n in by_rule.items() if aid == "arb-1" and rule in arb_active) >= 1
    )

    # AC 9 in a real engine: trace on in the baseline -> one record per agent per step.
    assert len(result.decisions) == STEPS * 3
    assert dfn.spent > 0 and dfn.interventions == by_rule[("defender-1", "defend_buy")]
    assert arb.snapshot()["type"] == "arbitrageur"


def test_repeat_run_is_identical():
    r1 = Engine(build()[0]).run()
    r2 = Engine(build()[0]).run()
    assert r1.events == r2.events
    assert r1.decisions == r2.decisions
    assert (r1.steps_run, r1.terminated_by) == (r2.steps_run, r2.terminated_by)
