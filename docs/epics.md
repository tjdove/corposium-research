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
| 2. Runner, calibration, validation | Oct 3–15 | Sweeps, Monte Carlo, calibrated parameters, USDC-2023 validation, headline threshold |
| 3. What the model asked for | Oct 6–20 | Fill-price fix, defense-policy chart, 1992 switch-sides test, budget vs attack, repo hardening; stretch OU reference, multi-tranche holder, LP agent |
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
runner, replace placeholder parameters with documented real-world values, reproduce the
shape of the USDC March-2023 depeg, and add a 1992-motivated scenario from
`docs/BACKGROUND.md`. End of epic: the headline threshold finding exists with confidence
bands, and every figure in the note can be regenerated by one command.

**Delivers:** Sweep runner with the recovery-metric fix, Monte Carlo, calibration doc
with sources, calibrated baseline, 1992 analogue scenario, USDC validation and overlay
chart, threshold surface, oracle-lag sensitivity, committed figures.

**Story Count:** 9 stories (expanded 2026-10-03; 2.6 added 2026-10-04 after the replay failed validation, F-08; 2.8 added 2026-10-04 after the surface measured the clock, F-11)

**Epic sequencing rationale:** 2.1 makes many-run experiments possible and fixes the one
metric Epic 1 left ambiguous. 2.2 adds uncertainty. 2.3 grounds the parameters. 2.4 is
the historical anchor (first-generation model, reserve exhaustion). 2.5 is the
validation against a real depeg. 2.6–2.8 are the headline charts (2.8 inserted after 2.7 showed the par criterion measures the clock). Each later story runs
on the output of the earlier ones.

---

### Story 2.1: Sweep Runner and Recovery Metrics

As a **researcher**,
I want to run a grid of scenarios varying any config path and aggregate the summaries,
So that one command produces the data behind a sensitivity chart.

**Acceptance Criteria:**
1. `summarize` replaces `time_to_recovery_steps` with `steps_to_first_band_entry` (same definition as before) and `steps_to_sustained_recovery` (= `steps_run − for_steps − step_of_max_depeg` when `terminated_by == "peg_recovered"`, else null) per ADR-0013; tests and the 1.8 determinism fixtures updated
2. Manifest round-trip test: `ScenarioConfig.model_validate(manifest["config"]).content_hash() == manifest["scenario_hash"]` (ADR-0014)
3. `experiments/sweep.py`: `SweepSpec` (base scenario path, `axes: dict[str, list]` keyed by dotted config path such as `amm.reserve_stable` or `agents[0].capital`, `seeds: list[int]`, `name`), loaded from YAML in `sweeps/`
4. `expand(spec) -> list[ScenarioConfig]` produces the full grid × seeds with `name = f"{spec.name}/{cell_index}"`, applying overrides through `model_copy(update=…)` on frozen models (helper `set_path(cfg, path, value)`), and rejects unknown paths with a clear error
5. `run_sweep(spec, output_dir, workers=N)` runs every cell through `run_scenario` using `multiprocessing.Pool` (spawn context), writes each run to `output/<sweep>/<cell>/`, then aggregates all `summary.json` rows plus the axis values into `output/<sweep>/sweep.parquet` and writes `output/<sweep>/manifest.json` (spec, cell count, package version, created_utc)
6. Determinism: `run_sweep` twice with `workers=1` and `workers=4` yields byte-identical `sweep.parquet` (sorted by cell index)
7. Guard: if any axis touches `amm.fee_bps` or an arbitrageur `min_profit_bps`, `expand` raises unless the spec also sets `termination.peg_recovered.tolerance` as an axis or a fixed override ≥ the resulting band (ADR-0013 trap); test
8. CLI: `python -m depeg_sim.sweep sweeps/<name>.yaml --workers 4 --output output/`
9. `sweeps/pool-depth-x-attacker.yaml`: pool depth {250k, 500k, 1M, 2M} × attacker capital {100k, 300k, 600k, 1.2M}, seed 42, flat environment → 16 cells; test runs a 2×2 subset
10. `pytest` and `ruff check .` pass; CI green

**Prerequisites:** Epic 1 complete

---

### Story 2.2: Monte Carlo over Seeds

As a **researcher**,
I want each sweep cell run across many seeds with volatility on,
So that every threshold claim carries a confidence band.

**Acceptance Criteria:**
1. `SweepSpec.seeds` may be `{"count": N, "start": s}`; expanded to `range(s, s+N)`
2. `experiments/mc.py`: `aggregate_mc(sweep.parquet) -> mc.parquet` grouping by all axis columns, computing for each numeric summary metric `mean, std, p05, p50, p95, n`, and for booleans (`reserves_exhausted`) the proportion and a Wilson 95% interval
3. `terminated_by` becomes three proportion columns (`p_reserves_exhausted, p_peg_recovered, p_max_steps`)
4. `sweeps/pool-depth-x-attacker-mc.yaml`: same grid as 2.1 with `volatility_per_step: 0.0005` and 32 seeds → 512 runs; a test runs a 2×2×4 subset
5. Runtime budget: the full 512-run sweep completes in under 10 minutes on 4 workers on Seoul (record the actual time in Completion Notes; if over, reduce `max_steps` for sweeps via an override and say so)
6. `pytest` and `ruff check .` pass; CI green

**Prerequisites:** Story 2.1

---

### Story 2.3: Calibration Sources

As a **researcher**,
I want every baseline parameter traced to a public source,
So that a reader can check where the numbers came from.

**Acceptance Criteria:**
1. `docs/calibration/SOURCES.md` with one section per parameter group, each giving: the value used, the source (URL + access date), the raw figure from the source, and the conversion to simulator units (e.g. annualised vol → per-12s-step log-return sd; daily redemption throughput → per-step capacity)
2. Pool depth: Curve 3pool and Uniswap v3 USDC/USDT TVL and effective depth near peg, with the note that a constant-product pool at depth D approximates a stableswap pool at depth kD for small moves (state the k used and why)
3. Oracle: Chainlink USDC/USD mainnet heartbeat and deviation threshold, converted to steps
4. Redemption: Circle's published redemption terms and observed daily burn volume in March 2023, converted to `capacity_per_step`
5. Attacker sizing: USDC March 2023 net outflows over the depeg window, and the 1992 Quantum position relative to BoE reserves (ratio, not absolute), as two anchors
6. `scenarios/calibrated-baseline.yaml` using those values, with a header comment pointing at SOURCES.md sections; it runs and terminates by something other than `max_steps`
7. Every figure in SOURCES.md marked **verified** (primary source read) or **secondary** (needs primary); nothing unmarked
8. `pytest` and `ruff check .` pass (scenario validates and runs in a test)

**Prerequisites:** Story 2.1

---

### Story 2.4: The 1992 Analogue Scenario

As a **researcher**,
I want a scenario parameterised from Black Wednesday in ratio terms,
So that the note can show the model reproducing the first-generation reserve-exhaustion story.

**Acceptance Criteria:**
1. `scenarios/soros-1992.yaml` built from `docs/BACKGROUND.md` §"Mapping 1992 to the simulator": attacker capital / defender resources ≈ Quantum $10bn vs the reserves the Treasury was willing to spend (use the gross-spend figure as the defense budget and the net-cost figure as a check, both cited to BACKGROUND.md with their verification status); a scheduled negative shock one "day" before the attack (Schlesinger remarks); defender policy with `spread_adjust_bps > 0` standing in for the rate rises; no arbitrageur latency advantage
2. Units: one step is still 12 s; the scenario comment states the time-scaling assumption (one simulated "trading day" = N steps) and why
3. Run terminates `reserves_exhausted`; `max_depeg_bps` and `steps_run` recorded in the scenario comment and Completion Notes
4. A variant `scenarios/soros-1992-no-defense.yaml` (defender budget → tiny) shows the counterfactual: how fast the price falls with no intervention
5. `plot_peg_trajectory` on both produces charts; both committed under `docs/figures/` by Story 2.7's script
6. `pytest` passes (both scenarios validate and run in tests with reduced `max_steps`)

**Prerequisites:** Story 2.3

---

### Story 2.5: USDC March-2023 Validation

As a **researcher**,
I want the model to reproduce the shape of a real depeg,
So that the note's claims rest on more than internal consistency.

**Acceptance Criteria:**
1. `data/usdc-2023-03.csv`: hourly USDC/USD reference price 2023-03-10 to 2023-03-14 from a public source (CoinGecko or Coinbase candles; source and retrieval command in `data/README.md`); committed
2. `scenarios/usdc-2023.yaml` with calibrated-baseline parameters, `environment` driven by that series (new `EnvironmentConfig.price_series_path`, read in `ReferencePrice.from_config`; one step per 12 s, series interpolated linearly), attacker modelled as the observed outflow pace, defender as Circle's actual behaviour (no AMM buying; redemptions honoured at par once banks reopened — a scheduled `spread` or `capacity` change at the Monday-morning step)
3. `plot_validation_overlay(run_dir)`: simulated AMM price vs observed price on one axis, with trough depth and time-to-recovery annotated for both; chart conventions apply
4. Quantitative check in Completion Notes and the note: simulated vs observed trough (observed ≈ $0.88), and the sign/timing of recovery relative to the SVB backstop announcement
5. `pytest` passes; the validation run is a test with the full series

**Prerequisites:** Story 2.3

---

### Story 2.6: Par-Expecting Buyer Agent

As a **researcher**,
I want an agent that buys the discounted stablecoin because it expects redemption at par,
So that the replay can reproduce the observed trough and the note can say what decided March 2023.

**Acceptance Criteria:**
1. `agents/holder.py`: `Holder(agent_id, capital, entry_discount_pct, pace, redeem_when_capacity: bool)` — holds `reference`; when AMM price < `1 − entry_discount_pct/100`, buys stable with `pace × reference_balance` per step; holds; if `redeem_when_capacity`, submits a `redeem` for its stable each step the redemption queue is shorter than one step's capacity (so it redeems once the channel reopens); rules `hold_wait`, `hold_buy`, `hold_redeem`, `hold_done`
2. `HolderConfig` in `config.py` (`type: "holder"`); added to the `AgentConfig` union; factory dispatch; existing hashes unchanged
3. Sized by back-solving on the replay: `scripts/fit_holder.py` sweeps `holder.capital` over a log grid with D\* fixed at 16,666,667 and picks the capital at which `max_depeg_bps` is closest to −1,373; `entry_discount_pct` and `pace` are assumptions (suggested 2% and 0.05; state why)
4. `scenarios/usdc-2023.yaml` gains the fitted holder; the replay re-run; `VALIDATION.md` updated with a before/after table and the fitted capital in dollars; the overlay regenerated
5. Calibrated-baseline and 1992 scenarios re-run with the holder present (same capital ratio to depth as the replay); outcomes recorded; the 1992 flip re-scanned
6. `Proposed` ADR: the holder's semantics, the fitted capital, and what changed in F-06/F-07 with the buyer present
7. `pytest` and `ruff check .` pass; holder unit tests mirror 1.7's per-agent pattern

**Prerequisites:** Story 2.5

---

### Story 2.7: Threshold Surface and Oracle-Lag Sensitivity

As a **researcher**,
I want the two headline charts at calibrated scale with the buyer present,
So that the note can state at what attacker size, relative to what the peg's defenders can absorb, the peg stays broken — and whether oracle lag changes that.

**Acceptance Criteria (summary; the story file is the contract, revised 2026-10-04 after 2.6):**
1. `summary.json` gains `defender_bought_stable`, `holder_bought_stable`, `holder_pnl`; `LinkedAxis` gains `scales` so a depth axis can carry the holder at `C*/D*`
2. `sweeps/threshold-surface-mc.yaml`: calibrated-**baseline** (calm, per F-04; revised 2026-10-04), depth `D* × {0.25…4}` × attacker capital at ratio `{0.3…1.5}` of `budget + reserves`, 16 seeds; `plot_threshold_surface`: heatmap of **`p_stays_broken = 1 − p_peg_recovered`** (reserve exhaustion is unreachable within the horizon at calibrated throughput, F-06) with 0.5 contour and Wilson annotations, plus the F-03 collapse panel against the absorbed ratio
3. `sweeps/oracle-lag-mc.yaml` (calibrated-stress; trough is the primary metric, F-04 floor drawn on the recovery panel): heartbeat `{5, 25, 300, 1500, 6900}` × deviation `{0, 0.1, 0.25, 1.0}%`, 32 seeds; `plot_oracle_sensitivity`: `max_depeg_bps` band and `p_stays_broken` vs heartbeat, one line per threshold
4. Both charts read only `mc.parquet` + manifest; the headline sentence drafted from the actual surface; Proposed ADR; tests on synthetic parquet; `pytest`, `ruff` pass

**Prerequisites:** Stories 2.2, 2.3, 2.6

---

### Story 2.8: Reference-Relative Recovery and the Budget × Depth Boundary

As a **researcher**,
I want the recovery criterion to be able to measure the venue against the market price rather than par,
So that the surface shows where the attack beats the defense (not where the reference wandered) and the note can test F-11's budget-vs-depth hypothesis.

**Acceptance Criteria (summary; the story file is the contract):**
1. `termination.peg_recovered.reference: par | oracle` (default `par`, all hashes unchanged), via `PegView.spot_price` and a `ReferenceView` Protocol — no protocol imports in the kernel
2. `sweeps/threshold-surface-ref-mc.yaml` (2.7's surface under `oracle`); chart heading carries the criterion
3. `sweeps/budget-x-depth-mc.yaml`: depth × defender budget at attacker ratio 1.0, 8 seeds; `plot_budget_depth` with the crossing budget vs depth on log–log
4. Headline sentence from the oracle-criterion surface; replay stays `par`; Proposed ADR; tests; `pytest`, `ruff`

**Prerequisites:** Story 2.7

---

### Story 2.9: Committed Figures, Time-to-Parity, and `make figures`

As a **reader**,
I want every chart in the note regenerable by one command and committed,
So that the README and the note can show figures without running code.

**Acceptance Criteria:**
1. `scripts/make_figures.py` writes `docs/figures/<name>.png` + `manifest.json` for: baseline peg trajectory, calibrated baseline, 1992 analogue (+ no-defense), USDC overlay, threshold surface (oracle criterion), **time-to-parity** (new chart, same sweep; separates price from clock, 2.8 review ruling 3), par surface (F-11 record), budget × depth, oracle sensitivity
2. `Makefile` targets `figures` (full) and `figures-quick` (reduced seeds, for CI)
3. Stale-figure guard keyed on source hashes in the manifest (no sweeps, no pixel comparison in CI); `figures-quick` is a 2-seed smoke test
4. README gains a "Results so far" section embedding two figures with one-sentence captions
5. `docs/figures/README.md` lists each figure, its scenario/sweep, and the command that regenerates it
6. The validation overlay's y-limits include both trough annotations (the 2.6 overlay clipped the observed-trough label; review ruling 4); the surface figure is the 2.8 oracle-criterion one

**Prerequisites:** Stories 2.4, 2.5, 2.6, 2.7, 2.8

---

**Epic 2 Complete:** Every number in the note is sourced, every chart is regenerable, and the headline threshold claim carries a confidence band.

---

## Epic 3: What the Model Asked For

**Expanded Goal:**

Epic 2 closed eight days early with eleven findings. Epic 3 was outlined before the model
had said anything; it is re-planned here from what the findings need (Epic 2 retro,
2026-10-05): fix the one artefact in figure 1, deliver the charter's defense-policy chart,
run the test of the note's thesis (do the believers have to switch sides for the 1992
analogue to break?), close F-11's open hypothesis, and harden the repo for readers.
Dates: **Oct 6–20**. Feature freeze **Oct 21** unchanged.

**Delivers:** defense-policy comparison chart (charter chart 5); the 1992 switch-sides
result; the budget-vs-attack result; a repo a stranger can run and audit.

**Story Count:** 5 core + 3 stretch (ordered; stretch only if core is done by Oct 17). Story files are drafted one at a time; 3.1 drafted 2026-10-05.

---

### Story 3.1: Holder Fill-Price Limit

As a **researcher**,
I want the holder to stop buying when its own fill would lift the venue price above its entry price,
So that figure 1's first 3.5 hours show the market, not a model artefact (ADR-0021 sawtooth).

**Acceptance Criteria (summary):**
1. `Holder` sizes each buy to `min(pace × reference, the amount that moves spot to entry_price)` (closed-form on constant product, like the arbitrageur); rule name unchanged; `HolderConfig` unchanged; hashes unchanged
2. `fit_holder.py` re-run under the amended AC 4 rule; new `C*` recorded in three units; replay re-run; overlay regenerated; VALIDATION.md before/after row; propagated scenarios re-run at the new `C*/D*`
3. The 2.6 overlay's ±310/−220 sawtooth is gone or stated as reduced with numbers; trough timing and depth reported against the ±2 h / observed targets
4. Proposed ADR; tests; `make figures` regenerated; `pytest`, `ruff`

**Prerequisites:** Story 2.9

---

### Story 3.2: Defender Policy Comparison

As a **researcher**,
I want four defender policies compared under the same attack,
So that the note can say which defense survives (charter chart 5).

**Acceptance Criteria (summary):**
1. `DefenderConfig` gains `restore_threshold_pct` (re-arm after recovery; default absent = current widen-once/restore-once) and `order: buy_first | spread_first`
2. `sweeps/policy-comparison-mc.yaml`: calibrated-baseline, oracle criterion, holder present; policies {early-aggressive (0.5%, pace 0.5), late-conservative (2%, pace 0.1), spread-only (no buys), no-defense} × attacker ratio {0.5, 0.7, 1.0}; 16 seeds
3. `plot_policy_comparison(sweep_dir)`: per policy, time-to-parity and defender spend at each ratio, with Wilson bars; `p_stays_broken` as a second panel
4. Completion Notes: which policy minimises time-to-parity per unit spent; whether spread-only ever recovers (F-07 dead zone); Proposed ADR; tests

**Prerequisites:** Story 3.1

---

### Story 3.3: Holder Sell Rule and the 1992 Switch-Sides Test

As a **researcher**,
I want the holder to be able to lose its belief and sell,
So that the note can test BACKGROUND §4's claim that Black Wednesday needed the convergence traders to turn.

**Acceptance Criteria (summary):**
1. `HolderConfig` gains `exit_discount_pct: float | None = None` (sell all stable on the AMM once spot < 1 − exit/100; rule `hold_exit`; one-way, never re-enters); hashes unchanged when absent
2. On `soros-1992` at 6×: sweep `exit_discount_pct ∈ {None, 5, 10, 20, 40}` × holder capital ∈ {C*, 5 C*, 25 C*} (the last ≈ the attacker), 8 seeds; record reserves-exhausted step, trough, holder PnL
3. Multiple re-scan 4.0–7.0 at the largest holder with and without an exit rule: does the flip move, and in which direction?
4. Completion Notes answer the question in one paragraph with numbers; FINDINGS candidate; Proposed ADR; tests

**Prerequisites:** Story 3.1

---

### Story 3.4: Budget Against Attack at a Deep Pool

As a **researcher**,
I want the price-defense boundary mapped against attack size at a pool too deep to crash,
So that F-11's withdrawn clause is replaced by a tested one.

**Acceptance Criteria (summary):**
1. `sweeps/budget-x-attack-mc.yaml`: 2× D\* fixed, oracle criterion, holder present; defender budget × {0.5, 1, 1.5, 2, 3} × attacker ratio {0.5, 0.8, 1.0, 1.5, 2.0}; 8 seeds
2. `plot_budget_attack(sweep_dir)`: heatmap of never-re-enters (price loss) with 0.5 contour, plus the crossing budget vs attack on log–log with slope
2b. `sweeps/pace-x-trigger-mc.yaml` (3.2 review ruling 3): D\*, ratio 1.0, oracle criterion; defender `spend_pace {0.05, 0.1, 0.2, 0.5}` × `threshold_pct {0.5, 1, 2, 4}` × attacker `pace {0.1, 0.02}`; 8 seeds; `plot_pace_trigger`: time-to-parity heatmaps per attacker pace; answers whether F-13 is pace, trigger, or pace relative to attacker pace
3. Completion Notes: is the crossing budget proportional to attack size, to what the attacker extracts, or to neither; one sentence for the note; Proposed ADR; tests

**Prerequisites:** Story 2.9

---

### Story 3.5: Test Hardening, Repo Polish, and the Pace-Ratio Sweep

As a **reader**,
I want to clone the repo and reproduce every figure without asking anyone,
So that the note's claims are auditable.

**Acceptance Criteria (summary):**
1. Coverage ≥ 85% on `protocol/` and `agents/`; property tests on AMM invariants and redemption accounting; termination edge cases (both criteria)
2. README: full quick start, scenario reference table (every YAML, one line each, with hash), sweep reference, `make` targets, figure index, FINDINGS pointer
3. `CONTRIBUTING.md` (story process, determinism rule, how to add a scenario); `docs/REPRODUCIBILITY.md` checklist (versions, hashes, commands, expected wall times on a named machine); `summarize` gains `arbitrageur_redeemed` (3.2 review ruling 5)
4. Dependency pins reviewed; `pip install -e .` on a clean 3.12 venv documented with timing
0. `sweeps/pace-ratio-mc.yaml` + `plot_pace_ratio` commit the 3.4 slow-attack probe (3.4 review ruling 3)
5. `docs/figures/manifest.json` gains `code_hash` (sha256 over `src/depeg_sim/**/*.py`); `figures-check` warns on a code-hash mismatch and fails on a source mismatch; `make figures` is on the freeze checklist (3.1 review ruling 4); Makefile prefers `.venv/bin/python` when present (2.9 review ruling 6)

**Prerequisites:** Stories 3.1–3.4

---

### Story 3.6 (stretch): Mean-Reverting Reference

Replace the calm random walk with an OU process calibrated from the calm USDC series' autocorrelation; re-run the par-criterion surface; report whether the D\* clock effect survives (F-04 root cause). Story file drafted 2026-10-06; `mean_reversion_per_step`, `scripts/fit_reversion.py`, `calibrated-baseline-ou.yaml`, `threshold-surface-ou-mc`, verdict on whether the oracle criterion was a workaround.

### Story 3.7 (stretch): Multi-Tranche Holder

`HolderConfig.tranches: list[{entry_discount_pct, share}]`; re-fit on the replay; report whether the F-09 cliff becomes a curve and the fit lands within 5% of −1,373. Story file drafted 2026-10-07: three fixed ladders, C* fitted per ladder, cliff test at C* × {0.8…1.2}, best ladder as `usdc-2023-tranches.yaml` (replay file untouched).

### Story 3.8 (stretch): LP Withdrawal Agent

Single `panic_threshold_pct`; pool depth becomes endogenous; re-run the calibrated baseline and the 1992 analogue. Story file drafted 2026-10-07: `AMM.remove_liquidity`, `LiquidityProvider(share, panic_threshold_pct, pace)`, `calibrated-baseline-lp.yaml`, `lp-flight-mc` sweep (threshold × share × attack), `pool_depth_at_trough`; the 1992 re-run is dropped from this story (the analogue's depth is already a fitted aggregate).

**Dropped:** Anvil/Foundry replay. A forked-chain execution check touches no finding and costs 2–3 days of plumbing; recorded in the charter decision log 2026-10-05.

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
