import pytest

from depeg_sim.analysis.stats import wilson


@pytest.mark.parametrize(
    "k, n, expected",
    [
        (0, 10, (0.0, 0.278)),
        (5, 10, (0.237, 0.763)),
        (10, 10, (0.722, 1.0)),
    ],
)
def test_wilson_known_values(k, n, expected):
    lo, hi = wilson(k, n)
    assert (round(lo, 3), round(hi, 3)) == expected


def test_wilson_empty_sample():
    assert wilson(0, 0) == (0.0, 1.0)


def test_wilson_properties():
    for n in (1, 7, 16, 100):
        for k in range(n + 1):
            lo, hi = wilson(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0
    narrow, wide = wilson(8, 16), wilson(8, 16, z=2.576)  # 99% is wider than 95%
    assert wide[0] < narrow[0] and wide[1] > narrow[1]
    lo, hi = wilson(50, 100)
    assert lo == pytest.approx(1 - hi)  # symmetric at p = 0.5


@pytest.mark.parametrize("k, n", [(-1, 10), (11, 10)])
def test_wilson_rejects_impossible_counts(k, n):
    with pytest.raises(ValueError):
        wilson(k, n)
