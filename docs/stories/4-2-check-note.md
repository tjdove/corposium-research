# Story 4.2: Research Note — `check_note.py`

Status: ready-for-dev

## Story

As a **reader of the note**,
I want a script that proves every figure and every fitted number the note cites is the one in the repository,
so that the note cannot silently drift from the frozen code.

The note itself (`docs/NOTE.md` v1.0) is already written by the dev manager and merged (PR #38).
This story is the **builder task only**: the checker. Do not edit the note's prose. If a check
you write fails against the current note, that is a result: record it in the Dev Agent Record
and block; do not change the note or the fit record to make it pass.

## Acceptance Criteria

1. `scripts/check_note.py [--note docs/NOTE.md] [--manifest docs/figures/manifest.json] [--fits docs/calibration/fits]` exits 0 with one `ok:` line per check, or exits 1 naming each failure. No new dependencies.
2. **Figures.** Every `figures/<name>.png` referenced in the note (markdown image or link) exists on disk and is a key in `manifest.json`; every figure in the note's figure-list table is referenced at least once in the note body (image or link) — a listed-but-uncited figure is a failure. The four record-only figures named in `docs/figures/README.md` must not be cited.
3. **Freeze.** The tag the note cites (`v0.9-freeze`, found by regex `v\d+\.\d+-freeze`) resolves (`git rev-parse`) to a commit whose `docs/figures/manifest.json` has the same `code_hash` as the working tree's manifest. If git is unavailable, warn, do not fail.
4. **Numbers.** A table in the script maps each fit record to the values the note quotes from it, with a rounding rule, and the check fails if the note's text does not contain the rounded value. At minimum:
   - `holder-single.json`: `c_star_usd` → `$2.15B`; the trough at `c_star` from `runs` → `−1,138 bps` (round half up to integer, thin-space/minus-sign tolerant); time of trough **not** checked (not in the record).
   - `holder-ladder-b.json`: `c_star_usd` → `$2.54B`; trough → `−1,323 bps`.
   - `depth.json`: `d_star` → not quoted in dollars in the note; check instead that `D\*` appears and that `16,666,667` appears **nowhere** in the note (the note deliberately uses the symbol) — a warn, not a fail.
   - `reversion.json`: `half_life_h` → `1.4 h`.
   The ratio `c_star_usd / attacker_usd` (attacker $2.71B, constant in the script with its source comment) → `0.79×` and `0.94×`.
5. `make note-check` target; added to the CI job line alongside `figures-check`.
6. `tests/test_check_note.py`: a synthetic note + manifest + fits directory in `tmp_path`, one passing case, and one failing case per check (missing figure, uncited listed figure, record-only cited, wrong number). Run the real check once in a test too (`subprocess`, exit 0).
7. `pytest`, `ruff check .` green; `make figures-check` still clean (no change under `src/`, `scenarios/`, `sweeps/`, `docs/figures/`).

## Tasks / Subtasks

- [ ] Figure checks (AC: 1, 2)
- [ ] Freeze check (AC: 3)
- [ ] Number table (AC: 4)
- [ ] Make + CI (AC: 5)
- [ ] Tests (AC: 6, 7)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 4.2: check_note.py`, push branch `story/4-2-check-note`

## Dev Notes

### Learnings from Previous Story

**From Story 4.1 (Status: done)**

- The code is frozen. This story touches `scripts/`, `tests/`, `Makefile`, `.github/` only.
  `code_hash` in the manifest covers `src/` — confirm with `make figures-check` before pushing.
- Fit records have no timestamp; their `result` dicts are the ground truth for AC 4. Read
  `scripts/fit_record.py` for the schema rather than guessing.
- `tests/test_note_figures.py` already compares the figure-list table with `docs/figures/README.md`.
  Reuse its table parser (import it or lift it into a shared helper under `scripts/`); do not
  write a second one.

[Source: docs/stories/4-1-figure-pass-and-freeze.md#Senior-Developer-Review, docs/adr/0032]

### Rounding

The note prints bps as `−1,138` with a Unicode minus (U+2212) and a comma. Normalise both the
note and the computed string (strip U+2009/U+202F, map U+2212 → `-`) before comparing. Dollars:
`c_star_usd / 1e9` to two decimals, prefixed `$`, suffixed `B`.

### What a failure means

The checker is a guard, like `check_figures.py`. If it fails on the committed note, either the
note or the record is wrong, and the dev manager decides which. Block with the failing line.

### References

- [Source: docs/epics.md#Story-4.2]
- [Source: docs/NOTE.md] — the text under check
- [Source: scripts/check_figures.py] — pattern to follow (`ok:` lines, exit codes)
- [Source: docs/calibration/fits/*.json]

## Dev Agent Record

## Change Log

- 2026-10-09: Story drafted by dev manager after NOTE.md v1.0 merged (PR #38)
