# Story 2.4: Aggregate Depth Fit and the 1992 Analogue Scenario

Status: done

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

- [x] Boundary probe (AC: 4)
  - [x] `scripts/probe_boundary.py`; run; table in Completion Notes

- [x] 1992 scenario (AC: 5–10)
  - [x] `scenarios/soros-1992.yaml` with full header comment (every ratio → BACKGROUND section, status)
  - [x] Run; adjust attacker multiple per AC 10 if needed; record

- [x] Counterfactual and charts (AC: 11)
  - [x] `scenarios/soros-1992-no-defense.yaml`; run both with charts; look at both PNGs and describe them

- [x] ADR, tests, close out (AC: 12, 13)
  - [x] Proposed ADR; `tests/test_1992_scenarios.py`; `tests/test_scripts.py` (dry-run)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.4: aggregate depth fit and 1992 analogue`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul

### Debug Log References

Final run, captured in one pass after all edits (the 1992 runs at the end are the AC 10/11 records):

```
$ pytest; echo exit=$?
435 passed in 4.89s
exit=0
$ ruff check .; echo exit=$?
All checks passed!
exit=0
$ ruff format --check .; echo exit=$?
78 files already formatted
exit=0
$ python scripts/fit_depth.py --workers 4; echo exit=$?
grid pass (target -1300 bps):
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
    1000000       -9,972.1 peg_recovered    16,119,549.5       7051
    2000000       -9,899.4 peg_recovered    26,071,985.8       7066
    5000000       -9,525.1 peg_recovered    41,346,974.0      15676
   10000000       -9,141.1     max_steps    41,346,974.0      18000
   20000000       -9,101.4     max_steps    41,346,974.0      18000
   50000000       -8,410.1     max_steps    41,346,974.0      18000
  100000000       -7,455.4     max_steps    41,346,974.0      18000
  200000000       -5,994.0     max_steps    41,346,974.0      18000
  500000000       -3,676.8     max_steps    41,346,974.0      18000

no grid depth reaches -1300 bps; extending by one decade

extension pass:
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
 1000000000       -2,213.9     max_steps    41,346,974.0      18000
 2000000000       -1,229.3     max_steps    41,346,974.0      18000
 5000000000         -525.4     max_steps    41,346,974.0      18000

refine pass between 1,000,000,000 and 2,000,000,000:
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
 1166666667       -1,953.5     max_steps    41,346,974.0      18000
 1333333333       -1,747.8     max_steps    41,346,974.0      18000
 1500000000       -1,581.1     max_steps    41,346,974.0      18000
 1666666667       -1,443.5     max_steps    41,346,974.0      18000
 1833333333       -1,327.8     max_steps    41,346,974.0      18000

D* = 1833333333 (trough -1327.8 bps)
exit=0
$ python scripts/probe_boundary.py --workers 8; echo exit=$?
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=6 seeds=8 (1000..1007) cells=48
 ratio  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.500  8                 0.000            0.000        1.000           -494.971       41,346,974.000
 0.750  8                 0.000            0.000        1.000           -926.820       41,346,974.000
 1.000  8                 0.000            0.000        1.000         -1,327.782       41,346,974.000
 1.250  8                 0.000            0.000        1.000         -1,702.659       41,346,974.000
 1.500  8                 0.000            0.000        1.000         -2,053.664       41,346,974.000
 2.000  8                 0.000            0.000        1.000         -2,691.806       41,346,974.000
exit=0
$ python scripts/probe_boundary.py --workers 8 --ratios 0.1,0.15,0.2,0.25,0.3,0.35,0.4 --output output/probe-low; echo exit=$?
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=7 seeds=8 (1000..1007) cells=56
 ratio  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.100  8                 0.000            1.000        0.000           -108.392       14,884,910.640
 0.150  8                 0.000            0.750        0.250           -117.012       20,177,323.312
 0.200  8                 0.000            0.625        0.375           -110.127       27,798,397.560
 0.250  8                 0.000            0.625        0.375           -129.151       35,797,477.090
 0.300  8                 0.000            0.000        1.000           -127.190       41,346,974.000
 0.350  8                 0.000            0.000        1.000           -221.422       41,346,974.000
 0.400  8                 0.000            0.000        1.000           -314.322       41,346,974.000
exit=0
$ python run.py scenarios/calibrated-baseline.yaml; echo exit=$?
depeg-sim: scenario=calibrated-baseline seed=42 hash=fae4d315a5a6
run: steps=18000 terminated_by=max_steps max_depeg_bps=-1327.8 reserves_exhausted=False
wrote: output/calibrated-baseline-42-fae4d315
exit=0
$ python run.py scenarios/calibrated-stress.yaml; echo exit=$?
depeg-sim: scenario=calibrated-stress seed=42 hash=2d8b5013683f
run: steps=18000 terminated_by=max_steps max_depeg_bps=-1327.9 reserves_exhausted=False
wrote: output/calibrated-stress-42-2d8b5013
exit=0
$ python run.py scenarios/soros-1992.yaml; echo exit=$?
depeg-sim: scenario=soros-1992 seed=42 hash=4d1e7c611e08
run: steps=9932 terminated_by=reserves_exhausted max_depeg_bps=-619.1 reserves_exhausted=True
wrote: output/soros-1992-42-4d1e7c61
exit=0
$ python run.py scenarios/soros-1992-no-defense.yaml; echo exit=$?
depeg-sim: scenario=soros-1992-no-defense seed=42 hash=1e70ca4f11b2
run: steps=7944 terminated_by=reserves_exhausted max_depeg_bps=-1269.5 reserves_exhausted=True
wrote: output/soros-1992-no-defense-42-1e70ca4f
exit=0
```

Ad-hoc checks behind the Completion Notes (inline python, output pasted as printed):

```
# ad-hoc checks (inline python, not committed): set_path on the scenario, run_scenario, print summary
# pace check on calibrated-baseline (D*):
pace=0.1 trough=-1327.8 step=145 final=-1217.6 term=max_steps spent=41,346,974
pace=0.01 trough=-1341.1 step=830 final=-1235.8 term=max_steps spent=41,346,974
pace=0.001 trough=-1308.2 step=5598 final=-1237.8 term=max_steps spent=41,346,974
# attacker-multiple scan on soros-1992 (capital = m x 42,625,746; everything else fixed):
m=4.0 ratio=0.847 term=max_steps steps=14400 trough=-205.5 spent=100,703,325 paid=47,490,109
m=4.5 ratio=0.952 term=max_steps steps=14400 trough=-266.4 spent=100,703,325 paid=68,023,239
m=4.6 ratio=0.974 term=max_steps steps=14400 trough=-284.1 spent=100,703,325 paid=71,834,830
m=4.7 ratio=0.995 term=max_steps steps=14400 trough=-303.1 spent=100,703,325 paid=76,113,299
m=4.8 ratio=1.016 term=max_steps steps=14400 trough=-323.2 spent=100,703,325 paid=80,059,960
m=4.9 ratio=1.037 term=max_steps steps=14400 trough=-344.5 spent=100,703,325 paid=84,490,711
m=5.0 ratio=1.058 term=max_steps steps=14400 trough=-366.5 spent=100,703,325 paid=88,609,803
m=5.1 ratio=1.079 term=max_steps steps=14400 trough=-389.4 paid=92,709,230 final=-189.1
m=5.2 ratio=1.101 term=max_steps steps=14400 trough=-412.9 paid=95,689,138 final=-199.3
m=5.3 ratio=1.122 term=reserves_exhausted steps=14105 trough=-437.1 paid=100,703,325 final=-184.6
m=5.4 ratio=1.143 term=reserves_exhausted steps=11836 trough=-461.8 paid=100,703,325 final=-192.0
m=5.5 ratio=1.164 term=reserves_exhausted steps=10195 trough=-487.2 spent=100,703,325 paid=100,703,325
m=6.0 ratio=1.270 term=reserves_exhausted steps=9932 trough=-619.1 spent=100,703,325 paid=100,703,325
m=5.0 max_steps=43200: max_steps 43200 90,669,409 -195.9
# 1992 runs, first step at or below each deviation (bps) and first redeem request:
soros-1992             first crossing {100: 715, 200: 2583, 300: 2934, 500: 3980, 600: 5124} first redeem 2585; last spread change step 2364; 57 spread_changed events; defender buys steps 716..2506 (171)
soros-1992-no-defense  first crossing {100: 715, 200: 860, 300: 1022, 500: 1391, 600: 1605} first redeem 743
```

### Completion Notes List

**Precondition.** The story file was not on `main`: it lived on the dev manager's unmerged
branch `origin/story/2-4-1992` (commit 73d5f81, the 2.3 review). I merged it into `main`
(clean, no conflicts) before starting; that merge is in this push.

**Part A: D\* = 1,833,333,333, achieved trough −1327.8 bps** (target −1300).
`market_depth_multiple` = 1833.33. The AC 2 rule was applied in code, no hand-picking:
- No point on the specified grid 1M…500M reaches −1300 (500M: −3676.8). The context
  constraint says "If the grid needs extending, say so and extend by one decade only":
  the script does so automatically (1B, 2B, 5B) and prints it. 2B (−1229.3) is the
  smallest passing depth; 1B misses; 5 refined points between them; the closest to −1300
  among the refined points and the bracket is 1,833,333,333 (−1327.8; 2B was 70.7 bps off).
- **Conflict flagged:** the Dev Notes say that for D\* > 200M one should "pick the grid
  point closest to −1300 rather than extend the grid." That would be 500M at −3676.8,
  2,377 bps from the observation. I followed the context constraint; ADR-0019 lists the
  alternative. If the dev manager prefers 500M, it is a two-line YAML change and two
  pinned hashes.
- D\* is far outside the expected 20–100 multiple: ≈ $430B per side at `s`, ≈ 10× USDC's
  supply. **It is not a physical depth.** See finding (a) below.
- Re-runs at D\*: calibrated-baseline `max_steps`, −1327.8 bps at step 145, final −1217.6,
  defender_spent 41,346,974 (all), redemption_paid 10,871,507; calibrated-stress
  `max_steps`, −1327.9. Neither recovers in 60 h (at single-venue depth both recovered).
  The stress header's "seed 42 is one of the 5/32" line was updated accordingly.

**Boundary probe at D\*: no ADR-0017-style boundary on the AC 4 ratios.**

| ratio | p_reserves_exhausted | p_peg_recovered | p_max_steps | trough p50 (bps) |
|---|---|---|---|---|
| 0.5 | 0 | 0 | 1 | −495 |
| 0.75 | 0 | 0 | 1 | −927 |
| 1.0 | 0 | 0 | 1 | −1328 |
| 1.25 | 0 | 0 | 1 | −1703 |
| 1.5 | 0 | 0 | 1 | −2054 |
| 2.0 | 0 | 0 | 1 | −2692 |

*Answer:* at calibrated depth, ratios 0.5–2.0 sit entirely on one side. The defender
spends its whole budget, reserves never exhaust (the channel delivers ≤ 7.9% of them in
60 h), and nothing recovers. **A boundary does exist, but at nominal ratio ≈ 0.25–0.30**
(extra probe, same script, `--ratios 0.1…0.4`: 0.25 recovers 5/8, 0.30 recovers 0/8).
That matches the prediction (budget + capacity × max_steps) / (budget + reserves) =
(41.35M + 10.90M) / 179.45M = 0.291. It is a `peg_recovered` ↔ `max_steps` boundary, not
`reserves_exhausted`. Ratio 1.0 is therefore not on the boundary: it is ≈ 3.4× past it.

**Part B: 1992 analogue.** Ratios capital : budget : reserves : depth =
1.270 : 0.500 : 0.500 : 9.103. Units: the same `s` as the USDC scenarios, GBP→USD 1.75,
depth D\*. No 1992 sterling-depth figure exists, so I assume, and state, that it equals
the fitted USDC aggregate depth in dollars. Statuses follow BACKGROUND: £27bn `secondary`,
Quantum ~$10bn `secondary`, split and multiple `assumption` (one-sentence reasons in the
header). I tried to read the Treasury FOI primary (BACKGROUND ref 13, margaretthatcher.org)
to verify £27bn/£3.3bn: HTTP 403. So no primary was read and no BACKGROUND figure was
overridden. The 1.75 FX rate is the story's, not verified: a higher pre-exit rate would
shrink defense in dollars and lower the flip multiple.

- **soros-1992 (multiple 6): `reserves_exhausted`, steps_run 9,932, max_depeg_bps −619.1
  (step 5,985), defender_spent 100,703,325, redemption_paid_total 100,703,325.** No AC 10
  adjustment was needed. **Flip multiple: 5.3** (ratio 1.122). 5.2 ends `max_steps` with
  95.7M of 100.7M paid. Exhaustion arrives 9,332 steps (31.1 h) after the attack starts,
  not "within ~7,200 steps" as the Dev Notes expected: redemption only opens once the
  defender stops (see finding c), and then drains at capacity (reserves / 7,200) for
  ≈ 7,000 steps.
- **soros-1992-no-defense: `reserves_exhausted`, steps_run 7,944 (1,988 steps / 6.6 h
  earlier), max_depeg_bps −1269.5 (step 5,697), twice as deep.** The price falls much
  faster: −200 bps at step 860 vs 2,583 (1,723 steps sooner), −500 bps at 1,391 vs 3,980
  (2,589 sooner). Redemption opens at step 743 vs 2,585.
- Net-cost plausibility (Dev Notes, check only): defender PnL at the last step is
  −3,164,317 (timeseries `defender_pnl`, marked at final spot 0.9627), i.e. 3.1% of its
  budget and 1.6% of budget + reserves, against the Treasury's £3.3bn / £27bn ≈ 12%. The
  model's defense is much cheaper than 1992's: its stable is marked at −373 bps, while
  sterling fell well over 10% after the exit (BACKGROUND §3). Attacker PnL −7,252,668.

**Charts** (not committed, 2.7):
- `output/soros-1992-42-4d1e7c61/peg_trajectory.png`. Flat at 0 bps for the 2 h before the
  attack. The −1% Schlesinger shock does not move the AMM; it moves only the oracle. From
  120 min a regular sawtooth between 0 and −100 bps: the attacker drags the price to the
  −1% trigger and the defender buys it back to par. The defender-buy ticks crowd together
  as each buy (20% of what remains) gets smaller, and the budget falls in a staircase to
  zero at ~475 min. Then the price slides smoothly to a **trough of −619 bps at ~1,200 min
  (20 h)**. Reserves are flat until ~517 min, then fall in a straight line (capacity-bound)
  to zero at ~1,986 min. The price is *recovering* (−373 bps) when they run out, because
  the attacker's geometric selling has thinned while redemption keeps pulling stable out.
  **Ends `reserves_exhausted`.**
- `output/soros-1992-no-defense-42-1e70ca4f/peg_trajectory.png`. Same flat start; one
  orange tick-cluster at ~150 min (the 1-unit budget buying once); no sawtooth. The price
  falls immediately and convexly to a **trough of −1,270 bps at ~1,140 min**, then edges
  up to −1,178 at the end. Reserves start draining at ~149 min and fall linearly to zero at
  ~1,589 min. **Ends `reserves_exhausted`**, about 400 min (6.6 h) earlier than defended.

**ADR:** [ADR-0019](../adr/0019-fitted-depth-and-1992-analogue.md) (Proposed): D\*, the
1992 split and multiple, the flip multiple, and the probe answer.

**Findings not already in F-01–F-05** (for the dev manager to accept or reject):

(a) *At calibrated scale the trough is set by the conservation residual, not by the first
dump or the pace.* Trough at D\* for pace 0.1 / 0.01 / 0.001: −1327.8 / −1341.1 / −1308.2;
only its timing moves (step 145 / 830 / 5,598). With the sinks throughput-bound, ~127M of
the 179M attack has nowhere to go but the pool. So D\* (a) is ~10× the first-dump estimate
the ADR-0018 amendment described and (b) absorbs the ratio-1.0 attacker size (≈ $42B
selling vs ≈ $4B observed net burn). Pace becomes a separate lever for trough *timing*
(observed: hours, model at pace 0.1: 19 min). Refines F-05.

(b) *With throughput-bound redemption the outcome boundary moves from capital ≈ budget +
reserves to capital ≈ budget + capacity × horizon, and becomes recover-vs-stay-broken.*
At calibrated parameters that is nominal ratio ≈ 0.29 (measured between 0.25 and 0.30).
This extends F-02/F-03: the conservation law holds with "reserves" replaced by "reserves
the channel can deliver before the clock runs out". It is the March-2023 shape: reserves
ample, peg still broken, because the banks were shut.

(c) *In the 1992 run the two defenses are spent in sequence, not together, and the spread
lever makes a dead zone.* While the defender holds the price above −100 bps, the
arbitrageur never buys (its trigger is the oracle at 0.99 minus the band, ≈ −121 bps vs
peg), so no redemption happens. Once the spread is widened, redemption opens only below
−200 bps. The reserve therefore starts draining only after the market defense is gone.
Below the flip the run stalls between −100 and −200 bps with reserves left: at 5.0× over
six days, 90.7M of 100.7M paid, price −196 bps, neither exhausting nor recovering. That is
why the flip is at ratio 1.12, not ≈ 1.0. The defender also flaps the spread on every
sawtooth (57 changes), because it has no hysteresis. For the note: raising the cost of exit
doesn't stop the run; it delays when the reserve is touched and leaves part of it stranded.

### File List

**Created:**
- `scripts/fit_depth.py`
- `scripts/probe_boundary.py`
- `scenarios/soros-1992.yaml`
- `scenarios/soros-1992-no-defense.yaml`
- `tests/test_scripts.py`
- `tests/test_1992_scenarios.py`
- `docs/adr/0019-fitted-depth-and-1992-analogue.md`

**Modified:**
- `scenarios/calibrated-baseline.yaml`, `scenarios/calibrated-stress.yaml` (D\*, header)
- `docs/calibration/SOURCES.md` (`market_depth_multiple` row, pool rows, pool note, ratios)
- `tests/test_calibrated_scenarios.py` (pinned hashes; D\* and SOURCES row tests)
- `docs/stories/2-4-depth-fit-and-1992.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.3 review; Part A added per ADR-0018 amendment / F-05
- 2026-10-04: Implemented by Claude Code (Opus 5.5). Part A committed separately (D* = 1,833,333,333, trough −1327.8 bps, grid extended one decade); boundary probe; 1992 analogue and counterfactual (both reserves_exhausted; flip multiple 5.3); ADR-0019 Proposed. Status → review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-04
**Outcome:** **APPROVE** ✅ — with ADR-0019 §1 superseded

### Summary

435 passed, ruff clean, CI run 37225011935 green. Every AC met as written, the builder
resolved a Dev-Notes-vs-constraint conflict correctly (constraint is stricter), and the
analysis in ADR-0019 is the reason the review can fix the real problem: **D\* ≈ $430B per
side is the model telling us the attacker is ten times too large**, and the builder's
decision 2 proves it (pace doesn't move the trough; attacker size does). My ADR-0018
attacker ratio was the wrong input. Reversed; 2.5 re-anchors the attacker to the observed
episode flow and re-fits depth.

### Rulings

- **ADR-0019 §1 (D\* = 1.83B): superseded.** Re-fit in 2.5 with the episode-sized attacker.
- **§2 (D\* absorbs attacker size, not pace): accepted** and is the basis for the reversal.
- **§3 (boundary at 0.29; deliverable reserves): accepted → F-06.** The formula generalises
  ADR-0016/0017 to throughput-bound redemption; the three-way outcome is March 2023.
- **§4 (1992 at 5.3× Quantum; spread dead zone): accepted provisionally → F-07.** Re-run
  after the re-fit.
- **Builder merged the dev manager's unmerged story branch into main.** Correct: the story
  file must be on `main` before work starts; the PR had been approved in chat. Going
  forward the dev manager confirms the merge before issuing a prompt.

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1–2 | ✅ | `fit_depth.py`; rule applied mechanically; grid extended one decade per constraint |
| 3 | ✅ | YAMLs and SOURCES.md updated (to be revised in 2.5) |
| 4 | ✅ | `probe_boundary.py`; 0.5–2.0 all `max_steps`; extra 0.1–0.4 probe found 0.25–0.30 |
| 5–9 | ✅ | `soros-1992.yaml` with statuses per line; 50:50 split; 6× Quantum; shock; spread 200; capacity unbound |
| 10 | ✅ | `reserves_exhausted` at 9,932; flip 5.3× recorded |
| 11 | ✅ | `soros-1992-no-defense.yaml`; both charts described |
| 12 | ✅ | ADR-0019; three findings written up |
| 13 | ✅ | `435 passed`; CI green |

**13 of 13 ACs met.**

### Key Findings

No High or Medium issues.

**Low / advisory:**
- **[LOW-1]** Defender spread chatter (57 `spread_changed` in soros-1992): add
  `restore_threshold_pct` in Epic 3.
- **[LOW-2]** The £27bn Treasury primary returned 403; status stays `secondary`. Tim may
  be able to retrieve it from the Thatcher Foundation archive link in BACKGROUND.md.

### Learnings for Story 2.5

- Anchor the attacker to the episode; fit depth second. Report D\* as a dollar figure and
  as a multiple of the Curve leg so a reader can judge it.
- Pace is free to fit trough *timing* once depth is set.
- Recovery in the calibrated scenario needs the outside backstop; 2.5 models it as a
  scheduled capacity change at the Monday-morning step.
- 2026-10-04: Senior review APPROVE; status set to done. ADR-0019 §1 superseded (attacker re-anchored, D* re-fit in 2.5); F-06, F-07 and an F-05 correction added.
