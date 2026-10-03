"""AC 8-11: the real scenario files, byte-level determinism, and what the seed reaches."""

import json

from depeg_sim.experiments.runner import run_scenario
from depeg_sim.kernel.config import load_scenario

BASELINE = "scenarios/soros-baseline.yaml"
VOLATILE = "scenarios/soros-volatile.yaml"
SAME_BYTES = ("timeseries.parquet", "summary.json", "events.jsonl", "decisions.jsonl")


def run(path, out, seed=None):
    return run_scenario(load_scenario(path), seed_override=seed, output_dir=out, chart=False)


def manifest_without_time(art):
    m = json.loads((art.run_dir / "manifest.json").read_text())
    del m["created_utc"]
    return m


def test_retuned_baseline_does_not_end_by_max_steps(tmp_path):
    cfg = load_scenario(BASELINE)
    assert cfg.steps.max_steps == 5000
    assert cfg.agents[0].start_step < cfg.termination.peg_recovered.for_steps
    art = run(BASELINE, tmp_path)
    assert art.summary["terminated_by"] != "max_steps"
    assert art.summary["terminated_by"] == "peg_recovered"
    assert art.summary["max_depeg_bps"] < -100  # the attack is visible
    assert art.summary["defender_interventions"] > 0


def test_baseline_twice_is_byte_identical(tmp_path):
    a = run(BASELINE, tmp_path / "a")
    b = run(BASELINE, tmp_path / "b")
    for name in SAME_BYTES:
        assert (a.run_dir / name).read_bytes() == (b.run_dir / name).read_bytes(), name
    for ca, cb in zip(
        sorted((a.run_dir / "checkpoints").iterdir()),
        sorted((b.run_dir / "checkpoints").iterdir()),
        strict=True,
    ):
        assert ca.read_bytes() == cb.read_bytes()
    assert manifest_without_time(a) == manifest_without_time(b)


def test_seed_does_not_reach_the_flat_baseline(tmp_path):
    # Baseline volatility is 0, so nothing draws from ctx.rng: the seed can only
    # change labels (manifest, run_id, the run_started event), never the model.
    a = run(BASELINE, tmp_path, seed=42)
    b = run(BASELINE, tmp_path, seed=7)
    assert a.manifest["seed"] == 42 and b.manifest["seed"] == 7
    assert a.manifest["run_id"] != b.manifest["run_id"]
    assert a.run_dir != b.run_dir
    pa = (a.run_dir / "timeseries.parquet").read_bytes()
    pb = (b.run_dir / "timeseries.parquet").read_bytes()
    assert pa == pb


def test_seed_changes_the_volatile_scenario(tmp_path):
    cfg = load_scenario(VOLATILE)
    assert cfg.environment.volatility_per_step == 0.0005
    a = run(VOLATILE, tmp_path, seed=42)
    b = run(VOLATILE, tmp_path, seed=7)
    pa = (a.run_dir / "timeseries.parquet").read_bytes()
    pb = (b.run_dir / "timeseries.parquet").read_bytes()
    assert pa != pb
    assert not a.metrics["reference_price"].equals(b.metrics["reference_price"])


def test_volatile_is_baseline_plus_volatility_only():
    base = load_scenario(BASELINE).model_dump(mode="json")
    vol = load_scenario(VOLATILE).model_dump(mode="json")
    for d in (base, vol):
        d.pop("name")
        d["environment"].pop("volatility_per_step")
    assert base == vol
