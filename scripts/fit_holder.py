"""Fit the par-expecting buyer's capital C* to the observed March-2023 trough (Story 2.6, F-08).

On the USDC replay (``scenarios/usdc-2023.yaml``), with D* and everything else held fixed,
puts one holder in the scenario (``entry_discount_pct``, ``pace``, ``redeem_when_capacity
true``; an existing holder entry is replaced) and sweeps its ``capital`` with
``run_sweep``, reading ``sweep.parquet``.

Selection rule (story 2.6 AC 4), applied mechanically:

1. Run the log grid ``GRID``. The pick is the grid capital whose ``max_depeg_bps`` is
   closest to the target (default -1373, the Bitstamp hourly low 0.86267).
2. Refine with 5 evenly spaced capitals strictly between the pick's two grid neighbours
   (between the pick and its one neighbour at either end of the grid).
3. Re-pick the closest among everything run so far and refine once more with 5 points
   strictly between its new neighbours in that sorted set (amended 2026-10-04).
4. ``C*`` is the capital closest to the target among every point run (ties go to the
   smaller capital). Stop there.

Prints the grid table, the two refinement tables, then ``C* = <units> (trough <bps>) ≈
$<dollars>`` with dollars = units / s (SOURCES.md). ``--dry-run`` prints the grid and exits.

``--tranches entry:share,…`` (Story 3.7) gives the holder a ladder of entry prices instead
of ``--entry-discount`` (e.g. ``1:0.5,2:0.3,5:0.2``); ``capital`` is the ladder's total and
the rule above is unchanged. Sweep directories get a ``-tranches-<entries>`` suffix so the
three ladders' runs do not overwrite each other.

``--at-multiples-of C`` (Story 3.7's cliff test) skips the fit: it runs the holder at
``round(C x m)`` for ``m`` in ``MULTIPLES`` and prints that one table.

``--write PATH`` (Story 4.1) also writes the fit record (``scripts/fit_record.py``): the
scenario and its replay series with their hashes, the holder arguments, every capital run
and ``C*``. Not with ``--at-multiples-of`` (that is not a fit).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from fit_record import fit_record, script_path, write_fit

from depeg_sim.experiments.sweep import SWEEP_PARQUET, SweepSpec, run_sweep
from depeg_sim.kernel.config import ScenarioConfig, load_scenario

GRID = [1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000, 100_000_000]
REFINE_POINTS = 5
MULTIPLES = [0.8, 0.9, 1.0, 1.1, 1.2]  # the cliff test (Story 3.7 AC 4)
S = 1_000_000 / 234_600_000  # model units per $ (SOURCES.md)
HOLDER_ID = "holder-1"
CAPITAL_PATH = "agents[type=holder].capital"
COLUMNS = ["holder_capital", "max_depeg_bps", "step_of_max_depeg", "terminated_by", "steps_run"]


def parse_tranches(text: str) -> list[tuple[float, float]]:
    """``"1:0.5,2:0.3,5:0.2"`` -> ``[(1.0, 0.5), (2.0, 0.3), (5.0, 0.2)]``."""
    pairs = []
    for item in text.split(","):
        entry, sep, share = item.strip().partition(":")
        if not sep:
            raise argparse.ArgumentTypeError(f"tranche {item!r} is not entry:share")
        pairs.append((float(entry), float(share)))
    return pairs


def with_holder(
    scenario: Path,
    entry_discount: float,
    pace: float,
    tranches: list[tuple[float, float]] | None = None,
) -> ScenarioConfig:
    """The scenario with exactly one holder (capital is a placeholder; the sweep sets it).
    With ``tranches`` the holder has that ladder instead of ``entry_discount``."""
    data = load_scenario(scenario).model_dump(mode="json")
    agents = [a for a in data["agents"] if a["type"] != "holder"]
    holder = {
        "type": "holder",
        "id": HOLDER_ID,
        "capital": GRID[0],
        "entry_discount_pct": entry_discount,
        "pace": pace,
        "redeem_when_capacity": True,
    }
    if tranches is not None:
        del holder["entry_discount_pct"]
        holder["tranches"] = [{"entry_discount_pct": e, "share": s} for e, s in tranches]
    agents.append(holder)
    data["agents"] = agents
    return ScenarioConfig.model_validate(data)


def write_base(cfg: ScenarioConfig, output: Path) -> Path:
    """Write the holder-bearing base where the sweep can load it (series path is absolute)."""
    output.mkdir(parents=True, exist_ok=True)
    path = output / "fit-holder-base.yaml"
    path.write_text(yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False), "utf-8")
    return path


def spec_for(name: str, base: Path, capitals: list[int]) -> SweepSpec:
    return SweepSpec(
        version=1,
        name=name,
        base=base,
        axes={CAPITAL_PATH: capitals},
        seeds=[load_scenario(base).seed],
    )


def refine_between(lo: int, hi: int) -> list[int]:
    """``REFINE_POINTS`` evenly spaced integer capitals strictly between ``lo`` and ``hi``."""
    return [int(round(x)) for x in np.linspace(lo, hi, REFINE_POINTS + 2)[1:-1]]


def run_table(spec: SweepSpec, output: Path, workers: int) -> pd.DataFrame:
    df = pd.read_parquet(run_sweep(spec, output, workers=workers) / SWEEP_PARQUET)
    df = df.rename(columns={CAPITAL_PATH: "holder_capital"})
    return df[COLUMNS].sort_values("holder_capital").reset_index(drop=True)


def closest(df: pd.DataFrame, target: float) -> pd.Series:
    """Row closest to ``target``; ties go to the smaller capital."""
    gap = (df["max_depeg_bps"] - target).abs()
    order = pd.DataFrame({"gap": gap, "c": df["holder_capital"]}).sort_values(["gap", "c"])
    return df.loc[order.index[0]]


def neighbours(capitals: list[int], pick: int) -> tuple[int, int]:
    """The pick's neighbours in ``capitals`` (sorted, unique); the pick itself at an end."""
    i = capitals.index(pick)
    return capitals[max(i - 1, 0)], capitals[min(i + 1, len(capitals) - 1)]


def tried(df: pd.DataFrame) -> pd.DataFrame:
    """Every distinct capital run so far, sorted (a refined point can repeat a grid one)."""
    return df.drop_duplicates("holder_capital").sort_values("holder_capital").reset_index(drop=True)


def show(title: str, df: pd.DataFrame) -> None:
    print(title)
    print(df.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scenario", type=Path, default=Path("scenarios/usdc-2023.yaml"))
    p.add_argument("--target-bps", type=float, default=-1373.0)
    p.add_argument("--entry-discount", type=float, default=2.0)
    p.add_argument("--pace", type=float, default=0.05)
    p.add_argument(
        "--tranches",
        type=parse_tranches,
        default=None,
        help="entry:share,… ladder replacing --entry-discount (Story 3.7)",
    )
    p.add_argument(
        "--at-multiples-of",
        type=int,
        default=None,
        metavar="C",
        help="no fit: run capital round(C x m) for m in 0.8..1.2 (the cliff test)",
    )
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--dry-run", action="store_true", help="List the grid and exit")
    p.add_argument("--write", type=Path, default=None, help="write the fit record here")
    args = p.parse_args(argv)
    if args.write is not None and args.at_multiples_of is not None:
        p.error("--write records a fit; --at-multiples-of is not one")

    entry = (
        f"entry_discount_pct={args.entry_discount:g}"
        if args.tranches is None
        else "tranches=" + ",".join(f"{e:g}:{s:g}" for e, s in args.tranches)
    )
    print(
        f"fit_holder: scenario={args.scenario} target_bps={args.target_bps:g} "
        f"{entry} pace={args.pace:g}"
    )
    print(f"grid ({len(GRID)}): " + ", ".join(f"{c:,}" for c in GRID))
    if args.dry_run:
        return 0

    cfg = with_holder(args.scenario, args.entry_discount, args.pace, args.tranches)
    tag = (
        "" if args.tranches is None else "-tranches-" + "-".join(f"{e:g}" for e, _ in args.tranches)
    )
    base = write_base(cfg, args.output / f"fit-holder-base{tag}")
    if args.at_multiples_of is not None:
        caps = [int(round(args.at_multiples_of * m)) for m in MULTIPLES]
        table = run_table(spec_for(f"fit-holder-cliff{tag}", base, caps), args.output, args.workers)
        table.insert(1, "multiple", MULTIPLES)
        show(f"cliff test at multiples of {args.at_multiples_of:,}:", table)
        return 0
    grid = run_table(spec_for(f"fit-holder{tag}", base, GRID), args.output, args.workers)
    show(f"grid pass (target {args.target_bps:g} bps):", grid)
    seen = grid
    for n, name in enumerate((f"fit-holder-refine{tag}", f"fit-holder-refine2{tag}"), start=1):
        pick = int(closest(seen, args.target_bps)["holder_capital"])
        lo, hi = neighbours(seen["holder_capital"].astype(int).tolist(), pick)
        refined = run_table(spec_for(name, base, refine_between(lo, hi)), args.output, args.workers)
        show(f"refine pass {n} between {lo:,} and {hi:,} (pick {pick:,}):", refined)
        seen = tried(pd.concat([seen, refined]))
    best = closest(seen, args.target_bps)
    c_star = int(best["holder_capital"])
    print(
        f"C* = {c_star} (trough {best['max_depeg_bps']:.1f} bps) ≈ ${c_star / S:,.0f} "
        f"at s = {S:.10f} units/$"
    )
    if args.write is not None:
        series = load_scenario(args.scenario).environment.price_series_path
        result = {
            "c_star": c_star,
            "c_star_usd": round(c_star / S),
            "trough_bps": float(best["max_depeg_bps"]),
            "step_of_max_depeg": int(best["step_of_max_depeg"]),
            "runs": [
                {"holder_capital": int(c), "max_depeg_bps": float(b)}
                for c, b in zip(seen["holder_capital"], seen["max_depeg_bps"], strict=True)
            ],
        }
        args_ = {
            "scenario": args.scenario.as_posix(),
            "target_bps": args.target_bps,
            "entry_discount_pct": None if args.tranches else args.entry_discount,
            "tranches": None if args.tranches is None else [list(t) for t in args.tranches],
            "pace": args.pace,
            "grid": GRID,
            "refine_points": REFINE_POINTS,
            "units_per_usd": S,
        }
        data = None if series is None else _repo_relative(Path(series))
        record = fit_record(script_path(__file__), args.scenario, data, args_, result)
        write_fit(args.write, record)
    return 0


def _repo_relative(path: Path) -> Path:
    """The scenario's (absolute) series path relative to the working directory."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
