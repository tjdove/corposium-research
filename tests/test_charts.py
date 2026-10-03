import matplotlib
import matplotlib.pyplot as plt
from test_metrics import cfg_with

from depeg_sim.analysis.charts import plot_peg_trajectory
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.kernel.config import ScenarioConfig, load_scenario


def test_backend_is_headless():
    assert matplotlib.get_backend().lower() == "agg"


def test_peg_trajectory_png(tmp_path):
    art = run_scenario(load_scenario("scenarios/soros-baseline.yaml"), output_dir=tmp_path)
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
    art = run_scenario(ScenarioConfig.model_validate(data), output_dir=tmp_path)
    assert plot_peg_trajectory(art.run_dir).is_file()
