# Story 3.1: Holder Fill-Price Limit

Status: in-progress

## Story

As a **researcher**,
I want the holder to stop buying when its own fill would lift the venue price above its entry price,
so that figure 1's first hours show the market, not a model artefact (ADR-0021 sawtooth), and C\* is fitted on a buyer that behaves like one.

## Acceptance Criteria

1. `Holder.decide`: the buy amount is `min(pace × reference_balance, amount_in that moves the AMM spot exactly to entry_price)`, the second term from the arbitrageur's existing `_reference_to_reach` helper, **reused unchanged** (amended 2026-10-05: it ignores the 1 bp fee and undershoots the target by ≤ 0.1 bps, the approximation Story 1.7 accepted; "exactly" is withdrawn); if the smaller of the two terms is ≤ `DUST` the holder does not buy that step and falls through to the redeem / `hold_wait` / `hold_done` rules (amended 2026-10-05); rule names unchanged; `HolderConfig` unchanged; every scenario `content_hash()` unchanged (test)
2. `tests/test_holder.py`: a buy that would overshoot is capped so post-trade spot ≤ entry_price within 1e-9; a buy that would not overshoot is uncapped; a new two-step synthetic (attacker dump between holder buys) shows spot above par under the old rule and not under the new one (amended 2026-10-05: there was no existing sawtooth test)
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
  green; `C*` changes here, so nine of ten figures regenerate (every scenario except
  soros-baseline carries the holder; amended 2026-10-05).
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

## Blockers

**AC 1 asks for a fee-aware closed form that reaches `entry_price` exactly, and also asks
to reuse the arbitrageur's sizing helper, which ignores the fee.** No code written.

- `src/depeg_sim/agents/arbitrageur.py:43` `_reference_to_reach(k, r, target)` returns
  `sqrt(k·target) − R`, with the docstring "(fee ignored)". The module docstring says: "With
  a fee the input is reduced before the curve, so spot slightly undershoots the target;
  this is accepted, not solved iteratively". Story 1.7's Dev Notes (`1-7-agents.md:114–120`)
  say the same: exact only at `fee_bps = 0`.
- AC 1 wants "the `amount_in` that moves the AMM spot **exactly** to `entry_price`, closed
  form on constant product **with the fee on input**", "computed the way `Arbitrageur`
  sizes its trades (reuse or share that helper)". The Dev Notes ("the same computation")
  and the prompt ("it already sizes a trade to a target price on constant product with
  fee on input … do not write a second version") make the same assumption. The helper
  cannot do both.
- **Size.** Real AMM `quote`, target 0.98 (scratch calculation, not committed):

  | pool / start spot / fee | helper `x` → spot after | fee-exact `x` → spot after |
  |---|---|---|
  | 1M-ish, 0.950, 1 bp | 14,883.4 → −0.0154 bps from 0.98 | 14,884.2 → −1e-12 bps |
  | D\*, 0.943, 1 bp | 317,928.5 → −0.0193 bps | 317,944.4 → 0 |
  | D\*, 0.826, 1 bp | 1,347,643.1 → −0.0817 bps | 1,347,710.5 → +2e-12 bps |
  | 1M-ish, 0.950, 30 bp | 14,883.4 → −0.4628 bps | 14,905.8 → 0 |

  Both satisfy AC 2's test (post-trade spot ≤ `entry_price` within 1e-9). The helper misses
  "exactly" by at most ~0.08 bps at the calibrated 1 bp fee. The fee-exact form is the root
  of `(1−f)x² + (2−f)R·x + R² − k·p = 0`:
  `x = [−(2−f)R + sqrt(f²R² + 4(1−f)k·p)] / (2(1−f))`.

**Options** (not chosen):

- **(a) Reuse `_reference_to_reach` unchanged** (recommended). The holder's cap is
  `_reference_to_reach(amm.k, amm.reserve_reference, entry_price)`, imported from
  `arbitrageur.py` or moved to `agents/base.py` with the arbitrageur importing it. The
  arbitrageur's behaviour does not change, and there is one helper. AC 1's "exactly"
  becomes "to `entry_price`, fee ignored; spot undershoots by ≤ f·x/√(k·p) (≤ 0.1 bps
  here)", the same accepted approximation as Story 1.7.
- **(b) A fee-exact helper for the holder only.** Exact as written, but it is the "second
  version" the prompt forbids, and the two agents then size the same thing two ways.
- **(c) Make the shared helper fee-exact for both agents.** One exact helper, but every
  arbitrageur trade changes, so every scenario's output moves (and every committed figure
  with it, including `soros-baseline`). That is outside this story's scope ("every scenario
  hash unchanged" still holds, but outputs do not).

**Smaller points; I will do as stated unless the ruling says otherwise:**

1. **"Old sawtooth test case" (AC 2).** `tests/test_holder.py` has no such test (19 tests,
   none about overshoot). I will write a new two-step synthetic: real AMM at the context's
   numbers, holder buy, attacker dump, holder buy. Under the old rule it shows spot above
   par after a holder buy, and under the new rule it does not.
2. **Which term is ≤ DUST, and which rule fires.** AC 1 checks only the cap term, and says
   "does not buy that step (`hold_wait`)". The context test idea ("spot 0.979 and tiny
   reference: cap ≤ DUST → `hold_wait`") makes the *pace* term tiny. At spot 0.979 on a 1M
   pool the cap term is about 500 units, not ≤ DUST. I will skip the buy when
   `min(pace × reference, cap) ≤ DUST` and fall through to the existing chain (redeem if
   the tranche rule applies, else `hold_wait` if it holds stable, else `hold_done`). Rule
   names are unchanged. That is "does not buy", and it does not invent a `hold_wait` for a
   holder with nothing to wait on.
3. **Figure count.** The Dev Notes say five figures regenerate. Every scenario except
   `soros-baseline` carries the holder, including `calibrated-stress` (`oracle-lag-mc`)
   and the calibrated and 1992 trajectories, so nine of ten source hashes change.
   `make figures` regenerates all ten either way; the guard will name nine.

## Rulings

**2026-10-05 (dev manager), on the Blockers above.**

1. **Option (a).** Reuse `_reference_to_reach` unchanged. The ≤ 0.1 bps undershoot on a
   200 bps target is immaterial and it is the approximation the project already accepted
   in 1.7; two sizing formulas for the same trade would be worse than either. "Exactly" in
   AC 1 was mine, written without opening the helper (L-2). AC 1 amended. State the
   undershoot in the ADR.
2. **New two-step sawtooth test** — accepted; AC 2 amended.
3. **Skip the buy when the smaller term is ≤ DUST and fall through** — accepted; AC 1
   amended.
4. **Nine of ten figures regenerate** — accepted; Dev Notes amended.

Resume at the Fill rule task.

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
- 2026-10-05: Blocked by builder (Claude Code, Opus 5.5) before Task 1: the arbitrageur's sizing helper ignores the fee, AC 1 asks for fee-exact; see Blockers
- 2026-10-05: Dev manager ruled on Blockers: reuse the arbitrageur helper unchanged (option a); three implementation notes accepted; AC 1, AC 2 and Dev Notes amended; Status back to in-progress
