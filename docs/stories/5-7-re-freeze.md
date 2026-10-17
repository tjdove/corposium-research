# Story 5.7: Re-freeze

Status: ready-for-dev

## Story

As a **reader of note v2**,
I want every figure and fit record the note cites regenerated from one tagged commit, with the guard strict again,
so that the second freeze is as clean as the first.

## Acceptance Criteria

1. `docs/REPRODUCIBILITY.md` "Before the freeze" checklist executed again, every box
   ticked with command output in the Debug Log; a new "Executed 2026-10-XX (Story 5.7)"
   paragraph below the first, same shape: commit, tag **`v0.95-freeze`**, code hash,
   figure count, fit count, `make figures` wall time, which PNGs changed bytes (expected:
   none; say so if any did and why).
2. `make figures` run once from a clean `output/`; all committed PNGs, `manifest.json`
   and all six fit records regenerated and committed. The 25 existing figures and 6 fit
   records are expected byte-identical; list any that are not.
3. The freeze commit is the figures commit, tagged `v0.95-freeze` (Tim pushes the tag if
   the builder cannot). The next commit records the hash (ADR-0032 ruling 4) and switches
   CI's note-check to `--strict-freeze`; `docs/NOTE.md`'s header line is changed by the
   builder from `v0.9-freeze` to `v0.95-freeze` **and nothing else in the note** (the dev
   manager rewrites it for v2 against this tag). `make note-check` is clean with no
   warning at that commit.
4. `docs/figures/README.md` and the note's figure list match (figure-set test); every
   caption of a figure added in Epic 5 leads with what was fed in or held fixed.
5. `make test lint`, `make figures-check`, `make note-check --strict` (or however the
   Makefile spells it) all clean; CI green on both commits.
6. `docs/retrospectives/epic-5-retro.md` **drafted by the builder** this once (the dev
   manager amends in review): stories 5.1–5.7 with dates, the seven predictions and how
   many held (count from the reviews), what the referee asked for and which story
   answered it (map to review §5 item numbers), carry-overs (trigger-separation sweep;
   belief-as-a-process holder; multi-venue), and anything about the process the builder
   wants the dev manager to hear.

## Tasks / Subtasks

- [ ] Checklist and `make figures` (AC: 1, 2)
- [ ] Freeze commit and tag; hash commit, strict note-check, NOTE.md header (AC: 3)
- [ ] Captions and figure-set (AC: 4)
- [ ] Gates and CI (AC: 5)
- [ ] Epic 5 retro draft (AC: 6)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commits `story 5.7: re-freeze` (figures) and `story 5.7: record freeze hash` (docs), pushed to `main` as in 4.1

## Dev Notes

### Learnings from Previous Story

- 4.1's Debug Log is the template; the freeze commit cannot contain its own hash
  (ADR-0032 ruling 4).
- `make figures` is now ~17 min on Seoul (25 figures incl. the 720-run policy sweep
  reused from `output/` if present — check whether the Makefile re-runs it; if it does,
  budget 25 min).
- The builder fast-forwards main as in 4.1 only for the two freeze commits; everything
  else in this epic went through PRs. Say in the Dev Agent Record which commits were
  pushed directly.
- `check_note.py --strict-freeze` will fail until the NOTE.md header names the new tag;
  order the commits so CI is green at each.

### References

- [Source: docs/stories/4-1-figure-pass-and-freeze.md] — the first freeze
- [Source: docs/adr/0032-figure-pass-fit-records-and-freeze.md] — ruling 4
- [Source: docs/REPRODUCIBILITY.md#Before-the-freeze]
- [Source: docs/retrospectives/epic-3-retro.md] — retro shape

## Dev Agent Record

## Change Log

- 2026-10-17: Story drafted by dev manager (Epic 5 close)
