"""Story 2.3: the calibrated scenarios, their sources table and their raw data."""

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from depeg_sim.experiments.runner import build_world
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine

SCENARIOS = ("scenarios/calibrated-baseline.yaml", "scenarios/calibrated-stress.yaml")
SOURCES = Path("docs/calibration/SOURCES.md")
DATA = Path("data")
STATUSES = {"verified", "secondary", "assumption"}


def leaf_paths(node, prefix=""):
    """Dotted config paths of every leaf, agents as ``agents[type=<type>].<field>``."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaf_paths(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list) and prefix == "agents":
        for agent in node:
            for k in agent:
                if k not in ("type", "id"):
                    yield f"agents[type={agent['type']}].{k}"
    else:
        yield prefix


@pytest.mark.parametrize("path", SCENARIOS)
def test_loads_and_follows_adr_0013(path):
    cfg = load_scenario(Path(path))
    assert [a.type for a in cfg.agents] == ["attacker", "arbitrageur", "defender"]
    arb = cfg.agents[1]
    band = (cfg.amm.fee_bps + arb.min_profit_bps) / 10_000
    assert cfg.termination.peg_recovered.tolerance >= band  # ADR-0013
    assert cfg.termination.peg_recovered.for_steps >= cfg.oracle.heartbeat_steps
    assert cfg.agents[0].start_step < cfg.termination.peg_recovered.for_steps  # ADR-0010
    assert cfg.steps.max_steps == 18_000
    # attacker sits at capital / (budget + reserves) = 1.0 (ADR-0018)
    assert cfg.agents[0].capital == cfg.agents[2].budget + cfg.redemption.reserves


def test_content_hashes_are_pinned():
    # A calibration change must be deliberate: update these with SOURCES.md.
    hashes = [load_scenario(Path(p)).content_hash()[:12] for p in SCENARIOS]
    assert hashes == ["fae4d315a5a6", "2d8b5013683f"]


def test_stress_differs_only_in_name_and_volatility():
    base, stress = (load_scenario(Path(p)).model_dump(mode="json") for p in SCENARIOS)
    assert base["environment"]["volatility_per_step"] == 3.086e-05
    assert stress["environment"]["volatility_per_step"] == 0.0007561
    for d in (base, stress):
        d.pop("name")
        d["environment"].pop("volatility_per_step")
    assert base == stress


@pytest.mark.parametrize("path", SCENARIOS)
def test_short_run_completes(path):
    cfg = set_path(load_scenario(Path(path)), "steps.max_steps", 500)
    cfg = set_path(cfg, "metrics.checkpoint_every", None)
    ctx = RunContext.from_config(cfg)
    build_world(cfg, ctx)
    result = Engine(ctx).run()
    assert result.steps_run <= 500
    assert result.terminated_by in {"max_steps", "peg_recovered", "reserves_exhausted"}


@pytest.mark.parametrize("path", SCENARIOS)
def test_header_points_at_sources(path):
    text = Path(path).read_text(encoding="utf-8")
    header = text.split("version:")[0]
    for section in (
        "time",
        "pool",
        "oracle",
        "redemption",
        "environment",
        "attacker",
        "defender",
        "arbitrageur",
        "termination",
    ):
        assert f"SOURCES.md#{section}" in header
    assert "ADR-0013" in header and "ADR-0017" in header


def table_rows(text):
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            yield [c.strip() for c in line.strip().strip("|").split("|")]


def test_every_sources_row_has_a_status():
    tables = 0
    for cells in table_rows(SOURCES.read_text(encoding="utf-8")):
        if cells[0] == "parameter":
            tables += 1
            assert cells == [
                "parameter",
                "value used",
                "source (URL, accessed)",
                "raw figure",
                "conversion",
                "status",
            ]
            continue
        if cells[0].startswith("`"):  # a parameter row
            assert len(cells) == 6, cells
            assert all(cells), f"empty cell in {cells[0]}"
            assert cells[-1] in STATUSES, f"{cells[0]}: status {cells[-1]!r}"
    assert tables >= 9


@pytest.mark.parametrize("path", SCENARIOS)
def test_every_scenario_parameter_has_a_row(path):
    text = SOURCES.read_text(encoding="utf-8")
    rows = {cells[0].split(" ")[0].strip("`") for cells in table_rows(text)}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    skip = {"version", "name"}
    params = [p for p in leaf_paths(data) if p.split(".")[0] not in skip and p != "assets"]
    missing = [p for p in params if p not in rows]
    assert missing == []


def test_data_files_small_and_documented():
    readme = (DATA / "README.md").read_text(encoding="utf-8")
    csvs = sorted(DATA.glob("*.csv"))
    assert len(csvs) == 3
    for f in csvs:
        assert f.stat().st_size < 1_000_000
        assert f"`{f.name}`" in readme
        assert hashlib.sha256(f.read_bytes()).hexdigest() in readme


D_STAR = 1_833_333_333  # Story 2.4: scripts/fit_depth.py, trough -1327.8 bps vs -1300 observed


@pytest.mark.parametrize("path", SCENARIOS)
def test_pool_is_fitted_aggregate_depth(path):
    cfg = load_scenario(Path(path))
    assert cfg.amm.reserve_stable == cfg.amm.reserve_reference == D_STAR
    header = Path(path).read_text(encoding="utf-8").split("version:")[0]
    assert "market_depth_multiple = D* / 1,000,000" in header and "F-05" in header


def test_sources_has_market_depth_multiple_row():
    rows = {cells[0]: cells for cells in table_rows(SOURCES.read_text(encoding="utf-8"))}
    row = rows["`market_depth_multiple`"]
    assert row[1] == f"{D_STAR / 1_000_000:.2f}"
    assert row[-1] == "assumption"
    assert "fitted to observed trough, this story" in row[2]
