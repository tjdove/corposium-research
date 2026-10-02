# corposium-research — Epic Breakdown

**Author:** Claude (dev manager)
**Date:** 2026-10-02
**Project:** Soros/ERM Stablecoin Depeg Simulator
**Target:** Publishable research artifact by 2026-11-01 (see `CHARTER.md`)

---

## Overview

This document is the master build plan. Each epic expands into stories in `docs/stories/`,
one file per story, worked one at a time by Claude Code per `CLAUDE.md`.

**Epic sequencing principles:**

- Epic 1 produces a running kernel and one end-to-end scenario with a chart.
- Each later epic delivers something a reader of the research note would see.
- Stories are vertically sliced, sequentially ordered, no forward dependencies.
- Stories are AI-agent sized: completable in one 2–4 hour focused session.
- Acceptance criteria are commands and numbers, not descriptions.

**Epic map against the charter timeline:**

| Epic | Dates | Delivers |
|---|---|---|
| 1. Kernel + first scenario | Oct 2–6 | Running engine, three agents, one scenario, first chart |
| 2. Runner, calibration, validation | Oct 7–13 | Sweeps, Monte Carlo, calibrated parameters, USDC-2023 validation, headline threshold |
| 3. Defense policies + stretch | Oct 14–20 | Defender policy comparison; LP agent and Anvil replay if time allows |
| 4. Publication | Oct 22–31 | Research note, final charts, site page, one-pager, launch thread |

---

## Epic 1: Kernel and First Scenario

**Expanded Goal:**

Build the deterministic simulation kernel and one complete protocol world, then run the
first Soros-style scenario end to end. By the end of this epic a researcher can clone the
repo, run one command, and get a parquet timeseries, a summary JSON and a chart showing
peg deviation and defender reserves over time, reproducible byte-for-byte from a seed.

**Delivers:** Project foundation, scenario config, kernel (engine/clock/scheduler/context),
AMM, oracle + environment, redemption, three agents, end-to-end run with chart.

**Story Count:** 8 stories

---

### Story 1.1: Project Foundation Setup

As a **developer**,
I want the Python project configured with packaging, testing and linting,
So that every later story builds on one verified toolchain.

**Acceptance Criteria:**
1. `pyproject.toml` defines package `depeg_sim` under `src/`, Python ≥3.12, dependencies pydantic, pyyaml, numpy, pandas, pyarrow, matplotlib; dev extras pytest, pytest-cov, ruff
2. `pip install -e ".[dev]"` succeeds in a clean venv
3. Package layout exists: `src/depeg_sim/{kernel,protocol,agents,environment,experiments,analysis}/__init__.py`
4. `src/depeg_sim/cli.py` exposes `main(argv)`; `python run.py scenarios/soros-baseline.yaml` exits 0 and prints the scenario path
5. `tests/test_smoke.py` passes; `pytest` exits 0
6. `ruff check .` exits 0
7. `.gitignore` excludes `.venv`, `output/*`, `.env`, caches; `output/.gitkeep` kept
8. GitHub Actions workflow `.github/workflows/ci.yml` runs `pytest` and `ruff check .` on push and PR, Python 3.12

**Prerequisites:** None (first story)

---

### Story 1.2: Scenario Configuration Model

As a **researcher**,
I want scenarios defined in versioned YAML validated by Pydantic,
So that every run is fully described by one human-readable file.

**Acceptance Criteria:**
1. `kernel/config.py` defines Pydantic v2 models: `ScenarioConfig` (version, name, seed, steps, assets, amm, oracle, redemption, environment, agents, termination, metrics)
2. `steps` has `interval_seconds` (default 12) and `max_steps`
3. `termination` supports: `reserves_exhausted`, `peg_recovered_for_steps: N` (within `tolerance`), `max_steps`
4. `agents` is a list of typed entries discriminated by `type: attacker|arbitrageur|defender`, each with its own parameter model
5. `load_scenario(path) -> ScenarioConfig` parses YAML and validates; unknown fields rejected (`extra="forbid"`)
6. `scenarios/soros-baseline.yaml` validates against the model and contains placeholder values for every required section
7. Tests: valid file loads; missing required field raises; unknown field raises; unsupported `version` raises; agent discriminator works
8. `ScenarioConfig.content_hash()` returns a stable SHA-256 of the canonical JSON dump (used in run manifests later)

**Prerequisites:** Story 1.1

---

### Story 1.3: Simulation Kernel

As a **developer**,
I want the engine, clock, scheduler and run context implemented with no domain logic,
So that protocol modules and agents plug into a fixed, versioned step order.

**Acceptance Criteria:**
1. `kernel/scheduler.py` defines `PHASE_ORDER_VERSION = 1` and the ordered phases: `environment_update, oracle_update, state_observation, agent_decision, action_queue, execution, protocol_events, metric_update, persistence`
2. `kernel/clock.py`: `Clock(interval_seconds)` with `step_index`, `elapsed_seconds`, `tick()`
3. `kernel/context.py`: `RunContext` holds config, `numpy.random.Generator` seeded from config, clock, registries for protocol modules and agents, an event sink, a metrics sink
4. `kernel/engine.py`: `Engine(config).run() -> RunResult`; each step calls registered subsystems in phase order; stops on first satisfied termination condition; records which condition fired
5. Protocol modules and agents implement small protocols (`typing.Protocol`) declared in `kernel/interfaces.py`: `observe(ctx)`, `decide(ctx) -> list[Action]`, `execute(ctx, actions)`, `on_step_end(ctx)` as applicable
6. `kernel/checkpoint.py` writes a JSON snapshot of global, protocol and agent state every `checkpoint_every` steps and at termination
7. Determinism test: two `Engine` runs with identical config produce identical event lists and identical checkpoint JSON
8. Termination tests: each of the three conditions fires correctly with stub modules
9. Engine contains no references to prices, swaps, reserves or agent types

**Prerequisites:** Story 1.2

---

### Story 1.4: Constant-Product AMM Module

As a **researcher**,
I want a constant-product AMM with fees as a formal state machine,
So that pool price impact of attacker and arbitrageur trades is exact and testable.

**Acceptance Criteria:**
1. `protocol/amm.py`: `ConstantProductAMM(reserve_stable, reserve_reference, fee_bps)` with `quote(amount_in, side) -> Quote` and `swap(amount_in, side) -> SwapResult`
2. Invariant `x*y=k` holds after fee-adjusted swap (within 1e-12 relative)
3. `SwapResult` reports amount_out, execution_price, spot_price_before, spot_price_after, slippage, fee_paid
4. `spot_price()` returns reference-per-stable
5. Emits `swap_executed` events through the context event sink
6. Tests against hand-computed values: 1,000 in on a 1M/1M pool at 30 bps; zero-amount swap rejected; swap larger than reserves bounded; fee accrual accumulates in reserves
7. Property test over 1,000 seeded random swaps: k never decreases
8. Module registers with the kernel via the Story 1.3 interface and runs in the `execution` phase

**Prerequisites:** Story 1.3

---

### Story 1.5: Oracle and Environment Modules

As a **researcher**,
I want an external reference price with seeded shocks and an oracle that lags it by heartbeat and deviation rules,
So that oracle delay is a first-class, calibratable parameter.

**Acceptance Criteria:**
1. `environment/price_process.py`: `ReferencePrice` produces per-step reference price from config: base price, per-step volatility (log-normal, seeded from ctx RNG), scheduled shock events `[{step, pct}]`
2. `protocol/oracle.py`: `Oracle(heartbeat_steps, deviation_threshold_pct)` updates its published price when either `heartbeat_steps` elapsed since last update or reference deviates by ≥ threshold; otherwise stale
3. Oracle exposes `price`, `last_update_step`, `staleness_steps`
4. Emits `price_updated` and `oracle_updated` events
5. Tests: zero-volatility price stays flat; shock at step N applies exactly N; oracle with heartbeat 25 updates at 0, 25, 50 under no deviation; oracle updates immediately on 0.5% move with 0.5% threshold; determinism across two runs
6. Both run in their kernel phases (`environment_update`, `oracle_update`)

**Prerequisites:** Story 1.3

---

### Story 1.6: Redemption Module

As a **researcher**,
I want a redemption facility with finite reserves, a spread, per-step capacity and a queue,
So that the "price promise" and its capacity limit are explicit state.

**Acceptance Criteria:**
1. `protocol/redemption.py`: `RedemptionModule(reserves, spread_bps, capacity_per_step, peg_price=1.0)`
2. `request(agent_id, amount_stable)` queues; `process(ctx)` fulfils FIFO up to capacity, paying `amount * peg * (1 - spread)` from reserves, partial fills allowed
3. `reserves_exhausted` flag set the step reserves hit zero with queue non-empty
4. Exposes `reserves`, `queue_depth`, `fulfilled_total`, `queued_total`
5. Emits `redeem_requested`, `redeem_fulfilled`, `reserves_exhausted` events
6. Accounting tests: reserves decrease by exact paid amount; queue drains in order; capacity respected per step; exhaustion flag fires once; totals reconcile (`fulfilled + queued == requested`)
7. Runs in `execution` phase after AMM swaps; `protocol_events` phase sets exhaustion flag

**Prerequisites:** Story 1.4

---

### Story 1.7: Attacker, Arbitrageur and Defender Agents

As a **researcher**,
I want the three core agents with explicit, parameterised policies and decision traces,
So that every action in a run can be explained by a rule and a threshold.

**Acceptance Criteria:**
1. `agents/base.py`: `Agent` with `agent_id`, balances, `observe`, `decide -> list[Action]`, `record_decision(reason)`; decisions appended to `ctx.decision_trace` when `trace: true`
2. `agents/attacker.py`: parameters `capital`, `start_step`, `pace` (fraction of remaining capital per step), `stop_below_price`; sells stable into the AMM each step from `start_step` until capital or stop condition
3. `agents/arbitrageur.py`: parameters `capital`, `min_profit_bps`, `latency_steps`; when AMM price deviates from oracle price by more than fees + `min_profit_bps`, trades toward parity, or redeems if redemption is the better route; acts `latency_steps` after observing
4. `agents/defender.py`: parameters `threshold_pct`, `spend_pace`, `spread_adjust_bps`, `max_spend`; when AMM price falls more than `threshold_pct` below peg, buys stable in the AMM from a defense budget at `spend_pace` per step and optionally widens redemption spread
5. PnL tracked per agent: realized, unrealized at current AMM spot
6. Tests per agent with a stub AMM/oracle: attacker starts at `start_step` and respects pace; arbitrageur does nothing within band, trades outside it, honors latency; defender triggers at threshold and never exceeds `max_spend`
7. Agents register from config via the Story 1.2 discriminated union; `agent_decision` phase runs all agents in config order

**Prerequisites:** Stories 1.5, 1.6

---

### Story 1.8: First Scenario End to End

As a **researcher**,
I want `python run.py scenarios/soros-baseline.yaml` to produce a parquet timeseries, a summary JSON and a chart,
So that the project has its first reproducible result and first public post.

**Acceptance Criteria:**
1. `analysis/metrics.py` computes per-step: step, elapsed_seconds, reference_price, oracle_price, amm_price, peg_deviation, reserves, queue_depth, attacker_pnl, defender_spend
2. `analysis/summary.py` computes final: max_depeg, time_to_recovery_steps (or null), reserves_exhausted (bool), terminated_by, attacker_pnl, defender_spend, steps_run
3. `experiments/writer.py` writes `output/<run_id>/timeseries.parquet`, `summary.json`, `events.jsonl`, `decisions.jsonl` (if trace), `manifest.json` (scenario hash, seed, phase order version, package version, timestamp)
4. `analysis/charts.py`: `plot_peg_trajectory(run_dir)` produces `peg_trajectory.png` with two panels: peg deviation (%) and defender reserves over elapsed time; attacker start and defender interventions marked
5. `cli.main` wires config → engine → writer → chart; `--seed` overrides scenario seed
6. `scenarios/soros-baseline.yaml` filled with placeholder-but-plausible values: 1M/1M pool, 30 bps fee, oracle heartbeat 25 steps / 0.5%, reserves 500k, attacker 300k starting step 50, defender threshold 1%
7. Determinism test: running the baseline twice yields byte-identical `timeseries.parquet` and `summary.json`
8. Running with a different `--seed` yields a different `manifest.json` seed and (with nonzero volatility) different timeseries
9. README quick start reflects the actual command and output paths

**Prerequisites:** Story 1.7

---

**Epic 1 Complete:** A reader can clone, install, run one command and get a reproducible chart.
First build-in-public post goes out with that chart.

---

## Epic 2: Runner, Calibration and Validation

**Expanded Goal:**

Turn the single-run engine into a research instrument. Add the sweep and Monte Carlo
runner, replace placeholder parameters with documented real-world values, and reproduce
the shape of the USDC March-2023 depeg. End of epic: the headline threshold finding exists
with confidence bands.

**Delivers:** Grid sweeps, Monte Carlo over seeds, aggregated results, calibration doc with
sources, validation scenario and overlay chart, threshold surface chart.

**Story Count:** 6 stories (drafted at Epic 1 retro; outline below)

- **2.1 Sweep runner** — `experiments/sweep.py`, grid over any config path, one manifest per sweep, parallel via `multiprocessing`, results aggregated to `sweep.parquet`
- **2.2 Monte Carlo** — N seeds per grid point, per-cell mean/p5/p95 of summary metrics, `mc.parquet`
- **2.3 Calibration sources** — `docs/calibration/SOURCES.md`: Curve 3pool / Uniswap USDC-USDT depth, Chainlink USDC/USD heartbeat and deviation, historical attacker sizing; `scenarios/calibrated-baseline.yaml`
- **2.4 USDC March-2023 validation** — `scenarios/usdc-2023.yaml`, hourly reference series from public data, overlay chart simulated vs observed trough and recovery
- **2.5 Threshold surface** — `plot_threshold_surface`: reserves-exhausted probability over pool depth × attacker capital, from MC results
- **2.6 Oracle-lag sensitivity** — sweep heartbeat and deviation threshold, `plot_oracle_sensitivity`

---

## Epic 3: Defense Policies and Stretch

**Expanded Goal:**

Answer "which defense survives." Compare defender policies under matched attack, and if
Epic 2 closes by Oct 14, add the LP withdrawal agent (reflexive liquidity flight) and the
Anvil replay.

**Delivers:** Defense policy comparison chart; stretch items as time allows.

**Story Count:** 3 core + 2 stretch (drafted at Epic 2 retro)

- **3.1 Defender policy variants** — early/aggressive, late/conservative, spread-only, no-defense; `plot_policy_comparison`
- **3.2 Test hardening** — coverage ≥85% on protocol and agents; property tests; termination edge cases
- **3.3 Repo polish** — README full docs, scenario reference, CONTRIBUTING, reproducibility checklist
- **3.4 (stretch) LP withdrawal agent** — single `panic_threshold_pct`; pool depth becomes endogenous
- **3.5 (stretch) Anvil replay** — one scenario against a forked Uniswap V2 pair; simulated vs on-chain execution price chart

**Feature freeze: 2026-10-21.**

---

## Epic 4: Publication

**Expanded Goal:**

Ship the artifact. No new mechanics.

**Story Count:** 5 stories (drafted at Epic 3 retro)

- **4.1 Research note** — 2,000–3,500 words, `docs/NOTE.md`, every chart reproduced by a named scenario
- **4.2 Final charts** — consistent style, captions, source lines
- **4.3 Site page** — static results page on corposium site
- **4.4 One-pager** — media reuse
- **4.5 Launch thread** — drafted, reviewed, scheduled for Nov 1

---

## Story Guidelines Reference

**Story Format:**

```
**Story [EPIC.N]: [Story Title]**

As a [user type],
I want [goal/desire],
So that [benefit/value].

**Acceptance Criteria:**
1. [Specific, testable criterion — a command, a file, a number]
2. ...

**Prerequisites:** [Dependencies on previous stories, if any]
```

**Story Requirements:**

- **Vertical slices** — complete, testable functionality
- **Sequential ordering** — logical progression within epic
- **No forward dependencies** — only depend on previous work
- **AI-agent sized** — completable in a 2–4 hour focused session
- **Command-verifiable** — every AC can be checked by running something

**Story file lifecycle:** `drafted → ready-for-dev → in-progress → review → done` (or `blocked`).
Status lives on line 3 of the story file. The dev manager moves `drafted → ready-for-dev`
and `review → done`; the builder moves `ready-for-dev → in-progress → review`.

**For implementation:** the dev manager generates `docs/stories/N-M-slug.md` and
`N-M-slug.context.xml` from this file, then assigns the story to Claude Code.
