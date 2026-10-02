# Story 1.5: Oracle and Environment Modules

Status: in-progress

## Story

As a **researcher**,
I want an external reference price with seeded shocks and an oracle that lags it by heartbeat and deviation rules,
so that oracle delay is a first-class, calibratable parameter.

## Acceptance Criteria

1. Carry-over: `ConstantProductAMM.cumulative_fees` is replaced by `cumulative_fees_stable` and `cumulative_fees_reference` (fee accrues in the input token of each swap); `snapshot()` exposes both and no longer has `cumulative_fees`; existing AMM tests updated; one new assertion checks a `sell_stable` swap increments only the stable counter
2. `src/depeg_sim/environment/price_process.py` defines `ReferencePrice(name="environment", base_price, volatility_per_step, shocks)` implementing `Subsystem` with `phases == {ENVIRONMENT_UPDATE}`
3. On each `ENVIRONMENT_UPDATE`, `ReferencePrice` sets `price` for the current step: `price = prev * exp(volatility_per_step * z)` with `z = ctx.rng.standard_normal()` drawn **only when `volatility_per_step > 0`**, then applies any `ShockEvent` whose `step == ctx.clock.step_index` as `price *= (1 + pct/100)`; step 0 starts from `base_price` (shocks at step 0 apply); emits `price_updated` with `{step, price, prev_price, shock_pct}` (`shock_pct` is `0.0` when none)
4. With `volatility_per_step == 0` and no shocks, `price == base_price` on every step and `ctx.rng` is **never** consumed (test: rng state before == after a 100-step run)
5. Two runs with the same seed and `volatility_per_step > 0` produce identical price sequences; a different seed produces a different sequence
6. `src/depeg_sim/protocol/oracle.py` defines `Oracle(name="oracle", heartbeat_steps, deviation_threshold_pct, source: ReferencePrice)` implementing `Subsystem` with `phases == {ORACLE_UPDATE}`
7. On each `ORACLE_UPDATE`, the oracle publishes `source.price` iff `(step - last_update_step) >= heartbeat_steps` **or** `abs(source.price / published_price - 1) * 100 >= deviation_threshold_pct` **or** it has never published; otherwise `published_price` is unchanged; `staleness_steps = step - last_update_step`; emits `oracle_updated` with `{step, price, reason}` only when it publishes (`reason in {"initial", "heartbeat", "deviation"}`)
8. `Oracle` exposes `price` (the published value), `last_update_step`, `staleness_steps`, and `reference_price` (pass-through to `source.price`, for diagnostics); it does **not** implement `PegView`
9. Oracle tests with a scripted source (stub whose `price` is set per step): heartbeat 25 and flat price → updates at steps 0, 25, 50, 75 only; threshold 0.5% and a 0.6% move at step 7 → updates at 0 and 7, then next at 7+heartbeat; a 0.4% move never triggers deviation; `staleness_steps` counts correctly between updates; `deviation_threshold_pct == 0` means every step updates
10. Both modules' `snapshot()` return their full state (`ReferencePrice`: `price, prev_price, step_applied_shocks`; `Oracle`: `published_price, last_update_step`), and `from_config` factories exist: `ReferencePrice.from_config(EnvironmentConfig)`, `Oracle.from_config(OracleConfig, source)`
11. Integration test: `Engine` with `ReferencePrice` (volatility 0.001, seed 42) + `Oracle` (heartbeat 10, threshold 1.0) + AMM, `max_steps 100` → run terminates by `max_steps`, `oracle_updated` count ≥ 10 and ≤ 100, every `oracle_updated.price` equals the `price_updated.price` of the same step, and the run is byte-identical on repeat (events list equality)
12. Scenario YAML field `environment.shocks[].pct` is documented in the module docstring as **percent**, not fraction (`-5.0` means minus five percent)
13. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Carry-over from 1.4 review (AC: 1)
  - [ ] Split `cumulative_fees` in `protocol/amm.py`; update docstring, `snapshot()`, `swap()`
  - [ ] Update `tests/test_amm.py` (snapshot key set, any fee assertions); add the per-token assertion
  - [ ] `pytest` green; commit separately as `story 1.5: split amm cumulative fees by token`

- [ ] Reference price process (AC: 2, 3, 4, 5, 10, 12)
  - [ ] `environment/price_process.py`: `ReferencePrice` class; `_shocks_by_step: dict[int, float]` built at construction (sum pcts if two shocks share a step; document)
  - [ ] `on_phase(ctx, ENVIRONMENT_UPDATE)` per AC 3; guard the rng draw on `volatility_per_step > 0`
  - [ ] `snapshot()`, `from_config`
  - [ ] Tests: flat price, rng untouched (compare `ctx.rng.bit_generator.state` dicts), shock at step 0 and step N, determinism across seeds, two shocks same step

- [ ] Oracle (AC: 6, 7, 8, 9, 10)
  - [ ] `protocol/oracle.py`: `Oracle` class holding a reference to the price source (duck-typed: anything with `.price`)
  - [ ] `on_phase(ctx, ORACLE_UPDATE)` per AC 7 with the three reasons; `staleness_steps` property
  - [ ] `snapshot()`, `from_config`
  - [ ] `tests/test_oracle.py` with a `ScriptedPriceSource` stub (put it in `tests/kernel_stubs.py`); cover every bullet of AC 9

- [ ] Integration (AC: 11)
  - [ ] `tests/test_oracle_integration.py`: register `environment`, `oracle`, `amm` in that order; assertions per AC 11; repeat-run equality

- [ ] Tests, lint, close out (AC: 13)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] `python run.py scenarios/soros-baseline.yaml` (unchanged output; modules not yet registered by the CLI)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 1.5: oracle and environment`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.4 (Status: done)**

- Construction validates invariants and raises `ValueError`; execution/hook paths never
  raise for domain conditions. Oracle and environment have no actions, so they have no
  rejection path at all; they only validate at construction (`heartbeat_steps > 0`,
  `base_price > 0`, `volatility_per_step >= 0`).
- `PegView` is the AMM's. The oracle must not provide it. Termination compares AMM spot to
  peg; agents (1.7) compare AMM spot to the *oracle* price. Keep them distinct.
- Events via `ctx.events.emit(step, kind, source, payload)`; `source` is the subsystem name.
- `SourceStub` now takes `kind`/`params`; `kernel_stubs.py` is the home for new stubs
  (`ScriptedPriceSource` goes there).
- Carry-over task 1 (fee split) is small; land it first and separately.

[Source: docs/stories/1-4-constant-product-amm.md#Senior-Developer-Review]

### Architecture Alignment

Two layers from the spec:

- **Market Environment Layer** → `ReferencePrice`. Exogenous. The only consumer of
  `ctx.rng` in Epic 1. It represents "what the stablecoin is really worth off-chain" (or,
  for a fiat peg, the fundamentals). Shocks are the scheduled events the spec calls for.
- **Protocol Model Layer** → `Oracle`. A mechanism, not an actor. It publishes a *stale*
  copy of the reference price under Chainlink-style rules: heartbeat (max age) and
  deviation threshold (min move). Epic 2 calibrates both to real Chainlink feeds.

Why this matters for the research question: the oracle lag is one of the three axes of
the headline sweep. The attacker can move the AMM price inside the oracle's blind window;
the arbitrageur reacts to the oracle, not the AMM. The window between "reference moved"
and "oracle published" is the exploitable gap. These two modules make that gap a number.

### Price process (normative)

```
step 0:     prev = base_price
each step:  p = prev
            if volatility_per_step > 0:
                p *= exp(volatility_per_step * ctx.rng.standard_normal())
            if step in shocks:  p *= 1 + shocks[step] / 100
            emit price_updated {step, price: p, prev_price: prev, shock_pct}
            prev = p
```

Geometric (log-normal) steps so price stays positive. `volatility_per_step` is the
per-step log-return standard deviation; Epic 2's calibration note will translate from
annualised vol and the 12 s step. Draw exactly one normal per step when vol > 0; never
draw when vol == 0 (AC 4 protects the seed stream for scenarios that want a deterministic
shock-only environment).

### Oracle rule (normative)

```
on ORACLE_UPDATE at step s:
    ref = source.price
    if never published:                    publish(ref, "initial")
    elif s - last_update_step >= heartbeat: publish(ref, "heartbeat")
    elif |ref/published - 1| * 100 >= threshold: publish(ref, "deviation")
    else: no-op
```

Check order matters for the `reason` string only; the published value is the same either
way. `threshold == 0` makes the deviation branch fire whenever `ref != published`, i.e.
effectively every step the reference moves; document that `0` means "no deviation
filtering."

Phase order guarantees `ENVIRONMENT_UPDATE` runs before `ORACLE_UPDATE` in the same step,
so the oracle always sees this step's reference price.

### Registration order (for 1.8, stated here so tests match)

`environment`, `oracle`, `amm`, `redemption`, agents in config order, `metrics`.

### References

- [Source: docs/epics.md#Story-1.5]
- [Source: docs/stories/1-3-simulation-kernel.md#Interfaces]
- [Source: docs/stories/1-4-constant-product-amm.md#Senior-Developer-Review]
- Chainlink data feeds: heartbeat and deviation threshold semantics (https://docs.chain.link/data-feeds)

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-5-oracle-and-environment.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output with exit codes)_

### Completion Notes List

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.4 review
