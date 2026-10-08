"""Story 2.6 AC 2: ``HolderConfig`` joins the agent union without moving any hash."""

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from depeg_sim.kernel.config import HolderConfig, ScenarioConfig, load_scenario

SCENARIO_DIR = Path("scenarios")
# Scenarios added after these snapshots, each pinned where it was added.
ADDED_LATER = {
    "calibrated-baseline-ou",  # Story 3.6: tests/test_calibrated_scenarios.py
    "usdc-2023-tranches",  # Story 3.7: tests/test_holder_tranches.py
}

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
    found = {p.stem for p in SCENARIO_DIR.glob("*.yaml")} - ADDED_LATER
    assert sorted(found) == sorted(PRE_HOLDER_HASHES)


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
        {"redeem_horizon_steps": 10},  # constructor default, not a config field
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


C_STAR = 9_166_667  # scripts/fit_holder.py on usdc-2023 (Story 2.6)
D_STAR = 16_666_667
WITH_HOLDER = [
    "usdc-2023",
    "calibrated-baseline",
    "calibrated-stress",
    "soros-1992",
    "soros-1992-no-defense",
]


@pytest.mark.parametrize("name", WITH_HOLDER)
def test_holder_at_the_replay_capital_to_depth_ratio(name):
    cfg = load_scenario(SCENARIO_DIR / f"{name}.yaml")
    (holder,) = [a for a in cfg.agents if a.type == "holder"]
    assert holder.capital == round(C_STAR * cfg.amm.reserve_stable / D_STAR)
    assert (holder.entry_discount_pct, holder.pace, holder.redeem_when_capacity) == (
        2.0,
        0.05,
        True,
    )


@pytest.mark.parametrize("name", ["soros-baseline", "soros-volatile"])
def test_soros_baselines_have_no_holder(name):
    cfg = load_scenario(SCENARIO_DIR / f"{name}.yaml")
    assert [a.type for a in cfg.agents] == ["attacker", "arbitrageur", "defender"]


# Story 3.1: the fill-price limit is a behaviour change only; no scenario hash moves until
# the re-fitted C* is written into the holder scenarios.
HASHES_3_1 = {
    "calibrated-baseline": "44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a",
    "calibrated-stress": "17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414",
    "soros-1992-no-defense": "516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b",
    "soros-1992": "f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270",
    "soros-baseline": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023": "2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531",
}


def test_every_scenario_hash_is_pinned_for_3_1():
    assert {p.stem for p in SCENARIO_DIR.glob("*.yaml")} - ADDED_LATER == set(HASHES_3_1)
    for name, h in HASHES_3_1.items():
        assert load_scenario(SCENARIO_DIR / f"{name}.yaml").content_hash() == h, name


# Story 3.3: exit rule ------------------------------------------------------------------


def test_exit_discount_defaults_to_none():
    assert HolderConfig.model_validate(HOLDER).exit_discount_pct is None


@pytest.mark.parametrize("bad", [0, -1, 100, 150])
def test_exit_discount_bounds(bad):
    with pytest.raises(ValidationError):
        HolderConfig.model_validate(HOLDER | {"exit_discount_pct": bad})


@pytest.mark.parametrize("exit_", [1.0, 2.0])
def test_exit_must_exceed_entry(exit_):
    with pytest.raises(ValidationError, match="must exceed entry_discount_pct"):
        HolderConfig.model_validate(HOLDER | {"exit_discount_pct": exit_})


def test_exit_above_entry_allowed():
    assert HolderConfig.model_validate(HOLDER | {"exit_discount_pct": 2.5}).exit_discount_pct == 2.5


def test_exit_none_leaves_the_hash_and_a_set_exit_moves_it(tmp_path):
    data = yaml.safe_load((SCENARIO_DIR / "soros-1992.yaml").read_text(encoding="utf-8"))
    (holder,) = [a for a in data["agents"] if a["type"] == "holder"]
    path = tmp_path / "s.yaml"
    holder["exit_discount_pct"] = None
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_scenario(path).content_hash() == HASHES_3_1["soros-1992"]
    holder["exit_discount_pct"] = 10.0
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_scenario(path).content_hash() != HASHES_3_1["soros-1992"]
