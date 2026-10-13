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

## Blockers

`make note-check` fails on the committed `docs/NOTE.md` (v1.0, `561e7ff`): AC 2's
listed-but-uncited check. The figure-list table lists 15 figures in the note; the body
(everything above `## Figure list`) links or embeds 6 of them. The other 9 are never
cited:

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
```

The failing lines are the figure-list rows at `docs/NOTE.md` lines 309, 311, 312, 313,
314, 316, 317, 318 and 321 (at `561e7ff`), the first being
`| — | \`peg_trajectory_calibrated.png\` † | 4 | F-06, F-03 | final |`. Five of the nine are
the † rows or "(supporting)" rows; `peg_trajectory_1992_no_defense.png` is Figure 5b, and
the body's only mention of it is line 223, Figure 5's caption, with no link: "The
no-defense counterfactual is in the repository."

Every other check passes against the note: the 6 cited figures exist and are in the
manifest; no record-only figure is cited; `v0.9-freeze` resolves to `76e7a1c` whose
manifest `code_hash` (a0ae9594…) is the working tree's; all 8 fitted values are quoted as
their records round them ($2.15B, −1,138 bps, 0.79×, $2.54B, −1,323 bps, 0.94×, 1.4 h,
and D\* as a symbol with 16,666,667 absent).

Per the story ("do not change the note or the fit record to make it pass") I changed
neither. Ways to clear it, for the dev manager: link each of the nine from the body
(e.g. "([figure](figures/budget_depth.png))", as §6 does for `oracle_sensitivity.png`);
or move the uncited ones to "record only" in both NOTE.md's list and
`docs/figures/README.md` (which also changes Story 4.1's four-figure record set and
`tests/test_note_figures.py::test_note_and_readme_record_sets_match`); or rule that
supporting figures need not be cited, and I narrow the check. Until then
`tests/test_check_note.py::test_the_committed_note_passes` is `xfail(strict=True)` (it
will XPASS-fail the suite once the note passes, so the mark has to come off), and CI's
`test` job will fail at `make note-check` (AC 5 puts it on the CI line).

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
