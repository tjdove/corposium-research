# Story 3.8 (stretch): LP Withdrawal Agent

Status: ready-for-dev

## Story

As a **researcher**,
I want liquidity providers who pull their liquidity when the peg looks lost,
so that pool depth becomes endogenous and the note can say what reflexive liquidity flight does to the thresholds the surfaces drew with depth held fixed.

## Acceptance Criteria

1. **AMM: `remove_liquidity`.** `AMM` gains `remove_liquidity(fraction) -> LiquidityResult` (0 < fraction ≤ 1): both reserves scale by `1 − fraction` (spot price unchanged, `k` scales by `(1 − fraction)²`), returns the stable and reference withdrawn; `execute` accepts `kind == "remove_liquidity"` with `params = {"fraction": f}`, emits `liquidity_removed {source, fraction, stable_out, reference_out, reserve_stable, reserve_reference}` or `liquidity_rejected`; the drain guard (reserves never reach zero) applies; existing swap behaviour byte-identical (run-vs-rerun fixtures untouched); the `k`-non-decreasing property test is amended to "non-decreasing between liquidity events" and a new test pins the scaling
2. **Agent.** `agents/lp.py`: `LiquidityProvider(agent_id, share, panic_threshold_pct, pace)` extending `Agent`: owns `share` (0 < share ≤ 1) of the pool at start; each step while `amm.peg_deviation < −panic_threshold_pct/100` and it still has share, submits `remove_liquidity` for `min(pace × share_remaining, share_remaining)` as a fraction **of the current pool** (`fraction = removed_share / total_share_remaining_in_pool`, document the arithmetic); one-way: it never re-adds; rules `lp_hold`, `lp_withdraw`, `lp_done`; PnL marks withdrawn reserves at spot; never calls `ctx.rng`; `LPConfig(type: "lp", id, share, panic_threshold_pct, pace)` in the `AgentConfig` union; `build_agents` dispatch; every existing scenario `content_hash()` unchanged (test)
3. Tests per the 1.7 pattern: holds above the threshold; withdraws at pace below it; stops at zero share; price unchanged by a withdrawal; `k` scales; a swap after a withdrawal has larger impact; decision records
4. **Scenario:** `scenarios/calibrated-baseline-lp.yaml` — `calibrated-baseline-ou.yaml` plus an LP with `share 0.5` (half the pool is flighty), `panic_threshold_pct 5`, `pace 0.1`; header states these as assumptions and why 5% (above the holder's 2% entry, below the trough at calibrated depth); `python run.py`; before/after against `calibrated-baseline-ou` in Completion Notes (trough, time-to-parity, defender spend, pool depth at the trough)
5. **Sweep:** `sweeps/lp-flight-mc.yaml` — base the LP scenario, par criterion; axes `agents[type=lp].panic_threshold_pct ∈ {2, 5, 10, 20}` × `agents[type=lp].share ∈ {0.25, 0.5, 0.75}` × attacker ratio `{0.5, 0.7, 1.0}`; 8 seeds; `plot_lp_flight(sweep_dir)`: time-to-parity heatmaps (threshold × share) per attack ratio, "never" hatched, 37 h line, plus a small panel of **pool depth remaining at the trough** (fraction of the start) over the same grid at ratio 1.0; reads parquet + manifest (add `pool_depth_at_trough` to `summarize`, `None` when no AMM)
6. Completion Notes: does liquidity flight make the depeg deeper (by how much, at which thresholds), does it make recovery faster or slower (F-03 says a shallower pool is cheaper to defend — does flight *help* the defender?), and is there a threshold below which the LP's flight is self-fulfilling (the withdrawal itself pushes the price past the next LP's threshold — one LP here, so report whether its own withdrawals deepen the trough it reacts to); one sentence for the note; F-03 either confirmed from the other side or qualified
7. A `Proposed` ADR: the AMM action, the agent, the scenario assumptions, the sweep result, and a finding candidate
8. Figure registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] AMM remove_liquidity (AC: 1)
  - [ ] Commit separately: `story 3.8: amm remove_liquidity`
- [ ] LP agent, config, factory, tests (AC: 2, 3)
  - [ ] Commit separately: `story 3.8: lp withdrawal agent`
- [ ] Scenario and sweep (AC: 4, 5)
- [ ] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.8: lp withdrawal agent and liquidity flight`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.7 (Status: done)**

- Assumptions are shown, not hidden: the LP's share, threshold and pace are three
  assumptions with no public anchor; say so in the scenario header and the ADR.
- Predictions below are predictions.
- This is the first `protocol/` change since Epic 1. The AMM's swap path must be
  byte-identical afterwards; the fixtures will tell you.

[Source: docs/stories/3-7-multi-tranche-holder.md#Senior-Developer-Review, F-03, F-11 refinements, CHARTER §4 stretch]

### Why this is the last story before the freeze

The charter called LP flight "the core Soros dynamic": liquidity that leaves when it is
needed. Every surface so far held depth fixed. This story makes depth respond to the
price, which is the reflexive loop the 1992 narrative is built on (BACKGROUND §4:
"positions all reversed at once"). It is also the one mechanism the note would be asked
about if it were absent.

### The arithmetic to get right

The LP owns a share of the pool, not an amount. A withdrawal of share `s` from a pool in
which flighty LPs hold `S` of the total scales both reserves by `1 − s`; the LP's remaining
share of the *new* pool is `(S − s)/(1 − s)`. Keep the agent's state in share terms and
convert to a pool fraction at the moment of the action. Write the formula in the agent's
docstring and test it with two consecutive withdrawals.

### Predictions (to be checked)

- At calibrated depth and ratio 1.0, a 50% flighty LP at 5% deepens the trough by 30–60%
  and *shortens* time-to-parity (F-03 from the other side: the shallower pool is cheaper
  for the defender and the holder to buy back).
- Pool depth remaining at the trough falls below 0.6 at thresholds ≤ 5% and stays near 1.0
  at 20%.
- The LP's own withdrawals deepen the trough it reacts to (the 2% threshold column is the
  worst), but with one LP there is no cascade: the effect is bounded by `share`.
- Flight never flips a recovering cell to "never" at D\* — the clock result stands — and
  it does not change which cells lose the price at deeper pools (depth was never the
  binding quantity there).

### Cost

Sweep: 4 × 3 × 3 × 8 = 288 runs; a few minutes on 10 workers.

### References

- [Source: docs/epics.md#Story-3.8]
- [Source: docs/CHARTER.md#4-Scope] — stretch item
- [Source: docs/FINDINGS.md] — F-03, F-11 (+ refinements), F-13
- [Source: src/depeg_sim/protocol/amm.py] — `swap`, `execute`, drain guard
- [Source: docs/adr/0005-construction-validates-execution-rejects.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-8-lp-withdrawal-agent.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: before/after runs, sweep with wall time, aggregate table, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: before/after table; the three AC 6 answers; the note sentence; chart description; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-07: Story drafted by dev manager after Story 3.7 review (third and last Epic 3 stretch story)
