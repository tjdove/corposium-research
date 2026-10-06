"""Story 3.4 AC 3: what the price-holding budget tracks, from a ``budget-x-attack-mc`` sweep.

Reads ``<sweep_dir>/mc.parquet`` + manifest. Per attack column it finds the 0.5 crossing
of p(never re-enters) over the defender budget (``charts.budget_crossing``, linear
interpolation) and, at that crossing, interpolates two attack-side candidates along the
same budget column, from the per-cell means over seeds:

- extraction = ``capital + attacker_pnl``: reference the attacker took out of the pool
  (its stable is fully sold by the end of the run, so its end PnL is reference received
  minus capital; nothing is marked to market);
- attacker loss = ``-attacker_pnl``: the discount the attacker gave up.

Prints each crossing with both candidates and ``budget / candidate``, then the log-log
least-squares slope of the crossing budget against attack size and against each
candidate. A quantity the budget is proportional to gives slope ~1 and a constant ratio.

    python scripts/budget_attack_table.py [output/budget-x-attack-mc]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from depeg_sim.analysis.charts import (
    BUDGET_PATH,
    CAPITAL_PATH,
    _axis_named,
    _read_sweep,
    budget_crossing,
    loglog_slope,
    p_never_reenters,
)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sweep_dir = Path(argv[0] if argv else "output/budget-x-attack-mc")
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    b_col, c_col = _axis_named(manifest, BUDGET_PATH), _axis_named(manifest, CAPITAL_PATH)
    b_cal = next(a for a in base["agents"] if a["type"] == "defender")["budget"]
    resources = b_cal + base["redemption"]["reserves"]
    mc["p"] = p_never_reenters(mc)[0]
    mc["extraction"] = mc[c_col] + mc["attacker_pnl_mean"]
    mc["loss"] = -mc["attacker_pnl_mean"]

    print(
        f"{'attack':>7} {'capital':>12} {'crossing':>9} {'budget':>12} {'extraction':>12} "
        f"{'loss':>12} {'B/cap':>6} {'B/extr':>6} {'B/loss':>6}"
    )
    rows = []
    for cap in sorted(mc[c_col].unique()):
        g = mc[mc[c_col] == cap].sort_values(b_col)
        x, kind = budget_crossing(g[b_col].tolist(), g["p"].tolist())
        if kind != "crossing":
            edge = g[b_col].min() if kind == "below" else g[b_col].max()
            word = "<" if kind == "below" else ">"
            print(
                f"{cap / resources:>6.3g}x {cap:>12,.0f} {word}{edge / b_cal:>7.3g}x  not reached"
            )
            continue
        ext = float(np.interp(x, g[b_col], g["extraction"]))
        loss = float(np.interp(x, g[b_col], g["loss"]))
        rows.append((cap, x, ext, loss))
        print(
            f"{cap / resources:>6.3g}x {cap:>12,.0f} {x / b_cal:>8.3g}x {x:>12,.0f} {ext:>12,.0f} "
            f"{loss:>12,.0f} {x / cap:>6.3f} {x / ext:>6.3f} {x / loss:>6.3f}"
        )
    if len(rows) >= 2:
        for name, i in (("attack size", 0), ("extraction", 2), ("attacker loss", 3)):
            slope = loglog_slope([(r[i], r[1]) for r in rows])
            ratios = [r[1] / r[i] for r in rows]
            spread = (max(ratios) - min(ratios)) / np.mean(ratios)
            print(
                f"crossing budget vs {name:<13}: log-log slope {slope:.2f}, "
                f"budget/{name} {min(ratios):.3f}..{max(ratios):.3f} (spread {spread:.0%})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
