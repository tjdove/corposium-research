# Story 1.4: Constant-Product AMM Module

Status: ready-for-dev

## Story

As a **researcher**,
I want a constant-product AMM with fees as a formal state machine,
so that pool price impact of attacker and arbitrageur trades is exact and testable.

## Acceptance Criteria

1. Carry-over: `ScenarioConfig` rejects `termination.max_steps: false` with a message stating that `steps.max_steps` is the mandatory safety cap; `tests/test_config.py` updated (the "nothing enabled" test becomes the `max_steps: false` test); all existing tests still pass
2. `src/depeg_sim/protocol/amm.py` defines `ConstantProductAMM(name="amm", reserve_stable, reserve_reference, fee_bps)` implementing `Subsystem`, `ActionTarget` and `PegView`
3. `quote(amount_in, side) -> Quote` is pure (no state change) and returns `amount_out, execution_price, spot_before, spot_after, slippage, fee_paid` for `side in {"sell_stable", "buy_stable"}`
4. `swap(amount_in, side) -> SwapResult` applies the fee-adjusted constant-product formula, updates reserves, and returns the same fields as `Quote` plus `reserves_stable_after, reserves_reference_after`
5. Invariant: after any swap, `reserve_stable * reserve_reference >= k_before` (fees accrue into reserves; k never decreases) — tested over 1,000 seeded random swaps from `ctx.rng`
6. `spot_price` property = `reserve_reference / reserve_stable` (reference per unit stable); `peg_deviation` property = `spot_price / peg_price - 1.0` where `peg_price` is injected at construction (default 1.0); this is the `PegView` the kernel's `peg_recovered` termination uses
7. `execute(ctx, action)` handles `action.kind == "swap"` with `params = {"amount_in": float, "side": str}`; emits a `swap_executed` event with the full `SwapResult` payload plus `action.source`; returns `ExecutionResult(ok=True, detail=payload)`; unknown `kind` → `ExecutionResult(ok=False, detail={"error": ...})` and a `swap_rejected` event (no exception)
8. Validation: `amount_in <= 0` rejected; `amount_in` that would drain a reserve to zero rejected (output capped so `reserve_out` stays `> 0`), both as `swap_rejected` events with reason strings; `fee_bps` outside `[0, 10000)` raises `ValueError` at construction
9. Hand-computed test: pool 1,000,000 / 1,000,000, fee 30 bps, `sell_stable` 1,000 → `amount_out == 996.006981…` (to 1e-9), `fee_paid == 3.0`, `spot_after < spot_before`, `slippage` matches `(execution_price - spot_before) / spot_before`
10. `snapshot()` returns `{"reserve_stable", "reserve_reference", "fee_bps", "k", "spot_price", "cumulative_fees"}`; `on_phase` is a no-op (AMM has no per-phase behaviour of its own); `phases == frozenset({Phase.EXECUTION})`
11. `AMMConfig` → module factory: `ConstantProductAMM.from_config(cfg: AMMConfig, peg_price: float)`
12. Integration test: register the AMM in a real `Engine` with `SourceStub` emitting one `swap` action per step; after N steps reserves have moved, `swap_executed` events == N, and `terminated_by == "max_steps"`; a `PegStub` is **not** registered — `peg_recovered` reads from the AMM
13. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Carry-over from 1.3 review (AC: 1)
  - [ ] Add `model_validator` on `ScenarioConfig` (or `TerminationConfig`): `max_steps` must be `True`
  - [ ] Rewrite `test_termination_nothing_enabled_rejected` → `test_termination_max_steps_false_rejected`; keep `test_termination_single_condition_accepted` meaningful (e.g. `reserves_exhausted: false, peg_recovered: null, max_steps: true` accepted)
  - [ ] Also assert the validator error message mentions "safety cap"

- [ ] AMM math and state (AC: 3, 4, 5, 6, 8)
  - [ ] `protocol/amm.py`: `Quote`, `SwapResult` frozen dataclasses; `ConstantProductAMM` class
  - [ ] Implement `_apply_fee(amount_in) -> (net_in, fee)`; `_out_for_in(net_in, r_in, r_out)`
  - [ ] `quote` and `swap` sharing one internal `_compute(amount_in, side)`
  - [ ] Reserve-drain guard; zero/negative guard
  - [ ] `spot_price`, `peg_deviation`, `k` properties; `cumulative_fees` counter
  - [ ] Tests: hand-computed case (AC 9); symmetry sanity (`buy_stable` moves spot up); invariant property test (AC 5); guards (AC 8)

- [ ] Subsystem contract (AC: 2, 7, 10, 11)
  - [ ] `name`, `phases`, `on_phase` no-op, `snapshot`, `execute`, `from_config`
  - [ ] `execute` → event emission via `ctx.events.emit(step, kind, source="amm", payload)`
  - [ ] Tests: `isinstance(amm, Subsystem/ActionTarget/PegView)`; execute happy path; unknown kind; rejected swap emits `swap_rejected` and returns `ok=False`

- [ ] Engine integration (AC: 12)
  - [ ] `tests/test_amm_integration.py` using `kernel_stubs.SourceStub` targeting `"amm"`
  - [ ] Second integration case: a source that sells stable every step until `peg_deviation` crosses a `PegRecoveredConfig` band is impossible to re-enter → confirm `peg_recovered` does *not* fire; then a scenario with no trades → `peg_recovered` fires at `for_steps`

- [ ] Tests, lint, close out (AC: 13)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 1.4: constant-product amm`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.3 (Status: done)**

- Subsystem contract: `name: str`, `phases: frozenset[Phase]`, `on_phase(ctx, phase)`,
  `snapshot() -> dict`. `ActionTarget` adds `execute(ctx, action) -> ExecutionResult`.
  `PegView` is a `peg_deviation: float` property. Protocols are `runtime_checkable`;
  `registry.find(PegView)` returns the first registered subsystem that has the attribute,
  so the AMM providing `peg_deviation` is enough.
- `on_phase` hooks run before the kernel routes actions in `EXECUTION`. The AMM does not
  need the hook; register for `EXECUTION` only so `by_phase` ordering stays trivial.
- Events: `ctx.events.emit(step=ctx.clock.step_index, kind=..., source=..., payload=dict)`.
- `KernelError` only for kernel-level misuse (unknown target). Domain rejections are
  `ExecutionResult(ok=False)` + an event, never exceptions. Agents in 1.7 will read the
  result.
- Stubs in `tests/kernel_stubs.py` (`SourceStub`, `TargetStub`, `PegStub`, …) are reusable.
- `termination.max_steps` becomes mandatory in this story (task 1).

[Source: docs/stories/1-3-simulation-kernel.md#Senior-Developer-Review]

### Architecture Alignment

This is the first **Protocol Model Layer** module. The spec's rule: a formal state machine
with explicit state, valid actions, execution rules, invariant checks, emitted events and
measurable outputs. Everything below maps to that.

| Spec item | Implementation |
|---|---|
| state | `reserve_stable`, `reserve_reference`, `fee_bps`, `cumulative_fees` |
| actions | `swap` (sides `sell_stable`, `buy_stable`) |
| execution rules | fee-adjusted constant product (below) |
| invariant | `k` non-decreasing |
| events | `swap_executed`, `swap_rejected` |
| outputs | `SwapResult`, `spot_price`, `peg_deviation`, `snapshot()` |

Liquidity add/remove is **out** for Epic 1 (pool depth is a static parameter swept across
runs; LP agent is an Epic 3 stretch). Do not add them.

### The math (normative)

Uniswap-V2 style, fee taken on input:

```
net_in  = amount_in * (1 - fee_bps / 10_000)
fee     = amount_in - net_in
out     = reserve_out * net_in / (reserve_in + net_in)
reserve_in  += amount_in          # fee stays in the pool
reserve_out -= out
execution_price (reference per stable):
    sell_stable: out / amount_in
    buy_stable:  amount_in / out
spot_before = reserve_reference / reserve_stable   (same definition after)
slippage    = (execution_price - spot_before) / spot_before   # negative when selling stable
```

Hand check for AC 9: `net_in = 997`, `out = 1_000_000 * 997 / 1_000_997 = 996.00698…`,
`fee = 3.0`. Use `math.isclose(..., rel_tol=1e-9)`.

**Floats, not Decimal.** Research-grade for our purposes means reproducible, not
wei-exact. Document in the module docstring that amounts are floats in token units and
that the Anvil replay (Epic 3 stretch) is where integer-exactness gets checked.

### Drain guard

If `out >= reserve_out`, reject rather than clamp: clamping would silently change the
trade size and make attacker PnL unattributable. Reason string: `"would drain reserve_out"`.
(In practice constant product never reaches zero, but floating point can; the guard makes
the contract explicit.)

### Events

```python
payload = {
    "source": action.source, "side": side, "amount_in": ..., "amount_out": ...,
    "execution_price": ..., "spot_before": ..., "spot_after": ..., "slippage": ...,
    "fee_paid": ..., "reserve_stable": ..., "reserve_reference": ...,
}
ctx.events.emit(step=ctx.clock.step_index, kind="swap_executed", source=self.name, payload=payload)
```

`swap_rejected` payload: `{"source", "side", "amount_in", "reason"}`.

### Peg deviation sign convention

`peg_deviation = spot_price / peg_price - 1.0`. Selling stable pushes `spot_price` (reference
per stable) **down**, so deviation goes **negative** under attack. Story 1.7's defender
triggers on `peg_deviation < -threshold_pct/100`. State the convention in the docstring;
it is easy to get backwards.

### Registration name

`name="amm"` is fixed; actions target `"amm"`. Story 1.8 registers exactly one.

### References

- [Source: docs/epics.md#Story-1.4]
- [Source: docs/stories/1-3-simulation-kernel.md#Interfaces]
- [Source: docs/CHARTER.md#4-Scope] — no LP actions in Epic 1
- Uniswap V2 whitepaper §3.2 (fee on input, k non-decreasing)

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-4-constant-product-amm.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output with exit codes)_

### Completion Notes List

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.3 review
