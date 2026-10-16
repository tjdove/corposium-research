# Story 4.2: Research Note — `check_note.py`

Status: blocked

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

- [x] Figure checks (AC: 1, 2)
- [x] Freeze check (AC: 3)
- [x] Number table (AC: 4)
- [x] Make + CI (AC: 5)
- [x] Tests (AC: 6, 7)
  - [ ] Dev Agent Record, Change Log, `Status: review` (Dev Agent Record and Change Log
        done; `Status: blocked`, see Blockers)
  - [ ] Commit `story 4.2: check_note.py`, push branch `story/4-2-check-note` (committed
        on the branch; not pushed while blocked)

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

## Rulings (dev manager, 2026-10-15, second round)

1. **"(supporting)" rows.** Marked † in `docs/NOTE.md` by the dev manager (PR #43). No
   change to the check: † in the file cell is the only exemption, as you built it.
2. **Freeze tag behind the code.** Expected during Epic 5: the freeze is lifted, the code
   hash moves, the note still names the tag its figures came from. Ruling: the freeze
   check **fails** if the named tag does not resolve or has no manifest, and **warns**
   (exit 0, one `warn:` line naming both hashes) when the tag's `code_hash` differs from
   the working tree's. Add `--strict-freeze` that turns the warning into a failure; CI
   does **not** pass it now; the re-freeze story at the end of Epic 5 will cite the new
   tag in the note and switch CI to `--strict-freeze`. Update the test accordingly
   (`test_the_committed_note_passes` should pass, not xfail, once PR #43 is on main).
3. Rebase on main after #43 merges, apply ruling 2, re-run `make note-check`, set
   `Status: review`, push.

## Blockers

**Re-blocked 2026-10-15, after the Story 5.1 review's ruling 4.** The ruling is applied:
rows whose file cell is marked † are exempt from the listed-but-uncited check, every
other listed row must be cited. Rebased on `main` at `7a37100` (NOTE.md with 1c/1d † and
5b linked). `make note-check` on that note still exits 1, on two things the ruling does
not cover:

```
note-check: FAIL: cited: budget_depth.png is in the figure list but never cited in the body
note-check: FAIL: cited: budget_attack.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_trigger.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_ratio.png is in the figure list but never cited in the body
note-check: FAIL: freeze: v0.9-freeze (76e7a1cf6a03) manifest has code_hash a0ae9594e7a4f6cc08e4c3e50540749dad4b24bd486a111421850f81c1c29150, the working tree's has 555833b72e0dbe565106ff13c3f2e7042d127715867712c2a490edb764aaa207
note-check: FAIL, 5 problem(s) in docs/NOTE.md
```

1. **Four "(supporting)" rows without †.** `budget_depth.png`, `budget_attack.png`,
   `pace_trigger.png`, `pace_ratio.png` say "4 (supporting)" / "5 (supporting)" in the
   section column but carry no † in the file cell, and the body never links them. Under
   the ruling as written ("every non-† row must be cited") they fail. Ways to clear it:
   mark them † in NOTE.md, link them from the body, or rule that "(supporting)" in the
   section column also exempts a row (a one-line change to `note_tables.supporting`; I
   did not make it, as the ruling names † only).
2. **Freeze tag is behind the code.** Story 5.1 changed `src/` (the two-series overlay),
   so the manifest's `code_hash` is now `555833b7…` and `v0.9-freeze` points at
   `a0ae9594…`. This is new since the first block (it passed at `561e7ff`). It clears
   when the note names a freeze tag at or after Story 5.1's figures commit (e.g. a
   `v1.0-freeze` for note v2), which is the dev manager's and Tim's call, not this story's.

I changed neither the note nor any tag. `test_the_committed_note_passes` stays
`xfail(strict=True)` with the reason updated.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code.

### Debug Log References

Branch `story/4-2-check-note` from `main` at `561e7ff`.

`python scripts/check_note.py` on the committed note (exit 1; the blocker):

```
note-check: FAIL: cited: peg_trajectory_calibrated.png is in the figure list but never cited in the body
note-check: FAIL: cited: threshold_surface_ou.png is in the figure list but never cited in the body
note-check: FAIL: cited: budget_depth.png is in the figure list but never cited in the body
note-check: FAIL: cited: budget_attack.png is in the figure list but never cited in the body
note-check: FAIL: cited: lp_flight.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_trigger.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_ratio.png is in the figure list but never cited in the body
note-check: FAIL: cited: peg_trajectory_baseline.png is in the figure list but never cited in the body
note-check: FAIL: cited: peg_trajectory_1992_no_defense.png is in the figure list but never cited in the body
note-check: FAIL, 9 problem(s) in docs/NOTE.md
note-check: ok: figures: 6 cited figures exist and are in the manifest
note-check: ok: freeze: v0.9-freeze is 76e7a1cf6a03, manifest code_hash a0ae9594e7a4 matches
note-check: ok: numbers: 8 fitted values quoted as their records round them
make: *** [Makefile:51: note-check] Error 1
```

`make figures-check` (no change under `src/`, `scenarios/`, `sweeps/`, `docs/figures/`):

```
.venv/bin/python scripts/check_figures.py
figures-check: ok, 19 figures match their sources (code_hash matches)
figures-check: ok, 4 fits match their inputs (script hashes match)
```

`pytest`:

```
931 passed, 1 xfailed in 23.89s
```

`make test`:

```
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
931 passed, 1 xfailed in 42.14s
```

`ruff check .` / `ruff format --check .`:

```
All checks passed!
104 files already formatted
```

CI was not run: the branch is not pushed while blocked, and with `note-check` on the CI
line (AC 5) the `test` job would fail on the committed note.

**Re-run after the Story 5.1 ruling (2026-10-15).** Rebased on `main` at `7a37100`;
† exemption added. `make note-check` (exit 1, see Blockers):

```
note-check: FAIL: cited: budget_depth.png is in the figure list but never cited in the body
note-check: FAIL: cited: budget_attack.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_trigger.png is in the figure list but never cited in the body
note-check: FAIL: cited: pace_ratio.png is in the figure list but never cited in the body
note-check: FAIL: freeze: v0.9-freeze (76e7a1cf6a03) manifest has code_hash a0ae9594e7a4f6cc08e4c3e50540749dad4b24bd486a111421850f81c1c29150, the working tree's has 555833b72e0dbe565106ff13c3f2e7042d127715867712c2a490edb764aaa207
note-check: FAIL, 5 problem(s) in docs/NOTE.md
note-check: ok: figures: 7 cited figures exist and are in the manifest
note-check: ok: numbers: 8 fitted values quoted as their records round them
```

`make test`, `ruff check .`, `make figures-check`:

```
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
947 passed, 1 xfailed in 66.08s (0:01:06)
All checks passed!
figures-check: ok, 21 figures match their sources (code_hash matches)
figures-check: ok, 4 fits match their inputs (script hashes match)
```

### Completion Notes List

- **`scripts/check_note.py`** follows `check_figures.py`: argparse (`--note`, `--manifest`,
  `--fits`), `note-check: ok: <check>: …` on stdout per passing check, `note-check: FAIL:
  …` per failure on stderr and exit 1, warnings on stderr (and `::warning::` under GitHub
  Actions). The ok lines for passing checks print even when another check fails, so a
  failing run still shows what passed. Four checks: `figures`, `cited`, `freeze`,
  `numbers`. No new dependencies; it runs no simulation.
- **Figures.** A citation is a markdown link or image target `figures/<name>.png` (`](…)`).
  "Is a key in manifest.json" is checked as the file's stem being a key (keys are the
  stems; `code_hash` excluded). Files resolve beside the note (`<note dir>/figures/`).
  The figure-list table's backticked names are not citations, and the body is the text
  above `## Figure list`, so the table cannot cite itself. The record-only set is read from
  the README beside the manifest; a record-only figure linked anywhere in the note fails.
- **Freeze.** The note must name exactly one `v\d+\.\d+-freeze` tag. It is resolved with
  `git rev-parse --verify <tag>^{commit}` (the tag is annotated) and the manifest read
  at that commit with `git show <sha>:./manifest.json` from the manifest's directory.
  Warn, not fail, when git is not installed or the note is not in a git work tree (e.g. a
  source tarball); fail when the tag does not resolve or `code_hash` differs. CI's `test`
  job now checks out with `fetch-depth: 0` so the tag is present.
- **Numbers.** `NUMBERS` maps a fit file and a function of its `result` to a rounding
  rule: dollars `$x.xxB` (`/1e9`, 2 dp), bps integer with thousands commas, ratio `x.xx×`,
  hours `x.x h`. Rounding is `Decimal` `ROUND_HALF_UP` (ties away from zero). The trough is
  the `max_depeg_bps` of the `runs` entry whose `holder_capital` is `c_star`. The attacker
  constant `ATTACKER_USD = 2.71e9` carries its SOURCES.md source comment. Normalisation as
  the Dev Notes say (U+2212 → `-`, U+2009/U+202F removed), plus whitespace runs collapsed
  to one space, because the note breaks "−1,138 bps" across a line. A number matches only
  whole (no digit/comma/point before it, no digit after); the unit may follow with or
  without a space.
- **Depth.** AC 4 says "a warn, not a fail" for D\*. I read it as: `16,666,667` printed in
  the note warns; the symbol D\* missing fails (it is the check that replaces the number).
  If the dev manager meant both to warn, it is a one-line change.
- **Shared parser.** The table parser in `tests/test_note_figures.py` moved to
  `scripts/note_tables.py` (`section`, `table_files`, `note_sets`, `readme_sets`);
  the test now imports it, unchanged in behaviour (its 6 tests pass).
- **Real-note test.** `test_the_committed_note_passes` runs the script with `subprocess`
  and asserts exit 0 and four ok lines; it is `xfail(strict=True)` with the blocker as the
  reason, so it turns red once the note passes and the mark must be removed.
- No change under `src/`, `scenarios/`, `sweeps/`, `docs/figures/`, nor to `docs/NOTE.md`
  or any fit record. No ADR: the judgment calls are local to the script and listed above.

- **† exemption (Story 5.1 review, ruling 4).** `note_tables.supporting(note)` returns
  the figure-list files whose file cell contains `†`; `check_cited` skips them, and its
  ok line now reads "all N listed figures not marked † are cited". Only the file cell is
  read: "(supporting)" in the section column does not exempt a row (tested both ways).

### File List

- `scripts/check_note.py` (new)
- `scripts/note_tables.py` (new; parser lifted from `tests/test_note_figures.py`)
- `tests/test_check_note.py` (new)
- `tests/test_note_figures.py` (imports the shared parser)
- `Makefile` (`note-check` target)
- `.github/workflows/ci.yml` (`note-check` on the `test` job line; `fetch-depth: 0`)
- `docs/stories/4-2-check-note.md`

## Change Log

- 2026-10-09: Story drafted by dev manager after NOTE.md v1.0 merged (PR #38)
- 2026-10-12: Builder: `check_note.py`, `note-check` target and CI line, tests. Blocked: the committed note's body cites 6 of its 15 listed figures (see Blockers).
- 2026-10-15: Builder: rebased on `main` (7a37100); † rows exempt from the listed-but-uncited check (ruling 4 of the Story 5.1 review). Still blocked: 4 "(supporting)" rows without † are uncited, and `v0.9-freeze` no longer matches `code_hash` after Story 5.1 (see Blockers).
