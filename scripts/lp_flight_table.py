"""Story 3.8 AC 6: what liquidity flight does, against the same runs with no LP.

Reads the ``lp-flight-mc`` sweep (``sweep.parquet`` and each cell's ``events.jsonl``) and
runs three companion sweeps with the same seeds and horizon into ``<output>/``:

- ``lp-flight-nolp``: ``scenarios/calibrated-baseline-ou.yaml`` (the LP scenario's base,
  so: the same world with no LP) over the sweep's attacker-capital axis;
- ``lp-flight-episode``: ``scenarios/calibrated-baseline-lp.yaml`` at its own attacker
  (the episode net burn, ratio 0.064) over the sweep's share x threshold axes;
- ``lp-flight-episode-nolp``: the OU base at the episode attacker.

Prints two tables, one row per cell, medians over seeds unless marked: trough (mean bps,
and its change against no LP), hours from run start to first re-entry (``never`` when
fewer than half the seeds re-enter), ``held_h``: hours from run start to the start of
the in-band stretch that ended the run (blank when fewer than half recovered), runs that
recovered (``peg_recovered``), defender spend (mean), pool liquidity at the trough (mean
``sqrt(k/k0)``), the LP's executed withdrawals, and ``panic steps``: in the matching
no-LP run with the same seed, the steps after the attack starts on which AMM spot was
below the LP's panic price, i.e. the withdrawals an LP whose own flight changed nothing
would have made. ``withdrawals > panic steps`` means the LP's withdrawals kept the price
below its threshold longer: its flight fed its own panic.

    python scripts/lp_flight_table.py [--sweep output/lp-flight-mc] [--output output]
        [--workers N]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from depeg_sim.analysis.charts import CAPITAL_PATH, LP_SHARE_PATH, LP_THRESHOLD_PATH
from depeg_sim.experiments.sweep import SWEEP_MANIFEST, SWEEP_PARQUET, SweepSpec, run_sweep

LP_BASE = Path("scenarios/calibrated-baseline-lp.yaml")
NOLP_BASE = Path("scenarios/calibrated-baseline-ou.yaml")


def _hours(df: pd.DataFrame, interval: float) -> pd.Series:
    return (df["step_of_max_depeg"] + df["steps_to_first_band_entry"]) * interval / 3600


def _held(df: pd.DataFrame, interval: float) -> pd.Series:
    """Hours from run start to the start of the in-band stretch that ended the run."""
    return (df["step_of_max_depeg"] + df["steps_to_sustained_recovery"]) * interval / 3600


def _cell_dirs(sweep_dir: Path) -> dict[int, Path]:
    return {int(p.name.split("-")[0]): p for p in sweep_dir.iterdir() if p.is_dir()}


def _withdrawals(cell: Path) -> int:
    with open(cell / "events.jsonl", encoding="utf-8") as f:
        return sum(json.loads(line)["kind"] == "liquidity_removed" for line in f)


def _panic_steps(cell: Path, threshold_pct: float, start_step: int) -> int:
    dev = pd.read_parquet(cell / "timeseries.parquet", columns=["step", "peg_deviation"])
    after = dev[dev["step"] >= start_step]
    return int((after["peg_deviation"] < -threshold_pct / 100).sum())


def load_runs(sweep_dir: Path) -> pd.DataFrame:
    """``sweep.parquet`` with each run's cell directory (``cell``)."""
    runs = pd.read_parquet(sweep_dir / SWEEP_PARQUET)
    cells = _cell_dirs(sweep_dir)
    runs["cell"] = [cells[int(i)] for i in runs["index"]]
    return runs


def _sweep(name, base, axes, seeds, max_steps, output, workers) -> pd.DataFrame:
    spec = SweepSpec(version=1, name=name, base=base, axes=axes, seeds=seeds, max_steps=max_steps)
    return load_runs(run_sweep(spec, output, workers=workers))


def table(lp: pd.DataFrame, nolp: pd.DataFrame, keys: list[str], interval: float,
          start_step: int) -> pd.DataFrame:  # fmt: skip
    """One row per ``keys`` cell of ``lp`` plus a ``no LP`` row per value of the first key
    shared with ``nolp`` (or one row when ``nolp`` has no such key)."""
    shared = [k for k in keys if k in nolp.columns]
    nolp = nolp.assign(hours=_hours(nolp, interval), held=_held(nolp, interval))
    nolp = nolp.set_index(["seed", *shared])
    lp = lp.assign(hours=_hours(lp, interval), held=_held(lp, interval))
    rows = []

    def summarise(g: pd.DataFrame, label: dict, base_trough: float | None) -> dict:
        n = len(g)
        entered = g["hours"].notna().sum()
        trough = g["max_depeg_bps"].mean()
        return label | {
            "trough_bps": round(trough, 1),
            "vs_no_lp": "" if base_trough is None else f"{trough / base_trough - 1:+.1%}",
            "hours": f"{g['hours'].median():.1f}" if entered >= n / 2 else "never",
            "held_h": f"{g['held'].median():.2f}" if g["held"].notna().sum() >= n / 2 else "",
            "recovered": f"{(g['terminated_by'] == 'peg_recovered').sum()}/{n}",
            "defender_M": round(g["defender_spent"].mean() / 1e6, 2),
            "liq_at_trough": round(g["pool_liquidity_at_trough"].mean(), 3),
        }

    for key, g in nolp.reset_index().groupby(shared or (lambda _: 0), sort=True):
        label = dict(zip(shared, key if isinstance(key, tuple) else (key,), strict=False))
        rows.append(summarise(g, {"cell": "no LP"} | label, None))
    for key, g in lp.groupby(keys, sort=True):
        label = dict(zip(keys, key, strict=True))
        match = tuple(label[k] for k in shared)
        ref = nolp.loc[[(s, *match) if match else s for s in g["seed"]]]
        row = summarise(g, {"cell": "LP"} | label, ref["max_depeg_bps"].mean())
        thr = label[LP_THRESHOLD_PATH]
        row["withdrawals"] = g["cell"].map(_withdrawals).median()
        row["panic_steps"] = pd.Series(
            [_panic_steps(c, thr, start_step) for c in ref["cell"]]
        ).median()
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.rename(
        columns={CAPITAL_PATH: "capital", LP_SHARE_PATH: "share", LP_THRESHOLD_PATH: "thr"}
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sweep", type=Path, default=Path("output/lp-flight-mc"))
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = p.parse_args(argv)

    manifest = json.loads((args.sweep / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    base = manifest["base_config"]
    seeds, max_steps = manifest["seeds"], manifest.get("max_steps")
    interval = base["steps"]["interval_seconds"]
    attacker = next(a for a in base["agents"] if a["type"] == "attacker")
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    resources = defender["budget"] + base["redemption"]["reserves"]
    axes = {a["name"]: a["values"] for a in manifest["axes"]}
    lp_axes = {k: axes[k] for k in (LP_SHARE_PATH, LP_THRESHOLD_PATH)}
    w, out = args.workers, args.output

    lp = load_runs(args.sweep)
    nolp = _sweep("lp-flight-nolp", NOLP_BASE, {CAPITAL_PATH: axes[CAPITAL_PATH]}, seeds,
                  max_steps, out, w)  # fmt: skip
    ep = _sweep("lp-flight-episode", LP_BASE, lp_axes, seeds, max_steps, out, w)
    ep_nolp = _sweep("lp-flight-episode-nolp", NOLP_BASE, {}, seeds, max_steps, out, w)

    pd.set_option("display.width", 200)
    keys = [CAPITAL_PATH, LP_SHARE_PATH, LP_THRESHOLD_PATH]
    a = table(lp, nolp, keys, interval, attacker["start_step"])
    a.insert(1, "ratio", (a.pop("capital") / resources).round(2))
    print(f"A. sweep attacks ({len(seeds)} seeds per cell)")
    print(a.fillna("").to_string(index=False))
    print()
    b = table(ep, ep_nolp, keys[1:], interval, attacker["start_step"])
    print(
        f"B. episode attack: capital {attacker['capital']:,} "
        f"(ratio {attacker['capital'] / resources:.3f}; {len(seeds)} seeds per cell)"
    )
    print(b.fillna("").to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
