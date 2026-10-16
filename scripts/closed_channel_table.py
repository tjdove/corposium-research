"""Story 5.5 AC 4-5: the par ladder-B replay with the weekend redemption channel open
(calibrated, 605.79/step), at 10% (60.579) and closed (0) until the 85 h reopening.

Runs the three scenarios and prints three tables:

1. **35-85 h:** min, max and mean deviation from peg of the AMM price (bps, every 12 s
   step with ``35 <= h < 85``), and hours inside the ADR-0013 band in that window. The
   observed row is the CSV's hourly closes in the same window (one hour per close), read
   from ``replay_table.OBSERVED_FROM``'s ``price_series_path`` for evaluation only.
2. **The 85 h reopening:** the deviation on the last step before the reopening step, the
   redemption queue then (total, and per source from the ``redeem_requested`` /
   ``redeem_fulfilled`` events before the reopening step), when the queue first empties
   from the reopening step on, the deepest deviation from then on, and the first time from
   then on inside the band. Rows are stamped ``step x 12 s``, so the reopening step is the
   85.00 h row.
3. **The arbitrageur:** reference it spent buying stable on the AMM (``swap_executed``,
   ``buy_stable``) and reference the channel paid it (``redeem_fulfilled``), over the
   attack's first four hours (27-31 h) and over 35-85 h.
4. **The holder at 85 h and at the end** (112 h): stable held, of which queued for
   redemption, reference held, PnL (``pnl_last``, marked at AMM spot), from the run's
   checkpoints. The runs set ``metrics.checkpoint_every`` to the reopening step (25,500),
   so the first checkpoint is the state after 85 h, before the reopening step applies; the
   engine writes the last at the end. Checkpointing changes nothing else in the run.

The full-window replay rows (trough, re-entry, hours in band, holder bought / redeemed /
PnL) are in ``scripts/replay_table.py``. Deterministic (seed 42, constant reference, no
wall clock in the output). ``--max-steps`` shortens every run (it must stay past the
reopening step). Model units (1M = $234.6M).

    python scripts/closed_channel_table.py [--output DIR] [--max-steps N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
from replay_table import OBSERVED_FROM, SECONDS_PER_HOUR

from depeg_sim.analysis.charts import BPS, _band
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import set_path
from depeg_sim.experiments.writer import EVENTS, MANIFEST, TIMESERIES
from depeg_sim.kernel.config import load_scenario

CHANNELS = (
    ("open (605.79/step)", "scenarios/usdc-2023-tranches-par.yaml"),
    ("10% (60.579/step)", "scenarios/usdc-2023-tranches-par-slow.yaml"),
    ("closed (0/step)", "scenarios/usdc-2023-tranches-par-closed.yaml"),
)
WINDOW_H = (35.0, 85.0)  # AC 4: where the price sits between the trough and the reopening
ATTACK_H = (27.0, 31.0)  # the attack's first four hours, to the observed trough (ADR-0033)
ARB = "arbitrageur"


def observed_window() -> dict:
    """The observed hourly closes in ``WINDOW_H`` (bps from peg; one hour per close)."""
    base = load_scenario(OBSERVED_FROM)
    obs = pd.read_csv(base.environment.price_series_path)
    hours = (obs["unix"] - obs["unix"].iloc[0]) / SECONDS_PER_HOUR
    dev = (obs["close"] / base.redemption.peg_price - 1) * BPS
    lo, hi = WINDOW_H
    win = dev[(hours >= lo) & (hours < hi)]
    band = _band(base.model_dump(mode="json")) * BPS
    return {
        "label": "observed (hourly)",
        "window_min_bps": float(win.min()),
        "window_max_bps": float(win.max()),
        "window_mean_bps": float(win.mean()),
        "window_in_band_h": float((win.abs() <= band).sum()),
    }


def _from_events(run_dir: Path, arb_id: str, reopen: int, interval: int) -> dict:
    """Stable still queued per source at the start of ``reopen``; the arbitrageur's AMM
    buys and channel payouts (reference) per window of ``ATTACK_H`` and ``WINDOW_H``."""
    queued: dict[str, float] = defaultdict(float)
    windows = {"attack": ATTACK_H, "window": WINDOW_H}
    arb = {f"{k}_{w}": 0.0 for k in ("bought", "paid") for w in windows}
    with open(run_dir / EVENTS, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            kind, pay, step = e["kind"], e["payload"], e["step"]
            h = step * interval / SECONDS_PER_HOUR
            if kind == "redeem_requested" and step < reopen:
                queued[pay["source"]] += pay["amount_stable"]
            elif kind == "redeem_fulfilled" and step < reopen:
                queued[pay["source"]] -= pay["amount_stable"]
            if pay.get("source") != arb_id:
                continue
            for w, (lo, hi) in windows.items():
                if lo <= h < hi:
                    if kind == "swap_executed" and pay["side"] == "buy_stable":
                        arb[f"bought_{w}"] += pay["amount_in"]
                    elif kind == "redeem_fulfilled":
                        arb[f"paid_{w}"] += pay["paid_reference"]
    return {"queue_by_source": {k: v for k, v in sorted(queued.items()) if v > 1e-6}} | arb


def _holder(checkpoint: Path) -> dict:
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    h = next(s for s in state["subsystems"].values() if s.get("type") == "holder")
    return {
        "h": state["elapsed_seconds"] / SECONDS_PER_HOUR,
        "stable": h["balances"]["stable"],
        "queued": h["queued_redeem"],
        "reference": h["balances"]["reference"],
        "pnl": h["pnl_last"],
    }


def channel_row(label: str, run_dir: Path) -> dict:
    config = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))["config"]
    reopen = config["redemption"]["capacity_schedule"][0]["step"]
    interval = config["steps"]["interval_seconds"]
    reopen_h = reopen * interval / SECONDS_PER_HOUR
    band = _band(config)
    ts = pd.read_parquet(run_dir / TIMESERIES)
    hours = ts["elapsed_seconds"] / SECONDS_PER_HOUR
    dev = ts["peg_deviation"] * BPS
    lo, hi = WINDOW_H
    win = dev[(hours >= lo) & (hours < hi)]
    after = ts["step"] >= reopen
    empty = hours[after & (ts["redemption_queued_total"] <= 1e-6)]
    inside = hours[after & (dev.abs() <= band * BPS)]
    checkpoints = sorted((run_dir / "checkpoints").glob("step-*.json"))
    arb_id = next(a["id"] for a in config["agents"] if a["type"] == ARB)
    at_reopen = run_dir / "checkpoints" / f"step-{reopen:06d}.json"
    return {
        "label": label,
        "capacity": config["redemption"]["capacity_per_step"],
        "window_min_bps": float(win.min()),
        "window_max_bps": float(win.max()),
        "window_mean_bps": float(win.mean()),
        "window_in_band_h": float((win.abs() <= band * BPS).sum()) * interval / SECONDS_PER_HOUR,
        "reopen_h": reopen_h,
        "at_reopen_bps": float(dev[~after].iloc[-1]),
        "queue_at_reopen": float(ts["redemption_queued_total"][~after].iloc[-1]),
        "queue_empty_h": None if empty.empty else float(empty.iloc[0]),
        "after_min_bps": float(dev[after].min()),
        "after_in_band_h": None if inside.empty else float(inside.iloc[0]),
        "holder_reopen": _holder(at_reopen),
        "holder_end": _holder(checkpoints[-1]),
    } | _from_events(run_dir, arb_id, reopen, interval)


def build(output: Path, max_steps: int | None = None) -> list[dict]:
    rows = []
    for label, path in CHANNELS:
        cfg = load_scenario(Path(path))
        reopen = cfg.redemption.capacity_schedule[0].step
        cfg = set_path(cfg, "metrics.checkpoint_every", reopen)
        if max_steps is not None:
            if max_steps <= reopen:
                raise ValueError(f"--max-steps must be past the reopening step {reopen}")
            cfg = set_path(cfg, "steps.max_steps", max_steps)
        run = run_scenario(cfg, output_dir=output, chart=False)
        rows.append(channel_row(label, run.run_dir))
    return rows


def _h(v: float | None) -> str:
    return "never" if v is None else f"{v:.2f}"


def format_tables(rows: list[dict]) -> str:
    lo, hi = WINDOW_H
    out = [f"1. AMM price, {lo:.0f}-{hi:.0f} h (bps from peg, every step)"]
    head = f"{'weekend channel':<20} {'min':>9} {'max':>9} {'mean':>9} {'in band h':>9}"
    out += [head, "-" * len(head)]
    for r in [observed_window(), *rows]:
        out.append(
            f"{r['label']:<20} {r['window_min_bps']:>9,.1f} {r['window_max_bps']:>9,.1f} "
            f"{r['window_mean_bps']:>9,.1f} {r['window_in_band_h']:>9.2f}"
        )

    out += ["", f"2. the reopening at {rows[0]['reopen_h']:.0f} h (capacity -> 19,181.59/step)"]
    head = (
        f"{'weekend channel':<20} {'bps at':>8} {'queue at':>11} {'queue empty':>11} "
        f"{'deepest after':>13} {'in band':>8}  queued by source at the reopening"
    )
    out += [head, "-" * len(head)]
    for r in rows:
        who = ", ".join(f"{k} {v:,.0f}" for k, v in r["queue_by_source"].items()) or "-"
        out.append(
            f"{r['label']:<20} {r['at_reopen_bps']:>8,.1f} {r['queue_at_reopen']:>11,.0f} "
            f"{_h(r['queue_empty_h']):>11} {r['after_min_bps']:>13,.1f} "
            f"{_h(r['after_in_band_h']):>8}  {who}"
        )
    out.append("bps at, queue at: the last step before the reopening; queue empty, in band: "
               "first hour from the reopening step on")  # fmt: skip

    (a_lo, a_hi), (w_lo, w_hi) = ATTACK_H, WINDOW_H
    out += ["", "3. the arbitrageur (reference)"]
    head = (
        f"{'weekend channel':<20} {f'bought {a_lo:.0f}-{a_hi:.0f} h':>15} "
        f"{f'paid {a_lo:.0f}-{a_hi:.0f} h':>13} {f'bought {w_lo:.0f}-{w_hi:.0f} h':>15} "
        f"{f'paid {w_lo:.0f}-{w_hi:.0f} h':>13}"
    )
    out += [head, "-" * len(head)]
    for r in rows:
        out.append(
            f"{r['label']:<20} {r['bought_attack']:>15,.0f} {r['paid_attack']:>13,.0f} "
            f"{r['bought_window']:>15,.0f} {r['paid_window']:>13,.0f}"
        )
    out.append("bought: spent on AMM buy_stable swaps; paid: by the redemption channel")

    out += ["", "4. the holder (checkpoints)"]
    head = (
        f"{'weekend channel':<20} {'at h':>6} {'stable':>11} {'queued':>11} "
        f"{'reference':>11} {'PnL':>10}"
    )
    out += [head, "-" * len(head)]
    for r in rows:
        for h in (r["holder_reopen"], r["holder_end"]):
            out.append(
                f"{r['label']:<20} {h['h']:>6.1f} {h['stable']:>11,.0f} {h['queued']:>11,.0f} "
                f"{h['reference']:>11,.0f} {h['pnl']:>10,.0f}"
            )
    out += ["", "model units (1M = $234.6M); PnL marked at AMM spot"]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", type=Path, default=None, help="keep the runs here (default: temp)")
    p.add_argument("--max-steps", type=int, default=None, help="shorten every run (smoke test)")
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="closed-channel-") as tmp:
        rows = build(args.output or Path(tmp), args.max_steps)
    print(format_tables(rows))
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # skip teardown: pyarrow's thread pool can abort there (see depeg_sim.mc)
