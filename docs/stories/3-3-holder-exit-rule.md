# Story 3.3: Holder Sell Rule and the 1992 Switch-Sides Test

Status: ready-for-dev

## Story

As a **researcher**,
I want the holder to be able to lose its belief and sell,
so that the note can test BACKGROUND §4's claim that Black Wednesday needed the convergence traders to turn — and say, with numbers, whether a believer who switches sides is what breaks a peg.

## Acceptance Criteria

1. `HolderConfig` gains `exit_discount_pct: float | None = None` (`gt=0, lt=100` when set); `Holder` gains rule `hold_exit`: on the first step where `amm.spot_price < 1 − exit_discount_pct/100`, it cancels nothing already queued but sells **all** stable it holds on the AMM in one `swap sell_stable` (if that amount is ≤ `DUST`, no action), sets a one-way `exited` flag, and from then on never buys or redeems again (`hold_done`); `exit_discount_pct` must exceed `entry_discount_pct` (validator, error names the rule); every existing scenario `content_hash()` unchanged (test); decision trace records `hold_exit` once
2. `tests/test_holder.py`: exits once below the exit price; never re-enters when the price recovers; exit with nothing held records no action; validator error; PnL after a buy-then-exit cycle at a lower price is negative
3. `sweeps/holder-exit-1992-mc.yaml`: base `soros-1992.yaml` at 6× (as committed); axes `agents[type=holder].exit_discount_pct ∈ {null, 5, 10, 20, 40}` × `agents[type=holder].capital ∈ {C*, 5 C*, 25 C*}` (9,166,667; 45,833,335; 229,166,675 — the last ≈ 0.9× the attacker); 8 seeds from 1000; `max_steps` as the scenario; `sweep.parquet` gains nothing new, but the per-run summary must include `holder_pnl` (exists) and `reserves_exhausted`, `steps_run`; `null` must be expressible on an axis (if `set_path` cannot set `None`, make it able to, with a test)
4. Multiple re-scan 4.0–7.0 by 0.1 on `soros-1992`, holder at 25 C\*, with `exit_discount_pct` `null` and `10`, seed 42: the flip multiple in each; a `scripts/scan_1992.py` that does this (replacing the scratch scripts of 2.5/2.6/3.1; takes `--holder-capital`, `--exit`, `--range`), with a dry-run test
5. `plot_holder_exit(sweep_dir) -> Path`: left, heatmap of `p_reserves_exhausted` over exit × capital with the `null` column labelled "never sells"; right, mean reserves-exhausted step (or "not exhausted") and mean holder PnL as two small panels, one line per capital; reads parquet + manifest
6. Completion Notes answer, in one paragraph with numbers: at the largest holder, does the analogue exhaust *without* the holder selling? With it selling at which discount? Does the flip multiple move, and in which direction, when the holder can switch sides? What does the holder's PnL look like in the runs where reserves exhaust versus where they don't? Then one sentence on whether BACKGROUND §4's claim is supported, contradicted, or not testable at this size
7. A `Proposed` ADR: the exit rule semantics, the sweep, the verdict, and a finding candidate if the believer's exit decides the outcome
8. `make figures` with the new figure registered; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] Exit rule (AC: 1, 2)
  - [ ] Config field + validator; `hold_exit`; tests; hash test
  - [ ] Commit separately: `story 3.3: holder exit rule`
- [ ] Sweep and scan (AC: 3, 4)
  - [ ] `None` on an axis if needed; sweep spec; `scripts/scan_1992.py`; runs
- [ ] Chart (AC: 5)
- [ ] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.3: holder exit rule and 1992 switch-sides test`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.2 (Status: done)**

- Every prediction in 3.2 missed; the mechanism (price paid) was what mattered. Below are
  predictions again, labelled as such.
- Name agents by what they do. The exit rule is "sells everything once"; the note will
  call it switching sides.
- `base_axis` exists now; not needed here (one base).

[Source: docs/stories/3-2-defender-policy-comparison.md#Senior-Developer-Review, F-12, F-13]

### Who this agent is now

F-12 showed the capped holder is a redeemer in waiting: it buys below par and redeems
whenever it can, and at 25 C\* it would be a second attacker on the redemption channel
even without selling. The exit rule adds the convergence trader's other move: dumping
sterling on the market once the peg looks lost. In the model that is a `sell_stable` on
the AMM, which pushes the price down (helps the attacker) and hands the holder reference
at the crashed price (it loses). The question is whether that sale is what exhausts the
reserves, or whether the redemption channel does it anyway.

### Why 25 C\* and why one-way

At C\* the holder is 3.6% of the attacker (ADR-0021) and cannot decide anything. 25 C\*
puts it at 0.9× the attacker — BACKGROUND §4's convergence traders were the larger pool of
capital. One-way because a believer who switches sides and then switches back is a
different agent (a momentum trader), and the note's claim is about belief breaking.

### Predictions (to be checked)

- At 25 C\* with `null` (never sells), reserves do **not** exhaust at 6×: the holder's
  redemptions compete with the arbitrageur's but its buying holds the price up.
- With exit at 10% or 20%, reserves exhaust earlier than without the holder at all (the
  dump adds to the attack).
- At 40% the holder never exits (the price never gets there at 6×), so that column equals
  `null`.
- The flip multiple at 25 C\* moves *down* with an exit rule (less attacker capital needed)
  and *up* without one.
- Holder PnL is negative in every run where it exits.

### Cost

5 × 3 × 8 = 120 runs at 14,400 steps plus 62 scan runs: a few minutes on 10 workers.

### References

- [Source: docs/epics.md#Story-3.3]
- [Source: docs/BACKGROUND.md#4-The-attackers] — the convergence trades
- [Source: docs/FINDINGS.md] — F-07 (+ refinements), F-08, F-12, F-13
- [Source: docs/adr/0021-par-expecting-holder.md, 0024-holder-fill-price-limit.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-3-holder-exit-rule.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: sweep and scan runs with wall times, aggregate table, flip multiples, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: the verdict paragraph; the flip table; chart description; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-05: Story drafted by dev manager after Story 3.2 review
