# Story 2.4: Aggregate Depth Fit and the 1992 Analogue Scenario

Status: in-progress

## Story

As a **researcher**,
I want the calibrated pool to stand for the aggregate USDC market, and a scenario parameterised from Black Wednesday in ratio terms,
so that the note can show one fitted parameter against one observation, and the model reproducing the first-generation reserve-exhaustion story.

## Acceptance Criteria

### Part A — aggregate depth fit (F-05)

1. `scripts/fit_depth.py` sweeps a linked axis `pool_depth` over `[1M, 2M, 5M, 10M, 20M, 50M, 100M, 200M, 500M]` on `scenarios/calibrated-baseline.yaml` (seed 42, calm vol, everything else fixed) and prints a table of `pool_depth, max_depeg_bps, terminated_by, defender_spent, steps_run`; it uses `run_sweep` and reads `sweep.parquet`, no bespoke loop
2. The fitted depth `D*` is the smallest grid value at which `max_depeg_bps >= -1300` (the March-2023 observed trough, Chainalysis $0.87 → −1300 bps); if the crossing falls between grid points, refine with a second pass of 5 points between them and take the one closest to −1300; the script prints `D*` and the achieved trough
3. `scenarios/calibrated-baseline.yaml` and `calibrated-stress.yaml` are updated to `D*` (both reserves); the header comment states `market_depth_multiple = D* / 1,000,000` and cites F-05; `docs/calibration/SOURCES.md` gains the `market_depth_multiple` row (status `assumption`, source "fitted to observed trough, this story", conversion shown) and the pool section's "single venue" note is updated to "single constant-product venue standing for aggregate depth"
4. With `D*`, `scripts/probe_boundary.py` runs attacker ratios `[0.5, 0.75, 1.0, 1.25, 1.5, 2.0]` × seeds `{count: 8}` (calm vol) and prints `p_reserves_exhausted`, `p_peg_recovered`, `p_max_steps` per ratio; Completion Notes state whether an ADR-0017-style boundary now exists at calibrated depth, and at what ratio

### Part B — the 1992 analogue

5. `scenarios/soros-1992.yaml`, built from `docs/BACKGROUND.md` § "Mapping 1992 to the simulator" with **ratios** from §5 "The cost": defense resources anchored to the **gross** intervention figure (£27bn, status `secondary` per BACKGROUND's verification list; `budget : reserves` split stated as an `assumption` with reasoning — suggested 50:50, since the BoE both bought sterling in the market and honoured ERM obligations), attacker capital anchored to Quantum's ~$10bn **plus** a multiple for the rest of the market (BACKGROUND §4: "Quantum was the most visible seller but not the only one"; choose a multiple, status `assumption`, such that `capital / (budget + reserves)` ≈ 1.2–1.5, and say why); pool depth = `D*` from Part A (the only shared parameter); fee, oracle and redemption spread as calibrated-baseline
6. Time scaling: one step is still 12 s; the scenario comment states one simulated "trading day" = 7,200 steps and that the attack runs over one such day (`start_step` 600 ≈ 2 h in, `pace` set so ~90% of capital is sold within the day); `max_steps` 14,400 (two days)
7. Environment: a scheduled negative shock at `start_step − 600` of **−1.0%** standing for the Schlesinger remarks (BACKGROUND §3, 15 September); calm volatility
8. Defender: `threshold_pct 1.0`, `spend_pace 0.2`, `spread_adjust_bps 200` (standing for the two rate rises, 10→12→15%; `assumption`, reasoning: the spread widening is the model's only "raise the cost of exit" lever), `max_spend` = budget
9. Redemption capacity: **not** throughput-bound — `capacity_per_step` set so the whole reserve can be paid out within the attack day (`reserves / 7200`), with the comment that 1992 FX settlement had no weekend-bank constraint
10. Run terminates **`reserves_exhausted`**; `max_depeg_bps`, `steps_run`, `defender_spent`, `redemption_paid_total` recorded in the scenario header and Completion Notes; if it does not exhaust, raise the attacker multiple (AC 5) until it does and record the multiple at which it flips — that multiple is itself a result
11. `scenarios/soros-1992-no-defense.yaml`: identical but `defender.budget` → 1 and `spread_adjust_bps` → 0; run; record the trough and how many steps faster the price falls; both scenarios charted with `plot_peg_trajectory`; PNG paths in Completion Notes (committed figures are 2.7)
12. A `Proposed` ADR recording `D*`, the 1992 split and multiple, and the boundary-probe answer; a FINDINGS-style write-up in Completion Notes if the probe or the 1992 run shows something not already in F-01–F-05
13. `pytest` and `ruff check .` pass; tests: both 1992 scenarios validate and run short; `fit_depth.py --dry-run` lists the grid without running; SOURCES.md status regex still passes

## Tasks / Subtasks

- [x] Depth fit (AC: 1, 2, 3)
  - [x] `scripts/fit_depth.py` (argparse; `--dry-run`; uses `SweepSpec` built in code, `run_sweep`, pandas)
  - [x] Run; refine; record `D*` and trough
  - [x] Update both calibrated YAMLs and SOURCES.md; re-run both and record new outcomes
  - [x] Commit separately: `story 2.4: fit aggregate depth D* to observed trough`

- [ ] Boundary probe (AC: 4)
  - [ ] `scripts/probe_boundary.py`; run; table in Completion Notes

- [ ] 1992 scenario (AC: 5–10)
  - [ ] `scenarios/soros-1992.yaml` with full header comment (every ratio → BACKGROUND section, status)
  - [ ] Run; adjust attacker multiple per AC 10 if needed; record

- [ ] Counterfactual and charts (AC: 11)
  - [ ] `scenarios/soros-1992-no-defense.yaml`; run both with charts; look at both PNGs and describe them

- [ ] ADR, tests, close out (AC: 12, 13)
  - [ ] Proposed ADR; `tests/test_1992_scenarios.py`; `tests/test_scripts.py` (dry-run)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.4: aggregate depth fit and 1992 analogue`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.3 (Status: done)**

- Sourced ratios against a single Curve pool's depth put the attacker at 179× depth and
  the pool at $0.003 (F-05). The fix is to let the pool stand for aggregate market depth,
  fitted to the observed trough. That is Part A, and it must land before Part B so the two
  scenarios share `D*`.
- Fit, don't tune: one parameter, one named observation, stated as `assumption`.
- The USDC scenario is throughput-bound on redemption (`reserves_exhausted` unreachable);
  that is historically right. The 1992 analogue is where exhaustion is the expected
  outcome, so its redemption capacity is *not* throughput-bound (AC 9).
- Stress volatility makes `peg_recovered` unreachable (F-04); both scenarios here use calm
  volatility. The stress question is parked until the `reference` option exists.
- Two of the dev manager's pre-filled figures were wrong; the builder's primary reads win.
  Same rule here: if BACKGROUND.md's figures conflict with a primary you read, use the
  primary and note it.

[Source: docs/stories/2-3-calibration-sources.md#Senior-Developer-Review, docs/FINDINGS.md F-04, F-05]

### Why fit depth to the trough and nothing else

The trough is the one March-2023 observation that is (a) widely reported, (b) a direct
function of attack size vs effective depth in a constant-product model, and (c) not
already used to set any other parameter. Fitting `D*` to it uses one degree of freedom
to absorb the single-venue simplification. Recovery timing, defender spend and
redemption volume stay as out-of-sample checks for 2.5.

Expect `D*` in the tens of millions of model units (i.e. a `market_depth_multiple` of
20–100). If it comes out above 200M, the attacker's `pace` (0.1 per step) is probably too
fast for a market that absorbs selling over hours, and the honest move is to note it and
pick the grid point closest to −1300 rather than extend the grid.

### 1992 ratios (from BACKGROUND.md; verify the status of each there)

| Quantity | Figure | Status in BACKGROUND | Use |
|---|---|---|---|
| Gross intervention | £27bn | secondary (FOI release to confirm) | budget + reserves |
| Net cost | £3.3bn | verified (Treasury FOI 2005) | check only: `defender_spent + paid` loss ≈ 12% of gross is a plausibility test, not a target |
| Quantum short | ~$10bn ≈ £5.7bn at ~1.75 | secondary (Mallaby) | attacker core |
| Rest of market | unsourced | assumption | multiple on Quantum |

Convert to model units with `s_1992 = D* / (effective sterling market depth)`. We have no
figure for 1992 sterling market depth, so **state the ratios directly in the YAML
comment** (`capital : budget : reserves : depth`) and derive the absolute numbers from
`D*`. The ratios are the claim; the absolutes are presentation.

### What the 1992 run should show

The BoE spent reserves through the day and the pound still broke the floor by evening.
In model terms: `reserves_exhausted` fires within ~7,200 steps of `start_step`, the
defender spends its full budget, the spread widening doesn't stop the selling, and the
no-defense counterfactual breaks faster and deeper. If the defended run *also* recovers,
the attacker multiple is too low for the first-generation story and AC 10 says raise it;
the multiple at which it flips is the model's statement of "how much bigger than Quantum
the market had to be."

### Charts

Both 1992 PNGs are produced by the existing `plot_peg_trajectory` and go in
`output/`; 2.7 commits them. Describe each in Completion Notes the same way 1.8 did.

### References

- [Source: docs/epics.md#Story-2.4]
- [Source: docs/FINDINGS.md] — F-03, F-04, F-05
- [Source: docs/adr/0018-calibration-judgment-calls.md] — amendment
- [Source: docs/BACKGROUND.md] — §3, §4, §5, mapping table, verification list
- [Source: docs/calibration/SOURCES.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-4-depth-fit-and-1992.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output; fit table, probe table, both 1992 runs' CLI lines)_

### Completion Notes List

_(include: D*, achieved trough, probe table and its answer, 1992 outcomes for both scenarios, chart descriptions, ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.3 review; Part A added per ADR-0018 amendment / F-05
