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
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class RedemptionConfig(StrictModel):
    reserves: float = Field(ge=0)
    spread_bps: int = Field(ge=0, lt=10_000)
    capacity_per_step: float = Field(gt=0)
    peg_price: float = Field(default=1.0, gt=0)


class ShockEvent(StrictModel):
    step: int = Field(ge=0)
    pct: float  # +/- percent applied to the reference price


class EnvironmentConfig(StrictModel):
    base_price: float = Field(default=1.0, gt=0)
    volatility_per_step: float = Field(default=0.0, ge=0)
    shocks: list[ShockEvent] = Field(default_factory=list)


class PegRecoveredConfig(StrictModel):
    for_steps: int = Field(gt=0)
    tolerance: float = Field(gt=0)  # fraction, e.g. 0.001


class TerminationConfig(StrictModel):
    reserves_exhausted: bool = True
    peg_recovered: PegRecoveredConfig | None = None
    max_steps: bool = True

    @model_validator(mode="after")
    def _at_least_one_enabled(self) -> TerminationConfig:
        if not (self.reserves_exhausted or self.peg_recovered is not None or self.max_steps):
            raise ValueError(
                "termination: at least one of reserves_exhausted, peg_recovered, "
                "max_steps must be enabled"
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
    type: Literal["defender"]
    id: str
    budget: float = Field(gt=0)
    threshold_pct: float = Field(gt=0)
    spend_pace: float = Field(gt=0, le=1)
    spread_adjust_bps: int = Field(default=0, ge=0)
    max_spend: float | None = None


AgentConfig = Annotated[
    AttackerConfig | ArbitrageurConfig | DefenderConfig, Field(discriminator="type")
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
        """SHA-256 hex digest of the canonical JSON dump (sorted keys, compact)."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def load_scenario(path: Path) -> ScenarioConfig:
    """Parse a scenario YAML file and validate it.

    Raises FileNotFoundError if the path is missing and pydantic.ValidationError
    if the content does not match the schema.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ScenarioConfig.model_validate(data)
