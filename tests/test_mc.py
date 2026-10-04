import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pydantic
import pytest
import yaml

from depeg_sim.analysis.stats import wilson
from depeg_sim.experiments import mc as mc_mod
from depeg_sim.experiments.mc import METRICS, NULLABLE, aggregate_mc, axis_columns
from depeg_sim.experiments.sweep import SeedRange, SweepSpec, expand, load_sweep, run_sweep
from depeg_sim.experiments.sweep import main as sweep_main

ATK = "agents[type=attacker].capital"
REAL_SPECS = ("sweeps/capital-vs-resources-mc.yaml", "sweeps/pool-depth-x-attacker-mc.yaml")


def expected_columns(axes):
    cols = [*axes, "n"]
    for m in METRICS:
        cols += [f"{m}_{s}" for s in ("mean", "std", "p05", "p50", "p95")]
        if m in NULLABLE:
            cols.append(f"{m}_n")
    return cols + [
        "p_reserves_exhausted",
        "p_reserves_exhausted_lo",
        "p_reserves_exhausted_hi",
        "p_reserves_exhausted_term",
        "p_peg_recovered",
        "p_max_steps",
    ]


# AC 1: seeds forms ----------------------------------------------------------------------


def base_spec(**kw) -> SweepSpec:
    data = {"version": 1, "name": "t", "base": "scenarios/soros-baseline.yaml", "seeds": [42]}
    return SweepSpec.model_validate(data | kw)


def test_seed_range_form():
    s = base_spec(seeds={"count": 3, "start": 10})
    assert s.seeds == SeedRange(count=3, start=10)
    assert s.seed_list() == [10, 11, 12]
    assert [c.seed for c in expand(s)] == [10, 11, 12]
    assert base_spec(seeds={"count": 2}).seed_list() == [0, 1]
    assert base_spec(seeds=[7, 3]).seed_list() == [7, 3]


@pytest.mark.parametrize(
    "seeds",
    [[], {"count": 0, "start": 1}, {"count": 2, "start": -1}, {"count": 2, "stop": 5}],
)
def test_bad_seeds_rejected(seeds):
    with pytest.raises(pydantic.ValidationError):
        base_spec(seeds=seeds)


def test_real_mc_specs():
    s = load_sweep(REAL_SPECS[0])
    assert str(s.base) == "scenarios/soros-volatile.yaml"
    assert [a.name for a in s.axis_list()] == [
        "pool_depth",
        ATK,
        "agents[type=defender].budget",
        "redemption.reserves",
    ]
    assert s.seed_list() == list(range(1000, 1016))
    assert s.max_steps == 1500
    grid = 1
    for a in s.axis_list():
        grid *= len(a.values)
    assert (grid, grid * len(s.seed_list())) == (126, 2016)

    p = load_sweep(REAL_SPECS[1])
    assert str(p.base) == "scenarios/soros-volatile.yaml"
    assert [len(a.values) for a in p.axis_list()] == [4, 4]
    assert len(p.seed_list()) == 32  # 16 x 32 = 512 runs


# AC 2, 3, 4: aggregation on a synthetic sweep.parquet --------------------------------------


def synthetic(tmp_path, rows, axes=("pool_depth", ATK), seeds=(1, 2, 3, 4)):
    sweep_dir = tmp_path / "syn"
    sweep_dir.mkdir()
    manifest = {
        "sweep_name": "syn",
        "axes": [{"name": a, "paths": [a], "values": []} for a in axes],
        "seeds": list(seeds),
    }
    (sweep_dir / "manifest.json").write_text(json.dumps(manifest))
    pd.DataFrame(rows).to_parquet(sweep_dir / "sweep.parquet", index=False)
    return sweep_dir


def run_row(index, seed, depth, cap, *, depeg, sustained, exhausted, term):
    row = {"index": index, "seed": seed, "pool_depth": depth, ATK: cap}
    row |= dict.fromkeys(METRICS, 1.0)
    row |= {
        "max_depeg_bps": depeg,
        "steps_to_sustained_recovery": sustained,
        "steps_to_first_band_entry": 3.0,
        "reserves_exhausted": exhausted,
        "terminated_by": term,
        "scenario": "syn/x",
    }
    return row


def rows_two_points():
    # Grid point A (depth 2M, cap 100k) and B (depth 500k, cap 100k); 4 seeds each.
    # Rows are deliberately interleaved and listed out of grid order.
    a = [
        (-10.0, 5.0, False, "peg_recovered"),
        (-20.0, None, False, "max_steps"),
        (-30.0, 7.0, False, "peg_recovered"),
        (-40.0, None, True, "reserves_exhausted"),
    ]
    b = [(-100.0, None, True, "reserves_exhausted")] * 4
    rows = []
    for i, ((da, sa, ea, ta), (db, sb, eb, tb)) in enumerate(zip(a, b, strict=True)):
        rows.append(
            run_row(2 * i, i, 2_000_000, 100_000, depeg=da, sustained=sa, exhausted=ea, term=ta)
        )
        rows.append(
            run_row(2 * i + 1, i, 500_000, 100_000, depeg=db, sustained=sb, exhausted=eb, term=tb)
        )
    return rows


def test_aggregate_known_values(tmp_path):
    out = aggregate_mc(synthetic(tmp_path, rows_two_points()))
    assert out == tmp_path / "syn" / "mc.parquet"
    mc = pd.read_parquet(out)
    assert list(mc.columns) == expected_columns(["pool_depth", ATK])
    assert len(mc) == 2
    # sorted by axis columns in spec order: pool_depth ascending first
    assert mc["pool_depth"].tolist() == [500_000, 2_000_000]
    b, a = mc.iloc[0], mc.iloc[1]
    assert a["n"] == 4 and b["n"] == 4

    depegs = np.array([-10.0, -20.0, -30.0, -40.0])
    assert a["max_depeg_bps_mean"] == -25.0
    assert a["max_depeg_bps_std"] == pytest.approx(depegs.std(ddof=1))
    assert a["max_depeg_bps_p50"] == -25.0
    assert a["max_depeg_bps_p05"] == pytest.approx(np.percentile(depegs, 5))
    assert a["max_depeg_bps_p95"] == pytest.approx(np.percentile(depegs, 95))

    # nullable metric: stats over the 2 non-null values, _n counts them
    assert a["steps_to_sustained_recovery_n"] == 2
    assert a["steps_to_sustained_recovery_mean"] == 6.0
    assert a["steps_to_sustained_recovery_p50"] == 6.0
    assert b["steps_to_sustained_recovery_n"] == 0
    assert np.isnan(b["steps_to_sustained_recovery_mean"])
    assert np.isnan(b["steps_to_sustained_recovery_std"])
    assert a["steps_to_first_band_entry_n"] == 4

    # zero spread -> std 0 with n>=2
    assert b["max_depeg_bps_std"] == 0.0

    assert a["p_reserves_exhausted"] == 0.25
    assert (a["p_reserves_exhausted_lo"], a["p_reserves_exhausted_hi"]) == pytest.approx(
        wilson(1, 4)
    )
    assert b["p_reserves_exhausted"] == 1.0
    assert (b["p_reserves_exhausted_lo"], b["p_reserves_exhausted_hi"]) == pytest.approx(
        wilson(4, 4)
    )
    assert (a["p_reserves_exhausted_term"], a["p_peg_recovered"], a["p_max_steps"]) == (
        0.25,
        0.5,
        0.25,
    )
    for _, r in mc.iterrows():
        assert r["p_reserves_exhausted_term"] + r["p_peg_recovered"] + r["p_max_steps"] == 1.0


def test_std_nan_with_single_value(tmp_path):
    rows = [run_row(0, 1, 1, 1, depeg=-5.0, sustained=None, exhausted=False, term="max_steps")]
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows, seeds=(1,))))
    assert mc.loc[0, "max_depeg_bps_mean"] == -5.0
    assert np.isnan(mc.loc[0, "max_depeg_bps_std"])
    assert mc.loc[0, "max_depeg_bps_p05"] == mc.loc[0, "max_depeg_bps_p95"] == -5.0


def test_axes_come_from_manifest_not_columns(tmp_path):
    rows = rows_two_points()
    for r in rows:
        r["agents[type=defender].budget"] = 400_000  # looks like an axis, isn't one
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows)))
    assert "agents[type=defender].budget" not in mc.columns
    assert "seed" not in mc.columns and "index" not in mc.columns
    assert len(mc) == 2


def test_axis_order_follows_spec(tmp_path):
    rows = rows_two_points()
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows, axes=(ATK, "pool_depth"))))
    assert list(mc.columns[:2]) == [ATK, "pool_depth"]
    assert mc["pool_depth"].tolist() == [500_000, 2_000_000]


def test_missing_axis_column_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="axis columns"):
        aggregate_mc(synthetic(tmp_path, rows_two_points(), axes=("pool_depth", "nope")))


def test_no_axes_is_one_grid_point(tmp_path):
    rows = rows_two_points()
    for r in rows:
        del r["pool_depth"], r[ATK]
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows, axes=())))
    assert len(mc) == 1 and mc.loc[0, "n"] == 8
    assert list(mc.columns) == expected_columns([])


def test_aggregate_is_byte_deterministic(tmp_path):
    sweep_dir = synthetic(tmp_path, rows_two_points())
    first = aggregate_mc(sweep_dir).read_bytes()
    assert aggregate_mc(sweep_dir).read_bytes() == first


def test_axis_columns_helper():
    m = {"axes": [{"name": "pool_depth"}, {"name": ATK}]}
    assert axis_columns(m) == ["pool_depth", ATK]


# AC 5, 10: tiny end-to-end through both CLIs -------------------------------------------------


def tiny_spec(tmp_path) -> "tuple[SweepSpec, object]":
    """2 x 2 grid (one linked axis, one plain), 3 seeds, max_steps 200 on soros-volatile."""
    data = {
        "version": 1,
        "name": "tiny-mc",
        "base": "scenarios/soros-volatile.yaml",
        "linked_axes": [
            {
                "name": "pool_depth",
                "paths": ["amm.reserve_stable", "amm.reserve_reference"],
                "values": [500_000, 1_000_000],
            }
        ],
        "axes": {ATK: [300_000, 1_200_000]},
        "seeds": {"count": 3, "start": 7},
        "max_steps": 200,
    }
    path = tmp_path / "tiny.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return SweepSpec.model_validate(data), path


def test_tiny_spec_is_within_ci_budget(tmp_path):
    spec, _ = tiny_spec(tmp_path)
    grid = 1
    for a in spec.axis_list():
        grid *= len(a.values)
    assert grid <= 8 and len(spec.seed_list()) <= 3 and spec.max_steps <= 300


def test_sweep_cli_with_mc(tmp_path, capsys):
    _, path = tiny_spec(tmp_path)
    out = tmp_path / "out"
    assert sweep_main([str(path), "--output", str(out), "--workers", "1", "--mc"]) == 0
    sweep_dir = out / "tiny-mc"
    assert capsys.readouterr().out.splitlines() == [
        "sweep: tiny-mc cells=12 workers=1",
        f"wrote: {sweep_dir / 'sweep.parquet'}",
        "mc: tiny-mc grid_points=4 seeds=3 runs=12",
        f"wrote: {sweep_dir / 'mc.parquet'}",
    ]
    manifest = json.loads((sweep_dir / "manifest.json").read_text())
    assert manifest["seeds"] == [7, 8, 9]
    mc = pd.read_parquet(sweep_dir / "mc.parquet")
    assert list(mc.columns) == expected_columns(["pool_depth", ATK])
    assert mc["n"].tolist() == [3, 3, 3, 3]
    assert mc[["pool_depth", ATK]].values.tolist() == [
        [500_000, 300_000],
        [500_000, 1_200_000],
        [1_000_000, 300_000],
        [1_000_000, 1_200_000],
    ]
    sweep = pd.read_parquet(sweep_dir / "sweep.parquet")
    # the per-point mean matches a direct groupby over the raw runs
    direct = sweep.groupby(["pool_depth", ATK])["max_depeg_bps"].mean().tolist()
    assert mc["max_depeg_bps_mean"].tolist() == pytest.approx(direct)
    # volatility on: seeds give different runs at the same grid point (the trough is the
    # first dump and noise-free, so look at where the run ends)
    assert sweep.groupby(["pool_depth", ATK])["final_depeg_bps"].nunique().min() == 3


def test_mc_module_cli_and_rerun_bytes(tmp_path):
    spec, _ = tiny_spec(tmp_path)
    sweep_dir = run_sweep(spec, tmp_path / "out", workers=1)
    proc = subprocess.run(
        [sys.executable, "-m", "depeg_sim.mc", str(sweep_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "mc: tiny-mc grid_points=4 seeds=3 runs=12",
        f"wrote: {sweep_dir / 'mc.parquet'}",
    ]
    first = (sweep_dir / "mc.parquet").read_bytes()
    assert mc_mod.main([str(sweep_dir)]) == 0
    assert (sweep_dir / "mc.parquet").read_bytes() == first


def test_mc_cli_exit_codes(tmp_path, capsys):
    assert mc_mod.main([str(tmp_path / "nope")]) == 2
    d = tmp_path / "bad"
    d.mkdir()
    (d / "sweep.parquet").write_bytes(b"")
    assert mc_mod.main([str(d)]) == 2  # no manifest
    (d / "manifest.json").write_text("{not json")
    assert mc_mod.main([str(d)]) == 3
    (d / "manifest.json").write_text(json.dumps({"sweep_name": "x"}))  # no axes
    assert mc_mod.main([str(d)]) == 3
    assert "error" in capsys.readouterr().err


# Story 2.7 AC 1: the absorbed-stable columns -------------------------------------------


def test_mc_carries_absorbed_stable_columns(tmp_path):
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows_two_points())))
    for m in ("defender_bought_stable", "holder_bought_stable", "holder_pnl"):
        assert mc[f"{m}_mean"].tolist() == [1.0, 1.0]


def test_pre_2_7_sweep_parquet_aggregates_to_nan(tmp_path):
    rows = rows_two_points()
    for r in rows:
        for m in ("defender_bought_stable", "holder_bought_stable", "holder_pnl"):
            del r[m]
    mc = pd.read_parquet(aggregate_mc(synthetic(tmp_path, rows)))
    assert list(mc.columns) == expected_columns(["pool_depth", ATK])
    assert mc["holder_bought_stable_mean"].isna().all()
    assert mc["max_depeg_bps_mean"].notna().all()
