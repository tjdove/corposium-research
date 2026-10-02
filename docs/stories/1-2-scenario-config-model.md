# Story 1.2: Scenario Configuration Model

Status: ready-for-dev

## Story

As a **researcher**,
I want scenarios defined in versioned YAML validated by Pydantic,
so that every run is fully described by one human-readable file.

## Acceptance Criteria

1. `src/depeg_sim/kernel/config.py` defines Pydantic v2 models: `ScenarioConfig` with fields `version`, `name`, `seed`, `steps`, `assets`, `amm`, `oracle`, `redemption`, `environment`, `agents`, `termination`, `metrics`
2. `steps` has `interval_seconds` (default 12, > 0) and `max_steps` (> 0)
3. `termination` supports three conditions, any subset enabled: `reserves_exhausted: bool`, `peg_recovered: {for_steps: int, tolerance: float}`, `max_steps: bool` (default true); at least one must be enabled
4. `agents` is a list of typed entries discriminated by `type: attacker | arbitrageur | defender`; each type has its own parameter model (fields listed in Dev Notes); unknown `type` rejected
5. `load_scenario(path: Path) -> ScenarioConfig` parses YAML and validates; all models use `extra="forbid"` so unknown fields raise
6. Only `version: 1` is accepted; any other value raises a validation error naming the supported version
7. `ScenarioConfig.content_hash() -> str` returns the SHA-256 hex digest of the canonical JSON dump (`model_dump_json` with sorted keys, no whitespace); two loads of the same file produce the same hash; changing any field changes it
8. `scenarios/soros-baseline.yaml` is rewritten to validate against the model with placeholder-but-plausible values for every section (values in Dev Notes)
9. `tests/test_config.py` covers: baseline file loads; each required top-level field missing raises; unknown top-level field raises; unknown nested field raises; `version: 2` raises; each agent type parses to its model; unknown agent type raises; `interval_seconds: 0` raises; termination with nothing enabled raises; hash stable across two loads; hash changes when seed changes
10. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Carry-over from Story 1.1 review (no AC; housekeeping)
  - [ ] In `.github/workflows/ci.yml` set `runs-on: ubuntu-24.04`, bump to `actions/checkout@v5` and `actions/setup-python@v6`; confirm CI still passes after push

- [ ] Define the config models (AC: 1, 2, 3, 4, 6)
  - [ ] Create `src/depeg_sim/kernel/config.py`
  - [ ] Base class `StrictModel(BaseModel)` with `model_config = ConfigDict(extra="forbid", frozen=True)`
  - [ ] `StepsConfig`, `AssetConfig`, `AMMConfig`, `OracleConfig`, `RedemptionConfig`, `EnvironmentConfig` (with `ShockEvent`), `TerminationConfig` (with `PegRecoveredConfig`), `MetricsConfig`
  - [ ] `AttackerConfig`, `ArbitrageurConfig`, `DefenderConfig`, each with `type: Literal[...]`; `AgentConfig = Annotated[Union[...], Field(discriminator="type")]`
  - [ ] `ScenarioConfig` with `version: Literal[1]` and a `model_validator` on `TerminationConfig` requiring at least one condition enabled
  - [ ] Use `Field(gt=0)` / `ge=0` constraints where Dev Notes specify

- [ ] Loader and hash (AC: 5, 7)
  - [ ] `load_scenario(path)` reads with `yaml.safe_load`, passes to `ScenarioConfig.model_validate`
  - [ ] `content_hash()` using `hashlib.sha256` over `model_dump_json(by_alias=True)` of a dict with sorted keys (dump to dict, `json.dumps(..., sort_keys=True, separators=(",", ":"))`)

- [ ] Rewrite the baseline scenario (AC: 8)
  - [ ] Replace `scenarios/soros-baseline.yaml` with the full structure from Dev Notes
  - [ ] Confirm `load_scenario(Path("scenarios/soros-baseline.yaml"))` succeeds

- [ ] Wire the CLI to validate (partial AC 5; keeps `run.py` honest)
  - [ ] `cli.main` calls `load_scenario` and prints `name`, `seed`, `content_hash()[:12]` before the "kernel not implemented" line; validation errors print to stderr and return 3
  - [ ] Update `tests/test_smoke.py` expectations accordingly

- [ ] Tests (AC: 9, 10)
  - [ ] Write `tests/test_config.py` covering every case in AC 9
  - [ ] `pytest`, `ruff check .`, `ruff format --check .`; paste output in Debug Log

- [ ] Close out
  - [ ] Fill Dev Agent Record, Change Log, set `Status: review`
  - [ ] Commit `story 1.2: scenario config model`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.1 (Status: done)**

- Scaffold is sound; nothing needed fixing. Toolchain is pytest + ruff 0.16; ruff also formats
  Markdown, so `ruff format --check .` counts `.md` files.
- Seoul runs Python 3.14; CI runs 3.12. Write 3.12-compatible code (no 3.13+/3.14-only syntax).
- Paste `exit=N` after each command in the Debug Log. Reviewer re-runs everything.
- PyYAML reads `on:` as `True`; irrelevant here but don't be surprised by YAML 1.1 quirks
  (`yes`/`no` become booleans — avoid them as string values in scenarios).

[Source: docs/stories/1-1-project-foundation-setup.md#Senior-Developer-Review]

### Architecture Alignment

This story is the **Scenario Definition Layer** from the original spec: the contract
between research design and execution. Everything the kernel (1.3), protocol modules
(1.4–1.6) and agents (1.7) need is declared here first, so they implement against a fixed
schema. Keep the models **data only** — no behavior, no defaults that encode mechanism
choices beyond what's listed below.

Models are `frozen=True` so a loaded config cannot be mutated mid-run (determinism).

### Model fields

```python
class StepsConfig:        interval_seconds: int = 12 (gt=0); max_steps: int (gt=0)
class AssetConfig:        symbol: str; decimals: int = 18 (ge=0, le=18)
class AMMConfig:          reserve_stable: float (gt=0); reserve_reference: float (gt=0); fee_bps: int (ge=0, lt=10_000)
class OracleConfig:       heartbeat_steps: int (gt=0); deviation_threshold_pct: float (ge=0)
class RedemptionConfig:   reserves: float (ge=0); spread_bps: int (ge=0, lt=10_000); capacity_per_step: float (gt=0); peg_price: float = 1.0 (gt=0)
class ShockEvent:         step: int (ge=0); pct: float            # +/- percent applied to reference price
class EnvironmentConfig:  base_price: float = 1.0 (gt=0); volatility_per_step: float = 0.0 (ge=0); shocks: list[ShockEvent] = []
class PegRecoveredConfig: for_steps: int (gt=0); tolerance: float (gt=0)   # tolerance as fraction, e.g. 0.001
class TerminationConfig:  reserves_exhausted: bool = True; peg_recovered: PegRecoveredConfig | None = None; max_steps: bool = True
                          # validator: at least one of (reserves_exhausted, peg_recovered is not None, max_steps) true
class MetricsConfig:      record_every: int = 1 (gt=0); trace_decisions: bool = False; checkpoint_every: int | None = None (gt=0)

class AttackerConfig:     type: Literal["attacker"]; id: str; capital: float (gt=0); start_step: int (ge=0); pace: float (gt=0, le=1); stop_below_price: float | None = None
class ArbitrageurConfig:  type: Literal["arbitrageur"]; id: str; capital: float (gt=0); min_profit_bps: int (ge=0); latency_steps: int = 0 (ge=0)
class DefenderConfig:     type: Literal["defender"]; id: str; budget: float (gt=0); threshold_pct: float (gt=0); spend_pace: float (gt=0, le=1); spread_adjust_bps: int = 0 (ge=0); max_spend: float | None = None

class ScenarioConfig:     version: Literal[1]; name: str; seed: int (ge=0); steps; assets: list[AssetConfig] (min 2); amm; oracle; redemption; environment; agents: list[AgentConfig]; termination; metrics
```

Agent `id` values must be unique — add a validator on `ScenarioConfig`.

### Baseline scenario content

```yaml
version: 1
name: soros-baseline
seed: 42
steps:
  interval_seconds: 12
  max_steps: 5000
assets:
  - { symbol: STABLE, decimals: 18 }
  - { symbol: REF, decimals: 18 }
amm:
  reserve_stable: 1_000_000
  reserve_reference: 1_000_000
  fee_bps: 30
oracle:
  heartbeat_steps: 25
  deviation_threshold_pct: 0.5
redemption:
  reserves: 500_000
  spread_bps: 10
  capacity_per_step: 25_000
  peg_price: 1.0
environment:
  base_price: 1.0
  volatility_per_step: 0.0
  shocks: []
agents:
  - { type: attacker, id: attacker-1, capital: 300_000, start_step: 50, pace: 0.1 }
  - { type: arbitrageur, id: arb-1, capital: 200_000, min_profit_bps: 20, latency_steps: 1 }
  - { type: defender, id: defender-1, budget: 400_000, threshold_pct: 1.0, spend_pace: 0.2 }
termination:
  reserves_exhausted: true
  peg_recovered: { for_steps: 100, tolerance: 0.001 }
  max_steps: true
metrics:
  record_every: 1
  trace_decisions: true
  checkpoint_every: 500
```

Note: YAML `1_000_000` parses as the integer 1000000 in PyYAML; pydantic coerces int → float
for float fields. If PyYAML on 3.12 does not accept underscores, write `1000000`.

### Content hash

```python
def content_hash(self) -> str:
    payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
```

### CLI behavior after this story

```
$ python run.py scenarios/soros-baseline.yaml
depeg-sim: scenario=soros-baseline seed=42 hash=<12 hex>
kernel not implemented yet (see docs/epics.md, Story 1.3)
```
Validation failure → message on stderr, exit 3. Missing file stays exit 2.

### References

- [Source: docs/epics.md#Story-1.2]
- [Source: docs/CHARTER.md#4-Scope]
- [Source: docs/stories/1-1-project-foundation-setup.md#Senior-Developer-Review]
- Pydantic v2 discriminated unions: https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-2-scenario-config-model.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output with exit codes)_

### Completion Notes List

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.1 review
