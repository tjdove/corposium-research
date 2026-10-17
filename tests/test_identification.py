"""Story 5.2: depth x capital on the par-reference replay, and the ladders side by side."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from depeg_sim.analysis.charts import (
    IDENTIFICATION_SURFACE,
    OBSERVED_TROUGH_BPS,
    plot_identification_surface,
)
from depeg_sim.experiments.sweep import expand, load_sweep, sweep_spec_hash
from depeg_sim.kernel.config import load_scenario

sys.path.insert(0, str(Path("scripts").resolve()))

import identification_table as it  # noqa: E402
import replay_table  # noqa: E402

SPEC = Path("sweeps/usdc-par-depth-x-capital.yaml")
SPEC_HASH = "bdf2a026ce52b28fb075831f347498cd8718d041002e701d13c280d04b903192"
D_STAR, C_STAR_B = 16_666_667, 10_833_333
OPEN_SCAN = [9_166_667, 10_000_000, 10_833_333, 11_666_667, 12_500_000]
CLOSED_SCAN = [10_000_000, 11_666_667, 13_333_333, 15_000_000, 16_666_667]


def test_spec_hash_is_pinned():
    assert sweep_spec_hash(SPEC) == SPEC_HASH


def test_spec_is_the_40_cell_par_grid():
    spec = load_sweep(SPEC)
    assert spec.base == Path("scenarios/usdc-2023-tranches-par.yaml")
    assert spec.seed_list() == [42] and spec.max_steps is None and spec.overrides == {}
    cells = expand(spec)
    assert len(cells) == 40
    depths = sorted({c.axis_values["pool_depth"] for c in cells})
    caps = sorted({c.axis_values["holder_capital"] for c in cells})
    assert depths == [0.5, 0.75, 1, 1.5, 2]
    assert caps == [0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 2]
    base = load_scenario(spec.base)
    for c in cells:
        d, k = c.axis_values["pool_depth"], c.axis_values["holder_capital"]
        assert c.config.amm.reserve_stable == c.config.amm.reserve_reference == d * D_STAR
        holder = next(a for a in c.config.agents if a.type == "holder")
        assert holder.capital == k * C_STAR_B
        assert holder.tranches == next(a for a in base.agents if a.type == "holder").tranches
        assert c.config.environment == base.environment  # par: nothing observed fed in
        assert c.config.agents[0] == base.agents[0]  # attacker (pace) unchanged


def test_target_constant_is_the_observed_trough():
    base = load_scenario(replay_table.OBSERVED_FROM)
    obs = replay_table.observed_row(base.environment.price_series_path, 1.0, 0.0031, 27.0)
    assert OBSERVED_TROUGH_BPS == pytest.approx(obs["trough_bps"], abs=0.05)


@pytest.mark.parametrize(
    ("troughs", "expected"),
    [
        ([-2000.0, -1000.0], [(0.5 + 0.5 * 558 / 1000, 0.5 + 0.5 * 695.4 / 1000)]),
        ([-1000.0, -2000.0], [(0.5 + 0.5 * 304.6 / 1000, 0.5 + 0.5 * 442 / 1000)]),
        ([-500.0, -1000.0], []),
        ([-1373.0, -1373.0], [(0.5, 1.0)]),
    ],
)
def test_capital_ranges_interpolates_linearly(troughs, expected):
    got = it.capital_ranges([0.5, 1.0], troughs, -1442.0, -1304.6)
    assert len(got) == len(expected)
    for g, e in zip(got, expected, strict=True):
        assert g == pytest.approx(e)


def test_capital_ranges_merges_touching_and_keeps_disjoint_pieces():
    caps, troughs = [1, 2, 3, 4, 5], [-1400.0, -1400.0, -1350.0, -500.0, -1400.0]
    got = it.capital_ranges(caps, troughs, -1442.0, -1304.6)
    assert len(got) == 2
    assert got[0][0] == 1 and 3 < got[0][1] < 4
    assert 4 < got[1][0] < 5 and got[1][1] == 5


def _synthetic_sweep(tmp_path: Path) -> Path:
    spec = load_sweep(SPEC)
    rows = []
    for c in expand(spec):
        d, k = c.axis_values["pool_depth"], c.axis_values["holder_capital"]
        rows.append({"pool_depth": d, "holder_capital": k, "n": 1,
                     "max_depeg_bps_mean": -2000.0 if k < d else -1000.0 - 100 * d})  # fmt: skip
    sweep_dir = tmp_path / spec.name
    sweep_dir.mkdir()
    pd.DataFrame(rows).to_parquet(sweep_dir / "mc.parquet", index=False)
    manifest = {
        "sweep_name": spec.name,
        "spec_hash": "ab" * 32,
        "base_scenario_hash": "cd" * 32,
        "base_config": load_scenario(spec.base).model_dump(mode="json"),
        "axes": spec.manifest_axes(),
        "seeds": spec.seed_list(),
        "max_steps": None,
    }
    (sweep_dir / "manifest.json").write_text(json.dumps(manifest))
    return sweep_dir


def test_surface_renders_from_a_synthetic_sweep(tmp_path):
    png = plot_identification_surface(_synthetic_sweep(tmp_path))
    assert png.name == IDENTIFICATION_SURFACE and png.stat().st_size > 30_000
    assert plt.imread(png).shape[:2] == (1080, 1500)
    assert plt.get_fignums() == []


def test_table_smoke_and_deterministic(tmp_path):
    spec = load_sweep(SPEC)
    small = spec.model_copy(
        update={
            "linked_axes": [
                spec.linked_axes[0].model_copy(update={"values": [1, 2]}),
                spec.linked_axes[1].model_copy(update={"values": [0.9, 1]}),
            ]
        }
    )
    a = it.build(tmp_path / "a", max_steps=8400, spec=small)
    assert len(a["cells"]) == 4 and len(a["ladders"]) == 7
    assert a["observed"]["trough_bps"] == pytest.approx(-1373.3, abs=0.05)
    assert [r["capital"] for r in a["ladders"]] == [8_333_333, 10_833_333, 10_000_000] + [
        C_STAR_B
    ] * 4
    # ladder B at its own C* and at ladder B's C* are the same run
    assert a["ladders"][1]["trough_bps"] == a["ladders"][4]["trough_bps"]
    text = it.format_tables(a)
    assert text.startswith("observed trough -1,373.3 bps at 31.0 h")
    assert "2. capital (x ladder B's C* = 10,833,333)" in text
    assert "continuous (2, 4, ..., 20% at 10% each), ladder B's C*" in text
    # table 4 (Story 5.6): three fits, each a 5-point scan with C* in the middle
    assert [f["fit"] for f in a["fits"]] == [
        "holder-ladder-b.json", "holder-ladder-b-par.json", "holder-ladder-b-closed.json"
    ]  # fmt: skip
    assert [f["c_star"] for f in a["fits"]] == [C_STAR_B, C_STAR_B, 13_333_333]
    assert [s["capital"] for s in a["fits"][2]["scan"]] == CLOSED_SCAN
    assert all(f["scan"][2]["capital"] == f["c_star"] for f in a["fits"])
    assert "4. ladder B's C* by fit, with a 5-point scan" in text
    assert "par reference, channel closed (holder-ladder-b-closed.json) scan: 10,000,000" in text
    b = it.build(tmp_path / "b", max_steps=8400, spec=small)
    assert it.format_tables(b) == text


def test_continuous_ladder_is_ten_equal_tranches_over_2_to_20():
    tranches = it.CONTINUOUS[1]
    assert [d for d, _ in tranches] == [2.0 * k for k in range(1, 11)]
    assert {s for _, s in tranches} == {0.1}
    cfg = it.ladder_config(tranches, C_STAR_B, None)
    holder = next(a for a in cfg.agents if a.type == "holder")
    assert len(holder.tranches) == 10 and holder.capital == C_STAR_B


# Story 5.6: table 4's scan from the committed fit records -------------------------------


@pytest.mark.parametrize(
    ("name", "lo", "step", "scan"),
    [
        ("holder-ladder-b.json", 10_000_000, 5_000_000 / 6, OPEN_SCAN),
        ("holder-ladder-b-par.json", 10_000_000, 5_000_000 / 6, OPEN_SCAN),
        ("holder-ladder-b-closed.json", 10_000_000, 10_000_000 / 6, CLOSED_SCAN),
    ],
)
def test_scan_is_the_second_refinement_lattice(name, lo, step, scan):
    record = json.loads((it.FITS_DIR / name).read_text())
    assert it.refine_step(record) == pytest.approx((lo, step))
    assert it.scan_capitals(record["result"]["c_star"], lo, step) == scan
    # k = ±1 are capitals the fit itself ran
    ran = {r["holder_capital"] for r in record["result"]["runs"]}
    assert {scan[1], scan[3]} <= ran


def test_scan_off_the_lattice_centres_on_c_star():
    assert it.scan_capitals(10_400_000, 10_000_000, 1_000_000) == [
        8_400_000, 9_400_000, 10_400_000, 11_400_000, 12_400_000
    ]  # fmt: skip


def test_refine_step_rejects_runs_that_are_not_the_rule():
    record = json.loads((it.FITS_DIR / "holder-ladder-b-closed.json").read_text())
    record["result"]["runs"].append({"holder_capital": 12_345_678, "max_depeg_bps": -1500.0})
    with pytest.raises(ValueError, match="two-pass rule"):
        it.refine_step(record)
