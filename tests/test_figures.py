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


def test_guard_checks_a_second_source(tmp_path):
    """Story 5.1: a two-run overlay is stale when either of its scenarios changes."""
    h = load_scenario("scenarios/usdc-2023.yaml").content_hash()
    h_par = load_scenario("scenarios/usdc-2023-par.yaml").content_hash()
    second = {"second_source": "scenarios/usdc-2023-par.yaml"}
    m = _manifest(
        tmp_path,
        {
            "both_current": _entry("a.png", "scenarios/usdc-2023.yaml", h)
            | second | {"second_source_hash": h_par},
            "second_stale": _entry("b.png", "scenarios/usdc-2023.yaml", h)
            | second | {"second_source_hash": "0" * 64},
        },
    )  # fmt: skip
    out = guard(m)
    assert out.returncode == 1
    assert "second_stale: STALE, scenarios/usdc-2023-par.yaml changed" in out.stderr
    assert "both_current" not in out.stderr
    assert "FAIL, 1 problem(s) in 2 figures" in out.stderr


def test_guard_checks_an_observed_source(tmp_path):
    """Story 5.5: the scenario run only for its CSV is checked like the other two."""
    par = "scenarios/usdc-2023-tranches-par.yaml"
    closed = "scenarios/usdc-2023-tranches-par-closed.yaml"
    obs = "scenarios/usdc-2023-tranches.yaml"
    entry = _entry("a.png", par, load_scenario(par).content_hash()) | {
        "second_source": closed,
        "second_source_hash": load_scenario(closed).content_hash(),
        "observed_source": obs,
    }
    m = _manifest(
        tmp_path,
        {
            "current": entry | {"observed_source_hash": load_scenario(obs).content_hash()},
            "observed_stale": entry | {"file": "b.png", "observed_source_hash": "0" * 64},
        },
    )
    out = guard(m)
    assert out.returncode == 1
    assert f"observed_stale: STALE, {obs} changed" in out.stderr
    assert "current:" not in out.stderr
    assert "FAIL, 1 problem(s) in 2 figures" in out.stderr


def test_registry_names_every_source_once_per_file():
    files = [f.file for f in make_figures.FIGURES]
    assert len(files) == len(set(files)) == 25  # Story 5.4: LP disposal
    for f in make_figures.FIGURES:
        assert Path(f.source).is_file(), f.source
        assert f.second is None or Path(f.second).is_file(), f.second
        assert f.observed is None or Path(f.observed).is_file(), f.observed
        assert f.observed is None or f.second is not None
    assert {f.function_name for f in make_figures.FIGURES} == {
        "depeg_sim.analysis.charts.plot_peg_trajectory",
        "depeg_sim.analysis.charts.plot_validation_overlay",
        "depeg_sim.analysis.charts.plot_threshold_surface",
        "depeg_sim.analysis.charts.plot_time_to_parity",
        "depeg_sim.analysis.charts.plot_budget_depth",
        "depeg_sim.analysis.charts.plot_oracle_sensitivity",
        "depeg_sim.analysis.charts.plot_policy_comparison",
        "depeg_sim.analysis.charts.plot_holder_exit",
        "depeg_sim.analysis.charts.plot_budget_attack",
        "depeg_sim.analysis.charts.plot_pace_trigger",
        "depeg_sim.analysis.charts.plot_pace_ratio",
        "depeg_sim.analysis.charts.plot_lp_flight",
        "depeg_sim.analysis.charts.plot_identification_surface",
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


# Story 3.5 AC 3: the code hash warns, the source hash fails ------------------------------


def test_code_hash_covers_paths_and_bytes_in_sorted_order(tmp_path):
    pkg = tmp_path / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "sub" / "b.py").write_text('"""doc."""\n')
    (pkg / "notes.txt").write_text("not code")
    h = check_figures.code_hash(pkg)
    assert h == check_figures.code_hash(pkg) and len(h) == 64
    (pkg / "notes.txt").write_text("still not code")
    assert check_figures.code_hash(pkg) == h  # only *.py counts
    (pkg / "sub" / "b.py").write_text('"""doc, edited."""\n')
    edited = check_figures.code_hash(pkg)
    assert edited != h  # a docstring edit changes the hash
    (pkg / "sub" / "b.py").rename(pkg / "c.py")
    assert check_figures.code_hash(pkg) != edited  # so does a rename


def _with_code_hash(path: Path, value: str | None) -> Path:
    m = json.loads(path.read_text())
    if value is not None:
        m["code_hash"] = value
    path.write_text(json.dumps(m))
    return path


def _current(tmp_path) -> Path:
    h = load_scenario("scenarios/soros-baseline.yaml").content_hash()
    return _manifest(tmp_path, {"a": _entry("a.png", "scenarios/soros-baseline.yaml", h)})


def test_guard_silent_when_code_hash_matches(tmp_path):
    out = guard(_with_code_hash(_current(tmp_path), check_figures.code_hash()))
    assert out.returncode == 0, out.stderr
    assert "ok, 1 figures match their sources (code_hash matches)" in out.stdout
    assert "WARNING" not in out.stderr


@pytest.mark.parametrize("recorded", [None, "0" * 64])
def test_guard_warns_but_passes_on_code_hash_mismatch(tmp_path, recorded):
    out = guard(_with_code_hash(_current(tmp_path), recorded))
    assert out.returncode == 0, out.stderr
    assert "WARNING: figures were drawn by other code" in out.stderr
    assert check_figures.code_hash() in out.stderr  # names the current hash in full
    assert ("no code_hash" if recorded is None else f"code_hash {recorded}") in out.stderr
    assert "code differs, see warning" in out.stdout


def test_guard_fails_on_source_mismatch_even_with_matching_code(tmp_path):
    m = _manifest(tmp_path, {"s": _entry("s.png", "scenarios/usdc-2023.yaml", "0" * 64)})
    out = guard(_with_code_hash(m, check_figures.code_hash()))
    assert out.returncode == 1
    assert "s: STALE" in out.stderr and "WARNING" not in out.stderr


def test_guard_annotates_on_github_actions(tmp_path):
    import os

    out = subprocess.run(
        [sys.executable, "scripts/check_figures.py", "--manifest", str(_current(tmp_path))],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GITHUB_ACTIONS": "true"},
    )
    assert out.returncode == 0
    assert out.stdout.startswith("::warning title=figures-check::WARNING")


def test_figures_sharing_a_scenario_keep_both_pngs(tmp_path, monkeypatch):
    """Story 5.1: the par overlay reruns usdc-2023; the first overlay's PNG must survive
    until it is copied (make figures failed with FileNotFoundError before the fix)."""
    from depeg_sim.experiments.sweep import set_path

    def short(path):
        return set_path(load_scenario(path), "steps.max_steps", 8400)

    monkeypatch.setattr(make_figures, "load_scenario", short)
    by_file = {f.file: f for f in make_figures.FIGURES}
    first = make_figures.render(by_file["validation_overlay_usdc_2023.png"], tmp_path, tmp_path)
    second = make_figures.render(
        by_file["validation_overlay_usdc_2023_par.png"], tmp_path, tmp_path
    )
    assert first.is_file() and second.is_file() and first != second
