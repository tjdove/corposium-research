import pytest

from depeg_sim.kernel.clock import Clock


def test_clock_starts_at_zero():
    c = Clock(12)
    assert c.step_index == 0
    assert c.elapsed_seconds == 0


def test_clock_arithmetic():
    c = Clock(12)
    for _ in range(5):
        c.tick()
    assert c.step_index == 5
    assert c.elapsed_seconds == 60


def test_elapsed_always_step_times_interval():
    c = Clock(7)
    for _ in range(100):
        assert c.elapsed_seconds == c.step_index * 7
        c.tick()


@pytest.mark.parametrize("bad", [0, -1])
def test_clock_rejects_nonpositive_interval(bad):
    with pytest.raises(ValueError):
        Clock(bad)
