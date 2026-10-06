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

    python scripts/policy_table.py [output/policy-comparison-mc]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from depeg_sim.analysis.stats import wilson
from depeg_sim.experiments.sweep import SWEEP_MANIFEST, SWEEP_PARQUET

CAPITAL = "agents[type=attacker].capital"


def table(sweep_dir: Path) -> pd.DataFrame:
    sweep_dir = Path(sweep_dir)
    manifest = json.loads((sweep_dir / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    runs = pd.read_parquet(sweep_dir / SWEEP_PARQUET)
    interval = manifest["base_config"]["steps"]["interval_seconds"]
    runs["arb_redeemed"] = runs["arbitrageur_redeemed"]
    runs["holder_redeemed"] = runs["redemption_paid_total"] - runs["arbitrageur_redeemed"]
    runs["hours"] = (
        (runs["step_of_max_depeg"] + runs["steps_to_first_band_entry"]) * interval / 3600
    )
    resources = manifest["base_config"]["redemption"]["reserves"] + next(
        a["budget"] for a in manifest["base_config"]["agents"] if a["type"] == "defender"
    )
    rows = []
    for (policy, capital), g in runs.groupby(["policy", CAPITAL], sort=False):
        n = len(g)
        k = int((g["terminated_by"] != "peg_recovered").sum())
        lo, hi = wilson(k, n)
        entered = g["hours"].notna().sum()
        rows.append(
            {
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
                "p_broken": k / n,
                "p_lo": lo,
                "p_hi": hi,
            }
        )
    df = pd.DataFrame(rows)
    none = df[df["policy"] == "no-defense"].set_index("ratio")["ttp_h"]
    df["hours_saved"] = df["ratio"].map(none) - df["ttp_h"]
    df["spent_per_hour_saved"] = df["defender_spent"] / df["hours_saved"].where(
        df["hours_saved"] > 0
    )
    return df


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    sweep_dir = Path(args[0]) if args else Path("output/policy-comparison-mc")
    df = table(sweep_dir)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    fmt = {c: "{:,.0f}".format for c in df.columns if c.endswith(("spent", "bought", "paid"))}
    fmt |= {c: "{:,.0f}".format for c in ("arb_redeemed", "holder_redeemed")}
    fmt |= {"spent_per_hour_saved": "{:,.0f}".format}
    print(df.sort_values(["ratio", "policy"]).to_string(index=False, formatters=fmt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
