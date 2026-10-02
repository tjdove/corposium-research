from kernel_stubs import PegStub, RecordingStub, ReservesStub, RngStub, SourceStub, TargetStub

from depeg_sim.kernel.interfaces import (
    ActionSource,
    ActionTarget,
    PegView,
    ReservesView,
    Subsystem,
)


def test_structural_stub_is_subsystem():
    assert isinstance(RngStub(), Subsystem)


def test_explicit_subclass_inherits_default_snapshot():
    assert RecordingStub("r").snapshot() == {}


def test_source_and_target_conformance():
    assert isinstance(SourceStub(), ActionSource)
    assert not isinstance(SourceStub(), ActionTarget)
    assert isinstance(TargetStub(), ActionTarget)
    assert not isinstance(TargetStub(), ActionSource)
    assert not isinstance(RecordingStub("r"), ActionSource)


def test_views():
    assert isinstance(ReservesStub(3), ReservesView)
    assert not isinstance(ReservesStub(3), PegView)
    assert isinstance(PegStub([0.0]), PegView)
    assert not isinstance(PegStub([0.0]), ReservesView)


def test_object_missing_hooks_is_not_subsystem():
    class Bare:
        name = "bare"
        phases = frozenset()

    assert not isinstance(Bare(), Subsystem)
