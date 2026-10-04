"""Story 2.6 AC 2: ``HolderConfig`` joins the agent union without moving any hash."""

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from depeg_sim.kernel.config import HolderConfig, ScenarioConfig, load_scenario

SCENARIO_DIR = Path("scenarios")

# content_hash() of every scenario as of Story 2.5 (commit 9a62e23), before HolderConfig
# existed. With any holder entries removed, each scenario must still hash to this value:
# the schema change moves nothing, and a holder is the only 2.6 change to any scenario.
PRE_HOLDER_HASHES = {
    "calibrated-baseline": "0ef967d36e345525a8732da87674be5ab3a968887cc121768473163658992881",
    "calibrated-stress": "d7fe2f1626b8c81c3da7ff12e0123814ebd3d556d824a20b9e981c0ff46162e6",
    "soros-1992-no-defense": "1badaed6cf4a01f43b96240ef08cd84f857c2936c99992097ca331a91ef0b673",
    "soros-1992": "329eda7c21187e0d618997a96ff86b19d4fe7be8127dcd59af9321507b5af0f1",
    "soros-baseline": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023": "73db527c8ddf7fd82391a927430d538b71600564a72ce92da9648e7267d3bd88",
}

HOLDER = {
    "type": "holder",
    "id": "holder-1",
    "capital": 1_000_000,
    "entry_discount_pct": 2.0,
    "pace": 0.05,
}


def without_holders(cfg: ScenarioConfig) -> ScenarioConfig:
    data = cfg.model_dump(mode="json")
    data["agents"] = [a for a in data["agents"] if a["type"] != "holder"]
    return ScenarioConfig.model_validate(data)


def test_every_scenario_is_pinned():
    assert sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml")) == sorted(PRE_HOLDER_HASHES)


@pytest.mark.parametrize("name", sorted(PRE_HOLDER_HASHES))
def test_hash_unchanged_by_holder_schema(name):
    cfg = load_scenario(SCENARIO_DIR / f"{name}.yaml")
    assert without_holders(cfg).content_hash() == PRE_HOLDER_HASHES[name]


def test_holder_parses_in_the_union_with_default():
    data = load_scenario(SCENARIO_DIR / "soros-baseline.yaml").model_dump(mode="json")
    data["agents"].append(dict(HOLDER))
    cfg = ScenarioConfig.model_validate(data)
    holder = cfg.agents[-1]
    assert isinstance(holder, HolderConfig)
    assert holder.redeem_when_capacity is True
    assert cfg.content_hash() != PRE_HOLDER_HASHES["soros-baseline"]


@pytest.mark.parametrize(
    "bad",
    [
        {"capital": 0},
        {"entry_discount_pct": -0.1},
        {"pace": 0},
        {"pace": 1.01},
        {"redeem_fraction_min": 0.1},  # constructor default, not a config field
    ],
)
def test_holder_field_constraints(bad):
    with pytest.raises(ValidationError):
        HolderConfig.model_validate(HOLDER | bad)


def test_holder_pace_one_and_zero_discount_allowed():
    cfg = HolderConfig.model_validate(HOLDER | {"pace": 1, "entry_discount_pct": 0})
    assert cfg.pace == 1 and cfg.entry_discount_pct == 0


def test_holder_yaml_round_trip(tmp_path):
    data = yaml.safe_load((SCENARIO_DIR / "soros-baseline.yaml").read_text(encoding="utf-8"))
    data["agents"].append(copy.deepcopy(HOLDER) | {"redeem_when_capacity": False})
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_scenario(path).agents[-1].redeem_when_capacity is False
