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
