from depeg_sim import __version__
from depeg_sim.cli import main


def test_version():
    assert __version__ == "0.1.0"


def test_cli_runs_on_baseline_scenario(capsys):
    rc = main(["scenarios/soros-baseline.yaml"])
    assert rc == 0
    assert "soros-baseline" in capsys.readouterr().out


def test_cli_missing_scenario():
    assert main(["scenarios/does-not-exist.yaml"]) == 2
