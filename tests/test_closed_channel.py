"""Story 5.5: the par ladder-B replay with the weekend redemption channel closed / at 10%."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from depeg_sim.analysis.charts import plot_validation_overlay
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import load_scenario

sys.path.insert(0, str(Path("scripts").resolve()))

import closed_channel_table as cc  # noqa: E402

S = Path("scenarios")
BASE = "usdc-2023-tranches-par"
# content_hash() of each new scenario, usdc-2023-tranches-par-<variant> (AC 1)
HASHES = {
    "closed": "c2e0f5a7cf5793af48d24e008489986ff70f892a3986f903988bb374253e72f3",
    "slow": "90c61264e8c2fb9d06d94fc8d7475438f4e053211df62e3d7ae2a8ce8225b8bb",
}
CAPACITY = {"closed": 0.0, "slow": 60.579}
REOPEN = 25_500  # 85 h, Monday 13 March 13:00 UTC


@pytest.mark.parametrize("variant", sorted(HASHES))
def test_scenario_hash_is_pinned(variant):
    assert load_scenario(S / f"{BASE}-{variant}.yaml").content_hash() == HASHES[variant]


@pytest.mark.parametrize("variant", sorted(HASHES))
def test_only_name_and_weekend_capacity_differ_from_the_base(variant):
    new = load_scenario(S / f"{BASE}-{variant}.yaml").model_dump(mode="json")
    base = load_scenario(S / f"{BASE}.yaml").model_dump(mode="json")
    assert new["name"] == f"{BASE}-{variant}"
    assert new["redemption"]["capacity_per_step"] == CAPACITY[variant]
    assert base["redemption"]["capacity_per_step"] == 605.79
    assert (
        new["redemption"]["capacity_schedule"]
        == base["redemption"]["capacity_schedule"]
        == [{"step": REOPEN, "capacity_per_step": 19181.59}]
    )
    for d in (new, base):
        del d["name"], d["redemption"]["capacity_per_step"]
    assert new == base


def _short(name, tmp_path, max_steps):
    cfg = set_path(load_scenario(S / f"{name}.yaml"), "steps.max_steps", max_steps)
    cfg = set_path(cfg, "metrics.checkpoint_every", None)
    return run_scenario(cfg, output_dir=tmp_path, chart=False)


def _events(run_dir, kind):
    with open(run_dir / "events.jsonl", encoding="utf-8") as f:
        return [e for e in map(json.loads, f) if e["kind"] == kind]


def test_closed_channel_pays_nothing_until_the_reopening(tmp_path):
    run = _short("usdc-2023-tranches-par-closed", tmp_path, REOPEN + 300)
    fills = _events(run.run_dir, "redeem_fulfilled")
    assert fills and min(e["step"] for e in fills) == REOPEN
    # the holder never queues while the channel is closed (its tranche sizes to 0)
    requests = _events(run.run_dir, "redeem_requested")
    assert {e["payload"]["source"] for e in requests if e["step"] < REOPEN} == {"arb-1"}
    assert [e["payload"] for e in _events(run.run_dir, "capacity_changed")] == [
        {"step": REOPEN, "old": 0.0, "new": 19181.59}
    ]
    ts = pd.read_parquet(run.run_dir / "timeseries.parquet")
    before = ts[ts["step"] < REOPEN]
    assert (before["redemption_reserves"] == 138_107_417).all()
    assert run.summary["terminated_by"] == "max_steps"


def test_overlay_with_the_csv_from_a_third_run(tmp_path):
    observed = _short("usdc-2023-tranches", tmp_path, 8400)
    par = _short(BASE, tmp_path, 8400)
    closed = _short("usdc-2023-tranches-par-closed", tmp_path, 8400)
    png = plot_validation_overlay(par.run_dir, closed.run_dir, observed_from=observed.run_dir)
    assert png == closed.run_dir / "validation_overlay.png"
    assert not (par.run_dir / "validation_overlay.png").exists()
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 1500)
    assert plt.get_fignums() == []
    with pytest.raises(ValueError, match="no environment.price_series_path"):
        plot_validation_overlay(par.run_dir, closed.run_dir)  # neither run was fed the CSV


def test_table_smoke_and_deterministic(tmp_path):
    rows = cc.build(tmp_path / "a", max_steps=REOPEN + 300)
    assert [r["label"] for r in rows] == [label for label, _ in cc.CHANNELS]
    assert [r["capacity"] for r in rows] == [605.79, 60.579, 0.0]
    closed = rows[2]
    assert closed["reopen_h"] == 85.0 and closed["paid_attack"] == closed["paid_window"] == 0.0
    assert closed["holder_reopen"]["h"] == 85.0 and closed["holder_reopen"]["queued"] == 0.0
    assert closed["holder_end"]["h"] == pytest.approx((REOPEN + 300) * 12 / 3600)
    assert set(closed["queue_by_source"]) == {"arb-1"}
    text = cc.format_tables(rows)
    assert text.splitlines()[3].startswith("observed (hourly)")
    assert cc.format_tables(cc.build(tmp_path / "b", max_steps=REOPEN + 300)) == text
    with pytest.raises(ValueError, match="past the reopening step"):
        cc.build(tmp_path / "c", max_steps=REOPEN)
