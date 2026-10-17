# Story 5.7: Re-freeze

Status: review

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

- [x] Checklist and `make figures` (AC: 1, 2)
- [x] Freeze commit and tag; hash commit, strict note-check, NOTE.md header (AC: 3)
- [x] Captions and figure-set (AC: 4)
- [x] Gates and CI (AC: 5)
- [x] Epic 5 retro draft (AC: 6)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commits `story 5.7: re-freeze` (figures) and `story 5.7: record freeze hash` (docs), pushed to `main` as in 4.1

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

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

**Setup.** Started from `main` at `e620d6a` (Story 5.4 merged, this story drafted in
`528122f`). Before anything ran, `output/` was emptied: everything except `.gitkeep` was
moved to `/home/dove/code/corposium-output-pre-5-7` (outside the repo, 63 GB), so every
sweep below ran from nothing.

**Blocker found and resolved by asking.** `check_note.py` required the note to name exactly
one freeze tag. `docs/NOTE.md` names `v0.9-freeze` three times: the header, §9 and a Change
Log line. With only the header changed, the check would fail with "must name one freeze tag",
so the story's two requirements (header line only; `make note-check` clean) could not
both hold. Tim chose: the header line's tag is compared on `code_hash`, every other tag the
note names must resolve but is not compared, and the NOTE.md edit stays at the header line
(ADR-0039, Proposed).

**Freeze checklist (docs/REPRODUCIBILITY.md), top to bottom.**

1. `git status` on `main` before the run:
   ```
   On branch main
   Your branch is up to date with 'origin/main'.
   Untracked files:
   	data(1)/
   nothing added to commit but untracked files present (use "git add" to track)
   e620d6a5794573450de608a72fbb4588ff7c1e0e
   ```
   (`data(1)/` is Tim's untracked directory, never committed; it is not under any manifest
   input path, see step 4.)
2. Clean venv (`/home/dove/code/freeze-venv-5-7`, outside the repo so `output/` stayed
   empty):
   ```
   $ time python3.12 -m venv $V                                   real 0m1.038s
   $ time $V/bin/pip install -q --no-cache-dir -e ".[dev]"        real 0m48.893s
   Python 3.12.13
   matplotlib 3.11.2, numpy 2.5.4, pandas 3.0.6, pyarrow 25.0.1, pydantic 2.14.1,
   pytest 9.1.1, PyYAML 6.0.3, ruff 0.17.1
   ```
   numpy 2.5.4, pydantic 2.14.1 and ruff 0.17.1 are newer than at the first freeze; every
   pinned hash test passed on them.
3. `make test lint PYTHON=$V/bin/python` (`TMPDIR` on disk):
   ```
   TOTAL                                    988     10    99%
   Required test coverage of 85% reached. Total coverage: 98.99%
   1029 passed in 234.86s (0:03:54)
   /home/dove/code/freeze-venv-5-7/bin/python -m ruff check .
   All checks passed!
   /home/dove/code/freeze-venv-5-7/bin/python -m ruff format --check .
   114 files already formatted
   make exit 0
   ```
4. `make figures WORKERS=12` from the empty `output/` (634 GB free under `/home`):
   ```
   sweep sweeps/threshold-surface-ref-mc.yaml: wall time 135 s
   sweep sweeps/threshold-surface-mc.yaml: wall time 135 s
   sweep sweeps/budget-x-depth-mc.yaml: wall time 49 s
   sweep sweeps/oracle-lag-mc.yaml: wall time 114 s
   sweep sweeps/policy-comparison-mc.yaml: wall time 74 s
   sweep sweeps/holder-exit-1992-mc.yaml: wall time 18 s
   sweep sweeps/budget-x-attack-mc.yaml: wall time 57 s
   sweep sweeps/pace-x-trigger-mc.yaml: wall time 92 s
   sweep sweeps/pace-ratio-mc.yaml: wall time 23 s
   sweep sweeps/threshold-surface-ou-mc.yaml: wall time 128 s
   sweep sweeps/lp-flight-mc.yaml: wall time 53 s
   sweep sweeps/usdc-par-depth-x-capital.yaml: wall time 16 s
   sweep sweeps/policy-comparison-gradual-mc.yaml: wall time 276 s
   sweep sweeps/lp-flight-disposal-mc.yaml: wall time 52 s
   wrote: 25 figures and docs/figures/manifest.json (commit e620d6a57945, code_hash 446e73ef88a9)
   D* = 16666667 (trough -1253.2 bps)
   wrote docs/calibration/fits/depth.json
   C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-single.json
   C* = 10833333 (trough -1323.3 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-ladder-b.json
   C* = 10833333 (trough -1279.2 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-ladder-b-par.json
   C* = 13333333 (trough -1007.0 bps) ≈ $3,127,999,922 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-ladder-b-closed.json
   kappa_step = 0.00163402  (interval 12 s, 300 steps/h)
   stationary_sd_bps (model, sigma 3.086e-05 with kappa_step) = 5.40
   wrote docs/calibration/fits/reversion.json
   fits: wall time 46 s
   make figures: wall time 1299 s (12 workers)
   exit 0
   ```
   The `make_figures.py` line said `commit e620d6a57945` but the manifest recorded
   `e620d6a…-dirty`. The cause was me: I edited `scripts/check_note.py` while the sweeps ran,
   and `scripts/` is one of the paths the manifest's dirty check covers. To get a clean
   `commit`, I set that edit aside (`git status --porcelain -- src scenarios sweeps scripts
   data pyproject.toml` → empty) and re-ran `python scripts/make_figures.py --workers 12`
   alone. It redraws from the sweeps already in `output/` and re-runs the 9 scenario
   figures; no sweep re-ran:
   ```
   wrote: 25 figures and docs/figures/manifest.json (commit e620d6a57945, code_hash 446e73ef88a9)
   real	0m30.746s
   ```
   Then I restored the edit. All 25 `commit` fields are now `e620d6a5794573450de608a72fbb4588ff7c1e0e`
   (no `-dirty`).
5. **What changed bytes.** `git status --short` after both runs: only
   `docs/figures/manifest.json` among generated files. **No PNG and no fit record changed
   bytes**: all 25 figures and all 6 fit records are byte-identical to the ones Epic 5's
   stories committed. The manifest diff is the `commit` field of every entry
   (`d775a38…-dirty` → `e620d6a…`), 25 lines each way; `code_hash` was already `446e73ef…`
   (Story 5.4). Committed in the freeze commit `467ea54` (below).
6. `make figures-check` (at `467ea54`, and again at the hash commit):
   ```
   figures-check: ok, 25 figures match their sources (code_hash matches)
   figures-check: ok, 6 fits match their inputs (script hashes match)
   ```
   No `WARNING` line.
7. **Numbers re-read.** No figure changed bytes, so no caption or note number moved. Count
   statements that were stale (none of them a result), corrected:
   - README: "all 19 committed figures and the 4 fit records: 15 min" → 25 / 6 / 22 min;
     "re-runs the four fits" → six.
   - `docs/figures/README.md`: "the eleven sweeps … the four fits (~15 min)" → fourteen /
     six / ~22 min.
   - `docs/REPRODUCIBILITY.md`: the timing table gains the three Epic 5 sweeps; totals
     1,299 s, 25 figures, 6 fits. The old run total (3,977) was off by one: the eleven
     sweeps sum to 3,976, and with the new three to 4,952. Also updated: the disk estimate
     (44 GB measured), the code hash, and the pinned summary sha256 `0085b134…`
     (`python run.py scenarios/soros-baseline.yaml` → `sha256sum` matched).
   - `docs/calibration/README.md`: the fit index had four rows; the two Epic 5 records
     (`holder-ladder-b-par`, `holder-ladder-b-closed`) were added from the records
     themselves.
   - Not changed (the story allows only the header line): NOTE.md §9 still says "Nineteen
     figures regenerate in about fifteen minutes" and "Code is frozen at `v0.9-freeze`",
     for the v2 rewrite.
8. CI, checked by looking at the runs:
   - **Freeze commit `467ea54`:** two runs, both green.
     - [39042906248](https://github.com/tjdove/corposium-research/actions/runs/39042906248), the push to `main`:
       ```
       {"c":"success","jobs":[{"completedAt":"2026-10-17T15:05:04Z","conclusion":"success","name":"test","startedAt":"2026-10-17T14:56:55Z"},{"completedAt":"2026-10-17T15:31:49Z","conclusion":"success","name":"figures-quick","startedAt":"2026-10-17T14:56:55Z"}]}
       ```
     - [39042906958](https://github.com/tjdove/corposium-research/actions/runs/39042906958), the tag push: `test` success at 15:10:26Z,
       `figures-quick` success at 15:14:43Z.
   - **Hash commit:** reported after the push (a commit cannot cite its own CI run).

**Gates at the freeze commit** (`.venv`, `make test lint figures-check note-check`):
```
TOTAL                                    988     10    99%
Required test coverage of 85% reached. Total coverage: 98.99%
1033 passed in 242.57s (0:04:02)
All checks passed!
114 files already formatted
figures-check: ok, 25 figures match their sources (code_hash matches)
figures-check: ok, 6 fits match their inputs (script hashes match)
note-check: WARNING: freeze: v0.9-freeze (76e7a1cf6a03) manifest has code_hash a0ae9594…, the working tree's has 446e73ef…
note-check: ok: freeze: v0.9-freeze is 76e7a1cf6a03 (code differs, see warning)
make exit 0
```
(The 4 new tests are in `tests/test_check_note.py`: 1,029 → 1,033.)

**Tag.** Annotated, created and pushed by the builder:
```
$ git push origin main
   e620d6a..467ea54  main -> main
$ git push origin v0.95-freeze
 * [new tag]         v0.95-freeze -> v0.95-freeze
$ git rev-parse 'v0.95-freeze^{commit}'
467ea54f063ab62c771ba335083ef2ec237eda5a
```

**Strict note-check at the hash commit** (`make note-check`, now `--strict-freeze`):
```
.venv/bin/python scripts/check_note.py --strict-freeze
note-check: ok: figures: 7 cited figures exist and are in the manifest
note-check: ok: cited: all 7 listed figures not marked † are cited; none of the 4 record-only figures is
note-check: ok: freeze: v0.95-freeze is 467ea54f063a, manifest code_hash 446e73ef88a9 matches; older tags named resolve: v0.9-freeze
note-check: ok: numbers: 8 fitted values quoted as their records round them
exit 0
```
No `WARNING` line.

### Completion Notes List

- **Freeze commit `467ea54f063ab62c771ba335083ef2ec237eda5a`, tag `v0.95-freeze`.**
  `code_hash` `446e73ef88a95ffbe7821dc1048b9c3249ed3e2f8176a29397351c3e4f1605a2`. 25
  figures and 6 fit records, all byte-identical to Epic 5's; only the manifest's `commit`
  fields changed.
- **Pushed directly to `main`** (as in 4.1), and only these two commits:
  `467ea54` `story 5.7: re-freeze` and the commit after it, `story 5.7: record freeze
  hash`. The tag was pushed between them, so CI on the hash commit can resolve
  `v0.95-freeze`.
- **What CI sees at each commit.**
  - **Freeze commit:** note-check is still non-strict and the note still names
    `v0.9-freeze`, so it warns and passes.
  - **Hash commit:** the header names `v0.95-freeze`, whose manifest has the working
    tree's `code_hash`, and `make note-check` passes `--strict-freeze`.

  Neither commit can fail on the freeze check.
- **The hash commit** changes nothing under `src/`, `scripts/`, `scenarios/`, `sweeps/` or
  `data/` (ADR-0032 ruling 4). It touches the NOTE.md header line, the Makefile
  (`note-check` strict, and its header comment), `docs/REPRODUCIBILITY.md` (the "Executed"
  paragraph), this story file and the retro.
- **Judgment calls (ADR-0039, Proposed):**
  1. The note's freeze tag is the one on its header line (the first line naming a tag);
     older tags must resolve and are not compared. This was Tim's choice; tests cover the
     header tag compared, a newer tag lower down ignored, an unresolved older tag, and two
     tags on the header line.
  2. Strictness lives in the Makefile, not only `ci.yml`, so a local `make note-check`
     and CI agree. **From now on any `src/depeg_sim/` change fails note-check until the
     next freeze**; the ADR says how to relax it.
- **Captions (AC 4).** Of the six figures added in Epic 5, five already led with what was
  fed in or held fixed. `lp_flight_disposal.png` led with its conclusion and now leads with
  "At D\* (8 seeds per cell), with the fleeing liquidity provider's panic threshold held at
  5%, one column per what it does…". `tests/test_note_figures.py` passes (the figure-set
  test).
- **The retro (AC 6)** is drafted at `docs/retrospectives/epic-5-retro.md`. AC 6 says "the
  seven predictions"; I find six prediction blocks (one in each of 5.1–5.6) and 17
  claims. The retro says so and counts per block from the reviews, rather than inventing a
  seventh.
- **For the dev manager:**
  - NOTE.md §9 ("Nineteen figures … about fifteen minutes", "Code is frozen at
    `v0.9-freeze`") is stale, left for v2.
  - The retro's housekeeping list includes two broken ADR links in FINDINGS.md (not
    edited, per CLAUDE.md).
  - `make figures-quick` timings in REPRODUCIBILITY were last measured with 19 figures.
  - `output/` before this story is at `/home/dove/code/corposium-output-pre-5-7` (63 GB),
    for Tim to delete or keep.

### File List

**Created:**

- `docs/adr/0039-re-freeze-header-tag.md`
- `docs/retrospectives/epic-5-retro.md`

**Modified (freeze commit `467ea54`):**

- `scripts/check_note.py` (header-tag rule), `tests/test_check_note.py` (4 tests, one
  message)
- `docs/figures/manifest.json` (`commit` fields), `docs/figures/README.md`
  (`lp_flight_disposal` caption, `make figures` line)
- `docs/REPRODUCIBILITY.md` (timings, counts, hashes), `README.md` (counts),
  `docs/calibration/README.md` (two fit rows, counts)

**Modified (hash commit):**

- `docs/NOTE.md` (header line only)
- `Makefile` (`note-check --strict-freeze`, header comment)
- `docs/REPRODUCIBILITY.md` ("Executed 2026-10-17" paragraph)
- `docs/stories/5-7-re-freeze.md`

## Change Log

- 2026-10-17: Story drafted by dev manager (Epic 5 close)
- 2026-10-17: Implemented (builder): `make figures` from an empty `output/` (1,299 s, all 25 figures and 6 fits byte-identical); freeze commit `467ea54`, tag `v0.95-freeze`; note-check header-tag rule and `--strict-freeze` (ADR-0039 proposed); NOTE.md header line; Epic 5 retro drafted; Status: review
