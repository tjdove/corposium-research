"""Story 5.1 AC 3: the USDC March-2023 replay with and without the observed series as input.

Runs the six replay scenarios (observed reference, constant par reference, calm OU
reference; each with the single-entry holder and with ladder B) and the two Story 5.5
weekend-channel variants of the par ladder-B replay (redemption capacity at 10% of
calibrated, and 0, until the 85 h reopening), and prints one table, the observed series on
the top row. Columns:

- ``trough``: ``max_depeg_bps`` and ``step_of_max_depeg`` from the run's summary; ``h`` is
  that step's ``elapsed_seconds / 3600`` (hours from the series start, 2023-03-10 00:00
  UTC). Observed: the CSV's lowest hourly close against ``redemption.peg_price``.
- ``re-entry h``: the first time after the trough at which ``|deviation| <=`` the ADR-0013
  band (31 bps, ``charts._band``); ``never`` if it does not happen in the window.
- ``in band h``: hours inside the band from the attack start (27 h) to the end of the
  observed series (its last close, 95 h, counted as the hour 95-96 h). Observed: one hour
  per hourly close inside the band. Simulated: steps inside the band x 12 s. The two are
  sampled differently (hourly close vs every 12 s spot), so this column compares their
  time in band, not their paths point for point.
- ``holder bought``: ``holder_bought_stable``; ``holder redeemed``: reference paid by the
  redemption channel to the holder (``redeem_fulfilled`` events); ``holder PnL``:
  ``holder_pnl``; ``arb redeemed``: ``arbitrageur_redeemed``. Model units (1M = $234.6M).

The observed CSV is read from the observed-reference scenario's ``price_series_path`` and
is used here only for evaluation. Deterministic (fixed seeds, no wall clock in the
output). ``--max-steps`` shortens every run (the smoke test); the observed row and the
window are unchanged by it.

    python scripts/replay_table.py [--output DIR] [--max-steps N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

from depeg_sim.analysis.charts import BPS, _band
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.writer import EVENTS, MANIFEST, TIMESERIES
from depeg_sim.kernel.config import load_scenario

# (label, scenario); the observed-reference pair first, then par (primary), then OU.
REPLAYS = (
    ("observed ref, single entry", "scenarios/usdc-2023.yaml"),
    ("observed ref, ladder B", "scenarios/usdc-2023-tranches.yaml"),
    ("par ref, single entry", "scenarios/usdc-2023-par.yaml"),
    ("par ref, ladder B", "scenarios/usdc-2023-tranches-par.yaml"),
    ("OU ref, single entry", "scenarios/usdc-2023-ou.yaml"),
    ("OU ref, ladder B", "scenarios/usdc-2023-tranches-ou.yaml"),
    # Story 5.5: par ref, ladder B, weekend channel at 10% of calibrated / closed until 85 h
    ("par ref, ladder B, channel 10%", "scenarios/usdc-2023-tranches-par-slow.yaml"),
    ("par ref, ladder B, channel closed", "scenarios/usdc-2023-tranches-par-closed.yaml"),
)
OBSERVED_FROM = Path("scenarios/usdc-2023.yaml")
SECONDS_PER_HOUR = 3600


def observed_row(series_path: Path, peg: float, band: float, start_h: float) -> dict:
    obs = pd.read_csv(series_path)
    hours = (obs["unix"] - obs["unix"].iloc[0]) / SECONDS_PER_HOUR
    dev = obs["close"] / peg - 1
    i = int(dev.idxmin())
    end_h = float(hours.iloc[-1]) + 1  # the last close stands for the hour after it
    window = (hours >= start_h) & (hours < end_h)
    after = hours[(hours > hours.loc[i]) & (dev.abs() <= band)]
    return {
        "label": "observed (Bitstamp hourly close)",
        "trough_bps": float(dev.loc[i]) * BPS,
        "trough_step": None,
        "trough_h": float(hours.loc[i]),
        "reentry_h": None if after.empty else float(after.iloc[0]),
        "in_band_h": float((dev[window].abs() <= band).sum()),
        "window_h": (start_h, end_h),
    }


def _holder_redeemed(run_dir: Path, holder_id: str | None) -> float | None:
    if holder_id is None:
        return None
    paid = 0.0
    with open(run_dir / EVENTS, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] == "redeem_fulfilled" and e["payload"]["source"] == holder_id:
                paid += e["payload"]["paid_reference"]
    return paid


def simulated_row(label: str, run_dir: Path, window_h: tuple[float, float]) -> dict:
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    config = manifest["config"]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    ts = pd.read_parquet(run_dir / TIMESERIES, columns=["step", "elapsed_seconds", "peg_deviation"])
    hours = ts["elapsed_seconds"] / SECONDS_PER_HOUR
    dev = ts["peg_deviation"]
    band = _band(config)
    trough_step = int(summary["step_of_max_depeg"])
    trough_h = float(hours[ts["step"] == trough_step].iloc[0])
    after = hours[(hours > trough_h) & (dev.abs() <= band)]
    lo, hi = window_h
    window = (hours >= lo) & (hours < hi)
    interval = config["steps"]["interval_seconds"]
    holder_id = next((a["id"] for a in config["agents"] if a["type"] == "holder"), None)
    return {
        "label": label,
        "hash": manifest["scenario_hash"][:12],
        "trough_bps": float(summary["max_depeg_bps"]),
        "trough_step": trough_step,
        "trough_h": trough_h,
        "reentry_h": None if after.empty else float(after.iloc[0]),
        "in_band_h": float((dev[window].abs() <= band).sum()) * interval / SECONDS_PER_HOUR,
        "holder_bought": summary["holder_bought_stable"],
        "holder_redeemed": _holder_redeemed(run_dir, holder_id),
        "holder_pnl": summary["holder_pnl"],
        "arb_redeemed": summary["arbitrageur_redeemed"],
    }


def _num(v: float | None, fmt: str) -> str:
    return "n/a" if v is None else format(v, fmt)


def format_table(rows: list[dict]) -> str:
    head = (
        f"{'replay':<34} {'hash':<12} {'trough bps':>10} {'step':>6} {'h':>5} "
        f"{'re-entry h':>10} {'in band h':>9} {'holder bought':>13} {'holder redeemed':>15} "
        f"{'holder PnL':>10} {'arb redeemed':>12}"
    )
    lines = [head, "-" * len(head)]
    for r in rows:
        reentry = "never" if r["reentry_h"] is None else f"{r['reentry_h']:.1f}"
        lines.append(
            f"{r['label']:<34} {r.get('hash', ''):<12} {r['trough_bps']:>10,.1f} "
            f"{_num(r['trough_step'], 'd'):>6} {r['trough_h']:>5.1f} {reentry:>10} "
            f"{r['in_band_h']:>9.1f} {_num(r.get('holder_bought'), ',.0f'):>13} "
            f"{_num(r.get('holder_redeemed'), ',.0f'):>15} "
            f"{_num(r.get('holder_pnl'), ',.0f'):>10} {_num(r.get('arb_redeemed'), ',.0f'):>12}"
        )
    return "\n".join(lines)


def build(output: Path, max_steps: int | None = None) -> list[dict]:
    base = load_scenario(OBSERVED_FROM)
    attacker = next(a for a in base.agents if a.type == "attacker")
    start_h = attacker.start_step * base.steps.interval_seconds / SECONDS_PER_HOUR
    obs = observed_row(
        base.environment.price_series_path,
        base.redemption.peg_price,
        _band(base.model_dump(mode="json")),
        start_h,
    )
    rows = [obs]
    for label, path in REPLAYS:
        cfg = load_scenario(Path(path))
        if max_steps is not None:
            cfg = cfg.model_copy(
                update={"steps": cfg.steps.model_copy(update={"max_steps": max_steps})}
            )
        run = run_scenario(cfg, output_dir=output, chart=False)
        rows.append(simulated_row(label, run.run_dir, obs["window_h"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", type=Path, default=None, help="keep the runs here (default: temp)")
    p.add_argument("--max-steps", type=int, default=None, help="shorten every run (smoke test)")
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="replay-table-") as tmp:
        rows = build(args.output or Path(tmp), args.max_steps)
    lo, hi = rows[0]["window_h"]
    print(format_table(rows))
    print(
        f"band ±{_band(load_scenario(OBSERVED_FROM).model_dump(mode='json')) * BPS:g} bps; "
        f"in band h over {lo:.0f}-{hi:.0f} h; model units (1M = $234.6M)"
    )
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # skip teardown: pyarrow's thread pool can abort there (see depeg_sim.mc)
