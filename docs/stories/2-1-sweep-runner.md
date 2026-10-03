# Story 2.1: Sweep Runner and Recovery Metrics

Status: done

## Story

As a **researcher**,
I want to run a grid of scenarios varying any config path and aggregate the summaries,
so that one command produces the data behind a sensitivity chart.

## Acceptance Criteria

1. `summarize` replaces `time_to_recovery_steps` with `steps_to_first_band_entry` (identical definition to the old field) and `steps_to_sustained_recovery` (= `steps_run − peg_recovered.for_steps − step_of_max_depeg` when `terminated_by == "peg_recovered"`, else `null`) per ADR-0013; `summary.json` key list in 1.8's AC 4 updated accordingly; all 1.8 tests pass with the new keys
2. Manifest round-trip test: `ScenarioConfig.model_validate(manifest["config"]).content_hash() == manifest["scenario_hash"]` for a baseline run (ADR-0014)
3. `src/depeg_sim/experiments/sweep.py` defines `SweepSpec` (Pydantic, `extra="forbid"`): `name: str`, `base: Path` (scenario YAML), `axes: dict[str, list[Any]]` keyed by dotted config path, `seeds: list[int]`, `overrides: dict[str, Any] = {}` (fixed path→value applied to every cell), `max_steps: int | None = None` (convenience override); `load_sweep(path) -> SweepSpec`
4. `set_path(cfg: ScenarioConfig, path: str, value) -> ScenarioConfig` applies one override through `model_copy(update=…)` on frozen models; supports nested attributes (`amm.reserve_stable`), list indices (`agents[0].capital`), and the special form `agents[type=attacker].capital` (first agent of that type); unknown path raises `SweepPathError` naming the path
5. `expand(spec) -> list[SweepCell]` where `SweepCell = (index: int, axis_values: dict[str, Any], seed: int, config: ScenarioConfig)`; cells enumerate the Cartesian product of axes in spec order, then seeds; `config.name = f"{spec.name}/{index:04d}"`; `overrides` applied before axes, `max_steps` last
6. ADR-0013 guard: if any axis or override touches `amm.fee_bps` or any arbitrageur `min_profit_bps`, `expand` raises `SweepSpecError` unless `termination.peg_recovered.tolerance` is also an axis or an override (the message cites ADR-0013); test both the raise and the pass
7. `run_sweep(spec, output_dir: Path, workers: int = 1) -> Path` runs every cell via `run_scenario` in a `multiprocessing.get_context("spawn").Pool(workers)` (workers=1 runs in-process for debuggability), writing each to `output_dir/<spec.name>/<index:04d>/` (no chart), then aggregates every cell's `summary.json` plus its `axis_values` and `seed` into `output_dir/<spec.name>/sweep.parquet` sorted by `index`, and writes `output_dir/<spec.name>/manifest.json` (`sweep_name, base_scenario_hash, axes, seeds, overrides, cell_count, package_version, python_version, created_utc`)
8. Determinism: `run_sweep` with `workers=1` and again with `workers=4` on a 2×2×1 spec yields byte-identical `sweep.parquet`
9. CLI: `python -m depeg_sim.sweep sweeps/<name>.yaml [--workers N] [--output DIR]` prints `sweep: <name> cells=<n> workers=<w>` then `wrote: <dir>/sweep.parquet` and exits 0; a missing or invalid spec exits 2/3 like `run.py`
10. `sweeps/pool-depth-x-attacker.yaml`: base `scenarios/soros-baseline.yaml`; axes `amm.reserve_stable` and `amm.reserve_reference` **linked** (see Dev Notes: a `linked_axes` list so depth varies as one axis of 4 values {250k, 500k, 1M, 2M}), `agents[type=attacker].capital` {100k, 300k, 600k, 1.2M}; seed 42; `max_steps: 2000` → 16 cells; a test runs a 2×2 subset and asserts the parquet has 4 rows with the expected axis columns
11. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Recovery metrics and manifest round-trip (AC: 1, 2)
  - [x] `analysis/summary.py`: rename + add; update docstring with the ADR-0013 definitions
  - [x] Update `tests/test_summary.py` key list and add the sustained-recovery case (baseline: `steps_run 192 − 100 − 50 = 42`)
  - [x] Update any 1.8 tests referencing the old key
  - [x] `tests/test_run_determinism.py` or new `test_manifest.py`: round-trip hash equality
  - [x] Commit separately: `story 2.1: recovery metrics per ADR-0013; manifest round-trip test`

- [x] Path setter (AC: 4)
  - [x] `experiments/sweep.py`: `set_path`, `SweepPathError`; parse `a.b`, `a[0].b`, `a[type=x].b`
  - [x] Tests: each form; unknown path; frozen model returns a new object; original unchanged

- [x] Spec and expansion (AC: 3, 5, 6, 10)
  - [x] `SweepSpec` + `load_sweep`; `linked_axes` support
  - [x] `expand`; cell naming; ADR-0013 guard
  - [x] `sweeps/pool-depth-x-attacker.yaml`
  - [x] Tests: product order; names; overrides-before-axes; guard raise/pass; 2×2 expansion of the real sweep file

- [x] Runner and aggregation (AC: 7, 8)
  - [x] `run_sweep`; worker function must be a module-level picklable function taking `(cell, output_dir)`; `run_scenario(..., chart=False)` (add the flag if absent)
  - [x] Aggregation to parquet; sweep manifest
  - [x] Tests: 2×2×1 subset, `workers=1` vs `workers=2` byte equality; manifest fields; per-cell dirs exist

- [x] CLI (AC: 9)
  - [x] `experiments/sweep.py` gains `main(argv)`; `src/depeg_sim/sweep.py` thin `__main__` shim or `[project.scripts] depeg-sweep`
  - [x] Tests: exit codes; two output lines

- [x] Tests, lint, close out (AC: 11)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Time the 16-cell sweep at `workers=4` on Seoul; record wall time in Completion Notes (feeds 2.2's budget)
  - [x] Dev Agent Record, Change Log, `Status: review`; propose ADRs for any semantic you had to pin
  - [x] Commit `story 2.1: sweep runner`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.8 (Status: done) and the Epic 1 retro**

- `run_scenario(cfg, *, seed_override, output_dir) -> RunArtifacts` is the single-run
  primitive. It replaces its own directory, is deterministic, and writes a self-describing
  manifest (ADR-0014). Sweeps call it with distinct `run_id`s; because `cfg.name` carries
  the cell index, `run_id` is unique per cell.
- `ScenarioConfig` is frozen; overrides go through `model_copy(update=…)`, nested one
  level at a time (build the new inner model, then the new outer model).
- Chart conventions are code (`plot_peg_trajectory`). Sweeps do not chart per cell.
- ADR-0013: a sweep over fee or arb profit silently makes `peg_recovered` unreachable
  unless tolerance moves with it. The guard in AC 6 exists because of this.
- Builders propose ADRs for judgment calls (CLAUDE.md § Decisions).

[Source: docs/retrospectives/epic-1-retro.md, docs/adr/0013, docs/adr/0014]

### Architecture Alignment

This is the spec's **Experiment Orchestration** layer: expand a parameter space, assign
seeds, execute runs, persist, aggregate. Epic 1 built the engine; this story makes it an
instrument. Monte Carlo (2.2) is a thin layer on top (seeds become a list of 32, and the
aggregation groups by axis).

### Linked axes

Pool depth is two config fields that must move together (`reserve_stable` and
`reserve_reference`). Spec form:

```yaml
name: pool-depth-x-attacker
base: scenarios/soros-baseline.yaml
linked_axes:
  - name: pool_depth
    paths: [amm.reserve_stable, amm.reserve_reference]
    values: [250000, 500000, 1000000, 2000000]
axes:
  agents[type=attacker].capital: [100000, 300000, 600000, 1200000]
seeds: [42]
max_steps: 2000
```

A linked axis appears in `axis_values` and in `sweep.parquet` under its `name`
(`pool_depth`), not under each path. Ordinary axes use their path as the column name.
Expansion order: linked axes first (spec order), then ordinary axes (spec order), then
seeds.

### `set_path` grammar

```
path     := segment ("." segment)*
segment  := ident | ident "[" index "]" | ident "[type=" ident "]"
```

Implementation: walk the model, collecting `(parent_model, attr, index_or_None)` frames,
then rebuild from the leaf outward with `model_copy(update={attr: new_value})`. For a
list element, copy the list, replace the element, and `model_copy` the parent. Keep it
under ~60 lines; no generic path library.

### Worker function

```python
def _run_cell(args: tuple[SweepCell, Path]) -> dict:
    cell, out = args
    arts = run_scenario(cell.config, output_dir=out / f"{cell.index:04d}", chart=False)
    return {"index": cell.index, "seed": cell.seed, **cell.axis_values, **arts.summary}
```

`spawn` context so numpy/matplotlib state is never inherited; `chart=False` avoids
importing pyplot in workers. `imap` in index order, or `map` then sort. With `workers=1`
call `_run_cell` directly (no pool) so tracebacks are readable.

### Aggregated parquet schema

One row per cell: `index, seed, <axis columns…>, <every summary key>`. Axis columns come
first after `index, seed`. `terminated_by` stays a string here; 2.2 turns it into
proportions. Sorted by `index`. Written with `index=False`.

### Expected 16-cell behaviour (for Completion Notes)

Attack of 100k into a 2M pool should recover quickly; 1.2M into 250k should exhaust
reserves or run to `max_steps`. The interesting diagonal is where `terminated_by` flips.
Report the `terminated_by` grid as a 4×4 table in Completion Notes — that table is the
first look at the threshold surface.

### References

- [Source: docs/epics.md#Story-2.1]
- [Source: docs/adr/0013-recovery-tolerance-outside-arb-band.md]
- [Source: docs/adr/0014-manifest-embeds-resolved-config.md]
- [Source: docs/stories/1-8-first-scenario-end-to-end.md#Senior-Developer-Review]
- [Source: docs/BACKGROUND.md#How-economists-explain-it] — first-generation model: the sweep is looking for the Krugman/Flood–Garber exhaustion boundary

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-1-sweep-runner.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

Task 1 (`b5edb32`):

```
$ pytest            # after task 1
330 passed in 2.04s        (the 328 existing, under the renamed keys, + 2 new)
```

Final:

```
$ pytest; echo exit=$?
380 passed in 3.17s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
67 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml; echo exit=$?      # unchanged from 1.8
depeg-sim: scenario=soros-baseline seed=42 hash=2e09f431ce74
run: steps=192 terminated_by=peg_recovered max_depeg_bps=-573.2 reserves_exhausted=False
wrote: output/soros-baseline-42-2e09f431
exit=0

$ time python -m depeg_sim.sweep sweeps/pool-depth-x-attacker.yaml --workers 4; echo exit=$?
sweep: pool-depth-x-attacker cells=16 workers=4
wrote: output/pool-depth-x-attacker/sweep.parquet

real	0m0.558s
user	0m2.733s
sys	0m0.120s
exit=0

$ time python -m depeg_sim.sweep sweeps/pool-depth-x-attacker.yaml --workers 1 --output <scratch>/w1
real	0m0.554s
$ time python -m depeg_sim.sweep sweeps/pool-depth-x-attacker.yaml --workers 4 --output <scratch>/w4
real	0m0.571s
$ cmp w1/pool-depth-x-attacker/sweep.parquet w4/pool-depth-x-attacker/sweep.parquet
sweep.parquet identical (workers 1 vs 4)

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/analysis/summary.py               43      1    98%   68
src/depeg_sim/experiments/runner.py             51      0   100%
src/depeg_sim/experiments/sweep.py             169      0   100%
src/depeg_sim/sweep.py                           3      3     0%   7-10
TOTAL                                         1513     11    99%
```

CI on push of `933eb06`:

```
completed	success	story 2.1: sweep runner	ci	main	push	37159786414	40s	2026-10-03T22:50:30Z
```

(`src/depeg_sim/sweep.py` is the `-m` shim. It runs in a subprocess in
`test_module_entry_point_with_spawn_workers`, which coverage doesn't trace.)

Seoul has 12 cores (`nproc`).

328 → 380 tests (+52), counted with `pytest --collect-only`: task 1 +2 (summary sustained
recovery, manifest round-trip); `test_set_path.py` 16; `test_sweep.py` 33; `test_runner.py`
+1 (`chart` flag).

### Completion Notes List

- **16-cell sweep wall time: 0.56 s at `workers=4`** (0.55 s at `workers=1`). Every cell
  ends by step 75–212, far below the 2000 cap, so a cell costs ~25 ms. The spawn pool's
  startup (fresh interpreters importing numpy/pandas/pydantic) cancels the parallel gain
  at this size. For 2.2's budget: per-cell cost scales with `steps_run`. A cell that runs
  to its `max_steps` cap costs proportionally more. Workers pay off once cells take
  longer than spawn startup (~0.3 s). This is an extrapolation, not a measurement.
- **4×4 `terminated_by` table (first look at the threshold surface):**

  | pool depth \ attacker capital | 100k | 300k | 600k | 1.2M |
  |---|---|---|---|---|
  | 250k | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
  | 500k | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
  | 1M   | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
  | 2M   | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |

  `steps_run`: 195/205/212/86, 188/199/202/76, 181/192/196/75, 173/185/189/75 (rows as
  above). `max_depeg_bps` runs from −187 (100k into 2M) to −5430 (1.2M into 250k).
  `steps_to_sustained_recovery`: 22–62 where recovered.
- **Surprise → proposed ADR-0016 (finding).** The flip isn't diagonal as the Dev Notes
  expected. It's a column: termination depends on attacker capital only, at every pool
  depth. Depth changes the trough (×4 shallower from 250k to 2M) and recovery time, not
  the verdict. The event logs show the mechanism. The arbitrageur is the only redeemer
  and recycles the attacker's dumped stable into redemptions. Whatever the defender's
  400k doesn't absorb ends up against the 500k reserves, so exhaustion arrives when
  capital ≳ budget + reserves. That is a first-generation-model result, and the ADR
  suggests axes for 2.2/2.5 to test it.
- **Spec conflict → proposed ADR-0015.** AC 5 (`name = "<spec>/<index:04d>"`) together
  with `run_scenario`'s `run_id = "<name>-<seed>-<hash8>"` makes AC 7's exact
  `<sweep>/<index:04d>/` path impossible without changing `run_scenario`. The Dev Notes
  worker (`output_dir=out/<index>`) would nest `<sweep>/0000/<sweep>/0000-42-…/`. I call
  `run_scenario(cell.config, output_dir=output_dir, chart=False)` instead, so each cell
  is `<output_dir>/<spec.name>/<index:04d>-<seed>-<hash8>/`. The worker is still a
  module-level `_run_cell((cell, output_dir))`.
- **`set_path` validates.** The rebuild uses `model_copy(update=…)` as specified, but the
  leaf is set through the parent's `model_validate`, and the whole config is re-validated
  at the end. YAML ints become floats (`250000` → `250000.0`, so hashes match a
  hand-written YAML). Invalid values raise `pydantic.ValidationError`, and model-level
  validators (unique agent ids) still run. Unknown paths raise `SweepPathError` with the
  path in the message. The CLI maps both to exit 3.
- **ADR-0013 guard details.** It triggers on `amm.fee_bps` or any `agents…min_profit_bps`
  path, in axes, linked axes or overrides. It's satisfied by
  `termination.peg_recovered.tolerance` as an axis or override, and skipped when the base
  scenario has no `peg_recovered` (nothing to make unreachable).
- **Spec details beyond the AC list:** `SweepSpec.name` must match `[A-Za-z0-9_.-]+` (it's
  a directory name), `max_steps > 0`, axis names must be unique. Seeds are written into
  `cfg.seed` (so each cell's manifest/config carries its seed), applied after
  `max_steps`; `name` is set last. `base` is resolved relative to the working directory,
  like `run.py`'s scenario argument.
- **Aggregation always reads `summary.json` from disk** (for `workers=1` too), so both
  paths build the parquet from identical inputs. Summary columns follow `SUMMARY_KEYS`
  order (the files are sorted-key JSON). `seed` appears once, in position 2.
  `terminated_by` stays a string.
- **Sweep manifest** has the AC 7 keys plus `max_steps`, needed to reproduce the cells.
  `axes` is a list of `{name, paths, values}` in expansion order; an ordinary axis has
  `paths == [name]`.
- **`run_scenario(chart=True)` now draws the chart itself** (pyplot imported lazily, so
  sweep workers never import it). `cli.py` passes `chart=not args.no_chart`. CLI output
  is unchanged. Existing 1.8 tests that list run-dir files now pass `chart=False`. In
  scope: the new default would otherwise add a PNG to those listings.
- `AC 8` is tested at workers 1 vs 2 (CI has 2 cores, per the context's test
  standards). I also checked it by hand at 1 vs 4 on the full 16-cell sweep (`cmp`
  above).
- `run_sweep` replaces `<output_dir>/<spec.name>/` on rerun.
- Not done (not in scope): README section for sweeps, `depeg-sweep` console script.

### File List

**Created:**

- `src/depeg_sim/experiments/sweep.py`
- `src/depeg_sim/sweep.py` (`python -m` shim)
- `sweeps/pool-depth-x-attacker.yaml`
- `docs/adr/0015-sweep-cell-directory-layout.md` (Proposed)
- `docs/adr/0016-outcome-set-by-capital-not-depth.md` (Proposed, finding)
- `tests/test_set_path.py`, `tests/test_sweep.py`

**Modified:**

- `src/depeg_sim/analysis/summary.py` (task 1)
- `src/depeg_sim/experiments/runner.py` (`chart` flag)
- `src/depeg_sim/cli.py` (uses the flag)
- `tests/test_summary.py`, `tests/test_runner.py` (task 1; `chart` flag)
- `tests/test_charts.py`, `tests/test_run_determinism.py` (`chart=False`)
- `docs/stories/2-1-sweep-runner.md`

## Change Log

- 2026-10-03: Story drafted by dev manager from epics.md (Epic 2 expanded after Epic 1 retro)
- 2026-10-03: Implemented by Claude Code (Opus 5.5); 380 tests pass; 16-cell sweep 0.56 s at workers=4; ADR-0015 and ADR-0016 proposed; status → review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-03
**Outcome:** **APPROVE** ✅

### Summary

The engine is now an instrument. Reviewer re-ran on a separate machine: 380 passed, ruff
clean; the 16-cell sweep at `workers=2` reproduced the builder's `terminated_by` grid and
trough table to the bps. CI run 37159833757 green. Both proposed ADRs accepted; 0016 is
the best piece of analysis in the project so far.

### Rulings

- **ADR-0015 (cell directory layout): Accepted.** My AC 7 and Dev Notes contradicted AC 5
  and the 1.8 `run_id` convention. The builder found the one layout that satisfies the
  intent without adding a second naming path. Spec defect; mine.
- **ADR-0016 (capital, not depth, decides): Accepted as a finding, amended.** The
  amendment states the conservation law (two sinks for attacker stable; depth is a price,
  not a sink) and re-aims 2.6's primary axis at `capital / (budget + reserves)`. Candidate
  headline: *depth decides how far the peg falls; resources decide whether it comes back.*
- **`set_path` re-validates the whole config.** Correct; catches duplicate ids and
  coerces types. Ratified.
- **Sweep manifest carries the resolved spec.** Consistent with ADR-0014. Ratified.
- **`run_scenario` draws the chart itself behind `chart=`.** Fine; CLI unchanged.
- **`/usr/bin/time` absent on Seoul; bash `time` used.** Correct adaptation; no install needed.

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1 | ✅ | `steps_to_first_band_entry` 2, `steps_to_sustained_recovery` 42 on baseline; commit `b5edb32` at 330 |
| 2 | ✅ | Round-trip hash test |
| 3 | ✅ | `SweepSpec`, `load_sweep`, `linked_axes` |
| 4 | ✅ | `set_path` three forms; 16 tests; unknown path names the path |
| 5 | ✅ | `expand` order and naming |
| 6 | ✅ | ADR-0013 guard raise/pass tests |
| 7 | ✅ | `run_sweep`, spawn pool, disk aggregation; layout per ADR-0015 |
| 8 | ✅ | Byte-identical across worker counts (reviewer: 2 vs builder's 1 and 4 all match) |
| 9 | ✅ | CLI two lines; exit codes |
| 10 | ✅ | 16-cell sweep file; 2×2 subset test |
| 11 | ✅ | `380 passed`, `All checks passed!`, CI green |

**11 of 11 ACs met.**

### Key Findings

No High or Medium issues.

**Low / advisory:**
- **[LOW-1] Sweep is CPU-trivial (0.56 s / 16 cells).** 2.2's 512-run Monte Carlo will
  take ~20 s, not 10 min. The budget in 2.2 AC 5 is generous by 30×; keep it as a ceiling.
- **[LOW-2] Spawn overhead dominates at this scale.** Not worth optimising; sweeps will
  grow.

### Learnings for Story 2.2

- `sweep.parquet` has one row per cell with `terminated_by` as a string; 2.2 groups by
  axis columns and turns it into proportions.
- ADR-0016 changes 2.2's grid: add `agents[type=defender].budget` and
  `redemption.reserves` as axes, and refine capital between 600k and 1.2M.
- Every cell finished by step 212; `max_steps: 2000` is plenty for the MC sweep.
- 2026-10-03: Senior review APPROVE; status set to done. ADR-0015 accepted; ADR-0016 accepted with amendment (conservation law; 2.6 primary axis).
