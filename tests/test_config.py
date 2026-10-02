import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from depeg_sim.kernel.config import (
    ArbitrageurConfig,
    AttackerConfig,
    DefenderConfig,
    ScenarioConfig,
    load_scenario,
)

BASELINE = Path("scenarios/soros-baseline.yaml")
TOP_LEVEL_FIELDS = list(ScenarioConfig.model_fields)


@pytest.fixture
def baseline_dict() -> dict:
    with open(BASELINE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_baseline_loads():
    cfg = load_scenario(BASELINE)
    assert isinstance(cfg, ScenarioConfig)
    assert cfg.name == "soros-baseline"
    assert cfg.seed == 42
    assert len(cfg.agents) == 3


def test_top_level_field_list_matches_spec():
    assert TOP_LEVEL_FIELDS == [
        "version",
        "name",
        "seed",
        "steps",
        "assets",
        "amm",
        "oracle",
        "redemption",
        "environment",
        "agents",
        "termination",
        "metrics",
    ]


@pytest.mark.parametrize("field", TOP_LEVEL_FIELDS)
def test_missing_top_level_field_raises(tmp_path, baseline_dict, field):
    del baseline_dict[field]
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert field in str(exc.value)


def test_unknown_top_level_field_raises(tmp_path, baseline_dict):
    baseline_dict["foo"] = 1
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "foo" in str(exc.value)


def test_unknown_nested_field_raises(tmp_path, baseline_dict):
    baseline_dict["amm"]["foo"] = 1
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "amm.foo" in str(exc.value)


def test_unknown_agent_field_raises(tmp_path, baseline_dict):
    baseline_dict["agents"][0]["foo"] = 1
    with pytest.raises(ValidationError):
        load_scenario(write(tmp_path, baseline_dict))


def test_version_2_rejected(tmp_path, baseline_dict):
    baseline_dict["version"] = 2
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    msg = str(exc.value)
    assert "version" in msg
    assert "1" in msg.split("version", 1)[1]


def test_each_agent_type_parses_to_its_model():
    cfg = load_scenario(BASELINE)
    assert [type(a) for a in cfg.agents] == [AttackerConfig, ArbitrageurConfig, DefenderConfig]


def test_unknown_agent_type_rejected(tmp_path, baseline_dict):
    baseline_dict["agents"][0]["type"] = "liquidator"
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "liquidator" in str(exc.value)


def test_duplicate_agent_id_rejected(tmp_path, baseline_dict):
    baseline_dict["agents"][1]["id"] = baseline_dict["agents"][0]["id"]
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "duplicate" in str(exc.value)


def test_interval_seconds_zero_rejected(tmp_path, baseline_dict):
    baseline_dict["steps"]["interval_seconds"] = 0
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "interval_seconds" in str(exc.value)


def test_interval_seconds_defaults_to_12(tmp_path, baseline_dict):
    del baseline_dict["steps"]["interval_seconds"]
    assert load_scenario(write(tmp_path, baseline_dict)).steps.interval_seconds == 12


def test_termination_nothing_enabled_rejected(tmp_path, baseline_dict):
    baseline_dict["termination"] = {
        "reserves_exhausted": False,
        "peg_recovered": None,
        "max_steps": False,
    }
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    assert "termination" in str(exc.value)


def test_termination_single_condition_accepted(tmp_path, baseline_dict):
    baseline_dict["termination"] = {"reserves_exhausted": False, "max_steps": False}
    baseline_dict["termination"]["peg_recovered"] = {"for_steps": 10, "tolerance": 0.01}
    cfg = load_scenario(write(tmp_path, baseline_dict))
    assert cfg.termination.peg_recovered is not None


def test_config_is_frozen():
    cfg = load_scenario(BASELINE)
    with pytest.raises(ValidationError):
        cfg.seed = 7


def test_hash_stable_across_loads():
    h1 = load_scenario(BASELINE).content_hash()
    h2 = load_scenario(BASELINE).content_hash()
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_hash_changes_when_seed_changes(tmp_path, baseline_dict):
    original = load_scenario(write(tmp_path, copy.deepcopy(baseline_dict))).content_hash()
    baseline_dict["seed"] = 43
    changed = load_scenario(write(tmp_path, baseline_dict)).content_hash()
    assert original != changed
