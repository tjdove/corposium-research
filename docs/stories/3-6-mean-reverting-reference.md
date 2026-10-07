# Story 3.6 (stretch): Mean-Reverting Reference

Status: done

## Story

As a **researcher**,
I want the calm reference price to revert to par the way an off-venue stablecoin price does,
so that the surface can be measured against par again and the note can say whether "D\* breaks on the clock" is the model or the random walk.

## Acceptance Criteria

1. `EnvironmentConfig` gains `mean_reversion_per_step: float = Field(default=0.0, ge=0, lt=1)`; when > 0 the per-step update becomes `log p ← log p + κ·(log base − log p) + σ·z` (κ = `mean_reversion_per_step`, σ = `volatility_per_step`, one `standard_normal` draw per step as now); κ = 0 reproduces the current random walk byte-for-byte (test); incompatible with `price_series_path` (validator names the rule); every existing scenario `content_hash()` unchanged
2. **Calibrate κ** from `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv`: `scripts/fit_reversion.py` fits an AR(1) on hourly log deviations from 1.0 (`x_{t+1} = φ x_t + ε`), converts to the 12-s step (`κ_step = 1 − φ^(1/300)`), prints φ, κ_step, the implied half-life in hours, and the stationary sd; a `--dry-run`; the result goes in SOURCES.md with status `fitted` and the caveat that 13 zero-volume hours and isolated prints inflate the calm series (SOURCES.md note)
3. `scenarios/calibrated-baseline-ou.yaml`: `calibrated-baseline.yaml` plus κ, header stating the fit; `python run.py` on it; `peg_recovered.reference` stays `par`
4. `sweeps/threshold-surface-ou-mc.yaml`: `threshold-surface-mc.yaml` (the par-criterion surface of 2.7) with the OU base; run; `plot_threshold_surface` and `plot_time_to_parity` on it; per-row 0.5 crossings beside the 2.7 (par, random walk) and 2.8 (oracle criterion) tables
5. Completion Notes answer: with a reference that reverts, does the par criterion still show D\* breaking on the clock (median re-entry after 37 h at ≥ 0.8× resources)? Does the above-par "stays broken" population (F-11: 68 runs ending > +31 bps) disappear? Do the ≥ 2× D\* rows still lose the price? One sentence on whether the oracle criterion (ADR-0023) is still needed for sweeps or was a workaround for the random walk
6. A `Proposed` ADR: the OU update, κ and its fit, what moved in the surface, and the verdict on F-04's root cause; a finding candidate if the clock result changes
7. Figures registered (`threshold_surface_ou.png`, `time_to_parity_ou.png`); `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [x] OU update and validator (AC: 1)
  - [x] Commit separately: `story 3.6: mean-reverting reference`
- [x] Fit κ and scenario (AC: 2, 3)
- [x] OU surface and charts (AC: 4)
- [x] Verdict, ADR, figures, close out (AC: 5, 6, 7)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.6: mean-reverting reference and OU surface`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.5 (Status: done)**

- The guard now warns on code changes; this story changes `environment/`, so `make
  figures` regenerates and the manifest's code hash moves — expected.
- Predictions below are predictions.

[Source: docs/stories/3-5-hardening-and-polish.md#Senior-Developer-Review, F-04 refinement, F-11 refinement]

### Why this story exists

F-04 (and its refinement from 2.7): the calm reference is a driftless random walk, so over
6,900 steps it wanders ≈ 26 bps — the band width — and a par criterion fails late
recoveries and counts above-par drift as "broken". 2.8 worked around it with the oracle
criterion. A real off-venue stablecoin price mean-reverts through redemption arbitrage.
This story puts that in, calibrated from the same calm series σ came from, and re-asks
the question the oracle criterion answered. If D\* still breaks on the clock under OU +
par, the clock result is the model's; if not, part of it was the random walk.

### The fit, and its caveat

The calm series is thin (Bitstamp; 13 zero-volume hours; isolated prints to 0.99636). An
AR(1) on 120 hourly points gives a rough φ; report its standard error. If φ is not
significantly below 1, say so — then the data cannot distinguish OU from a random walk at
this horizon and the story's answer is "undetermined from this series", which is still an
answer. Do not tune κ to make the surface look right.

### Predictions (to be checked)

- φ ≈ 0.7–0.9 hourly (half-life a few hours); κ_step ≈ 0.001–0.002; stationary sd ≈ 5–10
  bps, inside the band.
- With OU + par: the above-par population vanishes; ≤ 0.5× D\* back in time at every
  ratio; D\* still clock at ≥ 0.8× (median re-entry 42–56 h is the redemption channel,
  not the reference); ≥ 2× D\* still never re-enters at ≥ 0.8×.
- Verdict: the oracle criterion was a workaround, and both criteria now agree at
  calibrated scale; the note can use par throughout, which is simpler to explain.

### Cost

Surface 640 runs (≈ 2.5 min on 10 workers). Fit: seconds.

### References

- [Source: docs/epics.md#Story-3.6]
- [Source: docs/FINDINGS.md] — F-04 (+ refinement), F-11 (+ refinements)
- [Source: docs/adr/0023-reference-relative-recovery.md] — what this story re-tests
- [Source: docs/calibration/SOURCES.md#environment]
- [Source: src/depeg_sim/environment/price_process.py]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-6-mean-reverting-reference.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

All on Seoul (12 cores, Python 3.12.13, `.venv`), 2026-10-07.

**AC 1: byte-identity at κ = 0** (first commit `83c2c29`, `story 3.6: mean-reverting
reference`). Old code (`a0ee711`, in a worktree) against new, `run.py --no-chart`:

```
same soros-baseline-42-2e09f431/{timeseries.parquet,summary.json,events.jsonl,decisions.jsonl,checkpoints}
same soros-volatile-42-84ad0b81/{timeseries.parquet,summary.json,events.jsonl,decisions.jsonl,checkpoints}
same calibrated-baseline-42-44ac03c6/{timeseries.parquet,summary.json,events.jsonl,checkpoints}   (no decisions.jsonl: trace off)
manifest.json (minus created_utc), each run:  >    "mean_reversion_per_step": 0.0,
```

Every scenario hash unchanged (`content_hash()[:12]`): calibrated-baseline 44ac03c60e5f,
calibrated-stress 17b24b458e47, policies 2ea789dddc6c / e9c44d939fb2 / 36c6cd80fc72 /
ba8301d92026, soros-1992-no-defense 516edaef4795, soros-1992 f4e26ae66440, soros-baseline
2e09f431ce74, soros-volatile 84ad0b810807, usdc-2023 2c3aeaa9825d. The pinned
soros-baseline `summary.json` sha256 test (`f2428bdb…`) passes unchanged.

Process note: I committed `83c2c29` once with two failing tests (an existing test pinned the
`price_series_path` validator message, which I had reworded). I restored that message,
gave κ its own message, and amended the commit before pushing. The pushed `83c2c29` passes.

**AC 2: the fit**

```
$ python scripts/fit_reversion.py --dry-run
csv: data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv
model: x_t = ln(close_t), x_(t+1) = phi * x_t + e (least squares, no constant)
rule: significant if (phi - 1) / se < -1.95 (Dickey-Fuller 5%)
kappa_step = 1 - phi ** (1 / 300)  (interval 12 s)

$ python scripts/fit_reversion.py
csv: data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv  hourly points: 120  pairs: 119
deviation from 1.0: mean -3.37 bps, sd 5.01 bps
phi = 0.6123  se = 0.0728  95% CI [0.4696, 0.7549]
unit-root stat (phi - 1) / se = -5.33 (Dickey-Fuller 5% critical -1.95): significantly below 1
kappa_step = 0.00163402  (interval 12 s, 300 steps/h)
half_life_h = 1.413
stationary_sd_bps (data, sd(e) / sqrt(1 - phi^2)) = 6.07
stationary_sd_bps (model, sigma 3.086e-05 with kappa_step) = 5.40
```

Sensitivity (not used): an AR(1) with a constant gives φ = 0.433 ± 0.083 and intercept
−1.93e-4, i.e. reversion to the series mean (−3.4 bps), not to par.

**AC 3**

```
$ python run.py scenarios/calibrated-baseline-ou.yaml
depeg-sim: scenario=calibrated-baseline-ou seed=42 hash=741f1bdd0012
run: steps=7024 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
wrote: output/calibrated-baseline-ou-42-741f1bdd
```

The seed-42 summary matches calibrated-baseline to two decimals (7,024 steps; −1,253.19 bps;
final −19.88; first entry 37; sustained 74; defender spent 7,699,786.64). At the
calibrated attack the run ends at step 7,024, before κ has anything to correct.

**AC 4: the OU surface**

```
$ python -m depeg_sim.sweep sweeps/threshold-surface-ou-mc.yaml --mc --workers 12
sweep: threshold-surface-ou-mc cells=640 workers=12
wrote: output/threshold-surface-ou-mc/sweep.parquet
mc: threshold-surface-ou-mc grid_points=40 seeds=16 runs=640
wrote: output/threshold-surface-ou-mc/mc.parquet
wall 127 s
```

Analysis script (`<scratch>/s36_surface.py`): 2.8's script with the OU surface added as a
third column. All three surfaces are current code: the random-walk par and oracle outputs
are the ones `make figures` re-ran below. κ = 0 is byte-identical, so 3.6 cannot have
moved them.

```
par RW (2.7) p_stays_broken
ratio  0.3  0.4    0.5    0.6    0.8    1.0    1.2    1.5
0.25   0.0  0.0  0.000  0.000  0.000  0.000  0.125  0.188
0.50   0.0  0.0  0.000  0.188  0.375  0.562  0.562  0.500
1.00   0.0  0.0  0.375  0.562  1.000  1.000  1.000  1.000
2.00   0.0  0.0  0.500  1.000  1.000  1.000  1.000  1.000
4.00   0.0  0.0  0.000  0.500  1.000  1.000  1.000  1.000

oracle RW (2.8) p_stays_broken
0.25   0.062  0.062  0.062  0.062  0.062  0.000  0.00  0.00
0.50   0.000  0.000  0.062  0.000  0.188  0.188  0.25  0.25
1.00   0.062  0.000  0.062  0.188  1.000  1.000  1.00  1.00
2.00   0.000  0.000  0.125  1.000  1.000  1.000  1.00  1.00
4.00   0.000  0.000  0.000  0.125  1.000  1.000  1.00  1.00

par OU (3.6) p_stays_broken
0.25   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
0.50   0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
1.00   0.0  0.0  0.0  0.0  1.0  1.0  1.0  1.0
2.00   0.0  0.0  0.0  1.0  1.0  1.0  1.0  1.0
4.00   0.0  0.0  0.0  0.0  1.0  1.0  1.0  1.0

par OU (3.6) median hours from run start to first re-entry (NaN = never)
0.25   0.4  0.4   0.4   0.4   0.4   0.4   6.8  12.2
0.50   0.4  0.4   0.4   8.6  20.9  25.5  28.1  30.5
1.00   0.3  0.4  18.3  30.1  41.9  48.2  52.2  56.4
2.00   0.3  2.0  23.8  42.5   NaN   NaN   NaN   NaN
4.00   0.3  3.6   3.6  26.2   NaN   NaN   NaN   NaN
(max |difference| in median hours, OU vs RW par: 0.0000 h; OU vs RW oracle: 0.0400 h; same "never" cells)

per-row 0.5 crossing (nominal ratio): linear | logistic
   depth                    par RW (2.7)                 oracle RW (2.8)                    par OU (3.6)
  0.25xD   not reached (max 0.19) | 1.74  not reached (max 0.06) | -0.60    not reached (max 0.00) | n/a
   0.5xD                     0.93 | 1.20   not reached (max 0.25) | 1.77    not reached (max 0.00) | n/a
   1.0xD                     0.57 | 0.56                     0.68 | 0.65                     0.70 | 0.70
   2.0xD                     0.50 | 0.50                     0.54 | 0.52                     0.55 | 0.55
   4.0xD                     0.60 | 0.60                     0.69 | 0.62                     0.70 | 0.70

broken-run anatomy (runs not peg_recovered), final_depeg_bps vs par
    par RW (2.7): broken 279 | end > +31 bps  68 | end < -31 bps 168 | end in band  43 | never re-enter 168 | re-enter late (> step 11,100)  65
 oracle RW (2.8): broken 237 | end > +31 bps  31 | end < -31 bps 154 | end in band  52 | never re-enter 128 | re-enter late (> step 11,100)  80
    par OU (3.6): broken 208 | end > +31 bps   0 | end < -31 bps 128 | end in band  80 | never re-enter 128 | re-enter late (> step 11,100)  80

OU, ratio >= 0.8, terminated_by:     max_steps  peg_recovered
  0.25                                    0             64
  0.50                                    0             64
  1.00                                   64              0
  2.00                                   64              0
  4.00                                   64              0
OU, ratio >= 0.8, first re-entry step from run start: 1x D* median 15,053 (min 12,557, max 16,931)
OU, ratio 1.5, median final_depeg_bps: 0.25x -13.1, 0.5x -13.4, 1x -18.2, 2x -3,485.6, 4x -4,061.5
  (random-walk par and oracle at 1.5: 2x -3,485.6, 4x -4,061.5: identical)
```

The par RW and oracle RW crossings are identical to the 2.7 and 2.8 tables (ADR-0023 §4)
to two decimals, on current code.

**AC 7: `make figures`** (code commit `8c5fdf3`):

```
$ make figures WORKERS=12
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 140 s
sweep sweeps/threshold-surface-mc.yaml: wall time 130 s
sweep sweeps/budget-x-depth-mc.yaml: wall time 51 s
sweep sweeps/oracle-lag-mc.yaml: wall time 117 s
sweep sweeps/policy-comparison-mc.yaml: wall time 78 s
sweep sweeps/holder-exit-1992-mc.yaml: wall time 17 s
sweep sweeps/budget-x-attack-mc.yaml: wall time 58 s
sweep sweeps/pace-x-trigger-mc.yaml: wall time 90 s
sweep sweeps/pace-ratio-mc.yaml: wall time 23 s
sweep sweeps/threshold-surface-ou-mc.yaml: wall time 127 s
wrote: 17 figures and docs/figures/manifest.json (commit 8c5fdf39b707, code_hash 01754f98382a)
make figures: wall time 840 s (12 workers)
$ make figures-check
figures-check: ok, 17 figures match their sources (code_hash matches)
exit=0
$ make figures-quick WORKERS=12
... quick sweep: threshold-surface-ou-mc (17 s) ...
quick: ok, 17 figures drawn; wrote docs/figures/quick-ok only
make figures-quick: wall time 147 s (12 workers)
```

The 15 existing PNGs came out byte-identical (`git status`: only `manifest.json` modified
and the two new PNGs).

**Close-out**

```
$ make test
TOTAL                                    769      7    99%
Required test coverage of 85% reached. Total coverage: 99.09%
773 passed in 21.57s          (762 at the first commit; 745 before this story)
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
93 files already formatted
exit=0
$ make figures-check
figures-check: ok, 17 figures match their sources (code_hash matches)
exit=0
$ git diff --stat a0ee711 -- src/depeg_sim/kernel src/depeg_sim/protocol
 src/depeg_sim/kernel/config.py | 12 +++++++++++-
PHASE_ORDER_VERSION = 1
```

CI on `8c5fdf3`, run [37657607713](https://github.com/tjdove/corposium-research/actions/runs/37657607713):
`test` success, `figures-quick` success (`make figures-quick: wall time 1155 s (4 workers)`;
`quick sweep: threshold-surface-ou-mc (144 s)`). CI on the final commit runs after this file
is committed; its result is in the report to the dev manager.

### Completion Notes List

**Fit.** **φ = 0.6123 ± 0.0728** (hourly; 95% CI 0.470–0.755). It is significantly below 1
(unit-root statistic −5.33 against Dickey–Fuller 5% −1.95), so the result is not
"undetermined". **κ_step = 0.001634** (0.00163402 rounded to 4 s.f.); **half-life
1.41 h**; **stationary sd 5.40 bps** in the model (6.07 bps in the data). SOURCES.md row
added with status `fitted`, with the thin-book caveat. `fitted` was not in the SOURCES
status vocabulary, so I added a one-line definition; the vocabulary test now accepts it.

**Three-way crossings** (per-row 0.5, linear | logistic; current code):

| depth | par, random walk (2.7) | oracle, random walk (2.8) | par, OU (3.6) |
|---|---|---|---|
| 0.25× D\* | not reached (max 0.19) \| 1.74 | not reached (max 0.06) | not reached (max 0.00) |
| 0.5× D\* | 0.93 \| 1.20 | not reached (max 0.25) \| 1.77 | not reached (max 0.00) |
| 1× D\* | 0.57 \| 0.56 | 0.68 \| 0.65 | 0.70 \| 0.70 |
| 2× D\* | 0.50 \| 0.50 | 0.54 \| 0.52 | 0.55 \| 0.55 |
| 4× D\* | 0.60 \| 0.60 | 0.69 \| 0.62 | 0.70 \| 0.70 |

**AC 5 answers**

1. **Does par still show D\* breaking on the clock at ≥ 0.8×? Yes.** All 64 runs at
   1× D\*, ratio ≥ 0.8, re-enter the par band (first re-entry steps 12,557–16,931, median
   15,053), every one after step 11,100, and none recovers. Median hours 41.9 / 48.2 /
   52.2 / 56.4 at 0.8 / 1.0 / 1.2 / 1.5, identical to the random-walk surface. Median final
   deviation at 1.5 is −18 bps, in band. The clock is the model's, not the random walk's.
2. **Does the above-par population disappear? Yes: 68 → 0** runs ending above +31 bps.
   Its sibling goes too: runs that re-enter before the deadline and then drift out (46
   under the random-walk par surface, 29 under the oracle criterion) → 0. Every OU "broken" run is either
   never-re-entering (128) or late (80).
3. **Do ≥ 2× D\* still lose the price? Yes.** All 128 runs at 2× and 4× D\*, ratio ≥ 0.8,
   never re-enter. At 1.5 the final deviation is −3,486 / −4,062 bps, the same as both
   random-walk surfaces. 2× D\* at 0.6 is clock (42.5 h), as in 2.8.
4. **Is the oracle criterion still needed?** No: for calm-volatility sweeps it was a
   workaround for the random-walk reference. With a reference that reverts to par, the
   par criterion reproduces the oracle criterion's linear crossings to within 0.02 at
   every depth and gives a cleaner 0/1 surface. It may still be needed at stress
   volatility, which this story did not test.

**Predictions checked**

- φ ≈ 0.7–0.9, half-life a few hours: **missed.** φ = 0.61 (the CI's upper end, 0.75,
  reaches the range); half-life 1.4 h, faster than predicted.
- κ_step ≈ 0.001–0.002: **held** (0.00163).
- Stationary sd 5–10 bps, inside the band: **held** (5.4 model, 6.1 data).
- Above-par population vanishes: **held** (68 → 0).
- ≤ 0.5× D\* back in time at every ratio: **held.** p = 0 in all 16 cells; median re-entry
  ≤ 30.5 h.
- D\* still clock at ≥ 0.8×, median re-entry 42–56 h: **held** (41.9–56.4 h).
- ≥ 2× D\* never re-enters at ≥ 0.8×: **held** (128/128).
- Verdict "oracle was a workaround; both criteria agree": **held** for linear crossings
  (≤ 0.02). The logistic crossings differ by up to 0.08 (4× D\*: 0.70 vs 0.62), because
  the oracle surface keeps a few early-failing runs that OU + par does not.

**Not predicted.**
- Time to first re-entry does not depend on the reference at all: the median hours are
  identical to the random-walk par surface in all 40 cells.
- The OU surface is exactly 0 or 1 in every cell. The 2.8 oracle surface's residual 0.06–0.25
  at ≤ 0.5× D\* (29 early-failing runs) was also the random walk: an AMM tracking a moving
  reference against a stale oracle.

**Charts.**
- `threshold_surface_ou.png`, left: a two-colour heatmap. Pale everywhere except a dark
  block at 1× and 4× D\* from 0.8×, and at 2× D\* from 0.6×. The 0.5 contour steps around
  it, and every cell reads 0.00 or 1.00 ± 0.10. Right: the collapse test, with every point
  at p = 0 or 1; the logistic fit puts 0.5 at an absorbed ratio of 1.03. The heading names
  the OU reference and κ.
- `time_to_parity_ou.png`: hour by hour the same picture as `time_to_parity.png`. The
  dashed deadline outline encloses the 1× D\* row from 0.8× (41.9–56.4 h, "clock") and
  2× D\* at 0.6× (42.5 h). 2× and 4× D\* from 0.8× are hatched "never". The heading reads
  "OU reference, κ 0.001634/step".

**ADR-0029** (Proposed): the update, κ and its fit, what moved, and the verdict on F-04's
root cause. Finding candidate: the clock result does not change, which is the finding.
The wander was the random walk; the clock and the price are the model's; par can replace
the oracle criterion for calm sweeps.

**Judgment calls.**
- The context's "κ = 1 pins price to base" test against AC 1's `lt=1`: the config field
  is `lt=1` as the AC says. `ReferencePrice` accepts [0, 1], and the κ = 1 test runs at
  class level.
- The three existing tests that enumerate every scenario file now name
  `calibrated-baseline-ou` as added later and pinned in `test_calibrated_scenarios.py`.
  Their pinned hashes are untouched.
- Chart headings gain "OU reference, κ …" only when κ > 0. Existing figures are
  unchanged (all 15 PNGs byte-identical).
- README and REPRODUCIBILITY gain the new scenario, sweep and timings.

**Not done.** Stress volatility with κ (F-04's original case). At stress σ the OU
stationary sd would be ≈ 132 bps, still above the band, so this story does not answer it.

### File List

**Created:**

- `scripts/fit_reversion.py`
- `scenarios/calibrated-baseline-ou.yaml`
- `sweeps/threshold-surface-ou-mc.yaml`
- `docs/adr/0029-ou-reference-and-the-clock.md`
- `docs/figures/threshold_surface_ou.png`, `docs/figures/time_to_parity_ou.png`

**Modified:**

- `src/depeg_sim/kernel/config.py` (`mean_reversion_per_step`, validator, `content_hash`)
- `src/depeg_sim/environment/price_process.py` (OU branch)
- `src/depeg_sim/analysis/charts.py` (`_reversion` in two headings)
- `scripts/make_figures.py` (two figures), `Makefile` (OU sweep)
- `docs/calibration/SOURCES.md` (κ row, `fitted` status)
- `docs/figures/README.md`, `docs/figures/manifest.json`, `README.md`, `docs/REPRODUCIBILITY.md`
- `tests/test_price_process.py`, `tests/test_scripts.py`, `tests/test_calibrated_scenarios.py`,
  `tests/test_charts.py`, `tests/test_figures.py`, `tests/test_holder_config.py`,
  `tests/test_reference_recovery.py`
- `docs/stories/3-6-mean-reverting-reference.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-07
**Outcome:** **APPROVE** ✅ — F-04's root cause is fixed at source, and the clock result is
the model's own.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest` → `773 passed`;
`ruff check .` → `All checks passed!`; `ruff format --check .` → `93 files already
formatted`; `make figures-check` → ok, 17 figures, code hash matches. `fit_reversion.py`
→ φ = 0.6123, se 0.0728, CI [0.4696, 0.7549], unit-root −5.33, κ_step 0.00163402,
half-life 1.413 h, stationary sd 6.07 (data) / 5.40 (model) bps — identical.
`calibrated-baseline-ou` hash `741f1bdd0012`, `peg_recovered` at 7024, −1,253.2. **OU
surface slice** (D\* and 2× D\* at ratio {0.6, 0.8, 1.0}, 96 runs, 4m37s): D\* 0 / 1 / 1
(crossing between 0.6 and 0.8 — the 0.70), re-entry 30.1 / 41.9 / 48.2 h identical to the
random-walk surface, 2× D\* never from 0.8×. Both charts read.

### Rulings

1. **ADR-0029 → Accepted (finding, amended).** The amendment names what the story found
   and did not predict: time to first re-entry is identical in all 40 cells whether the
   reference wanders or reverts, so the clock at D\* is the redemption channel, full stop;
   and the OU surface is exactly 0/1 everywhere — the par criterion with a reverting
   reference is the sharpest of the three.
2. **F-04 → resolved.** Root cause (driftless random walk) confirmed and removed; the
   stationary sd (5.4 bps) sits well inside the 31 bps band. FINDINGS gets a resolution
   entry, not a new number.
3. **ADR-0023 (oracle criterion) → amended, not superseded.** It stays for stress
   volatility (not re-tested here) and for the replay (where the reference *is* the
   observed depeg). For calm sweeps it was a workaround.
4. **Criterion for the note:** every sweep figure the note uses reports **time to first
   re-entry**, which this story shows is criterion- and reference-independent; the "stays
   broken" probability is quoted from the OU + par surface. Figure 2 becomes
   `time_to_parity_ou.png`; `time_to_parity.png` stays in the record. The note explains one
   reference (reverting, calibrated) and one criterion (par). ADR-0023's oracle criterion
   is mentioned once, in methods, as the sensitivity check it now is.
5. **Prediction φ ≈ 0.7–0.9 missed (0.61, half-life 1.4 h)** — faster reversion than I
   guessed; the thin Bitstamp series may overstate it (SOURCES caveat stands). Immaterial
   to any result: both reversion rates put the stationary sd inside the band.
6. **κ = 1 test on `ReferencePrice` directly** — accepted; the context file's test idea
   contradicted AC 1's `lt=1`, and the builder chose the right reading.
7. **A commit pushed once with two failing tests, then amended before push** — the pushed
   commit passes; the Debug Log says so. Fine.
8. **CI run 37660256282 on d97e51b: both jobs green** — recorded here as asked.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | OU update; κ = 0 byte-identical; one draw per step; validator; hashes unchanged |
| 2 | ✅ | `fit_reversion.py` with se and unit-root test; SOURCES.md `fitted` row and status definition |
| 3 | ✅ | `calibrated-baseline-ou.yaml`, header, run, hash pinned |
| 4 | ✅ | OU surface; both charts; three-way crossings table; slice reproduced |
| 5 | ✅ | four answers with numbers |
| 6 | ✅ | ADR-0029 |
| 7 | ✅ | figures registered; `make figures` 840 s; guard ok; 773 tests; CI green |

**7 of 7 ACs met.**

### Key Findings

- **F-04 resolved:** with a reference that reverts to par at the rate the calm USDC series
  implies (half-life 1.4 h), the par criterion gives a clean 0/1 surface; the above-par
  "stays broken" population (68 runs) is gone; D\* still breaks on the clock at ≥ 0.8×
  (median re-entry 41.9–56.4 h, unchanged to the decimal); ≥ 2× D\* still loses the price.
- Time to first re-entry does not depend on the reference process at all. The clock is
  the redemption channel.

### Learnings for Story 3.7

- When a workaround and a fix both exist, run the fix and keep the workaround as the
  sensitivity check; don't carry two criteria into the note.
- Predictions on fitted parameters should carry a range wide enough to be wrong usefully;
  "a few hours" was the right shape, the number was not.

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.5 review (first Epic 3 stretch story)
- 2026-10-07: Implemented by Claude Code (Opus 5.5) on Seoul: OU reference (κ = 0 byte-identical), κ fitted (φ 0.6123 ± 0.0728), OU scenario and surface; the clock and the price survive, the wander was the random walk; Proposed ADR-0029; Status review
- 2026-10-07: Senior review APPROVE; ADR-0029 accepted (finding, amended); F-04 resolved; note uses OU + par; Status done
