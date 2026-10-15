# Story 5.1: Par-Reference Replay

Status: ready-for-dev

## Story

As a **reader who doubts the replay**,
I want the USDC March 2023 replay run with nothing from the observed price series fed to the model,
so that whatever agreement remains between the simulated and observed paths cannot be the input showing through.

## Why (read this first)

Outside review 1 (`docs/reviews/2026-10-15-outside-review-1-finance-professor.md`, §1 and
§5.6/§5.14) made one objection that matters more than the rest: in `usdc-2023.yaml` the
reference price **is** the observed USDC/USD series, the oracle follows it, and the
arbitrageur trades against that oracle, so the simulated venue is anchored to the thing we
are comparing it with. VALIDATION.md already says the later path is "the input series
showing through." This story removes the input and reports what is left. **The result
decides how note v2 describes the replay.** Do not tune anything to make the result look
better. A trough that moves away from the observation is a result.

## Acceptance Criteria

1. Two new scenarios, hashes recorded:
   - `scenarios/usdc-2023-par.yaml`: `usdc-2023.yaml` with `price_series_path` removed,
     `base_price 1.0`, `volatility_per_step 0.0`, `mean_reversion_per_step` absent (constant
     par reference). Everything else byte-identical in meaning (same attacker, holder,
     capacity schedule, max_steps, seed).
   - `scenarios/usdc-2023-tranches-par.yaml`: the same change applied to
     `usdc-2023-tranches.yaml` (ladder B, C\* 10,833,333).
   Header comments say what changed and cite this story.
2. A third pair with the calm OU reference instead of constant par (`volatility_per_step
   3.086e-05`, `mean_reversion_per_step 0.001634`, from `calibrated-baseline-ou.yaml`), as
   `usdc-2023-ou.yaml` and `usdc-2023-tranches-ou.yaml`. Seed 42. These are a sensitivity
   check; the par pair is the primary result.
3. `scripts/replay_table.py` runs the six replay scenarios (observed-reference ×2, par ×2,
   OU ×2) and prints one table: trough bps, trough step and hour, first band re-entry hour,
   hours in band, holder bought / redeemed / PnL, arbitrageur redeemed. Observed row at the
   top (−1,373 bps, 31.0 h, from the CSV). Deterministic; runnable on Seoul in < 5 min.
4. `plot_validation_overlay` gains an optional second simulated series: new figures
   `validation_overlay_usdc_2023_par.png` and `validation_overlay_usdc_2023_tranches_par.png`
   show observed (blue), observed-reference replay (grey, dashed) and par-reference replay
   (black). Captions in `docs/figures/README.md` lead with what was fed in. Added to
   `make figures`, the manifest and the note's figure list (figure-set test updated).
5. `docs/calibration/VALIDATION.md` gains a section "Par-reference replay (Story 5.1)" with
   the AC 3 table and a plain statement of what moved and what did not, **in the builder's
   words, without interpretation of what it means for the note** (the dev manager does
   that in review).
6. If the par-reference trough is within ±10% of the observed trough for ladder B, say so.
   If it is not, say so. Either way, record the number. Do not re-fit C\* or pace in this
   story.
7. Tests: scenario hashes pinned; `replay_table.py` smoke test on a shortened `max_steps`;
   overlay with two simulated series renders. `pytest`, `ruff check .`, `make figures-check`
   (code hash will change: this epic lifts the freeze; record the new hash in the Dev Agent
   Record).

## Tasks / Subtasks

- [ ] Scenarios: par pair, OU pair (AC: 1, 2)
- [ ] `replay_table.py` (AC: 3)
- [ ] Overlay with second series; figures; manifest; figure list (AC: 4)
- [ ] VALIDATION.md section (AC: 5, 6)
- [ ] Tests, lint, figures-check (AC: 7)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.1: par-reference replay`, push branch `story/5-1-par-reference-replay`

## Dev Notes

### Learnings from Previous Story

**From Story 4.1/4.2 and the outside review**

- The freeze is lifted for Epic 5 only. Change what the ACs name; nothing else under `src/`.
- Every result in this epic goes into the note as a number first and a sentence second.
  Write the number down before deciding what it means (PROCESS L-19).
- `price_process.py`: with `price_series_path` absent, `volatility_per_step 0` and no
  `mean_reversion_per_step`, the reference is constant `base_price`. Confirm by reading the
  module, not by assuming (L-2).
- The holder's entry test is against `peg_price × (1 − entry_discount_pct/100)`, not the
  oracle (ADR-0021, ADR-0024), so the holder is unaffected by this change; the arbitrageur
  (oracle-relative) and the oracle module are what change. Say so in VALIDATION.md.

### What to expect (dev manager's prediction, to be checked, not aimed at)

The trough is set in the first four hours by the attacker against the holder, with the
arbitrageur capacity-bound at 605.79/step; it should move little. The recovery path after
~35 h will no longer track the observed series. Whether it recovers faster (par oracle,
arbitrageur always buying below 0.998) or slower is the open question. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §1, §5.6, §5.14, §7]
- [Source: docs/calibration/VALIDATION.md] — current replay record
- [Source: scenarios/usdc-2023.yaml, usdc-2023-tranches.yaml, calibrated-baseline-ou.yaml]
- [Source: src/depeg_sim/environment/price_process.py]
- [Source: src/depeg_sim/analysis/charts.py#plot_validation_overlay]

## Dev Agent Record

## Change Log

- 2026-10-15: Story drafted by dev manager from outside review 1 (Epic 5)
