"""Phase order for one simulation step.

This is the single source of truth for step ordering. ``PHASES`` is derived from
the ``Phase`` enum's declaration order. Any change to the members or their order
must bump ``PHASE_ORDER_VERSION`` (see CLAUDE.md, "Phase order is versioned").
"""

from __future__ import annotations

import enum

PHASE_ORDER_VERSION = 1


class Phase(enum.Enum):
    ENVIRONMENT_UPDATE = "environment_update"
    ORACLE_UPDATE = "oracle_update"
    STATE_OBSERVATION = "state_observation"
    AGENT_DECISION = "agent_decision"
    ACTION_QUEUE = "action_queue"
    EXECUTION = "execution"
    PROTOCOL_EVENTS = "protocol_events"
    METRIC_UPDATE = "metric_update"
    PERSISTENCE = "persistence"


PHASES: tuple[Phase, ...] = tuple(Phase)
