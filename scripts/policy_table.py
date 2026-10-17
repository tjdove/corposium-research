"""Story 3.2 AC 5: the defender-policy table from a ``policy-comparison-mc`` sweep.

Reads ``<sweep_dir>/sweep.parquet`` and the sweep manifest only (no per-cell files;
Story 3.5) and prints, per policy and attack ratio, means over seeds of: defender spent
and stable bought, holder stable bought, redemption paid in total and to the arbitrageur
(``arbitrageur_redeemed``) and the holder (``redemption_paid_total -
arbitrageur_redeemed``: the arbitrageur and the holder are the only agents that redeem);
the median hours from run start to first re-entry into the recovery band ("never" when
fewer than half the seeds re-enter, as ``charts.time_to_parity_hours``);
``p_stays_broken`` with Wilson 95% bounds; and, against no-defense at the same ratio,
hours saved and defender spend per hour saved.

Story 5.3 adds, per row, the average price the defender paid per stable (``price_paid``,
mean over the seeds that bought of ``defender_spent / defender_bought_stable``, as panel
(b) of ``plot_policy_comparison``) and the mean ``discount_bps_hours`` (``disc_bps_h``;
NaN for a sweep run before the metric existed). ``--sweep DIR`` names the sweep
directory (the positional argument still works). A sweep with an attacker-pace axis
(``sweeps/policy-comparison-gradual-mc.yaml``) is grouped by pace as well, and a second
table gives, per pace and ratio, **which policy minimises ``discount_bps_hours`` and which
minimises time to parity** (ties joined with ``=``; "none" when no policy re-enters),
with ``agree`` saying whether they are the same (yes / no; "-" when either is "none").

    python scripts/policy_table.py [--sweep output/policy-comparison-gradual-mc]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from depeg_sim.analysis.stats import wilson
from depeg_sim.experiments.sweep import SWEEP_MANIFEST, SWEEP_PARQUET

CAPITAL = "agents[type=attacker].capital"
PACE = "agents[type=attacker].pace"
DISCOUNT = "discount_bps_hours"


def table(sweep_dir: Path) -> pd.DataFrame:
    sweep_dir = Path(sweep_dir)
    manifest = json.loads((sweep_dir / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    runs = pd.read_parquet(sweep_dir / SWEEP_PARQUET)
    if DISCOUNT not in runs:  # a sweep run before Story 5.3
        runs[DISCOUNT] = float("nan")
    bought = runs["defender_bought_stable"].where(runs["defender_bought_stable"] > 0)
    runs["price_paid"] = runs["defender_spent"] / bought
    paced = PACE in runs and any(PACE in a.get("paths", ()) for a in manifest.get("axes", []))
    keys = ["policy", CAPITAL] + ([PACE] if paced else [])
    interval = manifest["base_config"]["steps"]["interval_seconds"]
    runs["arb_redeemed"] = runs["arbitrageur_redeemed"]
    # the difference of two float sums: clip the ~1e-9 residue where the holder never redeemed
    runs["holder_redeemed"] = (runs["redemption_paid_total"] - runs["arbitrageur_redeemed"]).clip(
        lower=0.0
    )
    runs["hours"] = (
        (runs["step_of_max_depeg"] + runs["steps_to_first_band_entry"]) * interval / 3600
    )
    resources = manifest["base_config"]["redemption"]["reserves"] + next(
        a["budget"] for a in manifest["base_config"]["agents"] if a["type"] == "defender"
    )
    rows = []
    for key, g in runs.groupby(keys, sort=False):
        policy, capital = key[0], key[1]
        n = len(g)
        k = int((g["terminated_by"] != "peg_recovered").sum())
        lo, hi = wilson(k, n)
        entered = g["hours"].notna().sum()
        rows.append(
            ({"attacker_pace": key[2]} if paced else {})
            | {
                "policy": policy,
                "ratio": round(capital / resources, 2),
                "defender_spent": g["defender_spent"].fillna(0).mean(),
                "defender_bought": g["defender_bought_stable"].fillna(0).mean(),
                "holder_bought": g["holder_bought_stable"].mean(),
                "redemption_paid": g["redemption_paid_total"].mean(),
                "arb_redeemed": g["arb_redeemed"].mean(),
                "holder_redeemed": g["holder_redeemed"].mean(),
                "ttp_h": g["hours"].median() if entered >= n / 2 else float("nan"),
                "entered": f"{entered}/{n}",
                "price_paid": g["price_paid"].mean(),
                "disc_bps_h": g[DISCOUNT].mean(),
                "p_broken": k / n,
                "p_lo": lo,
                "p_hi": hi,
            }
        )
    df = pd.DataFrame(rows)
    cell = ["attacker_pace", "ratio"] if paced else ["ratio"]
    none = df.loc[df["policy"] == "no-defense", [*cell, "ttp_h"]]
    df = df.merge(none.rename(columns={"ttp_h": "none_ttp_h"}), on=cell, how="left")
    df["hours_saved"] = df.pop("none_ttp_h") - df["ttp_h"]
    df["spent_per_hour_saved"] = df["defender_spent"] / df["hours_saved"].where(
        df["hours_saved"] > 0
    )
    return df


def _argmin(g: pd.DataFrame, col: str) -> str:
    """The policy (or ``=``-joined tied policies) with the smallest ``col``; "none" if all NaN."""
    v = g[col]
    if v.isna().all():
        return "none"
    return "=".join(g.loc[v == v.min(), "policy"])


def winners(df: pd.DataFrame) -> pd.DataFrame:
    """Per (pace,) ratio: the policy minimising mean ``disc_bps_h`` and the one minimising
    median time to parity, side by side (AC 4)."""
    cell = [c for c in ("attacker_pace", "ratio") if c in df]
    rows = []
    for key, g in df.groupby(cell, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        by_disc, by_ttp = _argmin(g, "disc_bps_h"), _argmin(g, "ttp_h")
        rows.append(
            dict(zip(cell, key, strict=True))
            | {
                "min_discount": by_disc,
                "disc_bps_h": g["disc_bps_h"].min(),
                "min_time_to_parity": by_ttp,
                "ttp_h": g["ttp_h"].min(),
                "agree": "-"
                if "none" in (by_disc, by_ttp)
                else "yes"
                if by_disc == by_ttp
                else "no",
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("sweep_dir", nargs="?", type=Path, default=None)
    p.add_argument("--sweep", type=Path, default=None, help="sweep output directory")
    args = p.parse_args(argv)
    sweep_dir = args.sweep or args.sweep_dir or Path("output/policy-comparison-mc")
    df = table(sweep_dir)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    fmt = {c: "{:,.0f}".format for c in df.columns if c.endswith(("spent", "bought"))}
    fmt |= {c: "{:,.0f}".format for c in ("redemption_paid", "arb_redeemed", "holder_redeemed")}
    fmt |= {"spent_per_hour_saved": "{:,.0f}".format, "price_paid": "{:.3f}".format}
    fmt |= {"disc_bps_h": "{:,.0f}".format}
    order = [c for c in ("attacker_pace", "ratio", "policy") if c in df]
    ascending = [c != "attacker_pace" for c in order]
    print(df.sort_values(order, ascending=ascending).to_string(index=False, formatters=fmt))
    if "attacker_pace" in df:
        w = winners(df).sort_values(["attacker_pace", "ratio"], ascending=[False, True])
        print()
        print("which policy minimises discount_bps_hours, and which time to parity:")
        fmt = {"disc_bps_h": "{:,.0f}".format, "ttp_h": "{:.1f}".format}
        print(w.to_string(index=False, formatters=fmt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
