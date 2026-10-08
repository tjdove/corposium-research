"""Story 2.8: ``peg_recovered.reference`` (par | oracle), ReferenceView, summary metrics."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from kernel_stubs import PegStub, ScriptedPriceSource, make_config
from test_metrics import cfg_with, run

from depeg_sim.analysis.summary import summarize
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.kernel import termination
from depeg_sim.kernel.config import ScenarioConfig, load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import PegView, ReferenceView, Subsystem
from depeg_sim.kernel.scheduler import Phase
from depeg_sim.protocol.oracle import Oracle


def term(reference, for_steps=3, tolerance=0.001):
    return {
        "reserves_exhausted": False,
        "peg_recovered": {"for_steps": for_steps, "tolerance": tolerance, "reference": reference},
        "max_steps": True,
    }


class RefStub(Subsystem):
    """ReferenceView with a settable published price."""

    def __init__(self, published=None, name="ref"):
        self.name = name
        self.phases = frozenset({Phase.ORACLE_UPDATE})
        self.published = published

    def on_phase(self, ctx, phase):
        pass

    @property
    def published_price(self):
        return self.published


class TrackingAMM(Subsystem):
    """PegView whose spot equals a price source's current price (an AMM that tracks the
    market perfectly); peg 1.0."""

    def __init__(self, source, name="amm"):
        self.name = name
        self.phases = frozenset({Phase.METRIC_UPDATE})
        self.source = source

    def on_phase(self, ctx, phase):
        pass

    @property
    def spot_price(self):
        return self.source.price

    @property
    def peg_deviation(self):
        return self.spot_price - 1.0


def check_once(ctx):
    return termination.check(ctx), ctx.term_state.consecutive_in_band


# -- config and hashes ----------------------------------------------------------------

BEFORE_2_8 = {  # content_hash of every scenario at b29c7c0, before the field existed
    "calibrated-baseline.yaml": "44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a",
    "calibrated-stress.yaml": "17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414",
    "soros-1992-no-defense.yaml": (
        "516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b"
    ),
    "soros-1992.yaml": "f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270",
    "soros-baseline.yaml": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile.yaml": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023.yaml": "2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531",
}


def test_every_scenario_hash_unchanged():
    later = {  # pinned where they were added
        "calibrated-baseline-ou.yaml",  # Story 3.6, test_calibrated_scenarios.py
        "usdc-2023-tranches.yaml",  # Story 3.7, test_holder_tranches.py
        "calibrated-baseline-lp.yaml",  # Story 3.8, test_lp.py
    }
    found = {
        p.name: load_scenario(p).content_hash()
        for p in Path("scenarios").glob("*.yaml")
        if p.name not in later
    }
    assert found == BEFORE_2_8
    assert load_scenario(Path("scenarios/usdc-2023.yaml")).content_hash()[:12] == "2c3aeaa9825d"


def test_reference_defaults_to_par_and_oracle_changes_the_hash():
    cfg = load_scenario(Path("scenarios/calibrated-baseline.yaml"))
    assert cfg.termination.peg_recovered.reference == "par"
    data = cfg.model_dump(mode="json")
    assert data["termination"]["peg_recovered"]["reference"] == "par"  # manifest records it
    data["termination"]["peg_recovered"]["reference"] = "oracle"
    oracle_cfg = ScenarioConfig.model_validate(data)
    assert oracle_cfg.content_hash() != cfg.content_hash()
    data["termination"]["peg_recovered"]["reference"] = "spot"
    with pytest.raises(ValueError):
        ScenarioConfig.model_validate(data)


# -- views ----------------------------------------------------------------------------


def test_oracle_is_reference_view_not_peg_view():
    src = ScriptedPriceSource([1.0, 1.2])
    oracle = Oracle(heartbeat_steps=25, deviation_threshold_pct=0.5, source=src)
    assert isinstance(oracle, ReferenceView)
    assert not isinstance(oracle, PegView)  # ADR-0007 unchanged
    assert oracle.published_price is None  # before the first publish
    src.price = 1.2
    assert oracle.reference_price == 1.2  # Story 1.5 pass-through unchanged


def test_amm_is_peg_view_with_spot_not_reference_view():
    from depeg_sim.protocol.amm import ConstantProductAMM

    amm = ConstantProductAMM(reserve_stable=1_000, reserve_reference=1_005, fee_bps=30)
    assert isinstance(amm, PegView) and not isinstance(amm, ReferenceView)
    assert amm.spot_price == pytest.approx(1.005)


# -- termination.check ----------------------------------------------------------------


def test_unpublished_oracle_is_out_of_band():
    ctx = RunContext.from_config(make_config(max_steps=100, termination=term("oracle")))
    ctx.registry.register(PegStub([0.0]))  # spot exactly 1.0
    ref = RefStub(published=None)
    ctx.registry.register(ref)
    for _ in range(5):
        assert check_once(ctx) == (None, 0)
    ref.published = 1.0
    assert check_once(ctx) == (None, 1)


def test_oracle_criterion_without_reference_view_is_out_of_band():
    ctx = RunContext.from_config(make_config(max_steps=100, termination=term("oracle")))
    ctx.registry.register(PegStub([0.0]))
    assert check_once(ctx) == (None, 0)


@pytest.mark.parametrize(("reference", "counted"), [("par", 0), ("oracle", 1)])
def test_spot_and_oracle_both_at_1005(reference, counted):
    ctx = RunContext.from_config(make_config(max_steps=100, termination=term(reference)))
    ctx.registry.register(PegStub([0.005]))  # spot 1.005: 50 bps off par
    ctx.registry.register(RefStub(published=1.005))
    assert check_once(ctx) == (None, counted)


@pytest.mark.parametrize(
    ("reference", "ended"), [("par", "max_steps"), ("oracle", "peg_recovered")]
)
def test_reference_drifts_50_bps_and_amm_tracks_it(reference, ended):
    # The reference walks from 1.000 to 1.005 over 50 steps and stays; a real Oracle
    # (zero threshold: publishes every step) follows it; the AMM tracks it exactly.
    prices = [1.0 + 0.005 * min(s, 50) / 50 for s in range(400)]
    ctx = RunContext.from_config(
        make_config(max_steps=400, termination=term(reference, for_steps=100, tolerance=0.001))
    )
    src = ScriptedPriceSource(prices)
    oracle = Oracle(heartbeat_steps=25, deviation_threshold_pct=0.0, source=src)
    for sub in (src, oracle, TrackingAMM(src)):
        ctx.registry.register(sub)
    result = Engine(ctx).run()
    assert result.terminated_by == ended
    if reference == "oracle":
        assert result.steps_run == 100  # in band against the oracle from step 0
    else:
        assert result.steps_run == 400


# -- summary --------------------------------------------------------------------------


def oracle_cfg(base):
    data = base.model_dump(mode="json")
    data["termination"]["peg_recovered"]["reference"] = "oracle"
    return ScenarioConfig.model_validate(data)


def test_summary_band_entry_follows_the_criterion():
    cfg = cfg_with(max_steps=60)  # tolerance 60 bps
    _, world, result, _ = run(cfg)
    # trough at step 1; the AMM sits +100 bps off par from step 2 on, tracking an oracle
    # that is +100 bps too; the oracle is unpublished at step 2.
    df = pd.DataFrame(
        {
            "step": [0, 1, 2, 3, 4],
            "peg_deviation": [0.0, -0.05, 0.01, 0.01, 0.01],
            "amm_price": [1.0, 0.95, 1.01, 1.01, 1.01],
            "oracle_price": [1.0, 1.0, float("nan"), 1.01, 1.01],
        }
    )
    par = summarize(cfg, result, df, world)
    ora = summarize(oracle_cfg(cfg), result, df, world)
    assert par["steps_to_first_band_entry"] is None  # 100 bps off par throughout
    assert ora["steps_to_first_band_entry"] == 2  # step 3: first published in-band step
    assert par["max_depeg_bps"] == ora["max_depeg_bps"] == pytest.approx(-500.0)


def test_flat_reference_oracle_equals_par(tmp_path):
    # soros-baseline has zero volatility: the oracle publishes 1.0 forever, so the two
    # criteria agree step for step and the run ends identically.
    base = load_scenario(Path("scenarios/soros-baseline.yaml"))
    a = run_scenario(base, output_dir=tmp_path / "par", chart=False).summary
    b = run_scenario(oracle_cfg(base), output_dir=tmp_path / "oracle", chart=False).summary
    for k in ("terminated_by", "steps_run", "steps_to_first_band_entry"):
        assert a[k] == b[k], k
    assert a["steps_to_sustained_recovery"] == b["steps_to_sustained_recovery"] == 42


def test_soros_baseline_summary_bytes_unchanged(tmp_path):
    # summary.json sha256 re-captured in Story 3.8 (two new keys, pool_depth_at_trough and
    # pool_liquidity_at_trough); without those lines it is the Story 3.5 capture (one new
    # key, arbitrageur_redeemed), and without that line the bytes captured at b29c7c0,
    # before Story 2.8.
    art = run_scenario(
        load_scenario(Path("scenarios/soros-baseline.yaml")), output_dir=tmp_path, chart=False
    )
    raw = (art.run_dir / "summary.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "be7d32669a8fe6e2efb933bfca6ed213240b9eb85c26a2ee7aef4bea6cdc2fa9"
    )
    lines = raw.splitlines(keepends=True)
    pool = [ln for ln in lines if ln.startswith((b'  "pool_depth_at', b'  "pool_liquidity_at'))]
    assert len(pool) == 2
    lines = [ln for ln in lines if ln not in pool]
    assert hashlib.sha256(b"".join(lines)).hexdigest() == (
        "f2428bdb6b6fc52188e7761f9170fbddda5cb501a74849e7c7f1284e73677865"
    )
    added = [ln for ln in lines if b'"arbitrageur_redeemed"' in ln]
    assert len(added) == 1
    before = b"".join(ln for ln in lines if ln not in added)
    assert hashlib.sha256(before).hexdigest() == (
        "ae9578ad45a35fe6986537a344d20746451d2ac74bd5a8ae331816f89fd77704"
    )
    json.loads((art.run_dir / "summary.json").read_text())
