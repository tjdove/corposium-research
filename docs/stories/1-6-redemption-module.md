# Story 1.6: Redemption Module

Status: done

## Story

As a **researcher**,
I want a redemption facility with finite reserves, a spread, per-step capacity and a queue,
so that the "price promise" and its capacity limit are explicit state.

## Acceptance Criteria

1. `src/depeg_sim/protocol/redemption.py` defines `RedemptionModule(name="redemption", reserves, spread_bps, capacity_per_step, peg_price=1.0)` implementing `Subsystem`, `ActionTarget` and `ReservesView`; `phases == frozenset({Phase.EXECUTION, Phase.PROTOCOL_EVENTS})`
2. `execute(ctx, action)` handles `action.kind == "redeem"` with `params = {"amount_stable": float}`: validates `amount_stable > 0`, appends `(agent_id=action.source, amount_stable, step)` to a FIFO queue, emits `redeem_requested {source, amount_stable, queue_depth}`, returns `ExecutionResult(ok=True, detail={"queued": amount_stable, "queue_depth": n})`; invalid amount or unknown kind → `ok=False` + `redeem_rejected {source, reason}`
3. On `PROTOCOL_EVENTS` each step, `process(ctx)` fulfils the queue FIFO: for each request, `fill = min(remaining_request, remaining_capacity_this_step, reserves_affordable)` where a stable unit pays out `peg_price * (1 - spread_bps/10_000)` reference and `reserves_affordable = reserves / payout_per_unit`; reserves decrease by `fill * payout_per_unit`; partially filled requests stay at the head with the remainder; emits `redeem_fulfilled {source, amount_stable, paid_reference, remaining_request, reason}` with `reason in {"full", "partial_capacity", "partial_reserves"}`
4. `reserves_exhausted` (the `ReservesView` property) becomes `True` the first step at which `reserves <= 0` (or below `payout_per_unit` for one minimal unit, i.e. cannot pay anything) **and** the queue is non-empty; emits `reserves_exhausted {step, reserves, queue_depth, queued_total}` exactly once; stays `True` thereafter
5. Properties: `reserves`, `queue_depth` (count of pending requests), `queued_total` (sum of pending stable amounts), `fulfilled_total` (sum of stable fulfilled), `paid_total` (sum of reference paid), `spread_bps` (readable and settable via `set_spread_bps(bps)` for Story 1.7's defender; emits `spread_changed {old, new, source}`), `payout_per_unit`
6. Accounting invariant tested after every step of a randomised run: `fulfilled_total + queued_total == requested_total` (to 1e-9) and `paid_total == fulfilled_total * payout_per_unit_at_fill_time` accumulated (track paid per fill, not recomputed from current spread)
7. Per-step capacity is enforced across requests: with capacity 100 and three queued requests of 60, 60, 60 → step 1 fills 60 + 40 (partial), step 2 fills 20 + 60, step 3 fills 0 remaining; `reason` strings match
8. Reserves limit: with reserves 50 reference, payout 0.999 per unit, one request of 100 stable → fills `50/0.999 ≈ 50.05` stable with `reason == "partial_reserves"`, reserves hit 0, `reserves_exhausted` fires that step, request remainder stays queued
9. `snapshot()` returns `{reserves, spread_bps, capacity_per_step, peg_price, queue_depth, queued_total, fulfilled_total, paid_total, reserves_exhausted}`; `from_config(RedemptionConfig)`
10. Construction raises `ValueError` for `reserves < 0`, `spread_bps` outside `[0, 10_000)`, `capacity_per_step <= 0`, `peg_price <= 0`; execution never raises
11. Integration test: `Engine` with `redemption` + a `SourceStub` emitting one `redeem` of 30,000 stable per step, reserves 500,000, capacity 25,000, spread 10 bps, `max_steps 100`, `termination.reserves_exhausted: true` → `terminated_by == "reserves_exhausted"`, `steps_run` equals the first step at which reserves could no longer pay (assert the exact number computed from the parameters), `reserves_exhausted` event count is 1, and the run is identical on repeat
12. The `ReservesView` is found by `ctx.registry.find(ReservesView)` without registering any stub; a test proves `termination.check` reads it
13. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Module and queue (AC: 1, 2, 5, 9, 10)
  - [x] `protocol/redemption.py`: `RedemptionRequest` dataclass (mutable: `remaining` changes), `RedemptionModule`
  - [x] Constructor validation; `payout_per_unit` property; `set_spread_bps`
  - [x] `execute` → queue + `redeem_requested` / `redeem_rejected`
  - [x] `snapshot`, `from_config`
  - [x] Tests: construction guards; queue FIFO; rejection paths; snapshot keys; protocol `isinstance` checks (incl. `ReservesView` True, `PegView` False)

- [x] Processing (AC: 3, 4, 6, 7, 8)
  - [x] `on_phase(ctx, PROTOCOL_EVENTS)` → `process(ctx)`
  - [x] Capacity accounting per step; partial fills keep remainder at head
  - [x] Reserves-affordable logic; exhaustion flag + single event
  - [x] Tests: AC 7 table case; AC 8 reserves case; invariant over 200 random steps using `numpy.random.default_rng(99)` for request sizes; exhaustion fires once and latches

- [x] Kernel integration (AC: 11, 12)
  - [x] `tests/test_redemption_integration.py`
  - [x] Compute expected `steps_run` in the test from parameters (do not hard-code a magic number without the formula in a comment)

- [x] Tests, lint, close out (AC: 13)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] `python run.py scenarios/soros-baseline.yaml` (unchanged output)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 1.6: redemption module`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.5 (Status: done)**

- Hybrid subsystem pattern: `ActionTarget` for requests (`EXECUTION`) **and** a hook
  (`PROTOCOL_EVENTS`) for settlement. The kernel calls `on_phase(EXECUTION)` before routing
  actions; redemption needs nothing there, so `on_phase` should early-return unless the phase
  is `PROTOCOL_EVENTS`.
- Reason strings in event payloads (`full/partial_capacity/partial_reserves`) keep tests
  readable and will show up in decision traces.
- Construction validates and raises; execution/hooks never raise for domain reasons.
- `registry.find(ReservesView)` returns the first subsystem with a `reserves_exhausted`
  attribute. Register exactly one redemption module.
- Allow-lists in context files name intent; fixing a test elsewhere that your change broke
  is in scope.

[Source: docs/stories/1-5-oracle-and-environment.md#Senior-Developer-Review]

### Architecture Alignment

This module *is* the Soros thesis in code. The redemption facility is the price promise: "one
stable unit is worth `peg_price` reference, and we will honour that on demand." The reserves
are the Bank of England's foreign-currency reserves. `capacity_per_step` is the operational
throughput of the defense. `spread_bps` is the small haircut the promise charges. The queue is
what builds when demand exceeds capacity. `reserves_exhausted` is Black Wednesday.

Spec mapping (Protocol Model Layer, Redemption module):

| Spec | Implementation |
|---|---|
| state: treasury reserves, redemption spread, queue depth, per-step capacity | `reserves`, `spread_bps`, queue, `capacity_per_step` |
| actions: redeem stable token, consume reserves, queue if capacity constrained | `execute("redeem")`, `process()` |
| outputs: reserves remaining, fulfilment time, queue growth | properties + `redeem_fulfilled.step - request.step` |

### Settlement rule (normative)

```
on PROTOCOL_EVENTS at step s:
    cap = capacity_per_step
    ppu = peg_price * (1 - spread_bps / 10_000)      # reference paid per stable unit
    while queue and cap > 0 and reserves > 0:
        req = queue[0]
        affordable = reserves / ppu
        fill = min(req.remaining, cap, affordable)
        if fill <= 0: break
        paid = fill * ppu
        reserves -= paid ; cap -= fill
        req.remaining -= fill
        fulfilled_total += fill ; paid_total += paid
        reason = "full" if req.remaining == 0 (within 1e-12)
                 else "partial_reserves" if fill == affordable (reserves now ~0)
                 else "partial_capacity"
        emit redeem_fulfilled {...}
        if req.remaining == 0: queue.popleft()
    if not exhausted and queue and reserves < ppu * 1e-9 (effectively zero):
        exhausted = True ; emit reserves_exhausted {...}
```

Use `collections.deque`. Clamp tiny float residue: treat `req.remaining < 1e-12` as zero.

**Capacity is stable units per step**, not reference. Document it; Epic 2 calibrates it to
real on-chain redemption throughput (e.g. Circle's daily mint/burn processed per 12-second
slot), so units matter.

### Why spread is settable

Story 1.7's defender has a `spread_adjust_bps` policy: widening the spread under attack
raises the cost of redemption, which is one of the three defensive levers the spec names
("adjust redemption spreads"). `set_spread_bps` must emit `spread_changed` so decision
traces and charts can show when the defender pulled that lever. Paid amounts already
recorded must not change retroactively (hence AC 6's "at fill time").

### Exhaustion semantics

`reserves_exhausted` requires **both** empty reserves and pending demand. Empty reserves
with an empty queue is not a failure; it is a defense that spent everything and was not
tested further. Termination (1.3) reads the flag; the kernel emits `run_terminated` with
reason `reserves_exhausted` the same step.

### AC 11 expected step (worked)

Reserves 500,000 reference; ppu = 0.999; affordable stable = 500,500.5. Capacity 25,000/step;
requests 30,000/step. Each step fills 25,000, backlog grows 5,000/step. Reserves run out
after `500,500.5 / 25,000 = 20.02` steps → step index 20 fills the last 500.5 then can pay
nothing more; queue non-empty → exhausted at step 20; `steps_run == 21`. Put this arithmetic
in the test as comments and compute it, don't hard-code 21.

### References

- [Source: docs/epics.md#Story-1.6]
- [Source: docs/stories/1-3-simulation-kernel.md#Interfaces] — `ReservesView`
- [Source: docs/stories/1-5-oracle-and-environment.md#Senior-Developer-Review]
- [Source: docs/CHARTER.md#1-Mission] — "a peg is a price promise"

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-6-redemption-module.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

```
$ pytest; echo exit=$?
232 passed in 0.45s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
40 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml; echo exit=$?
depeg-sim: scenario=soros-baseline seed=42 hash=7c4f870b2d8a
run: steps=5000 terminated_by=max_steps
exit=0

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/protocol/redemption.py           137      1    99%   233
TOTAL                                          764      3    99%
```

193 → 232 tests (+39: 35 collected from `test_redemption.py` including parametrized
cases, 4 from `test_redemption_integration.py`). CLI output is
identical to the Story 1.5 record; the CLI does not register the module yet.

CI on push of `01080bc`:

```
$ gh run list --limit 1
completed	success	story 1.6: redemption module	ci	main	push	37017835481	33s	2026-10-02T14:08:56Z
```

### Completion Notes List

- **`set_spread_bps` takes `ctx` first: `set_spread_bps(ctx, bps, source="redemption")`.**
  The context interface lists `set_spread_bps(bps, source)`, but AC 5 requires it to emit
  `spread_changed`, and emitting needs the event sink and the step. Every other emitting
  method here (`execute`, `process`) takes `ctx` first, so I followed that. It raises
  `ValueError` for `bps` outside `[0, 10_000)` (a direct-call API, not `execute`/`on_phase`).
  It emits on every call, including a call that sets the same value, so traces show each
  time the lever was pulled. Story 1.7's defender has `ctx` in `decide`, so this should fit.
- **Reserves-limited fills pay exactly the remaining reserves** and set `reserves = 0.0`,
  rather than `reserves -= fill * ppu`. That removes float residue (which would leave
  tiny positive reserves and cause repeated tiny fills). `paid` differs from `fill * ppu` by
  at most an ulp. `paid_total` is the sum of per-fill `paid`, exactly equal in the invariant
  test.
- **Reason precedence:** `full` if the remainder is under 1e-12 (then clamped to 0), else
  `partial_reserves` if reserves are now 0, else `partial_capacity`. Capacity residue under
  1e-12 also ends the step's loop.
- **Exhaustion threshold** is `reserves < ppu * 1e-9` with a non-empty queue, checked after
  the settlement loop, as in the normative block. Tested: empty reserves + empty queue is
  not exhausted; exact spend-down with an empty queue is not exhausted; demand arriving
  later against empty reserves is; event fires once and latches.
- **Additions beyond the ACs** (small, read-only): `requested_total` property (AC 6 names
  it), `pending` (copy of the queue for tests), and `step_requested` in the
  `redeem_fulfilled` payload so fulfilment time (spec output) can be computed from one
  event. The snapshot has exactly the AC 9 keys.
- **AC 11 arithmetic** is in `expected_exhaustion_step()` in
  `tests/test_redemption_integration.py`: `ceil((500_000 / 0.999) / 25_000) - 1 = 20`, so
  `steps_run == 21`, computed in the test. The test also checks every step before 20 fills
  exactly 25,000, step 20 fills `500_500.5 - 20 * 25_000` with `partial_reserves`, and
  `run_terminated` fires at step 20.
- `spread_bps` must be an `int` (bools and floats rejected). `RedemptionConfig.spread_bps`
  is an int, so `from_config` is unaffected.
- The single uncovered line (233) is the normative `if fill <= 0: break` guard. The loop
  guards make it unreachable in practice; kept as written in the Dev Notes.
- No tests elsewhere broke; no other files changed.

### File List

**Created:**

- `src/depeg_sim/protocol/redemption.py`
- `tests/test_redemption.py`
- `tests/test_redemption_integration.py`

**Modified:**

- `docs/stories/1-6-redemption-module.md`

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.5 review
- 2026-10-02: Implemented by Claude Code (Opus 5.5); 232 tests pass; status → review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-02
**Outcome:** **APPROVE** ✅

### Summary

The price promise is now explicit state. Reviewer re-ran on a separate machine: 232 passed,
ruff clean; an independent engine run with the baseline redemption parameters and a
30,000/step redeem stream terminated by `reserves_exhausted` at `steps_run == 21` with
exactly one exhaustion event, `reserves == 0.0`, queued backlog 129,499.5 stable, the
accounting identity holding, repeat-run identical, `ReservesView` True and `PegView` False.
CI run 37017987294 green. Module at 99% (the unreachable `fill <= 0` guard).

### Rulings on the flagged items

1. **`set_spread_bps(ctx, bps, source)` — ctx first.** Correct; the context file's signature
   omitted `ctx` and the method cannot emit without it. **Ratified.** Standard from here:
   any subsystem method that emits takes `ctx` as its first argument.
2. **Last reserve-limited fill pays out exactly the remainder and sets reserves to `0.0`.**
   Right call; avoids float dust producing repeated micro-fills. `paid_total` as the exact
   sum of recorded payouts is the correct bookkeeping. **Ratified.**
3. **`requested_total`, read-only `pending`, `step_requested` in `redeem_fulfilled`.** All
   useful, all read-only, snapshot keys unchanged. **Ratified.** `step_requested` in the
   fulfilment event gives fulfilment latency from one event, which the 1.8 metrics will use.
4. **`spread_changed` emitted even when unchanged.** Acceptable but noisy for decision
   traces. **Decision:** the *caller* avoids no-op calls; Story 1.7's defender only calls
   `set_spread_bps` when the target differs from the current value. No change to this module.
5. **Exhaustion step computed as `ceil(500_000/0.999/25_000) − 1 = 20` → `steps_run 21`.**
   Matches the Dev Notes working and the reviewer's run. **Ratified.**

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1 | ✅ | Class, three protocols, `phases == {EXECUTION, PROTOCOL_EVENTS}` |
| 2 | ✅ | `execute("redeem")` queues; `redeem_requested`/`redeem_rejected` |
| 3 | ✅ | FIFO settlement with reason strings; partial remainder stays at head |
| 4 | ✅ | Exhaustion requires both; latches; one event (reviewer: count 1) |
| 5 | ✅ | All properties; `set_spread_bps` emits `spread_changed` |
| 6 | ✅ | 200-step randomised invariant; paid at fill time |
| 7 | ✅ | 60/60/60 capacity-100 table case with reasons |
| 8 | ✅ | Reserves-50 case: ≈50.05 fill, `partial_reserves`, exhaustion fires |
| 9 | ✅ | Snapshot keys exact; `from_config` |
| 10 | ✅ | Construction guards; no domain exceptions in execution |
| 11 | ✅ | Integration: computed 21, one event, repeat identical (reviewer reproduced) |
| 12 | ✅ | `registry.find(ReservesView)`; `termination.check` reads it |
| 13 | ✅ | `232 passed`, `All checks passed!`, CI green |

**13 of 13 ACs met.**

### Key Findings

No High or Medium issues. No Low items requiring action.

### Learnings for Story 1.7

- Three `ActionTarget`s now exist for agents to address: `amm` (`swap`), `redemption`
  (`redeem`). Agents are `ActionSource`s; `decide(ctx)` returns `Action(source=agent_id,
  target=..., kind=..., params=...)`.
- Agents observe via the registry: `ctx.registry.get("amm").spot_price`,
  `ctx.registry.get("oracle").price`, `ctx.registry.get("redemption").payout_per_unit`.
  Observation happens in `decide`; the `STATE_OBSERVATION` phase hook is available if an
  agent wants to cache a view before deciding.
- `ExecutionResult` is returned by `execute()` to the kernel, not to the agent. Agents
  learn outcomes from events or by re-observing next step. (The kernel discards the result
  today; 1.7 may add `ctx.last_results` if PnL needs it — see 1.7 Dev Notes.)
- Methods that emit take `ctx` first.
- 2026-10-02: Senior review APPROVE; status set to done. ctx-first signature standard ratified.
