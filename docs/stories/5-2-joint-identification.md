# Story 5.2: Joint Identification of D* and C*

Status: ready-for-dev

## Story

As a **reader who suspects the fitted triple is one of many**,
I want the trough drawn as a surface over pool depth and believers' capital on the par-reference replay, with all three ladders beside it,
so that the note can say how wide the family of fits is instead of reporting one point.

## Why

Referee §5.9–5.11: three fitting rules do not give three independent pieces of
information; D\*, C\* and pace interact, and the ladder was chosen after seeing the fits.
Story 5.1 showed the trough survives without the observed input (F-16), so the par
replay is the right surface to draw. The pace is **not** swept here (it was fitted to the
trough's timing, and the timing is what the par replay reproduces least well; 5.5 looks
at the weekend first).

## Acceptance Criteria

1. `sweeps/usdc-par-depth-x-capital.yaml`: base `scenarios/usdc-2023-tranches-par.yaml`
   (ladder B), axes `amm.reserve_stable`/`reserve_reference` linked (`LinkedAxis`) over
   {0.5, 0.75, 1, 1.5, 2} × D\* and `agents[type=holder].capital` over
   {0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 2} × C\*(ladder B) — 40 cells, seed 42 only (the
   reference is constant, so there is nothing to average). Output `max_depeg_bps`,
   `step_of_max_depeg`, `steps_to_first_band_entry`, holder bought/redeemed/PnL.
2. `plot_identification_surface`: heatmap of trough bps over the two axes; the ±5% and
   ±10% contours around −1,373 drawn and labelled; the fitted point marked.
   `docs/figures/identification_surface.png`, in `make figures`, manifest, figure list
   (marked †), README caption leading with "on the par-reference replay, nothing from the
   observed series fed in."
3. `scripts/identification_table.py`: prints the cells inside ±10%, and for each depth the
   C\* range that lands inside ±5% (linear interpolation between grid points). Deterministic.
4. **Ladders side by side.** The same script's second table: ladders A (1/2/5% at
   50/30/20), B (2/5/10/20% at 25% each), C (1/2/5/10/15% at 20% each) on the par
   replay at D\*, each at **its own** fitted C\* from Story 3.7 (read the values from
   `docs/calibration/fits/` or the 3.7 story; do not re-fit), and also at ladder B's C\*
   so the reader sees capital held constant. Trough, trough time, re-entry.
5. If cheap (≤ 1 h): a fourth holder variant with a **continuous** entry distribution,
   uniform over 2–20% in 10 equal tranches of 10% each, same C\*. One row in the ladder
   table. If not cheap, say so and skip; do not build a new agent type.
6. `docs/calibration/VALIDATION.md` gains "Identification (Story 5.2)" with both tables and
   a plain description of the surface's shape (where the cliff is, how the ±5% region is
   oriented) — numbers and shape only, no interpretation.
7. Tests: sweep spec hash pinned; surface renders from a synthetic parquet; table script
   smoke test. `pytest`, `ruff`, `make figures-check`.

## Tasks / Subtasks

- [ ] Sweep spec and run (AC: 1)
- [ ] Surface figure (AC: 2)
- [ ] Tables (AC: 3, 4, 5)
- [ ] VALIDATION.md (AC: 6)
- [ ] Tests, gates (AC: 7)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.2: joint identification`, push `story/5-2-joint-identification`

## Dev Notes

### Learnings from Previous Story

- 5.1's `replay_table.py` holds the metric definitions ("first back in band after the
  trough"); reuse its functions, do not re-implement (ADR-0033 ruling 3).
- `LinkedAxis` with `scales` (Story 2.7) is how depth is swept with both reserves
  together; D\* = 16,666,667.
- Each sweep cell on the replay is ~2 s; 40 cells is fine on Seoul with `--workers 8`.
- The holder's `tranches` config is in `scenarios/usdc-2023-tranches-par.yaml`; ladders A
  and C are defined in Story 3.7 / ADR-0030.

### Prediction (to be checked, not aimed at)

The ±5% region is a thin diagonal band: deeper pools need more believers' capital to
reach the same trough, because the attacker is paid more per unit. The cliff (F-09) runs
below the band. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §5.9–5.11]
- [Source: docs/stories/5-1-par-reference-replay.md#Senior-Developer-Review]
- [Source: docs/adr/0030-multi-tranche-holder.md] (ladders)
- [Source: sweeps/pool-depth-x-attacker-mc.yaml] (LinkedAxis example)

## Dev Agent Record

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
