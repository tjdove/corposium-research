# Story 1.3: Simulation Kernel

Status: review

## Story

As a **developer**,
I want the engine, clock, scheduler and run context implemented with no domain logic,
so that protocol modules and agents plug into a fixed, versioned step order.

## Acceptance Criteria

1. `kernel/scheduler.py` defines `PHASE_ORDER_VERSION = 1` and `PHASES: tuple[Phase, ...]` as an enum in this exact order: `ENVIRONMENT_UPDATE, ORACLE_UPDATE, STATE_OBSERVATION, AGENT_DECISION, ACTION_QUEUE, EXECUTION, PROTOCOL_EVENTS, METRIC_UPDATE, PERSISTENCE`
2. `kernel/clock.py`: `Clock(interval_seconds)` with `step_index: int` (starts 0), `elapsed_seconds: int`, `tick()`; `elapsed_seconds == step_index * interval_seconds` always
3. `kernel/context.py`: `RunContext` holds `config: ScenarioConfig`, `rng: numpy.random.Generator` seeded from `seed`, `clock`, `events: EventSink`, `decisions: DecisionTrace`, `registry: Registry` of subsystems; `RunContext.from_config(config, seed_override=None)`
4. `kernel/events.py`: `Event(step, kind, source, payload: dict)`; `EventSink.emit(...)` appends in order; `EventSink.all() -> list[Event]`; `DecisionTrace` same shape with `agent_id, rule, observed, action`
5. `kernel/interfaces.py` declares `typing.Protocol` classes: `Subsystem` (`name`, `phases: frozenset[Phase]`, `on_phase(ctx, phase)`), `ActionSource` (extends Subsystem with `decide(ctx) -> list[Action]`), `ActionTarget` (extends Subsystem with `execute(ctx, action) -> ExecutionResult`), plus `Action` and `ExecutionResult` dataclasses; the kernel calls only these
6. `kernel/engine.py`: `Engine(ctx).run() -> RunResult`; each step iterates `PHASES`, dispatching `on_phase` to every registered subsystem whose `phases` contains that phase, in registration order; in `AGENT_DECISION` it collects actions from `ActionSource`s into `ctx.action_queue`; in `EXECUTION` it routes each action to the `ActionTarget` named by `action.target` in queue order; termination is checked after `PERSISTENCE` each step
7. `kernel/termination.py`: `check(ctx) -> str | None` evaluates the enabled conditions from `config.termination` in fixed order `reserves_exhausted, peg_recovered, max_steps` and returns the first that fires; the kernel reads the needed values through two small accessor protocols `ReservesView` (`reserves_exhausted: bool`) and `PegView` (`peg_deviation: float`) that subsystems may register; a condition whose view is not registered is skipped
8. `kernel/checkpoint.py`: `write_checkpoint(ctx, path)` dumps `{step, elapsed_seconds, phase_order_version, rng_state, subsystems: {name: subsystem.snapshot()}}` as JSON (sorted keys); called every `metrics.checkpoint_every` steps and at termination when set; `Subsystem` gains an optional `snapshot() -> dict` (default `{}`)
9. `RunResult` dataclass: `steps_run, terminated_by, events, decisions, checkpoints: list[Path]`
10. Determinism test: two engines built from the same config with stub subsystems that draw from `ctx.rng` produce identical event lists and identical checkpoint JSON bytes
11. Termination tests with stubs: `reserves_exhausted` fires the step a stub sets its flag; `peg_recovered` fires only after `for_steps` consecutive steps within `tolerance`, and resets its counter on any excursion; `max_steps` fires at exactly `max_steps`; precedence order holds when two fire the same step
12. Phase-order test: a recording stub registered for all phases sees exactly `PHASES` order each step; a stub registered for a subset sees only those
13. `grep -rn -i "price\|swap\|reserve\|attacker\|arbitrag\|defender" src/depeg_sim/kernel/*.py` matches only in `config.py`, `termination.py` (the two view protocols) and docstrings; no mechanism logic in the kernel
14. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Phases and clock (AC: 1, 2)
  - [x] `kernel/scheduler.py`: `class Phase(enum.Enum)`, `PHASES`, `PHASE_ORDER_VERSION`
  - [x] `kernel/clock.py`: `Clock`
  - [x] Tests: phase count is 9 and order matches; clock arithmetic

- [x] Events, actions, interfaces (AC: 4, 5)
  - [x] `kernel/events.py`: `Event`, `EventSink`, `Decision`, `DecisionTrace` (all frozen dataclasses + append-only sinks)
  - [x] `kernel/interfaces.py`: `Action`, `ExecutionResult`, `Subsystem`, `ActionSource`, `ActionTarget`, `ReservesView`, `PegView` (Protocols; `@runtime_checkable`)
  - [x] Tests: sinks preserve order; Protocol conformance via a minimal stub

- [x] Run context and registry (AC: 3)
  - [x] `kernel/context.py`: `Registry` (ordered dict by name; `register(subsystem)` rejects duplicate names; `by_phase(phase)`, `sources()`, `targets()`, `get(name)`), `RunContext`, `from_config`
  - [x] RNG: `numpy.random.default_rng(seed)`; `seed_override` wins when given (this is what `--seed` will use in 1.8)
  - [x] Tests: registry ordering, duplicate rejection, `rng` reproducibility for a given seed

- [x] Termination (AC: 7)
  - [x] `kernel/termination.py`: `check(ctx)`; `PegRecoveredTracker` keeps the consecutive counter on the context
  - [x] Tests per AC 11 using stubs that implement only `ReservesView` or `PegView`

- [x] Checkpoints (AC: 8)
  - [x] `kernel/checkpoint.py`: `write_checkpoint`; rng state via `ctx.rng.bit_generator.state` (JSON-safe dict)
  - [x] Test: file written at the right steps; JSON keys sorted; byte-identical across two deterministic runs

- [x] Engine (AC: 6, 9)
  - [x] `kernel/engine.py`: `Engine`, `RunResult`; step loop as specified; `ctx.action_queue` cleared at `ACTION_QUEUE` phase start, filled from sources at `AGENT_DECISION`, drained at `EXECUTION`
  - [x] Unknown `action.target` raises `KernelError` with the action and step in the message
  - [x] Tests per AC 10, 12; engine stops at the right step; `RunResult` fields populated

- [x] Kernel purity check (AC: 13)
  - [x] Run the grep from AC 13; paste output in Debug Log; fix any leak

- [x] Wire CLI minimally (no new AC; keeps `run.py` honest)
  - [x] `cli.main`: build `RunContext.from_config(cfg, seed_override=args.seed)`, run `Engine` with **no** subsystems registered (so only `max_steps` can fire), print `steps_run` and `terminated_by`; replace the "kernel not implemented" line
  - [x] Update `tests/test_smoke.py`

- [x] Tests, lint, close out (AC: 14)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N` in Debug Log
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 1.3: simulation kernel`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.2 (Status: done)**

- `StrictModel` (`extra="forbid"`, `frozen=True`) is the base for any config. Kernel runtime
  objects are **not** config: use `@dataclass(frozen=True)` for events/actions and plain classes
  for mutable state (clock, sinks, registry).
- `cfg.content_hash()` exists; the manifest in 1.8 will use it. Don't recompute hashes here.
- `--seed` on the CLI is inert today. This story gives `RunContext.from_config` a
  `seed_override`; `cli.main` passes `args.seed` through. That closes the 1.2 advisory.
- Builder follows the story file over any kickoff prompt. Correct; keep doing that.

[Source: docs/stories/1-2-scenario-config-model.md#Senior-Developer-Review]

### Architecture Alignment

This is the **Simulation Kernel** layer. The spec's rule is the whole point of this story:
the kernel orchestrates and never impersonates a protocol module or agent. If you find
yourself writing `price`, `swap`, or `reserve` arithmetic in `kernel/`, stop.

**Step loop (one step):**

```
for phase in PHASES:
    if phase is ACTION_QUEUE: ctx.action_queue.clear()
    for sub in registry.by_phase(phase): sub.on_phase(ctx, phase)
    if phase is AGENT_DECISION:
        for src in registry.sources(): ctx.action_queue.extend(src.decide(ctx))
    if phase is EXECUTION:
        for action in ctx.action_queue:
            registry.get(action.target).execute(ctx, action)   # KernelError if missing
    if phase is PERSISTENCE and checkpoint due: write_checkpoint(...)
reason = termination.check(ctx)
if reason: stop
ctx.clock.tick()
```

Note the ordering subtlety: `on_phase` hooks run first in every phase, then the
phase-specific kernel action. So a protocol module registered for `EXECUTION` gets
`on_phase(EXECUTION)` **before** actions are routed to it. Modules that need to act after
all actions settle use `PROTOCOL_EVENTS`. Document this in the `engine.py` module docstring.

**Why both `on_phase` and `decide`/`execute`:** `on_phase` is the generic hook (oracle ticks,
environment updates, metric collection). `decide`/`execute` are the typed action path so the
kernel can route without knowing what an action means. An `Action` is just
`(source: str, target: str, kind: str, params: dict)`.

**Registration order is execution order.** Story 1.8 registers subsystems in a fixed
sequence (environment, oracle, amm, redemption, agents in config order, metrics). The
kernel never sorts.

### Interfaces (normative)

```python
# kernel/interfaces.py
@dataclass(frozen=True)
class Action:
    source: str; target: str; kind: str; params: Mapping[str, Any]

@dataclass(frozen=True)
class ExecutionResult:
    ok: bool; detail: Mapping[str, Any]

@runtime_checkable
class Subsystem(Protocol):
    name: str
    phases: frozenset[Phase]
    def on_phase(self, ctx: "RunContext", phase: Phase) -> None: ...
    def snapshot(self) -> dict: ...          # may return {}

@runtime_checkable
class ActionSource(Subsystem, Protocol):
    def decide(self, ctx: "RunContext") -> list[Action]: ...

@runtime_checkable
class ActionTarget(Subsystem, Protocol):
    def execute(self, ctx: "RunContext", action: Action) -> ExecutionResult: ...

@runtime_checkable
class ReservesView(Protocol):
    @property
    def reserves_exhausted(self) -> bool: ...

@runtime_checkable
class PegView(Protocol):
    @property
    def peg_deviation(self) -> float: ...    # fraction; 0.0 = at peg
```

`Registry.sources()` returns registered subsystems that satisfy `ActionSource`;
`targets()` those satisfying `ActionTarget`. Views are found the same way:
`termination.check` looks for the first registered subsystem satisfying `ReservesView`
/ `PegView`. (Story 1.6's redemption module will provide `ReservesView`; 1.4's AMM or
1.8's metrics will provide `PegView`.)

### Events

```python
@dataclass(frozen=True)
class Event:
    step: int; kind: str; source: str; payload: Mapping[str, Any]

@dataclass(frozen=True)
class Decision:
    step: int; agent_id: str; rule: str; observed: Mapping[str, Any]; action: Mapping[str, Any] | None
```

Sinks are append-only lists with `emit`/`record` and `all()`. The kernel itself emits two
events: `run_started` (step 0, payload: seed, scenario hash, phase order version) and
`run_terminated` (payload: reason, steps_run).

### Termination

`peg_recovered` needs memory across steps. Keep a `PegRecoveredTracker` on the context
(`ctx.term_state`) with `consecutive_in_band: int`. Rule: at check time, if
`abs(peg_deviation) <= tolerance` increment, else reset to 0; fire when counter reaches
`for_steps`. `max_steps` fires when `clock.step_index + 1 >= max_steps` evaluated after the
step runs, so a scenario with `max_steps: 10` runs exactly 10 steps (indices 0–9).

### Checkpoint JSON shape

```json
{"elapsed_seconds": 600, "phase_order_version": 1,
 "rng_state": {"bit_generator": "PCG64", "state": {...}},
 "step": 50, "subsystems": {"stub": {...}}}
```

Use `json.dumps(..., sort_keys=True, indent=None)` so bytes are stable. `numpy` RNG state
contains ints that fit JSON; test it round-trips.

### Stub subsystems for tests

Put them in `tests/kernel_stubs.py` (not under `src/`). Suggested:
- `RecordingStub(name, phases)`: appends `(step, phase)` to a list on each `on_phase`
- `RngStub`: draws `ctx.rng.random()` in `ENVIRONMENT_UPDATE` and emits it as an event
- `ReservesStub(exhaust_at_step)`: implements `ReservesView`
- `PegStub(deviations: list[float])`: implements `PegView`, returns `deviations[step]`
- `SourceStub` / `TargetStub`: one action per step; target records what it received

These stubs are the only place "reserves" or "peg" appear in tests for this story.

### CLI after this story

```
$ python run.py scenarios/soros-baseline.yaml
depeg-sim: scenario=soros-baseline seed=42 hash=7c4f870b2d8a
run: steps=5000 terminated_by=max_steps
```
(No subsystems yet, so `reserves_exhausted` and `peg_recovered` views are absent and skipped.)

### References

- [Source: docs/epics.md#Story-1.3]
- [Source: docs/CHARTER.md#9-Principles] — deterministic and replayable, always
- [Source: CLAUDE.md#Hard-rules] — determinism, phase order versioned, no domain logic in kernel
- [Source: docs/stories/1-2-scenario-config-model.md#Senior-Developer-Review]
- numpy Generator state: https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.BitGenerator.state.html

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-3-simulation-kernel.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code on Seoul. Commands run in the repo
`.venv` (Python 3.12.13, same minor as CI); package installed with `uv pip install -e ".[dev]"`.

### Debug Log References

Final run, verbatim:

```
$ pytest
........................................................................ [ 78%]
....................                                                     [100%]
92 passed in 0.30s
exit=0

$ pytest --cov=depeg_sim.kernel --cov-report=term-missing

Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
src/depeg_sim/kernel/__init__.py          0      0   100%
src/depeg_sim/kernel/checkpoint.py       12      0   100%
src/depeg_sim/kernel/clock.py            12      0   100%
src/depeg_sim/kernel/config.py           99      0   100%
src/depeg_sim/kernel/context.py          60      1    98%   54
src/depeg_sim/kernel/engine.py           72      0   100%
src/depeg_sim/kernel/events.py           39      1    97%   75
src/depeg_sim/kernel/interfaces.py       30      0   100%
src/depeg_sim/kernel/scheduler.py        14      0   100%
src/depeg_sim/kernel/termination.py      21      0   100%
-------------------------------------------------------------------
TOTAL                                   359      2    99%
92 passed in 0.60s
exit=0

$ ruff check .
All checks passed!
exit=0

$ ruff format --check .
29 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml
depeg-sim: scenario=soros-baseline seed=42 hash=7c4f870b2d8a
run: steps=5000 terminated_by=max_steps
exit=0

$ grep -rn -i "price\|swap\|reserve\|attacker\|arbitrag\|defender" src/depeg_sim/kernel/*.py
src/depeg_sim/kernel/interfaces.py:12:``ReservesView`` and ``PegView`` are the two read-only accessors the termination
src/depeg_sim/kernel/interfaces.py:68:class ReservesView(Protocol):
src/depeg_sim/kernel/interfaces.py:70:    def reserves_exhausted(self) -> bool: ...
src/depeg_sim/kernel/config.py:34:    reserve_stable: float = Field(gt=0)
src/depeg_sim/kernel/config.py:35:    reserve_reference: float = Field(gt=0)
src/depeg_sim/kernel/config.py:45:    reserves: float = Field(ge=0)
src/depeg_sim/kernel/config.py:48:    peg_price: float = Field(default=1.0, gt=0)
src/depeg_sim/kernel/config.py:53:    pct: float  # +/- percent applied to the reference price
src/depeg_sim/kernel/config.py:57:    base_price: float = Field(default=1.0, gt=0)
src/depeg_sim/kernel/config.py:68:    reserves_exhausted: bool = True
src/depeg_sim/kernel/config.py:74:        if not (self.reserves_exhausted or self.peg_recovered is not None or self.max_steps):
src/depeg_sim/kernel/config.py:76:                "termination: at least one of reserves_exhausted, peg_recovered, "
src/depeg_sim/kernel/config.py:88:class AttackerConfig(StrictModel):
src/depeg_sim/kernel/config.py:89:    type: Literal["attacker"]
src/depeg_sim/kernel/config.py:94:    stop_below_price: float | None = None
src/depeg_sim/kernel/config.py:97:class ArbitrageurConfig(StrictModel):
src/depeg_sim/kernel/config.py:98:    type: Literal["arbitrageur"]
src/depeg_sim/kernel/config.py:105:class DefenderConfig(StrictModel):
src/depeg_sim/kernel/config.py:106:    type: Literal["defender"]
src/depeg_sim/kernel/config.py:116:    AttackerConfig | ArbitrageurConfig | DefenderConfig, Field(discriminator="type")
src/depeg_sim/kernel/termination.py:3:Conditions are checked in fixed precedence order ``reserves_exhausted``,
src/depeg_sim/kernel/termination.py:5:reads domain state only through the ``ReservesView`` / ``PegView`` accessors; a
src/depeg_sim/kernel/termination.py:12:from depeg_sim.kernel.interfaces import PegView, ReservesView
src/depeg_sim/kernel/termination.py:18:    if term.reserves_exhausted:
src/depeg_sim/kernel/termination.py:19:        view = ctx.registry.find(ReservesView)
src/depeg_sim/kernel/termination.py:20:        if view is not None and view.reserves_exhausted:
src/depeg_sim/kernel/termination.py:21:            return "reserves_exhausted"
exit=0
```

AC 13 grep result: no matches in `scheduler.py`, `clock.py`, `events.py`, `context.py`,
`checkpoint.py` or `engine.py`. Matches are in `config.py` (schema), `termination.py` (the two
view lookups and its docstring) and `interfaces.py`: line 12 is the module docstring, lines
68/70 are the `ReservesView` protocol itself. See Completion Note 2.

### Completion Notes List

1. **Deviation from the Dev Notes step loop: queue clear moved to `AGENT_DECISION`.** The
   normative loop clears `ctx.action_queue` at the start of `ACTION_QUEUE`, but AC 1 orders
   `AGENT_DECISION` → `ACTION_QUEUE` → `EXECUTION`. Implemented literally, every action decided
   in a step is discarded before `EXECUTION`, so nothing is ever executed and AC 6 cannot hold.
   The smallest change that keeps "clear → fill → drain" per step is to clear at the start of
   `AGENT_DECISION` (before its hooks). `ACTION_QUEUE` hooks therefore see the full queue for
   the step. Documented in the `engine.py` docstring; covered by
   `test_queue_holds_only_current_step_actions`. **Dev manager: please confirm or rule
   otherwise.**
2. **AC 13 vs Interfaces block.** AC 13 says the view protocols live in `termination.py`; the
   normative Interfaces block and the Tasks put `ReservesView`/`PegView` in `interfaces.py`.
   I followed the Interfaces block, so the grep matches `interfaces.py` (the protocol
   definition only) rather than `termination.py`. Moving them is a one-line change if
   preferred, but `interfaces.py` would still need to re-export or not mention them.
3. **Ordering subtlety** (`on_phase` before the kernel's phase action) is documented in the
   `engine.py` module docstring and tested by `test_on_phase_runs_before_kernel_phase_action`.
4. **`snapshot()` optional:** the `Subsystem` Protocol carries a default body returning `{}`,
   inherited by classes that subclass it explicitly. `Registry.register` checks
   `isinstance(sub, Subsystem)` and raises `KernelError` otherwise, so a structural implementer
   must define `snapshot()`; otherwise it would silently fail the `ActionSource`/`ActionTarget`
   checks. Both styles are covered in `tests/kernel_stubs.py` (`RngStub` structural, others
   subclass).
5. **Checkpoint step numbering:** `step` = steps completed (`step_index + 1`) and
   `elapsed_seconds = step * interval`, matching the Dev Notes example (`step 50, 600 s`) and
   the context's "files at steps 5, 10 and final 12". Files go to
   `<output_dir>/checkpoints/step-NNNNNN.json`. No final duplicate is written when the cadence
   already hit the last step. With `output_dir=None` no checkpoints are written; the CLI passes
   none, since run output belongs to 1.8.
6. **`KernelError`** lives in `interfaces.py` (no ninth kernel file); `engine.py` also raises it
   when the named target exists but is not an `ActionTarget`.
7. **CLI:** prints `ctx.seed` (so `--seed 7` shows `seed=7`); new smoke test covers this.
8. **`pyproject.toml`:** added `[tool.ruff.format] exclude = ["*.md"]`. ruff 0.16 formats
   Python blocks inside Markdown, and `ruff format --check .` failed on this story's own Dev
   Notes. I did not want to rewrite the spec's code blocks. CI does not run the format check.
9. **Open question, not built:** with `termination.max_steps: false`, a run whose enabled views
   are not registered (or never fire) loops forever. `steps.max_steps` is not used as a hard cap
   because the story does not say to. Suggest 1.8 or a follow-up decides whether
   `steps.max_steps` is always a hard stop.
10. `ExecutionResult` returned by `execute` is not recorded by the kernel (not specified);
    targets emit their own events.

### File List

**Created:**
- `src/depeg_sim/kernel/scheduler.py`
- `src/depeg_sim/kernel/clock.py`
- `src/depeg_sim/kernel/events.py`
- `src/depeg_sim/kernel/interfaces.py`
- `src/depeg_sim/kernel/context.py`
- `src/depeg_sim/kernel/termination.py`
- `src/depeg_sim/kernel/checkpoint.py`
- `src/depeg_sim/kernel/engine.py`
- `tests/kernel_stubs.py`
- `tests/test_scheduler.py`, `tests/test_clock.py`, `tests/test_events.py`,
  `tests/test_interfaces.py`, `tests/test_context.py`, `tests/test_termination.py`,
  `tests/test_checkpoint.py`, `tests/test_engine.py`

**Modified:**
- `src/depeg_sim/cli.py`: runs the engine with no subsystems; `--seed` now live
- `tests/test_smoke.py`: expects the `run:` line; seed override test
- `pyproject.toml`: ruff format excludes `*.md`
- `docs/stories/1-3-simulation-kernel.md`: this record

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.2 review
- 2026-10-02: Implemented by Claude Code (Opus 5.5); 92 tests pass, ruff clean; queue-clear deviation and AC 13 location flagged in Completion Notes; status → review
