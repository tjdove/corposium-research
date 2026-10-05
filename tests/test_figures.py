"""Story 2.9: the stale-figure guard and the figure registry (no sweeps run here)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))

import check_figures  # noqa: E402
import make_figures  # noqa: E402

from depeg_sim.experiments.sweep import load_sweep, sweep_spec_hash  # noqa: E402
from depeg_sim.kernel.config import load_scenario  # noqa: E402


def guard(manifest: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/check_figures.py", "--manifest", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )


def _entry(file, source, source_hash):
    return {"file": file, "source": source, "source_hash": source_hash, "function": "f",
            "commit": "c"}  # fmt: skip


def _manifest(tmp_path, entries: dict) -> Path:
    for e in entries.values():
        (tmp_path / e["file"]).write_bytes(b"png")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(entries))
    return path


def test_source_hash_kinds():
    assert check_figures.source_hash(Path("scenarios/usdc-2023.yaml")) == (
        load_scenario("scenarios/usdc-2023.yaml").content_hash()
    )
    spec = Path("sweeps/oracle-lag-mc.yaml")
    assert check_figures.source_hash(spec) == sweep_spec_hash(spec)


def test_guard_passes_when_every_hash_matches(tmp_path):
    m = _manifest(
        tmp_path,
        {
            "a": _entry("a.png", "scenarios/soros-baseline.yaml",
                        load_scenario("scenarios/soros-baseline.yaml").content_hash()),
            "b": _entry("b.png", "sweeps/oracle-lag-mc.yaml",
                        sweep_spec_hash("sweeps/oracle-lag-mc.yaml")),
        },
    )  # fmt: skip
    out = guard(m)
    assert out.returncode == 0, out.stderr
    assert "ok, 2 figures" in out.stdout


def test_guard_names_each_stale_figure(tmp_path):
    m = _manifest(
        tmp_path,
        {
            "current": _entry("current.png", "scenarios/soros-baseline.yaml",
                              load_scenario("scenarios/soros-baseline.yaml").content_hash()),
            "stale_scenario": _entry("s.png", "scenarios/usdc-2023.yaml", "0" * 64),
            "stale_sweep": _entry("w.png", "sweeps/budget-x-depth-mc.yaml", "f" * 64),
        },
    )  # fmt: skip
    out = guard(m)
    assert out.returncode == 1
    assert "stale_scenario: STALE, scenarios/usdc-2023.yaml changed" in out.stderr
    assert (
        "stale_sweep: STALE, sweeps/budget-x-depth-mc.yaml or its base scenario changed"
        in out.stderr
    )
    assert "current" not in out.stderr
    assert "FAIL, 2 problem(s) in 3 figures" in out.stderr


def test_guard_fails_on_missing_png_or_source(tmp_path):
    h = load_scenario("scenarios/soros-baseline.yaml").content_hash()
    m = _manifest(tmp_path, {"gone": _entry("gone.png", "scenarios/nope.yaml", h)})
    (tmp_path / "gone.png").unlink()
    out = guard(m)
    assert out.returncode == 1
    assert "figure file gone.png is missing" in out.stderr
    assert "source scenarios/nope.yaml is missing" in out.stderr


def test_registry_names_every_source_once_per_file():
    files = [f.file for f in make_figures.FIGURES]
    assert len(files) == len(set(files)) == 10
    for f in make_figures.FIGURES:
        assert Path(f.source).is_file(), f.source
    assert {f.function_name for f in make_figures.FIGURES} == {
        "depeg_sim.analysis.charts.plot_peg_trajectory",
        "depeg_sim.analysis.charts.plot_validation_overlay",
        "depeg_sim.analysis.charts.plot_threshold_surface",
        "depeg_sim.analysis.charts.plot_time_to_parity",
        "depeg_sim.analysis.charts.plot_budget_depth",
        "depeg_sim.analysis.charts.plot_oracle_sensitivity",
    }


@pytest.mark.parametrize("recorded", [None, "0" * 64])
def test_full_run_refuses_a_sweep_from_another_spec(tmp_path, recorded):
    for spec in {f.source for f in make_figures.FIGURES if check_figures.is_sweep(Path(f.source))}:
        d = tmp_path / load_sweep(spec).name
        d.mkdir()
        (d / "mc.parquet").write_bytes(b"")
        good = sweep_spec_hash(spec)
        bad = spec == "sweeps/budget-x-depth-mc.yaml"
        (d / "manifest.json").write_text(json.dumps({"spec_hash": recorded if bad else good}))
    problems = make_figures.check_sweep_dirs(tmp_path)
    assert len(problems) == 1
    assert "budget-x-depth-mc" in problems[0] and "does not match" in problems[0]
