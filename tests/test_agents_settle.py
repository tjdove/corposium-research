"""AC 7: settle against real modules routed by a real Engine."""

import pytest
from agent_world import config

from depeg_sim.agents.arbitrageur import Arbitrageur
from depeg_sim.agents.attacker import Attacker
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.protocol.amm import ConstantProductAMM
from depeg_sim.protocol.redemption import RedemptionModule


def kinds(result, kind):
    return [e for e in result.events if e.kind == kind]


def test_attacker_sell_settles_from_swap_executed():
    ctx = RunContext.from_config(config(max_steps=1))
    amm = ConstantProductAMM(1_000_000.0, 1_000_000.0, fee_bps=30)
    atk = Attacker("atk", capital=10_000.0, start_step=0, pace=0.1)  # sells 1_000
    for sub in (amm, atk):
        ctx.registry.register(sub)
    result = Engine(ctx).run()

    (swap,) = kinds(result, "swap_executed")
    assert swap.payload["source"] == "atk"
    assert swap.payload["amount_in"] == 1_000.0
    assert atk.balances["stable"] == 10_000.0 - 1_000.0
    assert atk.balances["reference"] == swap.payload["amount_out"]
    assert atk.sold_total == 1_000.0
    assert atk.pnl_last == pytest.approx(atk.pnl(ctx))


def test_arbitrageur_redeem_settles_from_redeem_fulfilled():
    ctx = RunContext.from_config(config(max_steps=3))
    amm = ConstantProductAMM(1_000_000.0, 980_000.0, fee_bps=30)  # spot 0.98 < ppu 0.999
    red = RedemptionModule(reserves=500_000.0, spread_bps=10, capacity_per_step=400.0)
    arb = Arbitrageur("arb", capital=1.0, min_profit_bps=20, latency_steps=0)
    arb.balances["stable"] = 1_000.0  # no oracle registered: only the redeem route applies
    for sub in (amm, red, arb):
        ctx.registry.register(sub)
    result = Engine(ctx).run()

    (req,) = kinds(result, "redeem_requested")
    assert req.payload == {"source": "arb", "amount_stable": 1_000.0, "queue_depth": 1}
    fills = kinds(result, "redeem_fulfilled")
    assert [(e.step, e.payload["amount_stable"]) for e in fills] == [
        (0, 400.0),
        (1, 400.0),
        (2, 200.0),
    ]
    paid = sum(e.payload["paid_reference"] for e in fills)
    assert arb.balances["stable"] == pytest.approx(0.0, abs=1e-9)
    assert arb.balances["reference"] == pytest.approx(1.0 + paid)
    assert paid == pytest.approx(999.0)
    assert arb.queued_redeem == 0.0
    assert red.paid_total == pytest.approx(paid)
