# Story 3.4: Budget Against Attack at a Deep Pool, and Pace Against Trigger

Status: ready-for-dev

## Story

As a **researcher**,
I want the price-defense boundary mapped against attack size at a pool too deep to crash, and the defender's pace separated from its trigger,
so that F-11's withdrawn clause is replaced by a tested one and F-13 names the right parameter.

## Acceptance Criteria

1. `sweeps/budget-x-attack-mc.yaml`: base `calibrated-baseline.yaml` with `overrides` for depth 2× D\* (`amm.reserve_stable`, `amm.reserve_reference` = 33,333,334; `agents[type=holder].capital` = 18,333,334) and `termination.peg_recovered.reference: oracle`; axes `agents[type=defender].budget ∈ {0.5, 1, 1.5, 2, 3} × 41,346,974` and `agents[type=attacker].capital ∈ {0.5, 0.8, 1.0, 1.5, 2.0} × 179,454,391`; 8 seeds from 1000; `max_steps` 18000; header states every number's origin and why 2× D\* (F-11 refinement: the price is lost there, not the clock)
2. `plot_budget_attack(sweep_dir) -> Path`: left, heatmap of **p(never re-enters)** (`1 − steps_to_first_band_entry_n / n`, the price-loss probability) over budget × attack with the 0.5 contour; right, the budget at each attack column's 0.5 crossing (linear interpolation; "not reached" marked) against attack on log–log, with slope-1 and slope-0 reference lines through the middle crossing and the least-squares slope in the legend; reads parquet + manifest
3. Completion Notes: the crossing budgets per attack; the slope; whether the crossing budget is proportional to attack size (slope ≈ 1), to what the attacker extracts from the pool (compute `attacker_pnl`-based extraction per cell and test that too), or to neither; one sentence for the note in the form "at a pool too deep to crash, holding the price against an attack of X needs a budget of ≈ Y·X (or ≈ Z regardless of X)"
4. `sweeps/pace-x-trigger-mc.yaml` (3.2 review ruling 3): base `calibrated-baseline.yaml`, oracle criterion, attacker at ratio 1.0; axes `agents[type=defender].spend_pace ∈ {0.05, 0.1, 0.2, 0.5}` × `agents[type=defender].threshold_pct ∈ {0.5, 1, 2, 4}` × `agents[type=attacker].pace ∈ {0.1, 0.02}`; 8 seeds; `max_steps` 18000
5. `plot_pace_trigger(sweep_dir) -> Path`: two heatmaps (one per attacker pace) of median time-to-parity in hours from run start over defender pace × trigger, "never" hatched, 37 h line; a third small panel of average price paid per stable (`defender_spent / defender_bought_stable`) over the same grid at attacker pace 0.1
6. Completion Notes for AC 4–5: does time-to-parity vary along pace, along trigger, or both; does the best defender pace move when the attacker's pace changes (hypothesis: the operative quantity is defender pace relative to attacker pace); one sentence restating F-13 with the right parameter named
7. A `Proposed` ADR covering both sweeps and their verdicts on the F-11 and F-13 hypotheses; finding candidates where the data supports them
8. Both figures registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] Budget × attack (AC: 1, 2, 3)
  - [ ] Spec; run; chart; synthetic test; look and describe
  - [ ] Commit separately: `story 3.4: budget x attack at 2x D*`
- [ ] Pace × trigger (AC: 4, 5, 6)
  - [ ] Spec; run; chart; test; look and describe
- [ ] ADR, figures, close out (AC: 7, 8)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.4: budget vs attack and pace vs trigger`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.3 (Status: done)**

- Map actions by what they touch (price, reserves, budget), not by their names. Here:
  "price loss" is never-re-enters; "clock" is late re-entry; keep them apart in every
  table.
- Predictions below are predictions. 3.2 and 3.3 both inverted theirs.
- `base_axis` and `None` on an axis exist if needed; neither is needed here.

[Source: docs/stories/3-3-holder-exit-rule.md#Senior-Developer-Review, F-11 refinement, F-13, F-14]

### Why 2× D\* and why never-re-enters

The F-11 refinement showed D\* breaks on the clock and 2× D\* on the price. The budget ×
depth sweep at a fixed attack said the budget interval that decides 2× and 4× D\* is the
same, so the operative quantity at that attack was the budget itself. This sweep varies
the attack at fixed depth to see what the budget has to match. The metric is price loss
(never re-enters), which `steps_to_first_band_entry_n` gives directly, so the clock
cannot contaminate it.

### Predictions (to be checked)

- Budget × attack: the crossing budget rises with attack size but less than
  proportionally (slope between 0.3 and 0.7), because what the attacker extracts from a
  constant-product pool saturates at the pool's reference side as the attack grows.
- The crossing budget tracks extraction (`−attacker_pnl` in reference terms at the
  trough) more closely than attack size.
- Pace × trigger: time-to-parity varies mostly along pace; trigger matters only at 4%,
  where the defender starts after the attacker has already finished (then it is cheap and
  fast — the F-13 mechanism). At attacker pace 0.02 (a slower attack, 500 steps instead of
  50), the best defender pace moves down.
- Average price paid falls monotonically with slower pace at every trigger.

### Cost

25 cells × 8 seeds = 200 runs; 32 cells × 8 = 256 runs; ≤ 18,000 steps each. A few minutes
each on 10 workers. Report real times.

### References

- [Source: docs/epics.md#Story-3.4]
- [Source: docs/FINDINGS.md] — F-03, F-11 (+ refinement), F-13
- [Source: docs/adr/0023-reference-relative-recovery.md, 0025-defender-policy-comparison.md]
- [Source: sweeps/budget-x-depth-mc.yaml, policy-comparison-mc.yaml] — spec style

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-4-budget-vs-attack.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: both sweep runs with wall times, aggregate tables, crossings, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: crossing budgets and slope; the extraction test; the F-11 sentence; pace vs trigger verdict; the F-13 sentence; chart descriptions; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.3 review
