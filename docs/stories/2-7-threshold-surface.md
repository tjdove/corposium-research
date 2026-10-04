# Story 2.7: Threshold Surface and Oracle-Lag Sensitivity

Status: review

## Story

As a **researcher**,
I want the two headline charts at calibrated scale with the buyer present,
so that the note can state at what attacker size, relative to what the peg's defenders can absorb, the peg stays broken — and whether oracle lag changes that.

## Acceptance Criteria

1. `summarize` gains `defender_bought_stable`, `holder_bought_stable`, `holder_pnl` (floats; `None` when the agent is absent); `mc.parquet` carries them; every existing run-vs-rerun determinism test still passes; `scenario_hash` of every scenario unchanged
2. `LinkedAxis` gains optional `scales: list[float]` (same length as `paths`, default all 1.0); each path is set to `value × scale`; existing sweep specs expand to identical cells (test on `sweeps/pool-depth-x-attacker.yaml`: same `index`, same per-cell `content_hash()` as before the change)
3. `sweeps/threshold-surface-mc.yaml`: base **`scenarios/calibrated-baseline.yaml`** (calm volatility, per F-04; amended 2026-10-04, see Rulings); linked axis `pool_depth` over `D* × {0.25, 0.5, 1, 2, 4}` setting `amm.reserve_stable`, `amm.reserve_reference` (scale 1) and `agents[type=holder].capital` (scale `C*/D* = 0.55`); axis `agents[type=attacker].capital` over `ratio × (budget + reserves)` for ratio `{0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5}` (= 179,454,391 × ratio, rounded); 16 seeds from 1000; `max_steps` 18000; header comment states every number's origin; if no cell has `p_stays_broken ≥ 0.9`, extend the ratio axis upward by 0.5 steps until one does and say so in Completion Notes
4. `plot_threshold_surface(sweep_dir) -> Path` writes `threshold_surface.png`: **left panel** heatmap of `p_stays_broken = 1 − p_peg_recovered` over pool depth (rows, labelled as multiples of D\* and in $ at `s`) × attacker capital (columns, labelled as ratio to `budget + reserves` and in $), contour at 0.5, each cell annotated with its Wilson half-width; **right panel** `p_stays_broken` against the **absorbed ratio** `capital / (defender_bought_stable + holder_bought_stable + redemption_paid_total)` for every cell, one marker style per depth, with a logistic fit through all points and its 0.5 crossing printed in the legend (the F-03 collapse test at calibrated scale)
5. `sweeps/oracle-lag-mc.yaml`: base `scenarios/calibrated-stress.yaml` (stress volatility is the point: on a calm reference the oracle has nothing to lag behind; header says so and names the F-04 floor); axes `oracle.heartbeat_steps {5, 25, 300, 1500, 6900}` × `oracle.deviation_threshold_pct {0, 0.1, 0.25, 1.0}`; 32 seeds from 1000; `max_steps` 18000; header states the calibrated cell is (6900, 0.25) and that 0 is zero-lag (ADR-0009)
6. `plot_oracle_sensitivity(sweep_dir) -> Path` writes `oracle_sensitivity.png`: two panels sharing a log-x heartbeat axis — `max_depeg_bps` mean with p05–p95 band, one line per threshold; and `p_stays_broken` with Wilson bars, one line per threshold, with the F-04 floor drawn as a horizontal reference (the `p_stays_broken` of the base scenario's own attack at ratio 0.064, from `probe_boundary.py`, stated in the caption as "under stress volatility most seeds never re-enter the band regardless of the attack"); the calibrated cell marked; **the trough panel is the primary result of this chart**
7. Both chart functions read only `mc.parquet` and the sweep manifest (ADR-0014 pattern); chart conventions per `charts.py` (10×6 per panel, footer with sweep name and base scenario hash)
8. Both sweeps run with `--mc`; both charts generated and looked at; `aggregate_mc` tables pasted in the Debug Log; `python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc --workers N` and the oracle one each reported with wall time
9. Completion Notes draft the note's headline sentence **from the actual surface**, in the form "At calibrated depth and calm volatility, an attack of ≥ X× the defenders' nominal resources leaves the peg broken through the 60-hour horizon with probability ≥ 0.5; across depths from 0.25× to 4× D\* the boundary sits at an absorbed ratio of Y ± Z", and a one-paragraph answer to "does oracle lag matter under deviation-triggered updates?"
10. A `Proposed` ADR: the `p_stays_broken` metric choice (why not `p_reserves_exhausted` at calibrated scale), the absorbed-ratio definition, `scales` on linked axes, and any finding from the collapse or the oracle sweep
11. `pytest` (chart tests on a tiny synthetic `mc.parquet` + manifest in `tmp_path`; summary field tests; `scales` tests) and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Summary fields (AC: 1)
  - [x] `defender_bought_stable`, `holder_bought_stable`, `holder_pnl` in `summarize`; tests; mc columns
  - [x] Commit separately: `story 2.7: summary absorbed-stable fields` (bca5025)
- [x] Linked-axis scales (AC: 2)
  - [x] `LinkedAxis.scales`; validator (length match, all > 0); `expand` applies; equivalence test on the existing spec
  - [x] Commit separately: `story 2.7: linked axis scales` (d41c164)
- [x] Threshold surface (AC: 3, 4, 8) (blocked on the stress base, unblocked by Rulings 1)
  - [x] Sweep spec (base `calibrated-baseline` per amended AC 3); run
  - [x] `plot_threshold_surface`; synthetic-parquet test; look at the chart and describe it
- [x] Oracle sensitivity (AC: 5, 6, 8)
  - [x] Sweep spec; run; `plot_oracle_sensitivity`; test; look and describe
- [x] Headline, ADR, close out (AC: 7, 9, 10, 11)
  - [x] Headline sentence and oracle paragraph in Completion Notes; Proposed ADR (0022)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.7: threshold surface and oracle sensitivity`, push to `main`

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

### Base scenarios (amended 2026-10-04)

The surface runs on the **calm** calibrated baseline. F-04 showed that under realised
stress volatility most seeds never re-enter the ±31 bps band whatever the attack, so on
`calibrated-stress` `p_stays_broken` has a floor near 0.69 and no 0.5 contour exists. The
original AC 3 contradicted F-04 (dev-manager error, L-2). The note states the calm-volatility
limitation next to the surface, and the `peg_recovered.reference` option that would lift
it is Epic 3 work.

The oracle sweep runs on **stress**, because oracle lag only matters when the reference
moves. Its primary metric is `max_depeg_bps`; its `p_stays_broken` panel carries the F-04
floor and says so.

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

## Blockers

**The surface's base scenario (`calibrated-stress`) makes `p_stays_broken` measure F-04,
not the attack. The story contradicts F-04, and AC 9's headline sentence cannot be
drafted honestly from this surface.**

1. **The contradiction.** AC 3 (and epics.md §2.7) set the base to
   `scenarios/calibrated-stress.yaml`. FINDINGS F-04, "What it changed", says: *"Until
   then [a `peg_recovered.reference` option], headline sweeps use calm volatility and the
   note states the limitation."* That option does not exist yet. The Dev Notes' expected
   shape ("at D\* the 2.6 probe put the 50% point at nominal ratio ≈ 0.50") comes from the
   2.6 probe, which ran on `calibrated-baseline` (calm), not on stress.

2. **What the specified sweep shows** (run exactly as AC 3 specifies, 640 runs, 2m45s on
   10 workers; output in the Debug Log). `p_stays_broken` is **≥ 0.6875 in all 40 cells**,
   including ratio 0.3 at every depth. 11 of the 16 seeds (1001, 1004–1006, 1008–1011,
   1013–1015) **never recover in any of the 40 cells**, whatever the attack or the depth.
   So the floor is exactly 11/16 = 0.6875, and the seed's reference path decides it. The
   median final deviation in most shallow cells is **+215 bps, above peg**: the pool
   tracks a reference that has drifted. The 31 bps / 6,900-step criterion against par is
   the thing being failed. A small attack confirms the floor: at the base file's own
   attacker (ratio 0.064) `scripts/probe_boundary.py` gives `p_peg_recovered` 0.25.
   Consequences per AC:
   - AC 3's extension rule is not triggered (cells ≥ 0.9 exist), but the 0.5 contour
     does not exist inside the grid. Extending the axis cannot fix that, because the
     problem is at the low end.
   - AC 4 right panel: the logistic's 0.5 crossing would be an extrapolation below
     every observed point (the absorbed ratio spans 0.84–1.14 while p ∈ [0.69, 1]).
   - AC 9: "an attack of ≥ X× … leaves the peg broken with probability ≥ 0.5" is true
     for every X in the grid and for X = 0.064. Any X I write would be F-04, not the
     attack's threshold.

3. **Diagnostic, not a deliverable** (scratchpad only, not committed): the identical
   grid with `base: scenarios/calibrated-baseline.yaml` (the only difference between the
   two files is `volatility_per_step` and `name`; 640 runs, 2m09s). It gives the surface
   the story expects. At D\* the 0.5 crossing is between ratio 0.5 (0.375) and 0.6
   (0.5625), consistent with the 2.6 probe's ≈ 0.50. Shallower rows break later (0.25×D\*
   never reaches 0.5 by 1.5; 0.5×D\* crosses at ≈ 1.0), as F-03 predicts. The absorbed
   ratio at the transition is ≈ 0.96–1.0 in every row, which looks like the F-03
   collapse. `p_reserves_exhausted` = 0 everywhere. Tables are in the Debug Log.

**Options for the dev manager** (I have not chosen; each changes the spec):

- **(a)** Surface on `calibrated-baseline` (calm), per F-04's rule. The oracle sweep
  stays on `calibrated-stress`, where stress volatility is the point (Dev Notes: the
  deviation trigger fires within a few steps). Its `max_depeg_bps` panel is unaffected;
  its `p_stays_broken` panel would carry the same F-04 floor, and the caption should say
  so. Smallest change: one line of AC 3.
- **(b)** Keep stress and report the floor as the result. AC 9's headline form would
  have to change, e.g. to "the attack raises p_stays_broken from the volatility floor
  0.69 to 1.0 at ratio ≥ X".
- **(c)** Build `peg_recovered.reference: peg | oracle` first (scheduled in the ADR-0018
  amendment). This touches termination code, which may be kernel scope, and it is not in
  this story.

The oracle sweep (AC 5) has the same base and the same floor in its `p_stays_broken`
panel. I have not run it. Whether its base also changes is part of the ruling.

**State left behind.** AC 1 and AC 2 are done and committed separately (bca5025,
d41c164). Committed with this blocker: `sweeps/threshold-surface-mc.yaml` exactly as AC 3
specifies, and the sweep manifest now carrying `base_config` (the resolved base scenario,
ADR-0014 pattern), so the charts can read `budget + reserves` from the manifest alone.
Charts, the oracle sweep, the ADR and the close-out are not started.
`pytest` and `ruff check .` pass at this commit (Debug Log).

## Rulings

**2026-10-04 (dev manager), on the Blockers above.**

1. **Option (a).** Surface base → `scenarios/calibrated-baseline.yaml`. AC 3 amended. The
   contradiction with F-04 was mine. Re-run the surface through the spec (not from the
   scratch diagnostic) so `mc.parquet` and the manifest exist; the diagnostic tables stay
   in the Debug Log as the record of why the base changed. The ADR and the figure caption
   both state "calm volatility" and cite F-04.
2. **Oracle sweep stays on stress.** AC 5 and AC 6 amended: trough panel is primary; the
   `p_stays_broken` panel draws the F-04 floor (from the base scenario's own attack via
   `probe_boundary.py`, one extra short run, reported) and the caption names it. If the
   trough does not move with heartbeat at thresholds ≤ 0.25%, that is the oracle
   paragraph.
3. **Option (c) → Epic 3.** `peg_recovered.reference: peg | oracle` is scheduled there
   (already in FINDINGS open questions). Not this story.
4. **`base_config` in the sweep manifest → accepted.** Consistent with ADR-0014; mention
   it in the ADR.
5. **The specified-stress surface result is itself a finding refinement (F-04).** Record
   in Completion Notes: 11 of 16 seeds never re-enter the band in any of 40 cells; median
   final deviation +215 bps *above* peg. The dev manager will add it to FINDINGS at review.
   Do not make a chart of it.

Resume at the Threshold surface task with the amended base. Everything else as written.

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-7-threshold-surface.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

#### Part 1: the stress-base surface (before the Rulings; record of why the base changed)

**Probe on the stress base before the sweep** (`--output` was the session scratchpad):

```
$ time python scripts/probe_boundary.py --scenario scenarios/calibrated-stress.yaml --ratios 0.0643,0.3 --seeds 16 --workers 10 --output <scratch>/probe
probe_boundary: scenario=scenarios/calibrated-stress.yaml budget+reserves=179,454,391 ratios=2 seeds=16 (1000..1015) cells=32
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.064              0.221 16                 0.000            0.250        0.750         -1,253.027        5,989,768.596
 0.300              1.030 16                 0.000            0.312        0.688         -4,286.803       31,858,781.944

real	0m6.874s
```

**Threshold-surface sweep as specified (AC 3).** First run's wall time was lost
(`/usr/bin/time` and `bc` are absent). Re-run with bash `time`, `mc.parquet`
byte-compared to the first run:

```
$ time python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc --workers 10; echo exit=$?; cmp output/threshold-surface-mc/mc.parquet <scratch>/mc_run1.parquet && echo mc-identical
sweep: threshold-surface-mc cells=640 workers=10
wrote: output/threshold-surface-mc/sweep.parquet
mc: threshold-surface-mc grid_points=40 seeds=16 runs=640
wrote: output/threshold-surface-mc/mc.parquet

real	2m45.328s
user	26m55.808s
sys	0m9.181s
exit=0
mc-identical
```

Tables from `mc.parquet`. Rows are depth / D\* and columns are capital / 179,454,391.
Script (inline, run from the repo root):

```python
import pandas as pd
mc=pd.read_parquet('output/threshold-surface-mc/mc.parquet')
A='agents[type=attacker].capital'
mc['ratio']=(mc[A]/179454391).round(2)
mc['xD']=(mc.pool_depth/16666667).round(2)
mc['p_broken']=1-mc.p_peg_recovered
print(mc.pivot(index='xD',columns='ratio',values='p_broken').to_string())
print(mc.pivot(index='xD',columns='ratio',values='p_reserves_exhausted').to_string())
mc['absorbed']=mc.defender_bought_stable_mean+mc.holder_bought_stable_mean+mc.redemption_paid_total_mean
mc['abs_ratio']=mc[A]/mc.absorbed
print(mc.pivot(index='xD',columns='ratio',values='abs_ratio').round(2).to_string())
print(mc.pivot(index='xD',columns='ratio',values='max_depeg_bps_p50').round(0).to_string())
print(mc.pivot(index='xD',columns='ratio',values='final_depeg_bps_p50').round(0).to_string())
```

```
p_stays_broken
ratio     0.3     0.4     0.5     0.6     0.8     1.0     1.2     1.5
xD
0.25   0.8125  0.6875  0.6875  0.6875  0.8125  0.8125  0.8125  0.8750
0.50   0.8125  0.8125  0.8125  0.8125  0.8750  0.8750  0.9375  0.9375
1.00   0.6875  0.6875  0.8750  0.9375  1.0000  1.0000  1.0000  1.0000
2.00   0.8125  0.8125  0.8750  1.0000  1.0000  1.0000  1.0000  1.0000
4.00   0.6875  0.8125  0.8125  0.8750  1.0000  1.0000  1.0000  1.0000
p_reserves_exhausted: 0.0 in all 40 cells
absorbed ratio (capital / mean(defender_bought + holder_bought + redemption_paid))
ratio   0.3   0.4   0.5   0.6   0.8   1.0   1.2   1.5
xD
0.25   0.95  0.96  0.96  0.97  0.97  0.98  0.99  1.01
0.50   0.91  0.93  0.94  0.95  0.99  1.01  1.02  1.04
1.00   0.87  0.90  0.94  0.98  1.03  1.05  1.06  1.07
2.00   0.84  0.88  0.95  1.00  1.06  1.08  1.10  1.11
4.00   0.85  0.88  0.91  0.96  1.04  1.08  1.11  1.14
max_depeg_bps_p50
ratio   0.3   0.4   0.5   0.6   0.8   1.0   1.2   1.5
xD
0.25  -8096.0 -8651.0 -8994.0 -9221.0 -9494.0 -9645.0 -9737.0 -9820.0
0.50  -6309.0 -7114.0 -7681.0 -8096.0 -8651.0 -8994.0 -9221.0 -9441.0
1.00  -4287.0 -5114.0 -5774.0 -6309.0 -7475.0 -8151.0 -8520.0 -8868.0
2.00  -2588.0 -3230.0 -3792.0 -4935.0 -6514.0 -7306.0 -7788.0 -8259.0
4.00  -1439.0 -1850.0 -2232.0 -2780.0 -4646.0 -5737.0 -6473.0 -7208.0
final_depeg_bps_p50
ratio    0.3    0.4    0.5    0.6    0.8     1.0     1.2     1.5
xD
0.25   215.0  215.0  215.0  215.0  215.0   215.0   215.0   215.0
0.50   215.0  215.0  215.0  215.0  215.0   215.0   215.0   215.0
1.00   215.0  215.0  215.0  215.0  215.0   215.0   215.0   215.0
2.00    75.0   86.0  215.0  215.0 -469.0 -1767.0 -2614.0 -3486.0
4.00    26.0   25.0   27.0   87.0 -533.0 -2002.0 -3017.0 -4062.0
```

Per-seed recovery from `sweep.parquet`: number of the 8 capitals that recovered, per
seed × depth.

```python
df=pd.read_parquet('output/threshold-surface-mc/sweep.parquet')
df['xD']=(df.pool_depth/16666667).round(2)
df['rec']=(df.terminated_by=='peg_recovered').astype(int)
print(df.pivot_table(index='seed',columns='xD',values='rec',aggfunc='sum').to_string())
print(df.groupby('seed').final_depeg_bps.median().round(0).to_string())
```

```
xD    0.25  0.50  1.00  2.00  4.00      seed  median final_depeg_bps
seed
1000     7     4     2     2     3      1000    -202.0
1001     0     0     0     0     0      1001    1110.0
1002     3     0     2     0     1      1002      -2.0
1003     3     0     2     0     1      1003    -859.0
1004     0     0     0     0     0      1004    1653.0
1005     0     0     0     0     0      1005    1629.0
1006     0     0     0     0     0      1006      -0.0
1007     8     8     4     3     4      1007      -1.0
1008     0     0     0     0     0      1008      -0.0
1009     0     0     0     0     0      1009    1617.0
1010     0     0     0     0     0      1010     708.0
1011     0     0     0     0     0      1011    1668.0
1012     8     6     3     3     4      1012      -8.0
1013     0     0     0     0     0      1013     430.0
1014     0     0     0     0     0      1014      -3.0
1015     0     0     0     0     0      1015    1654.0
```
(The two printouts are shown side by side here; they were printed one after the other.)

**Diagnostic (not a deliverable): same grid on the calm base.** The spec is
`sweeps/threshold-surface-mc.yaml` with `name: diag-threshold-surface-calm` and
`base: scenarios/calibrated-baseline.yaml` (sed), in the scratchpad. The baseline and stress
files differ only in `name` and `volatility_per_step` (diff shown in the run):

```
$ time python -m depeg_sim.sweep <scratch>/diag-calm.yaml --mc --workers 10 --output <scratch>/out; echo exit=$?
sweep: diag-threshold-surface-calm cells=640 workers=10
wrote: <scratch>/out/diag-threshold-surface-calm/sweep.parquet
mc: diag-threshold-surface-calm grid_points=40 seeds=16 runs=640
wrote: <scratch>/out/diag-threshold-surface-calm/mc.parquet

real	2m8.851s
exit=0

p_stays_broken (calm)
ratio  0.3  0.4    0.5     0.6    0.8     1.0     1.2     1.5
xD
0.25   0.0  0.0  0.000  0.0000  0.000  0.0000  0.1250  0.1875
0.50   0.0  0.0  0.000  0.1875  0.375  0.5625  0.5625  0.5000
1.00   0.0  0.0  0.375  0.5625  1.000  1.0000  1.0000  1.0000
2.00   0.0  0.0  0.500  1.0000  1.000  1.0000  1.0000  1.0000
4.00   0.0  0.0  0.000  0.5000  1.000  1.0000  1.0000  1.0000
absorbed ratio (calm)
ratio    0.3    0.4    0.5    0.6    0.8    1.0    1.2    1.5
xD
0.25   0.946  0.960  0.971  0.978  0.989  0.996  1.000  1.017
0.50   0.937  0.954  0.964  0.963  0.993  1.011  1.023  1.033
1.00   0.934  0.951  0.955  0.985  1.027  1.049  1.060  1.068
2.00   0.934  0.945  0.953  0.996  1.055  1.083  1.097  1.107
4.00   0.933  0.945  0.956  0.961  1.037  1.085  1.114  1.139
p_reserves_exhausted max: 0.0
```

**Constraints check.** Scenario hashes at e793656 (before the story) and now were
byte-compared with `diff` and are identical:

```
calibrated-baseline.yaml 44ac03c60e5f
calibrated-stress.yaml 17b24b458e47
soros-1992-no-defense.yaml 516edaef4795
soros-1992.yaml f4e26ae66440
soros-baseline.yaml 2e09f431ce74
soros-volatile.yaml 84ad0b810807
usdc-2023.yaml 2c3aeaa9825d
$ git diff e793656 --stat -- src/depeg_sim/kernel src/depeg_sim/protocol    (empty)
PHASE_ORDER_VERSION = 1
```

**Tests and lint at the blocked commit (93794ed):**

```
$ ruff check .; echo ruff_check_exit=$?; ruff format --check .; echo ruff_format_exit=$?
All checks passed!
ruff_check_exit=0
83 files already formatted
ruff_format_exit=0
$ python -m pytest 2>&1 | tail -1
512 passed in 6.06s
```

#### Part 2: after the Rulings

**Threshold-surface sweep, base `calibrated-baseline` (amended AC 3), through the spec:**

```
$ time python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc --workers 10; echo exit=$?
sweep: threshold-surface-mc cells=640 workers=10
wrote: output/threshold-surface-mc/sweep.parquet
mc: threshold-surface-mc grid_points=40 seeds=16 runs=640
wrote: output/threshold-surface-mc/mc.parquet

real	2m23.731s
user	23m22.162s
sys	0m7.481s
exit=0
```

Its `p_stays_broken` and absorbed-ratio tables are identical to the Part 1 calm
diagnostic, as expected (same configs except `name`).

**Surface aggregate tables:** `<scratch>/surface_tables.py`, run from the repo root.

```python
import numpy as np, pandas as pd
mc = pd.read_parquet("output/threshold-surface-mc/mc.parquet")
A = "agents[type=attacker].capital"
mc["ratio"] = (mc[A] / 179454391).round(2)
mc["xD"] = (mc.pool_depth / 16666667).round(2)
mc["p_broken"] = 1 - mc.p_peg_recovered
mc["absorbed"] = mc.defender_bought_stable_mean + mc.holder_bought_stable_mean + mc.redemption_paid_total_mean
mc["abs_ratio"] = mc[A] / mc.absorbed
for col, fmt in [("p_broken", 4), ("p_reserves_exhausted", 4), ("abs_ratio", 3),
                 ("defender_bought_stable_mean", 0), ("holder_bought_stable_mean", 0),
                 ("redemption_paid_total_mean", 0), ("max_depeg_bps_p50", 0)]:
    print(col); print(mc.pivot(index="xD", columns="ratio", values=col).round(fmt).to_string())
def cross(x, p):
    """first upward 0.5 crossing by linear interpolation; None if never >= 0.5"""
    x, p = np.asarray(x), np.asarray(p)
    for i in range(len(p)):
        if p[i] >= 0.5:
            if i == 0: return f"<= {x[0]:.3f}"
            return round(float(x[i-1] + (0.5 - p[i-1]) * (x[i] - x[i-1]) / (p[i] - p[i-1])), 3)
    return None
print("0.5 crossing per depth row: nominal ratio, absorbed ratio")
for xd, g in mc.sort_values("ratio").groupby("xD"):
    print(xd, cross(g.ratio, g.p_broken), cross(g.abs_ratio, g.p_broken),
          "monotone_abs" if g.abs_ratio.is_monotonic_increasing else "NONMONOTONE_abs")
```
```
p_broken
ratio  0.3  0.4    0.5     0.6    0.8     1.0     1.2     1.5
xD                                                           
0.25   0.0  0.0  0.000  0.0000  0.000  0.0000  0.1250  0.1875
0.50   0.0  0.0  0.000  0.1875  0.375  0.5625  0.5625  0.5000
1.00   0.0  0.0  0.375  0.5625  1.000  1.0000  1.0000  1.0000
2.00   0.0  0.0  0.500  1.0000  1.000  1.0000  1.0000  1.0000
4.00   0.0  0.0  0.000  0.5000  1.000  1.0000  1.0000  1.0000
p_reserves_exhausted
ratio  0.3  0.4  0.5  0.6  0.8  1.0  1.2  1.5
xD                                           
0.25   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
0.50   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
1.00   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
2.00   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
4.00   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
abs_ratio
ratio    0.3    0.4    0.5    0.6    0.8    1.0    1.2    1.5
xD                                                           
0.25   0.946  0.960  0.971  0.978  0.989  0.996  1.000  1.017
0.50   0.937  0.954  0.964  0.963  0.993  1.011  1.023  1.033
1.00   0.934  0.951  0.955  0.985  1.027  1.049  1.060  1.068
2.00   0.934  0.945  0.953  0.996  1.055  1.083  1.097  1.107
4.00   0.933  0.945  0.956  0.961  1.037  1.085  1.114  1.139
defender_bought_stable_mean
ratio         0.3         0.4         0.5          0.6          0.8          1.0          1.2          1.5
xD                                                                                                        
0.25   49837018.0  67232637.0  84596290.0  101946768.0  136509253.0  170930872.0  202846597.0  248892483.0
0.50   48114603.0  65555334.0  83011140.0   97876884.0  125274273.0  153585142.0  182291610.0  226038637.0
1.00   44698782.0  62051797.0  72050524.0   82491715.0  104704540.0  128135541.0  152938442.0  190424923.0
2.00   39400451.0  53530957.0  60044202.0   67426868.0   84205477.0  102838543.0  122832089.0  153699203.0
4.00   33624235.0  47212483.0  50679043.0   55307779.0   67042838.0   80069368.0   93672623.0  114991859.0
holder_bought_stable_mean
ratio         0.3         0.4         0.5         0.6         0.8         1.0         1.2          1.5
xD                                                                                                    
0.25    3051286.0   3329827.0   3592390.0   3858384.0   4409387.0   4996770.0   6037457.0    8320622.0
0.50    5101744.0   5463855.0   5825801.0   6979612.0  10181800.0  14002085.0  18083342.0   24265265.0
1.00    8697949.0   9164307.0  13042647.0  16514596.0  24209620.0  32068681.0  39419677.0   50790557.0
2.00   14011313.0  17563198.0  24315050.0  29755220.0  40972645.0  51977055.0  62592219.0   78559930.0
4.00   19861067.0  23730513.0  38050528.0  46850347.0  60504737.0  74443861.0  88706165.0  110497014.0
redemption_paid_total_mean
ratio        0.3        0.4        0.5         0.6         0.8         1.0         1.2         1.5
xD                                                                                                
0.25   3992688.0  4237443.0  4251240.0   4240504.0   4246640.0   4232793.0   6479706.0   7523457.0
0.50   4234663.0  4260047.0  4263356.0   6899798.0   9169081.0   9958468.0  10166784.0  10280559.0
1.00   4227391.0  4274904.0  8898714.0  10319014.0  10871507.0  10871507.0  10871507.0  10871507.0
2.00   4259131.0  4826310.0  9768285.0  10871428.0  10871507.0  10871507.0  10871507.0  10871507.0
4.00   4215510.0  4978587.0  5107589.0   9886614.0  10871507.0  10871507.0  10871507.0  10871507.0
max_depeg_bps_p50
ratio     0.3     0.4     0.5     0.6     0.8     1.0     1.2     1.5
xD                                                                   
0.25  -8096.0 -8651.0 -8994.0 -9221.0 -9494.0 -9645.0 -9737.0 -9820.0
0.50  -6309.0 -7114.0 -7681.0 -8096.0 -8651.0 -8994.0 -9221.0 -9441.0
1.00  -4287.0 -5114.0 -5774.0 -6309.0 -7475.0 -8151.0 -8520.0 -8868.0
2.00  -2588.0 -3230.0 -3792.0 -4935.0 -6514.0 -7306.0 -7788.0 -8259.0
4.00  -1439.0 -1850.0 -2232.0 -2780.0 -4646.0 -5737.0 -6473.0 -7208.0
0.5 crossing per depth row: nominal ratio, absorbed ratio
0.25 None None monotone_abs
0.5 0.933 1.005 NONMONOTONE_abs
1.0 0.567 0.975 monotone_abs
2.0 0.5 0.953 monotone_abs
4.0 0.6 0.961 monotone_abs
```

**Collapse test** (`<scratch>/collapse.py`): pooled vs per-depth binomial logistic fits
with `depeg_sim.analysis.stats.fit_logistic`, likelihood-ratio test, nominal comparison.

```python
import math, pandas as pd
from depeg_sim.analysis.stats import fit_logistic
mc = pd.read_parquet("output/threshold-surface-mc/mc.parquet")
A = "agents[type=attacker].capital"
mc["p"] = 1 - mc.p_peg_recovered
mc["k"] = (mc.p * mc.n).round().astype(int)
mc["x"] = mc[A] / (mc.defender_bought_stable_mean + mc.holder_bought_stable_mean + mc.redemption_paid_total_mean)
mc["nom"] = mc[A] / 179454391
def ll(g, a, b):
    s = 0.0
    for x, k, n in zip(g.x, g.k, g.n):
        p = min(max(1 / (1 + math.exp(-(a + b * x))), 1e-12), 1 - 1e-12)
        s += k * math.log(p) + (n - k) * math.log(1 - p)
    return s
a, b = fit_logistic(mc.x.tolist(), mc.k.tolist(), mc.n.astype(int).tolist())
ll1 = ll(mc, a, b)
print(f"pooled: a={a:.2f} b={b:.2f} x50={-a/b:.4f} loglik={ll1:.2f}")
llsum = 0.0; x50s = []
for d, g in mc.groupby("pool_depth"):
    ad, bd = fit_logistic(g.x.tolist(), g.k.tolist(), g.n.astype(int).tolist())
    an, bn = fit_logistic(g.nom.tolist(), g.k.tolist(), g.n.astype(int).tolist())
    llsum += ll(g, ad, bd); x50s.append(-ad / bd)
    print(f"depth {d/16666667:.2f}xD*: absorbed x50={-ad/bd:.4f} (b={bd:.1f}); nominal x50={-an/bn:.3f}; absorbed range {g.x.min():.3f}-{g.x.max():.3f}")
lr = 2 * (llsum - ll1)
print(f"LR test per-depth vs pooled: stat={lr:.1f} on 8 df (chi2_0.999,8 = 26.1)")
s = pd.Series(x50s)
print(f"per-depth absorbed x50: mean {s.mean():.3f} sd {s.std(ddof=1):.3f} min {s.min():.3f} max {s.max():.3f}")
# pooled fit on the nominal ratio, for comparison
an, bn = fit_logistic(mc.nom.tolist(), mc.k.tolist(), mc.n.astype(int).tolist())
print(f"pooled nominal: x50={-an/bn:.3f}; loglik={ll(mc.assign(x=mc.nom), an, bn):.2f} vs absorbed {ll1:.2f}")
```
```
pooled: a=-50.46 b=50.19 x50=1.0054 loglik=-211.62
depth 0.25xD*: absorbed x50=1.0290 (b=105.3); nominal x50=1.737; absorbed range 0.946-1.017
depth 0.50xD*: absorbed x50=1.0173 (b=42.7); nominal x50=1.198; absorbed range 0.937-1.033
depth 1.00xD*: absorbed x50=0.9765 (b=79.2); nominal x50=0.564; absorbed range 0.934-1.068
depth 2.00xD*: absorbed x50=0.9533 (b=1200.6); nominal x50=0.500; absorbed range 0.934-1.107
depth 4.00xD*: absorbed x50=0.9610 (b=1759.9); nominal x50=0.600; absorbed range 0.933-1.139
LR test per-depth vs pooled: stat=179.4 on 8 df (chi2_0.999,8 = 26.1)
per-depth absorbed x50: mean 0.987 sd 0.034 min 0.953 max 1.029
pooled nominal: x50=0.870; loglik=-332.19 vs absorbed -211.62
```

**Oracle-lag sweep (AC 5)**, run in the background with output captured to a file:

```
$ (time python -m depeg_sim.sweep sweeps/oracle-lag-mc.yaml --mc --workers 10; echo exit=$?) > <scratch>/oracle_run.txt 2>&1
sweep: oracle-lag-mc cells=640 workers=10
wrote: output/oracle-lag-mc/sweep.parquet
mc: oracle-lag-mc grid_points=20 seeds=32 runs=640
wrote: output/oracle-lag-mc/mc.parquet

real	1m55.237s
user	18m50.467s
sys	0m6.637s
exit=0
```

**Oracle aggregate tables** (`<scratch>/oracle_tables.py`):

```python
import pandas as pd
mc = pd.read_parquet("output/oracle-lag-mc/mc.parquet")
H, T = "oracle.heartbeat_steps", "oracle.deviation_threshold_pct"
mc["p_broken"] = 1 - mc.p_peg_recovered
for col, r in [("max_depeg_bps_mean", 1), ("max_depeg_bps_p05", 1), ("max_depeg_bps_p95", 1),
               ("p_broken", 4), ("steps_to_sustained_recovery_mean", 0), ("defender_spent_mean", 0),
               ("holder_bought_stable_mean", 0), ("final_depeg_bps_p50", 1)]:
    print(col); print(mc.pivot(index=T, columns=H, values=col).round(r).to_string())
```
```
max_depeg_bps_mean
oracle.heartbeat_steps            5       25      300     1500    6900
oracle.deviation_threshold_pct                                        
0.00                           -1243.0 -1243.0 -1243.0 -1243.0 -1243.0
0.10                           -1242.8 -1242.9 -1242.9 -1242.9 -1242.9
0.25                           -1243.0 -1242.7 -1242.5 -1242.5 -1242.5
1.00                           -1242.9 -1246.1 -1253.2 -1253.2 -1253.2
max_depeg_bps_p05
oracle.heartbeat_steps            5       25      300     1500    6900
oracle.deviation_threshold_pct                                        
0.00                           -1253.2 -1253.2 -1253.2 -1253.2 -1253.2
0.10                           -1253.2 -1253.2 -1253.2 -1253.2 -1253.2
0.25                           -1253.2 -1253.2 -1253.2 -1253.2 -1253.2
1.00                           -1253.2 -1253.2 -1253.2 -1253.2 -1253.2
max_depeg_bps_p95
oracle.heartbeat_steps            5       25      300     1500    6900
oracle.deviation_threshold_pct                                        
0.00                           -1199.4 -1199.4 -1199.4 -1199.4 -1199.4
0.10                           -1209.2 -1209.2 -1209.2 -1209.2 -1209.2
0.25                           -1203.2 -1206.2 -1206.2 -1206.2 -1206.2
1.00                           -1209.6 -1223.4 -1253.2 -1253.2 -1253.2
p_broken
oracle.heartbeat_steps            5       25      300     1500    6900
oracle.deviation_threshold_pct                                        
0.00                            0.7188  0.7188  0.7188  0.7188  0.7188
0.10                            0.7188  0.7188  0.7188  0.7188  0.7188
0.25                            0.7188  0.6875  0.6875  0.6875  0.6875
1.00                            0.7188  0.6875  0.7188  0.7500  0.7500
steps_to_sustained_recovery_mean
oracle.heartbeat_steps            5       25      300     1500    6900
oracle.deviation_threshold_pct                                        
0.00                            3635.0  3635.0  3635.0  3635.0  3635.0
0.10                            3760.0  3760.0  3760.0  3760.0  3760.0
0.25                            3638.0  4115.0  4112.0  4112.0  4112.0
1.00                            3757.0  4010.0  4456.0  3970.0  3970.0
defender_spent_mean
oracle.heartbeat_steps               5          25         300        1500       6900
oracle.deviation_threshold_pct                                                       
0.00                            6005237.0  6005237.0  6005237.0  6005237.0  6005237.0
0.10                            5995945.0  5995544.0  5995544.0  5995544.0  5995544.0
0.25                            6022744.0  5992532.0  6001218.0  6001218.0  6001218.0
1.00                            5995036.0  6014649.0  6040020.0  6040020.0  6040020.0
holder_bought_stable_mean
oracle.heartbeat_steps               5          25         300        1500       6900
oracle.deviation_threshold_pct                                                       
0.00                            4703759.0  4703759.0  4703759.0  4703759.0  4703759.0
0.10                            4711449.0  4711441.0  4711441.0  4711441.0  4711441.0
0.25                            4688710.0  4710348.0  4703030.0  4703030.0  4703030.0
1.00                            4711438.0  4698617.0  4676139.0  4676139.0  4676139.0
final_depeg_bps_p50
oracle.heartbeat_steps           5      25     300    1500   6900
oracle.deviation_threshold_pct                                   
0.00                            112.4  112.4  112.4  112.4  112.4
0.10                            119.7  119.7  119.7  119.7  119.7
0.25                            109.4  119.7  110.6  110.6  110.6
1.00                            114.8  127.1  142.4  147.5  147.5
```

**F-04 floor probe (Rulings 2):** base attack on `calibrated-stress`, 32 seeds. I typed
the ratio as 0.06430930152 instead of 11,540,596 / 179,454,391 = 0.0643093542, so capital
is 11,540,586.54 rather than 11,540,596 (10 units short of 11.5M, 9e-7 relative).

```
$ time python scripts/probe_boundary.py --scenario scenarios/calibrated-stress.yaml --ratios 0.06430930152 --seeds 32 --workers 10 --output <scratch>/probe32
probe_boundary: scenario=scenarios/calibrated-stress.yaml budget+reserves=179,454,391 ratios=1 seeds=32 (1000..1031) cells=32
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.064              0.221 32                 0.000            0.312        0.688         -1,253.193        6,001,210.271

real	0m6.496s
$ python scripts/probe_boundary.py --scenario scenarios/calibrated-stress.yaml --ratios 0.06430930152 --seeds 1 --dry-run | tail -1
ratio 0.0643093: capital 11,540,586.54
```

`p_stays_broken` = 0.688 = 22/32 is identical to the oracle sweep's calibrated cell
(6900, 0.25): 0.6875. The chart draws the floor from that cell, since it is the same
configuration (base attack, calibrated oracle) and the chart reads only `mc.parquet`.

**What "stays broken" is made of on the calm surface (Completion Notes, ADR-0022 §7)**:
`<scratch>/above_peg.py`, `ref_drift.py`, `below_ref.py`.

```python
import pandas as pd
df = pd.read_parquet("output/threshold-surface-mc/sweep.parquet")
A = "agents[type=attacker].capital"
df["ratio"] = (df[A] / 179454391).round(2); df["xD"] = (df.pool_depth / 16666667).round(2)
broken = df[df.terminated_by != "peg_recovered"]
print("broken runs:", len(broken), "of", len(df))
print("broken runs ending ABOVE +31 bps:", int((broken.final_depeg_bps > 31).sum()),
      "| below -31 bps:", int((broken.final_depeg_bps < -31).sum()),
      "| inside band:", int((broken.final_depeg_bps.abs() <= 31).sum()))
t = broken.assign(above=(broken.final_depeg_bps > 31).astype(int))
print("count of broken runs ending above peg, by depth x ratio:")
print(t.pivot_table(index="xD", columns="ratio", values="above", aggfunc="sum", fill_value=0).to_string())
print("count of broken runs ending below peg:")
t["below"] = (t.final_depeg_bps < -31).astype(int)
print(t.pivot_table(index="xD", columns="ratio", values="below", aggfunc="sum", fill_value=0).to_string())
```
```
broken runs: 279 of 640
broken runs ending ABOVE +31 bps: 68 | below -31 bps: 168 | inside band: 43
count of broken runs ending above peg, by depth x ratio:
ratio  0.5  0.6  0.8  1.0  1.2  1.5
xD                                 
0.25     0    0    0    0    1    2
0.50     0    2    4    6    6    5
1.00     4    6    4    4    5    5
2.00     5    4    0    0    0    0
4.00     0    5    0    0    0    0
count of broken runs ending below peg:
ratio  0.5  0.6  0.8  1.0  1.2  1.5
xD                                 
0.25     0    0    0    0    1    1
0.50     0    1    1    2    2    2
1.00     1    2    3    5    5    7
2.00     2    3   16   16   16   16
4.00     0    2   16   16   16   16
```
```python
import pandas as pd
from pathlib import Path
from depeg_sim.experiments.sweep import load_sweep, expand, cell_run_dir
df = pd.read_parquet("output/threshold-surface-mc/sweep.parquet")
cells = {c.index: c for c in expand(load_sweep("sweeps/threshold-surface-mc.yaml"))}
broken = df[df.terminated_by != "peg_recovered"].copy()
broken["cls"] = pd.cut(broken.final_depeg_bps, [-1e9, -31, 31, 1e9], labels=["below", "inside", "above"])
rows = []
for _, r in broken.iterrows():
    ts = pd.read_parquet(cell_run_dir(cells[int(r["index"])], Path("output")) / "timeseries.parquet",
                         columns=["reference_price", "amm_price"])
    ref = ts.reference_price.iloc[-1]
    rows.append({"cls": r.cls, "ref_final_bps": (ref - 1) * 1e4,
                 "amm_minus_ref_bps": (ts.amm_price.iloc[-1] / ref - 1) * 1e4})
out = pd.DataFrame(rows)
print(out.groupby("cls", observed=True).describe().round(1).T.to_string())
```
```
cls                      above   below  inside
ref_final_bps     count   68.0   168.0    43.0
                  mean    68.7    -8.8     2.1
                  std     10.2    58.3    31.3
                  min     43.1  -103.5   -39.1
                  25%     61.0   -42.1   -26.7
                  50%     68.3   -25.9    -1.4
                  75%     75.5    43.1    28.5
                  max     85.4    85.4    62.4
amm_minus_ref_bps count   68.0   168.0    43.0
                  mean    -5.8 -1711.1    -6.6
                  std     11.7  1441.4    19.0
                  min    -30.5 -4111.8   -40.1
                  25%    -10.7 -3000.6   -16.6
                  50%     -9.8 -1817.7    -2.6
                  75%      0.2  -413.6     6.1
                  max     14.9    61.7    18.0
```
```python
"""Diagnostic: p(attack-broken) = share of runs not recovered AND ending with the AMM more than
the 31 bps tolerance below the reference price (not par). Per-row 0.5 crossings, nominal ratio."""
import numpy as np, pandas as pd
from pathlib import Path
from depeg_sim.experiments.sweep import load_sweep, expand, cell_run_dir
df = pd.read_parquet("output/threshold-surface-mc/sweep.parquet")
cells = {c.index: c for c in expand(load_sweep("sweeps/threshold-surface-mc.yaml"))}
A = "agents[type=attacker].capital"
gap = []
for _, r in df.iterrows():
    ts = pd.read_parquet(cell_run_dir(cells[int(r["index"])], Path("output")) / "timeseries.parquet",
                         columns=["reference_price", "amm_price"])
    gap.append((ts.amm_price.iloc[-1] / ts.reference_price.iloc[-1] - 1) * 1e4)
df["gap_bps"] = gap
df["attack_broken"] = ((df.terminated_by != "peg_recovered") & (df.gap_bps < -31)).astype(int)
df["ratio"] = (df[A] / 179454391).round(2); df["xD"] = (df.pool_depth / 16666667).round(2)
tab = df.pivot_table(index="xD", columns="ratio", values="attack_broken", aggfunc="mean")
print(tab.round(4).to_string())
for xd, row in tab.iterrows():
    x, p = np.array(row.index), row.to_numpy()
    hit = np.nonzero(p >= 0.5)[0]
    if hit.size == 0: print(xd, "not reached (max %.3f)" % p.max()); continue
    i = hit[0]
    print(xd, round(float(x[i-1] + (0.5 - p[i-1]) * (x[i] - x[i-1]) / (p[i] - p[i-1])), 3) if i else f"<= {x[0]}")
```
```
ratio  0.3  0.4  0.5    0.6    0.8    1.0     1.2    1.5
xD                                                      
0.25   0.0  0.0  0.0  0.000  0.000  0.000  0.0000  0.000
0.50   0.0  0.0  0.0  0.000  0.000  0.000  0.0000  0.000
1.00   0.0  0.0  0.0  0.000  0.125  0.125  0.0625  0.125
2.00   0.0  0.0  0.0  0.125  1.000  1.000  1.0000  1.000
4.00   0.0  0.0  0.0  0.000  1.000  1.000  1.0000  1.000
0.25 not reached (max 0.000)
0.5 not reached (max 0.000)
1.0 not reached (max 0.125)
2.0 0.686
4.0 0.7
```

**Palette check** (dataviz validator, the five categorical colours used in both charts):

```
$ node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4" --mode light
  [PASS] Lightness band         all 5 inside L 0.43–0.77
  [PASS] Chroma floor           all 5 >= 0.1
  [PASS] CVD separation         worst adjacent #eda100↔#1baf7a ΔE 9.1 (protan) · tritan 5.8
  [PASS] Normal-vision floor    worst adjacent #e87ba4↔#eda100 ΔE 19.6 (normal)
  [WARN] Contrast vs surface    below 3:1 — relief required (visible labels or table view): [["#1baf7a",2.74],["#eda100",2.11],["#e87ba4",2.62]]
  → ALL CHECKS PASS
```
Relief for the contrast WARN: every series also has a distinct marker shape and a legend
entry.

**Charts regenerated from the final code; constraints; tests and lint:**

```
$ python -c "...plot_threshold_surface('output/threshold-surface-mc'), plot_oracle_sensitivity('output/oracle-lag-mc')..."
output/threshold-surface-mc/threshold_surface.png 280267
output/oracle-lag-mc/oracle_sensitivity.png 196250
$ ruff check .; echo ruff_check_exit=$?; ruff format --check .; echo ruff_format_exit=$?
All checks passed!
ruff_check_exit=0
83 files already formatted
ruff_format_exit=0
$ python -m pytest 2>&1 | tail -1; echo pytest_exit=${PIPESTATUS[0]}
518 passed in 7.22s
pytest_exit=0
$ git diff e793656 --stat -- src/depeg_sim/kernel src/depeg_sim/protocol    (empty)
PHASE_ORDER_VERSION = 1
scenario hashes: diff against the e793656 list above -> hashes-identical-to-e793656
```

### Completion Notes List

**Headline sentence (AC 9), drafted from the calm surface:**

> At calibrated depth and calm volatility, an attack of ≥ 0.56× the defenders' nominal
> resources (≈ $24B against $42.1B of defender budget plus redemption reserves) leaves
> the peg broken through the 60-hour horizon with probability ≥ 0.5; across depths from
> 0.25× to 4× D\* the boundary sits at an absorbed ratio of 0.99 ± 0.04.

X = 0.56: the D\* row's 0.5 crossing is 0.567 by linear interpolation between 0.5
(0.375) and 0.6 (0.5625), and 0.564 by per-row logistic. Y ± Z: the mean of the five
per-depth logistic crossings on the absorbed ratio is 0.987 (sd 0.034, range
0.953–1.029), quoted as 0.99 ± 0.04 (half-range). **Read with the qualification below
before quoting: at D\* "broken" is mostly the clock, not the attack.**

**⚠ For the reviewer: what `p_stays_broken` measures at calibrated depth (ADR-0022 §7,
finding candidate).** On the calm surface 279 of 640 runs do not recover. 168 end
below −31 bps of par, 68 end *above* +31 bps, and 43 end inside the band without
having held it for 6,900 steps. In the above-band and in-band runs the AMM tracks the
reference (median gap −9.8 / −2.6 bps); in the above-band runs the reference itself
ended 43–85 bps above par. Calm volatility still spreads the reference by σ√6900 ≈ 26 bps
over one recovery window, comparable to the 31-bps band, so a recovery that starts late
cannot finish 6,900 in-band steps against par before step 18,000. Counting only runs
that end with the AMM more than 31 bps below the **reference**: 0/16 at 0.25× and 0.5×
D\* at every ratio, ≤ 2/16 at D\* (max 0.125), and the 0.5 crossing appears only at 2×
D\* (nominal 0.686) and 4× D\* (0.70). So at D\* and shallower, the defender plus holder
absorb attacks up to 1.5× resources (consistent with F-03: in a thin pool the budget buys
3.7–5.5× its face value at −9,000 bps). The headline's X = 0.56 is where recovery
becomes too *slow* to complete within the horizon. This is F-04 in miniature at calm
volatility. I have not changed the metric or the charts (both per AC). The diagnostic
(scripts and output) is in the Debug Log for the ruling. A reference-relative sentence,
if preferred: "the attack itself leaves the AMM below the dollar with p ≥ 0.5 only in
pools ≥ 2× D\*, at ≥ 0.69× resources."

**0.5 contour per depth row (nominal ratio; linear interpolation | per-row logistic):**

| depth | crossing | note |
|---|---|---|
| 0.25× D\* ($0.98B) | not reached (max 0.19 at 1.5) | logistic extrapolates 1.74 |
| 0.5× D\* ($1.96B) | 0.93 \| 1.20 | plateaus at 0.50–0.56 from 1.0 to 1.5; there the defender's full 41.3M budget buys 153–226M stable, and the broken runs end at +51 bps median (above peg) |
| 1× D\* ($3.91B) | 0.57 \| 0.56 | |
| 2× D\* ($7.82B) | 0.50 \| 0.50 | the 0.5 cell itself is exactly 0.50 |
| 4× D\* ($15.64B) | 0.60 \| 0.60 | the 0.6 cell itself is exactly 0.50 |

The AC 3 extension rule did **not** trigger: 13 cells have `p_stays_broken ≥ 0.9`. The
ratio axis is as specified. `p_reserves_exhausted = 0` in every cell of both sweeps.

**Collapse verdict (AC 4 right panel): a narrow fan, not one logistic.** The pooled
logistic on the absorbed ratio crosses 0.5 at **1.005**. Per-depth crossings are 1.029
(0.25×, extrapolated past its largest observed absorbed ratio 1.017), 1.017 (0.5×),
0.977 (1×), 0.953 (2×) and 0.961 (4×). The absorbed ratio pulls the crossings from
0.50–1.74 (nominal) into 0.95–1.03 and improves the pooled log-likelihood from −332.2 to
−211.6. But per-depth curves beat the pooled one decisively (LR 179.4 on 8 df vs
χ²₀.₉₉₉ = 26.1): deeper pools stay broken at a slightly lower absorbed ratio. F-03 holds
at calibrated scale with the buyer present from 0.25× to 1× D\* (nominal crossing falls
1.74 → 1.20 → 0.56), then saturates (2× 0.50, 4× 0.60).

**Oracle paragraph (AC 9):** Oracle lag does not matter under deviation-triggered updates
at Chainlink's cadence. On the stress base at the episode-sized attack, the mean trough
across all 20 (heartbeat × threshold) settings lies between −1,253.2 and −1,242.5 bps, a
10.7-bps range on a −1,243-bps trough. The calibrated oracle (heartbeat 6,900 steps =
23 h, threshold 0.25%) gives −1,242.5, within 0.5 bps of the zero-lag oracle (−1,243.0).
At thresholds ≤ 0.25% heartbeat moves the trough by ≤ 0.5 bps. At every threshold,
heartbeats of 300 steps and above give identical results: under stress volatility the
deviation trigger fires before an hour-long heartbeat would. Only a 1% threshold with a
heartbeat ≥ 1 h changes anything. It deepens the mean trough by 10.2 bps, to −1,253.2 in
every seed (p05 = p95). That is consistent with the arbitrageur no longer following small
reference moves before the attack, so the dump always lands on a pool sitting at par.
`p_stays_broken` is 0.69–0.75 in every cell, inside each other's Wilson intervals: it is
the F-04 floor (0.6875 at the calibrated cell; the probe at the base attack gives 0.688
on the same 32 seeds), not an oracle effect.

**Chart descriptions.**
- `threshold_surface.png`, left: a 5 × 8 blue heatmap, light where the peg recovers and
  dark where it stays broken. The bottom two rows (0.25×, 0.5× D\*) stay light to mid-blue
  across the whole capital range. The top three rows turn fully dark from 0.6–0.8× upward.
  The orange 0.5 contour runs from about 0.6× at the top row, cuts left to 0.5× at 2×
  D\*, back to about 0.57× at D\*, then bends far right along the 0.5× D\* row (0.93 →
  1.5×) and never reaches the bottom row. Every cell is annotated with p and its Wilson
  half-width (±0.10 at p = 0 or 1, ±0.21–0.22 near 0.5).
- `threshold_surface.png`, right: all 40 cells against the absorbed ratio. Points sit at
  0 below about 0.95 and at 1 above about 1.03 for every depth. The transition is packed
  into 0.95–1.03 with one black logistic (0.5 at 1.005) through it. The deep-pool markers
  (2×, 4×) reach 0.5 just left of the curve (0.953, 0.961); the shallow ones (0.25× blue
  circles) lie right of and below it, at 0.12–0.19 near 1.0–1.017.
- `oracle_sensitivity.png`, top (primary): four nearly flat lines at −1,243 bps across
  heartbeats 5 to 6,900. Only the 1% line (yellow diamonds) steps down to −1,253 from
  heartbeat 300. A text note prints the 10.7-bps all-cell range, and dotted p05/p95 lines
  show the per-seed spread (−1,253 to −1,199). Bottom: four lines at 0.69–0.75 with
  overlapping Wilson bars (≈ 0.51–0.87), a dashed F-04 floor at 0.69, and the calibrated
  cell ringed on both panels.

**Stress-base surface (Rulings 5, recorded for FINDINGS; not charted):** run as
originally specified on `calibrated-stress`, 11 of 16 seeds (1001, 1004–1006, 1008–1011,
1013–1015) never re-enter the ±31 bps band in any of the 40 cells, whatever the attack
or depth. `p_stays_broken` therefore has a floor of exactly 11/16 = 0.6875. The median
final deviation is **+215 bps, above peg**, in every cell of the 0.25×, 0.5× and 1× D\*
rows. Tables are in Debug Log Part 1.

**Other notes.**
- AC 1: `defender_bought_stable` is a new `Defender.bought_stable` counter (sum of
  `amount_out` over executed buys, mirroring `Holder.bought_stable`). It is **not** added
  to `_snapshot_extra`, so timeseries and checkpoints are unchanged. The new summary keys
  sit after `arbitrageur_pnl`; the existing keys keep their order. `aggregate_mc` treats a
  metric missing from an older `sweep.parquet` as NaN.
- AC 2: `scales` is checked in `expand` (`SweepSpecError`), next to the duplicate-axis
  check. A scale of exactly 1 leaves the value untouched. The manifest dumps axes with
  `exclude_none`, so unscaled sweeps' manifests are unchanged. Equivalence is pinned by
  the first and last cell hashes and a digest over all 16 cells of
  `pool-depth-x-attacker.yaml`, captured at bca5025.
- Sweep manifest `base_config` (Rulings 4). The dollar scale is the chart constant
  `USD_PER_UNIT = 234.6` (SOURCES.md `s`), overridable by keyword, since it is not a
  config field.
- Holder capital at the D\* row is 9,166,666.85 (0.55 × 16,666,667) against the base
  file's 9,166,667 (C\*/D\* = 0.550000009; the spec says 0.55). Stated in the sweep
  header.
- `fit_logistic` (binomial MLE, Newton on standardised x, 1e-6 ridge so separated data
  converge) is added to `analysis/stats.py`, per the context's "short numpy Newton" note,
  in plain Python.
- AC 6 floor: the chart draws it from the calibrated cell of `mc.parquet`. That cell *is*
  the base scenario's own attack at the calibrated oracle, so AC 7 (parquet + manifest
  only) holds. The probe run the Rulings ask for gives the same 0.688. Note that every
  cell of this sweep uses the base attack, so the floor and the attack are not separable
  here. The panel answers only "does oracle lag move p away from the floor?" (no).
- Chart conventions: each panel is 10 × 6 in at 150 dpi (surface 20 × 6 side by side,
  oracle 10 × 12 stacked), with footer `sweep=<name> base_hash=<12>`. Categorical colours
  passed the dataviz palette validator; marker shapes give non-colour identity.
- ADR: **0022** (Proposed).
- Wall times (10 workers, Seoul): surface **2m23.7s**, oracle **1m55.2s**.

### File List

**Created:**
- `sweeps/threshold-surface-mc.yaml`
- `sweeps/oracle-lag-mc.yaml`
- `docs/adr/0022-threshold-surface-metric-and-oracle-lag.md`

**Modified:**
- `src/depeg_sim/analysis/summary.py` (three keys)
- `src/depeg_sim/agents/defender.py` (`bought_stable` counter)
- `src/depeg_sim/experiments/mc.py` (three METRICS; missing-column tolerance)
- `src/depeg_sim/experiments/sweep.py` (`LinkedAxis.scales`, `path_values`, checks in `expand`; manifest `base_config`, `exclude_none` axes)
- `src/depeg_sim/analysis/stats.py` (`fit_logistic`)
- `src/depeg_sim/analysis/charts.py` (`plot_threshold_surface`, `plot_oracle_sensitivity`)
- `tests/test_summary.py`, `tests/test_mc.py`, `tests/test_sweep.py`, `tests/test_stats.py`, `tests/test_charts.py`
- `docs/stories/2-7-threshold-surface.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.6 review
- 2026-10-04: AC 1 and AC 2 implemented (bca5025, d41c164). Threshold-surface sweep run
  as specified; blocked because the stress base's F-04 floor (p_stays_broken ≥ 0.6875 in
  every cell) contradicts F-04's calm-volatility rule for headline sweeps. Status: blocked.
- 2026-10-04: Dev manager ruled on Blockers: surface on calm baseline (F-04), oracle on stress with trough primary; AC 3/5/6/9 and Dev Notes amended; Status back to in-progress
- 2026-10-04: Resumed after Rulings. Surface re-run on `calibrated-baseline` (2m23.7s),
  oracle sweep on `calibrated-stress` (1m55.2s), both charts, F-04 floor probe, collapse
  and "stays broken" diagnostics, ADR-0022 (Proposed). 518 tests pass, ruff clean.
  Status: review.
