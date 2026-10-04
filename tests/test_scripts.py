"""Story 2.4: the analysis scripts' dry runs (no sweeps in CI)."""

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


@pytest.mark.parametrize("script", ["fit_depth.py"])
def test_dry_run_writes_nothing(script, tmp_path):
    dry_run(script, "--output", str(tmp_path))
    assert list(tmp_path.iterdir()) == []
