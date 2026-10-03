# Story 1.8: First Scenario End to End

Status: done

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

- [x] Carry-over (AC: 1)
  - [x] Widen `DecisionTrace.record` type; test list → `{"actions": [...]}`; commit separately `story 1.8: decision record accepts action list`

- [x] Metrics and summary (AC: 3, 4)
  - [x] `analysis/metrics.py` `MetricsCollector`; `analysis/summary.py` `summarize`
  - [x] Tests with a short engine run: column set exact; `record_every 5` yields the right row count; summary keys exact; `time_to_recovery_steps` null when never recovered

- [x] Runner and writer (AC: 2, 5)
  - [x] `experiments/runner.py` `build_world`, `run_scenario`, `RunArtifacts` dataclass
  - [x] `experiments/writer.py` `write_run`
  - [x] Tests: registration order (assert `registry` names in order); all files present; parquet round-trips; manifest fields

- [x] Chart (AC: 6)
  - [x] `analysis/charts.py` `plot_peg_trajectory`; `matplotlib.use("Agg")` at module top
  - [x] Test: PNG exists, non-trivial size (> 20 kB), and `plt.imread` shape has 3–4 channels; no display backend needed

- [x] Baseline retune (AC: 8, 11)
  - [x] Choose an ADR-0010 lever (Dev Notes); edit `scenarios/soros-baseline.yaml` with a comment block; add `scenarios/soros-volatile.yaml`
  - [x] Run it; record `terminated_by`, `max_depeg_bps`, `steps_run` in Completion Notes; if `max_steps` still fires, try the next lever, do not widen `max_steps`

- [x] CLI (AC: 7)
  - [x] Wire; `--no-chart`; update `tests/test_smoke.py` to the new three-line output

- [x] Determinism and seed tests (AC: 9, 10)
  - [x] `tests/test_run_determinism.py`: byte equality; seed-invariance on flat baseline; seed-variance on volatile

- [x] README and CI (AC: 12, 13)
  - [x] README quick start + output tree; `.github/workflows/ci.yml` adds the run step and `actions/upload-artifact@v4` for the PNG

- [x] Tests, lint, close out (AC: 13)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`; paste the three CLI output lines
  - [x] Dev Agent Record, Change Log, `Status: review`; **attach or describe the chart** in Completion Notes
  - [x] Commit `story 1.8: first scenario end to end`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

Task 1 (`7cd9ea4`):

```
$ pytest            # after task 1
297 passed in 0.59s        (296 existing + 1 new)
```

Retune trial (ADR-0010 option 1 only; scratch script, same world as `build_world`):

```
tolerance 0.006 -> peg_recovered 192 max_depeg_bps -573.2 at 50 final -18.26 reserves 409101
```

Final:

```
$ pytest; echo exit=$?
328 passed in 1.86s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
63 files already formatted
exit=0

$ python run.py scenarios/soros-baseline.yaml; echo exit=$?
depeg-sim: scenario=soros-baseline seed=42 hash=2e09f431ce74
run: steps=192 terminated_by=peg_recovered max_depeg_bps=-573.2 reserves_exhausted=False
wrote: output/soros-baseline-42-2e09f431
exit=0

$ python run.py scenarios/soros-volatile.yaml --output <scratch>
depeg-sim: scenario=soros-volatile seed=42 hash=84ad0b810807
run: steps=426 terminated_by=peg_recovered max_depeg_bps=-573.2 reserves_exhausted=False

$ pytest --cov=depeg_sim --cov-report=term-missing   (excerpt)
src/depeg_sim/analysis/charts.py                66      0   100%
src/depeg_sim/analysis/metrics.py               44      0   100%
src/depeg_sim/analysis/summary.py               41      1    98%   59
src/depeg_sim/cli.py                            36      0   100%
src/depeg_sim/experiments/runner.py             48      0   100%
src/depeg_sim/experiments/writer.py             35      0   100%
TOTAL                                         1339      8    99%
```

CI on push of `9b344fe` (run 37081609248):

```
completed	success	story 1.8: first scenario end to end	ci	main	push	37081609248	38s	2026-10-03T00:19:57Z
Run python run.py scenarios/soros-baseline.yaml --output /tmp/ci-run
  depeg-sim: scenario=soros-baseline seed=42 hash=2e09f431ce74
  run: steps=192 terminated_by=peg_recovered max_depeg_bps=-573.2 reserves_exhausted=False
  wrote: /tmp/ci-run/soros-baseline-42-2e09f431
Run actions/upload-artifact@v4
  Artifact peg-trajectory has been successfully uploaded! Final size is 95186 bytes. Artifact ID is 11258792473
```

296 → 328 tests (+32), counted with `pytest --collect-only`: 1 decision-record (task 1),
11 metrics (incl. 4 parametrized guards), 6 summary, 5 runner/writer, 3 chart, 5
determinism/seed, and +1 smoke (`--no-chart`; smoke went 5 → 6, the others rewritten for
the three-line output).

### Completion Notes List

- **Retune: ADR-0010 option 1, tolerance ≥ arb band.** `peg_recovered.tolerance`
  0.001 → 0.006 (60 bps, just outside the 50 bps fee + min-profit band). Nothing else in
  the scenario changed; `max_steps` stays 5000. Result: `terminated_by=peg_recovered`,
  `steps_run=192`, `max_depeg_bps=-573.2` (step 50). Options 2 and 3 were not tried
  because option 1 met the stop condition. The YAML has a header comment block. Because
  this sets a rule for every future scenario, I proposed **ADR-0013** (tolerance sits
  just outside the arbitrage band).
- **Chart (`output/soros-baseline-42-2e09f431/peg_trajectory.png`).** Top panel: flat at
  0 bps for the first 10 minutes. At the attack marker (10.0 min, step 50) it plunges to
  the trough of −573 bps. Then a sawtooth: the attacker's decaying sells push it down
  and the defender plus arbitrageur buy it back. The 16 defender buys appear as orange
  ticks along the top from 10.2 to 15.4 min (steps 51–77). The last buy overshoots to
  +94 bps at 15.4 min. The swings narrow and the line last leaves the ±60 bps grey band
  at 18.2 min (step 91). After that it relaxes towards −18 bps and stays inside the
  band. The run ends by `peg_recovered` at 38.2 min (step 192, 100 in-band steps).
  Bottom panel: the defender budget (orange) falls from 400k to ~199k in a staircase
  over 10–15.4 min, then is flat. Redemption reserves (blue) step down from 500k to
  ~409k between ~10.8 and ~23 min as the arbitrageur redeems, and never come close to
  exhaustion. Footer: `scenario=soros-baseline seed=42 hash=2e09f431ce74`. I viewed
  the rendered PNG to check this.
- **The run's ending still contains the ADR-0010 dead zone.** The price recovers *into
  the band* and parks at −18.3 bps. With the 60 bps tolerance that now counts as
  recovered. The chart shows both facts.
- **`time_to_recovery_steps` is 2 on the baseline.** That's per the AC definition: the
  first recorded step after the trough with |dev| ≤ tolerance. Step 52 overshoots into
  the band before the price falls out again. It measures first touch, not sustained
  recovery. I implemented it as a duration (recovery step − `step_of_max_depeg`), which
  is what the name suggests. The AC wording ("first step after max_depeg at which…")
  could also be read as a step index. Recorded in ADR-0013's consequences. A "sustained"
  variant would be an Epic 2 metric.
- **`manifest.json` has one key beyond the AC 5 list: `config`** (the resolved
  scenario). `plot_peg_trajectory(run_dir)` needs the tolerance band, the step interval
  and the attacker/defender ids, and no other artifact holds them. Proposed
  **ADR-0014**. `files` lists everything in the run dir when the manifest is written
  (checkpoints included). The chart is drawn afterwards, so it isn't listed.
- **Run dir replacement.** `run_scenario` deletes an existing `output_dir/<run_id>/`
  before running, so stale checkpoints or a stale PNG never mix with a new run.
- **Determinism.** Two baseline runs give byte-identical parquet, summary, events,
  decisions and checkpoints. Manifests match without `created_utc`. **Seed 42 vs 7 on
  the flat baseline: identical `timeseries.parquet`**, different `run_id`/`seed`
  (asserted). On `soros-volatile` the parquet differs. The volatile run itself ends
  `peg_recovered` at step 426.
- **CLI.** `max_depeg_bps` is printed to one decimal. `reserves_exhausted` prints
  Python `True`/`False`. Exit codes 0/2/3 are unchanged, and 2 and 3 create no output
  directory (tested).
- **Summary JSON is strict.** NaN becomes `null`, numpy scalars become Python types.
  `attacker_pnl` / `arbitrageur_pnl` are the agents' `pnl_last`, settled at the last
  step's `METRIC_UPDATE`.
- **Tests outside the new files that the retune affected (in scope):**
  `tests/test_agents_integration.py` asserted the 1.7 dead-zone outcome (`max_steps`).
  It is now pinned to the pre-retune tolerance 0.001 via a new `tolerance=` argument on
  `tests/agent_world.config`, so it still documents ADR-0010. `tests/test_smoke.py` is
  updated to the three-line output and now writes to `tmp_path`. The old smoke test
  had written into the repo's `output/`; I removed the two directories it created.
  `output/.gitkeep` is still the only tracked file there.
- `DecisionTrace.record` now wraps a list itself (ADR-0011 encoding), so
  `Agent.record` passes actions through unchanged.
- CI artifact upload confirmed: see the Debug Log.

### File List

**Created:**

- `src/depeg_sim/analysis/metrics.py`
- `src/depeg_sim/analysis/summary.py`
- `src/depeg_sim/analysis/charts.py`
- `src/depeg_sim/experiments/runner.py`
- `src/depeg_sim/experiments/writer.py`
- `scenarios/soros-volatile.yaml`
- `docs/adr/0013-recovery-tolerance-outside-arb-band.md` (Proposed)
- `docs/adr/0014-manifest-embeds-resolved-config.md` (Proposed)
- `tests/test_metrics.py`, `tests/test_summary.py`, `tests/test_runner.py`,
  `tests/test_charts.py`, `tests/test_run_determinism.py`

**Modified:**

- `src/depeg_sim/kernel/events.py` (task 1), `src/depeg_sim/agents/base.py` (task 1)
- `src/depeg_sim/cli.py`
- `scenarios/soros-baseline.yaml`
- `README.md`, `.github/workflows/ci.yml`
- `tests/test_events.py` (task 1), `tests/test_smoke.py`, `tests/agent_world.py`,
  `tests/test_agents_integration.py`
- `docs/stories/1-8-first-scenario-end-to-end.md`

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md after Story 1.7 review
- 2026-10-02: Implemented by Claude Code (Opus 5.5); 328 tests pass; baseline retuned via ADR-0010 option 1 (ends peg_recovered at step 192); ADR-0013, ADR-0014 proposed; status → review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-02
**Outcome:** **APPROVE** ✅ — Epic 1 complete

### Summary

The project now produces its first reproducible result. Reviewer re-ran on a separate
machine: 328 passed, ruff clean; two baseline runs produced byte-identical
`timeseries.parquet`; summary matched the builder's to full precision
(`peg_recovered` at 192, trough −573.2 bps at step 50, final −18.26 bps, defender spent
200,656, redemption paid 90,899). CI run 37081677864 green with the `peg-trajectory`
artifact uploaded. Reviewer opened the PNG: it follows every chart convention and reads
clearly — a 10-minute flat line, a cliff at the attack marker, a saw-tooth as defender
buys (orange ticks) and attacker sells alternate, a final overshoot to +94 bps from the
defender's last buy, then the slow settle to −18 bps inside the shaded ±60 bps band. The
bottom panel shows the defender spending half its budget by minute 15 and reserves losing
91k to arbitrageur redemptions and never approaching exhaustion.

### Rulings

- **ADR-0013 (tolerance outside the arb band): Accepted, amended.** The rule is right and
  the reasoning about sweeps is exactly the trap Epic 2 must avoid. Amendment: the
  `time_to_recovery_steps` definition in AC 4 produces a misleading number (2); Story 2.1
  splits it into `steps_to_first_band_entry` and `steps_to_sustained_recovery`.
- **ADR-0014 (manifest embeds config): Accepted.** Self-describing run directories are
  worth 1.5 kB. The round-trip property (`model_validate(manifest["config"]).content_hash()
  == manifest["scenario_hash"]`) should get a test in 2.1.
- **Rerun replaces the directory.** Correct for determinism; a stale file from a previous
  run would be worse than a missing one.
- **`test_agents_integration.py` pins the old tolerance** so the ADR-0010 dead zone stays
  under test. Good instinct: findings should have regression tests.

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1 | ✅ | `record` accepts list; ADR-0011 encoding kept; commit `7cd9ea4` |
| 2 | ✅ | `build_world` fixed order (tested); `run_scenario` |
| 3 | ✅ | Exact column list; `record_every`; NaN for absent agents |
| 4 | ✅ | Exact key list; reviewer-verified values |
| 5 | ✅ | Six files + manifest (ADR-0014 adds `config`) |
| 6 | ✅ | Chart per conventions; reviewer inspected |
| 7 | ✅ | Three CLI lines; `--no-chart`; exit codes |
| 8 | ✅ | Option 1 retune; `peg_recovered` at 192; YAML header; ADR-0013 |
| 9 | ✅ | Byte-identical parquet/summary (reviewer reproduced) |
| 10 | ✅ | Flat baseline seed-invariant |
| 11 | ✅ | `soros-volatile` seed-variant |
| 12 | ✅ | README updated; `output/.gitkeep` only |
| 13 | ✅ | `328 passed`; CI green; artifact uploaded |

**13 of 13 ACs met. Epic 1: 8 of 8 stories done.**

### Learnings for Epic 2

- `run_scenario` is the single-run primitive the sweep runner wraps. It is deterministic,
  self-describing, and replaces its directory; sweeps can parallelise it safely with
  distinct `run_id`s.
- The chart conventions are now code; new chart types copy `plot_peg_trajectory`'s
  figure setup rather than inventing their own.
- Every lever in ADR-0010 options 2–3 (bigger attack, smaller pool) is an Epic 2 sweep axis.
- 2026-10-02: Senior review APPROVE; status set to done. ADR-0013 accepted with amendment; ADR-0014 accepted. Epic 1 complete.
