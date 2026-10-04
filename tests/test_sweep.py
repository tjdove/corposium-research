import hashlib
import json
import platform
import subprocess
import sys

import pandas as pd
import pydantic
import pytest
import yaml

from depeg_sim import __version__
from depeg_sim.analysis.summary import SUMMARY_KEYS
from depeg_sim.experiments.sweep import (
    SweepSpec,
    SweepSpecError,
    expand,
    load_sweep,
    main,
    run_sweep,
)
from depeg_sim.kernel.config import ScenarioConfig, load_scenario

BASE = "scenarios/soros-baseline.yaml"
REAL = "sweeps/pool-depth-x-attacker.yaml"
ATK = "agents[type=attacker].capital"


def spec(**kw) -> SweepSpec:
    data = {"version": 1, "name": "t", "base": BASE, "seeds": [42]} | kw
    return SweepSpec.model_validate(data)


def small(**kw) -> SweepSpec:
    """2x2x1 subset of the real sweep, short runs."""
    real = load_sweep(REAL).model_dump(mode="json")
    real["linked_axes"][0]["values"] = [500_000, 1_000_000]
    real["axes"] = {ATK: [100_000, 300_000]}
    real["max_steps"] = 150
    real["name"] = "small"
    return SweepSpec.model_validate(real | kw)


# AC 3: spec ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw", [{"extra_field": 1}, {"version": 2}, {"seeds": []}, {"name": "a/b"}, {"max_steps": 0}]
)
def test_spec_is_strict(kw):
    with pytest.raises(pydantic.ValidationError):
        spec(**kw)  # name is used as a directory name, so no "/"


def test_load_real_sweep():
    s = load_sweep(REAL)
    assert s.name == "pool-depth-x-attacker"
    assert str(s.base) == BASE
    assert [a.name for a in s.linked_axes] == ["pool_depth"]
    assert s.linked_axes[0].paths == ["amm.reserve_stable", "amm.reserve_reference"]
    assert s.linked_axes[0].values == [250_000, 500_000, 1_000_000, 2_000_000]
    assert s.axes == {ATK: [100_000, 300_000, 600_000, 1_200_000]}
    assert (s.seeds, s.max_steps, s.overrides) == ([42], 2000, {})


# AC 5, 10: expansion ----------------------------------------------------------------


def test_real_sweep_expands_to_16_cells():
    cells = expand(load_sweep(REAL))
    assert len(cells) == 16
    assert [c.index for c in cells] == list(range(16))
    # linked axis varies slowest, attacker capital fastest
    assert cells[0].axis_values == {"pool_depth": 250_000, ATK: 100_000}
    assert cells[1].axis_values == {"pool_depth": 250_000, ATK: 300_000}
    assert cells[4].axis_values == {"pool_depth": 500_000, ATK: 100_000}
    c = cells[15].config
    assert (c.amm.reserve_stable, c.amm.reserve_reference) == (2_000_000.0, 2_000_000.0)
    assert c.agents[0].capital == 1_200_000.0
    assert c.steps.max_steps == 2000
    assert c.name == "pool-depth-x-attacker/0015"
    assert len({cell.config.content_hash() for cell in cells}) == 16


def test_order_linked_then_axes_then_seeds_and_names():
    s = spec(
        linked_axes=[{"name": "depth", "paths": ["amm.reserve_stable"], "values": [1, 2]}],
        axes={"agents[0].pace": [0.1, 0.2]},
        seeds=[5, 6],
    )
    cells = expand(s)
    got = [(c.axis_values["depth"], c.axis_values["agents[0].pace"], c.seed) for c in cells]
    assert got == [
        (1, 0.1, 5),
        (1, 0.1, 6),
        (1, 0.2, 5),
        (1, 0.2, 6),
        (2, 0.1, 5),
        (2, 0.1, 6),
        (2, 0.2, 5),
        (2, 0.2, 6),
    ]
    assert [c.config.name for c in cells] == [f"t/{i:04d}" for i in range(8)]
    assert all(c.config.seed == c.seed for c in cells)


def test_overrides_before_axes_and_max_steps_last():
    s = spec(
        overrides={"agents[0].pace": 0.5, "steps.max_steps": 77, "amm.reserve_stable": 5.0},
        axes={"amm.reserve_stable": [10.0, 20.0]},
        max_steps=123,
    )
    cells = expand(s)
    assert [c.config.amm.reserve_stable for c in cells] == [10.0, 20.0]  # axis wins
    assert all(c.config.agents[0].pace == 0.5 for c in cells)
    assert all(c.config.steps.max_steps == 123 for c in cells)  # max_steps applied last


def test_no_axes_is_one_cell_per_seed():
    cells = expand(spec(seeds=[1, 2, 3]))
    assert [(c.index, c.seed, c.axis_values) for c in cells] == [(0, 1, {}), (1, 2, {}), (2, 3, {})]


def test_duplicate_axis_names_rejected():
    s = spec(
        linked_axes=[
            {"name": "amm.reserve_stable", "paths": ["amm.reserve_stable"], "values": [1]}
        ],
        axes={"amm.reserve_stable": [5]},
    )
    with pytest.raises(SweepSpecError, match="duplicate"):
        expand(s)


# AC 6: ADR-0013 guard -----------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {"axes": {"amm.fee_bps": [5, 30]}},
        {"overrides": {"amm.fee_bps": 5}},
        {"axes": {"agents[type=arbitrageur].min_profit_bps": [0, 50]}},
        {"axes": {"agents[1].min_profit_bps": [0, 50]}},
        {"linked_axes": [{"name": "x", "paths": ["amm.fee_bps"], "values": [5]}]},
    ],
)
def test_guard_raises_without_tolerance(kw):
    with pytest.raises(SweepSpecError, match="ADR-0013"):
        expand(spec(**kw))


@pytest.mark.parametrize(
    "extra",
    [
        {"axes": {"amm.fee_bps": [5, 30], "termination.peg_recovered.tolerance": [0.004, 0.006]}},
        {
            "axes": {"amm.fee_bps": [5, 30]},
            "overrides": {"termination.peg_recovered.tolerance": 0.01},
        },
    ],
)
def test_guard_passes_with_tolerance(extra):
    cells = expand(spec(**extra))
    assert {c.config.amm.fee_bps for c in cells} == {5, 30}


def test_guard_ignores_unrelated_axes():
    assert len(expand(spec(axes={"amm.reserve_stable": [1.0, 2.0]}))) == 2


# AC 7, 8, 10: running and aggregation -------------------------------------------------


def test_run_sweep_small_subset(tmp_path):
    s = small()
    sweep_dir = run_sweep(s, tmp_path, workers=1)
    assert sweep_dir == tmp_path / "small"
    cells = expand(s)
    cell_dirs = sorted(p.name for p in sweep_dir.iterdir() if p.is_dir())
    assert cell_dirs == [f"{c.index:04d}-42-{c.config.content_hash()[:8]}" for c in cells]
    for d in cell_dirs:
        assert (sweep_dir / d / "summary.json").is_file()
        assert not (sweep_dir / d / "peg_trajectory.png").exists()

    df = pd.read_parquet(sweep_dir / "sweep.parquet")
    assert len(df) == 4
    assert list(df.columns[:4]) == ["index", "seed", "pool_depth", ATK]
    assert list(df.columns[4:]) == [k for k in SUMMARY_KEYS if k != "seed"]
    assert df["index"].tolist() == [0, 1, 2, 3]
    assert df["pool_depth"].tolist() == [500_000, 500_000, 1_000_000, 1_000_000]
    assert df[ATK].tolist() == [100_000, 300_000, 100_000, 300_000]
    assert df["scenario"].tolist() == [f"small/{i:04d}" for i in range(4)]
    for i, d in enumerate(cell_dirs):
        summary = json.loads((sweep_dir / d / "summary.json").read_text())
        assert df.loc[i, "max_depeg_bps"] == summary["max_depeg_bps"]

    m = json.loads((sweep_dir / "manifest.json").read_text())
    assert m["sweep_name"] == "small"
    assert m["base_scenario_hash"] == load_scenario(BASE).content_hash()
    # Story 2.7: the resolved base config, so charts need only parquet + manifest
    base_cfg = ScenarioConfig.model_validate(m["base_config"])
    assert base_cfg.content_hash() == m["base_scenario_hash"]
    assert m["axes"] == [
        {
            "name": "pool_depth",
            "paths": ["amm.reserve_stable", "amm.reserve_reference"],
            "values": [500_000, 1_000_000],
        },
        {"name": ATK, "paths": [ATK], "values": [100_000, 300_000]},
    ]
    assert (m["seeds"], m["overrides"], m["max_steps"], m["cell_count"]) == ([42], {}, 150, 4)
    assert m["package_version"] == __version__
    assert m["python_version"] == platform.python_version()
    assert "created_utc" in m


def test_workers_1_and_2_give_identical_parquet(tmp_path):
    a = run_sweep(small(), tmp_path / "a", workers=1)
    b = run_sweep(small(), tmp_path / "b", workers=2)
    assert (a / "sweep.parquet").read_bytes() == (b / "sweep.parquet").read_bytes()
    for name in ("summary.json", "timeseries.parquet"):
        for da, db in zip(sorted(a.glob(f"*/{name}")), sorted(b.glob(f"*/{name}")), strict=True):
            assert da.read_bytes() == db.read_bytes()


def test_rerun_replaces_sweep_dir(tmp_path):
    sweep_dir = run_sweep(small(), tmp_path)
    (sweep_dir / "stale").mkdir()
    run_sweep(small(), tmp_path)
    assert not (sweep_dir / "stale").exists()


def test_workers_must_be_positive(tmp_path):
    with pytest.raises(ValueError):
        run_sweep(small(), tmp_path, workers=0)


# AC 9: CLI -----------------------------------------------------------------------------


def write_spec(tmp_path, s: SweepSpec):
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(s.model_dump(mode="json")), encoding="utf-8")
    return path


def test_cli_two_lines(tmp_path, capsys):
    path = write_spec(tmp_path, small())
    out = tmp_path / "out"
    assert main([str(path), "--output", str(out)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["sweep: small cells=4 workers=1", f"wrote: {out / 'small' / 'sweep.parquet'}"]
    assert (out / "small" / "sweep.parquet").is_file()


def test_cli_missing_spec(tmp_path, capsys):
    assert main([str(tmp_path / "nope.yaml")]) == 2
    assert "not found" in capsys.readouterr().err


def test_cli_missing_base(tmp_path):
    path = write_spec(tmp_path, small(base="scenarios/nope.yaml"))
    assert main([str(path), "--output", str(tmp_path / "out")]) == 2


HEAD = "version: 1\nname: x\nbase: scenarios/soros-baseline.yaml\nseeds: [1]\n"


@pytest.mark.parametrize(
    "text",
    [
        HEAD.replace("version: 1", "version: 2"),
        HEAD + "axes: {amm.nope: [1]}\n",  # SweepPathError
        HEAD + "axes: {amm.fee_bps: [1]}\n",  # ADR-0013 guard
        HEAD + "axes: {amm.fee_bps: [-1]}\n",  # value fails validation (guard first)
        HEAD + "axes: {amm.reserve_stable: [-1]}\n",  # value fails validation
        "version: 1\nname: [unclosed\n",  # YAML error
    ],
)
def test_cli_invalid_spec_exits_3(tmp_path, capsys, text):
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    assert main([str(path), "--output", str(out)]) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and "invalid sweep" in captured.err
    assert not out.exists()


def test_module_entry_point_with_spawn_workers(tmp_path):
    # The real `python -m depeg_sim.sweep` path: spawn workers re-import the main module.
    path = write_spec(tmp_path, small())
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "depeg_sim.sweep",
            str(path),
            "--workers",
            "2",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "sweep: small cells=4 workers=2"
    assert len(pd.read_parquet(out / "small" / "sweep.parquet")) == 4


# Story 2.7 AC 2: linked-axis scales ----------------------------------------------------

HOLDER_SPEC = {
    "version": 1,
    "name": "scaled",
    "base": "scenarios/calibrated-baseline.yaml",
    "seeds": [1],
    "linked_axes": [
        {
            "name": "pool_depth",
            "paths": [
                "amm.reserve_stable",
                "amm.reserve_reference",
                "agents[type=holder].capital",
            ],
            "values": [1_000_000, 4_000_000],
            "scales": [1, 1, 0.55],
        }
    ],
}


def test_scales_multiply_each_path():
    cells = expand(SweepSpec.model_validate(HOLDER_SPEC))
    for cell, v in zip(cells, [1_000_000, 4_000_000], strict=True):
        cfg = cell.config
        assert cfg.amm.reserve_stable == cfg.amm.reserve_reference == v
        holder = next(a for a in cfg.agents if a.type == "holder")
        assert holder.capital == pytest.approx(0.55 * v, rel=1e-15)
        assert cell.axis_values == {"pool_depth": v}


@pytest.mark.parametrize("scales", [[1, 0.55], [1, 1, 1, 1], [1, 0, 0.55], [1, 1, -1]])
def test_scales_length_and_sign_are_checked(scales):
    bad = json.loads(json.dumps(HOLDER_SPEC))
    bad["linked_axes"][0]["scales"] = scales
    with pytest.raises(SweepSpecError, match="scales"):
        expand(SweepSpec.model_validate(bad))


def test_default_scales_leave_existing_sweep_identical():
    # Pinned before LinkedAxis.scales existed (commit bca5025): same index, same per-cell
    # content_hash for every cell of the 16-cell real sweep.
    cells = expand(load_sweep(REAL))
    assert [c.index for c in cells] == list(range(16))
    assert (cells[0].index, cells[0].config.content_hash()) == (
        0,
        "e79a8ca8f7cdba6877ebec2be9bd1b24bb23b47c417a0ed56b13fc8306d14b5b",
    )
    assert (cells[-1].index, cells[-1].config.content_hash()) == (
        15,
        "007df1b7d4247b2b9a95943916c9919a33942d5999d235683edaa7263522acae",
    )
    joined = "".join(c.config.content_hash() for c in cells).encode()
    assert (
        hashlib.sha256(joined).hexdigest()
        == "0713dd709978a528053013db6cd4145edcea7ac21f477c97ceb88436e33ab30c"
    )
    explicit = load_sweep(REAL).model_dump(mode="json")
    explicit["linked_axes"][0]["scales"] = [1.0, 1.0]
    again = expand(SweepSpec.model_validate(explicit))
    assert [c.config.content_hash() for c in again] == [c.config.content_hash() for c in cells]


def test_threshold_surface_spec_expands():
    # Story 2.7 AC 3: 5 depths x 8 capitals x 16 seeds; holder at 0.55 x depth
    cells = expand(load_sweep("sweeps/threshold-surface-mc.yaml"))
    assert len(cells) == 640
    total = 41_346_974 + 138_107_417
    for c in cells[:: 16 * 8]:  # first capital of each depth
        holder = next(a for a in c.config.agents if a.type == "holder")
        assert holder.capital == pytest.approx(0.55 * c.axis_values["pool_depth"])
        assert c.config.amm.reserve_stable == c.config.amm.reserve_reference
    caps = sorted({c.axis_values[ATK] for c in cells})
    ratios = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5]
    assert caps == [round(r * total) for r in ratios]
    assert {c.config.steps.max_steps for c in cells} == {18_000}
