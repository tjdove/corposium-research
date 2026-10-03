# Story 1.8: First Scenario End to End

Status: in-progress

## Story

As a **researcher**,
I want `python run.py scenarios/soros-baseline.yaml` to produce a parquet timeseries, a summary JSON and a chart,
so that the project has its first reproducible result and first public post.

## Acceptance Criteria

1. Carry-over: `DecisionTrace.record` accepts `action: dict | list | None` natively (ADR-0011 encoding unchanged: a list is stored as `{"actions": [...]}`); one test
2. `src/depeg_sim/experiments/runner.py`: `build_world(cfg, ctx)` registers, in this fixed order: `environment`, `oracle`, `amm`, `redemption`, agents from `build_agents(cfg)` in config order, then `metrics`; `run_scenario(cfg, *, seed_override=None, output_dir) -> RunArtifacts` builds the context and world, runs the engine, writes outputs, returns paths and the `RunResult`
3. `src/depeg_sim/analysis/metrics.py`: `MetricsCollector(name="metrics")`, a hook subsystem on `METRIC_UPDATE` (registered last so it sees settled agent balances), appends one row per step when `step % record_every == 0`, with columns exactly: `step, elapsed_seconds, reference_price, oracle_price, amm_price, peg_deviation, amm_reserve_stable, amm_reserve_reference, redemption_reserves, redemption_queue_depth, redemption_queued_total, attacker_stable, attacker_reference, attacker_pnl, arbitrageur_pnl, defender_reference, defender_spent, defender_pnl` (agent columns use the first agent of each type; `NaN` when absent); `to_dataframe() -> pandas.DataFrame`
4. `src/depeg_sim/analysis/summary.py`: `summarize(cfg, result, metrics_df, world) -> dict` with keys exactly: `scenario, seed, scenario_hash, steps_run, terminated_by, max_depeg_bps` (most negative deviation × 10⁴), `step_of_max_depeg, final_depeg_bps, time_to_recovery_steps` (first step after `max_depeg` at which `abs(dev) <= peg_recovered.tolerance`, else `null`), `reserves_exhausted` (bool), `redemption_paid_total, defender_spent, defender_interventions, attacker_pnl, arbitrageur_pnl, phase_order_version, package_version`
5. `src/depeg_sim/experiments/writer.py`: `write_run(run_dir, cfg, result, metrics_df, summary)` writes `timeseries.parquet` (pyarrow, no index), `summary.json` (sorted keys, indent 2), `events.jsonl` (one event per line, `payload` as nested JSON), `decisions.jsonl` (only if `trace_decisions`), `manifest.json` (`run_id, scenario_name, scenario_hash, seed, phase_order_version, package_version, python_version, created_utc, files: [...]`); `run_id = f"{scenario_name}-{seed}-{scenario_hash[:8]}"`
6. `src/depeg_sim/analysis/charts.py`: `plot_peg_trajectory(run_dir) -> Path` reads `timeseries.parquet` + `events.jsonl` and writes `peg_trajectory.png` (matplotlib, Agg backend, 150 dpi) with two stacked panels sharing the x-axis in **elapsed minutes**: top = `peg_deviation` in bps with a zero line and the `peg_recovered.tolerance` band shaded; bottom = `redemption_reserves` and `defender_reference` as two lines; vertical markers at the attacker's first `swap_executed` and at each `defend_buy`-bearing `swap_executed`; title includes scenario name and seed; a footer line gives `scenario_hash[:12]`
7. `cli.main` wires `load_scenario → run_scenario → plot_peg_trajectory` and prints: `depeg-sim: scenario=<name> seed=<seed> hash=<12>`, `run: steps=<n> terminated_by=<reason> max_depeg_bps=<x> reserves_exhausted=<bool>`, `wrote: <run_dir>` on three lines; `--output` sets the parent directory; `--no-chart` skips the PNG; exit codes unchanged (0/2/3)
8. `scenarios/soros-baseline.yaml` is retuned so the run **does not** end by `max_steps` and the chart shows the attack, the defense and the outcome (see Dev Notes for the lever chosen); the file carries a top comment block stating which ADR-0010 option it uses and why; `max_steps` stays 5000
9. Determinism: running the baseline twice yields byte-identical `timeseries.parquet` and `summary.json` (test compares file bytes); `events.jsonl` identical; `manifest.json` identical except `created_utc`
10. `--seed 7` produces a different `manifest.seed`, a different `run_id`, and (because baseline volatility is 0) an **identical** `timeseries.parquet` to seed 42 — assert this; it proves the seed only matters through the rng, which the flat baseline never draws
11. A second scenario `scenarios/soros-volatile.yaml` (baseline + `volatility_per_step: 0.0005`) is added and a test shows seeds 42 and 7 give different `timeseries.parquet` for it
12. README quick start updated to the real commands and output tree; `output/.gitkeep` remains the only tracked file under `output/`
13. `pytest` and `ruff check .` pass; CI green; CI additionally runs `python run.py scenarios/soros-baseline.yaml --output /tmp/ci-run` and uploads `peg_trajectory.png` as a workflow artifact

## Tasks / Subtasks

- [ ] Carry-over (AC: 1)
  - [ ] Widen `DecisionTrace.record` type; test list → `{"actions": [...]}`; commit separately `story 1.8: decision record accepts action list`

- [ ] Metrics and summary (AC: 3, 4)
  - [ ] `analysis/metrics.py` `MetricsCollector`; `analysis/summary.py` `summarize`
  - [ ] Tests with a short engine run: column set exact; `record_every 5` yields the right row count; summary keys exact; `time_to_recovery_steps` null when never recovered

- [ ] Runner and writer (AC: 2, 5)
  - [ ] `experiments/runner.py` `build_world`, `run_scenario`, `RunArtifacts` dataclass
  - [ ] `experiments/writer.py` `write_run`
  - [ ] Tests: registration order (assert `registry` names in order); all files present; parquet round-trips; manifest fields

- [ ] Chart (AC: 6)
  - [ ] `analysis/charts.py` `plot_peg_trajectory`; `matplotlib.use("Agg")` at module top
  - [ ] Test: PNG exists, non-trivial size (> 20 kB), and `plt.imread` shape has 3–4 channels; no display backend needed

- [ ] Baseline retune (AC: 8, 11)
  - [ ] Choose an ADR-0010 lever (Dev Notes); edit `scenarios/soros-baseline.yaml` with a comment block; add `scenarios/soros-volatile.yaml`
  - [ ] Run it; record `terminated_by`, `max_depeg_bps`, `steps_run` in Completion Notes; if `max_steps` still fires, try the next lever, do not widen `max_steps`

- [ ] CLI (AC: 7)
  - [ ] Wire; `--no-chart`; update `tests/test_smoke.py` to the new three-line output

- [ ] Determinism and seed tests (AC: 9, 10)
  - [ ] `tests/test_run_determinism.py`: byte equality; seed-invariance on flat baseline; seed-variance on volatile

- [ ] README and CI (AC: 12, 13)
  - [ ] README quick start + output tree; `.github/workflows/ci.yml` adds the run step and `actions/upload-artifact@v4` for the PNG

- [ ] Tests, lint, close out (AC: 13)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`; paste the three CLI output lines
  - [ ] Dev Agent Record, Change Log, `Status: review`; **attach or describe the chart** in Completion Notes
  - [ ] Commit `story 1.8: first scenario end to end`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 1.7 (Status: done)**

- All modules exist with `from_config` factories: `ReferencePrice.from_config(env_cfg)`,
  `Oracle.from_config(oracle_cfg, source)`, `ConstantProductAMM.from_config(amm_cfg, peg_price)`,
  `RedemptionModule.from_config(red_cfg)`, `build_agents(cfg)`.
- Agents settle in `METRIC_UPDATE`; the metrics collector must register **after** agents so
  the same phase sees settled balances (registration order = execution order within a phase).
- Decision records: one per agent per step; multi-action steps use `{"actions": [...]}` (ADR-0011).
- **ADR-0010 (dead zone):** the current baseline ends only by `max_steps` and sits at
  −18 bps forever. 1.8 must retune.

[Source: docs/stories/1-7-agents.md#Senior-Developer-Review, docs/adr/0010-dead-zone-finding.md]

### Architecture Alignment

This story is the spec's Persistence/Event Logging layer (file-based per ADR-0004) plus
the thinnest slice of the Analysis layer: one chart. The experiment *runner* (sweeps, Monte
Carlo) is Epic 2; `run_scenario` here is the single-run primitive it will call.

### Retuning the baseline (ADR-0010 options, in preference order)

The first public chart must show a dynamic with an ending. Try in order; stop at the first
that terminates by something other than `max_steps` **and** shows a visible attack:

1. **Tolerance ≥ arb band.** Set `peg_recovered.tolerance: 0.006` (60 bps, just outside the
   50 bps band). Recovery becomes reachable once the arbitrageur has done its work. This is
   the most defensible: "recovered" means "within the band where no rational actor acts."
   Expected: terminates `peg_recovered` ~100 steps after the arb settles the price.
2. **Stronger attack.** Raise attacker capital to 600k and defender budget stays 400k.
   Expected: deeper trough, possibly `reserves_exhausted` if the arb redeems heavily.
3. **Smaller pool.** 500k/500k. Same capital, twice the impact.

Record which lever, the resulting `terminated_by`, `max_depeg_bps` and `steps_run`. If
option 1 works it becomes the baseline; options 2–3 become the seeds of Epic 2's sweep.
`start_step` must stay below `peg_recovered.for_steps` (ADR-0010, second observation).

### Metrics column sources

| column | source |
|---|---|
| `reference_price` | `environment.price` |
| `oracle_price` | `oracle.price` |
| `amm_price`, `peg_deviation`, `amm_reserve_*` | AMM properties |
| `redemption_*` | redemption properties |
| `attacker_*`, `defender_*`, `arbitrageur_pnl` | first agent of that type: `balances`, `pnl(ctx)`, `defender.spent` |

Collect in `METRIC_UPDATE` **after** agents (registration order). `elapsed_seconds` from
`ctx.clock`.

### Chart conventions (keep for every chart in the note)

- Figure 10×6 in, 150 dpi, `constrained_layout=True`.
- x-axis in **minutes** (`elapsed_seconds / 60`) so a 5,000-step run reads as "16.7 hours"
  rather than "60,000 s".
- Deviation in **bps**, zero line dashed, tolerance band as a light `axvspan`/`axhspan`.
- Event markers: attacker start = one vertical line; defender buys = short ticks along the
  top of the deviation panel, not full-height lines (they clutter).
- Colors: deviation in one dark line; reserves and defender budget in two distinct lines
  with a legend. No red/green semantic colouring (colour-blind readers; also avoids
  implying judgment).
- Footer: `scenario=<name> seed=<seed> hash=<12>` in small monospace so every published
  chart is traceable to a config.

### Output tree (for README)

```
output/soros-baseline-42-7c4f870b/
  manifest.json
  summary.json
  timeseries.parquet
  events.jsonl
  decisions.jsonl
  checkpoints/step-000500.json …
  peg_trajectory.png
```

(The hash prefix changes when the baseline is retuned; compute it, don't copy.)

### CI artifact

```yaml
      - run: python run.py scenarios/soros-baseline.yaml --output /tmp/ci-run
      - uses: actions/upload-artifact@v4
        with:
          name: peg-trajectory
          path: /tmp/ci-run/**/peg_trajectory.png
```

### References

- [Source: docs/epics.md#Story-1.8]
- [Source: docs/adr/0004-files-not-sql.md]
- [Source: docs/adr/0010-dead-zone-finding.md]
- [Source: docs/adr/0011-multi-action-decision-record.md]
- [Source: docs/stories/1-7-agents.md#Senior-Developer-Review]

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-8-first-scenario-end-to-end.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output with exit codes, including the three CLI lines)_

### Completion Notes List

_(include: which ADR-0010 lever, resulting terminated_by / max_depeg_bps / steps_run, and a description of what the chart shows)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.7 review
