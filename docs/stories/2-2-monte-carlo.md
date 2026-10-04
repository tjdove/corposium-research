# Story 2.2: Monte Carlo over Seeds

Status: review

## Story

As a **researcher**,
I want each sweep cell run across many seeds with volatility on,
so that every threshold claim carries a confidence band and the ADR-0016 prediction is tested.

## Acceptance Criteria

1. `SweepSpec.seeds` accepts either a list or `{"count": N, "start": s}` (→ `range(s, s+N)`); `expand` and the sweep manifest record the expanded list
2. `src/depeg_sim/experiments/mc.py`: `aggregate_mc(sweep_dir: Path) -> Path` reads `sweep.parquet`, groups by every axis column (linked-axis names and dotted paths; **not** `seed`, `index`), and writes `mc.parquet` with one row per grid point containing: the axis columns; `n`; for each numeric summary metric (`max_depeg_bps, step_of_max_depeg, final_depeg_bps, steps_to_first_band_entry, steps_to_sustained_recovery, steps_run, redemption_paid_total, defender_spent, defender_interventions, attacker_pnl, arbitrageur_pnl`) the columns `<m>_mean, <m>_std, <m>_p05, <m>_p50, <m>_p95` (NaN-aware: `steps_to_sustained_recovery` is null on non-recovery runs, so its stats use only non-null values and an extra `<m>_n` column counts them); for `reserves_exhausted` the proportion `p_reserves_exhausted` with Wilson 95% bounds `p_reserves_exhausted_lo/_hi`; and for `terminated_by` the three proportions `p_reserves_exhausted_term, p_peg_recovered, p_max_steps` (they sum to 1)
3. Wilson interval implemented in `analysis/stats.py` as `wilson(k, n, z=1.96) -> (lo, hi)` with tests against known values (k=0,n=10 → (0, 0.278); k=5,n=10 → (0.237, 0.763); k=10,n=10 → (0.722, 1)) to 3 dp
4. `aggregate_mc` is deterministic (byte-identical `mc.parquet` on repeat) and sorted by axis columns in spec order
5. CLI: `python -m depeg_sim.sweep <spec> --mc` runs the sweep then aggregates; `python -m depeg_sim.mc <sweep_dir>` aggregates an existing sweep; prints `mc: <name> grid_points=<g> seeds=<n> runs=<g·n>` then `wrote: <dir>/mc.parquet`
6. `sweeps/capital-vs-resources-mc.yaml` (the ADR-0016 test): base `scenarios/soros-volatile.yaml`; axes `agents[type=attacker].capital` {600k, 700k, 800k, 900k, 1.0M, 1.1M, 1.2M}, `agents[type=defender].budget` {200k, 400k, 600k}, `redemption.reserves` {250k, 500k, 750k}; linked axis `pool_depth` {500k, 2M}; seeds `{count: 16, start: 1000}`; `max_steps: 1500` → 7×3×3×2 = 126 grid points × 16 = 2016 runs
7. `sweeps/pool-depth-x-attacker-mc.yaml`: the 2.1 grid on `soros-volatile`, 32 seeds → 512 runs (kept for 2.6's secondary-axis chart)
8. Both MC sweeps complete on Seoul at `workers=4`; wall times in Completion Notes; hard ceiling 10 minutes each (per 2.1's timing, expect < 1 minute)
9. Analysis in Completion Notes and a `Proposed` ADR: for `capital-vs-resources-mc`, tabulate `p_reserves_exhausted` against the ratio `capital / (budget + reserves)` pooled across the other axes; state whether the 0.5 crossing sits near ratio 1.0 as ADR-0016 predicts, whether `pool_depth` shifts it, and the width of the transition band (ratio at p=0.05 to ratio at p=0.95). Include the 7-column table at `pool_depth=500k` and at `2M` separately
10. `pytest` and `ruff check .` pass; CI green; the test suite runs only tiny MC specs (≤ 2×2×2 grid, 3 seeds, `max_steps` ≤ 300)

## Tasks / Subtasks

- [x] Seeds spec form (AC: 1)
  - [x] `SeedsSpec = list[int] | SeedRange` in `sweep.py`; normalise in `expand`
  - [x] Tests: both forms; manifest lists the expanded seeds

- [x] Stats helper (AC: 3)
  - [x] `analysis/stats.py`: `wilson`; tests at the three known points plus `n=0` → `(0, 1)`

- [x] Aggregation (AC: 2, 4)
  - [x] `experiments/mc.py`: `aggregate_mc`; axis-column discovery from the sweep manifest (not by column-name guessing)
  - [x] Column generation loop over the metric list; NaN-aware stats; the `_n` companion for nullable metrics
  - [x] Tests on a synthetic `sweep.parquet` (hand-built DataFrame): known means/percentiles; proportions sum to 1; Wilson bounds present; repeat-run bytes equal; sort order

- [x] CLI (AC: 5)
  - [x] `--mc` flag on the sweep CLI; `src/depeg_sim/mc.py` entry; two output lines; exit codes

- [x] Sweep specs and full runs (AC: 6, 7, 8, 9)
  - [x] Write both YAML files with header comments citing ADR-0016
  - [x] Run both at `workers=4`; record wall times
  - [x] Build the ratio table (pandas, in a scratch script; paste the result, not the script) and write the Proposed ADR
  - [x] Tiny-spec tests for CI (AC 10)

- [x] Tests, lint, close out (AC: 10)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.2: monte carlo over seeds`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.1 (Status: done)**

- `sweep.parquet` schema: `index, seed, <axis cols>, <summary keys>`; `terminated_by` is
  a string. Cell dirs at `<sweep>/<index>-<seed>-<hash8>/` (ADR-0015).
- The sweep manifest records the resolved spec, so `aggregate_mc` reads axis names from
  `manifest["spec"]` (linked axis `name`s + ordinary axis paths) rather than inferring
  from columns.
- Sweeps are CPU-trivial at this size (16 cells in 0.56 s); 2016 runs ≈ 70 s. Spawn
  overhead dominates; don't optimise.
- **ADR-0016:** outcome is set by `capital ≷ budget + reserves`, not depth. This story's
  main grid exists to test that across seeds and noise.

[Source: docs/stories/2-1-sweep-runner.md#Senior-Developer-Review, docs/adr/0016]

### Architecture Alignment

Monte Carlo in the spec: "many randomized runs over distributions." We randomise via
seeds on the volatile environment (`volatility_per_step: 0.0005`, ≈ 0.05% per 12 s step,
≈ 2.6% daily — a rough stablecoin-stress figure; 2.3 calibrates it). The aggregation is
the Analysis layer's first real product: per-grid-point distributions.

### Why the grid in AC 6

ADR-0016 predicts a boundary at `capital ≈ budget + reserves`. The grid is built so that
ratio spans ~0.46 (600k / 1.35M) to ~2.7 (1.2M / 450k) with many combinations landing
near 1.0 from different (budget, reserves) splits. If the prediction holds:
- `p_reserves_exhausted` should rise from ~0 to ~1 as the ratio crosses 1 regardless of
  how the denominator is split;
- `pool_depth` (500k vs 2M) should not shift the crossing, only the trough columns.
If the split matters (budget vs reserves not interchangeable), that's a refinement of
0016 and goes in the ADR. If depth shifts the crossing, 0016 needs revisiting.

### Wilson interval

```
centre = (k + z²/2) / (n + z²)
half   = z · sqrt(k(n−k)/n + z²/4) / (n + z²)
```

Return `(max(0, centre − half), min(1, centre + half))`; `n == 0` → `(0.0, 1.0)`.

### `mc.parquet` column order

Axis columns (spec order) → `n` → for each metric in the AC 2 list: `_mean,_std,_p05,_p50,_p95[,_n]`
→ `p_reserves_exhausted, _lo, _hi` → `p_reserves_exhausted_term, p_peg_recovered, p_max_steps`.
Fixed order makes the file diffable.

Percentiles via `numpy.percentile(..., method="linear")` on non-null values. `std` with
`ddof=1`; NaN when `n_nonnull < 2`.

### Ratio table for AC 9

```python
mc["ratio"] = mc["agents[type=attacker].capital"] / (mc["agents[type=defender].budget"] + mc["redemption.reserves"])
mc.sort_values("ratio")[["ratio","pool_depth","p_reserves_exhausted","p_reserves_exhausted_lo","p_reserves_exhausted_hi"]]
```

Then bin `ratio` into ~10 bins and report pooled `p` with pooled Wilson bounds per bin,
once for each `pool_depth`. Paste both tables into the ADR.

### References

- [Source: docs/epics.md#Story-2.2]
- [Source: docs/adr/0016-outcome-set-by-capital-not-depth.md]
- [Source: docs/adr/0015-sweep-cell-directory-layout.md]
- [Source: docs/BACKGROUND.md#How-economists-explain-it] — first-generation boundary
- Wilson, E. B. (1927). "Probable Inference, the Law of Succession, and Statistical Inference." *JASA* 22.

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-2-monte-carlo.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

```
$ pytest; echo exit=$?
405 passed in 3.74s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
72 files already formatted
exit=0

$ time python -m depeg_sim.sweep sweeps/capital-vs-resources-mc.yaml --workers 4 --mc; echo exit=$?
sweep: capital-vs-resources-mc cells=2016 workers=4
wrote: output/capital-vs-resources-mc/sweep.parquet
mc: capital-vs-resources-mc grid_points=126 seeds=16 runs=2016
wrote: output/capital-vs-resources-mc/mc.parquet

real	0m15.576s
user	0m59.555s
sys	0m1.033s
exit=0

$ time python -m depeg_sim.sweep sweeps/pool-depth-x-attacker-mc.yaml --workers 4 --mc; echo exit=$?
sweep: pool-depth-x-attacker-mc cells=512 workers=4
wrote: output/pool-depth-x-attacker-mc/sweep.parquet
mc: pool-depth-x-attacker-mc grid_points=16 seeds=32 runs=512
wrote: output/pool-depth-x-attacker-mc/mc.parquet

real	0m4.467s
user	0m16.967s
sys	0m0.334s
exit=0

$ python -m depeg_sim.mc output/capital-vs-resources-mc; echo exit=$?
mc: capital-vs-resources-mc grid_points=126 seeds=16 runs=2016
wrote: output/capital-vs-resources-mc/mc.parquet
exit=0

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/analysis/stats.py                 11      0   100%
src/depeg_sim/experiments/mc.py                 76      0   100%
src/depeg_sim/experiments/sweep.py             186      0   100%
src/depeg_sim/mc.py                              3      3     0%   7-10
src/depeg_sim/sweep.py                           3      3     0%   7-10
TOTAL                                         1620     14    99%
```

CI on push of `5b24f7c`:

```
completed	success	story 2.2: monte carlo over seeds	ci	main	push	37164336778	48s	2026-10-04T00:14:34Z
```

(The two `-m` shims run in subprocess tests, which coverage doesn't trace.)

380 → 405 tests (+25): `test_stats.py` 7, `test_mc.py` 18.

### Completion Notes List

- **Wall times (Seoul, `workers=4`): 2016 runs in 15.6 s; 512 runs in 4.5 s.** Well under
  the 10-minute ceiling and 4.5× faster than the 70 s estimate. Most runs end by step
  ~80–600; only `max_steps` runs go to 1500/2000.
- **AC 9: the ADR-0016 test → proposed ADR-0017 (finding, refines and partly contradicts
  ADR-0016).** Ratio `capital / (budget + reserves)`, pooled per bin, Wilson 95% on the
  pooled runs:

**pool_depth = 500k**

| ratio bin | points | runs | exhausted | p | lo | hi |
|---|---|---|---|---|---|---|
| [0.40, 0.60) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [0.60, 0.70) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.70, 0.80) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.80, 0.90) | 8 | 128 | 0 | 0.000 | 0.000 | 0.029 |
| [0.90, 1.00) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [1.00, 1.10) | 8 | 128 | 1 | 0.008 | 0.001 | 0.043 |
| [1.10, 1.25) | 6 | 96 | 80 | 0.833 | 0.746 | 0.895 |
| [1.25, 1.50) | 8 | 128 | 128 | 1.000 | 0.971 | 1.000 |
| [1.50, 2.00) | 7 | 112 | 112 | 1.000 | 0.967 | 1.000 |
| [2.00, 2.80) | 4 | 64 | 64 | 1.000 | 0.943 | 1.000 |

**pool_depth = 2M**

| ratio bin | points | runs | exhausted | p | lo | hi |
|---|---|---|---|---|---|---|
| [0.40, 0.60) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [0.60, 0.70) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.70, 0.80) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.80, 0.90) | 8 | 128 | 0 | 0.000 | 0.000 | 0.029 |
| [0.90, 1.00) | 5 | 80 | 2 | 0.025 | 0.007 | 0.087 |
| [1.00, 1.10) | 8 | 128 | 76 | 0.594 | 0.507 | 0.675 |
| [1.10, 1.25) | 6 | 96 | 96 | 1.000 | 0.962 | 1.000 |
| [1.25, 1.50) | 8 | 128 | 128 | 1.000 | 0.971 | 1.000 |
| [1.50, 2.00) | 7 | 112 | 112 | 1.000 | 0.967 | 1.000 |
| [2.00, 2.80) | 4 | 64 | 64 | 1.000 | 0.943 | 1.000 |

  Per grid point (`p_reserves_exhausted`, rows budget/reserves, columns capital):

| 500k depth | 600k | 700k | 800k | 900k | 1000k | 1100k | 1200k |
|---|---|---|---|---|---|---|---|
| 200k/250k | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/500k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| 400k/250k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 400k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| 400k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 600k/250k | 0.00 | 0.00 | 0.00 | 0.06 | 1.00 | 1.00 | 1.00 |
| 600k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 600k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

| 2M depth | 600k | 700k | 800k | 900k | 1000k | 1100k | 1200k |
|---|---|---|---|---|---|---|---|
| 200k/250k | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/500k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| 400k/250k | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 400k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| 400k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.75 |
| 600k/250k | 0.00 | 0.00 | 0.12 | 1.00 | 1.00 | 1.00 | 1.00 |
| 600k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| 600k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

- **Answers.** (1) The 0.5 crossing sits near 1.0, just above it: ~1.10 at 500k depth,
  ~1.03 at 2M. (2) **Depth shifts it, contradicting ADR-0016's "depth cannot enter":** six
  grid points flip from p ≤ 0.06 to p ≥ 0.75, and the *deeper* pool breaks at the lower
  ratio. Mechanism, measured from the event logs: in a shallow pool the defender buys
  stable much further below peg (avg 0.78 vs 0.92 at one flipped point), so its budget
  absorbs more stable (1.19 vs 1.02 stable per budget unit across all runs). That is the
  "adjusted for prices paid" term, and depth controls it; there is no third sink. A
  price-adjusted ratio (`capital / (defender stable bought + reserves/0.999)`) separates
  2016 runs at 1.005 with 5 errors (nominal: 93). It uses a run outcome, so it confirms
  the conservation law rather than predicting the verdict. (3) The budget/reserves split
  matters through the same channel: budget is worth > face value when bought below peg,
  reserves exactly 1/0.999. Small-reserve splits exhaust slightly early. (4) Within a
  depth the transition is a near-step, ≤ ~0.05 wide in ratio (only 3/126 points have
  0 < p < 1). The two depths' bands are disjoint; pooled they span ~1.00–1.11.
- **`pool-depth-x-attacker-mc` (512 runs)** reproduces the 2.1 column exactly across 32
  noisy seeds: `p_reserves_exhausted` 0 at capital ≤ 600k, 1 at 1.2M, every depth.
  `max_depeg_bps_mean` −186 (100k/2M) to −5430 (1.2M/250k);
  `steps_to_sustained_recovery_p50` 33–70 where recovered.
- **Noise shows up in `p_max_steps`, not in the verdict.** 6–25% of runs in the
  recovering region end by `max_steps`: reference-price drift (the oracle follows it, the
  AMM peg is fixed at 1.0) keeps the AMM outside the 60 bps band for 100 consecutive
  steps. That's a 2.3 calibration matter; noted in ADR-0017.
- **Axis discovery.** The Dev Notes say `manifest["spec"]`, but 2.1's sweep manifest has
  no `spec` key. It records the resolved axes as `manifest["axes"]` (a list of
  `{name, paths, values}` in expansion order). `aggregate_mc` reads axis names from
  there (`axis_columns`), never from DataFrame columns. A test puts a non-axis column
  that looks like an axis into the parquet and checks it's ignored.
- **Nullable metrics.** `_n` companions for `steps_to_first_band_entry` and
  `steps_to_sustained_recovery`, the two summary metrics that are null by definition on
  some runs. The column set is fixed (it doesn't depend on the data), so the file stays
  diffable. All metric stats are NaN-aware regardless.
- `p_reserves_exhausted` uses the `reserves_exhausted` flag; `p_reserves_exhausted_term`
  uses `terminated_by`. They coincide whenever `termination.reserves_exhausted` is on.
- **CLI.** `sweep --mc` prints the two sweep lines then the two mc lines. `python -m
  depeg_sim.mc <dir>` exits 2 when `sweep.parquet` or `manifest.json` is missing and 3
  when they can't be aggregated. Seeds in the manifest are the expanded list
  (`{count: 16, start: 1000}` → 1000…1015).
- AC 10 / CI budget: the only end-to-end MC tests use a 2×2 grid, 3 seeds, `max_steps`
  200 (asserted in `test_tiny_spec_is_within_ci_budget`). Aggregation logic is tested on
  hand-built `sweep.parquet` files with known values.
- Not done (not in scope): charts (2.6); README sweep/MC section.

### File List

**Created:**

- `src/depeg_sim/experiments/mc.py`
- `src/depeg_sim/analysis/stats.py`
- `src/depeg_sim/mc.py` (`python -m` shim)
- `sweeps/capital-vs-resources-mc.yaml`, `sweeps/pool-depth-x-attacker-mc.yaml`
- `docs/adr/0017-depth-enters-through-defender-price.md` (Proposed, finding)
- `tests/test_mc.py`, `tests/test_stats.py`

**Modified:**

- `src/depeg_sim/experiments/sweep.py` (`SeedRange`, `seed_list`, `--mc`)
- `docs/stories/2-2-monte-carlo.md`

## Change Log

- 2026-10-03: Story drafted by dev manager after Story 2.1 review; grid reshaped by ADR-0016
- 2026-10-03: Implemented by Claude Code (Opus 5.5); 405 tests pass; MC sweeps 15.6 s (2016 runs) and 4.5 s (512 runs); ADR-0017 proposed; status → review
