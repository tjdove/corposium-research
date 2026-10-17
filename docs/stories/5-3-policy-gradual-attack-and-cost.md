# Story 5.3: Policy Comparison Under a Gradual Attack, With a Cost of Discount

Status: review

## Story

As a **reader who runs a treasury desk**,
I want the defender policies compared under an attack that does not crash the price in one step, and judged on what the discount costs while it lasts as well as on when parity returns,
so that "spend slower than the attacker sells" is either shown to hold where it matters or dropped.

## Why

Referee §5.21–5.23: the policy sweep's attacker sells 10% of its stock in the first
12 seconds, so the price is near $0.23 before any trigger can bind ("triggers are inert"
is partly the shock design), and the model charges nothing for the time spent at a
discount, so a defender that waits and buys the bottom is rewarded by construction.

## Acceptance Criteria

1. **One new summary metric, `discount_bps_hours`**: Σ over steps of
   `max(0, −peg_deviation_bps) × (interval_seconds / 3600)`, i.e. the area between the
   venue price and par while below par, in bps·h, from the attack start to run end.
   Added to `SUMMARY_KEYS`, `summarize()`, and `mc.parquet` aggregates (mean, p05, p95).
   Every existing scenario's hash is unchanged (summary columns are not in the scenario
   hash; confirm with the pinned-hash tests). Document in `summary.py`'s docstring.
2. `sweeps/policy-comparison-gradual-mc.yaml`: the five policies of
   `policy-comparison-mc.yaml`, same three attack ratios, same 16 seeds, but attacker
   `pace` as a third axis over {0.1 (existing), 0.02, 0.01}. 5 × 3 × 3 × 16 = 720 runs.
3. `plot_policy_comparison` gains a pace facet (one row per attacker pace) and a fourth
   panel: **discount_bps_hours** (mean, p05–p95) per policy. `docs/figures/
   policy_comparison_gradual.png`; the existing `policy_comparison.png` is unchanged
   (its sweep is untouched).
4. `scripts/policy_table.py` gains `--sweep` to point at the new sweep and prints, per pace
   and ratio: time to parity, price paid, discount_bps_hours, P(never recovers), and
   **which policy minimises discount_bps_hours and which minimises time to parity** —
   two columns, so the reader sees when they disagree.
5. Trigger test: at pace 0.01, report the step at which each policy's trigger first
   binds and the price at that step, for the 1.0× ratio, seed 1000. One small table in
   VALIDATION.md or FINDINGS-ready notes (builder's choice of file; say which).
6. `docs/calibration/VALIDATION.md` or a new `docs/calibration/POLICY.md` (builder's
   choice; link it from the README): the tables, in the builder's words, numbers only.
7. Tests: metric unit test on a synthetic path (known area); sweep spec hash; figure
   renders from synthetic parquet. `pytest`, `ruff`, `make figures-check`.

## Tasks / Subtasks

- [x] `discount_bps_hours` metric (AC: 1)
- [x] Gradual sweep (AC: 2)
- [x] Figure and table (AC: 3, 4)
- [x] Trigger-binding table (AC: 5)
- [x] Write-up (AC: 6)
- [x] Tests, gates (AC: 7)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.3: policy under gradual attack`, push `story/5-3-policy-gradual-attack-and-cost`

## Dev Notes

### Learnings from Previous Story

- The policy sweep uses `base_axis` (ADR-0025); adding an attacker-pace axis is an
  ordinary `axes:` entry on top of it.
- `peg_deviation_bps` is the per-step column the summary already reads for
  `max_depeg_bps`; the integral is over the same series. Use the attack start step
  (first step the attacker sells) as the lower bound; document the choice.
- 720 runs at 18,000 steps: ~15 min on Seoul at 8 workers. Run once. Do not run under
  `/tmp` (REPRODUCIBILITY.md).
- F-13's refinement (3.4) already found pace ratio first-order and the trigger inert
  *at pace 0.1*. This story asks whether that survives at 0.01–0.02. Either answer is a
  result.

### Prediction (to be checked, not aimed at)

At pace 0.01 the triggers bind at different steps and the early-aggressive defender
buys above $0.90 before the attacker is a tenth done; it may still lose on
discount_bps_hours because it is dry when the attack is only beginning. The slow
defender's advantage on time-to-parity should shrink; on discount_bps_hours it may
reverse. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §5.21–5.23]
- [Source: docs/stories/3-2-defender-policy-comparison.md, 3-4-budget-attack.md]
- [Source: sweeps/policy-comparison-mc.yaml, src/depeg_sim/analysis/summary.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log

The sweep was run once, into `output/` (`output/policy-comparison-gradual-mc`, 720 run
directories with `events.jsonl` and `timeseries.parquet`), after the metric was in
`summary.py`:

```
$ time python -m depeg_sim.sweep sweeps/policy-comparison-gradual-mc.yaml --mc --workers 12
sweep: policy-comparison-gradual-mc cells=720 workers=12
wrote: output/policy-comparison-gradual-mc/sweep.parquet
mc: policy-comparison-gradual-mc grid_points=45 seeds=16 runs=720
wrote: output/policy-comparison-gradual-mc/mc.parquet

real	4m29.293s
user	50m20.204s
sys	0m22.978s
```

`python scripts/policy_table.py --sweep output/policy-comparison-gradual-mc`, the second
table (the first is transcribed into POLICY.md by a script that reads `table()`; nothing
is hand-copied):

```
which policy minimises discount_bps_hours, and which time to parity:
 attacker_pace  ratio      min_discount disc_bps_h min_time_to_parity ttp_h agree
          0.10    0.5 late-conservative      5,242  late-conservative   6.6   yes
          0.10    0.7 late-conservative     37,884  late-conservative  19.2   yes
          0.10    1.0 late-conservative     87,082  late-conservative  29.9   yes
          0.02    0.5 late-conservative    282,570  late-conservative  57.5   yes
          0.02    0.7 late-conservative    380,920               none   NaN     -
          0.02    1.0 late-conservative    428,725               none   NaN     -
          0.01    0.5 late-conservative    320,055               none   NaN     -
          0.01    0.7 late-conservative    409,817               none   NaN     -
          0.01    1.0 late-conservative    452,147               none   NaN     -
```

`python scripts/trigger_table.py`, then `--pace 0.02`, `--pace 0.1`, `--ratio 0.5`:

```
attacker pace 0.01, ratio 1, seed 1000
policy             trigger binds step     h    act price seen first buy at attacker sold trough bps trough step
---------------------------------------------------------------------------------------------------------------
calibrated             1.0         51  0.17    buy     0.8150       0.7584          1.0%   -9,798.3         457
early-aggressive       0.5         51  0.17    buy     0.8150       0.7584          1.0%   -9,801.5         454
late-conservative      2.0         51  0.17    buy     0.8150       0.7584          1.0%   -9,785.2         463
spread-only            1.0         51  0.17 spread     0.8150            -          1.0%   -9,851.2         427
no-defense            none      never     -      -          -            -             -   -9,850.8         427
attacker pace 0.02, ratio 1, seed 1000
policy             trigger binds step     h    act price seen first buy at attacker sold trough bps trough step
---------------------------------------------------------------------------------------------------------------
calibrated             1.0         51  0.17    buy     0.6770       0.6158          2.0%   -9,716.0         304
early-aggressive       0.5         51  0.17    buy     0.6770       0.6158          2.0%   -9,726.5         301
late-conservative      2.0         51  0.17    buy     0.6770       0.6158          2.0%   -9,669.8         310
spread-only            1.0         51  0.17 spread     0.6770            -          2.0%   -9,777.5         292
no-defense            none      never     -      -          -            -             -   -9,777.1         292
attacker pace 0.1, ratio 1, seed 1000
policy             trigger binds step     h    act price seen first buy at attacker sold trough bps trough step
---------------------------------------------------------------------------------------------------------------
calibrated             1.0         51  0.17    buy     0.2319       0.2707         10.0%   -8,151.2          84
early-aggressive       0.5         51  0.17    buy     0.2319       0.2780         10.0%   -8,698.1          78
late-conservative      2.0         51  0.17    buy     0.2319       0.1893         10.0%   -7,681.2          50
spread-only            1.0         51  0.17 spread     0.2319            -         10.0%   -9,496.9          60
no-defense            none      never     -      -          -            -             -   -9,496.9          60
attacker pace 0.01, ratio 0.5, seed 1000
policy             trigger binds step     h    act price seen first buy at attacker sold trough bps trough step
---------------------------------------------------------------------------------------------------------------
calibrated             1.0         51  0.17    buy     0.9004       0.8621          1.0%   -8,819.2         562
early-aggressive       0.5         51  0.17    buy     0.9004       0.8621          1.0%   -8,824.7         562
late-conservative      2.0         51  0.17    buy     0.9004       0.8621          1.0%   -8,796.9         565
spread-only            1.0         51  0.17 spread     0.9004            -          1.0%   -9,558.3         469
no-defense            none      never     -      -          -            -             -   -9,557.5         466
```

Checks on the sweep (one-off `python -c`, not committed):
- `policy_table.table()` at pace 0.1 equals the Story 3.2 table from
  `output/policy-comparison-mc` (`pd.testing.assert_frame_equal`). All 240 pace-0.1 runs
  equal the Story 3.2 runs on every shared summary column (`240 True`).
- The largest range over seeds within a cell: `discount_bps_hours` 0.0 / 297.4 / 1,964.9
  at pace 0.01 / 0.02 / 0.1. `max_depeg_bps` and `step_of_max_depeg` are 0 at every pace.
  `final_depeg_bps` is 0.0 / 187.4 / 170.5.

`time python scripts/make_figures.py --workers 12` (existing sweeps in `output/`, nothing
re-run):

```
real	0m33.834s
user	0m34.187s
sys	0m0.549s
```

`git status` afterwards: only `docs/figures/manifest.json` modified and
`policy_comparison_gradual.png` new, so the 23 existing PNGs are byte-identical.

`tests/test_reference_recovery.py::test_soros_baseline_summary_bytes_unchanged` failed
on the first `make test`, because the new key changes `summary.json`'s bytes. It is
re-pinned as in Story 3.8: the new sha256 is `d653c4764a8c…`, and with the
`discount_bps_hours` line removed the bytes hash to the old `be7d32669a8f…` (both
asserted).

Gates:

```
$ time make test
Required test coverage of 85% reached. Total coverage: 99.06%
991 passed in 192.37s (0:03:12)
$ make lint
All checks passed!
113 files already formatted
$ make figures-check
figures-check: ok, 24 figures match their sources (code_hash matches)
figures-check: ok, 6 fits match their inputs (script hashes match)
$ make note-check
note-check: WARNING: freeze: v0.9-freeze (76e7a1cf6a03) manifest has code_hash a0ae9594e7a4…, the working tree's has 84505b3b3a11…
note-check: ok: figures: 7 cited figures exist and are in the manifest
note-check: ok: cited: all 7 listed figures not marked † are cited; none of the 4 record-only figures is
note-check: ok: freeze: v0.9-freeze is 76e7a1cf6a03 (code differs, see warning)
note-check: ok: numbers: 8 fitted values quoted as their records round them
```

### Completion Notes List

- **AC 1.** The lower bound of `discount_bps_hours` is the attacker's first *executed*
  sale, not its configured `start_step`; the two coincide at step 50 in every run here.
  The metric is `None` with no attacker, or an attacker that never sells. Each recorded
  row is weighted `record_every` steps. No scenario hash changed (the pinned-hash tests
  pass). One pinned `summary.json` byte hash was re-pinned, as above.
- **AC 2.** Spec hash `712e3cd96851…`. The spec is the policy sweep plus the pace axis
  (`tests/test_policy_gradual.py` checks that nothing else differs).
- **AC 3.** `plot_policy_comparison` dispatches on the pace axis to
  `_plot_policy_by_pace`. The old figure's code path is untouched and
  `policy_comparison.png` is byte-identical. Time to parity in the faceted chart is the
  per-run median (`policy_cells`), not `time_to_parity_hours`. The latter needs one
  trough step per cell; that holds in this sweep, but under a gradual attack it need
  not.
- **AC 4.** `policy_table.py --sweep` adds `price_paid`, `disc_bps_h` and the
  two-minimiser table, with `agree` = yes / no / "-".
- **AC 5.** New `scripts/trigger_table.py` reads the sweep's own runs and reruns nothing.
  The table is in **`docs/calibration/POLICY.md`** (builder's choice). All four defenders
  act at step 51 at every pace and ratio checked.
- **AC 6.** New `docs/calibration/POLICY.md`, linked from the README. Its tables are
  generated from `policy_table.table()`.
- **Results, recorded before interpretation.**
  - At pace 0.02 and 0.01, no policy recovers at any ratio (P = 1.00).
  - Late-conservative minimises `discount_bps_hours` in all 9 cells, and time to parity
    in the 4 cells where anyone re-enters. The two measures never disagree in this sweep.
  - At pace 0.01, 1.0×, its margin over calibrated is 0.5%.
  - The triggers bind on the first sale everywhere.
- **Prediction.**
  - Triggers bind at different steps: wrong.
  - Early-aggressive buys above $0.90: no. Its first buy is at 0.862 (0.5×) or 0.758
    (1.0×), and its average price is 0.911 at 0.5×.
  - Early-aggressive loses on discount: yes, the largest discount of the buyers in all 9
    cells.
  - The slow defender's time-to-parity advantage shrinks: yes, from 11.7 h to 1.0 h
    where measurable.
  - The discount ranking may reverse: no.
- **Also changed:** the Makefile `SWEEPS` list (so `make figures` runs the new sweep),
  figure row 3b † in NOTE.md, a figures README row and caption, the figure count in
  `test_figures.py`.
- **ADR-0037 Proposed** (finding + interface). Index and FINDINGS.md not edited.
- New code hash `84505b3b3a11…`; note-check warns about the freeze, as expected.

### File List

- `src/depeg_sim/analysis/summary.py` (`discount_bps_hours`, `_attack_start`, docstring)
- `src/depeg_sim/experiments/mc.py` (`METRICS`, docstring)
- `src/depeg_sim/analysis/charts.py` (`POLICY_COMPARISON_GRADUAL`, `policy_cells`, `_plot_policy_by_pace`, dispatch)
- `sweeps/policy-comparison-gradual-mc.yaml` (new)
- `scripts/policy_table.py` (`--sweep`, price paid, discount, `winners`)
- `scripts/trigger_table.py` (new)
- `scripts/make_figures.py` (registry entry)
- `Makefile` (`SWEEPS`, header)
- `docs/figures/policy_comparison_gradual.png` (new), `docs/figures/manifest.json`
- `docs/figures/README.md`, `docs/NOTE.md` (figure list row 3b †, change log), `README.md` (link)
- `docs/calibration/POLICY.md` (new)
- `docs/adr/0037-policy-gradual-attack-and-cost.md` (new, Proposed)
- `tests/test_summary.py`, `tests/test_policy_gradual.py` (new), `tests/test_figures.py`, `tests/test_reference_recovery.py`
- `docs/stories/5-3-policy-gradual-attack-and-cost.md`

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
- 2026-10-16: Implemented by Claude Code (Opus 5.5): `discount_bps_hours`, the 720-run gradual policy sweep, a pace-faceted policy figure with a discount panel, `policy_table.py --sweep`, `trigger_table.py`, POLICY.md, ADR-0037 proposed. Against 2%/1%-per-step attackers no policy recovers; every trigger binds on the first sale; late-conservative still has the smallest discount in every cell (by 0.5% at pace 0.01, 1.0×). Status: review.
