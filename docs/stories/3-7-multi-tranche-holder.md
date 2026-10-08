# Story 3.7 (stretch): Multi-Tranche Holder

Status: in-progress

## Story

As a **researcher**,
I want the believers to enter at a spread of prices rather than one,
so that the note can say whether F-09's cliff becomes a curve and how close a buyer with a distribution of entry prices gets to the observed trough.

## Acceptance Criteria

1. `HolderConfig` gains `tranches: list[Tranche] | None = None` with `Tranche(entry_discount_pct: float ge 0, share: float gt 0 le 1)`, shares summing to 1 within 1e-9 (validator), entry discounts strictly increasing (validator); when set, `entry_discount_pct` must be absent (validator names the rule); every existing scenario `content_hash()` unchanged; `Holder` with tranches keeps one reference balance per tranche (`capital × share`), applies the fill-price cap per tranche against that tranche's entry price, and the redeem / exit rules unchanged on the pooled stable; rule names unchanged; decision record gains `tranche` where a buy came from
2. Tests: three tranches, price steps down through each entry — each tranche buys only below its own entry and only from its own share; a single tranche at share 1 is byte-identical to the scalar form on `usdc-2023.yaml` (test); validators
3. `scripts/fit_holder.py` gains `--tranches` taking `entry:share,…` and fits total capital `C*` by the unchanged two-pass rule; run it on `usdc-2023.yaml` for **three fixed ladders** (no tuning of the ladders; they are assumptions, stated): `A` = `1:0.5,2:0.3,5:0.2`; `B` = `2:0.25,5:0.25,10:0.25,20:0.25`; `C` = `1:0.2,2:0.2,5:0.2,10:0.2,15:0.2`; report `C*` in three units and the trough for each, with the single-entry 2.6/3.1 result as the baseline row
4. The fitted trough's distance from −1,373 for each ladder; the **cliff test**: for the best ladder, the trough at `C* × {0.8, 0.9, 1.0, 1.1, 1.2}` beside the single-entry values at the same multiples (from 2.6's refinement table) — a curve if the bimodal jump is gone
5. The best ladder (closest trough, ties to fewer tranches) becomes `scenarios/usdc-2023-tranches.yaml` (the replay file itself is untouched); replay run; overlay generated as `validation_overlay_usdc_2023_tranches.png`; VALIDATION.md gains a 3.7 row and a paragraph; SOURCES.md a tranche row (`assumption`)
6. Completion Notes: whether the cliff is gone, the best trough vs −1,373, whether trough timing moved, and one sentence for the note's limitations section (F-09 resolved, narrowed, or unchanged)
7. A `Proposed` ADR: tranche semantics, the three ladders and why those, the fit results, the cliff verdict
8. Figure registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] Tranche config and holder (AC: 1, 2)
  - [ ] Commit separately: `story 3.7: holder tranches`
- [ ] Fit three ladders (AC: 3, 4)
- [ ] Best ladder scenario, overlay, docs (AC: 5)
- [ ] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.7: multi-tranche holder and the cliff test`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.6 (Status: done)**

- One parameter fitted, everything else an assumption stated as such. Here the ladders are
  assumptions and `C*` is the one fitted number per ladder.
- Predictions below are predictions.
- The replay keeps `par` and the random-walk-free observed series; nothing from 3.6 touches
  it.

[Source: docs/stories/3-6-mean-reverting-reference.md#Senior-Developer-Review, F-09, ADR-0021, ADR-0024]

### Why ladders, not a fitted distribution

Fitting a distribution's shape to one observed trough is the hand-tuning the project has
refused since 2.4. Three fixed ladders bracket the plausible shapes (front-loaded,
uniform-wide, uniform-fine); if none lands closer than the single entry, that is the
answer. The ladder is the assumption; `C*` is the fit.

### Why the cap is per tranche

ADR-0024's fill-price cap stops the holder lifting the price above its entry. With several
entries, a 1% tranche must not lift the price above 0.99 while a 5% tranche is still
buying; each tranche caps against its own entry, from its own share of the reference.

### Predictions (to be checked)

- Ladder B or C lands within 5% of −1,373 (single entry: 17% short); A lands between.
- The cliff test shows a curve: trough changes by < 300 bps per 10% of `C*` for the best
  ladder, against the single entry's 7.5M → 10M jump of ≈ 2,000 bps.
- `C*` total for the best ladder is within 0.7–1.3× the single-entry 9,166,667.
- Trough timing moves by < 1 h.

### Cost

Three fits × ~17 runs of 33,600 steps: a few minutes each on 10 workers. One replay. The
cliff test: 10 runs.

### References

- [Source: docs/epics.md#Story-3.7]
- [Source: docs/FINDINGS.md] — F-08 confirmation, F-09, F-12
- [Source: docs/adr/0021-par-expecting-holder.md, 0024-holder-fill-price-limit.md]
- [Source: scripts/fit_holder.py]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-7-multi-tranche-holder.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: three fit tables, cliff test, replay, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: per-ladder C* and trough; cliff table; the limitations sentence; overlay description; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-07: Story drafted by dev manager after Story 3.6 review (second Epic 3 stretch story)
