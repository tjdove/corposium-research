# Story 1.5: Oracle and Environment Modules

Status: done

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

- [x] Carry-over from 1.4 review (AC: 1)
  - [x] Split `cumulative_fees` in `protocol/amm.py`; update docstring, `snapshot()`, `swap()`
  - [x] Update `tests/test_amm.py` (snapshot key set, any fee assertions); add the per-token assertion
  - [x] `pytest` green; commit separately as `story 1.5: split amm cumulative fees by token`

- [x] Reference price process (AC: 2, 3, 4, 5, 10, 12)
  - [x] `environment/price_process.py`: `ReferencePrice` class; `_shocks_by_step: dict[int, float]` built at construction (sum pcts if two shocks share a step; document)
  - [x] `on_phase(ctx, ENVIRONMENT_UPDATE)` per AC 3; guard the rng draw on `volatility_per_step > 0`
  - [x] `snapshot()`, `from_config`
  - [x] Tests: flat price, rng untouched (compare `ctx.rng.bit_generator.state` dicts), shock at step 0 and step N, determinism across seeds, two shocks same step

- [x] Oracle (AC: 6, 7, 8, 9, 10)
  - [x] `protocol/oracle.py`: `Oracle` class holding a reference to the price source (duck-typed: anything with `.price`)
  - [x] `on_phase(ctx, ORACLE_UPDATE)` per AC 7 with the three reasons; `staleness_steps` property
  - [x] `snapshot()`, `from_config`
  - [x] `tests/test_oracle.py` with a `ScriptedPriceSource` stub (put it in `tests/kernel_stubs.py`); cover every bullet of AC 9

- [x] Integration (AC: 11)
  - [x] `tests/test_oracle_integration.py`: register `environment`, `oracle`, `amm` in that order; assertions per AC 11; repeat-run equality

- [x] Tests, lint, close out (AC: 13)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] `python run.py scenarios/soros-baseline.yaml` (unchanged output; modules not yet registered by the CLI)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 1.5: oracle and environment`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

Task 1 baseline (before fee split) and after:

```
$ pytest            # at f1013e5, before task 1
139 passed in 0.36s
$ pytest            # after task 1 (6fe6174)
140 passed in 0.32s
```

Final:

```
$ pytest; echo exit=$?
193 passed in 0.43s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
37 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml; echo exit=$?
depeg-sim: scenario=soros-baseline seed=42 hash=7c4f870b2d8a
run: steps=5000 terminated_by=max_steps
exit=0

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/environment/price_process.py      58      0   100%
src/depeg_sim/protocol/amm.py                  111      0   100%
src/depeg_sim/protocol/oracle.py                68      0   100%
TOTAL                                          627      2    99%
193 passed in 0.91s
```

CLI output is identical to the same command run at `e36aa45` (pre-story), in a
temporary worktree.

CI on push of `75254c9`:

```
$ gh run list --branch main --limit 1
completed	success	story 1.5: oracle and environment	ci	main	push	37015325742	31s	2026-10-02T13:47:15Z
```

### Completion Notes List

- **Task 1** landed separately (`6fe6174`). Fee accrues in the swap's input token:
  `sell_stable` → `cumulative_fees_stable`, `buy_stable` → `cumulative_fees_reference`.
  `tests/test_amm_integration.py` also asserted the old `cumulative_fees` and had to be
  updated (one assertion became two); that file is outside the context's "amm.py and
  test_amm.py only" list, but it was not possible to keep the suite green otherwise.
- **Threshold 0.** Under the normative `>=` rule, `deviation_threshold_pct == 0` publishes
  every step, flat price included (AC 9 says this). The Dev Notes line "fires whenever
  `ref != published`" doesn't match `>=`. I followed the AC and the `>=` rule. Because
  the oracle publishes every step, the heartbeat never comes due, so every reason after
  `initial` is `deviation` (tested).
- **`Oracle.price` is `None` before the first publish** (the interface listed `float`).
  In an engine run it is set from step 0's `ORACLE_UPDATE` on, so agents (which run in
  `AGENT_DECISION`) always see a float. `staleness_steps` is 0 before the first publish.
- **Shock validation (small addition).** Shocks on the same step are summed at
  construction. Each step's summed pct must be > -100, otherwise `ValueError`, so the
  price stays positive. Shock steps must be ints ≥ 0 and pcts finite.
- **`step_applied_shocks`** is the list of `(step, summed_pct)` applied so far; the
  snapshot renders it as `[[step, pct], ...]` for JSON.
- **The oracle never raises in its hook.** If a published price is 0 (impossible with
  `ReferencePrice`, possible with a scripted source), the deviation is treated as
  infinite rather than dividing by zero. A source with no `.price` is rejected at
  construction (`ValueError`, via the runtime-checkable `PriceSource` protocol).
- `isinstance(oracle, PegView)` is False, and neither module is an `ActionSource` or
  `ActionTarget` (tested). The oracle holds `source` directly; no registry lookup.
- `ScriptedPriceSource` (in `tests/kernel_stubs.py`) is a `Subsystem` on
  `ENVIRONMENT_UPDATE` that sets `price = prices[step]` (last value repeats). `price` is
  also a plain attribute for direct setting.
- The rng tests compare `ctx.rng.bit_generator.state` before and after. The vol > 0 test
  replays a fresh `default_rng(seed)` and checks that exactly one `standard_normal()`
  was drawn per step (equal prices and equal final generator state).
- The integration test registers `environment`, `oracle`, `amm` in that order. It
  checks `max_steps` termination, an update count between 10 and 100, that each
  `oracle_updated.price` matches the same step's `price_updated.price`, that no gap
  between updates exceeds the heartbeat, and that a repeat run gives equal events and
  decisions lists.
- Neither module is registered by the CLI (scope), so the CLI output is unchanged.
- Test count 139 → 193 (+1 task 1, +25 `test_price_process.py`, +25 `test_oracle.py`,
  +3 `test_oracle_integration.py`).

### File List

**Created:**

- `src/depeg_sim/environment/price_process.py`
- `src/depeg_sim/protocol/oracle.py`
- `tests/test_price_process.py`
- `tests/test_oracle.py`
- `tests/test_oracle_integration.py`

**Modified:**

- `src/depeg_sim/protocol/amm.py` (task 1)
- `tests/test_amm.py` (task 1)
- `tests/test_amm_integration.py` (task 1; see notes)
- `tests/kernel_stubs.py` (`ScriptedPriceSource`)
- `docs/stories/1-5-oracle-and-environment.md`

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.4 review
- 2026-10-02: Implemented by Claude Code (Opus 5.5): AMM fee split, `ReferencePrice`, `Oracle`, tests (193 passed); status set to review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-02
**Outcome:** **APPROVE** ✅

### Summary

Both modules match the normative rules. Reviewer re-ran on a separate machine: 193 passed,
ruff clean, and an independent 100-step engine run (environment vol 0.001, oracle heartbeat
10 / threshold 1.0, AMM) produced exactly 10 `oracle_updated` events with reasons
`{initial, heartbeat}`, identical events on repeat, different events with another seed,
`isinstance(oracle, PegView) is False`, and an untouched rng state under zero volatility.
CI run 37015403889 green. Both new modules at full line coverage.

### Rulings on the flagged items

1. **`test_amm_integration.py` touched during the fee split.** Necessary; the allow-list in
   the context file was incomplete. **Ratified.** Allow-lists name intent, not a cage; when a
   listed change breaks a test elsewhere, fixing that test is in scope.
2. **Threshold `0` publishes every step, including when flat.** AC 9 and the Dev Notes
   disagreed; the builder followed the AC. **Ratified: AC wins.** Semantics are now:
   `deviation_threshold_pct: 0` = a perfect, zero-lag oracle (publishes every step, reason
   `deviation`). This is a useful sweep endpoint for Epic 2 ("what if the oracle were
   instantaneous"). Docstring should say so; builder already noted it.
3. **`Oracle.price` is `None` before first publish.** Acceptable. Phase order guarantees
   `ORACLE_UPDATE` precedes `AGENT_DECISION` within step 0, so no agent ever observes `None`
   in a real run. Story 1.7 agents may assume a float. Type hint should read
   `float | None`; no further action.
4. **Shocks summing to ≤ −100% rejected at construction.** Correct application of the
   construction-validates rule. **Ratified.**
5. **Zero published price treated as infinite move.** Only reachable via a test stub;
   harmless, and better than a `ZeroDivisionError`. **Ratified.**

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1 | ✅ | `cumulative_fees_stable` / `_reference`; snapshot keys; per-token assertion; commit `6fe6174` green at 140 |
| 2 | ✅ | `ReferencePrice`, `phases == {ENVIRONMENT_UPDATE}` |
| 3 | ✅ | Log-normal step, shock as percent, `price_updated` payload |
| 4 | ✅ | Flat-price test; rng state equality (reviewer reproduced) |
| 5 | ✅ | Seed determinism tests (reviewer reproduced) |
| 6 | ✅ | `Oracle`, `phases == {ORACLE_UPDATE}` |
| 7 | ✅ | Three-branch rule with reason strings; `oracle_updated` only on publish |
| 8 | ✅ | `price`, `last_update_step`, `staleness_steps`, `reference_price`; not `PegView` (tested) |
| 9 | ✅ | 25 oracle tests cover each bullet incl. 0.4% non-trigger and threshold 0 |
| 10 | ✅ | `snapshot()` and `from_config` on both |
| 11 | ✅ | 3 integration tests; repeat-run equality (reviewer reproduced) |
| 12 | ✅ | Percent semantics in module docstring |
| 13 | ✅ | `193 passed`, `All checks passed!`, CI green |

**13 of 13 ACs met.**

### Key Findings

No High or Medium issues.

**Low / advisory:**
- **[LOW-1] Dev Notes vs AC on threshold 0.** Spec defect, resolved by ruling 2. Future
  story Dev Notes will be checked against their ACs before drafting.
- **[LOW-2] The reviewer's ad-hoc run terminated by `peg_recovered` at step 100** (no trades,
  deviation 0 for 100 steps, `for_steps: 100`) rather than `max_steps`, because both fired the
  same step and `peg_recovered` has precedence. Correct per 1.3. Noting it because 1.8's
  baseline scenario must have the attacker actually move the price or every run will
  "recover" trivially.

### Learnings for Story 1.6

- Hook-only subsystems are now proven (`ReferencePrice`, `Oracle`). Redemption is a hybrid:
  an `ActionTarget` (`redeem` requests) **and** a hook (`PROTOCOL_EVENTS` to process the
  queue and set the exhaustion flag). It is also the first `ReservesView` provider.
- Registration order for 1.8 is now stated: `environment, oracle, amm, redemption, agents…, metrics`.
- Reason strings in events (`initial/heartbeat/deviation`) made the oracle tests readable.
  Redemption should emit reasons the same way (`fulfilled/partial/queued/exhausted`).

### Action Items

- [ ] [Low] `Oracle.price` type hint `float | None` (fold into any later touch of oracle.py; not a task)
- 2026-10-02: Senior review APPROVE; status set to done. Threshold-0 semantics ratified as zero-lag oracle.
