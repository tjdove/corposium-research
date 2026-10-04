# Story 2.7: Threshold Surface and Oracle-Lag Sensitivity

Status: in-progress

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
- [ ] Threshold surface (AC: 3, 4, 8) — **blocked, see Blockers**
  - [x] Sweep spec; run
  - [ ] `plot_threshold_surface`; synthetic-parquet test; look at the chart and describe it
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

**Tests and lint at the blocked commit:**

```
$ ruff check .; echo ruff_check_exit=$?; ruff format --check .; echo ruff_format_exit=$?
All checks passed!
ruff_check_exit=0
83 files already formatted
ruff_format_exit=0
$ python -m pytest 2>&1 | tail -1
512 passed in 6.06s
```

### Completion Notes List

- **Blocked. See `## Blockers`.** No headline sentence, collapse verdict, oracle
  paragraph or ADR yet: each depends on the ruling.
- AC 1: `defender_bought_stable` is a new `Defender.bought_stable` counter (sum of
  `amount_out` over executed buys, mirroring `Holder.bought_stable`). It is **not** added
  to `_snapshot_extra`, so timeseries and checkpoints are unchanged. New summary keys sit
  after `arbitrageur_pnl`; the existing keys keep their order. `aggregate_mc` treats a
  metric missing from an older `sweep.parquet` as NaN rather than raising.
- AC 2: `scales` is checked in `expand` (raising `SweepSpecError`), next to the
  duplicate-axis check. A pydantic validator would wrap it in `ValidationError`, and the
  context's test idea names `SweepSpecError`. A scale of exactly 1 sets the value
  untouched (no int → float). The manifest dumps axes with `exclude_none`, so unscaled
  sweeps' manifests are unchanged. Equivalence is pinned by the first and last cell
  hashes and a digest over all 16 cells of `pool-depth-x-attacker.yaml`, captured at
  bca5025 before the change.
- Sweep manifest gains `base_config` (the resolved base scenario). AC 7 says charts read
  only `mc.parquet` + manifest, and the nominal-ratio labels need `budget + reserves`.
  This is the ADR-0014 pattern at sweep level; it will go in the ADR.
- Holder capital at the D\* row is 9,166,666.85 (0.55 × 16,666,667) against the base
  file's 9,166,667, because C\*/D\* = 0.550000009 and the spec says 0.55. Stated in the
  sweep header.

### File List

**Created:**
- `sweeps/threshold-surface-mc.yaml`

**Modified:**
- `src/depeg_sim/analysis/summary.py` (three keys)
- `src/depeg_sim/agents/defender.py` (`bought_stable` counter)
- `src/depeg_sim/experiments/mc.py` (three METRICS; missing-column tolerance)
- `src/depeg_sim/experiments/sweep.py` (`LinkedAxis.scales`, `path_values`, checks in `expand`; manifest `base_config`, `exclude_none` axes)
- `tests/test_summary.py`, `tests/test_mc.py`, `tests/test_sweep.py`
- `docs/stories/2-7-threshold-surface.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.6 review
- 2026-10-04: AC 1 and AC 2 implemented (bca5025, d41c164). Threshold-surface sweep run
  as specified; blocked because the stress base's F-04 floor (p_stays_broken ≥ 0.6875 in
  every cell) contradicts F-04's calm-volatility rule for headline sweeps. Status: blocked.
- 2026-10-04: Dev manager ruled on Blockers: surface on calm baseline (F-04), oracle on stress with trough primary; AC 3/5/6/9 and Dev Notes amended; Status back to in-progress
