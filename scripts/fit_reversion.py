"""Fit the reference price's mean reversion to the calm USDC/USD series (Story 3.6 AC 2).

Model: hourly log deviation from par, ``x_t = ln(close_t / 1.0)``, follows an AR(1) with
no constant (the model's reference reverts to ``base_price = 1.0``, not to the sample
mean)::

    x_{t+1} = phi * x_t + e_t

Fit: least squares through the origin, ``phi = sum(x_t x_{t+1}) / sum(x_t^2)``, with the
usual standard error ``se = sqrt(s^2 / sum(x_t^2))``, ``s^2 = sum(e^2) / (n - 1)``.

Selection rule, applied mechanically:

1. ``phi`` is *significantly below 1* when the unit-root statistic ``(phi - 1) / se`` is
   below the Dickey-Fuller 5% critical value for the no-constant case, ``-1.95``
   (Fuller 1976, table 8.5.2, n = 100). The ordinary t threshold does not apply under the
   unit-root null.
2. If it is, ``kappa_step = 1 - phi ** (interval / 3600)`` (``interval`` = model step in
   seconds, 12: 300 steps per hour), so ``phi_step = 1 - kappa_step`` compounds to
   ``phi`` over one hour.
3. If it is not, the script prints ``undetermined from this series`` and still prints the
   point estimate, labelled; a scenario using it must say so.

Also printed: the half-life ``ln 2 / -ln phi`` hours, and two stationary standard
deviations in bps: the data's, ``sd(e) / sqrt(1 - phi^2)``, and the model's with the
scenario sigma, ``sigma_step / sqrt(1 - (1 - kappa_step)^2)``.

Caveat (docs/calibration/SOURCES.md, Environment): the calm series is Bitstamp's thin
book; 13 zero-volume hours repeat the previous close and isolated prints move it, both
of which bias a fit on 120 points. ``phi`` is a rough number; its se is the honest part.

    python scripts/fit_reversion.py [--csv PATH] [--interval 12] [--sigma 3.086e-05] [--dry-run]
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

CALM = Path("data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv")
DF_CRITICAL_5PCT = -1.95  # Dickey-Fuller, no constant, n = 100, 5% (Fuller 1976)
SIGMA_STEP = 3.086e-05  # calibrated-baseline environment.volatility_per_step (SOURCES.md)
BPS = 10_000


@dataclass(frozen=True)
class AR1Fit:
    n: int  # pairs used
    phi: float
    se: float
    resid_sd: float

    @property
    def unit_root_stat(self) -> float:
        return (self.phi - 1.0) / self.se

    @property
    def significant(self) -> bool:
        return self.unit_root_stat < DF_CRITICAL_5PCT


def fit_ar1(x: np.ndarray) -> AR1Fit:
    """AR(1) through the origin on ``x``; raises ``ValueError`` on fewer than 3 points or
    an all-zero series."""
    x = np.asarray(x, dtype="float64")
    if len(x) < 3:
        raise ValueError(f"need at least 3 points, got {len(x)}")
    a, b = x[:-1], x[1:]
    sxx = float(a @ a)
    if sxx == 0.0:
        raise ValueError("series is identically zero: phi is undefined")
    phi = float(a @ b) / sxx
    resid = b - phi * a
    s2 = float(resid @ resid) / (len(a) - 1)
    return AR1Fit(n=len(a), phi=phi, se=math.sqrt(s2 / sxx), resid_sd=math.sqrt(s2))


def kappa_step(phi: float, interval_seconds: float) -> float:
    """Per-step reversion whose ``(1 - kappa)`` compounds to ``phi`` over one hour."""
    return 1.0 - phi ** (interval_seconds / 3600.0)


def half_life_hours(phi: float) -> float:
    return math.log(2.0) / -math.log(phi)


def stationary_sd(sd: float, phi: float) -> float:
    """Stationary sd of an AR(1) with innovation sd ``sd`` and coefficient ``phi``."""
    return sd / math.sqrt(1.0 - phi * phi)


def deviations(csv: Path) -> np.ndarray:
    df = pd.read_csv(csv)
    return np.log(df["close"].to_numpy(dtype="float64") / 1.0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--csv", type=Path, default=CALM)
    p.add_argument("--interval", type=float, default=12.0, help="model step, seconds")
    p.add_argument("--sigma", type=float, default=SIGMA_STEP, help="model sigma per step")
    p.add_argument("--dry-run", action="store_true", help="describe the fit; do not run it")
    args = p.parse_args(argv)

    steps_per_hour = 3600.0 / args.interval
    if args.dry_run:
        print(f"csv: {args.csv}")
        print("model: x_t = ln(close_t), x_(t+1) = phi * x_t + e (least squares, no constant)")
        print(f"rule: significant if (phi - 1) / se < {DF_CRITICAL_5PCT} (Dickey-Fuller 5%)")
        print(f"kappa_step = 1 - phi ** (1 / {steps_per_hour:g})  (interval {args.interval:g} s)")
        return 0

    x = deviations(args.csv)
    fit = fit_ar1(x)
    k = kappa_step(fit.phi, args.interval)
    print(f"csv: {args.csv}  hourly points: {len(x)}  pairs: {fit.n}")
    print(f"deviation from 1.0: mean {x.mean() * BPS:+.2f} bps, sd {x.std(ddof=1) * BPS:.2f} bps")
    print(f"phi = {fit.phi:.4f}  se = {fit.se:.4f}  95% CI [{fit.phi - 1.96 * fit.se:.4f}, "
          f"{fit.phi + 1.96 * fit.se:.4f}]")  # fmt: skip
    print(
        f"unit-root stat (phi - 1) / se = {fit.unit_root_stat:.2f} "
        f"(Dickey-Fuller 5% critical {DF_CRITICAL_5PCT}): "
        + ("significantly below 1" if fit.significant else "NOT significantly below 1")
    )
    label = "" if fit.significant else "  [point estimate only: undetermined from this series]"
    print(
        f"kappa_step = {k:.6g}  (interval {args.interval:g} s, {steps_per_hour:g} steps/h){label}"
    )
    print(f"half_life_h = {half_life_hours(fit.phi):.3f}")
    print(f"stationary_sd_bps (data, sd(e) / sqrt(1 - phi^2)) = "
          f"{stationary_sd(fit.resid_sd, fit.phi) * BPS:.2f}")  # fmt: skip
    print(f"stationary_sd_bps (model, sigma {args.sigma:g} with kappa_step) = "
          f"{stationary_sd(args.sigma, 1.0 - k) * BPS:.2f}")  # fmt: skip
    if not fit.significant:
        print("undetermined from this series")
    return 0


if __name__ == "__main__":
    sys.exit(main())
