# Story 4.1: Figure Pass and Freeze

Status: review

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

- [x] Policy panel and captions (AC: 1, 2)
- [x] Fits under the guard (AC: 3)
- [x] Note/figure set test (AC: 4)
- [x] Freeze checklist, tag (AC: 5, 6)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 4.1: figure pass and freeze`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

**Setup.** The story and context were on `origin/epic-3-close` (dev manager's commits
`2d977ac`, `eea8a39`), not on `main`; `main` was fast-forwarded to it (`git merge
--ff-only`, docs only) before starting.

**Fits re-run before `--write`, all reproduce the recorded values:**

```
$ python scripts/fit_reversion.py
phi = 0.6123  se = 0.0728  95% CI [0.4696, 0.7549]
unit-root stat (phi - 1) / se = -5.33 (Dickey-Fuller 5% critical -1.95): significantly below 1
kappa_step = 0.00163402  (interval 12 s, 300 steps/h)
half_life_h = 1.413
$ python scripts/fit_depth.py --workers 12 --output output/fits          # 2.4 s
D* = 16666667 (trough -1253.2 bps)
$ python scripts/fit_holder.py --workers 6 --output output/fits          # 16.6 s
C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
$ python scripts/fit_holder.py --tranches 2:0.25,5:0.25,10:0.25,20:0.25 --workers 6 --output output/fits
C* = 10833333 (trough -1323.3 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
```

**Price paid per stable (`_price_paid` on `output/policy-comparison-mc`, after `make figures`):**

```
            policy  capital    paid_mean  paid_p05  paid_p95
        calibrated  89727196       0.574     0.574     0.574
        calibrated  125618074      0.442     0.442     0.442
        calibrated  179454391      0.323     0.323     0.323
  early-aggressive  89727196       0.579     0.579     0.579
  early-aggressive  125618074      0.464     0.464     0.464
  early-aggressive  179454391      0.358     0.358     0.358
 late-conservative  89727196       0.552     0.552     0.552
 late-conservative  125618074      0.402     0.402     0.402
 late-conservative  179454391      0.283     0.283     0.283
 spread-only / no-defense          NaN (never buy)
```

**Freeze checklist (docs/REPRODUCIBILITY.md), top to bottom.**

1. `git status` on `main` before the run:
   ```
   On branch main
   nothing to commit, working tree clean
   ae0f39f story 4.1: policy panel (b) price paid, captions condition-first, fits under the guard, note figure set test
   ```
   and after the freeze commit: `76e7a1cf6a034f42d3e701b40d3cc3330303853d`, `git status
   --short | wc -l` → `0`.
2. Clean venv (`output/freeze-venv`):
   ```
   $ time python3.12 -m venv output/freeze-venv          real 0m1.085s
   $ time output/freeze-venv/bin/pip install -q --no-cache-dir -e ".[dev]"   real 0m40.410s
   Python 3.12.13
   matplotlib 3.11.2, numpy 2.5.3, pandas 3.0.6, pyarrow 25.0.1, pydantic 2.14.0,
   pytest 9.1.1, PyYAML 6.0.3, ruff 0.16.10
   ```
   (pydantic resolved to 2.14.0; Seoul's `.venv` has 2.13.5. Every pinned hash test
   passed on 2.14.0.)
3. `make test lint PYTHON=output/freeze-venv/bin/python`:
   ```
   TOTAL                                    956      9    99%
   Required test coverage of 85% reached. Total coverage: 99.06%
   907 passed in 38.47s
   output/freeze-venv/bin/python -m ruff check .
   All checks passed!
   output/freeze-venv/bin/python -m ruff format --check .
   101 files already formatted
   make exit 0
   ```
4. `make figures WORKERS=12` (646 GB free under `/home`):
   ```
   sweep sweeps/threshold-surface-ref-mc.yaml: wall time 143 s
   sweep sweeps/threshold-surface-mc.yaml: wall time 132 s
   sweep sweeps/budget-x-depth-mc.yaml: wall time 49 s
   sweep sweeps/oracle-lag-mc.yaml: wall time 118 s
   sweep sweeps/policy-comparison-mc.yaml: wall time 75 s
   sweep sweeps/holder-exit-1992-mc.yaml: wall time 19 s
   sweep sweeps/budget-x-attack-mc.yaml: wall time 59 s
   sweep sweeps/pace-x-trigger-mc.yaml: wall time 91 s
   sweep sweeps/pace-ratio-mc.yaml: wall time 25 s
   sweep sweeps/threshold-surface-ou-mc.yaml: wall time 136 s
   sweep sweeps/lp-flight-mc.yaml: wall time 51 s
   D* = 16666667 (trough -1253.2 bps)
   wrote docs/calibration/fits/depth.json
   C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-single.json
   C* = 10833333 (trough -1323.3 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
   wrote docs/calibration/fits/holder-ladder-b.json
   kappa_step = 0.00163402  (interval 12 s, 300 steps/h)
   wrote docs/calibration/fits/reversion.json
   fits: wall time 25 s
   make figures: wall time 934 s (12 workers)
   exit 0
   ```
   `git status --short` afterwards: `M docs/figures/manifest.json`, `M
   docs/figures/policy_comparison.png` (and the untracked ADR). `cmp` against copies taken
   before the run: `policy_comparison.png` CHANGED, the other 18 PNGs identical; the four
   fit records unchanged (not in `git status`).
5. Committed in `76e7a1c` (`story 4.1: freeze: regenerated figures and manifest
   (code_hash a0ae9594), ADR-0032 proposed`); manifest diff: every `commit` 6f2859d →
   ae0f39f, `code_hash` c72e8639… → a0ae9594….
6. `make figures-check`:
   ```
   .venv/bin/python scripts/check_figures.py
   figures-check: ok, 19 figures match their sources (code_hash matches)
   figures-check: ok, 4 fits match their inputs (script hashes match)
   exit 0
   ```
   No `WARNING` line.
7. Numbers re-read: 18 of 19 figures are byte-identical to the ones the captions, README
   and note were written against, so nothing they quote moved. `policy_comparison.png`'s
   new caption numbers come from the table above; panels (a) and (c) match the old caption
   (6.6 / 19.2 / 29.9 h, no-defense 49–59 h; inspected). Fit results are unchanged
   (D\*, both C\*, κ as in SOURCES.md). README "18 figures, 14 min" corrected to 19 and 15.
8. CI on `76e7a1c`, run
   [37860754187](https://github.com/tjdove/corposium-research/actions/runs/37860754187),
   checked by viewing the run:
   ```
   {"c":"success","jobs":[{"completedAt":"2026-10-08T23:42:44Z","conclusion":"success","name":"test","startedAt":"2026-10-08T23:40:46Z"},{"completedAt":"2026-10-09T00:03:00Z","conclusion":"success","name":"figures-quick","startedAt":"2026-10-08T23:40:47Z"}]}
   ```
   (Also green on `ae0f39f`, run 37859233442.)

**Tag.** Annotated tag created by the builder and pushed:
```
$ git push origin v0.9-freeze
 * [new tag]         v0.9-freeze -> v0.9-freeze
$ git rev-parse v0.9-freeze^{commit}
76e7a1cf6a034f42d3e701b40d3cc3330303853d
```

### Completion Notes List

- **Freeze commit `76e7a1cf6a034f42d3e701b40d3cc3330303853d`, tag `v0.9-freeze`.**
  `code_hash` `a0ae9594e7a4f6cc08e4c3e50540749dad4b24bd486a111421850f81c1c29150`. The
  commit that records this (the final story commit) touches only docs, so the code hash
  and every source hash are the same there (ADR-0032 §4).
- **Policy panel in words:** panel (b) is now the average price the defender paid per
  stable (spend / stable bought, per run, mean and p05–p95 over 16 seeds) for the three
  buying policies. The slow buyer pays least at every attack: late-conservative 0.552 /
  0.402 / 0.283 at 0.5 / 0.7 / 1.0×, calibrated 0.574 / 0.442 / 0.323, early-aggressive
  0.579 / 0.464 / 0.358. Every line falls as the attack grows (the same whole budget buys
  a cheaper, bigger pile), the band has no width (every seed pays the same price), and
  spread-only and no-defense, which never buy, are left out and named in the legend title.
  A dotted line marks par. Panel (a)'s title is now "hours to parity"; the heading names all
  three panels.
- **Fit files written** (`docs/calibration/fits/`, indexed in
  `docs/calibration/README.md`): `depth.json` (D\* = 16,666,667, −1,253.2 bps),
  `holder-single.json` (C\* = 9,166,667, −1,137.8 bps), `holder-ladder-b.json` (C\* =
  10,833,333, −1,323.3 bps), `reversion.json` (κ_step = 0.00163402). Each records the
  script and its sha256, scenario + `content_hash()`, data file + sha256, the arguments
  that set the fit and every point it ran; no timestamp, so `make figures` re-wrote all
  four byte-identically. `check_figures.py` fails on an input change or a missing input,
  warns on a script change; tested on tmp fit files with a changed scenario, data,
  script and a deleted input.
- **Captions** rewritten condition-first, no story or ADR numbers (a test checks), in two
  sections: "Figures in the note" (15) and "Record only" (the four AC 2 names, each with
  why it is kept).
- **Judgment calls (ADR-0032, Proposed):** (1) price paid per run from `sweep.parquet`,
  not a new `mc.py` metric (src frozen outside `charts.py`); (2) fit-record details;
  (3) **NOTE.md's figure-list table edited** (only the table and a Change Log line) to the
  15-figure note set that AC 2 implies; eight rows added, the four not used by the outline
  text marked † for the dev manager to keep or move to the record; (4) the freeze commit is
  the figures commit, the hash is written by the next commit.
- **For the dev manager:** the README's "Price or clock" result still shows
  `time_to_parity.png`, now record only (its numbers are right for it); swapping it for
  `time_to_parity_ou.png` is an editorial call. `docs/epics.md` AC 3 also says "each
  figure's footer carries scenario/sweep + hash": already true for all 19 (unchanged).
- No change under `src/depeg_sim/` other than `analysis/charts.py`; no scenario, sweep or
  data file changed; 18 figures byte-identical.

### File List

**Created:**

- `scripts/fit_record.py`
- `docs/calibration/README.md`
- `docs/calibration/fits/depth.json`, `holder-single.json`, `holder-ladder-b.json`, `reversion.json`
- `docs/adr/0032-figure-pass-fit-records-and-freeze.md`
- `tests/test_fit_record.py`, `tests/test_note_figures.py`

**Modified:**

- `src/depeg_sim/analysis/charts.py` (`_price_paid`, `plot_policy_comparison` panel (b), titles)
- `scripts/fit_depth.py`, `scripts/fit_holder.py`, `scripts/fit_reversion.py` (`--write`)
- `scripts/check_figures.py` (fit records, `--fits`)
- `Makefile` (`make figures` re-writes the fits)
- `docs/figures/README.md` (two sections, captions), `docs/figures/policy_comparison.png`, `docs/figures/manifest.json`
- `docs/NOTE.md` (figure-list table and Change Log only)
- `docs/REPRODUCIBILITY.md` (fit records, timings, code hash, checklist executed)
- `README.md` (figure count, make targets)
- `tests/test_policy_comparison.py` (synthetic `sweep.parquet`, `_price_paid` test)
- `docs/stories/4-1-figure-pass-and-freeze.md`

## Change Log

- 2026-10-08: Story drafted by dev manager at the Epic 3 retro
- 2026-10-08: Implemented (builder): policy panel (b) price paid, captions, fit records under the guard, note/figure set test, freeze checklist executed; freeze commit `76e7a1c`, tag `v0.9-freeze`; Status: review
