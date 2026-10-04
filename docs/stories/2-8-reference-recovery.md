# Story 2.8: Reference-Relative Recovery and the Budget × Depth Boundary

Status: ready-for-dev

## Story

As a **researcher**,
I want the recovery criterion to be able to measure the venue against the market price rather than against par,
so that the threshold surface shows where the attack beats the defense rather than where the reference wandered, and the note can test whether the price-defense boundary is set by budget against depth (F-11).

## Acceptance Criteria

1. `PegRecoveredConfig` gains `reference: Literal["par", "oracle"] = "par"`; every existing scenario's `content_hash()` unchanged (test); with `"oracle"`, the in-band test in `termination.check` uses `spot / oracle_price − 1` instead of `peg_deviation`, where `spot` comes from a new `PegView.spot_price` property and `oracle_price` from a new `ReferenceView` Protocol (`reference_price: float | None`) in `kernel/interfaces.py`, implemented by the Oracle as its published price; before the first oracle publish the step counts as out of band; the kernel still reads only Protocol views (no import of `protocol/`); `PHASE_ORDER_VERSION` stays 1
2. `steps_to_first_band_entry` and `steps_to_sustained_recovery` in `summarize` follow the same criterion (document in the summary docstring which deviation they use); the manifest's resolved config already records `reference`
3. Tests: par behaviour byte-identical on `soros-baseline` (run-vs-rerun fixtures untouched); with `oracle` on a synthetic run where the reference drifts +50 bps and the AMM tracks it, `par` → `max_steps` and `oracle` → `peg_recovered`; before first publish → out of band
4. `sweeps/threshold-surface-ref-mc.yaml`: identical to `threshold-surface-mc.yaml` plus `overrides: {termination.peg_recovered.reference: oracle}`; run with `--mc`; `plot_threshold_surface` reads the criterion from the manifest's `base_config` (after overrides) and puts it in the heading; the chart written as `threshold_surface.png` in that sweep's directory
5. `sweeps/budget-x-depth-mc.yaml`: base `calibrated-baseline`, `reference: oracle`; linked depth axis as in 2.7 (five values, holder at 0.55×); axis `agents[type=defender].budget` over `41,346,974 × {0.25, 0.5, 1, 2, 4}`; attacker fixed by override at ratio 1.0 (`179,454,391`); 8 seeds from 1000; `max_steps` 18000; header states origins; `plot_budget_depth(sweep_dir) -> Path`: left panel heatmap of `p_stays_broken` over depth × budget with the 0.5 contour; right panel the budget at each depth row's 0.5 crossing (linear interpolation; "not reached" marked) against depth on log–log axes with a slope-1 reference line — the F-11 hypothesis is that the crossing budget scales with depth
6. Completion Notes: (a) the two surfaces side by side as a table of per-row 0.5 crossings (par criterion from 2.7 vs oracle criterion), (b) the budget × depth crossings and whether they scale with depth, (c) the headline sentence drafted from the oracle-criterion surface in the form "At calm volatility, an attack of X× the defenders' nominal resources leaves the venue price more than 31 bps below the market price through the 60 h horizon with probability ≥ 0.5 only in pools deeper than Y × D\*; the price-defense boundary is set by budget against depth: a budget of ≈ Z × the pool's reference-side depth holds the price against any attack in the grid", with X, Y, Z from the data or "not supported" if they aren't
7. `scenarios/usdc-2023.yaml` keeps `par` (the replay's reference *is* the observed depeg); VALIDATION.md gains one sentence saying so
8. A `Proposed` ADR: the criterion option and its Protocol-view design, what the oracle criterion changed in the surface, the budget × depth result and its verdict on F-11's hypothesis, and which surface the note uses
9. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Criterion option (AC: 1, 2, 3)
  - [ ] `PegView.spot_price`; `ReferenceView`; Oracle implements; `PegRecoveredConfig.reference`; `termination.check`; `summarize` metrics; tests; hash test
  - [ ] Commit separately: `story 2.8: peg_recovered.reference option`
- [ ] Reference-criterion surface (AC: 4)
  - [ ] Sweep spec; run; chart heading from manifest; look and describe
- [ ] Budget × depth (AC: 5)
  - [ ] Sweep spec; run; `plot_budget_depth`; synthetic-parquet test; look and describe
- [ ] Headline, ADR, close out (AC: 6, 7, 8, 9)
  - [ ] Completion Notes tables and sentence; VALIDATION.md line; Proposed ADR
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.8: reference-relative recovery and budget x depth`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.7 (Status: done)**

- The criterion decides the chart. 2.7's surface measured the clock at ≤ D\* because the
  par criterion fails late recoveries against a wandering reference (F-11, F-04
  refinement). This story makes the criterion explicit and runs the sweep through it; no
  post-hoc filters.
- Mechanism seen in 2.7's `sweep.parquet` at ratio 1.5: the defender spends its whole
  budget in every row; final deviation −9.5 bps at ≤ D\*, −3,486 / −4,062 at 2× / 4×. A
  fixed budget buys the dump back when the pool is shallow enough to crash. AC 5 tests
  whether the crossing budget scales with depth.
- Report per-depth medians of `defender_spent` and `final_depeg_bps` from `sweep.parquet`
  for both new sweeps; they were decisive in 2.7's review.
- Conservation-shaped collapses are checks, not results; no absorbed-ratio panel here.

[Source: docs/stories/2-7-threshold-surface.md#Senior-Developer-Review, docs/FINDINGS.md F-10, F-11, F-04 refinement]

### Why a Protocol view and not an oracle import

`CLAUDE.md`: no domain logic in the kernel. `termination.check` already reads the AMM
through `PegView` (ADR-0007). The oracle's published price is the second number the
criterion needs, and it reaches the kernel the same way: a `ReferenceView` Protocol that
the Oracle satisfies, found by `ctx.registry.find(ReferenceView)`. If more than one
subsystem satisfies it, `find` returns the first registered; document that. If this
conflicts with ADR-0007's ownership statement in a way you can't resolve, propose the
amendment in the ADR rather than importing `protocol/`.

### Why `oracle` and not `environment reference`

The oracle is what the arbitrageur sees and what a reader would call "the market price";
the raw environment reference is unobservable in the model's own terms. F-10 says they
are within 0.5 bps at Chainlink's settings, so the choice does not move results; it keeps
the kernel reading a published number.

### Expected shapes (predictions, to be checked, not enforced)

- Oracle-criterion surface: the ≤ 1× D\* rows go to ≈ 0 at every ratio; 2× and 4× cross
  near nominal 0.69–0.70 as the 2.7 post-hoc filter suggested. If the contour runs along
  depth rather than capital, F-11's hypothesis is supported.
- Budget × depth: a crossing budget that rises with depth, roughly proportionally (a
  slope near 1 on log–log). Where the attack (ratio 1.0, $42B-equivalent) exceeds the
  pool by a large factor, attacker size should not matter and the crossing should be
  set by `budget / depth`. If the slope is clearly not 1, report it; that is the result.
- `usdc-2023` is untouched; its hash `2c3aeaa9825d` must not change.

### Cost

Surface: 640 runs (≈ 2.5 min on 8 workers). Budget × depth: 200 runs. Report real times.

### References

- [Source: docs/epics.md#Story-2.8]
- [Source: docs/FINDINGS.md] — F-03, F-04 (+ refinements), F-06, F-11
- [Source: docs/adr/0007-peg-view-owner-and-sign.md] — PegView ownership
- [Source: docs/adr/0022-threshold-surface-metric-and-oracle-lag.md] — §7
- [Source: src/depeg_sim/kernel/termination.py, interfaces.py]

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-8-reference-recovery.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: both sweep runs with wall times, aggregate tables, per-depth medians, test and lint output)_

### Completion Notes List

_(include: the two-surface crossing table; budget × depth crossings and slope; the headline sentence; chart descriptions; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.7 review (F-11); inserted into Epic 2; figures story renumbered to 2.9
