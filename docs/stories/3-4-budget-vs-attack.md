# Story 3.4: Budget Against Attack at a Deep Pool, and Pace Against Trigger

Status: done

## Story

As a **researcher**,
I want the price-defense boundary mapped against attack size at a pool too deep to crash, and the defender's pace separated from its trigger,
so that F-11's withdrawn clause is replaced by a tested one and F-13 names the right parameter.

## Acceptance Criteria

1. `sweeps/budget-x-attack-mc.yaml`: base `calibrated-baseline.yaml` with `overrides` for depth 2× D\* (`amm.reserve_stable`, `amm.reserve_reference` = 33,333,334; `agents[type=holder].capital` = 18,333,334) and `termination.peg_recovered.reference: oracle`; axes `agents[type=defender].budget ∈ {0.5, 1, 1.5, 2, 3} × 41,346,974` and `agents[type=attacker].capital ∈ {0.5, 0.8, 1.0, 1.5, 2.0} × 179,454,391`; 8 seeds from 1000; `max_steps` 18000; header states every number's origin and why 2× D\* (F-11 refinement: the price is lost there, not the clock)
2. `plot_budget_attack(sweep_dir) -> Path`: left, heatmap of **p(never re-enters)** (`1 − steps_to_first_band_entry_n / n`, the price-loss probability) over budget × attack with the 0.5 contour; right, the budget at each attack column's 0.5 crossing (linear interpolation; "not reached" marked) against attack on log–log, with slope-1 and slope-0 reference lines through the middle crossing and the least-squares slope in the legend; reads parquet + manifest
3. Completion Notes: the crossing budgets per attack; the slope; whether the crossing budget is proportional to attack size (slope ≈ 1), to what the attacker extracts from the pool (compute `attacker_pnl`-based extraction per cell and test that too), or to neither; one sentence for the note in the form "at a pool too deep to crash, holding the price against an attack of X needs a budget of ≈ Y·X (or ≈ Z regardless of X)"
4. `sweeps/pace-x-trigger-mc.yaml` (3.2 review ruling 3): base `calibrated-baseline.yaml`, oracle criterion, attacker at ratio 1.0; axes `agents[type=defender].spend_pace ∈ {0.05, 0.1, 0.2, 0.5}` × `agents[type=defender].threshold_pct ∈ {0.5, 1, 2, 4}` × `agents[type=attacker].pace ∈ {0.1, 0.02}`; 8 seeds; `max_steps` 18000
5. `plot_pace_trigger(sweep_dir) -> Path`: two heatmaps (one per attacker pace) of median time-to-parity in hours from run start over defender pace × trigger, "never" hatched, 37 h line; a third small panel of average price paid per stable (`defender_spent / defender_bought_stable`) over the same grid at attacker pace 0.1
6. Completion Notes for AC 4–5: does time-to-parity vary along pace, along trigger, or both; does the best defender pace move when the attacker's pace changes (hypothesis: the operative quantity is defender pace relative to attacker pace); one sentence restating F-13 with the right parameter named
7. A `Proposed` ADR covering both sweeps and their verdicts on the F-11 and F-13 hypotheses; finding candidates where the data supports them
8. Both figures registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [x] Budget × attack (AC: 1, 2, 3)
  - [x] Spec; run; chart; synthetic test; look and describe
  - [x] Commit separately: `story 3.4: budget x attack at 2x D*`
- [x] Pace × trigger (AC: 4, 5, 6)
  - [x] Spec; run; chart; test; look and describe
- [x] ADR, figures, close out (AC: 7, 8)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.4: budget vs attack and pace vs trigger`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.3 (Status: done)**

- Map actions by what they touch (price, reserves, budget), not by their names. Here:
  "price loss" is never-re-enters; "clock" is late re-entry; keep them apart in every
  table.
- Predictions below are predictions. 3.2 and 3.3 both inverted theirs.
- `base_axis` and `None` on an axis exist if needed; neither is needed here.

[Source: docs/stories/3-3-holder-exit-rule.md#Senior-Developer-Review, F-11 refinement, F-13, F-14]

### Why 2× D\* and why never-re-enters

The F-11 refinement showed D\* breaks on the clock and 2× D\* on the price. The budget ×
depth sweep at a fixed attack said the budget interval that decides 2× and 4× D\* is the
same, so the operative quantity at that attack was the budget itself. This sweep varies
the attack at fixed depth to see what the budget has to match. The metric is price loss
(never re-enters), which `steps_to_first_band_entry_n` gives directly, so the clock
cannot contaminate it.

### Predictions (to be checked)

- Budget × attack: the crossing budget rises with attack size but less than
  proportionally (slope between 0.3 and 0.7), because what the attacker extracts from a
  constant-product pool saturates at the pool's reference side as the attack grows.
- The crossing budget tracks extraction (`−attacker_pnl` in reference terms at the
  trough) more closely than attack size.
- Pace × trigger: time-to-parity varies mostly along pace; trigger matters only at 4%,
  where the defender starts after the attacker has already finished (then it is cheap and
  fast — the F-13 mechanism). At attacker pace 0.02 (a slower attack, 500 steps instead of
  50), the best defender pace moves down.
- Average price paid falls monotonically with slower pace at every trigger.

### Cost

25 cells × 8 seeds = 200 runs; 32 cells × 8 = 256 runs; ≤ 18,000 steps each. A few minutes
each on 10 workers. Report real times.

### References

- [Source: docs/epics.md#Story-3.4]
- [Source: docs/FINDINGS.md] — F-03, F-11 (+ refinement), F-13
- [Source: docs/adr/0023-reference-relative-recovery.md, 0025-defender-policy-comparison.md]
- [Source: sweeps/budget-x-depth-mc.yaml, policy-comparison-mc.yaml] — spec style

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-4-budget-vs-attack.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

Python 3.12.13 (uv venv). Sweeps on 10 workers (12 cores).

**Budget × attack** (AC 1):

```
$ time python -m depeg_sim.sweep sweeps/budget-x-attack-mc.yaml --mc --workers 10
sweep: budget-x-attack-mc cells=200 workers=10
wrote: output/budget-x-attack-mc/sweep.parquet
mc: budget-x-attack-mc grid_points=25 seeds=8 runs=200
wrote: output/budget-x-attack-mc/mc.parquet
real	0m58.802s
```

p(never re-enters), rows budget (× calibrated), columns attack (× resources). Every cell is
0 or 1, and the trough step is identical across seeds in every cell:

```
bx \ ax  0.5  0.8  1.0  1.5  2.0
0.5      0.0  1.0  1.0  1.0  1.0
1.0      0.0  1.0  1.0  1.0  1.0
1.5      0.0  0.0  1.0  1.0  1.0
2.0      0.0  0.0  0.0  1.0  1.0
3.0      0.0  0.0  0.0  0.0  1.0
```

p_stays_broken on the same grid (shown so the clock is visible and kept apart):

```
bx \ ax  0.5    0.8    1.0    1.5   2.0
0.5      1.000  1.000  1.000  1.00  1.0
1.0      0.125  1.000  1.000  1.00  1.0
1.5      0.000  1.000  1.000  1.00  1.0
2.0      0.000  0.000  0.375  1.00  1.0
3.0      0.000  0.125  0.125  0.25  1.0
```

Clock (median hours to first re-entry, seeds that re-enter): 0.5× attack at 0.5×/1× budget
re-enters at 49.1 h / 23.9 h, so the price is held and the 0.5× budget cell is lost on the
clock only. 1.5× budget / 0.8× attack: 42.5 h. 2× / 1.0×: 36.6 h. 3× / 1.5×: 19.1 h.

AC 3 extraction test (`python scripts/budget_attack_table.py output/budget-x-attack-mc`):

```
 attack      capital  crossing       budget   extraction         loss  B/cap B/extr B/loss
   0.5x   89,727,196 <    0.5x  not reached
   0.8x  143,563,513     1.25x   51,683,718   79,905,481   63,658,032  0.360  0.647  0.812
     1x  179,454,391     1.75x   72,357,204  100,035,879   79,418,512  0.403  0.723  0.911
   1.5x  269,181,586      2.5x  103,367,435  130,828,957  138,352,629  0.384  0.790  0.747
     2x  358,908,782 >      3x  not reached
crossing budget vs attack size  : log-log slope 1.08, budget/attack size 0.360..0.403 (spread 11%)
crossing budget vs extraction   : log-log slope 1.40, budget/extraction 0.647..0.790 (spread 20%)
crossing budget vs attacker loss: log-log slope 0.84, budget/attacker loss 0.747..0.911 (spread 20%)
```

Diagnostic fine probe, not committed. The spec is `sweeps/budget-x-attack-mc.yaml` with
`name: budget-x-attack-fine` and budget axis `[round(41346974 * k / 8) for k in 2..32]`
(0.25× to 4× in steps of 0.125×). 155 grid points × 8 seeds:

```
$ time python -m depeg_sim.sweep <scratch>/budget-x-attack-fine.yaml --mc --workers 10 --output output
mc: budget-x-attack-fine grid_points=155 seeds=8 runs=1240
real	5m12.047s
$ python scripts/budget_attack_table.py output/budget-x-attack-fine
 attack      capital  crossing       budget   extraction         loss  B/cap B/extr B/loss
   0.5x   89,727,196 <   0.25x  not reached
   0.8x  143,563,513      1.1x   45,481,672   75,089,086   68,474,427  0.317  0.606  0.664
     1x  179,454,391     1.56x   64,604,647   94,325,747   85,128,644  0.360  0.685  0.759
   1.5x  269,181,586     2.55x  105,582,452  134,580,139  134,601,447  0.392  0.785  0.784
     2x  358,908,782     3.19x  131,793,480  161,503,488  197,405,294  0.367  0.816  0.668
crossing budget vs attack size  : log-log slope 1.16, budget/attack size 0.317..0.392 (spread 21%)
crossing budget vs extraction   : log-log slope 1.39, budget/extraction 0.606..0.816 (spread 29%)
crossing budget vs attacker loss: log-log slope 1.00, budget/attacker loss 0.664..0.784 (spread 17%)
```

Absorption at the first holding budget (fine probe, means over seeds; shares of attack
capital):

```
attack  B      avg px  defender  holder  redemption  sum
0.5x    0.25x  0.406   0.284     0.534   0.121       0.94
0.8x    1.13x  0.520   0.623     0.260   0.076       0.96
1.0x    1.63x  0.520   0.720     0.189   0.061       0.97
1.5x    2.63x  0.483   0.835     0.112   0.040       0.99
2.0x    3.25x  0.432   0.867     0.087   0.030       0.98
```

**Pace × trigger** (AC 4):

```
$ time python -m depeg_sim.sweep sweeps/pace-x-trigger-mc.yaml --mc --workers 10
sweep: pace-x-trigger-mc cells=256 workers=10
wrote: output/pace-x-trigger-mc/sweep.parquet
mc: pace-x-trigger-mc grid_points=32 seeds=8 runs=256
wrote: output/pace-x-trigger-mc/mc.parquet
real	1m29.126s
```

Attacker pace 0.1. Median hours to first re-entry (rows defender pace, columns trigger
%), price paid, p_stays_broken. Trough-step spread is 0 in every cell:

```
hours      0.5   1.0   2.0   4.0   | price paid  0.5    1.0    2.0    4.0   | p_broken
0.05       0.4   0.4   0.9   1.3   |             0.264  0.264  0.264  0.262 | 0.000 x4
0.10      29.9  29.9  29.9  29.9   |             0.283  0.283  0.283  0.283 | 0.375 x4
0.20      48.2  48.2  48.2  48.2   |             0.323  0.323  0.323  0.323 | 1.000 x4
0.50      53.1  53.1  53.1  53.1   |             0.358  0.358  0.358  0.358 | 1.000 x4
```

p(never re-enters) = 0 everywhere at 0.1. Defender spend 0.95–0.96 of budget at pace 0.05,
1.000 elsewhere. Troughs −7,697 / −7,681 / −8,151 / −8,698 bps by pace, at steps 51 / 50 /
84 / 78.

Attacker pace 0.02: `steps_to_first_band_entry_n = 0` in all 32 × 8 = 128 runs (never
re-enters), p_stays_broken 1.000 everywhere. Price paid by defender pace 0.05 / 0.1 / 0.2 /
0.5: 0.406 / 0.546 / 0.640 / 0.678, identical across triggers. The whole budget is spent
in every cell. Troughs −9,440 … −9,727 bps at steps 301–337.

Diagnostic slow-defender probe, not committed. The spec is
`sweeps/pace-x-trigger-mc.yaml` with `name: pace-slow-attack-probe` and axes attacker
pace [0.02, 0.1] × defender spend_pace [0.0025, 0.005, 0.01, 0.02, 0.03] × threshold_pct
[1]:

```
real	0m13.661s
atk   def     re/n  hours   price  spent  p_broken  final_bps
0.02  0.0025  8/8    2.027  0.197  0.597  0.125     -7.3
0.02  0.005   8/8    1.997  0.243  0.797  0.125    -10.7
0.02  0.01    8/8    7.857  0.286  1.000  0.000     -9.1
0.02  0.02    8/8   47.077  0.302  1.000  1.000    -24.5
0.02  0.03    0/8      —    0.331  1.000  1.000   -264.0
0.10  0.0025  8/8    0.847  0.186  0.310  0.000      1.0
0.10  0.005   8/8    0.473  0.171  0.369  0.125    -13.3
0.10  0.01    8/8    0.390  0.177  0.479  0.000     -9.2
0.10  0.02    8/8    0.383  0.206  0.660  0.000    -18.9
0.10  0.03    8/8    0.377  0.231  0.796  0.125    -12.5
```

Disk note: the first attempt wrote the fine probe into the session's `/tmp` scratchpad
and filled the tmpfs quota (a 200-run sweep is about 2.1 GB of run directories). It was
deleted and re-run into the gitignored `output/`.

**make figures / guard / tests / lint:**

```
$ make figures WORKERS=10            # all eight sweeps in full, then every figure
sweep: budget-x-attack-mc cells=200 workers=10
mc: budget-x-attack-mc grid_points=25 seeds=8 runs=200
sweep: pace-x-trigger-mc cells=256 workers=10
mc: pace-x-trigger-mc grid_points=32 seeds=8 runs=256
drew: budget_attack.png <- sweeps/budget-x-attack-mc.yaml
drew: pace_trigger.png <- sweeps/pace-x-trigger-mc.yaml
wrote: 14 figures and docs/figures/manifest.json (commit 866111936b47)
make figures: wall time 689 s (10 workers)
```

That run drew at a dirty tree (`866111936b47-dirty`), so the code was committed
(`b2d02ec`, "story 3.4: pace x trigger sweep and chart") and the figures were re-drawn
from the same sweep outputs, whose spec hashes match, as in 3.3:

```
$ time python scripts/make_figures.py --workers 10
wrote: 14 figures and docs/figures/manifest.json (commit b2d02ecfc415)
real	0m7.576s
```

The 12 existing PNGs are byte-identical to the committed ones (`git status` shows no
change to them), including `time_to_parity.png` after the `_parity_grid` refactor.

```
$ pytest
616 passed in 10.11s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
91 files already formatted
exit=0
$ make figures-check
figures-check: ok, 14 figures match their sources
exit=0
$ git diff --stat f406757 -- src/depeg_sim/kernel src/depeg_sim/protocol scenarios
(empty)
PHASE_ORDER_VERSION = 1
```

### Completion Notes List

**AC 1–3: budget × attack at 2× D\*.**

- **Crossing budgets** (0.5 crossing of p(never re-enters), linear interpolation). Story
  grid: attack 0.5× → not reached (holds at the smallest budget, 0.5×); 0.8× → 1.25×;
  1.0× → 1.75×; 1.5× → 2.5×; 2.0× → not reached (> 3×). Every cell is 0/8 or 8/8, so each
  crossing is the midpoint of its bracket. Fine probe (0.125× steps): 0.5× → < 0.25×;
  0.8× → 1.10×; 1.0× → 1.56×; 1.5× → 2.55×; 2.0× → 3.19×.
- **Slope.** Log–log least squares against attack: **1.08** (story grid, 3 crossings) and
  1.16 (fine, 4 crossings). Budget/attack is 0.36–0.40 (grid) and 0.32–0.39 (fine), with
  no trend.
- **Which quantity it tracks: attack size.** Extraction (`capital + attacker_pnl`, the
  reference the attacker took out of the pool) gives slope 1.40 / 1.39, with
  budget/extraction rising monotonically 0.65 → 0.79 / 0.61 → 0.82. The Dev Notes'
  literal "`−attacker_pnl`" is the attacker's loss, not its extraction (judgment call,
  ADR-0027 §4). Tested too: slope 0.84 / 1.00, ratio spread 20% / 17%. It fits about as
  well as attack size, but it is an outcome of the budget (a bigger budget pays the
  attacker more), as is extraction, which also contains the defender's own spend.
  Attack size is the input the budget has to match. Mechanism: at the crossing, defender
  + holder + redemption absorb 96–99% of the attacker's stable (conservation, F-02/F-03).
  The holder and redemption are fixed amounts, so the defender's share rises with the
  attack, at an average price paid of 0.43–0.52.
- **F-11 sentence:** "At a pool too deep to crash, holding the price against an attack of
  X needs a budget of ≈ 0.36·X (0.32–0.39 over X = 0.8–2× resources); below X ≈ 0.5×
  resources the believers and redemption hold it without the defender."
- **Chart (`budget_attack.png`).** Left: a staircase heatmap, dark (lost) in the lower
  right and light (held) in the upper left. The orange 0.5 contour climbs one budget row
  per attack column from 0.5× to 1.5×, and the whole 0.5× attack column is light. The 2×
  column is dark to the top. Right: three crossings on a line lying on the dashed slope-1
  reference and far off the dotted slope-0 line. An open ▽ at 0.5× marks "holds at the
  smallest budget", an open △ at 2× marks "no budget in the grid holds", and the legend
  reads slope 1.08.

**AC 4–6: pace × trigger.**

- **Time-to-parity varies along pace only.** At attacker pace 0.1: 0.4 / 29.9 / 48.2 /
  53.1 h for defender pace 0.05 / 0.1 / 0.2 / 0.5, identical at triggers 0.5, 1, 2 and
  4%. The single exception is pace 0.05, where the 2% and 4% triggers take 0.9 and 1.3 h
  instead of 0.4. The attacker's first sale (10% of 179.5M into a 16.7M stable side) puts
  spot near 0.23 on step 50, so every trigger fires on the first step of the attack. The
  0.1 / 0.2 / 0.5 rows reproduce F-13's late-conservative / calibrated / early-aggressive
  times exactly, so the "late" in late-conservative was the pace.
- **Does the best pace move with the attacker's pace? Yes, roughly in proportion.** On
  the AC grid this can't be seen: at attacker pace 0.02 every one of the 128 runs never
  re-enters. The slow-defender probe shows it. Against 0.02, defender pace ≤ 0.005 is back
  in 2.0 h, 0.01 in 7.9 h, 0.02 in 47.1 h (clock), ≥ 0.03 never. Against 0.1 the
  corresponding steps are ≤ 0.05 in 0.4 h, 0.1 in 29.9 h, 0.2 in 48.2 h (clock). At half
  the attacker's pace the defender is back fast, at equal pace late, and at ≥ 1.5–2× it
  misses the deadline or loses the price. That supports the hypothesis that the operative
  quantity is defender pace relative to attacker pace. It is first-order, not exact (equal
  ratio gives 29.9 h against 47.1 h).
- **F-13 sentence:** "The defender that wins is the one that spends more slowly than the
  attacker sells: time to parity is set by the defender's spending pace relative to the
  attacker's selling pace, and the trigger does not matter, because a fast first dump
  crosses every trigger up to 4%."
- **New candidate (in ADR-0027).** The attacker's pace is a lever as large as its size:
  the same 1.0× attack sold five times more slowly beats every defender pace from 0.05
  to 0.5. The defender buys near par while stock is still coming, paying 0.41–0.68 per
  stable against 0.26–0.36.
- **Chart (`pace_trigger.png`).** Left (attacker 0.1): four horizontal bands, uniform
  across the trigger columns. The bottom row is near-white (0.4–1.3 h), 0.1 is mid-blue
  (29.9 h), and the 0.2 and 0.5 rows are dark and tagged "clock". The orange dashed 37 h
  line runs straight across between 0.1 and 0.2. Middle (attacker 0.02): every cell is
  hatched "never". Right: price paid, banded by pace, darkest at 0.5 (0.358) and
  lightest at 0.05 (0.262–0.264), with no change across triggers.

**Predictions checked.**

1. Crossing slope 0.3–0.7: **missed** (1.08 / 1.16).
2. Crossing tracks extraction more than attack: **missed** (attack slope ≈ 1 with a flat
   ratio; extraction slope 1.4 with a drifting ratio).
3. Time-to-parity varies mostly along pace: **held** (only along pace).
4. Trigger matters only at 4%, after the attacker has finished: **missed**. 4% is crossed
   by the first sale, and the trigger moves nothing beyond 0.9 h.
5. Best defender pace moves down at attacker pace 0.02: **held**, but visible only in the
   diagnostic probe. On the AC grid everything at 0.02 is "never".
6. Price paid falls monotonically with slower pace at every trigger: **held** on the AC
   grid at both attacker paces. In the probe it bottoms out at 0.005 and rises again at
   0.0025 (0.171 → 0.186, attacker pace 0.1).

**Judgment calls (ADR-0027, Proposed):** extraction = `capital + attacker_pnl` with the
loss variant tested too; `D_STAR` label constant; `loglog_slope` and `_parity_grid`
factored out of the 2.8 and 2.9 charts with no change to their output logic; diagnostics
run into `output/` and not committed as sweeps.

Constraints: no `kernel/`, `protocol/` or config changes. `PHASE_ORDER_VERSION` stays 1.
No scenario file was touched, so every scenario hash is unchanged (the guard confirms
this for every figure source).

### File List

**Created:**

- `sweeps/budget-x-attack-mc.yaml`
- `sweeps/pace-x-trigger-mc.yaml`
- `scripts/budget_attack_table.py`
- `docs/adr/0027-budget-vs-attack-and-pace-vs-trigger.md`
- `docs/figures/budget_attack.png`
- `docs/figures/pace_trigger.png`

**Modified:**

- `src/depeg_sim/analysis/charts.py` (`plot_budget_attack`, `plot_pace_trigger`,
  `p_never_reenters`, `loglog_slope`, `_parity_grid`, `D_STAR`)
- `scripts/make_figures.py`, `Makefile` (two figures, two sweeps)
- `docs/figures/README.md`, `docs/figures/manifest.json`, `docs/figures/*.png` (regenerated)
- `tests/test_charts.py`, `tests/test_sweep.py`, `tests/test_figures.py`
- `docs/stories/3-4-budget-vs-attack.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-06
**Outcome:** **APPROVE** ✅ — both hypotheses answered, both against the Dev Notes, both
with a mechanism.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest` → `616 passed in
49.07s`; `ruff check .` → `All checks passed!`; `ruff format --check .` → `91 files already
formatted`; `make figures-check` → ok, 14 figures. **Both sweeps re-run in full** (200 runs
7m29s; 256 runs 14m07s on 2 workers). `scripts/budget_attack_table.py` reproduces the
crossings (1.25× / 1.75× / 2.5×, two not reached), slope 1.08 vs attack, 1.40 vs
extraction, 0.84 vs loss. Pace × trigger grid reproduced cell for cell: 0.4 / 29.9 / 48.2 /
53.1 h by pace at every trigger (0.9 and 1.3 h at pace 0.05 for 2% and 4%); attacker pace
0.02 never re-enters in all 128 runs. Both charts read.

### Rulings

1. **ADR-0027 → Accepted (finding, amended).** Finding A → F-11 second refinement; finding B
   → F-13 refinement; the "how fast matters as much as how much" candidate is folded into
   F-13 rather than numbered separately.
2. **Extraction candidate** — the builder is right that `capital + attacker_pnl` is
   extraction and `−attacker_pnl` is the attacker's loss; my Dev Notes conflated them. Both
   tested; attack size is the only input among the three and the one that fits. Recorded.
3. **The slow-attack result is uncommitted.** The committed grid shows only "never" at
   attacker pace 0.02; the relative-pace finding (back in 2 h at half the attacker's pace,
   late at equal, never at 1.5–2×) lives in an 80-run diagnostic. Story 3.5 commits it as
   `sweeps/pace-ratio-mc.yaml` (defender pace {0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1}
   × attacker pace {0.02, 0.1}, trigger 1%, 8 seeds) with a one-panel line chart of
   time-to-parity against defender/attacker pace ratio. The note cites that, not the ADR's
   table.
4. **`D_STAR` chart constant** → accepted; label only.
5. **Session `/tmp` quota on Seoul** → not a repo problem; 3.5's REPRODUCIBILITY.md notes
   `TMPDIR` and that sweeps belong in `output/`.
6. **Price paid bottoms at pace 0.005 and rises at 0.0025** → recorded as a nuance; below
   the attacker's pace by 20× the defender is buying after the arbitrageur has already
   pulled the price back. Not pursued.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | spec with origins; 2× D\* via overrides; reproduced |
| 2 | ✅ | `plot_budget_attack`, p(never re-enters), crossing + slope lines |
| 3 | ✅ | crossings, slope 1.08, both candidates tested, F-11 sentence |
| 4 | ✅ | spec; 256 runs; reproduced |
| 5 | ✅ | `plot_pace_trigger`, three panels |
| 6 | ✅ | pace only; best pace moves with attacker pace (diagnostic); F-13 sentence |
| 7 | ✅ | ADR-0027 |
| 8 | ✅ | two figures registered; `make figures` 689 s; guard ok; 616 tests; CI green |

**8 of 8 ACs met.**

### Key Findings

- **F-11, second refinement:** at a pool too deep to crash the holding budget is
  proportional to the attack — ≈ 0.36× (0.32–0.39 over 0.8–2× resources), slope 1.08 —
  because the holder and redemption are fixed absorbers and the defender takes the rest at
  0.43–0.52 per stable. Below ≈ 0.5× resources the believers and redemption hold it alone.
- **F-13 refinement:** the trigger does nothing (every trigger up to 4% is crossed by the
  first dump); time-to-parity is set by the defender's spending pace relative to the
  attacker's selling pace — half the attacker's pace is back in hours, equal is back late,
  1.5–2× never. "Late-conservative" was the pace.
- Against a five-times-slower attack, every defender on the grid loses the price. The slow
  attacker is the harder one.

### Learnings for Story 3.5

- A committed grid that reads all-"never" is not the figure; commit the probe that shows
  the gradient.
- Three "outcome" candidates (extraction, loss, absorbed ratio) have now each looked like
  a predictor and turned out to be conservation. Inputs only, from here.

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.3 review
- 2026-10-06: Implemented by Claude Code (Opus 5.5): two sweeps, two charts, extraction table, ADR-0027 Proposed; Status: review
- 2026-10-06: Senior review APPROVE; ADR-0027 accepted (finding, amended); F-11 and F-13 refined; pace-ratio sweep → 3.5; Status done
