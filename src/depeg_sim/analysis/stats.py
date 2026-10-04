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
