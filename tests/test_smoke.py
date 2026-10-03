import re

from depeg_sim import __version__
from depeg_sim.cli import main


def test_version():
    assert __version__ == "0.1.0"


def test_cli_runs_on_baseline_scenario(capsys, tmp_path):
    rc = main(["scenarios/soros-baseline.yaml", "--output", str(tmp_path)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert re.fullmatch(r"depeg-sim: scenario=soros-baseline seed=42 hash=[0-9a-f]{12}", lines[0])
    assert re.fullmatch(
        r"run: steps=\d+ terminated_by=peg_recovered max_depeg_bps=-\d+\.\d "
        r"reserves_exhausted=False",
        lines[1],
    )
    m = re.fullmatch(r"wrote: (.+)", lines[2])
    run_dir = tmp_path / m.group(1).rsplit("/", 1)[-1]
    assert m.group(1) == str(run_dir)
    assert (run_dir / "peg_trajectory.png").is_file()
    assert (run_dir / "summary.json").is_file()


def test_cli_no_chart(capsys, tmp_path):
    assert main(["scenarios/soros-baseline.yaml", "--output", str(tmp_path), "--no-chart"]) == 0
    (run_dir,) = tmp_path.iterdir()
    assert (run_dir / "timeseries.parquet").is_file()
    assert not (run_dir / "peg_trajectory.png").exists()
    assert len(capsys.readouterr().out.splitlines()) == 3


def test_cli_seed_override_reported(capsys, tmp_path):
    assert main(["scenarios/soros-baseline.yaml", "--seed", "7", "--output", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert " seed=7 " in out
    assert "soros-baseline-7-" in out


def test_cli_missing_scenario(tmp_path):
    assert main(["scenarios/does-not-exist.yaml", "--output", str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []


def test_cli_invalid_scenario_exits_3(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        open("scenarios/soros-baseline.yaml").read().replace("version: 1", "version: 2"),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert main([str(bad), "--output", str(out)]) == 3
    captured = capsys.readouterr()
    assert "version" in captured.err
    assert captured.out == ""
    assert not out.exists()
