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


def test_termination_max_steps_false_rejected(tmp_path, baseline_dict):
    baseline_dict["termination"] = {
        "reserves_exhausted": True,
        "peg_recovered": {"for_steps": 10, "tolerance": 0.01},
        "max_steps": False,
    }
    with pytest.raises(ValidationError) as exc:
        load_scenario(write(tmp_path, baseline_dict))
    msg = str(exc.value)
    assert "termination.max_steps" in msg
    assert "safety cap" in msg


def test_termination_single_condition_accepted(tmp_path, baseline_dict):
    baseline_dict["termination"] = {
        "reserves_exhausted": False,
        "peg_recovered": None,
        "max_steps": True,
    }
    cfg = load_scenario(write(tmp_path, baseline_dict))
    assert cfg.termination.max_steps is True
    assert not cfg.termination.reserves_exhausted
    assert cfg.termination.peg_recovered is None


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


# Story 2.5: price_series_path and capacity_schedule -------------------------------


def series_scenario(tmp_path, baseline_dict, closes, name="s.csv"):
    (tmp_path / name).write_text(
        "unix,close\n" + "".join(f"{1678406400 + 3600 * i},{c}\n" for i, c in enumerate(closes)),
        encoding="utf-8",
    )
    data = copy.deepcopy(baseline_dict)
    data["environment"] = {
        "base_price": 1.0,
        "volatility_per_step": 0.0,
        "shocks": [],
        "price_series_path": name,
    }
    return load_scenario(write(tmp_path, data))


def test_series_path_resolves_against_the_scenario_file(tmp_path, baseline_dict):
    cfg = series_scenario(tmp_path, baseline_dict, [1.0, 0.9])
    assert cfg.environment.price_series_path == (tmp_path / "s.csv").resolve()
    assert len(cfg.environment.price_series_sha256) == 64


def test_series_hash_follows_the_csv_bytes(tmp_path, baseline_dict):
    dirs = [tmp_path / d for d in "abc"]
    for d in dirs:
        d.mkdir()
    a, b, c = (
        series_scenario(d, baseline_dict, closes)
        for d, closes in zip(dirs, ([1.0, 0.9], [1.0, 0.8], [1.0, 0.9]), strict=True)
    )
    assert a.model_dump(exclude={"environment"}) == b.model_dump(exclude={"environment"})
    assert a.content_hash() != b.content_hash()
    assert a.content_hash() == c.content_hash()  # same bytes, different directory


@pytest.mark.parametrize(
    "extra", [{"volatility_per_step": 0.001}, {"shocks": [{"step": 1, "pct": -1.0}]}]
)
def test_series_forbids_noise_and_shocks(tmp_path, baseline_dict, extra):
    (tmp_path / "s.csv").write_text("unix,close\n0,1.0\n", encoding="utf-8")
    data = copy.deepcopy(baseline_dict)
    data["environment"] = {"price_series_path": "s.csv", **extra}
    with pytest.raises(
        ValidationError, match="volatility_per_step must be 0 and shocks must be empty"
    ):
        load_scenario(write(tmp_path, data))


def test_new_fields_absent_leave_existing_hashes_unchanged():
    pinned = {
        "scenarios/soros-baseline.yaml": "2e09f431ce74",
        "scenarios/soros-volatile.yaml": "84ad0b810807",
    }
    for path, h in pinned.items():
        cfg = load_scenario(Path(path))
        assert cfg.environment.price_series_path is None
        assert cfg.redemption.capacity_schedule == []
        assert cfg.content_hash()[:12] == h


def test_defender_buy_and_spread_cap_defaults_leave_every_scenario_hash_unchanged():
    """Story 3.2: ``buy`` and ``max_spread_bps`` at their defaults do not enter the hash.
    Pinned at the Story 3.1 commit (14aed1e)."""
    pinned = {
        "scenarios/calibrated-baseline.yaml": "44ac03c60e5f",
        "scenarios/calibrated-stress.yaml": "17b24b458e47",
        "scenarios/soros-1992-no-defense.yaml": "516edaef4795",
        "scenarios/soros-1992.yaml": "f4e26ae66440",
        "scenarios/soros-baseline.yaml": "2e09f431ce74",
        "scenarios/soros-volatile.yaml": "84ad0b810807",
        "scenarios/usdc-2023.yaml": "2c3aeaa9825d",
    }
    for path, h in pinned.items():
        cfg = load_scenario(Path(path))
        for a in cfg.agents:
            if a.type == "defender":
                assert (a.buy, a.max_spread_bps) == (True, None)
        assert cfg.content_hash()[:12] == h, path


def test_defender_buy_false_and_cap_enter_the_hash(tmp_path, baseline_dict):
    i = next(k for k, a in enumerate(baseline_dict["agents"]) if a["type"] == "defender")
    h0 = load_scenario(write(tmp_path, copy.deepcopy(baseline_dict))).content_hash()
    for extra in ({"buy": False}, {"max_spread_bps": 500}):
        d = copy.deepcopy(baseline_dict)
        d["agents"][i] |= extra
        assert load_scenario(write(tmp_path, d)).content_hash() != h0
    d = copy.deepcopy(baseline_dict)
    d["agents"][i] |= {"buy": True, "max_spread_bps": None}  # explicit defaults
    assert load_scenario(write(tmp_path, d)).content_hash() == h0


@pytest.mark.parametrize("bad", [-1, 10_000])
def test_defender_max_spread_bps_range(tmp_path, baseline_dict, bad):
    i = next(k for k, a in enumerate(baseline_dict["agents"]) if a["type"] == "defender")
    baseline_dict["agents"][i]["max_spread_bps"] = bad
    with pytest.raises(ValidationError):
        load_scenario(write(tmp_path, baseline_dict))
