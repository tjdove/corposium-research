"""Small statistics helpers. No scipy: each is a few lines and tested against known values."""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for ``k`` successes in ``n`` trials (Wilson 1927).

    ``z = 1.96`` gives a 95% interval. Unlike the normal approximation it stays inside
    [0, 1] and is informative at ``k = 0`` or ``k = n``. ``n == 0`` gives ``(0.0, 1.0)``.
    """
    if n == 0:
        return 0.0, 1.0
    if not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n, got k={k}, n={n}")
    z2 = z * z
    centre = (k + z2 / 2) / (n + z2)
    half = z * math.sqrt(k * (n - k) / n + z2 / 4) / (n + z2)
    return max(0.0, centre - half), min(1.0, centre + half)


def fit_logistic(
    x: list[float], k: list[int], n: list[int], ridge: float = 1e-6, iters: int = 100
) -> tuple[float, float]:
    """Binomial maximum-likelihood logistic fit ``p = 1 / (1 + exp(-(a + b * x)))`` to
    ``k`` successes out of ``n`` at each ``x``. Returns ``(a, b)``; the 0.5 crossing is
    ``-a / b``.

    Newton-Raphson on standardised ``x`` with a tiny ridge penalty (``ridge`` on both
    coefficients) so perfectly separated data still converge to a steep finite curve
    instead of diverging. Plain Python, no numpy or scipy needed.
    """
    if not (len(x) == len(k) == len(n)) or not x:
        raise ValueError("x, k and n must be non-empty and the same length")
    total = sum(n)
    mean = sum(xi * ni for xi, ni in zip(x, n, strict=True)) / total
    var = sum(ni * (xi - mean) ** 2 for xi, ni in zip(x, n, strict=True)) / total
    sd = math.sqrt(var) or 1.0
    z = [(xi - mean) / sd for xi in x]
    a = b = 0.0
    for _ in range(iters):
        ga, gb = -ridge * a, -ridge * b  # gradient of the penalised log-likelihood
        haa, hab, hbb = ridge, 0.0, ridge  # minus the Hessian
        for zi, ki, ni in zip(z, k, n, strict=True):
            p = 1.0 / (1.0 + math.exp(-(a + b * zi)))
            r = ki - ni * p
            w = ni * p * (1.0 - p)
            ga += r
            gb += r * zi
            haa += w
            hab += w * zi
            hbb += w * zi * zi
        det = haa * hbb - hab * hab
        da = (hbb * ga - hab * gb) / det
        db = (haa * gb - hab * ga) / det
        a, b = a + da, b + db
        if abs(da) < 1e-10 and abs(db) < 1e-10:
            break
    return a - b * mean / sd, b / sd
