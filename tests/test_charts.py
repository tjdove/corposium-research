import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from test_metrics import cfg_with

from depeg_sim.analysis.charts import (
    plot_oracle_sensitivity,
    plot_peg_trajectory,
    plot_threshold_surface,
    plot_time_to_parity,
    time_to_parity_hours,
)
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.kernel.config import ScenarioConfig, load_scenario


def test_backend_is_headless():
    assert matplotlib.get_backend().lower() == "agg"


def test_peg_trajectory_png(tmp_path):
    art = run_scenario(
        load_scenario("scenarios/soros-baseline.yaml"), output_dir=tmp_path, chart=False
    )
    png = plot_peg_trajectory(art.run_dir)
    assert png == art.run_dir / "peg_trajectory.png"
    assert png.stat().st_size > 20_000
    img = plt.imread(png)
    assert img.ndim == 3 and img.shape[2] in (3, 4)
    assert img.shape[:2] == (900, 1500)  # 10x6 in at 150 dpi
    assert plt.get_fignums() == []  # figure closed


def test_chart_without_attack_or_defense(tmp_path):
    data = cfg_with(max_steps=20).model_dump(mode="json")
    data["agents"] = []
    art = run_scenario(ScenarioConfig.model_validate(data), output_dir=tmp_path, chart=False)
    assert plot_peg_trajectory(art.run_dir).is_file()


# Story 2.7: sweep charts from a synthetic mc.parquet + manifest -------------------------

ATK = "agents[type=attacker].capital"
HB, TH = "oracle.heartbeat_steps", "oracle.deviation_threshold_pct"


def _manifest(sweep_dir, name, base_path, axes, seeds=16):
    base = load_scenario(base_path)
    m = {
        "sweep_name": name,
        "base_scenario_hash": base.content_hash(),
        "base_config": base.model_dump(mode="json"),
        "axes": axes,
        "seeds": list(range(1000, 1000 + seeds)),
        "max_steps": 18000,
    }
    (sweep_dir / "manifest.json").write_text(json.dumps(m))


def _surface_dir(tmp_path, step_at=1.0):
    """5 depths x 3 capitals; p_peg_recovered 1.0 below absorbed ratio ``step_at``, 0 above."""
    d = tmp_path / "surf"
    d.mkdir()
    depths = [4_166_667, 8_333_334, 16_666_667, 33_333_334, 66_666_668]
    caps = [53_836_317, 89_727_196, 179_454_391]
    rows = []
    for i, depth in enumerate(depths):
        for cap in caps:
            absorbed = cap / (0.9 + 0.1 * caps.index(cap) + 0.01 * i)
            ratio = cap / absorbed
            rows.append(
                {
                    "pool_depth": depth,
                    ATK: cap,
                    "n": 16,
                    "defender_bought_stable_mean": 0.8 * absorbed,
                    "holder_bought_stable_mean": 0.15 * absorbed,
                    "redemption_paid_total_mean": 0.05 * absorbed,
                    "p_peg_recovered": 1.0 if ratio < step_at else 0.0,
                }
            )
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {
            "name": "pool_depth",
            "paths": ["amm.reserve_stable", "amm.reserve_reference", "agents[type=holder].capital"],
            "values": depths,
            "scales": [1, 1, 0.55],
        },
        {"name": ATK, "paths": [ATK], "values": caps},
    ]
    _manifest(d, "surf", "scenarios/calibrated-baseline.yaml", axes)
    return d


def test_threshold_surface_png(tmp_path):
    d = _surface_dir(tmp_path)
    png = plot_threshold_surface(d)
    assert png == d / "threshold_surface.png"
    assert png.stat().st_size > 20_000
    img = plt.imread(png)
    assert img.shape[:2] == (900, 3000)  # two 10x6 in panels at 150 dpi
    assert plt.get_fignums() == []


def test_threshold_surface_without_any_crossing(tmp_path):
    # every cell recovers: no 0.5 contour to draw, the chart still renders
    d = _surface_dir(tmp_path, step_at=10.0)
    assert plot_threshold_surface(d).is_file()


def test_oracle_sensitivity_png(tmp_path):
    d = tmp_path / "oracle"
    d.mkdir()
    rows = []
    for th in (0.0, 0.25):
        for hb in (5, 300, 6900):
            rows.append(
                {
                    HB: hb,
                    TH: th,
                    "n": 32,
                    "max_depeg_bps_mean": -1243.0 - th * hb / 1000,
                    "max_depeg_bps_p05": -1253.0,
                    "max_depeg_bps_p95": -1200.0,
                    "p_peg_recovered": 0.3,
                }
            )
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {"name": HB, "paths": [HB], "values": [5, 300, 6900]},
        {"name": TH, "paths": [TH], "values": [0.0, 0.25]},
    ]
    _manifest(d, "oracle", "scenarios/calibrated-stress.yaml", axes, seeds=32)
    png = plot_oracle_sensitivity(d)
    assert png == d / "oracle_sensitivity.png"
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (1800, 1500)  # two stacked 10x6 in panels
    assert plt.get_fignums() == []


def test_sweep_chart_needs_its_axis(tmp_path):
    d = _surface_dir(tmp_path)
    m = json.loads((d / "manifest.json").read_text())
    m["axes"] = m["axes"][1:]
    (d / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="amm.reserve_stable"):
        plot_threshold_surface(d)


# Story 2.8: budget x depth and the criterion heading -----------------------------------

BUD = "agents[type=defender].budget"


def test_budget_crossing_kinds():
    from depeg_sim.analysis.charts import budget_crossing

    assert budget_crossing([1, 2, 4], [1.0, 0.0, 0.0]) == (1.5, "crossing")
    assert budget_crossing([4, 1, 2], [0.0, 1.0, 0.75]) == (pytest.approx(8 / 3), "crossing")
    assert budget_crossing([1, 2, 4], [0.25, 0.1, 0.0]) == (None, "below")
    assert budget_crossing([1, 2, 4], [1.0, 1.0, 0.5]) == (None, "above")


def test_criterion_helpers():
    from depeg_sim.analysis.charts import _against, _criterion

    assert _criterion({}) == "reference=par" and _against({}) == "par"
    assert _criterion({"reference": "oracle"}) == "reference=oracle"
    assert _against({"reference": "oracle"}) == "the published oracle price"


def _budget_dir(tmp_path, ps):
    d = tmp_path / "bud"
    d.mkdir()
    depths, budgets = [8_333_334, 16_666_667, 33_333_334], [20_673_487, 41_346_974, 82_693_948]
    rows = [
        {"pool_depth": dep, BUD: b, "n": 8, "p_peg_recovered": 1.0 - ps[i][j]}
        for i, dep in enumerate(depths)
        for j, b in enumerate(budgets)
    ]
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {
            "name": "pool_depth",
            "paths": ["amm.reserve_stable", "amm.reserve_reference", "agents[type=holder].capital"],
            "values": depths,
            "scales": [1, 1, 0.55],
        },
        {"name": BUD, "paths": [BUD], "values": budgets},
    ]
    _manifest(d, "bud", "scenarios/calibrated-baseline.yaml", axes, seeds=8)
    return d


def test_budget_depth_png_monotone_crossing(tmp_path):
    from depeg_sim.analysis.charts import plot_budget_depth

    # crossing budget rises with depth: one crossing per row -> three points
    ps = [[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [1.0, 1.0, 0.25]]
    png = plot_budget_depth(_budget_dir(tmp_path, ps))
    assert png.name == "budget_depth.png" and png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 3000)
    assert plt.get_fignums() == []


def test_budget_depth_with_bounds(tmp_path):
    from depeg_sim.analysis.charts import plot_budget_depth

    # one row holds everywhere (below), one never holds (above), one crossing
    ps = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    assert plot_budget_depth(_budget_dir(tmp_path, ps)).is_file()


# Story 2.9: time to parity -------------------------------------------------------------


def _parity_dir(tmp_path, trough_spread=0.0):
    """3 depths x 3 capitals. Entry steps from the trough chosen so that, with the trough
    at step 50 and 12 s steps: early (< 37 h), late (>= 37 h: clock) and never cells."""
    d = tmp_path / "parity"
    d.mkdir()
    depths = [8_333_334, 16_666_667, 33_333_334]
    caps = [53_836_317, 89_727_196, 179_454_391]
    entry = {  # (depth index, capital index) -> steps from trough, None = never
        (0, 0): 20, (0, 1): 100, (0, 2): 5_000,
        (1, 0): 30, (1, 1): 11_200, (1, 2): 14_000,
        (2, 0): 40, (2, 1): None, (2, 2): None,
    }  # fmt: skip
    rows = []
    for i, depth in enumerate(depths):
        for j, cap in enumerate(caps):
            e = entry[(i, j)]
            rows.append(
                {
                    "pool_depth": depth,
                    ATK: cap,
                    "n": 16,
                    "step_of_max_depeg_std": trough_spread,
                    "step_of_max_depeg_p05": 50.0 - trough_spread,
                    "step_of_max_depeg_p50": 50.0,
                    "step_of_max_depeg_p95": 50.0 + trough_spread,
                    "steps_to_first_band_entry_p50": float("nan") if e is None else float(e),
                    "steps_to_first_band_entry_n": 0 if e is None else 16,
                }
            )
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {"name": "pool_depth", "paths": ["amm.reserve_stable", "amm.reserve_reference"],
         "values": depths},
        {"name": ATK, "paths": [ATK], "values": caps},
    ]  # fmt: skip
    _manifest(d, "parity", "scenarios/calibrated-baseline.yaml", axes)
    return d


def test_time_to_parity_hours_from_run_start():
    mc = pd.DataFrame(
        {
            "n": [16, 16, 16],
            "step_of_max_depeg_std": [0.0, 0.0, float("nan")],
            "step_of_max_depeg_p05": [50.0, 80.0, 80.0],
            "step_of_max_depeg_p50": [50.0, 80.0, 80.0],
            "step_of_max_depeg_p95": [50.0, 80.0, 80.0],
            "steps_to_first_band_entry_p50": [250.0, 11_020.0, 40.0],
            "steps_to_first_band_entry_n": [16, 8, 7],
        }
    )
    h = time_to_parity_hours(mc, 12)
    assert h[0] == pytest.approx(300 * 12 / 3600)  # trough step added back: 1.0 h
    assert h[1] == pytest.approx(37.0)  # exactly half re-enter: still finite
    assert pd.isna(h[2])  # fewer than half re-enter: never


def test_time_to_parity_needs_one_trough_step_per_cell():
    mc = pd.DataFrame(
        {
            "n": [16],
            "step_of_max_depeg_std": [2.0],
            "step_of_max_depeg_p05": [48.0],
            "step_of_max_depeg_p50": [50.0],
            "step_of_max_depeg_p95": [52.0],
            "steps_to_first_band_entry_p50": [100.0],
            "steps_to_first_band_entry_n": [16],
        }
    )
    with pytest.raises(ValueError, match="trough step differs across seeds"):
        time_to_parity_hours(mc, 12)


def test_time_to_parity_png(tmp_path):
    d = _parity_dir(tmp_path)
    png = plot_time_to_parity(d)
    assert png == d / "time_to_parity.png"
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 1500)  # one 10x6 in panel at 150 dpi
    assert plt.get_fignums() == []


def test_time_to_parity_png_refuses_trough_spread(tmp_path):
    d = _parity_dir(tmp_path, trough_spread=3.0)
    with pytest.raises(ValueError, match="trough step differs"):
        plot_time_to_parity(d)
    plt.close("all")


def test_include_texts_keeps_offset_labels_inside_the_axes():
    # Story 2.6 review ruling 4: the overlay clipped the label 30 points below the trough
    from depeg_sim.analysis.charts import _include_texts

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150, constrained_layout=True)
    ax.plot([0, 1, 2], [0, -1000, -200])
    label = ax.annotate(
        "observed trough", xy=(1, -1000), xytext=(40, -30), textcoords="offset points"
    )
    _include_texts(fig, ax, [label])
    fig.canvas.draw()
    bottom = ax.transAxes.inverted().transform(label.get_window_extent())[0, 1]
    assert bottom >= 0.0
    plt.close(fig)


# Story 3.3: holder exit chart from a synthetic mc.parquet + manifest ---------------------


def _holder_exit_dir(tmp_path):
    from depeg_sim.experiments.sweep import load_sweep

    d = tmp_path / "hx"
    d.mkdir()
    spec = load_sweep(Path("sweeps/holder-exit-1992-mc.yaml"))
    axes = spec.manifest_axes()
    exits, caps = axes[0]["values"], axes[1]["values"]
    rows = []
    for i, x in enumerate(exits):
        for j, c in enumerate(caps):
            p = [1.0, 0.5, 0.0][j] if x is None else 1.0
            rows.append({
                axes[0]["name"]: np.nan if x is None else float(x), axes[1]["name"]: c, "n": 8,
                "p_reserves_exhausted": p, "steps_run_mean": 9_550.0 + 50 * j,
                "holder_pnl_mean": 1e5 if x is None else -1e6 * (i + 1),
                "holder_pnl_p05": -2e6, "holder_pnl_p95": 2e5,
            })  # fmt: skip
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    _manifest(d, "holder-exit-1992-mc", "scenarios/soros-1992.yaml", axes, seeds=8)
    return d


def test_holder_exit_png(tmp_path):
    from depeg_sim.analysis.charts import plot_holder_exit

    d = _holder_exit_dir(tmp_path)
    png = plot_holder_exit(d)
    assert png == d / "holder_exit.png"
    assert png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (960, 2250)  # 15 x 6.4 in at 150 dpi
    assert plt.get_fignums() == []


def test_holder_exit_labels_null_as_never_sells():
    from depeg_sim.analysis.charts import _exit_label

    assert _exit_label(np.nan) == "never sells" and _exit_label(10.0) == "sells below\n−10%"


def test_holder_exit_needs_its_axes(tmp_path):
    from depeg_sim.analysis.charts import plot_holder_exit

    d = _holder_exit_dir(tmp_path)
    m = json.loads((d / "manifest.json").read_text())
    m["axes"] = m["axes"][1:]
    (d / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="no axis setting"):
        plot_holder_exit(d)


# Story 3.4: budget x attack ----------------------------------------------------------------


def _budget_attack_dir(tmp_path, never):
    """3 budgets x 3 attacks at 2x D*; ``never[i][j]`` = seeds (of 8) that never re-enter."""
    d = tmp_path / "budatk"
    d.mkdir()
    budgets, caps = [20_673_487, 41_346_974, 82_693_948], [89_727_196, 179_454_391, 358_908_782]
    rows = [
        {BUD: b, ATK: c, "n": 8, "steps_to_first_band_entry_n": 8 - never[i][j]}
        for i, b in enumerate(budgets)
        for j, c in enumerate(caps)
    ]
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {"name": BUD, "paths": [BUD], "values": budgets},
        {"name": ATK, "paths": [ATK], "values": caps},
    ]
    _manifest(d, "budatk", "scenarios/calibrated-baseline.yaml", axes, seeds=8)
    return d


def test_p_never_reenters_counts_only_seeds_that_never_reenter():
    from depeg_sim.analysis.charts import p_never_reenters

    mc = pd.DataFrame({"n": [8, 8, 8], "steps_to_first_band_entry_n": [8, 3, 0]})
    p, lo, hi = p_never_reenters(mc)
    assert p.tolist() == [0.0, 0.625, 1.0]
    assert (lo <= p).all() and (p <= hi).all() and lo[0] == 0.0 and hi[2] == 1.0


def test_loglog_slope():
    from depeg_sim.analysis.charts import loglog_slope

    assert loglog_slope([(1, 3), (2, 6), (4, 12)]) == pytest.approx(1.0)
    assert loglog_slope([(1, 5), (10, 5)]) == pytest.approx(0.0)


def test_budget_attack_png_monotone_crossing(tmp_path):
    from depeg_sim.analysis.charts import plot_budget_attack

    # crossing budget rises with attack: one crossing per attack column -> three points
    never = [[4, 8, 8], [0, 8, 8], [0, 0, 6]]
    png = plot_budget_attack(_budget_attack_dir(tmp_path, never))
    assert png.name == "budget_attack.png" and png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 3000)
    assert plt.get_fignums() == []


def test_budget_attack_with_bounds(tmp_path):
    from depeg_sim.analysis.charts import plot_budget_attack

    # one column holds everywhere (below), one never holds (above), one crossing
    never = [[0, 8, 8], [0, 0, 8], [0, 0, 8]]
    assert plot_budget_attack(_budget_attack_dir(tmp_path, never)).is_file()
    assert plt.get_fignums() == []


# Story 3.4: pace x trigger -----------------------------------------------------------------

APACE, DPACE, TRIG = (
    "agents[type=attacker].pace",
    "agents[type=defender].spend_pace",
    "agents[type=defender].threshold_pct",
)


def _pace_trigger_dir(tmp_path, atk_paces=(0.1, 0.02)):
    """2 attacker paces x 3 defender paces x 2 triggers; at attacker pace 0.1 hours rise
    with defender pace (fast, clock, never); at 0.02 everything never re-enters."""
    d = tmp_path / "pacetrig"
    d.mkdir()
    paces, trigs = [0.05, 0.2, 0.5], [1.0, 4.0]
    entry = {0.05: 100, 0.2: 12_000, 0.5: None}
    rows = []
    for ap in atk_paces:
        for p in paces:
            for t in trigs:
                e = entry[p] if ap == 0.1 else None
                rows.append(
                    {
                        APACE: ap, DPACE: p, TRIG: t, "n": 8,
                        "step_of_max_depeg_std": 0.0,
                        "step_of_max_depeg_p05": 50.0,
                        "step_of_max_depeg_p50": 50.0,
                        "step_of_max_depeg_p95": 50.0,
                        "steps_to_first_band_entry_p50": float("nan") if e is None else float(e),
                        "steps_to_first_band_entry_n": 0 if e is None else 8,
                        "defender_spent_mean": 41_346_974.0,
                        "defender_bought_stable_mean": 41_346_974.0 / (0.25 + p / 4),
                    }
                )  # fmt: skip
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {"name": APACE, "paths": [APACE], "values": list(atk_paces)},
        {"name": DPACE, "paths": [DPACE], "values": paces},
        {"name": TRIG, "paths": [TRIG], "values": trigs},
    ]
    _manifest(d, "pacetrig", "scenarios/calibrated-baseline.yaml", axes, seeds=8)
    return d


def test_pace_trigger_png_three_axis_grid(tmp_path):
    from depeg_sim.analysis.charts import plot_pace_trigger

    png = plot_pace_trigger(_pace_trigger_dir(tmp_path))
    assert png.name == "pace_trigger.png" and png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 3300)  # (8 x 2 + 6) x 6 in at 150 dpi
    assert plt.get_fignums() == []


def test_pace_trigger_needs_the_base_attacker_pace_on_its_axis(tmp_path):
    from depeg_sim.analysis.charts import plot_pace_trigger

    with pytest.raises(ValueError, match="base attacker pace 0.1"):
        plot_pace_trigger(_pace_trigger_dir(tmp_path, atk_paces=(0.05, 0.02)))
    plt.close("all")


def test_deadline_crossing_kinds():
    from depeg_sim.analysis.charts import deadline_crossing

    nan = float("nan")
    r, kind = deadline_crossing([0.5, 1.0], [7.0, 47.0], 37.0)
    assert kind == "crossing" and r == pytest.approx(0.5 * 2 ** (30 / 40))
    assert deadline_crossing([1.0, 0.5, 2.0], [47.0, 7.0, nan], 37.0)[1] == "crossing"
    assert deadline_crossing([0.5, 1.0, 1.5], [7.0, 30.0, nan], 37.0) == (1.0, "before")
    assert deadline_crossing([0.1, 1.0], [0.4, 29.9], 37.0) == (None, "below")
    assert deadline_crossing([1.5, 5.0], [nan, nan], 37.0) == (None, "above")
    assert deadline_crossing([1.0, 2.0], [37.0, 50.0], 37.0) == (None, "above")


def _pace_ratio_dir(tmp_path):
    """2 attacker paces x 4 defender paces: at 0.1 every point re-enters early; at 0.02
    hours rise through the deadline and then never re-enter."""
    d = tmp_path / "paceratio"
    d.mkdir()
    paces = [0.005, 0.01, 0.02, 0.05]
    entry = {0.1: {p: 100 for p in paces}, 0.02: {0.005: 500, 0.01: 2_000, 0.02: 14_000,
                                                0.05: None}}  # fmt: skip
    rows = []
    for ap in (0.1, 0.02):
        for p in paces:
            e = entry[ap][p]
            rows.append(
                {
                    APACE: ap, DPACE: p, "n": 8,
                    "step_of_max_depeg_std": 0.0,
                    "step_of_max_depeg_p05": 50.0,
                    "step_of_max_depeg_p50": 50.0,
                    "step_of_max_depeg_p95": 50.0,
                    "steps_to_first_band_entry_p50": float("nan") if e is None else float(e),
                    "steps_to_first_band_entry_n": 0 if e is None else 8,
                }
            )  # fmt: skip
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    axes = [
        {"name": APACE, "paths": [APACE], "values": [0.1, 0.02]},
        {"name": DPACE, "paths": [DPACE], "values": paces},
    ]
    _manifest(d, "paceratio", "scenarios/calibrated-baseline.yaml", axes, seeds=8)
    return d


def test_pace_ratio_png_one_panel(tmp_path):
    from depeg_sim.analysis.charts import plot_pace_ratio

    png = plot_pace_ratio(_pace_ratio_dir(tmp_path))
    assert png.name == "pace_ratio.png" and png.stat().st_size > 20_000
    assert plt.imread(png).shape[:2] == (900, 1500)  # 10 x 6 in at 150 dpi
    assert plt.get_fignums() == []


def test_pace_ratio_needs_both_pace_axes(tmp_path):
    from depeg_sim.analysis.charts import plot_pace_ratio

    d = _pace_ratio_dir(tmp_path)
    m = json.loads((d / "manifest.json").read_text())
    m["axes"] = m["axes"][1:]
    (d / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="no axis setting"):
        plot_pace_ratio(d)


def test_reversion_heading_only_when_the_reference_reverts():
    from depeg_sim.analysis.charts import _reversion

    assert _reversion({"volatility_per_step": 3e-5}) == ""  # pre-3.6 manifests
    assert _reversion({"mean_reversion_per_step": 0.0}) == ""
    assert _reversion({"mean_reversion_per_step": 0.001634}) == "; OU reference, κ 0.001634/step"
