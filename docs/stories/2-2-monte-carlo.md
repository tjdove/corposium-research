# Story 2.2: Monte Carlo over Seeds

Status: ready-for-dev

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

- [ ] Seeds spec form (AC: 1)
  - [ ] `SeedsSpec = list[int] | SeedRange` in `sweep.py`; normalise in `expand`
  - [ ] Tests: both forms; manifest lists the expanded seeds

- [ ] Stats helper (AC: 3)
  - [ ] `analysis/stats.py`: `wilson`; tests at the three known points plus `n=0` → `(0, 1)`

- [ ] Aggregation (AC: 2, 4)
  - [ ] `experiments/mc.py`: `aggregate_mc`; axis-column discovery from the sweep manifest (not by column-name guessing)
  - [ ] Column generation loop over the metric list; NaN-aware stats; the `_n` companion for nullable metrics
  - [ ] Tests on a synthetic `sweep.parquet` (hand-built DataFrame): known means/percentiles; proportions sum to 1; Wilson bounds present; repeat-run bytes equal; sort order

- [ ] CLI (AC: 5)
  - [ ] `--mc` flag on the sweep CLI; `src/depeg_sim/mc.py` entry; two output lines; exit codes

- [ ] Sweep specs and full runs (AC: 6, 7, 8, 9)
  - [ ] Write both YAML files with header comments citing ADR-0016
  - [ ] Run both at `workers=4`; record wall times
  - [ ] Build the ratio table (pandas, in a scratch script; paste the result, not the script) and write the Proposed ADR
  - [ ] Tiny-spec tests for CI (AC 10)

- [ ] Tests, lint, close out (AC: 10)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.2: monte carlo over seeds`, push to `main`

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

_(fill in)_

### Debug Log References

_(real command output with exit codes; both sweep wall times)_

### Completion Notes List

_(include the two ratio tables and the ADR number proposed)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-03: Story drafted by dev manager after Story 2.1 review; grid reshaped by ADR-0016
