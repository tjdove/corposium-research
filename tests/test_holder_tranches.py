"""Story 3.7 AC 1, 2: the multi-tranche holder (a ladder of entry prices)."""

import json
from pathlib import Path

import pytest
from agent_world import decisions, events_of, rules, world
from pydantic import ValidationError

from depeg_sim.agents.arbitrageur import _reference_to_reach
from depeg_sim.agents.factory import build_agents
from depeg_sim.agents.holder import Holder
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import set_path
from depeg_sim.kernel.config import HolderConfig, ScenarioConfig, load_scenario

SCENARIO_DIR = Path("scenarios")
USDC = SCENARIO_DIR / "usdc-2023.yaml"

# content_hash() of every scenario at main before Story 3.7 (d97e51b): the tranche schema
# moves none of them.
HASHES_BEFORE_3_7 = {
    "calibrated-baseline-ou": "741f1bdd00120fa73f099669178f9bbc362e64ee762b8185abaf5e1dd058946c",
    "calibrated-baseline": "44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a",
    "calibrated-stress": "17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414",
    "soros-1992-no-defense": "516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b",
    "soros-1992": "f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270",
    "soros-baseline": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023": "2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531",
}

LADDER = [(1.0, 0.5), (2.0, 0.3), (5.0, 0.2)]  # ladder A of the story
BASE = {"type": "holder", "id": "holder-1", "capital": 1_000_000, "pace": 0.05}


def tranches(ladder=LADDER):
    return [{"entry_discount_pct": d, "share": s} for d, s in ladder]


def laddered(capital=100_000.0, ladder=LADDER, pace=0.05, redeem=False, **kw):
    return Holder(
        "h",
        capital=capital,
        entry_discount_pct=None,
        pace=pace,
        redeem_when_capacity=redeem,
        tranches=ladder,
        **kw,
    )


# config ----------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(HASHES_BEFORE_3_7))
def test_every_existing_scenario_hash_unchanged(name):
    assert load_scenario(SCENARIO_DIR / f"{name}.yaml").content_hash() == HASHES_BEFORE_3_7[name]


def test_tranches_parse_and_default_to_none():
    assert HolderConfig.model_validate(BASE | {"entry_discount_pct": 2.0}).tranches is None
    cfg = HolderConfig.model_validate(BASE | {"tranches": tranches()})
    assert [(t.entry_discount_pct, t.share) for t in cfg.tranches] == LADDER
    assert cfg.entry_discount_pct is None


def test_entry_discount_must_be_absent_with_tranches():
    with pytest.raises(ValidationError, match="entry_discount_pct must be absent"):
        HolderConfig.model_validate(BASE | {"entry_discount_pct": 2.0, "tranches": tranches()})


def test_one_entry_form_is_required():
    with pytest.raises(ValidationError, match="set entry_discount_pct or tranches"):
        HolderConfig.model_validate(BASE)


@pytest.mark.parametrize(
    "ladder",
    [[(1.0, 0.5), (2.0, 0.3)], [(1.0, 0.5), (2.0, 0.6)], [(1.0, 0.5), (2.0, 0.5 + 2e-9)]],
)
def test_shares_must_sum_to_one(ladder):
    with pytest.raises(ValidationError, match="must sum to 1"):
        HolderConfig.model_validate(BASE | {"tranches": tranches(ladder)})


def test_shares_within_tolerance_allowed():
    ladder = [(1.0, 0.5), (2.0, 0.5 + 1e-12)]
    assert sum(s for _, s in ladder) != 1.0
    assert HolderConfig.model_validate(BASE | {"tranches": tranches(ladder)}).tranches


@pytest.mark.parametrize("ladder", [[(2.0, 0.5), (1.0, 0.5)], [(2.0, 0.5), (2.0, 0.5)]])
def test_entry_discounts_strictly_increasing(ladder):
    with pytest.raises(ValidationError, match="strictly increasing"):
        HolderConfig.model_validate(BASE | {"tranches": tranches(ladder)})


@pytest.mark.parametrize(
    "bad",
    [
        [{"entry_discount_pct": -1.0, "share": 1.0}],
        [{"entry_discount_pct": 1.0, "share": 0.0}],
        [{"entry_discount_pct": 1.0, "share": 1.5}],
        [{"entry_discount_pct": 1.0, "share": 1.0, "x": 1}],
        [],
    ],
)
def test_tranche_field_constraints(bad):
    with pytest.raises(ValidationError):
        HolderConfig.model_validate(BASE | {"tranches": bad})


def test_exit_must_exceed_the_deepest_tranche():
    with pytest.raises(ValidationError, match="deepest tranche"):
        HolderConfig.model_validate(BASE | {"tranches": tranches(), "exit_discount_pct": 4.0})
    cfg = HolderConfig.model_validate(BASE | {"tranches": tranches(), "exit_discount_pct": 6.0})
    assert cfg.exit_discount_pct == 6.0


def _usdc_with_holder(**holder) -> ScenarioConfig:
    data = load_scenario(USDC).model_dump(mode="json")
    (h,) = [a for a in data["agents"] if a["type"] == "holder"]
    h.update(holder)
    return ScenarioConfig.model_validate(data)


def test_tranches_enter_the_hash_and_replace_entry_discount():
    single = _usdc_with_holder(entry_discount_pct=None, tranches=tranches([(2.0, 1.0)]))
    other = _usdc_with_holder(entry_discount_pct=None, tranches=tranches([(3.0, 1.0)]))
    assert len({single.content_hash(), other.content_hash(), HASHES_BEFORE_3_7["usdc-2023"]}) == 3


# construction ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {"entry_discount_pct": 2.0, "tranches": LADDER},
        {"entry_discount_pct": None, "tranches": None},
        {"entry_discount_pct": None, "tranches": []},
        {"entry_discount_pct": None, "tranches": [(1.0, 0.5), (2.0, 0.4)]},
        {"entry_discount_pct": None, "tranches": [(2.0, 0.5), (1.0, 0.5)]},
        {"entry_discount_pct": None, "tranches": [(1.0, 0.0), (2.0, 1.0)]},
        {"entry_discount_pct": None, "tranches": LADDER, "exit_discount_pct": 4.0},
    ],
)
def test_construction_guards(kw):
    with pytest.raises(ValueError):
        Holder("h", capital=100.0, pace=0.05, **kw)


def test_from_config_and_books():
    data = load_scenario(SCENARIO_DIR / "soros-baseline.yaml").model_dump(mode="json")
    data["agents"].append(BASE | {"tranches": tranches()})
    (h,) = [a for a in build_agents(ScenarioConfig.model_validate(data)) if a.type == "holder"]
    assert h.laddered and h.tranche_discounts == [1.0, 2.0, 5.0]
    assert h.tranche_reference == [500_000.0, 300_000.0, 200_000.0]
    assert h.entry_price == pytest.approx(0.99)  # it starts buying at the shallowest entry
    assert h.tranche_entry_prices == pytest.approx([0.99, 0.98, 0.95])


# buy rule --------------------------------------------------------------------------------


def _buys(w, acts):
    """``{tranche: amount_in}`` from this step's actions and the last decision record."""
    rec = decisions(w, "h")[-1].action
    recs = rec["actions"] if "actions" in rec else [rec]
    assert [r["params"] for r in recs] == [a.params for a in acts]
    return {r["tranche"]: r["params"]["amount_in"] for r in recs}


def test_price_steps_down_through_each_entry():
    w = world(fee_bps=1)
    h = laddered()
    w.set_spot(0.995)  # above every entry
    assert w.step(h) == []
    w.set_spot(0.98)  # below 0.99 only (strictly below is required)
    got = _buys(w, w.step(h))
    assert got == {0: pytest.approx(0.05 * 50_000.0)}
    w.set_spot(0.97)  # below 0.99 and 0.98
    got = _buys(w, w.step(h))
    assert set(got) == {0, 1}
    assert got[1] == pytest.approx(0.05 * 30_000.0)  # its own share, untouched so far
    assert got[0] == pytest.approx(0.05 * (50_000.0 - 2_500.0))  # its own remaining share
    w.set_spot(0.90)  # below every entry
    acts = w.step(h)
    got = _buys(w, acts)
    assert list(got) == [2, 1, 0]  # deepest entry first
    assert got[2] == pytest.approx(0.05 * 20_000.0)
    assert rules(w, "h") == ["hold_done", "hold_buy", "hold_buy", "hold_buy"]
    # pooled balances are the sum of the books; each tranche spent only its own share
    assert sum(h.tranche_reference) == pytest.approx(h.balances["reference"])
    assert sum(h.tranche_stable) == pytest.approx(h.balances["stable"])
    assert h.tranche_spent[2] == pytest.approx(1_000.0)
    for ref, spent, share in zip(
        h.tranche_reference, h.tranche_spent, (0.5, 0.3, 0.2), strict=True
    ):
        assert ref + spent == pytest.approx(100_000.0 * share)


def test_each_tranche_caps_at_its_own_entry():
    w = world(fee_bps=0)
    h = laddered(capital=10_000_000.0, pace=1.0)  # pace never binds: every buy is a cap
    w.set_spot(0.90)
    r0, k = w.amm.reserve_reference, w.amm.k
    got = _buys(w, w.step(h))
    cap5 = _reference_to_reach(k, r0, 0.95)
    cap2 = _reference_to_reach(k, r0 + cap5, 0.98)
    cap1 = _reference_to_reach(k, r0 + cap5 + cap2, 0.99)
    assert got == {2: pytest.approx(cap5), 1: pytest.approx(cap2), 0: pytest.approx(cap1)}
    assert w.amm.spot_price == pytest.approx(0.99)  # no fee: lands on the shallowest entry
    w.set_spot(0.97)  # below 0.99 and 0.98 only: the 5% tranche does not buy
    assert set(_buys(w, w.step(h))) == {1, 0}
    assert w.amm.spot_price <= 0.99 + 1e-12


def test_a_capped_deep_tranche_does_not_stop_shallower_ones():
    w = world(fee_bps=1)
    h = laddered(pace=1.0)
    w.set_spot(0.9499)  # just below 0.95: the 5% tranche's cap is tiny
    got = _buys(w, w.step(h))
    assert got[2] < 100.0 and got[1] > 0 and got[0] > 0


def test_single_tranche_records_no_tranche_key():
    w = world()
    h = laddered(ladder=[(2.0, 1.0)])
    assert not h.laddered
    w.set_spot(0.95)
    (act,) = w.step(h)
    assert decisions(w, "h")[-1].action == {
        "target": "amm",
        "kind": "swap",
        "params": act.params,
    }
    assert "tranches" not in h.snapshot()


# redeem / exit on the pooled stable --------------------------------------------------------


def test_redemption_pays_back_pro_rata_to_tranche_stable():
    w = world(fee_bps=1, capacity=1_000_000.0, spread_bps=0)
    h = laddered(redeem=True)
    w.set_spot(0.90)
    w.step(h)  # all three buy
    stable_before = list(h.tranche_stable)
    w.set_spot(1.0)
    (act,) = w.step(h)  # nothing to buy: redeems the pooled stable
    assert act.kind == "redeem"
    assert act.params["amount_stable"] == pytest.approx(sum(stable_before))
    (paid,) = events_of(w, "redeem_fulfilled")
    total = sum(stable_before)
    for i, st in enumerate(stable_before):
        assert h.tranche_reference[i] + h.tranche_spent[i] == pytest.approx(
            100_000.0 * LADDER[i][1] + paid.payload["paid_reference"] * st / total
        )
    assert h.tranche_stable == pytest.approx([0.0, 0.0, 0.0])
    assert sum(h.tranche_reference) == pytest.approx(h.balances["reference"])


def test_exit_sells_the_pooled_stable_and_credits_pro_rata():
    w = world(fee_bps=1)
    h = laddered(exit_discount_pct=10.0)
    w.set_spot(0.94)
    w.step(h)
    stable_before = list(h.tranche_stable)
    w.set_spot(0.85)
    (act,) = w.step(h)
    assert rules(w, "h")[-1] == "hold_exit" and act.params["side"] == "sell_stable"
    assert act.params["amount_in"] == pytest.approx(sum(stable_before))
    assert h.tranche_stable == pytest.approx([0.0, 0.0, 0.0])
    assert sum(h.tranche_reference) == pytest.approx(h.balances["reference"])
    assert h.snapshot()["tranches"][2]["spent_reference"] == pytest.approx(h.tranche_spent[2])


def test_never_draws_from_rng():
    w = world(fee_bps=1, capacity=1_000_000.0)
    h = laddered(redeem=True)
    before = w.ctx.rng.bit_generator.state
    for price in (0.9, 0.97, 1.0, 1.0):
        w.set_spot(price)
        w.step(h)
    assert w.ctx.rng.bit_generator.state == before


# AC 2: a single tranche at share 1 is the scalar form, byte for byte ---------------------


def _files(run_dir: Path) -> dict[str, bytes]:
    """Every run file but the manifest and summary (they carry the config and its hash),
    with ``events.jsonl``'s first line (``run_started``, which carries the hash) dropped."""
    skip = {"manifest.json", "summary.json"}
    files = {
        p.relative_to(run_dir).as_posix(): p.read_bytes()
        for p in sorted(run_dir.rglob("*"))
        if p.is_file() and p.name not in skip
    }
    first, rest = files["events.jsonl"].split(b"\n", 1)
    assert b'"run_started"' in first and b"scenario_hash" in first
    files["events.jsonl"] = rest
    return files


def test_single_tranche_is_byte_identical_to_the_scalar_form_on_the_replay(tmp_path):
    scalar = load_scenario(USDC)
    single = _usdc_with_holder(entry_discount_pct=None, tranches=tranches([(2.0, 1.0)]))
    assert single.content_hash() != scalar.content_hash()
    a = run_scenario(scalar, output_dir=tmp_path / "a", chart=False)
    b = run_scenario(single, output_dir=tmp_path / "b", chart=False)
    fa, fb = _files(a.run_dir), _files(b.run_dir)
    assert "timeseries.parquet" in fa and any(k.startswith("checkpoints") for k in fa)
    assert fa == fb  # timeseries, events, checkpoints
    sa = json.loads((a.run_dir / "summary.json").read_text())
    sb = json.loads((b.run_dir / "summary.json").read_text())
    assert sa.pop("scenario_hash") != sb.pop("scenario_hash")
    assert sa == sb  # everything but the hash of the (differently written) config
    assert sa["max_depeg_bps"] == pytest.approx(-1137.8, abs=0.05)


def test_single_tranche_byte_identical_with_trace_on_a_short_window(tmp_path):
    def short(cfg):
        cfg = set_path(cfg, "steps.max_steps", 9_000)
        return set_path(cfg, "metrics.trace_decisions", True)

    scalar = short(load_scenario(USDC))
    single = short(_usdc_with_holder(entry_discount_pct=None, tranches=tranches([(2.0, 1.0)])))
    a = run_scenario(scalar, output_dir=tmp_path / "a", chart=False)
    b = run_scenario(single, output_dir=tmp_path / "b", chart=False)
    fa, fb = _files(a.run_dir), _files(b.run_dir)
    assert "decisions.jsonl" in fa and b"hold_buy" in fa["decisions.jsonl"]
    assert fa == fb


# AC 5: the best ladder as its own replay scenario -----------------------------------------

TRANCHES_SCENARIO = SCENARIO_DIR / "usdc-2023-tranches.yaml"
LADDER_B = [(2.0, 0.25), (5.0, 0.25), (10.0, 0.25), (20.0, 0.25)]
C_STAR_B = 10_833_333  # scripts/fit_holder.py --tranches 2:0.25,5:0.25,10:0.25,20:0.25


def test_every_scenario_but_the_new_one_is_pinned_above():
    found = {p.stem for p in SCENARIO_DIR.glob("*.yaml")}
    assert found - set(HASHES_BEFORE_3_7) == {"usdc-2023-tranches"}


def test_tranches_scenario_is_the_replay_with_ladder_b():
    cfg = load_scenario(TRANCHES_SCENARIO)
    assert cfg.content_hash() == (
        "da3383d4e156754f3f16f95808704acc650afb11c3754dcca321347e004a5868"
    )
    (hold,) = [a for a in cfg.agents if a.type == "holder"]
    assert hold.capital == C_STAR_B and hold.entry_discount_pct is None
    assert [(t.entry_discount_pct, t.share) for t in hold.tranches] == LADDER_B
    assert (hold.pace, hold.redeem_when_capacity, hold.exit_discount_pct) == (0.05, True, None)
    # everything else is the replay's own
    replay = load_scenario(USDC).model_dump(mode="json")
    mine = cfg.model_dump(mode="json")
    for data in (replay, mine):
        del data["name"]
        data["agents"] = [a for a in data["agents"] if a["type"] != "holder"]
    assert mine == replay
