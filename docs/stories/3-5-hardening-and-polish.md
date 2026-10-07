# Story 3.5: Test Hardening, Repo Polish, and the Pace-Ratio Sweep

Status: done

## Story

As a **reader**,
I want to clone the repo and reproduce every figure and number without asking anyone,
so that the note's claims are auditable by a stranger — and the last uncommitted result (the pace ratio) is in the record.

## Acceptance Criteria

1. **Pace-ratio sweep** (3.4 review ruling 3): `sweeps/pace-ratio-mc.yaml` — base `calibrated-baseline.yaml`, oracle criterion, attacker ratio 1.0, trigger 1%; axes `agents[type=defender].spend_pace ∈ {0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1}` × `agents[type=attacker].pace ∈ {0.02, 0.1}`; 8 seeds; `plot_pace_ratio(sweep_dir)`: one panel, median time-to-parity (hours from run start) against defender pace / attacker pace on a log x-axis, one line per attacker pace, "never" at the top with open markers, the 37 h deadline dashed; registered as a figure; Completion Notes state the ratio at which each line crosses 37 h
2. **Summary fields:** `summarize` gains `arbitrageur_redeemed` (3.2 review ruling 5); `scripts/policy_table.py` reads it from the summary instead of `events.jsonl`; run-vs-rerun byte tests unchanged in intent (fixtures updated once, with the diff shown)
3. **Guard:** `docs/figures/manifest.json` gains `code_hash` (sha256 over the sorted contents of `src/depeg_sim/**/*.py`); `scripts/check_figures.py` **warns** (exit 0, message naming the hash) on a code-hash mismatch and **fails** on a source mismatch; `make figures` writes the current code hash; `docs/REPRODUCIBILITY.md` has a "before the freeze" checklist that includes `make figures` and a clean guard
4. **Makefile:** `PYTHON` defaults to `.venv/bin/python` when it exists, else `python`; documented in the README make section (2.9 review ruling 6)
5. **Coverage ≥ 85%** on `src/depeg_sim/protocol/` and `src/depeg_sim/agents/` (`pytest --cov`, report pasted); property-style tests (plain pytest parametrisation is fine, no new dependency): AMM `k` non-decreasing over random trade sequences from a seeded `Generator`, redemption accounting (requested = paid + queued + rejected) over random request sequences, both termination criteria at their edges (exactly `for_steps` in band; one step short; `reference: oracle` with no oracle registered)
6. **README** rewritten for a stranger: what this is in three sentences; quick start with expected output; "Results so far" kept; scenario reference table (every file in `scenarios/` and `scenarios/policies/`, one line each: name, what it is, `content_hash()` first 12); sweep reference table (every file in `sweeps/`, runs, wall time on Seoul); make targets; figure index pointing at `docs/figures/README.md`; links to FINDINGS, NOTE outline, BACKGROUND, ADR index, PROCESS, LITERATURE; license
7. **`CONTRIBUTING.md`**: the story process in one page (story file is the contract; builder/dev-manager roles; blocked means blocked), the determinism rule, how to add a scenario (header conventions, status lines, hash pin), how to add a sweep, how to add a figure (manifest, guard)
8. **`docs/REPRODUCIBILITY.md`**: Python version, install on a clean 3.12 venv with timing, every command that produces a figure with wall time on a named machine (Seoul, 12 workers) and on CI (4 workers), the hashes that must match, the `TMPDIR` note (sweeps write ~2 GB per 200 runs; use `output/`, set `TMPDIR` to a large disk for agent sessions), the "before the freeze" checklist
9. **Dependency pins** reviewed; `pyproject.toml` upper bounds where a major version would break (numpy, pandas, pyarrow, matplotlib, pydantic); CI unchanged
10. `make figures` (pace-ratio added); guard green with the new code hash; `pytest` and `ruff check .` pass; both CI jobs green; Proposed ADR only if a design decision was made (the guard semantics qualify)

## Tasks / Subtasks

- [x] Pace-ratio sweep and chart (AC: 1)
  - [x] Commit separately: `story 3.5: pace-ratio sweep`
- [x] Summary field and policy table (AC: 2)
- [x] Guard and Makefile (AC: 3, 4)
- [x] Coverage and property tests (AC: 5)
- [x] README, CONTRIBUTING, REPRODUCIBILITY, pins (AC: 6, 7, 8, 9)
- [x] Close out (AC: 10)
  - [x] `pytest --cov`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.5: hardening, polish, pace-ratio`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.4 (Status: done)**

- A committed grid that reads all-"never" is not the figure; AC 1 commits the probe that
  shows the gradient.
- Every "outcome" candidate turned out to be conservation; the README's results section
  quotes inputs (depth, budget, attack, pace) only.
- `make figures` after any agent or chart change; after this story the guard will at least
  warn when code changed.

[Source: docs/stories/3-4-budget-vs-attack.md#Senior-Developer-Review, F-11 and F-13 refinements]

### Why warn, not fail, on code hash

A code change that does not touch a figure's numbers (a docstring, a test) would otherwise
block CI until a 7-minute regeneration; a change that does touch them is caught at the
freeze by the checklist. The warning is loud and names the hash so a reviewer can't miss
it; the freeze checklist is the hard gate.

### What the README is for

A crypto researcher lands on it from the launch thread. In thirty seconds they should know
what the thing is, see one figure, and know the one command that regenerates everything.
Everything else is a link. No story numbers, no ADR numbers in the README body.

### Cost

Pace-ratio: 14 cells × 8 seeds = 112 runs, ≈ 1 min on 10 workers. Coverage run: the test
suite plus `--cov` ≈ 2 min. The rest is writing.

### References

- [Source: docs/epics.md#Story-3.5]
- [Source: docs/stories/2-9-committed-figures.md] — guard design
- [Source: docs/PROCESS.md] — the process CONTRIBUTING.md summarises
- [Source: docs/adr/0027-*.md] — the slow-attack probe table AC 1 commits

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-5-hardening-and-polish.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

All commands run on Seoul (12 cores, Python 3.12.13, `.venv`), 2026-10-06.

**AC 1: pace-ratio sweep** (first commit `58adfb2`, `story 3.5: pace-ratio sweep`):

```
$ python -m depeg_sim.sweep sweeps/pace-ratio-mc.yaml --mc --workers 12
sweep: pace-ratio-mc cells=112 workers=12
wrote: output/pace-ratio-mc/sweep.parquet
mc: pace-ratio-mc grid_points=14 seeds=8 runs=112
wrote: output/pace-ratio-mc/mc.parquet
(23 s in `make figures`)

time_to_parity_hours per point (ratio = defender spend_pace / attacker pace):
 atk   def     ratio   hours   entered  p_peg_recovered
 0.02  0.0025  0.125    2.03   8/8      0.875
 0.02  0.005   0.25     2.00   8/8      0.875
 0.02  0.01    0.5      7.86   8/8      1.000
 0.02  0.02    1.0     47.08   8/8      0.000
 0.02  0.03    1.5     never   0/8      0.000
 0.02  0.05    2.5     never   0/8      0.000
 0.02  0.1     5.0     never   0/8      0.000
 0.1   0.0025  0.025    0.85   8/8      1.000
 0.1   0.005   0.05     0.47   8/8      0.875
 0.1   0.01    0.1      0.39   8/8      1.000
 0.1   0.02    0.2      0.38   8/8      1.000
 0.1   0.03    0.3      0.38   8/8      0.875
 0.1   0.05    0.5      0.39   8/8      1.000
 0.1   0.1     1.0     29.88   8/8      0.625
```

**AC 2: summary key; determinism fixtures updated once.** `soros-baseline` seed 42
`summary.json` from the code before this change (`58adfb2`, run in a worktree) and after:

```
$ diff -u out-old/soros-baseline-42-2e09f431/summary.json out-new/soros-baseline-42-2e09f431/summary.json
@@ -1,5 +1,6 @@
 {
   "arbitrageur_pnl": 3040.987797278067,
+  "arbitrageur_redeemed": 90898.75060887457,
   "attacker_pnl": -11456.546807562234,
   "defender_bought_stable": 207210.1710084618,
   "defender_interventions": 16,
f2428bdb6b6fc52188e7761f9170fbddda5cb501a74849e7c7f1284e73677865  out-new/.../summary.json
ae9578ad45a35fe6986537a344d20746451d2ac74bd5a8ae331816f89fd77704  out-old/.../summary.json   (= the existing pin)
```

Fixture diffs (the only two pinned fixtures that name summary keys or bytes):

```diff
--- a/tests/test_summary.py
+++ b/tests/test_summary.py
@@ -22,6 +22,7 @@ EXPECTED = [
     "steps_to_sustained_recovery",
     "reserves_exhausted",
     "redemption_paid_total",
+    "arbitrageur_redeemed",
     "defender_spent",
--- a/tests/test_reference_recovery.py
+++ b/tests/test_reference_recovery.py
 def test_soros_baseline_summary_bytes_unchanged(tmp_path):
-    # summary.json sha256 captured at b29c7c0, before Story 2.8 touched anything
+    # summary.json sha256 re-captured in Story 3.5 (one new key, arbitrageur_redeemed).
+    # Without that line the bytes are the ones captured at b29c7c0, before Story 2.8.
 ...
-    digest = hashlib.sha256((art.run_dir / "summary.json").read_bytes()).hexdigest()
-    assert digest == "ae9578ad45a35fe6986537a344d20746451d2ac74bd5a8ae331816f89fd77704"
+    raw = (art.run_dir / "summary.json").read_bytes()
+    assert hashlib.sha256(raw).hexdigest() == (
+        "f2428bdb6b6fc52188e7761f9170fbddda5cb501a74849e7c7f1284e73677865"
+    )
+    lines = raw.splitlines(keepends=True)
+    added = [ln for ln in lines if b'"arbitrageur_redeemed"' in ln]
+    assert len(added) == 1
+    before = b"".join(ln for ln in lines if ln not in added)
+    assert hashlib.sha256(before).hexdigest() == (
+        "ae9578ad45a35fe6986537a344d20746451d2ac74bd5a8ae331816f89fd77704"
+    )
```

The run-vs-rerun byte tests (`tests/test_run_determinism.py`) are unchanged and pass.

`scripts/policy_table.py` from `sweep.parquet` alone, on the `policy-comparison-mc` output
that `make figures` re-ran: md5 `091ad07b9fd52380e9e1c9f1cbb91e5f`, the same md5 Story 3.2
recorded for the events-based table; 0.3 s (was 7.6 s). Before clipping the holder share
at zero the only difference was `-0` where `total - arbitrageur` left a −1e-9 residue.

**AC 3: the guard, both behaviours** (`make figures-check`; make exits 2 when the
script exits 1):

```
$ # (a) docstring edit in src/depeg_sim/protocol/amm.py
 src/depeg_sim/protocol/amm.py | 2 +-
$ make figures-check
.venv/bin/python scripts/check_figures.py
figures-check: WARNING: figures were drawn by other code: manifest has code_hash e97b43b811483fc92ca0e5a2029c2e486734a887b3bd5baa0f3f5d96d057b568, src/depeg_sim/**/*.py now hashes to 8d10858fc050a9a97338725e074cb2dc2ca38ebbfa320b1428d9e7520cd362b7. Numbers may differ; run `make figures` before the freeze (docs/REPRODUCIBILITY.md)
figures-check: ok, 15 figures match their sources (code differs, see warning)
exit=0
$ # (b) scenario edit: scenarios/soros-1992.yaml seed 42 -> 43
 scenarios/soros-1992.yaml | 2 +-
$ make figures-check
.venv/bin/python scripts/check_figures.py
figures-check: holder_exit: STALE, sweeps/holder-exit-1992-mc.yaml or its base scenario changed (manifest c809e733d7af, now 2a0e49f905bc); regenerate with `make figures`
figures-check: peg_trajectory_1992: STALE, scenarios/soros-1992.yaml changed (manifest f4e26ae66440, now c4ee2f3539b0); regenerate with `make figures`
figures-check: FAIL, 2 problem(s) in 15 figures
make: *** [Makefile:36: figures-check] Error 1
exit=2
$ # both reverted
$ make figures-check
figures-check: ok, 15 figures match their sources (code_hash matches)
exit=0
```

**AC 3 / 10: `make figures`** (code commit `7db6480`, `TMPDIR=output/tmp`):

```
$ make figures WORKERS=12
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 138 s
sweep sweeps/threshold-surface-mc.yaml: wall time 136 s
sweep sweeps/budget-x-depth-mc.yaml: wall time 52 s
sweep sweeps/oracle-lag-mc.yaml: wall time 110 s
sweep sweeps/policy-comparison-mc.yaml: wall time 74 s
sweep sweeps/holder-exit-1992-mc.yaml: wall time 19 s
sweep sweeps/budget-x-attack-mc.yaml: wall time 57 s
sweep sweeps/pace-x-trigger-mc.yaml: wall time 92 s
sweep sweeps/pace-ratio-mc.yaml: wall time 23 s
wrote: 15 figures and docs/figures/manifest.json (commit 7db648047112, code_hash e97b43b81148)
make figures: wall time 708 s (12 workers)
```

The fourteen existing PNGs came out byte-identical (`git status` shows only
`pace_ratio.png` new and `manifest.json` modified).

```
$ make figures-quick WORKERS=12
quick sweep: budget-x-attack-mc (16 s)   budget-x-depth-mc (13 s)   holder-exit-1992-mc (5 s)
quick sweep: oracle-lag-mc (8 s)   pace-ratio-mc (7 s)   pace-x-trigger-mc (25 s)
quick sweep: policy-comparison-mc (10 s)   threshold-surface-mc (18 s)   threshold-surface-ref-mc (19 s)
quick: ok, 15 figures drawn; wrote docs/figures/quick-ok only
make figures-quick: wall time 127 s (12 workers)
```

Non-figure sweeps, for the README table (12 workers): `pool-depth-x-attacker` 1 s (16
runs), `usdc-2023-pace` 4 s (7), `pool-depth-x-attacker-mc` 3 s (512),
`capital-vs-resources-mc` 11 s (2,016; mean 305 steps per run).

**CI** run [37549454426](https://github.com/tjdove/corposium-research/actions/runs/37549454426)
on `7db6480`: `test` success (1.5 min), `figures-quick` success (4 workers):

```
quick sweep: budget-x-attack-mc (132 s)
quick sweep: budget-x-depth-mc (109 s)
quick sweep: holder-exit-1992-mc (43 s)
quick sweep: oracle-lag-mc (65 s)
quick sweep: pace-ratio-mc (52 s)
quick sweep: pace-x-trigger-mc (191 s)
quick sweep: policy-comparison-mc (89 s)
quick sweep: threshold-surface-mc (150 s)
quick sweep: threshold-surface-ref-mc (165 s)
quick: ok, 15 figures drawn; wrote docs/figures/quick-ok only
make figures-quick: wall time 1019 s (4 workers)
```

CI on the final commit runs after this file is committed, so its result goes in the report to the dev manager, not here.

**AC 5: coverage**

```
$ pytest --cov=depeg_sim.protocol --cov=depeg_sim.agents --cov-report=term-missing
Name                                   Stmts   Miss  Cover   Missing
--------------------------------------------------------------------
src/depeg_sim/agents/__init__.py           0      0   100%
src/depeg_sim/agents/arbitrageur.py       99      2    98%   105, 147
src/depeg_sim/agents/attacker.py          42      0   100%
src/depeg_sim/agents/base.py              82      3    96%   62, 64, 197
src/depeg_sim/agents/defender.py          89      0   100%
src/depeg_sim/agents/factory.py           21      0   100%
src/depeg_sim/agents/holder.py           101      0   100%
src/depeg_sim/protocol/__init__.py         0      0   100%
src/depeg_sim/protocol/amm.py            111      0   100%
src/depeg_sim/protocol/oracle.py          71      0   100%
src/depeg_sim/protocol/redemption.py     153      2    99%   112, 267
--------------------------------------------------------------------
TOTAL                                    769      7    99%
745 passed in 18.58s
exit=0
```

Per package: `agents/` 429/434 = 98.8%, `protocol/` 333/335 = 99.4%. Coverage was already
there before this story (same per-file numbers before `tests/test_properties.py`); the
property tests add the AC's invariants, not lines.

**AC 9: pins.** Clean venv, no pip cache:

```
venv 1 s; pip install -e .[dev] (no cache) 72 s
Python 3.12.13
matplotlib 3.11.2  numpy 2.5.3  pandas 3.0.6  pyarrow 25.0.1  pydantic 2.13.5  PyYAML 6.0.3  pytest 9.1.1  ruff 0.16.10
pytest 13 s (all passed)
```

Floor versions (uv venv, Python 3.12.13): `pyyaml==6.0` failed to build (`Failed to build
pyyaml==6.0`; no cp312 wheel), so the floor is now 6.0.1. With numpy 1.26.4, pandas
2.2.3, pyarrow 16.0.0, matplotlib 3.9.4, pydantic 2.7.4, PyYAML 6.0.1:
`pytest -o addopts="" -q -p no:warnings` → `745 passed in 12.19s`.

**Close-out**

```
$ pytest -o addopts="" -q   (with --cov as above)
745 passed in 18.58s          (616 before this story, at ce5f565)
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
92 files already formatted
exit=0
$ make figures-check
figures-check: ok, 15 figures match their sources (code_hash matches)
exit=0
$ git diff --stat ce5f565 -- src/depeg_sim/kernel src/depeg_sim/protocol src/depeg_sim/agents scenarios
(empty)
PHASE_ORDER_VERSION = 1
```

### Completion Notes List

**37 h crossings (AC 1).** Interpolated linearly in log ratio (`charts.deadline_crossing`):

- **Attacker pace 0.02: crosses at a ratio of 0.84**, between 0.5 (7.9 h) and 1.0 (47.1 h).
  From 1.5 up no seed re-enters by 60 h.
- **Attacker pace 0.1: does not cross on this grid.** It stays at 0.4–0.9 h up to a ratio
  of 0.5 and reaches 29.9 h at 1.0, the largest ratio the AC's axes give it (defender pace
  0.1 / attacker pace 0.1). The pace-x-trigger grid has the next point (defender pace
  0.2, ratio 2: 48.2 h at trigger 1%), so this line crosses somewhere between 1 and 2.
  The spec's defender axis stops at 0.1, so `pace-ratio-mc` cannot locate that crossing.
  If the note wants it, adding 0.15 and 0.2 to the defender axis costs 32 runs.
- So the two lines do not coincide at equal ratio: the five-times-slower attacker is
  harder at every ratio from 0.125 to 1 (2.0 vs 0.4 h at 0.25; 47.1 vs 29.9 h at 1). The
  ratio is first-order, as ADR-0027 B said, but not the whole story: against the slow
  attacker the crossing comes at about 0.84 rather than above 1. Recorded as an
  observation for the review; I have not written a finding ADR for it.

**Coverage (AC 5):** agents 98.8%, protocol 99.4% (report above). `make test` now fails
below 85%. pytest-cov has no per-package threshold, so it is
`--cov-fail-under=85` over the two packages together. Property tests
(`tests/test_properties.py`, 117 cases, seeded `np.random.default_rng(seed)`, no new
dependency):

- AMM `k` non-decreasing over 300 random trades × 20 seeds × fees {0, 4, 30, 100} bps,
  with sizes log-uniform from 1e-9 to 0.5 of the input reserve. Strict `>=` with a fee;
  `>= k0 × (1 − 1e-12)` at fee 0, where `k` is constant and only the float product rounds.
- Redemption, 120 steps × 20 seeds of random requests (some bad amounts, some unknown
  kinds). After every step: requested = fulfilled + queued; every positive amount
  submitted = fulfilled + queued + rejected; reserves + paid = initial; no step fills
  more than its capacity. Event sums match the totals. A companion test checks that the
  random sequences reach both limits: 4/20 seeds exhaust reserves, 20/20 fill partially
  against capacity.
- Termination, both criteria (`par`, `oracle`):
  - exactly `for_steps` in band recovers at step `4 + for_steps − 1`;
  - one step short (in band `for_steps − 1`, then out, repeated) never recovers;
  - one step short at the horizon ends `max_steps` with the counter at `for_steps − 1`;
  - `reference: oracle` with no oracle registered never recovers, even at exact par,
    where `par` recovers at step 3.

**Guard (AC 3), Proposed ADR-0028.** The behaviours are shown above. Two parts of the
spec were left open, so I chose:
- what is hashed: path + NUL + bytes + NUL per file, sorted by relative path;
- a manifest without `code_hash` warns.

The warning names both full hashes and, under `GITHUB_ACTIONS`, is also a
`::warning::` annotation on the run page.

**Makefile (AC 4).** `PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)`.
`make lint` now calls `$(PYTHON) -m ruff` so it also works without activation. `make
figures` prints a wall time per sweep.

**Summary (AC 2).** `arbitrageur_redeemed` is 0.0 when the arbitrageur never redeems and
`None` without an arbitrageur or redemption module. `policy_table.py` takes the holder's
share as `redemption_paid_total − arbitrageur_redeemed`. That is valid while the
arbitrageur and holder are the only redeeming agents, which a test asserts. `mc.py`
METRICS is unchanged, so `mc.parquet` has no new column.

**README outline (AC 6):**
1. Title; three sentences: what it is, the USDC calibration and validation, the 1992
   mapping; every number comes from one command.
2. One figure (USDC overlay) and one command (`make figures`, 12 min on 12 cores);
   status line.
3. Quick start: clone, `python3.12 -m venv`, `pip install -e ".[dev]"` (~70 s),
   `pytest` (745), `run.py` with its expected output and the run-directory listing.
4. Results so far: validation and price-or-clock kept, plus one paragraph on pace from
   the pace-ratio sweep. Only one more embedded image (time to parity); pace links to
   its PNG.
5. Scenarios: 11 rows, with `content_hash()[:12]`.
6. Sweeps: 13 rows, with runs and Seoul wall time; the nine figure sweeps starred.
7. Make targets, including the `PYTHON` default.
8. Figures: a pointer to `docs/figures/README.md`.
9. Further reading: FINDINGS, BACKGROUND, LITERATURE, REPRODUCIBILITY, ADR index,
   PROCESS + CONTRIBUTING, CHARTER.
10. Layout; license.

No story or ADR numbers in the body; the only `f-NN` strings are inside FINDINGS anchor
URLs.

**What a stranger still could not reproduce / gaps:**
- **NOTE outline link missing (AC 6).** `docs/NOTE.md` is not on `main`. It exists only
  on the unmerged branch `origin/docs/note-outline` (`5b27329`). I did not merge a branch
  that is not mine, and I did not add a dead link. Once it is merged, add one line to
  "Further reading".
- The four uncalibrated or fitting sweeps (`capital-vs-resources-mc`,
  `pool-depth-x-attacker(-mc)`, `usdc-2023-pace`) run, and their times are in the
  table, but no committed artefact checks their outputs. Their numbers live only in
  story Debug Logs.
- The fitting and probe scripts (`fit_depth.py`, `fit_holder.py`, `probe_boundary.py`,
  `scan_1992.py`, `budget_attack_table.py`) are not in `make figures` or under the guard.
  The calibrated constants they produced are pinned in the scenario files, but the step
  from script to constant is reproducible only by reading the story Debug Logs.
- Full `make figures` has never run on CI. The 4-worker number is for `figures-quick`
  (1,019 s); a full run there is an extrapolation (about 1.5 h).
- Byte-identity across library versions is not promised. The only data point: the
  pinned `soros-baseline` `summary.json` is the same on the floor versions and current
  ones.
- `make figures` needs about 30 GB free under `output/`. My `output/` was 41 GB
  including earlier runs.
- The README's "Results so far" includes a second figure (time to parity) besides the
  thirty-second figure. I kept it because AC 6 says that section is kept. If "one figure"
  is meant strictly, it becomes a link.

**Other notes.** `pyproject.toml` raises the PyYAML floor from 6.0 to 6.0.1 (6.0 cannot be
installed on 3.12) and adds major-version upper bounds; CI is unchanged. The pace-ratio
caption is in `docs/figures/README.md`, the row tagged "F-13 refinement" pending review.

### File List

**Created:**

- `sweeps/pace-ratio-mc.yaml`
- `tests/test_properties.py`
- `CONTRIBUTING.md`
- `docs/REPRODUCIBILITY.md`
- `docs/adr/0028-figure-guard-code-hash.md`
- `docs/figures/pace_ratio.png`

**Modified:**

- `src/depeg_sim/analysis/charts.py` (`deadline_crossing`, `plot_pace_ratio`)
- `src/depeg_sim/analysis/summary.py` (`arbitrageur_redeemed`)
- `scripts/check_figures.py` (`code_hash`, warn semantics)
- `scripts/make_figures.py` (`pace_ratio.png` registered, `code_hash` written)
- `scripts/policy_table.py` (parquet only)
- `Makefile` (`PYTHON` default, pace-ratio sweep, per-sweep times, coverage gate, `python -m ruff`)
- `pyproject.toml` (bounds)
- `README.md`
- `docs/figures/README.md` (pace-ratio row and caption, code hash, timing)
- `docs/figures/manifest.json` (regenerated; `code_hash`)
- `tests/test_charts.py`, `tests/test_figures.py`, `tests/test_scripts.py`,
  `tests/test_summary.py`, `tests/test_reference_recovery.py`
- `docs/stories/3-5-hardening-and-polish.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-06
**Outcome:** **APPROVE** ✅ — Epic 3's core is complete, fifteen days before the freeze.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest --cov` → `745
passed`, **agents 98.8%, protocol 99.4%** (arbitrageur 98, base 96, redemption 99, the
rest 100); `ruff check .` → `All checks passed!`; `ruff format --check .` → `92 files
already formatted`; `make figures-check` → ok, 15 figures, code hash matches. **Guard,
both paths, proven here:** a docstring line in `amm.py` → WARNING naming both hashes,
exit 0; `capacity_per_step` 13986.57 → .58 in `soros-1992.yaml` → two figures STALE, exit
1. **Pace-ratio sweep re-run in full** (112 runs, 3m08s): identical — attacker 0.02: 2.0 /
2.0 / 7.9 / 47.1 h then never from ratio 1.5; attacker 0.1: < 1 h through 0.5, 29.9 h at
1.0. README read as a stranger would: three sentences, one figure, one command.

### Rulings

1. **ADR-0028 → Accepted.** Guard semantics as built (warn on code, fail on source) and
   the freeze checklist as the hard gate.
2. **The two attacker-pace lines do not coincide** — at every ratio the slow attacker
   takes longer to beat (7.9 h vs 0.4 h at 0.5; 47 h vs 30 h at 1.0). Recorded as the
   second-order term in the F-13 refinement: the ratio is first-order, the attacker's
   absolute pace second-order, and slower is harder. No new finding number.
3. **The 0.1 line's 37 h crossing is off the grid** (between ratio 1 and 2). Not extended;
   the pace × trigger sweep already brackets it at 48.2 h for ratio 2. The note quotes
   "between 1× and 2× the attacker's pace".
4. **"Results so far" keeps two figures** — accepted; "one figure" meant the hero image.
5. **PR #32 (NOTE outline) merged into this branch**, conflict in README resolved by
   keeping the 3.5 README and adding the NOTE link. The builder's "stranger couldn't find
   the NOTE" item is closed by this PR.
6. **What a stranger still cannot reproduce** (builder's list) → carried into the Epic 3
   retro: the fitting scripts' outputs are not under the guard (`fit_depth`, `fit_holder`
   results live in story logs); cross-version byte identity is not promised; a full
   regeneration needs ~30 GB. The first is worth a small AC in the Epic 4 figure pass
   (record the fit tables in `docs/calibration/` with their script hashes); the other two
   are stated in REPRODUCIBILITY.md and that is enough.
7. **PyYAML ≥ 6.0.1** — accepted.
8. **CI run 37551328758 on 917444a: both jobs green** — recorded here as the builder asked.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | `pace-ratio-mc`; `plot_pace_ratio`; registered; 37 h crossings reported; reproduced |
| 2 | ✅ | `arbitrageur_redeemed`; fixtures updated once with diff; policy table byte-identical from parquet |
| 3 | ✅ | `code_hash`; warn/fail proven here; REPRODUCIBILITY freeze checklist |
| 4 | ✅ | Makefile `PYTHON` prefers `.venv/bin/python`; documented |
| 5 | ✅ | 98.8% / 99.4%; AMM k, redemption accounting, termination edges with seeded Generator |
| 6 | ✅ | README for a stranger; no story/ADR numbers in body |
| 7 | ✅ | CONTRIBUTING.md |
| 8 | ✅ | REPRODUCIBILITY.md with timings, hashes, TMPDIR note, checklist |
| 9 | ✅ | pins reviewed; oldest-allowed versions pass 745 tests; clean install 72 s |
| 10 | ✅ | `make figures` 708 s; guard ok; 745 tests; both CI jobs green; ADR-0028 |

**10 of 10 ACs met.**

### Key Findings

No new finding. The pace-ratio figure is now the committed evidence for the F-13
refinement, with the slow-attacker term recorded.

### Learnings for the stretch stories

- The repo now warns when figures and code diverge; every stretch story ends with
  `make figures` anyway.
- Coverage is at 99% on the two packages that matter; stretch stories keep it there.

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.4 review
- 2026-10-06: Implemented by Claude Code (Opus 5.5) on Seoul: pace-ratio sweep and chart; `arbitrageur_redeemed`; guard `code_hash` (warn) with Proposed ADR-0028; Makefile `PYTHON` default; property tests; README, CONTRIBUTING, REPRODUCIBILITY; dependency bounds; Status review
- 2026-10-06: Senior review APPROVE; ADR-0028 accepted; Status done; Epic 3 core complete
