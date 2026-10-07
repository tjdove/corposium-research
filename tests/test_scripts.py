"""Stories 2.4, 2.6: the analysis scripts' dry runs (no sweeps in CI)."""

import subprocess
import sys

import pytest


def dry_run(script: str, *args: str) -> str:
    out = subprocess.run(
        [sys.executable, f"scripts/{script}", "--dry-run", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_fit_depth_dry_run_lists_grid():
    text = dry_run("fit_depth.py")
    grid = next(line for line in text.splitlines() if line.startswith("grid (9): "))
    assert grid.split(": ", 1)[1].split(", ")[0] == "1,000,000"
    assert grid.endswith("500,000,000")
    assert "extension if no grid depth reaches the target" in text


def test_probe_boundary_dry_run_lists_cells():
    text = dry_run("probe_boundary.py")
    assert "ratios=6 seeds=8" in text and "cells=48" in text
    ratios = [line.split(":")[0] for line in text.splitlines() if line.startswith("ratio ")]
    assert ratios == [f"ratio {r}" for r in ("0.5", "0.75", "1", "1.25", "1.5", "2")]


def test_fit_holder_dry_run_lists_grid():
    text = dry_run("fit_holder.py")
    assert "target_bps=-1373 entry_discount_pct=2 pace=0.05" in text
    grid = next(line for line in text.splitlines() if line.startswith("grid (7): "))
    values = grid.split(": ", 1)[1].split(", ")
    assert values == [
        "1,000,000",
        "2,000,000",
        "5,000,000",
        "10,000,000",
        "20,000,000",
        "50,000,000",
        "100,000,000",
    ]


@pytest.mark.parametrize("script", ["fit_depth.py", "probe_boundary.py", "fit_holder.py"])
def test_dry_run_writes_nothing(script, tmp_path):
    dry_run(script, "--output", str(tmp_path))
    assert list(tmp_path.iterdir()) == []


# Story 3.3: scan_1992 ------------------------------------------------------------------


def test_scan_1992_dry_run_lists_multiples():
    text = dry_run("scan_1992.py", "--holder-capital", "229166675", "--exit", "10")
    head = text.splitlines()[0]
    assert "holder_capital=229,166,675 exit_discount_pct=10 seed=42" in head
    assert "multiples=31 (4..7)" in head
    rows = [line for line in text.splitlines() if line.startswith("multiple ")]
    assert rows[0] == "multiple 4: capital 170,502,984.00 ratio 0.847"
    assert rows[20] == "multiple 6: capital 255,754,476.00 ratio 1.270"  # the committed 6x
    assert len(rows) == 31


def test_scan_1992_dry_run_defaults_to_the_scenario_holder_never_selling(tmp_path):
    text = dry_run("scan_1992.py", "--range", "5.0:5.2:0.1", "--output", str(tmp_path))
    assert "holder_capital=9,166,667 exit_discount_pct=none" in text
    assert "multiples=3 (5..5.2)" in text
    assert list(tmp_path.iterdir()) == []


def test_scan_1992_helpers():
    sys.path.insert(0, "scripts")
    import pandas as pd
    from scan_1992 import flip, multiples, parse_exit, spec_for

    assert multiples("4.0:4.3:0.1") == [4.0, 4.1, 4.2, 4.3]
    with pytest.raises(ValueError):
        multiples("5:4:0.1")
    assert parse_exit("none") is None and parse_exit("NULL") is None and parse_exit("10") == 10
    df = pd.DataFrame(
        {"multiple": [5.0, 5.1, 5.2, 5.3, 5.4], "reserves_exhausted": [1, 0, 1, 1, 1]}
    )
    assert flip(df) == (5.2, [5.0])
    assert flip(df.assign(reserves_exhausted=[1, 0, 1, 1, 0])) == (None, [5.0, 5.2, 5.3])
    assert flip(df.assign(reserves_exhausted=1)) == (5.0, [])
    from pathlib import Path

    spec = spec_for(Path("scenarios/soros-1992.yaml"), [6.0], 229166675.0, None, 42)
    assert spec.overrides == {
        "agents[type=holder].exit_discount_pct": None,
        "agents[type=holder].capital": 229166675.0,
    }
    assert spec.linked_axes[0].path_values(6.0) == [
        ("agents[type=attacker].capital", 6.0 * 42_625_746)
    ]


def test_policy_table_reads_redemptions_from_the_summary(tmp_path):
    """Story 3.5 AC 2: no per-cell events.jsonl; holder share is total minus arbitrageur."""
    import json
    from pathlib import Path

    import pandas as pd

    sys.path.insert(0, str(Path("scripts").resolve()))
    import policy_table

    from depeg_sim.kernel.config import load_scenario

    base = load_scenario("scenarios/calibrated-baseline.yaml").model_dump(mode="json")
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    resources = base["redemption"]["reserves"] + defender["budget"]
    (tmp_path / "manifest.json").write_text(json.dumps({"base_config": base}))
    rows = []
    for policy in ("no-defense", "calibrated"):
        for seed in (1, 2):
            rows.append(
                {
                    "index": len(rows), "seed": seed, "policy": policy,
                    policy_table.CAPITAL: resources,
                    "step_of_max_depeg": 50, "steps_to_first_band_entry": 100.0,
                    "terminated_by": "peg_recovered",
                    "defender_spent": None if policy == "no-defense" else 4.0e7,
                    "defender_bought_stable": None if policy == "no-defense" else 1.0e8,
                    "holder_bought_stable": 5.0, "redemption_paid_total": 10.0 + seed,
                    "arbitrageur_redeemed": 4.0,
                }
            )  # fmt: skip
    pd.DataFrame(rows).to_parquet(tmp_path / "sweep.parquet", index=False)
    df = policy_table.table(tmp_path).set_index("policy")
    assert list(df.index) == ["no-defense", "calibrated"]
    assert df.loc["calibrated", "arb_redeemed"] == 4.0
    assert df.loc["calibrated", "holder_redeemed"] == 7.5  # mean of 11 - 4 and 12 - 4
    assert df.loc["calibrated", "ratio"] == 1.0
    assert df.loc["calibrated", "entered"] == "2/2"


# Story 3.6: fit_reversion -----------------------------------------------------------------


def _fit_reversion():
    from pathlib import Path

    sys.path.insert(0, str(Path("scripts").resolve()))
    import fit_reversion

    return fit_reversion


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_fit_reversion_recovers_synthetic_phi(seed):
    import numpy as np

    fr = _fit_reversion()
    rng = np.random.default_rng(seed)
    phi, x = 0.6, [0.0]
    for _ in range(2_000):
        x.append(phi * x[-1] + 5e-4 * rng.standard_normal())
    fit = fr.fit_ar1(np.array(x))
    assert abs(fit.phi - phi) < 3 * fit.se and fit.se < 0.03
    assert fit.significant
    assert fit.resid_sd == pytest.approx(5e-4, rel=0.1)


def test_fit_reversion_random_walk_is_not_significant():
    import numpy as np

    fr = _fit_reversion()
    hits = 0
    for seed in range(40):
        walk = np.cumsum(np.random.default_rng(seed).standard_normal(120)) * 1e-4
        hits += fr.fit_ar1(walk).significant
    assert hits <= 6  # a 5% test: about 2 of 40 false rejections expected


def test_fit_reversion_conversions():
    fr = _fit_reversion()
    k = fr.kappa_step(0.5, 12)
    assert (1 - k) ** 300 == pytest.approx(0.5, rel=1e-12)
    assert fr.half_life_hours(0.5) == pytest.approx(1.0)
    assert fr.stationary_sd(0.6, 0.8) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="identically zero"):
        fr.fit_ar1([0.0, 0.0, 0.0])


def test_fit_reversion_dry_run_states_the_rule():
    text = dry_run("fit_reversion.py")
    assert "no constant" in text and "-1.95" in text and "1 / 300" in text


def test_fit_reversion_on_the_calm_series_matches_the_scenario():
    """The committed kappa is the fit's output rounded to 4 significant figures."""
    from depeg_sim.kernel.config import load_scenario

    fr = _fit_reversion()
    fit = fr.fit_ar1(fr.deviations(fr.CALM))
    assert fit.significant
    k = fr.kappa_step(fit.phi, 12)
    cfg = load_scenario("scenarios/calibrated-baseline-ou.yaml")
    assert cfg.environment.mean_reversion_per_step == float(f"{k:.4g}")
