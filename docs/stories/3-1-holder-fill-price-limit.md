# Story 3.1: Holder Fill-Price Limit

Status: ready-for-dev

## Story

As a **researcher**,
I want the holder to stop buying when its own fill would lift the venue price above its entry price,
so that figure 1's first hours show the market, not a model artefact (ADR-0021 sawtooth), and C\* is fitted on a buyer that behaves like one.

## Acceptance Criteria

1. `Holder.decide`: the buy amount is `min(pace × reference_balance, amount_in that moves the AMM spot exactly to entry_price)`, the second term closed-form on constant product with the fee on input, computed the way `Arbitrageur` sizes its trades (reuse or share that helper; cite it); if the second term is ≤ `DUST` the holder does not buy that step (`hold_wait`); rule names unchanged; `HolderConfig` unchanged; every scenario `content_hash()` unchanged (test)
2. `tests/test_holder.py`: a buy that would overshoot is capped so post-trade spot ≤ entry_price within 1e-9; a buy that would not overshoot is uncapped; the old sawtooth test case (spot swings above par) no longer occurs on a two-step synthetic
3. `scripts/fit_holder.py` re-run under the two-pass rule (unchanged); new `C*` in three units; `scenarios/usdc-2023.yaml` updated; replay re-run; `validation_comparison` numbers; VALIDATION.md gains a 3.1 row in the before/after table (2.5 → 2.6 → 3.1: trough depth, trough time, first in band, sawtooth amplitude in the first 3.5 h as max − min of deviation over steps 8,100–9,150)
4. The four propagated scenarios updated to the new `C*/D*`; re-run; outcomes before/after in Completion Notes; 1992 flip re-scanned 5.5–6.0 by 0.1 (the full scan is not needed unless 5.7 moves)
5. `make figures` re-run; guard green; the overlay figure's first-3.5 h band described in words before and after
6. A `Proposed` ADR: the fill rule, new `C*`, what moved; if the sawtooth is reduced but not gone, say why (the attacker's own 10%-of-remaining dumps between holder buys) and whether it is now within the hourly series' resolution
7. `pytest` and `ruff check .` pass; CI green on both jobs

## Tasks / Subtasks

- [ ] Fill rule (AC: 1, 2)
  - [ ] Sizing helper; `Holder.decide`; tests; hash test
  - [ ] Commit separately: `story 3.1: holder fill-price limit`
- [ ] Re-fit and replay (AC: 3)
- [ ] Propagate and figures (AC: 4, 5)
- [ ] ADR, close out (AC: 6, 7)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.1: holder fill-price limit, re-fit C*`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.9 (Status: done) and the Epic 2 retro**

- Every story that changes a calibrated parameter ends with `make figures` and the guard
  green; `C*` changes here, so five figures regenerate (overlay, both surfaces,
  time-to-parity, budget × depth — all carry the holder).
- Predictions below are predictions. Report misses as results.
- The arbitrageur already has closed-form sizing against a target price (Story 1.7); the
  holder's cap is the same computation with `entry_price` as the target. Open
  `agents/arbitrageur.py` before writing it; do not write a second version.

[Source: docs/stories/2-9-committed-figures.md#Senior-Developer-Review, docs/retrospectives/epic-2-retro.md, ADR-0021 Consequences]

### Why this changes C\*

ADR-0021: at the fitted size the holder's 5%-of-reference buys (~450k into a 16.7M pool)
overshoot par for the first 3.5 h, a sawtooth between +310 and −220 bps. Capping each
fill at the entry price removes the overshoot and makes each unit of holder capital
absorb slightly less per step early on, so the same capital reaches the trough with more
left, or the fit lands on a different `C*`. Expect `C*` to move by less than one grid
refinement (≤ 10%); if it moves more, say so.

### Predictions (to be checked)

- Sawtooth amplitude in steps 8,100–9,150: from ~530 bps to ≤ 60 bps (the attacker's own
  dumps between buys remain).
- `C*` within 8.3M–10M; trough within 100 bps of −1,138; trough time within 1 h of 34.2 h.
- 1992 flip stays at 5.7.

### References

- [Source: docs/epics.md#Story-3.1]
- [Source: docs/adr/0021-par-expecting-holder.md] — sawtooth, alternatives considered
- [Source: docs/stories/1-7-agents.md] — arbitrageur closed-form sizing
- [Source: docs/calibration/VALIDATION.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-1-holder-fill-price-limit.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: fit tables, replay CLI lines, propagated runs, 1992 re-scan, `make figures` time, guard, tests, lint)_

### Completion Notes List

_(include: C* three units before/after; VALIDATION.md row; sawtooth amplitude before/after; overlay description; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-05: Story drafted by dev manager at the Epic 2 retro
