import pydantic
import pytest

from depeg_sim.experiments.sweep import SweepPathError, set_path
from depeg_sim.kernel.config import load_scenario

BASE = load_scenario("scenarios/soros-baseline.yaml")


def test_nested_attribute():
    new = set_path(BASE, "amm.reserve_stable", 250_000)
    assert new.amm.reserve_stable == 250_000.0
    assert isinstance(new.amm.reserve_stable, float)  # coerced by the model
    assert new.amm.reserve_reference == BASE.amm.reserve_reference
    assert BASE.amm.reserve_stable == 1_000_000.0  # original unchanged
    assert new is not BASE and new.amm is not BASE.amm


def test_list_index():
    new = set_path(BASE, "agents[0].capital", 123.0)
    assert new.agents[0].capital == 123.0
    assert new.agents[1:] == BASE.agents[1:]
    assert BASE.agents[0].capital == 300_000.0


def test_type_selector_picks_first_of_type():
    new = set_path(BASE, "agents[type=defender].budget", 999.0)
    assert new.agents[2].budget == 999.0
    assert new.agents[:2] == BASE.agents[:2]


def test_deep_nested_and_top_level():
    new = set_path(BASE, "termination.peg_recovered.tolerance", 0.01)
    assert new.termination.peg_recovered.tolerance == 0.01
    assert new.termination.peg_recovered.for_steps == 100
    assert set_path(BASE, "seed", 7).seed == 7
    assert set_path(BASE, "name", "x/0001").name == "x/0001"


def test_whole_submodel_from_dict():
    new = set_path(BASE, "termination.peg_recovered", {"for_steps": 5, "tolerance": 0.02})
    assert new.termination.peg_recovered.for_steps == 5


def test_result_is_frozen_and_hash_changes():
    new = set_path(BASE, "amm.fee_bps", 5)
    with pytest.raises(pydantic.ValidationError):
        new.amm.fee_bps = 6
    assert new.content_hash() != BASE.content_hash()
    assert set_path(BASE, "amm.fee_bps", 30).content_hash() == BASE.content_hash()


@pytest.mark.parametrize(
    "path",
    [
        "amm.nope",
        "nope",
        "amm.reserve_stable.deeper",
        "agents[9].capital",
        "agents[type=whale].capital",
        "amm[0].fee_bps",
        "agents[x].capital",
        "agents..capital",
        "agents[0].nope",
    ],
)
def test_unknown_path_raises_naming_it(path):
    with pytest.raises(SweepPathError) as exc:
        set_path(BASE, path, 1)
    assert repr(path) in str(exc.value)


def test_invalid_value_is_a_validation_error():
    with pytest.raises(pydantic.ValidationError):
        set_path(BASE, "amm.fee_bps", 10_000)
    with pytest.raises(pydantic.ValidationError):  # model-level validator re-runs
        set_path(BASE, "agents[1].id", "attacker-1")


# Story 3.3: None on an axis ------------------------------------------------------------


def test_none_sets_an_optional_field_and_restores_the_hash():
    base = load_scenario("scenarios/soros-1992.yaml")
    path = "agents[type=holder].exit_discount_pct"
    on = set_path(base, path, 10)
    assert on.agents[3].exit_discount_pct == 10.0
    assert on.content_hash() != base.content_hash()
    off = set_path(on, path, None)
    assert off.agents[3].exit_discount_pct is None
    assert off.content_hash() == base.content_hash()


def test_none_on_a_required_field_is_rejected():
    with pytest.raises(pydantic.ValidationError):
        set_path(BASE, "agents[type=attacker].capital", None)
