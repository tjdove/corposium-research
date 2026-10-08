"""Story 4.1 AC 3: fit records under the guard (scripts/fit_record.py, --write, check)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))

import fit_record  # noqa: E402

FITS = Path("docs/calibration/fits")
COMMITTED = ["depth.json", "holder-single.json", "holder-ladder-b.json", "reversion.json"]


def guard(manifest: Path, fits: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/check_figures.py", "--manifest", str(manifest),
         "--fits", str(fits)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip


def _record(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """A fit file in ``tmp_path/fits`` over copies of a real scenario, data file and script
    (all under ``tmp_path``, referenced by absolute path)."""
    scenario = tmp_path / "s.yaml"
    shutil.copy("scenarios/soros-baseline.yaml", scenario)
    data = tmp_path / "d.csv"
    data.write_text("unix,close\n0,1.0\n")
    script = tmp_path / "fit_x.py"
    script.write_text("print('fit')\n")
    record = fit_record.fit_record(script, scenario, data, {"a": 1}, {"x": 2.5})
    path = fit_record.write_fit(tmp_path / "fits" / "x.json", record)
    return path, scenario, data, script


def test_record_shape_and_bytes_are_stable(tmp_path):
    path, scenario, data, script = _record(tmp_path)
    rec = json.loads(path.read_text())
    assert set(rec) == {"script", "script_sha256", "inputs", "result"}
    assert set(rec["inputs"]) == {"scenario", "scenario_hash", "data", "data_sha256", "args"}
    assert rec["inputs"]["data_sha256"] == fit_record.sha256_file(data)
    assert rec["inputs"]["scenario_hash"] == fit_record.scenario_hash(scenario)
    assert rec["result"] == {"x": 2.5}
    first = path.read_bytes()
    fit_record.write_fit(path, fit_record.fit_record(script, scenario, data, {"a": 1}, {"x": 2.5}))
    assert path.read_bytes() == first  # no timestamp: same inputs, same bytes
    assert fit_record.check_fit(path) == ([], [])


def test_changed_scenario_fails(tmp_path):
    path, scenario, _, _ = _record(tmp_path)
    scenario.write_text(scenario.read_text().replace("seed: 42", "seed: 43"))
    problems, warnings = fit_record.check_fit(path)
    assert len(problems) == 1 and "STALE, scenario" in problems[0] and warnings == []


def test_changed_data_fails(tmp_path):
    path, _, data, _ = _record(tmp_path)
    data.write_text("unix,close\n0,0.99\n")
    problems, _ = fit_record.check_fit(path)
    assert len(problems) == 1 and "STALE, data" in problems[0]


def test_missing_input_fails(tmp_path):
    path, _, data, _ = _record(tmp_path)
    data.unlink()
    problems, _ = fit_record.check_fit(path)
    assert problems == [f"x.json: data {data.as_posix()} is missing"]


def test_changed_script_only_warns(tmp_path):
    path, _, _, script = _record(tmp_path)
    script.write_text("print('fit, edited')\n")
    problems, warnings = fit_record.check_fit(path)
    assert problems == [] and len(warnings) == 1 and warnings[0].startswith("WARNING: x.json")


def test_guard_fails_on_a_stale_fit_and_warns_on_a_script(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({}))
    path, _, data, script = _record(tmp_path)
    ok = guard(manifest, path.parent)
    assert ok.returncode == 0, ok.stderr
    assert "ok, 1 fits match their inputs (script hashes match)" in ok.stdout
    script.write_text("# edited\n")
    warned = guard(manifest, path.parent)
    assert warned.returncode == 0 and "WARNING: x.json" in warned.stderr
    assert "a fit script differs" in warned.stdout
    data.write_text("changed\n")
    failed = guard(manifest, path.parent)
    assert failed.returncode == 1
    assert (
        "STALE, data" in failed.stderr and "1 problem(s) in 0 figures and 1 fits" in failed.stderr
    )


@pytest.mark.parametrize("name", COMMITTED)
def test_committed_fits_are_current(name):
    assert fit_record.check_fit(FITS / name) == ([], [])


def test_committed_fits_name_their_inputs():
    recs = {n: json.loads((FITS / n).read_text()) for n in COMMITTED}
    assert recs["depth.json"]["inputs"]["scenario"] == "scenarios/calibrated-baseline.yaml"
    assert recs["depth.json"]["result"]["d_star"] == 16_666_667
    assert recs["holder-single.json"]["result"]["c_star"] == 9_166_667
    assert recs["holder-single.json"]["inputs"]["args"]["entry_discount_pct"] == 2.0
    assert recs["holder-ladder-b.json"]["result"]["c_star"] == 10_833_333
    assert recs["holder-ladder-b.json"]["inputs"]["args"]["tranches"] == [
        [2.0, 0.25], [5.0, 0.25], [10.0, 0.25], [20.0, 0.25]
    ]  # fmt: skip
    for n in ("holder-single.json", "holder-ladder-b.json"):
        assert recs[n]["inputs"]["data"] == "data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv"
    rev = recs["reversion.json"]
    assert rev["inputs"]["scenario"] is None
    assert rev["inputs"]["data"] == "data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv"
    assert round(rev["result"]["kappa_step"], 6) == 0.001634
    assert {r["script"] for r in recs.values()} == {
        "scripts/fit_depth.py", "scripts/fit_holder.py", "scripts/fit_reversion.py"
    }  # fmt: skip


def test_fit_reversion_write_reproduces_committed_bytes(tmp_path):
    out = tmp_path / "reversion.json"
    run = subprocess.run(
        [sys.executable, "scripts/fit_reversion.py", "--write", str(out)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    assert out.read_bytes() == (FITS / "reversion.json").read_bytes()


def test_fit_depth_write_reproduces_committed_bytes(tmp_path):
    out = tmp_path / "depth.json"
    run = subprocess.run(
        [sys.executable, "scripts/fit_depth.py", "--workers", "4", "--output",
         str(tmp_path / "output"), "--write", str(out)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    assert out.read_bytes() == (FITS / "depth.json").read_bytes()


def test_fit_holder_write_refuses_the_cliff_test(tmp_path):
    run = subprocess.run(
        [sys.executable, "scripts/fit_holder.py", "--at-multiples-of", "100", "--write",
         str(tmp_path / "x.json")],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert run.returncode == 2 and "--write records a fit" in run.stderr
