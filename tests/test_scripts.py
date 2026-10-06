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
