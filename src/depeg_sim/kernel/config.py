"""Scenario configuration: the contract between research design and execution.

One YAML file fully describes one run. These models are data only; the kernel,
protocol and agent modules implement against them. All models are strict
(unknown fields rejected) and frozen (a loaded config cannot change mid-run).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StepsConfig(StrictModel):
    interval_seconds: int = Field(default=12, gt=0)
    max_steps: int = Field(gt=0)


class AssetConfig(StrictModel):
    symbol: str
    decimals: int = Field(default=18, ge=0, le=18)


class AMMConfig(StrictModel):
    reserve_stable: float = Field(gt=0)
    reserve_reference: float = Field(gt=0)
    fee_bps: int = Field(ge=0, lt=10_000)


class OracleConfig(StrictModel):
    heartbeat_steps: int = Field(gt=0)
    deviation_threshold_pct: float = Field(ge=0)


class CapacityChange(StrictModel):
    """From ``step`` on, redemption capacity is ``capacity_per_step`` (Story 2.5)."""

    step: int = Field(ge=0)
    capacity_per_step: float = Field(gt=0)


class RedemptionConfig(StrictModel):
    reserves: float = Field(ge=0)
    spread_bps: int = Field(ge=0, lt=10_000)
    capacity_per_step: float = Field(gt=0)
    peg_price: float = Field(default=1.0, gt=0)
    capacity_schedule: list[CapacityChange] = Field(default_factory=list)

    @model_validator(mode="after")
    def _schedule_ascending(self) -> RedemptionConfig:
        steps = [c.step for c in self.capacity_schedule]
        if any(b <= a for a, b in zip(steps, steps[1:], strict=False)):
            raise ValueError(
                f"redemption.capacity_schedule steps must be strictly ascending: {steps}"
            )
        return self


class ShockEvent(StrictModel):
    step: int = Field(ge=0)
    pct: float  # +/- percent applied to the reference price


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EnvironmentConfig(StrictModel):
    base_price: float = Field(default=1.0, gt=0)
    volatility_per_step: float = Field(default=0.0, ge=0)
    shocks: list[ShockEvent] = Field(default_factory=list)
    # Observed reference series (Story 2.5): a CSV with ``unix, close`` columns. A relative
    # path resolves against the scenario file's directory (``load_scenario`` passes it as
    # validation context ``base_dir``; without one, the working directory). Stored resolved.
    price_series_path: Path | None = None
    _price_series_sha256: str | None = PrivateAttr(default=None)

    @field_validator("price_series_path")
    @classmethod
    def _resolve(cls, v: Path | None, info: ValidationInfo) -> Path | None:
        if v is None:
            return None
        base = (info.context or {}).get("base_dir", Path.cwd())
        return v if v.is_absolute() else (Path(base) / v).resolve()

    @model_validator(mode="after")
    def _series_is_the_environment(self) -> EnvironmentConfig:
        if self.price_series_path is None:
            return self
        if self.volatility_per_step != 0 or self.shocks:
            raise ValueError(
                "environment.price_series_path is set, so volatility_per_step must be 0 and "
                "shocks must be empty: the observed series is the whole environment"
            )
        if not self.price_series_path.is_file():
            raise ValueError(f"environment.price_series_path not found: {self.price_series_path}")
        self._price_series_sha256 = _sha256(self.price_series_path)
        return self

    @property
    def price_series_sha256(self) -> str | None:
        """sha256 of the series file as read at load time; ``None`` without a series."""
        return self._price_series_sha256


class PegRecoveredConfig(StrictModel):
    """``reference`` picks what "in band" is measured against (Story 2.8): ``par`` (the
    default) uses the AMM's ``peg_deviation``; ``oracle`` uses ``spot / published oracle
    price - 1``, so a venue that tracks a wandering market price counts as recovered."""

    for_steps: int = Field(gt=0)
    tolerance: float = Field(gt=0)  # fraction, e.g. 0.001
    reference: Literal["par", "oracle"] = "par"


class TerminationConfig(StrictModel):
    reserves_exhausted: bool = True
    peg_recovered: PegRecoveredConfig | None = None
    max_steps: bool = True

    @model_validator(mode="after")
    def _max_steps_mandatory(self) -> TerminationConfig:
        if not self.max_steps:
            raise ValueError(
                "termination.max_steps must be true: steps.max_steps is the mandatory "
                "safety cap on every run"
            )
        return self


class MetricsConfig(StrictModel):
    record_every: int = Field(default=1, gt=0)
    trace_decisions: bool = False
    checkpoint_every: int | None = Field(default=None, gt=0)


class AttackerConfig(StrictModel):
    type: Literal["attacker"]
    id: str
    capital: float = Field(gt=0)
    start_step: int = Field(ge=0)
    pace: float = Field(gt=0, le=1)
    stop_below_price: float | None = None


class ArbitrageurConfig(StrictModel):
    type: Literal["arbitrageur"]
    id: str
    capital: float = Field(gt=0)
    min_profit_bps: int = Field(ge=0)
    latency_steps: int = Field(default=0, ge=0)


class DefenderConfig(StrictModel):
    """``buy: false`` (Story 3.2) is a defender that never buys on the AMM and may still
    widen the redemption spread (the "spread-only" policy). ``max_spread_bps`` caps the
    widened spread; ``None`` keeps the agent's ``MAX_SPREAD_BPS``."""

    type: Literal["defender"]
    id: str
    budget: float = Field(gt=0)
    threshold_pct: float = Field(gt=0)
    spend_pace: float = Field(gt=0, le=1)
    spread_adjust_bps: int = Field(default=0, ge=0)
    max_spend: float | None = None
    buy: bool = True
    max_spread_bps: int | None = Field(default=None, ge=0, lt=10_000)


class HolderConfig(StrictModel):
    """Par-expecting buyer (Story 2.6): buys below ``1 - entry_discount_pct/100``, redeems
    in tranches the redemption channel can pay. ``redeem_horizon_steps`` is a constructor
    default on the agent, not a config field. ``exit_discount_pct`` (Story 3.3): once spot
    falls below ``1 - exit_discount_pct/100`` it sells everything on the AMM and never
    re-enters; ``None`` (default) never sells."""

    type: Literal["holder"]
    id: str
    capital: float = Field(gt=0)
    entry_discount_pct: float = Field(ge=0)
    pace: float = Field(gt=0, le=1)
    redeem_when_capacity: bool = True
    exit_discount_pct: float | None = Field(default=None, gt=0, lt=100)

    @model_validator(mode="after")
    def _exit_below_entry(self) -> HolderConfig:
        if self.exit_discount_pct is not None and not (
            self.exit_discount_pct > self.entry_discount_pct
        ):
            raise ValueError(
                f"holder {self.id!r}: exit_discount_pct ({self.exit_discount_pct}) must exceed "
                f"entry_discount_pct ({self.entry_discount_pct}): the exit price must sit below "
                "the entry price, or the holder sells at the price it buys"
            )
        return self


AgentConfig = Annotated[
    AttackerConfig | ArbitrageurConfig | DefenderConfig | HolderConfig,
    Field(discriminator="type"),
]


class ScenarioConfig(StrictModel):
    version: Literal[1]
    name: str
    seed: int = Field(ge=0)
    steps: StepsConfig
    assets: list[AssetConfig] = Field(min_length=2)
    amm: AMMConfig
    oracle: OracleConfig
    redemption: RedemptionConfig
    environment: EnvironmentConfig
    agents: list[AgentConfig]
    termination: TerminationConfig
    metrics: MetricsConfig

    @model_validator(mode="after")
    def _unique_agent_ids(self) -> ScenarioConfig:
        ids = [a.id for a in self.agents]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"agents: duplicate id(s): {', '.join(dupes)}")
        return self

    def content_hash(self) -> str:
        """SHA-256 hex digest of the canonical JSON dump (sorted keys, compact).

        Story 2.5 fields enter only when used, so older scenarios keep their hash: an
        empty ``redemption.capacity_schedule`` and an absent ``price_series_path`` are
        dropped, as is ``termination.peg_recovered.reference`` when it is ``par``
        (Story 2.8). A set series enters as the file's sha256 (``price_series_sha256``), not
        its path, so the hash follows the data and does not depend on the machine. A
        defender's ``buy`` and ``max_spread_bps`` enter only when not at their defaults
        (``True``, ``None``; Story 3.2). A holder's ``exit_discount_pct`` enters only when set
        (Story 3.3)."""
        data = self.model_dump(mode="json")
        env = data["environment"]
        if env.pop("price_series_path") is not None:
            env["price_series_sha256"] = self.environment.price_series_sha256
        if not data["redemption"]["capacity_schedule"]:
            del data["redemption"]["capacity_schedule"]
        rec = data["termination"]["peg_recovered"]
        if rec is not None and rec["reference"] == "par":
            del rec["reference"]  # Story 2.8: the default leaves older hashes unchanged
        for agent in data["agents"]:
            if agent["type"] == "defender":  # Story 3.2: defaults leave older hashes unchanged
                if agent["buy"] is True:
                    del agent["buy"]
                if agent["max_spread_bps"] is None:
                    del agent["max_spread_bps"]
            elif agent["type"] == "holder" and agent["exit_discount_pct"] is None:
                del agent["exit_discount_pct"]  # Story 3.3: never-sells leaves hashes unchanged
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def load_scenario(path: Path) -> ScenarioConfig:
    """Parse a scenario YAML file and validate it.

    Raises FileNotFoundError if the path is missing and pydantic.ValidationError
    if the content does not match the schema. A relative
    ``environment.price_series_path`` resolves against the file's directory.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ScenarioConfig.model_validate(data, context={"base_dir": Path(path).parent})
