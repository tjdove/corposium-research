# Story 2.7: Threshold Surface and Oracle-Lag Sensitivity

Status: in-progress

## Story

As a **researcher**,
I want the two headline charts at calibrated scale with the buyer present,
so that the note can state at what attacker size, relative to what the peg's defenders can absorb, the peg stays broken — and whether oracle lag changes that.

## Acceptance Criteria

1. `summarize` gains `defender_bought_stable`, `holder_bought_stable`, `holder_pnl` (floats; `None` when the agent is absent); `mc.parquet` carries them; every existing run-vs-rerun determinism test still passes; `scenario_hash` of every scenario unchanged
2. `LinkedAxis` gains optional `scales: list[float]` (same length as `paths`, default all 1.0); each path is set to `value × scale`; existing sweep specs expand to identical cells (test on `sweeps/pool-depth-x-attacker.yaml`: same `index`, same per-cell `content_hash()` as before the change)
3. `sweeps/threshold-surface-mc.yaml`: base `scenarios/calibrated-stress.yaml`; linked axis `pool_depth` over `D* × {0.25, 0.5, 1, 2, 4}` setting `amm.reserve_stable`, `amm.reserve_reference` (scale 1) and `agents[type=holder].capital` (scale `C*/D* = 0.55`); axis `agents[type=attacker].capital` over `ratio × (budget + reserves)` for ratio `{0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5}` (= 179,454,391 × ratio, rounded); 16 seeds from 1000; `max_steps` 18000; header comment states every number's origin; if no cell has `p_stays_broken ≥ 0.9`, extend the ratio axis upward by 0.5 steps until one does and say so in Completion Notes
4. `plot_threshold_surface(sweep_dir) -> Path` writes `threshold_surface.png`: **left panel** heatmap of `p_stays_broken = 1 − p_peg_recovered` over pool depth (rows, labelled as multiples of D\* and in $ at `s`) × attacker capital (columns, labelled as ratio to `budget + reserves` and in $), contour at 0.5, each cell annotated with its Wilson half-width; **right panel** `p_stays_broken` against the **absorbed ratio** `capital / (defender_bought_stable + holder_bought_stable + redemption_paid_total)` for every cell, one marker style per depth, with a logistic fit through all points and its 0.5 crossing printed in the legend (the F-03 collapse test at calibrated scale)
5. `sweeps/oracle-lag-mc.yaml`: base `scenarios/calibrated-stress.yaml`; axes `oracle.heartbeat_steps {5, 25, 300, 1500, 6900}` × `oracle.deviation_threshold_pct {0, 0.1, 0.25, 1.0}`; 32 seeds from 1000; `max_steps` 18000; header states the calibrated cell is (6900, 0.25) and that 0 is zero-lag (ADR-0009)
6. `plot_oracle_sensitivity(sweep_dir) -> Path` writes `oracle_sensitivity.png`: two panels sharing a log-x heartbeat axis — `max_depeg_bps` mean with p05–p95 band, one line per threshold; and `p_stays_broken` with Wilson bars, one line per threshold; the calibrated cell marked
7. Both chart functions read only `mc.parquet` and the sweep manifest (ADR-0014 pattern); chart conventions per `charts.py` (10×6 per panel, footer with sweep name and base scenario hash)
8. Both sweeps run with `--mc`; both charts generated and looked at; `aggregate_mc` tables pasted in the Debug Log; `python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc --workers N` and the oracle one each reported with wall time
9. Completion Notes draft the note's headline sentence **from the actual surface**, in the form "At calibrated depth, an attack of ≥ X× the defenders' nominal resources leaves the peg broken through the 60-hour horizon with probability ≥ 0.5; across depths from 0.25× to 4× D\* the boundary sits at an absorbed ratio of Y ± Z", and a one-paragraph answer to "does oracle lag matter under deviation-triggered updates?"
10. A `Proposed` ADR: the `p_stays_broken` metric choice (why not `p_reserves_exhausted` at calibrated scale), the absorbed-ratio definition, `scales` on linked axes, and any finding from the collapse or the oracle sweep
11. `pytest` (chart tests on a tiny synthetic `mc.parquet` + manifest in `tmp_path`; summary field tests; `scales` tests) and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Summary fields (AC: 1)
  - [ ] `defender_bought_stable`, `holder_bought_stable`, `holder_pnl` in `summarize`; tests; mc columns
  - [ ] Commit separately: `story 2.7: summary absorbed-stable fields`
- [ ] Linked-axis scales (AC: 2)
  - [ ] `LinkedAxis.scales`; validator (length match, all > 0); `expand` applies; equivalence test on the existing spec
  - [ ] Commit separately: `story 2.7: linked axis scales`
- [ ] Threshold surface (AC: 3, 4, 8)
  - [ ] Sweep spec; run; `plot_threshold_surface`; synthetic-parquet test; look at the chart and describe it
- [ ] Oracle sensitivity (AC: 5, 6, 8)
  - [ ] Sweep spec; run; `plot_oracle_sensitivity`; test; look and describe
- [ ] Headline, ADR, close out (AC: 7, 9, 10, 11)
  - [ ] Headline sentence and oracle paragraph in Completion Notes; Proposed ADR
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.7: threshold surface and oracle sensitivity`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.6 (Status: done)**

- The holder is now part of the calibrated model. Every sweep runs with it present at
  `C*/D*` of the cell's depth — hence AC 2. Do not run the surface without it.
- A ruling's expectation is a prediction. If the surface or the oracle sweep contradicts
  the Dev Notes below, report it as the result.
- The F-03 price-adjusted ratio is an outcome, not a parameter: heatmap axes are nominal
  (depth, capital); the collapse plot is where the adjusted ratio appears.
- Scratch scripts whose numbers appear in the record go into the Debug Log in full.

[Source: docs/stories/2-6-holder-agent.md#Senior-Developer-Review, docs/FINDINGS.md F-08 confirmation, F-09]

### Why `p_stays_broken` and not `p_reserves_exhausted`

At calibrated scale the redemption channel pays 605.79 stable per step; in 18,000 steps
it can deliver 10.9M of the 138.1M reserves. `reserves_exhausted` is unreachable within
the horizon at any attacker size the sweep uses (F-06; the 2.5 and 2.6 probes found no
exhaustion). The failure mode at this scale is "the peg does not come back within the
horizon," which is what `terminated_by != peg_recovered` records. `p_peg_recovered` is
already in `mc.parquet`; `p_stays_broken` is its complement and needs no new aggregate
column — compute it in the chart. Say this plainly in the ADR and in the figure caption;
it is the F-06 finding made visible, and a reader who expects a "reserve exhaustion"
surface needs to be told why they are looking at this one instead.

### The absorbed ratio (AC 4 right panel)

F-03 at toy scale: `capital / (stable the defender bought + reserves/0.999)` separated
2,016 runs at a single threshold where the nominal ratio could not. At calibrated scale
three things absorb the attacker's stable: the defender's AMM buys, the holder's AMM buys,
and redemption (paid to whoever queued). The denominator is the sum of the three per
run, from the new summary fields plus `redemption_paid_total`. Expect the five depth
series to fall on one logistic if F-03 holds with the buyer present; if they fan out,
that is the result — report the per-depth 0.5 crossings instead.

### Expected shapes

- Surface: at D\* the 2.6 probe put the 50% point at nominal ratio ≈ 0.50 (budget +
  reserves denominator). Shallower rows should break at *higher* nominal ratios (F-03:
  cheaper defense), deeper rows at lower. If the whole 1.0–1.5 column is not ≥ 0.9, the
  extension rule in AC 3 applies.
- Oracle: with deviation triggering at 0.25%, the oracle updates whenever the reference
  moves a quarter percent, which under stress volatility (`0.0007561` per step) happens
  within a few steps, so heartbeat should barely matter at thresholds ≤ 0.25 and matter
  at 1.0. Threshold 0 is the zero-lag reference. If heartbeat has no effect anywhere, say
  so; "oracle lag does not matter under deviation-triggered updates at Chainlink's cadence"
  is a publishable sentence.

### Cost

Threshold surface: 40 cells × 16 seeds = 640 runs × ≤ 18,000 steps. Oracle: 20 cells ×
32 seeds = 640 runs. On Seoul with 8 workers expect a few minutes each; report real
times. If a run exceeds 15 minutes, stop and report before reducing seeds.

### References

- [Source: docs/epics.md#Story-2.7]
- [Source: docs/FINDINGS.md] — F-03, F-06 (+ refinements), F-08 confirmation, F-09
- [Source: docs/adr/0014-manifest-embeds-resolved-config.md] — charts read parquet + manifest
- [Source: docs/adr/0013-recovery-tolerance-outside-arb-band.md] — sweep guard (not triggered here)
- [Source: scripts/probe_boundary.py] — `resources`, `deliverable`, the ratio convention
- [Source: src/depeg_sim/experiments/mc.py] — `mc.parquet` columns

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-7-threshold-surface.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: both sweep runs with wall time, both aggregate tables, test and lint output)_

### Completion Notes List

_(include: the headline sentence from the surface; the collapse verdict with the 0.5 crossing(s); the oracle paragraph; chart descriptions in words; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.6 review
