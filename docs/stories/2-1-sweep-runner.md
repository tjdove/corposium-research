# Story 2.1: Sweep Runner and Recovery Metrics

Status: in-progress

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

- [ ] Recovery metrics and manifest round-trip (AC: 1, 2)
  - [ ] `analysis/summary.py`: rename + add; update docstring with the ADR-0013 definitions
  - [ ] Update `tests/test_summary.py` key list and add the sustained-recovery case (baseline: `steps_run 192 − 100 − 50 = 42`)
  - [ ] Update any 1.8 tests referencing the old key
  - [ ] `tests/test_run_determinism.py` or new `test_manifest.py`: round-trip hash equality
  - [ ] Commit separately: `story 2.1: recovery metrics per ADR-0013; manifest round-trip test`

- [ ] Path setter (AC: 4)
  - [ ] `experiments/sweep.py`: `set_path`, `SweepPathError`; parse `a.b`, `a[0].b`, `a[type=x].b`
  - [ ] Tests: each form; unknown path; frozen model returns a new object; original unchanged

- [ ] Spec and expansion (AC: 3, 5, 6, 10)
  - [ ] `SweepSpec` + `load_sweep`; `linked_axes` support
  - [ ] `expand`; cell naming; ADR-0013 guard
  - [ ] `sweeps/pool-depth-x-attacker.yaml`
  - [ ] Tests: product order; names; overrides-before-axes; guard raise/pass; 2×2 expansion of the real sweep file

- [ ] Runner and aggregation (AC: 7, 8)
  - [ ] `run_sweep`; worker function must be a module-level picklable function taking `(cell, output_dir)`; `run_scenario(..., chart=False)` (add the flag if absent)
  - [ ] Aggregation to parquet; sweep manifest
  - [ ] Tests: 2×2×1 subset, `workers=1` vs `workers=2` byte equality; manifest fields; per-cell dirs exist

- [ ] CLI (AC: 9)
  - [ ] `experiments/sweep.py` gains `main(argv)`; `src/depeg_sim/sweep.py` thin `__main__` shim or `[project.scripts] depeg-sweep`
  - [ ] Tests: exit codes; two output lines

- [ ] Tests, lint, close out (AC: 11)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Time the 16-cell sweep at `workers=4` on Seoul; record wall time in Completion Notes (feeds 2.2's budget)
  - [ ] Dev Agent Record, Change Log, `Status: review`; propose ADRs for any semantic you had to pin
  - [ ] Commit `story 2.1: sweep runner`, push to `main`

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

_(fill in)_

### Debug Log References

_(real command output with exit codes; include the 16-cell sweep timing)_

### Completion Notes List

_(include the 4×4 terminated_by table)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-03: Story drafted by dev manager from epics.md (Epic 2 expanded after Epic 1 retro)
