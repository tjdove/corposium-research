import json
import platform
import re

import pandas as pd
from test_metrics import cfg_with

from depeg_sim import __version__
from depeg_sim.experiments.runner import RunArtifacts, build_world, run_scenario
from depeg_sim.kernel.config import ScenarioConfig, load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION

BASELINE = "scenarios/soros-baseline.yaml"
MANIFEST_KEYS = {
    "run_id",
    "scenario_name",
    "scenario_hash",
    "seed",
    "phase_order_version",
    "package_version",
    "python_version",
    "created_utc",
    "files",
    "config",
}


def test_build_world_registration_order():
    cfg = load_scenario(BASELINE)
    ctx = RunContext.from_config(cfg)
    world = build_world(cfg, ctx)
    expected = [
        "environment",
        "oracle",
        "amm",
        "redemption",
        "attacker-1",
        "arb-1",
        "defender-1",
        "metrics",
    ]
    assert [s.name for s in ctx.registry.all()] == expected
    assert list(world) == expected
    assert all(world[n] is ctx.registry.get(n) for n in expected)
    assert world["oracle"].source is world["environment"]


def test_run_scenario_writes_all_files(tmp_path):
    cfg = cfg_with(max_steps=80)
    data = cfg.model_dump(mode="json")
    data["metrics"]["checkpoint_every"] = 40
    cfg = ScenarioConfig.model_validate(data)
    art = run_scenario(cfg, output_dir=tmp_path)

    assert isinstance(art, RunArtifacts)
    run_id = f"soros-baseline-42-{cfg.content_hash()[:8]}"
    assert art.run_dir == tmp_path / run_id
    names = sorted(
        p.relative_to(art.run_dir).as_posix() for p in art.run_dir.rglob("*") if p.is_file()
    )
    assert names == [
        "checkpoints/step-000040.json",
        "checkpoints/step-000080.json",
        "decisions.jsonl",
        "events.jsonl",
        "manifest.json",
        "summary.json",
        "timeseries.parquet",
    ]
    assert art.result.steps_run == 80

    # parquet round-trips the metrics frame exactly
    pd.testing.assert_frame_equal(pd.read_parquet(art.run_dir / "timeseries.parquet"), art.metrics)

    summary_text = (art.run_dir / "summary.json").read_text()
    assert json.loads(summary_text) == art.summary
    assert summary_text == json.dumps(art.summary, sort_keys=True, indent=2) + "\n"

    events = [json.loads(line) for line in (art.run_dir / "events.jsonl").read_text().splitlines()]
    assert len(events) == len(art.result.events)
    assert events[0]["kind"] == "run_started" and events[-1]["kind"] == "run_terminated"
    assert set(events[0]) == {"step", "kind", "source", "payload"}
    assert isinstance(events[0]["payload"], dict)

    decisions = (art.run_dir / "decisions.jsonl").read_text().splitlines()
    assert len(decisions) == 80 * 3

    m = json.loads((art.run_dir / "manifest.json").read_text())
    assert m == art.manifest
    assert set(m) == MANIFEST_KEYS
    assert m["run_id"] == run_id
    assert re.fullmatch(r"[a-z0-9-]+-\d+-[0-9a-f]{8}", m["run_id"])
    assert m["scenario_name"] == "soros-baseline"
    assert m["scenario_hash"] == cfg.content_hash()
    assert m["seed"] == 42
    assert m["phase_order_version"] == PHASE_ORDER_VERSION
    assert m["package_version"] == __version__
    assert m["python_version"] == platform.python_version()
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", m["created_utc"])
    assert m["files"] == names
    assert ScenarioConfig.model_validate(m["config"]) == cfg


def test_no_decisions_file_when_not_tracing(tmp_path):
    data = cfg_with(max_steps=10).model_dump(mode="json")
    data["metrics"]["trace_decisions"] = False
    art = run_scenario(ScenarioConfig.model_validate(data), output_dir=tmp_path)
    assert not (art.run_dir / "decisions.jsonl").exists()
    assert "decisions.jsonl" not in art.manifest["files"]


def test_rerun_replaces_run_dir(tmp_path):
    cfg = cfg_with(max_steps=10)
    art = run_scenario(cfg, output_dir=tmp_path)
    (art.run_dir / "stale.txt").write_text("old")
    art2 = run_scenario(cfg, output_dir=tmp_path)
    assert art2.run_dir == art.run_dir
    assert not (art.run_dir / "stale.txt").exists()


def test_seed_override_sets_run_id(tmp_path):
    cfg = cfg_with(max_steps=10)
    art = run_scenario(cfg, seed_override=7, output_dir=tmp_path)
    assert art.run_dir.name.startswith("soros-baseline-7-")
    assert art.summary["seed"] == 7 and art.manifest["seed"] == 7
