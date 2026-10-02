import re

from depeg_sim import __version__
from depeg_sim.cli import main


def test_version():
    assert __version__ == "0.1.0"


def test_cli_runs_on_baseline_scenario(capsys):
    rc = main(["scenarios/soros-baseline.yaml"])
    assert rc == 0
    out = capsys.readouterr().out
    assert re.search(r"^depeg-sim: scenario=soros-baseline seed=42 hash=[0-9a-f]{12}$", out, re.M)
    assert "kernel not implemented yet" in out


def test_cli_missing_scenario():
    assert main(["scenarios/does-not-exist.yaml"]) == 2


def test_cli_invalid_scenario_exits_3(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        open("scenarios/soros-baseline.yaml").read().replace("version: 1", "version: 2"),
        encoding="utf-8",
    )
    assert main([str(bad)]) == 3
    captured = capsys.readouterr()
    assert "version" in captured.err
    assert captured.out == ""
