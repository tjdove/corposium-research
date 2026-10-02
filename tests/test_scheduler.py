from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION, PHASES, Phase


def test_phase_order_version_is_1():
    assert PHASE_ORDER_VERSION == 1


def test_nine_phases_in_spec_order():
    assert len(PHASES) == 9
    assert [p.name for p in PHASES] == [
        "ENVIRONMENT_UPDATE",
        "ORACLE_UPDATE",
        "STATE_OBSERVATION",
        "AGENT_DECISION",
        "ACTION_QUEUE",
        "EXECUTION",
        "PROTOCOL_EVENTS",
        "METRIC_UPDATE",
        "PERSISTENCE",
    ]


def test_phases_derived_from_enum():
    assert PHASES == tuple(Phase)
