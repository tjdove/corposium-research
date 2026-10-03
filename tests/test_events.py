import dataclasses

import pytest

from depeg_sim.kernel.events import Decision, DecisionTrace, Event, EventSink


def test_event_sink_preserves_emit_order():
    sink = EventSink()
    for i in range(5):
        sink.emit(i, f"k{i}", "src", {"i": i})
    events = sink.all()
    assert [e.kind for e in events] == ["k0", "k1", "k2", "k3", "k4"]
    assert events[3] == Event(step=3, kind="k3", source="src", payload={"i": 3})


def test_event_is_frozen():
    e = EventSink().emit(0, "k", "s")
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.step = 1


def test_all_returns_copy():
    sink = EventSink()
    sink.emit(0, "k", "s")
    sink.all().clear()
    assert len(sink) == 1


def test_payload_is_copied_on_emit():
    payload = {"a": 1}
    e = EventSink().emit(0, "k", "s", payload)
    payload["a"] = 2
    assert e.payload == {"a": 1}


def test_decision_trace_preserves_order():
    trace = DecisionTrace()
    trace.record(0, "a1", "r1", {"x": 1}, {"do": "buy"})
    trace.record(1, "a2", "r2", {"x": 2}, None)
    assert trace.all() == [
        Decision(step=0, agent_id="a1", rule="r1", observed={"x": 1}, action={"do": "buy"}),
        Decision(step=1, agent_id="a2", rule="r2", observed={"x": 2}, action=None),
    ]


def test_decision_is_frozen():
    d = DecisionTrace().record(0, "a", "r", {}, None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.rule = "other"


def test_at_step_returns_only_that_step_in_order():
    sink = EventSink()
    for step, kind in [(0, "a"), (1, "b"), (1, "c"), (2, "d"), (2, "e")]:
        sink.emit(step, kind, "s")
    assert [e.kind for e in sink.at_step(2)] == ["d", "e"]
    assert [e.kind for e in sink.at_step(1)] == ["b", "c"]
    assert [e.kind for e in sink.at_step(0)] == ["a"]
    assert sink.at_step(3) == []
    assert EventSink().at_step(0) == []


def test_decision_record_accepts_action_list():
    trace = DecisionTrace()
    a, b = {"kind": "x"}, {"kind": "y"}
    d1 = trace.record(0, "ag", "r", {}, [a, b])
    d2 = trace.record(1, "ag", "r", {}, a)
    d3 = trace.record(2, "ag", "r", {}, None)
    assert d1.action == {"actions": [a, b]}
    assert d2.action == a
    assert d3.action is None
    a["kind"] = "changed"  # stored copies
    assert d1.action["actions"][0] == {"kind": "x"}
