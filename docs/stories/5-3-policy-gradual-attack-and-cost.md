# Story 5.3: Policy Comparison Under a Gradual Attack, With a Cost of Discount

Status: ready-for-dev

## Story

As a **reader who runs a treasury desk**,
I want the defender policies compared under an attack that does not crash the price in one step, and judged on what the discount costs while it lasts as well as on when parity returns,
so that "spend slower than the attacker sells" is either shown to hold where it matters or dropped.

## Why

Referee §5.21–5.23: the policy sweep's attacker sells 10% of its stock in the first
12 seconds, so the price is near $0.23 before any trigger can bind ("triggers are inert"
is partly the shock design), and the model charges nothing for the time spent at a
discount, so a defender that waits and buys the bottom is rewarded by construction.

## Acceptance Criteria

1. **One new summary metric, `discount_bps_hours`**: Σ over steps of
   `max(0, −peg_deviation_bps) × (interval_seconds / 3600)`, i.e. the area between the
   venue price and par while below par, in bps·h, from the attack start to run end.
   Added to `SUMMARY_KEYS`, `summarize()`, and `mc.parquet` aggregates (mean, p05, p95).
   Every existing scenario's hash is unchanged (summary columns are not in the scenario
   hash; confirm with the pinned-hash tests). Document in `summary.py`'s docstring.
2. `sweeps/policy-comparison-gradual-mc.yaml`: the five policies of
   `policy-comparison-mc.yaml`, same three attack ratios, same 16 seeds, but attacker
   `pace` as a third axis over {0.1 (existing), 0.02, 0.01}. 5 × 3 × 3 × 16 = 720 runs.
3. `plot_policy_comparison` gains a pace facet (one row per attacker pace) and a fourth
   panel: **discount_bps_hours** (mean, p05–p95) per policy. `docs/figures/
   policy_comparison_gradual.png`; the existing `policy_comparison.png` is unchanged
   (its sweep is untouched).
4. `scripts/policy_table.py` gains `--sweep` to point at the new sweep and prints, per pace
   and ratio: time to parity, price paid, discount_bps_hours, P(never recovers), and
   **which policy minimises discount_bps_hours and which minimises time to parity** —
   two columns, so the reader sees when they disagree.
5. Trigger test: at pace 0.01, report the step at which each policy's trigger first
   binds and the price at that step, for the 1.0× ratio, seed 1000. One small table in
   VALIDATION.md or FINDINGS-ready notes (builder's choice of file; say which).
6. `docs/calibration/VALIDATION.md` or a new `docs/calibration/POLICY.md` (builder's
   choice; link it from the README): the tables, in the builder's words, numbers only.
7. Tests: metric unit test on a synthetic path (known area); sweep spec hash; figure
   renders from synthetic parquet. `pytest`, `ruff`, `make figures-check`.

## Tasks / Subtasks

- [ ] `discount_bps_hours` metric (AC: 1)
- [ ] Gradual sweep (AC: 2)
- [ ] Figure and table (AC: 3, 4)
- [ ] Trigger-binding table (AC: 5)
- [ ] Write-up (AC: 6)
- [ ] Tests, gates (AC: 7)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.3: policy under gradual attack`, push `story/5-3-policy-gradual-attack-and-cost`

## Dev Notes

### Learnings from Previous Story

- The policy sweep uses `base_axis` (ADR-0025); adding an attacker-pace axis is an
  ordinary `axes:` entry on top of it.
- `peg_deviation_bps` is the per-step column the summary already reads for
  `max_depeg_bps`; the integral is over the same series. Use the attack start step
  (first step the attacker sells) as the lower bound; document the choice.
- 720 runs at 18,000 steps: ~15 min on Seoul at 8 workers. Run once. Do not run under
  `/tmp` (REPRODUCIBILITY.md).
- F-13's refinement (3.4) already found pace ratio first-order and the trigger inert
  *at pace 0.1*. This story asks whether that survives at 0.01–0.02. Either answer is a
  result.

### Prediction (to be checked, not aimed at)

At pace 0.01 the triggers bind at different steps and the early-aggressive defender
buys above $0.90 before the attacker is a tenth done; it may still lose on
discount_bps_hours because it is dry when the attack is only beginning. The slow
defender's advantage on time-to-parity should shrink; on discount_bps_hours it may
reverse. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §5.21–5.23]
- [Source: docs/stories/3-2-defender-policy-comparison.md, 3-4-budget-attack.md]
- [Source: sweeps/policy-comparison-mc.yaml, src/depeg_sim/analysis/summary.py]

## Dev Agent Record

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
