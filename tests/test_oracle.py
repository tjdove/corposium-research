import math

import pytest
from kernel_stubs import RecordingStub, ScriptedPriceSource, make_config

from depeg_sim.environment.price_process import ReferencePrice
from depeg_sim.kernel.config import OracleConfig
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import (
    ActionSource,
    ActionTarget,
    PegView,
    ReservesView,
    Subsystem,
)
from depeg_sim.kernel.scheduler import Phase
from depeg_sim.protocol.oracle import Oracle, PriceSource


class Probe(RecordingStub):
    """Records the oracle's staleness each step, after ORACLE_UPDATE."""

    def __init__(self, oracle):
        super().__init__("probe", phases={Phase.STATE_OBSERVATION})
        self.oracle = oracle
        self.staleness: list[int] = []

    def on_phase(self, ctx, phase):
        self.staleness.append(self.oracle.staleness_steps)


def run(prices, *, heartbeat=25, threshold=0.5, max_steps=100):
    src = ScriptedPriceSource(prices)
    oracle = Oracle(heartbeat_steps=heartbeat, deviation_threshold_pct=threshold, source=src)
    probe = Probe(oracle)
    ctx = RunContext.from_config(make_config(max_steps=max_steps))
    for sub in (src, oracle, probe):
        ctx.registry.register(sub)
    result = Engine(ctx).run()
    ups = [e for e in result.events if e.kind == "oracle_updated"]
    return oracle, probe, ups


def steps(ups):
    return [e.step for e in ups]


def reasons(ups):
    return [e.payload["reason"] for e in ups]


# AC 6 / 8 --------------------------------------------------------------------


def test_is_a_subsystem_on_oracle_update_only_and_not_a_peg_view():
    oracle = Oracle(25, 0.5, ScriptedPriceSource([1.0]))
    assert oracle.name == "oracle"
    assert oracle.phases == frozenset({Phase.ORACLE_UPDATE})
    assert isinstance(oracle, Subsystem)
    assert not isinstance(oracle, PegView)
    assert not isinstance(oracle, ReservesView)
    assert not isinstance(oracle, ActionSource)
    assert not isinstance(oracle, ActionTarget)


def test_price_sources_satisfy_protocol():
    assert isinstance(ScriptedPriceSource([1.0]), PriceSource)
    assert isinstance(ReferencePrice(1.0, 0.0), PriceSource)


def test_holds_its_source_directly():
    src = ScriptedPriceSource([1.0])
    oracle = Oracle(25, 0.5, src)
    assert oracle.source is src


def test_views_before_first_publish():
    src = ScriptedPriceSource([1.0])
    oracle = Oracle(25, 0.5, src)
    assert oracle.price is None
    assert oracle.last_update_step is None
    assert oracle.staleness_steps == 0
    assert oracle.reference_price == 1.0
    src.price = 1.2
    assert oracle.reference_price == 1.2


@pytest.mark.parametrize(
    ("heartbeat", "threshold", "source"),
    [
        (0, 0.5, ScriptedPriceSource([1.0])),
        (-1, 0.5, ScriptedPriceSource([1.0])),
        (2.5, 0.5, ScriptedPriceSource([1.0])),
        (True, 0.5, ScriptedPriceSource([1.0])),
        (25, -0.1, ScriptedPriceSource([1.0])),
        (25, math.nan, ScriptedPriceSource([1.0])),
        (25, 0.5, object()),
    ],
)
def test_invalid_construction_raises_value_error(heartbeat, threshold, source):
    with pytest.raises(ValueError):
        Oracle(heartbeat, threshold, source)


# AC 7 / 9 --------------------------------------------------------------------


def test_heartbeat_only_on_flat_price():
    oracle, _, ups = run([1.0], heartbeat=25)
    assert steps(ups) == [0, 25, 50, 75]
    assert reasons(ups) == ["initial", "heartbeat", "heartbeat", "heartbeat"]
    assert all(e.source == "oracle" for e in ups)
    assert all(
        e.payload == {"step": e.step, "price": 1.0, "reason": e.payload["reason"]} for e in ups
    )
    assert oracle.last_update_step == 75
    assert oracle.price == 1.0


def test_deviation_above_threshold_publishes_then_heartbeat_resets():
    prices = [1.0] * 7 + [1.006]
    oracle, _, ups = run(prices, heartbeat=25, threshold=0.5, max_steps=60)
    assert steps(ups) == [0, 7, 32, 57]
    assert reasons(ups) == ["initial", "deviation", "heartbeat", "heartbeat"]
    assert ups[1].payload["price"] == 1.006
    assert oracle.price == 1.006


def test_downward_deviation_also_publishes():
    _, _, ups = run([1.0] * 7 + [0.994], heartbeat=25, threshold=0.5, max_steps=30)
    assert steps(ups) == [0, 7]
    assert reasons(ups) == ["initial", "deviation"]


def test_move_below_threshold_never_triggers_deviation():
    oracle, probe, ups = run([1.0] * 7 + [1.004], heartbeat=25, threshold=0.5)
    assert steps(ups) == [0, 25, 50, 75]
    assert "deviation" not in reasons(ups)
    # the stale 1.0 stays published until the heartbeat at 25
    assert [e.payload["price"] for e in ups] == [1.0, 1.004, 1.004, 1.004]


def test_published_price_unchanged_between_updates():
    src = ScriptedPriceSource([1.0, 1.001, 1.002, 1.003])
    oracle = Oracle(25, 0.5, src)
    ctx = RunContext.from_config(make_config(max_steps=4))
    seen = []

    class Watch(RecordingStub):
        def on_phase(self, ctx, phase):
            seen.append((oracle.price, oracle.reference_price))

    for sub in (src, oracle, Watch("watch", phases={Phase.STATE_OBSERVATION})):
        ctx.registry.register(sub)
    Engine(ctx).run()
    assert seen == [(1.0, 1.0), (1.0, 1.001), (1.0, 1.002), (1.0, 1.003)]


def test_staleness_counts_between_updates():
    oracle, probe, _ = run([1.0], heartbeat=25, max_steps=60)
    assert probe.staleness[:27] == list(range(25)) + [0, 1]
    assert probe.staleness == [s % 25 for s in range(60)]


def test_staleness_resets_on_deviation():
    _, probe, _ = run([1.0] * 7 + [1.006], heartbeat=25, max_steps=40)
    assert probe.staleness == list(range(7)) + list(range(25)) + list(range(8))


def test_zero_threshold_updates_every_step():
    _, _, ups = run([1.0], heartbeat=25, threshold=0.0, max_steps=30)
    assert steps(ups) == list(range(30))
    # publishing every step keeps the heartbeat from ever coming due
    assert reasons(ups) == ["initial"] + ["deviation"] * 29


def test_heartbeat_checked_before_deviation():
    prices = [1.0] * 10 + [1.1]
    _, _, ups = run(prices, heartbeat=10, threshold=0.5, max_steps=11)
    assert steps(ups) == [0, 10]
    assert reasons(ups) == ["initial", "heartbeat"]
    assert ups[1].payload["price"] == 1.1


def test_heartbeat_one_publishes_every_step():
    _, _, ups = run([1.0], heartbeat=1, threshold=100.0, max_steps=10)
    assert steps(ups) == list(range(10))


def test_zero_published_price_does_not_raise():
    oracle, _, ups = run([0.0, 0.0, 1.0], heartbeat=25, threshold=0.5, max_steps=4)
    assert steps(ups) == [0, 2]
    assert oracle.price == 1.0


# AC 10 -------------------------------------------------------------------------


def test_snapshot_full_state():
    oracle = Oracle(25, 0.5, ScriptedPriceSource([1.0]))
    assert oracle.snapshot() == {"published_price": None, "last_update_step": None}
    oracle, _, _ = run([1.0] * 7 + [1.006], max_steps=10)
    assert oracle.snapshot() == {"published_price": 1.006, "last_update_step": 7}


def test_from_config():
    src = ScriptedPriceSource([1.0])
    oracle = Oracle.from_config(OracleConfig(heartbeat_steps=10, deviation_threshold_pct=1.0), src)
    assert oracle.name == "oracle"
    assert oracle.heartbeat_steps == 10
    assert oracle.deviation_threshold_pct == 1.0
    assert oracle.source is src


def test_from_baseline_scenario_config():
    oracle = Oracle.from_config(make_config().oracle, ReferencePrice(1.0, 0.0))
    assert oracle.heartbeat_steps == 25
    assert oracle.deviation_threshold_pct == 0.5
