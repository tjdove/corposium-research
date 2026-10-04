# Story 2.5: USDC March-2023 Validation

Status: done

## Story

As a **researcher**,
I want the model to reproduce the shape of a real depeg,
so that the note's claims rest on more than internal consistency.

## Acceptance Criteria

### Part A — re-anchor the attacker and re-fit depth (ADR-0019 amendment)

1. `docs/calibration/SOURCES.md` attacker row becomes `secondary`: `capital` = net USDC supply change from 2023-03-10 to 2023-03-13 computed from the committed `data/usdc_supply_defillama_2023-03-01_2023-03-20.csv` (show the two supply figures and the difference), converted by `s`; the peak-hour CEX outflow ($1.2B/h, Chainalysis) is stated as a cross-check, not an input; the "ratio 1.0" row is removed and its removal noted
2. `scripts/fit_depth.py` re-run on the re-anchored `calibrated-baseline.yaml` with the original grid (1M…500M); the AC 2 rule from 2.4 applies unchanged; `D*` reported as model units, as `market_depth_multiple`, **and as dollars per side at `s`**, alongside the Curve USDC leg ($234.6M) for comparison; both calibrated YAMLs updated; the `market_depth_multiple` row updated with the new value and "re-fit after attacker re-anchor (ADR-0019 amendment)"
3. `scripts/probe_boundary.py` re-run at the new `D*` on ratios `[0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 1.0]` with `deliverable reserves` printed alongside; Completion Notes state where the F-06 flip sits now and whether the F-06 formula still predicts it
4. `scenarios/soros-1992.yaml` and `-no-defense.yaml` re-run at the new `D*`; the 5.3× flip re-scanned (step 0.1× between 4.0 and 7.0); new values in both YAML headers; Completion Notes say whether F-07's conclusion holds
5. Commit Part A separately: `story 2.5: re-anchor attacker to episode flow; re-fit D*`

### Part B — observed-series environment and the replay

6. `EnvironmentConfig` gains `price_series_path: Path | None = None` (relative to the scenario file's directory); when set, `volatility_per_step` must be `0` and `shocks` empty (validator), and `ReferencePrice.from_config` loads the CSV (columns `unix, close` required), linearly interpolates `close` to 12-second steps from the first timestamp, and uses that as the reference price; past the end of the series the last value holds; `price_series_hash` (sha256 of the file) is included in `ScenarioConfig.content_hash()` via a validator that reads the file at load time (so a changed CSV changes the hash)
7. `ReferencePrice` emits `price_updated` as before; a test loads a 5-row synthetic CSV and checks interpolation at known steps and the hold-last behaviour; a second test shows two scenarios identical except for the CSV contents have different `content_hash()`
8. `scenarios/usdc-2023.yaml`: calibrated-baseline parameters, `environment.price_series_path: ../data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv`, `start_step` at the step corresponding to 2023-03-10 22:00 ET (Circle's disclosure; compute from the series' first timestamp and state it), attacker `capital` from AC 1, `pace` **fitted** so the simulated trough's timing lands within ±2 hours of the observed trough (2023-03-11 ~02:00 ET per Chainalysis; state the step) — scan `pace` over `[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]` and pick the closest, `assumption`; defender budget as calibrated but **`threshold_pct` set so the defender does not act** (Circle did not buy USDC on AMMs; `assumption`, cite 21Shares/Chainalysis silence) — or budget 1, whichever is cleaner, state which; redemption capacity: calibrated throughput until the step for **2023-03-13 09:00 ET** (banks reopen / Circle's statement), then a scheduled change to a capacity that clears the queue within one day (new `RedemptionConfig.capacity_schedule: list[{step, capacity_per_step}]`, applied in `PROTOCOL_EVENTS`; validator: steps ascending); `max_steps` covering 2023-03-10 22:00 ET to 2023-03-14 12:00 ET
9. `plot_validation_overlay(run_dir)`: one panel, elapsed hours on x (origin = series start), **observed** reference price (from the manifest's `price_series_path`, re-read) and **simulated** AMM price on the same axis in bps from peg; vertical markers at attack start and at the capacity-schedule step; annotations for observed trough (value, time) and simulated trough (value, time); chart conventions apply; footer with hash
10. Quantitative comparison in Completion Notes **and** written into `docs/calibration/VALIDATION.md`: observed vs simulated trough depth (bps) and time (hours after series start); observed vs simulated time at which the price is last outside the ADR-0013 band; the direction and timing of recovery relative to the capacity-schedule step; one paragraph on what matches and what does not, and why
11. `tests/test_usdc_2023.py`: scenario validates; hash includes the CSV; short run (`max_steps` 500) completes; `plot_validation_overlay` produces a PNG on a tiny run
12. A `Proposed` ADR for: the episode-flow attacker anchor as applied, the new `D*`, the fitted `pace`, the defender-inactive assumption, and the capacity-schedule semantics; a findings write-up in Completion Notes for anything new (candidates: whether `D*` is now physical; what the overlay shows about the model's recovery vs the real one)
13. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Part A (AC: 1–5)
  - [x] Compute net burn from the committed CSV; SOURCES.md attacker row; remove ratio-1.0 row
  - [x] Re-fit `D*`; update YAMLs and SOURCES.md; report three units
  - [x] Re-probe boundary; re-run and re-scan 1992
  - [x] Commit Part A

- [x] Schema and environment (AC: 6, 7)
  - [x] `EnvironmentConfig.price_series_path`; validator; hash inclusion
  - [x] `RedemptionConfig.capacity_schedule`; validator
  - [x] `ReferencePrice.from_config` series loading + interpolation; `RedemptionModule` schedule application in `PROTOCOL_EVENTS` (emit `capacity_changed`)
  - [x] Tests per AC 7 plus a capacity-schedule test (queue drains after the step)

- [x] Replay scenario (AC: 8)
  - [x] Compute `start_step`, backstop step, `max_steps` from the series timestamps; put the arithmetic in the YAML header
  - [x] Scan `pace`; pick; record
  - [x] Run; record three CLI lines

- [x] Overlay and validation doc (AC: 9, 10)
  - [x] `analysis/charts.py::plot_validation_overlay`
  - [x] `docs/calibration/VALIDATION.md`; look at the PNG and describe it

- [x] ADR, tests, close out (AC: 11, 12, 13)
  - [x] Proposed ADR; `tests/test_usdc_2023.py`
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.5: usdc march-2023 validation`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.4 (Status: done)**

- **The attacker ratio was the wrong input, not the depth grid.** D\* at $430B/side was
  the model absorbing a $42B attacker when the episode's net burn was ~$4B. Part A fixes
  the input and re-fits. Expect D\* in the low billions of dollars; report it in dollars
  so a reader can judge it against the Curve leg.
- Pace doesn't move the trough; it moves the trough's *timing*. That's why AC 8 fits pace
  to timing after depth is set.
- F-06: with throughput-bound redemption the far side of the boundary is "stays broken,"
  and recovery needs an outside backstop. AC 8's capacity schedule is that backstop.
- F-07: sequential defenses strand the price between them. The USDC replay has no AMM
  defender, so this doesn't arise here; it's a 1992 phenomenon.
- Builder may merge an approved-but-unmerged story branch into `main` before starting;
  the dev manager will confirm merges before prompts from now on.

[Source: docs/stories/2-4-depth-fit-and-1992.md#Senior-Developer-Review, docs/FINDINGS.md F-05 correction, F-06, F-07]

### Why this story allows schema changes

Two fields are required by the validation itself: an observed reference series, and a
scheduled change in redemption capacity (the banking-weekend-then-backstop mechanism).
Both are data-only additions to existing config models with validators, both default to
"absent" so every existing scenario and hash is unchanged. Nothing in kernel/ changes.
This is the one story in Epic 2 with a schema edit; say so in the ADR.

### Series interpolation

Hourly candles → 12 s steps means 300 steps per candle. Linear interpolation of `close`
between consecutive candle timestamps; step `k` is at `unix_0 + 12k`. Store the
interpolated array once at construction (≈ 20k floats for the stress file). The
environment still emits one `price_updated` per step. `volatility_per_step` must be 0 and
`shocks` empty when a series is set: the series *is* the environment.

### Timestamps to compute (state them in the YAML header)

- Series start: first `unix` in the stress CSV (2023-03-10 00:00 UTC per the filename).
- Attack start: 2023-03-10 22:00 ET = 2023-03-11 03:00 UTC → `(1678503600 − unix_0) / 12`.
- Observed trough: ~2023-03-11 02:00 ET = 07:00 UTC (Chainalysis "by 2am").
- Backstop / banks reopen: 2023-03-13 09:00 ET = 13:00 UTC. (The Fed/Treasury/FDIC
  statement was Sunday evening 2023-03-12; Circle's "100% safe" statement and the repeg
  were Monday morning. Use Monday 09:00 ET and say why.)
- End: 2023-03-14 12:00 ET = 16:00 UTC.

If the stress CSV ends before 2023-03-14, hold-last applies and the header says so.

### What "matches" should mean in VALIDATION.md

Be specific and modest. The model has one venue, no CEX, no cross-stablecoin rotation,
no bank. It can plausibly match: trough depth (by construction, via D\*), trough timing
(via pace), and the *shape* of the plateau (stays broken until the backstop). It cannot
match: intra-weekend wobbles driven by news, or the exact recovery slope (which depended
on how fast real redemptions cleared). Say which is which.

### Defender in the replay

Circle did not intervene on AMMs; the "defense" was the redemption promise and, after
Monday, honouring it. Simplest faithful encoding: keep the defender agent (so the
scenario schema is the calibrated one) but set `threshold_pct` to a value it never
reaches (e.g. 99.0) and note it. Setting budget to 1 also works; pick one and state it.

### References

- [Source: docs/epics.md#Story-2.5]
- [Source: docs/adr/0019-fitted-depth-and-1992-analogue.md] — review amendment
- [Source: docs/FINDINGS.md] — F-05 correction, F-06
- [Source: docs/calibration/SOURCES.md] — attacker, capacity, pool sections
- [Source: data/README.md] — stress and supply CSVs
- Chainalysis (trough by 2am ET Mar 11; $1.2B/h): https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/
- 21Shares (repeg Mar 13; reserves split): https://www.21shares.com/en-eu/insights/newsletter-issue-193

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-5-usdc-validation.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul

### Debug Log References

Final pass, captured after all edits (one shell block, output verbatim):

```
$ pytest; echo exit=$?
454 passed in 5.79s
exit=0
$ ruff check .; echo exit=$?
All checks passed!
exit=0
$ ruff format --check .; echo exit=$?
79 files already formatted
exit=0
$ python scripts/fit_depth.py --workers 8; echo exit=$?
grid pass (target -1300 bps):
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
    1000000       -7,844.7 peg_recovered     5,161,788.5       7030
    2000000       -5,979.0 peg_recovered     6,770,897.2       7040
    5000000       -3,398.8 peg_recovered     8,692,778.7       7018
   10000000       -1,962.2 peg_recovered     9,702,523.8       7083
   20000000       -1,061.3 peg_recovered    10,435,472.6       7017
   50000000         -446.1 peg_recovered    10,884,406.8       7001
  100000000         -226.9 peg_recovered    10,828,747.0       7204
  200000000         -154.7 peg_recovered    10,960,204.7       6987
  500000000         -116.0 peg_recovered    10,846,809.0       6982

refine pass between 10,000,000 and 20,000,000:
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
   11666667       -1,719.2 peg_recovered     9,879,920.7       7086
   13333333       -1,529.7 peg_recovered    10,056,633.2       7005
   15000000       -1,377.7 peg_recovered    10,169,402.5       7004
   16666667       -1,253.2 peg_recovered    10,261,333.7       7024
   18333333       -1,149.3 peg_recovered    10,332,016.4       7043

D* = 16666667 (trough -1253.2 bps)
exit=0
$ python scripts/probe_boundary.py --workers 8 --ratios 0.1,0.2,0.25,0.3,0.4,0.5,1.0; echo exit=$?
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=7 seeds=8 (1000..1007) cells=56
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.100              0.343  8                 0.000            1.000        0.000         -1,849.554       15,379,811.079
 0.200              0.687  8                 0.000            1.000        0.000         -3,229.693       27,842,908.468
 0.250              0.859  8                 0.000            1.000        0.000         -3,791.857       33,251,805.611
 0.300              1.030  8                 0.000            1.000        0.000         -4,286.803       38,249,139.232
 0.400              1.374  8                 0.000            0.375        0.625         -5,114.358       41,346,974.000
 0.500              1.717  8                 0.000            0.000        1.000         -6,858.466       41,346,974.000
 1.000              3.434  8                 0.000            0.000        1.000         -9,151.481       41,346,974.000
exit=0
$ python scripts/probe_boundary.py --workers 8 --ratios 0.325,0.35,0.375,0.4,0.425,0.45,0.475 --output output/probe-fine; echo exit=$?
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=7 seeds=8 (1000..1007) cells=56
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.325              1.116  8                 0.000            1.000        0.000         -4,512.369       40,530,431.239
 0.350              1.202  8                 0.000            0.750        0.250         -4,724.836       41,346,974.000
 0.375              1.288  8                 0.000            0.625        0.375         -4,925.198       41,346,974.000
 0.400              1.374  8                 0.000            0.375        0.625         -5,114.358       41,346,974.000
 0.425              1.460  8                 0.000            0.250        0.750         -5,302.277       41,346,974.000
 0.450              1.546  8                 0.000            0.375        0.625         -5,950.382       41,346,974.000
 0.475              1.631  8                 0.000            0.000        1.000         -6,454.812       41,346,974.000
exit=0
$ python run.py scenarios/calibrated-baseline.yaml; echo exit=$?
depeg-sim: scenario=calibrated-baseline seed=42 hash=0ef967d36e34
run: steps=7024 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
wrote: output/calibrated-baseline-42-0ef967d3
exit=0
$ python run.py scenarios/calibrated-stress.yaml; echo exit=$?
depeg-sim: scenario=calibrated-stress seed=42 hash=d7fe2f1626b8
run: steps=7225 terminated_by=peg_recovered max_depeg_bps=-1231.0 reserves_exhausted=False
wrote: output/calibrated-stress-42-d7fe2f16
exit=0
$ python run.py scenarios/soros-1992.yaml; echo exit=$?
depeg-sim: scenario=soros-1992 seed=42 hash=329eda7c2118
run: steps=9551 terminated_by=reserves_exhausted max_depeg_bps=-6332.2 reserves_exhausted=True
wrote: output/soros-1992-42-329eda7c
exit=0
$ python run.py scenarios/soros-1992-no-defense.yaml; echo exit=$?
depeg-sim: scenario=soros-1992-no-defense seed=42 hash=1badaed6cf4a
run: steps=7806 terminated_by=reserves_exhausted max_depeg_bps=-7800.9 reserves_exhausted=True
wrote: output/soros-1992-no-defense-42-1badaed6
exit=0
$ python scan1992.py  # scratch script, body below; 4.0..7.0 step 0.1 on soros-1992 via run_sweep
 multiple  ratio      terminated_by  steps_run  max_depeg_bps  defender_spent  redemption_paid_total  final_depeg_bps
      4.0    0.8          max_steps      14400       -2,260.2   100,703,325.0           62,876,446.0           -162.0
      4.1    0.9          max_steps      14400       -2,622.6   100,703,325.0           65,791,866.3           -161.7
      4.2    0.9          max_steps      14400       -2,962.3   100,703,325.0           70,786,696.0           -145.8
      4.3    0.9          max_steps      14400       -3,279.1   100,703,325.0           72,771,832.0           -144.3
      4.4    0.9          max_steps      14400       -3,571.9   100,703,325.0           71,312,138.9           -158.0
      4.5    1.0          max_steps      14400       -3,845.4   100,703,325.0           79,624,783.5           -163.6
      4.6    1.0          max_steps      14400       -4,098.5   100,703,325.0           88,097,659.2           -155.2
      4.7    1.0          max_steps      14400       -4,334.3   100,703,325.0           78,809,330.3           -150.9
      4.8    1.0          max_steps      14400       -4,553.5   100,703,325.0           85,261,812.9           -147.3
      4.9    1.0          max_steps      14400       -4,759.3   100,703,325.0           91,848,124.2           -152.2
      5.0    1.1          max_steps      14400       -4,950.8   100,703,325.0           98,470,204.0           -148.6
      5.1    1.1 reserves_exhausted      12676       -5,129.8   100,703,325.0          100,703,325.0           -146.9
      5.2    1.1 reserves_exhausted      13701       -5,298.4   100,703,325.0          100,703,325.0           -158.2
      5.3    1.1          max_steps      14400       -5,456.0   100,703,325.0           85,731,537.8           -157.2
      5.4    1.1          max_steps      14400       -5,604.4   100,703,325.0           89,879,662.0           -156.4
      5.5    1.2          max_steps      14400       -5,743.2   100,703,325.0           94,055,424.0           -146.0
      5.6    1.2          max_steps      14400       -5,874.8   100,703,325.0           98,209,648.9           -162.4
      5.7    1.2 reserves_exhausted       9662       -5,999.1   100,703,325.0          100,703,325.0           -147.1
      5.8    1.2 reserves_exhausted       9624       -6,116.6   100,703,325.0          100,703,325.0           -132.4
      5.9    1.2 reserves_exhausted       9587       -6,227.4   100,703,325.0          100,703,325.0           -122.2
      6.0    1.3 reserves_exhausted       9551       -6,332.2   100,703,325.0          100,703,325.0           -138.8
      6.1    1.3 reserves_exhausted       9518       -6,432.3   100,703,325.0          100,703,325.0           -133.8
      6.2    1.3 reserves_exhausted       9487       -6,527.7   100,703,325.0          100,703,325.0           -122.6
      6.3    1.3 reserves_exhausted       9455       -6,617.8   100,703,325.0          100,703,325.0           -146.6
      6.4    1.4 reserves_exhausted       9426       -6,704.5   100,703,325.0          100,703,325.0           -135.1
      6.5    1.4 reserves_exhausted       9396       -6,786.3   100,703,325.0          100,703,325.0           -129.3
      6.6    1.4 reserves_exhausted       9368       -6,864.7   100,703,325.0          100,703,325.0           -136.1
      6.7    1.4 reserves_exhausted       9342       -6,939.8   100,703,325.0          100,703,325.0           -149.6
      6.8    1.4 reserves_exhausted       9316       -7,011.3   100,703,325.0          100,703,325.0           -130.3
      6.9    1.5 reserves_exhausted       9292       -7,080.0   100,703,325.0          100,703,325.0           -137.4
      7.0    1.5 reserves_exhausted       9269       -7,145.8   100,703,325.0          100,703,325.0           -144.9
exit=0
$ python -m depeg_sim.sweep sweeps/usdc-2023-pace.yaml --workers 7; echo exit=$?
sweep: usdc-2023-pace cells=7 workers=7
wrote: output/usdc-2023-pace/sweep.parquet
exit=0
 pace  step_of_max_depeg  trough_h  gap_steps  max_depeg_bps terminated_by
0.001              10288     34.29        988   -5308.281718     max_steps
0.002               9488     31.63        188   -5768.512915     max_steps
0.005               8821     29.40        479   -6116.065373     max_steps
0.010               8525     28.42        775   -6260.451524     max_steps
0.020               8345     27.82        955   -6343.865406     max_steps
0.050               8213     27.38       1087   -6398.374966     max_steps
0.100               8162     27.21       1138   -6412.135695     max_steps
pick (min gap_steps): 0.002
$ python scripts/fit_depth.py --scenario scenarios/usdc-2023.yaml --workers 8 --output output/fit-replay  # diagnostic only
grid pass (target -1300 bps):
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
    1000000       -9,445.3     max_steps             0.0      33600
    2000000       -9,163.8     max_steps             0.0      33600
    5000000       -8,302.4     max_steps             0.0      33600
   10000000       -7,034.1     max_steps             0.0      33600
   20000000       -5,280.2     max_steps             0.0      33600
   50000000       -2,962.9     max_steps             0.0      33600
  100000000       -1,701.6     max_steps             0.0      33600
  200000000         -965.6     max_steps             0.0      33600
  500000000         -432.9     max_steps             0.0      33600

refine pass between 100,000,000 and 200,000,000:
 pool_depth  max_depeg_bps terminated_by  defender_spent  steps_run
  116666667       -1,489.8     max_steps             0.0      33600
  133333333       -1,324.7     max_steps             0.0      33600
  150000000       -1,206.7     max_steps             0.0      33600
  166666667       -1,110.6     max_steps             0.0      33600
  183333333       -1,031.0     max_steps             0.0      33600

D* = 133333333 (trough -1324.7 bps)
exit=0
$ python run.py scenarios/usdc-2023.yaml; echo exit=$?
depeg-sim: scenario=usdc-2023 seed=42 hash=73db527c8ddf
run: steps=33600 terminated_by=max_steps max_depeg_bps=-5768.5 reserves_exhausted=False
wrote: output/usdc-2023-42-73db527c
exit=0
```

CI on the implementation commit 486822f: `gh run list` → `completed success story 2.5: usdc march-2023 validation ci main push 37226427715 48s 2026-10-04T18:57:46Z`.

The 1992 re-scan script (scratch, not committed; it builds a `SweepSpec` and calls `run_sweep`):

```python
"""Story 2.5 AC 4: re-scan the soros-1992 attacker multiple 4.0..7.0 step 0.1 at the current D*."""
from pathlib import Path
import pandas as pd
from depeg_sim.experiments.sweep import SWEEP_PARQUET, LinkedAxis, SweepSpec, run_sweep

Q = 42_625_746  # Quantum's $10bn x s
R = 2 * 100_703_325  # budget + reserves
if __name__ == "__main__":
    ms = [round(4.0 + 0.1 * i, 1) for i in range(31)]
    spec = SweepSpec(version=1, name="scan-1992", base=Path("scenarios/soros-1992.yaml"),
        linked_axes=[LinkedAxis(name="capital", paths=["agents[type=attacker].capital"], values=[m * Q for m in ms])],
        seeds=[42])
    df = pd.read_parquet(run_sweep(spec, Path("output"), workers=8) / SWEEP_PARQUET)
    df["multiple"] = (df["capital"] / Q).round(1)
    df["ratio"] = (df["capital"] / R).round(3)
    cols = ["multiple", "ratio", "terminated_by", "steps_run", "max_depeg_bps", "defender_spent", "redemption_paid_total", "final_depeg_bps"]
    print(df[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
```

### Completion Notes List

**Net burn (AC 1).** DefiLlama CSV, total USDC supply at 00:00 UTC: 43,176,044,700
(2023-03-10) − 40,468,620,896 (2023-03-13) = **$2,707,423,804** → × s = **11,540,596**
model units (capital / (budget + reserves) = 0.064). The ADR-0019 amendment quoted
≈ $4.0B. That is the 11→15 March change used for redemption capacity, and it includes
post-backstop redemptions. I used the AC's 10→13 window and say so in SOURCES.md. The
$1.2B/h peak CEX outflow is stated as a cross-check (episode flow ≈ 2.3 peak hours). The
ratio-1.0 row (the attacker row's "design ratio" conversion, and "attacker / (budget +
reserves) = 1.0" in Ratios at a glance) is removed, with the removal explained under the
Attacker table.

**New D\* (AC 2):** **16,666,667 model units**, **`market_depth_multiple` 16.67**, **≈ $3.91B
per side** at `s`, against the Curve USDC leg's $234.6M (16.7×). That is ≈ 9% of USDC's
$43.2B supply on 10 March. Achieved trough −1253.2 bps. Rule unchanged, original grid, no
extension: 20M is the first at ≥ −1300 (−1061.3), 10M misses (−1962.2), and of the 5
refined points plus the bracket the closest is 16,666,667. In the calibrated scenarios
this looks physical. **But it is physical only because the calibrated AMM defender absorbs
most of the flow** (it spends 10.26M against the 11.54M attack at D\*); see finding (a).
Re-runs at D\*: calibrated-baseline `peg_recovered` (steps 7024, −1253.2);
calibrated-stress `peg_recovered` (steps 7225, −1231.0). Both recovered at single-venue
depth in 2.3 and both stayed broken at the 2.4 depth.

**F-06 (AC 3).** At the new D\* the deliverable reserves are 10,904,220 and the F-06
formula predicts the flip at nominal ratio **0.291**. Measured: 0.30 recovers 8/8, 0.40
3/8, 0.50 0/8. A finer pass (extra, same script) puts the 50% crossing between 0.375
(5/8) and 0.40 (3/8), so **≈ 0.39** (ratio_deliverable ≈ 1.33). The transition zone runs
0.35–0.475, much wider than F-03's near-step. **The formula no longer predicts the flip;
it is a lower bound.** Mechanism (F-03): at D\* the pool is shallow relative to the
attacker (capital/depth ≈ 4 at ratio 0.4), so the defender buys stable far below par and
its budget absorbs more stable than its face value. The far side is still `max_steps`
(stays broken) and nothing exhausts, so F-06's qualitative claim holds. Its formula needs
F-03's price adjustment at shallow depth.

**1992 (AC 4).** At D\* = 16,666,667 (depth : defense now 0.083): soros-1992
`reserves_exhausted` at step 9551, trough −6332.2 at step 3054, defender_spent 100,703,325
(gone by step 2,335), redemption_paid_total 100,703,325. soros-1992-no-defense
`reserves_exhausted` at 7806 (1,745 steps earlier), trough −7800.9 at 1391; it reaches
−1000 bps at step 614 vs 2225. Scan 4.0–7.0 step 0.1: **every multiple ≥ 5.7 (ratio 1.206)
exhausts. 5.1 and 5.2 also exhaust, but 5.3–5.6 stall at `max_steps`**, ending at −146
to −162 bps with 86–98M of 100.7M paid. **F-07 holds, and more strongly**: the dead zone
between the −100 bps defender trigger and the −200 bps widened spread is where every
non-exhausting run parks. At this depth it makes exhaustion non-monotone in attacker
size, since whether the last redemptions get through before the price settles in the dead
zone is path-dependent. The "5.3× flip" of 2.4 becomes "a band 5.1–5.7, clean from 5.7".
Defended runs show 1,593 `spread_changed` events (the known no-hysteresis chatter).

**Part B schema (AC 6).** Two fields, both default-absent; existing hashes unchanged
(soros-baseline still `2e09f431ce74`; the pinned calibrated and 1992 hashes and the
determinism tests pass unedited). `price_series_path` resolves against the scenario file
(via `load_scenario` validation context) and is stored absolute. The manifest records it
in `config` plus `price_series_sha256`. It enters `content_hash()` as the file's sha256,
not the path, so hashes don't depend on the machine. The sha256 is held in a pydantic
private attribute set by the validator, which is not a third schema field.
`PHASE_ORDER_VERSION` is 1. The only kernel/ file touched is `kernel/config.py`, which the
context names. The Dev Notes say "nothing in kernel/ changes", which conflicts with that;
only the data models changed.

**Replay (AC 8).** Timestamps (arithmetic in the YAML header; ET is EST before and EDT
after the 12 March DST change): attack step **8100** (22:00 ET 10 Mar), observed trough
step **9300** (07:00 UTC 11 Mar, also the CSV minimum, 0.86267), capacity change step
**25500** (09:00 ET 13 Mar), `max_steps` **33600** (12:00 ET 14 Mar). The series ends at
step 28500, so the last close holds for 17 h. **Fitted pace = 0.002** (trough at step
9488 = 31.6 h, +0.63 h vs observed; next best 0.005 at −1.33 h). Defender: `threshold_pct`
99.0, budget kept. Capacity schedule: 605.79 → 19,181.59 (reserves / 7,200) at 25500.
**Deviation from "calibrated-baseline parameters": `termination.peg_recovered` is
removed.** With the attack at step 8100 > `for_steps` 6900, the first pace scan ended
every run `peg_recovered` at step 6900 on the pre-attack calm (ADR-0010). That run is
discarded, and the band is measured from the timeseries instead. Replay:
`max_steps`, 33600 steps, trough −5768.5 bps, final −27.3, redemption_paid 11,516,914,
defender idle.

**Overlay (AC 9),** `output/usdc-2023-42-73db527c/validation_overlay.png`. One panel, x in
hours from the series start. The observed hourly closes (blue, dotted markers) are flat
until 27 h, dip to −1,373 at 31 h (annotated) and wobble between about −150 and −1,150
through Saturday. They settle near −400 from ~55 h, step up to about −100 at 70 h and
enter the band at 86 h. The simulated AMM price (black) falls almost vertically at the
"attack starts" marker to −5,769 at 31.6 h (annotated), then climbs back in a straight
line at the speed of redemption throughput. It meets the blue line at ~63 h and rides on
it, enters the band just after the "redemption capacity changes" marker at 85 h, and
holds −27 bps to 112 h. Band ±31 bps shaded; footer `hash=73db527c8ddf`.

**VALIDATION.md (AC 10)** (`docs/calibration/VALIDATION.md`):

| quantity | observed | simulated |
|---|---|---|
| trough depth | −1,373 bps | −5,769 bps |
| trough time | 31.0 h | 31.6 h (fitted) |
| at capacity change (85 h) | −36 bps | −52 bps |
| first in band after capacity change | 86.0 h | 85.3 h |
| last outside band | ≥ 95.0 h (censored: series ends at −45 bps) | 85.3 h |
| recovery vs capacity change | up into band within 1 h | up into band within 0.3 h (0.96M queue clears in ≈ 50 steps) |

What matches: trough timing (fitted, so not evidence); re-entry to the band within about
an hour of the bank reopening, through the right mechanism (queue clears when capacity
rises); the level from 63 h on (mostly the input showing through). What does not: trough
depth (4.2× too deep), the weekend shape (linear, throughput-driven rebound vs a fast,
news-driven one), and last-outside-band (not comparable, censored). Why: D\* was fitted with
an AMM defender that the replay correctly lacks; the arbitrageur's oracle is the observed
price, which pins the AMM to the input once they meet; and weekend capacity × weekend steps
(10.54M) ≈ the attack (11.54M).

**ADR:** [ADR-0020](../adr/0020-episode-flow-replay-and-capacity-schedule.md) (Proposed).

**Findings (new, for the dev manager to accept or reject):**

(a) *D\* is identified jointly with whatever absorbs the flow, and with the episode-sized
attacker it is physical only while the calibrated AMM defender stands in for the absorbers.*
Calibrated-baseline at D\* = $3.91B per side reproduces the trough. The replay, with no
issuer buying on AMMs (historically right), bottoms at −5,769 bps. The same fit on the
replay needs ≈ $31.3B per side (133,333,333; −1324.7 bps), ≈ 72% of USDC's supply. So the
answer to "is D\* physical now?" is **yes in the calibrated scenario, no in the faithful
replay**. The missing agent is a discount buyer who expects par (market makers, funds,
traders), and the calibrated "defender" budget has been playing that role. Refines F-05.

(b) *Driving the reference with the observed price of the asset itself makes the model
partly copy its input.* The arbitrageur trades toward an oracle that follows the observed
USDC price, so once the simulated price reaches the observed path the arbitrageur pins it
there (−45 … +64 bps from 63.3 h on). Validation statistics after that point are not
independent. A dollar reference (1.0) with a separate "market expectation" agent would
separate the two.

(c) *F-06's formula is a lower bound at shallow depth* (flip ≈ 0.39 vs 0.291 predicted;
F-03's price effect), and the transition widens (0.35–0.475).

(d) *F-07's dead zone makes the 1992 outcome non-monotone in attacker size at the new
depth* (5.1–5.2 exhaust, 5.3–5.6 don't, ≥ 5.7 do).

(e) *Most of the attack is redeemed during the weekend in the model.* 10.54M of 11.52M is
paid before the backstop at the calibrated capacity, so the backstop only clears a 0.96M
queue. In the real episode the price stayed 100–500 bps below peg all weekend. If that
was not unabsorbed flow, it was expectations, which the model doesn't have. Alternatively
the weekend channel was slower than the 11–15 March average used for capacity.

### File List

**Created:**
- `scenarios/usdc-2023.yaml`
- `sweeps/usdc-2023-pace.yaml`
- `docs/calibration/VALIDATION.md`
- `docs/adr/0020-episode-flow-replay-and-capacity-schedule.md`
- `tests/test_usdc_2023.py`

**Modified:**
- `src/depeg_sim/kernel/config.py` (`CapacityChange`, `capacity_schedule`, `price_series_path`, `content_hash`, `load_scenario` context)
- `src/depeg_sim/environment/price_process.py` (`from_series`, series path in `from_config`/`on_phase`)
- `src/depeg_sim/protocol/redemption.py` (capacity schedule, `capacity_changed`)
- `src/depeg_sim/experiments/runner.py`, `src/depeg_sim/experiments/writer.py` (interval to the environment; `price_series_sha256` in the manifest)
- `src/depeg_sim/analysis/charts.py` (`validation_comparison`, `plot_validation_overlay`)
- `scripts/probe_boundary.py` (deliverable reserves and the F-06 prediction)
- `scenarios/calibrated-baseline.yaml`, `scenarios/calibrated-stress.yaml`, `scenarios/soros-1992.yaml`, `scenarios/soros-1992-no-defense.yaml`
- `docs/calibration/SOURCES.md`
- `tests/test_calibrated_scenarios.py`, `tests/test_1992_scenarios.py`, `tests/test_config.py`, `tests/test_price_process.py`, `tests/test_redemption.py`
- `docs/stories/2-5-usdc-validation.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.4 review; Part A added per ADR-0019 amendment
- 2026-10-04: Implemented by Claude Code (Opus 5.5). Part A committed separately (net burn $2.71B; D* = 16,666,667 ≈ $3.91B/side); schema fields, series environment, capacity schedule; usdc-2023 replay (pace 0.002); overlay and VALIDATION.md; ADR-0020 Proposed. Status → review

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-04
**Outcome:** **APPROVE** ✅ — the replay fails validation, and that is the deliverable

### Summary

454 passed, ruff clean, CI run 37226493089 green. Baseline hash unchanged
(`2e09f431ce74`) despite two new schema fields. Reviewer re-ran the replay: −5,768.5 bps
at `max_steps`, identical; regenerated the overlay and inspected it. Part A re-anchored
the attacker correctly ($2.71B over 10–13 March, from the committed CSV) and re-fitted
D\* to a defensible $3.9B/side. Part B built the observed-series environment and the
capacity schedule cleanly.

Then the faithful replay — no AMM defender, because Circle didn't buy on AMMs — fell four
times further than the real market. The builder traced it: D\* was fitted with the
defender absorbing 89% of the attack, and nothing in the replay takes that role. The model
is missing the agent who bought USDC at $0.88 expecting $1.00 on Monday. That is **F-08**,
the most useful finding so far, and it changes Epic 2's scope.

### Rulings

- **ADR-0020: accepted.** All five decisions stand; `peg_recovered` dropped from the replay
  (pre-attack calm would count as recovery, ADR-0010); `threshold_pct 99` for schema parity.
- **Scope: Story 2.6 (par-expecting buyer) inserted; charts → 2.7; figures → 2.8;
  Epic 2 ends Oct 15.** Recorded in CHARTER.md's decision log for Tim's confirmation.
- **F-06 refinement** (flip at 0.39 not 0.29; F-03 price effect): recorded; 2.7's axis
  takes the price adjustment.
- **Duplicate ADR-0019:** my error; merged.

### Acceptance Criteria Coverage

| AC# | Status | Evidence |
|---|---|---|
| 1 | ✅ | Net burn $2,707,423,804 from CSV; ratio-1.0 row removed with note |
| 2 | ✅ | D\* 16,666,667 / 16.67 / $3.91B per side vs $234.6M leg; −1253.2 bps |
| 3 | ✅ | Probe: flip ≈ 0.39; formula now a lower bound |
| 4 | ✅ | 1992 re-run; flip no longer clean (5.1–5.2 exhaust, 5.3–5.6 stall, ≥5.7 exhaust) |
| 5 | ✅ | Part A commit `981d0ed` |
| 6–7 | ✅ | `price_series_path`, `capacity_schedule`, series sha256 in hash; interpolation and hash tests |
| 8 | ✅ | `usdc-2023.yaml` with timestamp arithmetic; pace 0.002 by scan rule; defender inactive |
| 9 | ✅ | `plot_validation_overlay` (reviewer inspected) |
| 10 | ✅ | `VALIDATION.md` with the comparison table; matches/doesn't/why |
| 11 | ✅ | `tests/test_usdc_2023.py` |
| 12 | ✅ | ADR-0020; findings in Completion Notes |
| 13 | ✅ | `454 passed`; CI green |

**13 of 13 ACs met.**

### Key Findings

- **F-08** (missing par-expecting buyer): the replay result.
- **[LOW-1]** Post-63 h agreement is the oracle following the input; VALIDATION.md says
  so. Any future "recovery matches" claim must exclude that window.
- **[LOW-2]** The 1992 flip's non-monotonicity (exhaust / stall / exhaust across 5.1–5.7×)
  is the F-07 dead zone interacting with pace; not worth chasing before 2.6.

### Learnings for Story 2.6

- Back-solve the buyer's capital from the replay with D\* held; one parameter, one
  observation.
- The buyer is a holder-family agent with the opposite sign to the spec's panic-seller;
  reuse the 1.7 agent pattern and tests.
- After 2.6, re-run calibrated-baseline and both 1992 scenarios with the buyer and see
  what moves.
- 2026-10-04: Senior review APPROVE; status set to done. ADR-0020 accepted; F-08 added; Story 2.6 (buyer agent) inserted into Epic 2.
