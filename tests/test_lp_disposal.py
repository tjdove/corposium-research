"""Story 5.4: the LP that sells or redeems the stable it withdrew; sweep, table, figure."""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pydantic
import pytest
import yaml
from agent_world import events_of, rules, world

from depeg_sim.agents.lp import LiquidityProvider
from depeg_sim.analysis.charts import plot_lp_flight
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import expand, load_sweep, set_path, sweep_spec_hash
from depeg_sim.kernel.config import LPConfig, ScenarioConfig, load_scenario
from depeg_sim.kernel.interfaces import Action

sys.path.insert(0, str(Path("scripts").resolve()))

import lp_flight_table  # noqa: E402

LP = {"type": "lp", "id": "lp-1", "share": 0.5, "panic_threshold_pct": 5.0, "pace": 0.1}
LP_SCENARIO = Path("scenarios/calibrated-baseline-lp.yaml")
SPEC = Path("sweeps/lp-flight-disposal-mc.yaml")
SPEC_HASH = "e15e1c4adcab2ccc132ea450d0433c16eb9bd4a448e641e0a9142c40efcc1389"
CAP = "agents[type=attacker].capital"
SHARE = "agents[type=lp].share"
MODE = "agents[type=lp].after_withdrawal"


def lp(mode="hold", disposal_pace=0.1, pace=0.1):
    return LiquidityProvider(
        "lp", share=0.5, panic_threshold_pct=5.0, pace=pace, after_withdrawal=mode,
        disposal_pace=disposal_pace,
    )  # fmt: skip


# config and hashes (AC 1) ---------------------------------------------------------------


def test_config_defaults_to_hold_at_pace_0_1():
    cfg = LPConfig.model_validate(LP)
    assert cfg.after_withdrawal == "hold" and cfg.disposal_pace == 0.1


@pytest.mark.parametrize(
    "bad",
    [
        {"after_withdrawal": "dump"},
        {"disposal_pace": 0},
        {"disposal_pace": 1.5},
    ],
)
def test_config_bounds(bad):
    with pytest.raises(pydantic.ValidationError):
        LPConfig.model_validate(LP | bad)


def _with_lp(**fields) -> ScenarioConfig:
    data = load_scenario(LP_SCENARIO).model_dump(mode="json")
    lp_cfg = next(a for a in data["agents"] if a["type"] == "lp")
    lp_cfg.update(fields)
    return ScenarioConfig.model_validate(data)


def test_defaults_written_out_keep_the_hash_and_others_move_it():
    h = load_scenario(LP_SCENARIO).content_hash()
    assert _with_lp(after_withdrawal="hold", disposal_pace=0.1).content_hash() == h
    moved = {
        _with_lp(after_withdrawal="sell").content_hash(),
        _with_lp(after_withdrawal="redeem").content_hash(),
        _with_lp(disposal_pace=0.2).content_hash(),
    }
    assert h not in moved and len(moved) == 3


# Every scenario's content_hash() on main before Story 5.4 (d775a38).
HASHES_5_3 = {
    "calibrated-baseline": "44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a",
    "calibrated-baseline-lp": "4707a65abb67784c2b21d5f178cbc207c4db6ca99d487b861bf13ff6e4b3fe16",
    "calibrated-baseline-ou": "741f1bdd00120fa73f099669178f9bbc362e64ee762b8185abaf5e1dd058946c",
    "calibrated-stress": "17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414",
    "soros-1992": "f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270",
    "soros-1992-no-defense": "516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b",
    "soros-baseline": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023": "2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531",
    "usdc-2023-ou": "77fc93f2f784983b354075a5d09e4417f6e6a9acbd3931457adc54c501921769",
    "usdc-2023-par": "7f3d0c583694faf0e37dc8e04582da02425288f8026a999bdc074a809848c21d",
    "usdc-2023-tranches": "da3383d4e156754f3f16f95808704acc650afb11c3754dcca321347e004a5868",
    "usdc-2023-tranches-ou": "b219b783b6a34363bd4308d3b2a54739829ef44cdde11b3a8dc9c280a385d280",
    "usdc-2023-tranches-par": "32a610a514f2a5bc55a0beda895d7aa9a7cc12f87302e79b8262efa1f9bd3712",
    "usdc-2023-tranches-par-closed": (
        "c2e0f5a7cf5793af48d24e008489986ff70f892a3986f903988bb374253e72f3"
    ),
    "usdc-2023-tranches-par-slow": (
        "90c61264e8c2fb9d06d94fc8d7475438f4e053211df62e3d7ae2a8ce8225b8bb"
    ),
}


def test_every_scenario_is_pinned():
    assert {p.stem for p in Path("scenarios").glob("*.yaml")} == set(HASHES_5_3)


@pytest.mark.parametrize("name", sorted(HASHES_5_3))
def test_existing_scenario_hashes_unchanged(name):
    assert load_scenario(Path("scenarios") / f"{name}.yaml").content_hash() == HASHES_5_3[name]


# agent (AC 2) -----------------------------------------------------------------------------


def _withdraw_then_calm(w, p):
    """Step 1 below the panic price (withdraw 0.05 of the pool), step 2 above it."""
    w.set_spot(0.9)
    w.step(p)
    w.set_spot(0.97)
    return w.step(p)


def test_sell_swaps_disposal_pace_of_the_withdrawn_stable_and_lowers_the_price():
    w = world(fee_bps=30)
    p = lp("sell")
    w.set_spot(0.9)
    w.step(p)
    withdrawn = p.balances["stable"]
    assert withdrawn == pytest.approx(0.05 * 1_000_000)
    w.set_spot(0.97)
    before = w.amm.spot_price
    (act,) = w.step(p)
    assert rules(w, "lp") == ["lp_withdraw", "lp_sell"]
    assert act.target == "amm" and act.kind == "swap"
    assert act.params == {"side": "sell_stable", "amount_in": pytest.approx(0.1 * withdrawn)}
    assert w.amm.spot_price < before
    assert p.balances["stable"] == pytest.approx(0.9 * withdrawn)
    assert p.sold_stable == pytest.approx(0.1 * withdrawn) == withdrawn - p.undisposed_stable
    (sw,) = [e for e in events_of(w, "swap_executed") if e.payload["source"] == "lp"]
    ref = 0.05 * 1_000_000 * 0.9 + sw.payload["amount_out"]
    assert p.balances["reference"] == pytest.approx(ref)  # sale proceeds are held


def test_redeem_queues_disposal_pace_at_the_back_of_the_shared_queue():
    w = world(capacity=25_000.0, spread_bps=10)
    p = lp("redeem")
    w.set_spot(0.9)
    w.step(p)
    withdrawn = p.balances["stable"]
    # another redeemer already in the queue, larger than one step's capacity
    w.redemption.execute(w.ctx, Action("holder", "redemption", "redeem", {"amount_stable": 30e3}))
    w.set_spot(0.97)
    (act,) = w.step(p)
    assert rules(w, "lp") == ["lp_withdraw", "lp_redeem"]
    assert act.target == "redemption" and act.kind == "redeem"
    assert act.params == {"amount_stable": pytest.approx(0.1 * withdrawn)}
    (req,) = [e for e in events_of(w, "redeem_requested") if e.payload["source"] == "lp"]
    assert req.payload["queue_depth"] == 2  # behind the holder: no priority
    assert [e.payload["source"] for e in events_of(w, "redeem_fulfilled")] == ["holder"]
    assert p.queued_redeem == pytest.approx(0.1 * withdrawn) and p.redeemed_stable == 0.0
    assert p.balances["stable"] == pytest.approx(withdrawn)  # queued, still owned
    # next step: the holder's 5k remainder, then the LP's 5k, then its next 4.5k tranche
    w.step(p)
    filled = [e for e in events_of(w, "redeem_fulfilled") if e.payload["source"] == "lp"]
    assert sum(e.payload["amount_stable"] for e in filled) == pytest.approx(0.19 * withdrawn)
    assert p.redeemed_stable == pytest.approx(0.19 * withdrawn)
    assert p.undisposed_stable == pytest.approx(0.81 * withdrawn)
    assert p.balances["reference"] == pytest.approx(
        0.05 * 1_000_000 * 0.9 + 0.19 * withdrawn * (1 - 10 / 10_000)
    )


def test_hold_never_disposes():
    w = world()
    p = lp("hold")
    assert _withdraw_then_calm(w, p) == []
    assert rules(w, "lp") == ["lp_withdraw", "lp_hold"]
    assert p.sold_stable == p.redeemed_stable == 0.0


@pytest.mark.parametrize("mode", ["sell", "redeem"])
def test_withdrawing_comes_first(mode):
    w = world()
    p = lp(mode)
    w.set_spot(0.9)
    for _ in range(3):
        (act,) = w.step(p)
        w.set_spot(0.9)
        assert act.kind == "remove_liquidity"
    assert rules(w, "lp") == ["lp_withdraw"] * 3


def test_disposes_after_the_pool_share_is_gone_then_is_done():
    w = world(fee_bps=0)
    p = lp("sell", disposal_pace=1.0, pace=1.0)
    w.set_spot(0.9)
    w.step(p)  # all its shares in one withdrawal
    assert p.share_remaining == 0.0
    w.set_spot(0.9)
    w.step(p)  # still below the panic price: nothing left to withdraw, so it sells
    w.step(p)
    assert rules(w, "lp") == ["lp_withdraw", "lp_sell", "lp_done"]
    assert p.balances["stable"] == pytest.approx(0.0, abs=1e-6)


def test_redeem_disposal_ends_and_draws_nothing_from_rng():
    # The tranche is a share of its own counter, so it falls below DUST and stops;
    # balances - queued_redeem would keep a residue of a few ulps and requeue it forever.
    w = world(capacity=1e9, reserves=1e9, spread_bps=0)
    p = lp("redeem", disposal_pace=0.5)
    state = w.ctx.rng.bit_generator.state
    _withdraw_then_calm(w, p)
    for _ in range(80):
        w.step(p)
    reqs = [e for e in events_of(w, "redeem_requested") if e.payload["source"] == "lp"]
    assert 40 < len(reqs) < 81 and rules(w, "lp")[-1] == "lp_hold"
    assert p.redeemed_stable == pytest.approx(0.05 * 1_000_000)
    assert w.ctx.rng.bit_generator.state == state


@pytest.mark.parametrize("bad", [{"after_withdrawal": "dump"}, {"disposal_pace": 0.0}])
def test_constructor_bounds(bad):
    with pytest.raises(ValueError):
        LiquidityProvider("lp", share=0.5, panic_threshold_pct=5.0, pace=0.1, **bad)


def test_from_config_carries_the_disposal_fields():
    cfg = LPConfig.model_validate(LP | {"after_withdrawal": "sell", "disposal_pace": 0.3})
    p = LiquidityProvider.from_config(cfg)
    assert p.after_withdrawal == "sell" and p.disposal_pace == 0.3
    assert p.snapshot()["after_withdrawal"] == "sell"
    assert (
        "after_withdrawal"
        not in LiquidityProvider.from_config(LPConfig.model_validate(LP)).snapshot()
    )  # the holding LP's checkpoint is unchanged


# summary columns (AC 3) -------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["hold", "sell"])
def test_summary_counts_what_the_lp_sold(tmp_path, mode):
    cfg = load_scenario(LP_SCENARIO)
    for path, value in [(CAP, 179454391), (MODE, mode), ("steps.max_steps", 400)]:
        cfg = set_path(cfg, path, value)
    art = run_scenario(cfg, output_dir=tmp_path, chart=False)
    s = art.summary
    with open(art.run_dir / "events.jsonl", encoding="utf-8") as f:
        ev = [json.loads(line) for line in f]
    sold = sum(
        e["payload"]["amount_in"]
        for e in ev
        if e["kind"] == "swap_executed" and e["payload"]["source"] == "lp-1"
    )
    assert s["lp_sold_stable"] == pytest.approx(sold)
    assert (sold > 1e6) == (mode == "sell")
    assert s["lp_redeemed_stable"] == 0.0 and isinstance(s["lp_pnl"], float)


# sweep, table, figure (AC 3, 4) -----------------------------------------------------------


def test_spec_hash_is_pinned():
    assert sweep_spec_hash(SPEC) == SPEC_HASH


def test_spec_is_the_flight_grid_without_threshold_plus_disposal():
    spec = yaml.safe_load(SPEC.read_text())
    flight = yaml.safe_load(Path("sweeps/lp-flight-mc.yaml").read_text())
    assert spec["axes"].pop(MODE) == ["hold", "sell", "redeem"]
    del flight["axes"]["agents[type=lp].panic_threshold_pct"]
    assert spec.pop("name") == "lp-flight-disposal-mc"
    flight.pop("name")
    assert spec == flight
    cells = expand(load_sweep(SPEC))
    assert len(cells) == 3 * 3 * 3 * 8 == 216
    assert {c.config.agents[-1].disposal_pace for c in cells} == {0.1}


def _synthetic(d: Path) -> Path:
    """mc.parquet + manifest for the disposal spec: sell deepens the trough, redeem never
    re-enters at the largest attack."""
    d.mkdir()
    base = load_scenario(LP_SCENARIO)
    caps, shares = [89727196, 125618074, 179454391], [0.25, 0.5, 0.75]
    rows = []
    for c in caps:
        for sh in shares:
            for mode in ("hold", "sell", "redeem"):
                never = mode == "redeem" and c == caps[-1]
                rows.append({
                    CAP: c, SHARE: sh, MODE: mode, "n": 8,
                    "p_peg_recovered": 0.0 if never else 1.0,
                    "step_of_max_depeg_std": 0.0, "step_of_max_depeg_p05": 82.0,
                    "step_of_max_depeg_p50": 82.0, "step_of_max_depeg_p95": 82.0,
                    "steps_to_first_band_entry_p50": float("nan") if never else 3000 / sh,
                    "steps_to_first_band_entry_n": 0 if never else 8,
                    "max_depeg_bps_mean": -5000 - 3000 * caps.index(c)
                    - (2000 * sh if mode == "sell" else 0),
                })  # fmt: skip
    pd.DataFrame(rows).to_parquet(d / "mc.parquet", index=False)
    values = ((CAP, caps), (SHARE, shares), (MODE, ["hold", "sell", "redeem"]))
    axes = [{"name": k, "paths": [k], "values": v} for k, v in values]
    m = {
        "sweep_name": "lp-flight-disposal-mc", "base_scenario_hash": base.content_hash(),
        "base_config": base.model_dump(mode="json"), "axes": axes,
        "seeds": list(range(1000, 1008)), "max_steps": 18000,
    }  # fmt: skip
    (d / "manifest.json").write_text(json.dumps(m))
    return d


def test_disposal_png_has_a_column_per_mode(tmp_path):
    png = plot_lp_flight(_synthetic(tmp_path / "s"))
    assert png.name == "lp_flight_disposal.png" and png.stat().st_size > 50_000
    assert plt.imread(png).shape[:2] == (1500, 2700)  # (5.5 x 3 + 1.5) x 10 in at 150 dpi
    assert plt.get_fignums() == []


def test_disposal_table_rows_and_lp_paid_from_events(tmp_path):
    def cell(name, paid):
        d = tmp_path / name
        d.mkdir()
        ev = [{"kind": "redeem_fulfilled", "payload": {"source": "lp-1", "paid_reference": x}}
              for x in paid] + [{"kind": "redeem_fulfilled",
                                 "payload": {"source": "arb", "paid_reference": 9.0}}]  # fmt: skip
        (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev))
        return d

    common = {CAP: 179454391, "seed": 1, "step_of_max_depeg": 300,
              "steps_to_first_band_entry": 600.0, "defender_spent": 2e6,
              "arbitrageur_redeemed": 1e6}  # fmt: skip
    rows = []
    for mode, trough, paid, term in [("hold", -8000.0, [], "peg_recovered"),
                                      ("sell", -8800.0, [], "peg_recovered"),
                                      ("redeem", -8000.0, [1e6, 2e6], "max_steps")]:  # fmt: skip
        rows.append(common | {
            SHARE: 0.5, MODE: mode, "max_depeg_bps": trough, "terminated_by": term,
            "lp_pnl": 1e6, "lp_sold_stable": 3e6 if mode == "sell" else 0.0,
            "lp_redeemed_stable": 3e6 if mode == "redeem" else 0.0, "cell": cell(mode, paid),
        })  # fmt: skip
    nolp = pd.DataFrame([common | {"max_depeg_bps": -7900.0, "terminated_by": "max_steps"}])
    df = lp_flight_table.disposal_table(pd.DataFrame(rows), nolp, 12, 179454391, "lp-1")
    assert df["mode"].tolist() == ["hold", "hold", "sell", "sell", "redeem", "redeem"]
    assert df["share"].tolist() == ["no LP", 0.5] * 3
    by = df[df["share"] == 0.5].set_index("mode")
    assert by.loc["sell", "vs_hold"] == "+10.0%" and by.loc["redeem", "vs_hold"] == "+0.0%"
    assert by.loc["redeem", "lp_paid_M"] == 3.0 and by.loc["sell", "lp_sold_M"] == 3.0
    assert by.loc["redeem", "recovered"] == "0/1" and by.loc["hold", "hours"] == "3.0"
