"""Append-only run records: the event log and the agent decision trace.

Records are frozen dataclasses; sinks only ever append, and ``all()`` returns a
copy so callers cannot rewrite history.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    step: int
    kind: str
    source: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class Decision:
    step: int
    agent_id: str
    rule: str
    observed: Mapping[str, Any]
    action: Mapping[str, Any] | None


class EventSink:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(
        self, step: int, kind: str, source: str, payload: Mapping[str, Any] | None = None
    ) -> Event:
        event = Event(step=step, kind=kind, source=source, payload=dict(payload or {}))
        self._events.append(event)
        return event

    def all(self) -> list[Event]:
        return list(self._events)

    def at_step(self, step: int) -> list[Event]:
        """Events emitted at ``step``, in emission order. Scans back from the tail and
        stops at the first earlier step, so asking for the current step is cheap."""
        out: list[Event] = []
        for event in reversed(self._events):
            if event.step < step:
                break
            if event.step == step:
                out.append(event)
        out.reverse()
        return out

    def __len__(self) -> int:
        return len(self._events)


class DecisionTrace:
    def __init__(self) -> None:
        self._decisions: list[Decision] = []

    def record(
        self,
        step: int,
        agent_id: str,
        rule: str,
        observed: Mapping[str, Any],
        action: Mapping[str, Any] | list[Mapping[str, Any]] | None,
    ) -> Decision:
        """A list of actions (a multi-action step) is stored as ``{"actions": [...]}``
        (ADR-0011)."""
        if isinstance(action, list):
            action = {"actions": [dict(a) for a in action]}
        decision = Decision(
            step=step,
            agent_id=agent_id,
            rule=rule,
            observed=dict(observed),
            action=None if action is None else dict(action),
        )
        self._decisions.append(decision)
        return decision

    def all(self) -> list[Decision]:
        return list(self._decisions)

    def __len__(self) -> int:
        return len(self._decisions)
