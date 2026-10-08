# Story 4.1: Figure Pass and Freeze

Status: in-progress

## Story

As a **reader**,
I want every figure the note uses to be final, captioned, and regenerable, and the code frozen behind them,
so that the note can be written against figures that will not change.

## Acceptance Criteria

1. `plot_policy_comparison` panel (b) becomes **average price paid per stable** (`defender_spent / defender_bought_stable`, mean with p05–p95, one line per buying policy; no-defense and spread-only omitted from that panel with a legend note); panel titles and the heading updated; the figure regenerated
2. `docs/figures/README.md` captions rewritten in the note's voice: one sentence naming what the reader is looking at, **the condition first** where a finding has one (F-14, F-15), no story or ADR numbers; `threshold_surface_par.png`, `threshold_surface.png` (random-walk, oracle criterion), `time_to_parity.png` (random-walk) and `holder_exit.png` moved to a "Record only" section of the README with one line each saying why they exist
3. **Fits under the guard:** `scripts/fit_depth.py`, `scripts/fit_holder.py` (run twice: single entry and ladder B) and `scripts/fit_reversion.py` gain `--write docs/calibration/fits/<name>.json` recording inputs (scenario path + hash, data file + sha256, arguments), the result, and the script file's sha256; `scripts/check_figures.py` also verifies each fit file's inputs still hash the same (fail) and script hash (warn); `make figures` writes them; `docs/calibration/README.md` lists them
4. `docs/NOTE.md`'s figure list and `docs/figures/README.md`'s note set match one-to-one (a test reads both)
5. `docs/REPRODUCIBILITY.md` freeze checklist executed: every box ticked with the command output pasted in the Debug Log; the freeze commit hash written into the checklist; git tag `v0.9-freeze` on that commit (Tim pushes the tag if the builder cannot)
6. `pytest`, `ruff check .`; `make figures` and `make figures-check` clean (code hash matches); both CI jobs green

## Tasks / Subtasks

- [ ] Policy panel and captions (AC: 1, 2)
- [ ] Fits under the guard (AC: 3)
- [ ] Note/figure set test (AC: 4)
- [ ] Freeze checklist, tag (AC: 5, 6)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 4.1: figure pass and freeze`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.8 (Status: done) and the Epic 3 retro**

- No new mechanics. If anything here needs a model change, stop and say so.
- Captions lead with the condition the finding depends on.
- `make figures` is ~15 min on Seoul; run it once at the end, not per change.

[Source: docs/retrospectives/epic-3-retro.md, docs/stories/3-8-lp-withdrawal-agent.md#Senior-Developer-Review]

### What "final" means

After this story the code hash in the manifest is the one the note cites. Any later change
to `src/` before Nov 1 is a bug fix, re-runs `make figures`, and is recorded in the note's
change log.

### References

- [Source: docs/epics.md#Story-4.1]
- [Source: docs/NOTE.md] — figure list
- [Source: docs/stories/3-2-defender-policy-comparison.md#Senior-Developer-Review] — ruling 4
- [Source: docs/stories/3-5-hardening-and-polish.md#Senior-Developer-Review] — ruling 6

## Dev Agent Record

### Context Reference

- [Story Context XML](./4-1-figure-pass-and-freeze.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(the freeze checklist output, `make figures` time, guard, tests, CI)_

### Completion Notes List

_(include: the freeze commit hash; the fit files written; the policy panel in words)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-08: Story drafted by dev manager at the Epic 3 retro
