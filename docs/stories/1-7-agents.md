# Story 1.7: Attacker, Arbitrageur and Defender Agents

Status: review

## Story

As a **researcher**,
I want the three core agents with explicit, parameterised policies and decision traces,
so that every action in a run can be explained by a rule and a threshold.

## Acceptance Criteria

1. Kernel addition (no domain logic): `RunContext.execution_results: list[tuple[Action, ExecutionResult]]` is cleared with the action queue at the start of `AGENT_DECISION` and appended by the engine in `EXECUTION` as each action is routed; `PHASE_ORDER_VERSION` unchanged; existing kernel tests still pass; one new engine test asserts results are recorded in queue order
2. `src/depeg_sim/agents/base.py` defines `Agent` (an `ActionSource` with `phases == {STATE_OBSERVATION, AGENT_DECISION, METRIC_UPDATE}`): `agent_id`, `balances: dict[str, float]` with keys `"stable"` and `"reference"`, `initial_value` (reference-denominated at `peg_price`), `observe(ctx) -> dict` (called in `STATE_OBSERVATION`, result cached as `self.last_obs`), `decide(ctx) -> list[Action]`, `settle(ctx)` (called in `METRIC_UPDATE`; applies this step's own swap results from `ctx.execution_results` and own `redeem_fulfilled` events to balances), `mark_to_market(ctx) -> float` (= `reference + stable * amm.spot_price`), `pnl(ctx) -> float` (= `mark_to_market − initial_value`), `record(ctx, rule, observed, action)` which appends to `ctx.decisions` only when `config.metrics.trace_decisions`
3. `agents/attacker.py`: `Attacker(agent_id, capital, start_step, pace, stop_below_price)` starts with `balances = {stable: capital, reference: 0}`; from `start_step`, each step sells `pace * stable_balance` into the AMM (`sell_stable`) unless `stable_balance < 1e-9` or (`stop_below_price` set and `amm.spot_price < stop_below_price`); records rule `"attack_dump"` / `"attack_stop_price"` / `"attack_exhausted"` / `"attack_waiting"`
4. `agents/arbitrageur.py`: `Arbitrageur(agent_id, capital, min_profit_bps, latency_steps)` starts with `balances = {stable: 0, reference: capital}`; in `observe` it compares `amm.spot_price` to `oracle.price` and computes a plan: if `spot < oracle * (1 − (fee_bps + min_profit_bps)/10_000)` → **buy stable** on the AMM with `x = min(reference_balance, sqrt(k · oracle) − R)` reference (closed form that restores spot to the oracle price); if `spot > oracle * (1 + (fee_bps + min_profit_bps)/10_000)` and `stable_balance > 0` → **sell stable** `y = min(stable_balance, sqrt(k / oracle) − S)`; additionally, whenever `stable_balance > 0` and `redemption.payout_per_unit > spot` → **redeem** all stable instead of selling; plans execute in `decide` only once `plan.step + latency_steps <= current step` (FIFO of pending plans; a new observation replaces an unexecuted plan of the same kind); rules `"arb_buy_amm"`, `"arb_sell_amm"`, `"arb_redeem"`, `"arb_idle"`, `"arb_waiting_latency"`
5. `agents/defender.py`: `Defender(agent_id, budget, threshold_pct, spend_pace, spread_adjust_bps, max_spend)` starts with `balances = {stable: 0, reference: budget}`; when `amm.peg_deviation < −threshold_pct/100` it **buys stable** with `x = min(spend_pace * reference_balance, sqrt(k · peg_price) − R, max_spend − spent)` (skip if `x <= 0`); if `spread_adjust_bps > 0` and the current redemption spread differs from `base_spread + spread_adjust_bps`, it calls `redemption.set_spread_bps(ctx, base + adjust, source=agent_id)` **once** on entering defense and restores `base_spread` once when deviation returns within band; tracks `spent` (reference) and `interventions` (count of buy actions); rules `"defend_buy"`, `"defend_spread_widen"`, `"defend_spread_restore"`, `"defend_budget_exhausted"`, `"defend_idle"`
6. All three register from config: `agents/factory.py` → `build_agents(config: ScenarioConfig) -> list[Agent]` in config order, dispatching on `AgentConfig.type`; agent `name == agent_id`
7. `settle` correctness, tested with a real AMM in a real engine: after an attacker `sell_stable` of 1,000, attacker `stable` decreases by 1,000 and `reference` increases by the `amount_out` in the matching `swap_executed` event; after an arbitrageur `redeem` fulfilment, its `stable` decreases by the fulfilled amount and `reference` increases by `paid_reference`
8. Per-agent tests with a real AMM and oracle (no engine, call phases manually): attacker waits before `start_step`, sells at `pace` fraction, stops at `stop_below_price`, records `attack_exhausted` when out of stable; arbitrageur does nothing inside the band, buys outside it, honours `latency_steps` (plan at step 3 with latency 2 executes at step 5), prefers redeem when `payout_per_unit > spot`; defender does nothing above threshold, buys below it, never exceeds `max_spend`, widens spread once and restores once; closed-form sizing restores spot to target within 1e-9 relative when uncapped
9. Decision trace: with `trace_decisions: true` every `decide` call records exactly one `Decision` per agent per step (including idle rules); with `false` none are recorded; `Decision.observed` includes at least `spot_price`, `oracle_price`, `peg_deviation`, and the agent's balances
10. Full-scenario integration test: `Engine` with environment, oracle, AMM, redemption and the three baseline agents (from `scenarios/soros-baseline.yaml`), `max_steps 300` → attacker's `stable` balance strictly decreases after `start_step`; at least one defender `defend_buy` decision occurs; at least one arbitrageur non-idle decision occurs; the run is identical on repeat; `terminated_by` is one of the three conditions (assert which, from the actual baseline parameters, and put the reasoning in a comment)
11. `snapshot()` on each agent returns `{agent_id, type, balances, initial_value, pnl_last}` plus type-specific fields (`attacker`: `sold_total`; `arbitrageur`: `pending_plans`; `defender`: `spent, interventions, spread_widened`)
12. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Kernel: execution results (AC: 1)
  - [x] `context.py`: `execution_results` list; `engine.py`: clear at `AGENT_DECISION`, append in `_route`
  - [x] `test_engine.py`: results recorded in queue order; cleared each step

- [x] Agent base (AC: 2, 9, 11)
  - [x] `agents/base.py`: `Agent` ABC with the contract above; `_amm(ctx)`, `_oracle(ctx)`, `_redemption(ctx)` helpers via `ctx.registry.get`
  - [x] `settle`: iterate `ctx.execution_results` for `action.source == agent_id` and `kind == "swap"` with `ok`; iterate this step's events for `kind == "redeem_fulfilled"` and `payload["source"] == agent_id` (add `EventSink.at_step(step)` helper in `events.py` if absent — returns events with that step; keep it O(tail))
  - [x] `record` gated on `ctx.config.metrics.trace_decisions`
  - [x] Tests: balances arithmetic with a scripted `execution_results`; trace gating

- [x] Attacker (AC: 3, 8)
  - [x] `agents/attacker.py`; tests per AC 8

- [x] Arbitrageur (AC: 4, 8)
  - [x] `agents/arbitrageur.py`; closed-form sizing helpers `_reference_to_reach(k, R, target)` and `_stable_to_reach(k, S, target)`; latency plan queue; tests per AC 8 incl. sizing precision

- [x] Defender (AC: 5, 8)
  - [x] `agents/defender.py`; spread widen/restore state machine; tests per AC 8

- [x] Factory and settle verification (AC: 6, 7)
  - [x] `agents/factory.py`; `test_agents_factory.py` (three types, order preserved, unknown type impossible by config)
  - [x] `test_agents_settle.py` with real AMM + redemption in an engine

- [x] Full integration (AC: 10)
  - [x] `tests/test_agents_integration.py` on the baseline scenario; repeat-run equality

- [x] Tests, lint, close out (AC: 12)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] `python run.py scenarios/soros-baseline.yaml` (unchanged; CLI registration is 1.8)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 1.7: attacker, arbitrageur and defender agents`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.6 (Status: done)**

- Targets available: `amm` (`swap`: `amount_in`, `side`), `redemption` (`redeem`: `amount_stable`).
- Methods that emit take `ctx` first: `redemption.set_spread_bps(ctx, bps, source=...)`.
- `spread_changed` fires on every call; the defender must only call when the value differs.
- `ExecutionResult` goes to the kernel, not the agent — hence AC 1's `execution_results`.
- Redemption fills happen in `PROTOCOL_EVENTS` (after `EXECUTION`), so an agent that
  redeems at step *s* sees the fill event at step *s* and can settle it in `METRIC_UPDATE`
  of the same step.

[Source: docs/stories/1-6-redemption-module.md#Senior-Developer-Review]

### Architecture Alignment

Agent Layer per the spec: structured actors with objectives, capital constraints,
holdings, information access, latency, strategy rules and risk thresholds. "Not free-form
AI personalities." Every `decide` is a rule lookup, and every rule has a name that lands in
the decision trace. The research value is in heterogeneity across *runs* (the sweep), not
cleverness within one agent.

Phase usage per agent:

| Phase | Agent does |
|---|---|
| `STATE_OBSERVATION` | `observe(ctx)` → `last_obs` (prices, balances, deviation) |
| `AGENT_DECISION` | `decide(ctx)` → actions; `record(...)` |
| `METRIC_UPDATE` | `settle(ctx)` → balances from this step's results/events |

Agents never touch protocol state directly; they only read it and emit actions. The one
exception is the defender's `set_spread_bps`, which is a policy lever the spec explicitly
names ("adjust redemption spreads"), and it goes through the module's method so it emits.

### The Soros mapping

- **Attacker** = Soros. Holds a large borrowed stable position (we model it as starting
  stable balance; the borrow is off-model) and dumps it at a pace. Its PnL in Epic 1 is the
  *cost* of the attack (negative), because v1 never buys back. That is deliberate: the
  question is whether the defense breaks, not whether the attacker profits. Epic 3 may add
  a buy-back leg.
- **Arbitrageur** = the market. Reacts to the gap between the AMM price and the oracle
  (lagged) price, and to the gap between AMM price and the redemption payout. Its latency
  is the "reaction time of the market."
- **Defender** = Bank of England. Spends reserves (reference) buying stable on the AMM to
  hold the price, and can raise the redemption spread (= raise interest rates: make the
  promise costlier to call). Budget is finite. `max_spend` is political will.

### Closed-form sizing (normative)

Constant product `k = S·R`, spot `p = R/S` (reference per stable).

- To move spot **up** to target `p₁` by buying stable with `x` reference (ignoring fee for
  sizing; the fee makes the result slightly undershoot, which is acceptable and documented):
  `x = sqrt(k · p₁) − R`
- To move spot **down** to `p₁` by selling `y` stable: `y = sqrt(k / p₁) − S`

Both are clamped at 0 and at the agent's balance. Test the uncapped case against a real
AMM: after the swap, `abs(spot_after / p₁ − 1) < 1e-9` **when fee_bps = 0**; with fee 30 bps
assert `spot_after` is within 0.5% of target and on the correct side.

### Arbitrage band

The arbitrageur trades only when the gap exceeds fees plus its required profit:
`gap_bps = (spot / oracle − 1) · 10_000`; act when `abs(gap_bps) > fee_bps + min_profit_bps`.
Use the AMM's `fee_bps` (read it from the module), not a hard-coded 30.

Redeem route: if the agent holds stable and `redemption.payout_per_unit > amm.spot_price`,
redeeming is strictly better than selling on the AMM (before considering queue delay, which
v1 ignores). It redeems **all** stable in one action; capacity limits will queue it.

### Defender band and hysteresis

Enter defense when `peg_deviation < −threshold_pct/100`. Widen spread on entry (if
configured). Restore when `peg_deviation >= −threshold_pct/100` again. No hysteresis band in
v1; if that chatters in Epic 2 sweeps, add a `restore_threshold_pct` then.

`spent` counts reference actually sent to the AMM (the `amount_in` of its own `swap_executed`
results), not planned spend.

### Decision record shape

```python
ctx.decisions.record(
    step=ctx.clock.step_index, agent_id=self.agent_id, rule="defend_buy",
    observed={"spot_price": ..., "oracle_price": ..., "peg_deviation": ..., "balances": {...}, ...},
    action={"target": "amm", "kind": "swap", "params": {...}} or None,
)
```

Exactly one record per agent per step when tracing (idle included). Multiple actions in one
step (defender widen + buy) → one record whose `action` is a list.

### Expected baseline behaviour (for AC 10's comment)

Baseline: attacker 300k stable at pace 0.1 from step 50 into a 1M/1M pool; defender 400k at
threshold 1%, pace 0.2; redemption 500k reserves, capacity 25k/step; arbitrageur 200k,
20 bps, latency 1; oracle heartbeat 25 / 0.5%; environment flat. Work out qualitatively in
the test comment which termination fires by step 300 and assert it. If the answer surprises
you, that is a finding, not a bug — record it in Completion Notes.

### References

- [Source: docs/epics.md#Story-1.7]
- [Source: docs/stories/1-3-simulation-kernel.md#Interfaces]
- [Source: docs/stories/1-4-constant-product-amm.md#Dev-Notes] — sign convention
- [Source: docs/stories/1-6-redemption-module.md#Senior-Developer-Review]
- [Source: docs/CHARTER.md#1-Mission]

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-7-agents.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

Task 1 (`2694cc0`). The baseline before it is 232 passing, per Story 1.6's Debug Log;
not re-run here:

```
$ pytest; echo exit=$?   # after task 1
233 passed in 0.45s
exit=0
```

Final:

```
$ pytest; echo exit=$?
296 passed in 0.60s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
53 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml; echo exit=$?
depeg-sim: scenario=soros-baseline seed=42 hash=7c4f870b2d8a
run: steps=5000 terminated_by=max_steps
exit=0

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/agents/arbitrageur.py             99      2    98%   105, 147
src/depeg_sim/agents/attacker.py                42      0   100%
src/depeg_sim/agents/base.py                    84      3    96%   62, 64, 199
src/depeg_sim/agents/defender.py                81      0   100%
src/depeg_sim/agents/factory.py                 18      0   100%
src/depeg_sim/kernel/engine.py                  73      0   100%
src/depeg_sim/kernel/events.py                  48      0   100%
TOTAL                                         1099      7    99%
```

232 → 296 tests (+64): 1 engine (task 1), 1 `EventSink.at_step`, 62 across the agent
test files. CLI output is identical to the Story 1.6 record; agents are not registered by
the CLI yet (1.8).

Baseline 300-step run, exploratory script (same setup as `test_agents_integration.py`):

```
terminated_by=max_steps steps_run=300
spot: step 49 1.0 | 50 0.94268 | 52 1.00439 | 100 0.99562 | 150..299 0.99817
steps with |deviation| <= 0.1%: 0-49, then scattered up to 111, none after
last defend_buy step 77 (16 buys, spent 200,656 of 400,000)
last arbitrageur trade step 114 (12 buys, 12 redeems, 1 sell)
redemption: 90,990 stable fulfilled, reserves 409,101 left, never exhausted
same scenario at max_steps 5000: terminated_by=max_steps
```

### Completion Notes List

- **AC 10 / research finding: the baseline never recovers the peg; `max_steps` fires.**
  I ran the scenario before writing the assertion, so the reasoning comment in
  `tests/test_agents_integration.py` explains an observed result. It was not a blind
  prediction. The attack is absorbed within ~60 steps (min spot 0.943 at step 50; the
  defender's last buy is step 77). After that the pool parks at ~0.9982 (-18 bps). That
  is inside the arbitrage band (fee 30 + min profit 20 = 50 bps) and above the defender's
  -1% trigger, so no agent has a rule that moves it. `peg_recovered` needs
  |deviation| <= 10 bps for 100 steps, which is tighter than the no-arbitrage band, so it
  can't fire once an attack has moved the price. It still hasn't fired at 5000 steps.
  Two consequences for Epic 2 calibration:
  (a) `peg_recovered.tolerance` must be >= the arbitrage band to be reachable, or there
  has to be a force inside the band (e.g. redemption at 0.999 arbitraged against an AMM
  above 0.999). With the current parameters, buy-then-redeem loses fee + spread = 40 bps.
  (b) Before the attack the pool sits at peg for 50 steps (0-49). With
  `start_step >= 100` the run would end `peg_recovered` before the attacker ever acts.
  The reserves were never under real pressure: 91k of 500k paid out.
- **`Decision.action` for multi-action steps is `{"actions": [...]}`, not a bare list.**
  `DecisionTrace.record` does `dict(action)` and `Decision.action` is typed `Mapping`.
  The context allows no kernel changes beyond task 1 and `at_step`, so `Agent.record`
  wraps a list. Only the defender's widen+buy step produces one.
- **Defender widen step rule.** The step that widens the spread is recorded as
  `defend_spread_widen` (action list `[spread change, buy]` when it also buys). Later
  defense steps record `defend_buy`. So `interventions` can exceed the count of
  `defend_buy` records by one when the spread lever is configured. `interventions` and
  `spent` count executed buys (from `execution_results`), not planned ones. The spread
  target is capped at 9,999 bps. The defender captures `base_spread` at the moment it
  widens and restores that value. It calls `set_spread_bps` only when the value would
  change.
- **Arbitrageur latency semantics (interpretation).** Each opportunity becomes a plan
  stamped with the step it was first seen. A later observation of the same kind refreshes
  the size but keeps the original step. Otherwise a persistent opportunity would reset its
  clock every step and never execute when `latency_steps >= 1`. An observation that no
  longer sees that kind drops the plan, so the market doesn't trade on a gap that closed
  before it reacted. At most one plan executes per step, FIFO. Size is clamped to the
  balance at execution. Within one observation the redeem plan is created before the buy
  plan, so a held position is redeemed first (tested).
- **Queued redemptions.** Stable queued for redemption stays in `balances["stable"]`
  until filled (AC 7 semantics) and is tracked in `queued_redeem`, set from the agent's
  own `ok` redeem results in `settle`. The arbitrageur redeems only `available_stable`
  (= stable − queued), so queued stable is never redeemed twice. A test shows the
  arbitrageur recycling redemption proceeds: it buys on the AMM, then redeems only the
  new stable.
- **Redeem route without an oracle.** The redeem check (`payout_per_unit > spot`) doesn't
  need an oracle price. AMM buy/sell plans do, and are skipped while `oracle.price` is
  None. `observe` tolerates missing modules (values `None`), which lets the AC 7 settle
  tests run in an engine with only the modules they need.
- `decide` uses `last_obs` from `STATE_OBSERVATION` (nothing changes the pool between
  observation and decision). `pnl_last` is updated in `settle` so `snapshot()` needs no
  ctx. `initial_value` uses `config.redemption.peg_price` (factory).
- `EventSink.at_step(step)` added to `kernel/events.py` (allowed by the context). It scans
  from the tail and stops at the first earlier step.
- Agent unit tests use `tests/agent_world.py` (new helper, test-only). It wires a real
  `ScriptedPriceSource`, `Oracle`, `ConstantProductAMM` and `RedemptionModule` and runs a
  step by hand in phase order. `World.set_spot` resets pool reserves directly to place
  spot (test-only).
- Uncovered lines are defensive: empty `agent_id`, bad `peg_price`, abstract `decide`
  body, a ready plan whose clamped size is dust, and the `amm is None` early return.
- No existing tests broke. `tests/test_engine.py` and `tests/test_events.py` gained one
  test each.

### File List

**Created:**

- `src/depeg_sim/agents/base.py`
- `src/depeg_sim/agents/attacker.py`
- `src/depeg_sim/agents/arbitrageur.py`
- `src/depeg_sim/agents/defender.py`
- `src/depeg_sim/agents/factory.py`
- `tests/agent_world.py`
- `tests/test_agents_base.py`
- `tests/test_attacker.py`
- `tests/test_arbitrageur.py`
- `tests/test_defender.py`
- `tests/test_agents_factory.py`
- `tests/test_agents_settle.py`
- `tests/test_agents_integration.py`

**Modified:**

- `src/depeg_sim/kernel/context.py` (task 1: `execution_results`)
- `src/depeg_sim/kernel/engine.py` (task 1: clear at `AGENT_DECISION`, append in `_route`)
- `src/depeg_sim/kernel/events.py` (`EventSink.at_step`)
- `tests/test_engine.py`, `tests/test_events.py`
- `docs/stories/1-7-agents.md`

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.6 review
- 2026-10-02: Implemented by Claude Code (Opus 5.5); 296 tests pass; baseline 300-step run ends `max_steps` (finding in Completion Notes); status → review
