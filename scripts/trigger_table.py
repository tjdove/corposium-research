"""Story 5.3 AC 5: when each defender policy's trigger first binds under a gradual attack.

Reads the runs of ``sweeps/policy-comparison-gradual-mc.yaml`` already under ``--output``
(``output/policy-comparison-gradual-mc/<cell>``: ``events.jsonl`` and
``timeseries.parquet`` per cell; nothing is re-run) for one attacker pace, one attack
ratio and one seed (default 0.01, 1.0x, seed 1000) and prints, per policy:

- ``trigger``: the defender's ``threshold_pct`` (defense is on while the AMM's deviation
  from par is below ``-threshold_pct``; ``defender.py``).
- ``binds``: the step of the defender's first act, its first executed AMM buy
  (``swap_executed`` with the defender as ``source``) or, for a policy that never buys,
  its first spread change (``spread_changed`` with the defender as ``source``). Hours
  are from run start.
- ``price seen``: the AMM price the trigger read, the recorded ``amm_price`` at the end
  of the step before (agents decide on the state the previous step left). The script
  raises if the deviation there is not below ``-threshold_pct``. ``first_past_trigger``
  (in the row, not printed) is the first step after a recorded deviation below it, so a
  defense that turned on before it first acted shows as an earlier step.
- ``first buy at``: that buy's ``execution_price`` (reference per stable).
- ``attacker sold``: the share of the attacker's capital sold by the end of the step
  before (``1 - attacker_stable / capital``).
- ``trough``: the run's ``max_depeg_bps`` and its step, for scale.

A policy with no defender (no-defense) has no trigger and is printed as such.

    python scripts/trigger_table.py [--output output]
        [--pace 0.01] [--ratio 1.0] [--seed 1000]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from depeg_sim.experiments.sweep import cell_run_dir, expand, load_sweep

SPEC = Path("sweeps/policy-comparison-gradual-mc.yaml")
CAPITAL = "agents[type=attacker].capital"
PACE = "agents[type=attacker].pace"


def _first_act(run_dir: Path, defender_id: str) -> tuple[int, str, float | None] | None:
    """``(step, kind, execution_price)`` of the defender's first buy or spread change."""
    with open(run_dir / "events.jsonl", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] == "swap_executed" and e["payload"]["source"] == defender_id:
                return e["step"], "buy", float(e["payload"]["execution_price"])
            if e["kind"] == "spread_changed" and e["payload"]["source"] == defender_id:
                return e["step"], "spread", None
    return None


def trigger_row(cell, output: Path) -> dict:
    cfg = cell.config
    run_dir = cell_run_dir(cell, output)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    hours = cfg.steps.interval_seconds / 3600
    attacker = next(a for a in cfg.agents if a.type == "attacker")
    defender = next((a for a in cfg.agents if a.type == "defender"), None)
    row = {
        "policy": cell.axis_values["policy"],
        "trigger_pct": None if defender is None else defender.threshold_pct,
        "binds_step": None,
        "binds_h": None,
        "act": None,
        "price_seen": None,
        "first_buy_price": None,
        "attacker_sold": None,
        "trough_bps": summary["max_depeg_bps"],
        "trough_step": summary["step_of_max_depeg"],
    }
    if defender is None:
        return row
    act = _first_act(run_dir, defender.id)
    if act is None:
        return row
    step, kind, price = act
    ts = pd.read_parquet(run_dir / "timeseries.parquet").set_index("step")
    seen = ts.loc[step - 1]
    threshold = -defender.threshold_pct / 100
    if not seen["peg_deviation"] < threshold:
        raise ValueError(f"{row['policy']}: deviation at step {step - 1} is not past the trigger")
    row |= {
        "binds_step": step,
        "binds_h": step * hours,
        "act": kind,
        "price_seen": float(seen["amm_price"]),
        "first_buy_price": price,
        "attacker_sold": 1.0 - float(seen["attacker_stable"]) / attacker.capital,
        "first_past_trigger": int(ts.index[ts["peg_deviation"] < threshold][0]) + 1,
    }
    return row


def build(output: Path, pace: float, ratio: float, seed: int, spec_path: Path = SPEC):
    spec = load_sweep(spec_path)
    cells = expand(spec)
    caps = sorted({c.axis_values[CAPITAL] for c in cells})
    base = cells[0].config
    defender = next(a for a in base.agents if a.type == "defender")
    resources = base.redemption.reserves + defender.budget
    capital = min(caps, key=lambda c: abs(c / resources - ratio))
    chosen = [
        c
        for c in cells
        if c.seed == seed and c.axis_values[PACE] == pace and c.axis_values[CAPITAL] == capital
    ]
    if not chosen:
        raise ValueError(f"no cells at pace {pace}, ratio {ratio}, seed {seed}")
    return capital / resources, [trigger_row(c, Path(output)) for c in chosen]


def _f(v, fmt: str, none: str = "-") -> str:
    return none if v is None or v != v else format(v, fmt)


def format_table(ratio: float, pace: float, seed: int, rows: list[dict]) -> str:
    head = (
        f"{'policy':<18} {'trigger':>7} {'binds step':>10} {'h':>5} {'act':>6} "
        f"{'price seen':>10} {'first buy at':>12} {'attacker sold':>13} {'trough bps':>10} "
        f"{'trough step':>11}"
    )
    out = [f"attacker pace {pace:g}, ratio {ratio:.2g}, seed {seed}", head, "-" * len(head)]
    for r in rows:
        out.append(
            f"{r['policy']:<18} {_f(r['trigger_pct'], '.1f', 'none'):>7} "
            f"{_f(r['binds_step'], 'd', 'never'):>10} {_f(r['binds_h'], '.2f'):>5} "
            f"{r['act'] or '-':>6} {_f(r['price_seen'], '.4f'):>10} "
            f"{_f(r['first_buy_price'], '.4f'):>12} {_f(r['attacker_sold'], '.1%'):>13} "
            f"{r['trough_bps']:>10,.1f} {r['trough_step']:>11,}"
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", type=Path, default=Path("output"), help="the sweeps' parent dir")
    p.add_argument("--pace", type=float, default=0.01)
    p.add_argument("--ratio", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=1000)
    args = p.parse_args(argv)
    ratio, rows = build(args.output, args.pace, args.ratio, args.seed)
    print(format_table(ratio, args.pace, args.seed, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
