import math

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


def test_fit_logistic_recovers_known_curve():
    import math

    from depeg_sim.analysis.stats import fit_logistic

    # Expected counts from p = 1/(1+exp(-(-20 + 20x))): crossing at x = 1.0. With n large
    # and exact expected counts, the MLE is the generating curve.
    xs = [0.8, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2]
    n = [100_000] * len(xs)
    k = [round(100_000 / (1 + math.exp(-(-20 + 20 * x)))) for x in xs]
    a, b = fit_logistic(xs, k, n)
    assert -a / b == pytest.approx(1.0, abs=1e-3)
    assert b == pytest.approx(20, rel=1e-2)


def test_fit_logistic_separated_data_converges():
    from depeg_sim.analysis.stats import fit_logistic

    a, b = fit_logistic([0.9, 0.95, 1.05, 1.1], [0, 0, 16, 16], [16] * 4)
    assert math.isfinite(a) and math.isfinite(b) and b > 0
    assert 0.95 < -a / b < 1.05
