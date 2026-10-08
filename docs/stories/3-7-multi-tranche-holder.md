# Story 3.7 (stretch): Multi-Tranche Holder

Status: done

## Story

As a **researcher**,
I want the believers to enter at a spread of prices rather than one,
so that the note can say whether F-09's cliff becomes a curve and how close a buyer with a distribution of entry prices gets to the observed trough.

## Acceptance Criteria

1. `HolderConfig` gains `tranches: list[Tranche] | None = None` with `Tranche(entry_discount_pct: float ge 0, share: float gt 0 le 1)`, shares summing to 1 within 1e-9 (validator), entry discounts strictly increasing (validator); when set, `entry_discount_pct` must be absent (validator names the rule); every existing scenario `content_hash()` unchanged; `Holder` with tranches keeps one reference balance per tranche (`capital × share`), applies the fill-price cap per tranche against that tranche's entry price, and the redeem / exit rules unchanged on the pooled stable; rule names unchanged; decision record gains `tranche` where a buy came from
2. Tests: three tranches, price steps down through each entry — each tranche buys only below its own entry and only from its own share; a single tranche at share 1 is byte-identical to the scalar form on `usdc-2023.yaml` (test); validators
3. `scripts/fit_holder.py` gains `--tranches` taking `entry:share,…` and fits total capital `C*` by the unchanged two-pass rule; run it on `usdc-2023.yaml` for **three fixed ladders** (no tuning of the ladders; they are assumptions, stated): `A` = `1:0.5,2:0.3,5:0.2`; `B` = `2:0.25,5:0.25,10:0.25,20:0.25`; `C` = `1:0.2,2:0.2,5:0.2,10:0.2,15:0.2`; report `C*` in three units and the trough for each, with the single-entry 2.6/3.1 result as the baseline row
4. The fitted trough's distance from −1,373 for each ladder; the **cliff test**: for the best ladder, the trough at `C* × {0.8, 0.9, 1.0, 1.1, 1.2}` beside the single-entry values at the same multiples (from 2.6's refinement table) — a curve if the bimodal jump is gone
5. The best ladder (closest trough, ties to fewer tranches) becomes `scenarios/usdc-2023-tranches.yaml` (the replay file itself is untouched); replay run; overlay generated as `validation_overlay_usdc_2023_tranches.png`; VALIDATION.md gains a 3.7 row and a paragraph; SOURCES.md a tranche row (`assumption`)
6. Completion Notes: whether the cliff is gone, the best trough vs −1,373, whether trough timing moved, and one sentence for the note's limitations section (F-09 resolved, narrowed, or unchanged)
7. A `Proposed` ADR: tranche semantics, the three ladders and why those, the fit results, the cliff verdict
8. Figure registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [x] Tranche config and holder (AC: 1, 2)
  - [x] Commit separately: `story 3.7: holder tranches`
- [x] Fit three ladders (AC: 3, 4)
- [x] Best ladder scenario, overlay, docs (AC: 5)
- [x] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.7: multi-tranche holder and the cliff test`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.6 (Status: done)**

- One parameter fitted, everything else an assumption stated as such. Here the ladders are
  assumptions and `C*` is the one fitted number per ladder.
- Predictions below are predictions.
- The replay keeps `par` and the random-walk-free observed series; nothing from 3.6 touches
  it.

[Source: docs/stories/3-6-mean-reverting-reference.md#Senior-Developer-Review, F-09, ADR-0021, ADR-0024]

### Why ladders, not a fitted distribution

Fitting a distribution's shape to one observed trough is the hand-tuning the project has
refused since 2.4. Three fixed ladders bracket the plausible shapes (front-loaded,
uniform-wide, uniform-fine); if none lands closer than the single entry, that is the
answer. The ladder is the assumption; `C*` is the fit.

### Why the cap is per tranche

ADR-0024's fill-price cap stops the holder lifting the price above its entry. With several
entries, a 1% tranche must not lift the price above 0.99 while a 5% tranche is still
buying; each tranche caps against its own entry, from its own share of the reference.

### Predictions (to be checked)

- Ladder B or C lands within 5% of −1,373 (single entry: 17% short); A lands between.
- The cliff test shows a curve: trough changes by < 300 bps per 10% of `C*` for the best
  ladder, against the single entry's 7.5M → 10M jump of ≈ 2,000 bps.
- `C*` total for the best ladder is within 0.7–1.3× the single-entry 9,166,667.
- Trough timing moves by < 1 h.

### Cost

Three fits × ~17 runs of 33,600 steps: a few minutes each on 10 workers. One replay. The
cliff test: 10 runs.

### References

- [Source: docs/epics.md#Story-3.7]
- [Source: docs/FINDINGS.md] — F-08 confirmation, F-09, F-12
- [Source: docs/adr/0021-par-expecting-holder.md, 0024-holder-fill-price-limit.md]
- [Source: scripts/fit_holder.py]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-7-multi-tranche-holder.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

All on Seoul (12 cores, Python 3.12.13, `.venv`), 2026-10-07.

**AC 1/2: first commit `1552208` (`story 3.7: holder tranches`).** Every scenario hash
unchanged, computed with the pre-story code (`d97e51b`, in a worktree) and the new code
over all 12 scenario files including `scenarios/policies/`: `diff` → identical
(calibrated-baseline-ou 741f1bdd0012, calibrated-baseline 44ac03c60e5f, calibrated-stress
17b24b458e47, policies 2ea789dddc6c / e9c44d939fb2 / 36c6cd80fc72 / ba8301d92026,
soros-1992-no-defense 516edaef4795, soros-1992 f4e26ae66440, soros-baseline 2e09f431ce74,
soros-volatile 84ad0b810807, usdc-2023 2c3aeaa9825d). `usdc-2023.yaml` is untouched.

Old code vs new, `run.py --no-chart` on the five holder scenarios (usdc-2023,
calibrated-baseline, calibrated-stress, soros-1992, soros-1992-no-defense): every run
file byte-identical (timeseries, summary, events, checkpoints); the manifest's `config`
gains `"tranches": null` on the holder, as 3.6's κ field did.

Single tranche at share 1 vs the scalar form, new code, full 33,600-step replay
(`test_single_tranche_is_byte_identical_to_the_scalar_form_on_the_replay`): timeseries,
checkpoints and events (after the `run_started` line, which carries the config hash)
byte-identical; `summary.json` equal except `scenario_hash`; trough −1,137.8 bps.
With decisions traced (9,000 steps), `decisions.jsonl` is byte-identical too.

**AC 3: the three fits** (`python scripts/fit_holder.py --workers 10 --tranches <ladder>`;
each fit ≈ 10 s wall):

```
fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 tranches=1:0.5,2:0.3,5:0.2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,452.0               9524     max_steps      33600
        2000000       -5,103.1               9560     max_steps      33600
        5000000       -3,757.2               9683     max_steps      33600
       10000000         -945.1              10982     max_steps      33600
       20000000         -202.1               9359     max_steps      33600
       50000000         -126.5               8113     max_steps      33600
      100000000         -126.5               8113     max_steps      33600

refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -2,109.0               9800     max_steps      33600
       10000000         -945.1              10982     max_steps      33600
       12500000         -501.4               9553     max_steps      33600
       15000000         -207.2               8736     max_steps      33600
       17500000         -204.6               8956     max_steps      33600

refine pass 2 between 7,500,000 and 12,500,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        8333333       -1,602.7               9831     max_steps      33600
        9166667       -1,136.9              10280     max_steps      33600
       10000000         -945.1              10982     max_steps      33600
       10833333         -504.3               8980     max_steps      33600
       11666667         -502.9               9189     max_steps      33600

C* = 8333333 (trough -1602.7 bps) ≈ $1,954,999,922 at s = 0.0042625746 units/$

fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 tranches=2:0.25,5:0.25,10:0.25,20:0.25 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,420.1               9527     max_steps      33600
        2000000       -5,033.8               9569     max_steps      33600
        5000000       -3,500.1               9704     max_steps      33600
       10000000       -1,858.6               9815     max_steps      33600
       20000000         -702.1              11625     max_steps      33600
       50000000         -225.9               8117     max_steps      33600
      100000000         -225.9               8117     max_steps      33600

refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -2,005.0               8788     max_steps      33600
       10000000       -1,858.6               9815     max_steps      33600
       12500000       -1,007.2               8686     max_steps      33600
       15000000       -1,004.7               8900     max_steps      33600
       17500000       -1,002.1               9306     max_steps      33600

refine pass 2 between 10,000,000 and 15,000,000 (pick 12,500,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
       10833333       -1,323.3               9346     max_steps      33600
       11666667       -1,069.0              10352     max_steps      33600
       12500000       -1,007.2               8686     max_steps      33600
       13333333       -1,006.3               8759     max_steps      33600
       14166667       -1,005.3               8845     max_steps      33600

C* = 10833333 (trough -1323.3 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$

fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 tranches=1:0.2,2:0.2,5:0.2,10:0.2,15:0.2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,431.4               9527     max_steps      33600
        2000000       -5,059.6               9566     max_steps      33600
        5000000       -3,602.9               9695     max_steps      33600
       10000000       -1,489.0               9836     max_steps      33600
       20000000         -505.5               8852     max_steps      33600
       50000000         -202.1               9359     max_steps      33600
      100000000         -126.5               8113     max_steps      33600

refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -1,762.5               9821     max_steps      33600
       10000000       -1,489.0               9836     max_steps      33600
       12500000       -1,004.8               8898     max_steps      33600
       15000000       -1,001.8               9400     max_steps      33600
       17500000         -507.5               8697     max_steps      33600

refine pass 2 between 7,500,000 and 12,500,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        8333333       -1,504.5               8884     max_steps      33600
        9166667       -1,502.9               9100     max_steps      33600
       10000000       -1,489.0               9836     max_steps      33600
       10833333       -1,137.8              10277     max_steps      33600
       11666667       -1,005.6               8814     max_steps      33600

C* = 10000000 (trough -1489.0 bps) ≈ $2,346,000,000 at s = 0.0042625746 units/$

fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 tranches=2:0.25,5:0.25,10:0.25,20:0.25 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
cliff test at multiples of 10,833,333:
 holder_capital  multiple  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        8666666       0.8       -2,003.1               9019     max_steps      33600
        9750000       0.9       -2,000.8               9638     max_steps      33600
       10833333       1.0       -1,323.3               9346     max_steps      33600
       11916666       1.1       -1,007.8               8642     max_steps      33600
       13000000       1.2       -1,006.7               8728     max_steps      33600

fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 entry_discount_pct=2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
cliff test at multiples of 9,166,667:
 holder_capital  multiple  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7333334       0.8       -2,257.6               9790     max_steps      33600
        8250000       0.9       -1,662.3               9827     max_steps      33600
        9166667       1.0       -1,137.8              10269     max_steps      33600
       10083334       1.1         -885.1              11421     max_steps      33600
       11000000       1.2         -225.9               8117     max_steps      33600
```

Baseline row (Story 3.1 Debug Log, unchanged rule): single 2% entry, `C* = 9166667
(trough -1137.8 bps)` at step 10,269.

**AC 4: cliff test** — the two `--at-multiples-of` runs are the last two tables above
(6.7 s wall for both).

**AC 5: replay** (`python run.py scenarios/usdc-2023-tranches.yaml`):

```
depeg-sim: scenario=usdc-2023-tranches seed=42 hash=da3383d4e156
run: steps=33600 terminated_by=max_steps max_depeg_bps=-1323.3 reserves_exhausted=False
wrote: output/usdc-2023-tranches-42-da3383d4
real	0m3.047s
```

Holder at the end of the replay (scratch script reading the agent after the run):

```
holder bought=8,662,811 spent=8,140,168 pnl=522,643.2 redeemed pre85h=6,469,837 post=2,192,974; arb redeemed 2,853,889
  tranche 2%: spent 2,720,015  stable left 0  reference 2,776,956
  tranche 5%: spent 2,711,819  stable left 0  reference 2,858,875
  tranche 10%: spent 2,708,333  stable left 0  reference 3,011,812
  tranche 20%: spent 0  stable left 0  reference 2,708,333
validation_comparison: simulated_trough_bps -1323.27 at 31.15 h; at capacity change -52.15;
first in band after change 85.32 h; last outside band 85.32 h
(single entry, same script: holder bought 9,418,433 spent 9,209,072 pnl 209,360.4,
redeemed 6,487,405 / 2,931,028; arb 2,098,246; trough -1137.82 at 34.23 h)
```

Path: −1,000 bps first reached at step 8,569 (28.6 h); leaves the −1,005 tread at step
9,194 (30.6 h); agrees with the single-entry replay to 0.05 bps from step 14,575 (48.6 h).

**AC 8: figures, guard, tests, lint.** `make figures` (12 workers; run after commit
`b1352c8`, which registers the figure):

```
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 136 s
sweep sweeps/threshold-surface-mc.yaml: wall time 144 s
sweep sweeps/budget-x-depth-mc.yaml: wall time 49 s
sweep sweeps/oracle-lag-mc.yaml: wall time 112 s
sweep sweeps/policy-comparison-mc.yaml: wall time 78 s
sweep sweeps/holder-exit-1992-mc.yaml: wall time 18 s
sweep sweeps/budget-x-attack-mc.yaml: wall time 56 s
sweep sweeps/pace-x-trigger-mc.yaml: wall time 90 s
sweep sweeps/pace-ratio-mc.yaml: wall time 22 s
sweep sweeps/threshold-surface-ou-mc.yaml: wall time 128 s
drew: validation_overlay_usdc_2023_tranches.png <- scenarios/usdc-2023-tranches.yaml
(… 17 other "drew:" lines …)
wrote: 18 figures and docs/figures/manifest.json (commit b1352c88a05e, code_hash e05b66d6ccd0)
make figures: wall time 843 s (12 workers)
exit=0
```

(The old-vs-new comparison runs above overlapped the first sweep by about 20 s of CPU.)
The 17 existing PNGs were redrawn byte-identical (`git status` shows only the manifest and
the new PNG).

```
$ make figures-check
figures-check: ok, 18 figures match their sources (code_hash matches)
exit=0
$ pytest
818 passed in 20.70s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
94 files already formatted
exit=0
$ make test   (coverage gate, protocol/ + agents/)
TOTAL                                    840      8    99%
Required test coverage of 85% reached. Total coverage: 99.05%
818 passed in 37.14s
```

### Completion Notes List

**Per-ladder fit** (C\* in units / $ at s / × attacker episode net burn 11,540,596):

| ladder | C\* | trough at C\* | distance from −1,373 | trough time |
|---|---|---|---|---|
| single 2% (2.6/3.1) | 9,166,667 / $2.15B / 0.79× | −1,137.8 | +235.2 bps (17.1%) | step 10,269 (34.2 h) |
| A 1:0.5,2:0.3,5:0.2 | 8,333,333 / $1.95B / 0.72× | −1,602.7 | −229.7 bps (16.7%) | step 9,831 (32.8 h) |
| **B 2:0.25,5:0.25,10:0.25,20:0.25** | **10,833,333 / $2.54B / 0.94×** | **−1,323.3** | **+49.7 bps (3.6%)** | **step 9,346 (31.2 h)** |
| C 1:0.2,2:0.2,5:0.2,10:0.2,15:0.2 | 10,000,000 / $2.35B / 0.87× | −1,489.0 | −116.0 bps (8.4%) | step 9,836 (32.8 h) |

Best ladder: **B** (closest trough; no tie).

**Cliff test.** 2.6's refinement table predates the 3.1 cap and has no points at these
multiples, so the single entry was re-run at its own `C* × m` with the current holder; the
2.6 points nearest each multiple are in VALIDATION.md beside them.

| m | B capital | B trough | single capital | single trough (3.1 holder) |
|---|---|---|---|---|
| 0.8 | 8,666,666 | −2,003.1 | 7,333,334 | −2,257.6 |
| 0.9 | 9,750,000 | −2,000.8 | 8,250,000 | −1,662.3 |
| 1.0 | 10,833,333 | −1,323.3 | 9,166,667 | −1,137.8 |
| 1.1 | 11,916,666 | −1,007.8 | 10,083,334 | −885.1 |
| 1.2 | 13,000,000 | −1,006.7 | 11,000,000 | −225.9 |

**Is the cliff gone? No — it becomes a staircase.** Over ±20% of C\* the trough range
halves (996 vs 2,032 bps), but the response is treads (flat at a tranche's entry price
while that tranche outlasts the attack: −2,000 at 0.8–0.9×, −1,007 at 1.1–1.2×) and
risers (where the shallower tranche runs out first and the attacker sets the trough).
Largest step per 10% of C\*: 677 bps (B, 0.9 → 1.0) vs 659 bps (single, 1.1 → 1.2).
Each riser is F-09's cliff at a quarter of the capital. C\* lies on the riser between the
10% and 20% treads: at the trough the 10% tranche has spent its whole 2.71M share and the
20% tranche has bought nothing.

**Best trough vs −1,373:** −1,323.3, 49.7 bps (3.6%) shallow, was 235.2 bps (17.1%).
**Trough timing moved:** 31.2 h (step 9,346) vs observed 31.0 h — 9 minutes late, where the
single entry was 3.2 h late. The ladder steps through its entries (−220, −510, −1,005 bps)
instead of holding −200 for 3.5 h; the 10% tranche runs out at ≈ 30.6 h. Pace not
re-fitted.

**Limitations sentence (F-09 narrowed, not resolved):** *With believers spread over four
entry prices the replay's trough comes within 4% of the observed depth and within ten
minutes of its timing, but depth still moves with believer capital in steps set by the
assumed entry prices, so the model matches March 2023's depth only to the spacing of a
ladder no public data pins down.*

**Predictions checked:**
- "B or C lands within 5% of −1,373": **held** — B 3.6% (C 8.4%). "A lands between":
  **held only nominally** — A is 16.7% off against the single entry's 17.1%, and on the
  other side (too deep).
- "Cliff test shows a curve: < 300 bps per 10% of C\*, against the single entry's ≈ 2,000
  jump": **missed.** B's largest step is 677 bps; it is a staircase, not a curve. The
  comparison number in the prediction is also stale: with the 3.1 cap the single entry's
  largest step at these multiples is 659 bps (the ≈ 2,000 jump was 7.5M → 10M in the
  uncapped 2.6 holder, 27% of C\*).
- "C\* total for the best ladder within 0.7–1.3× 9,166,667": **held** — 1.18×.
- "Trough timing moves by < 1 h": **missed, in the useful direction** — it moved 3.1 h
  earlier, from 34.2 h to 31.2 h (observed 31.0 h).

**Overlay** (`docs/figures/validation_overlay_usdc_2023_tranches.png`, its own figure):
the black line leaves 0 at 27 h and steps down a staircase — a short tread at ≈ −220, one
at ≈ −510 by 27.6 h, a long flat tread at −1,005 from 28.6 h to 30.6 h — then drops to
its trough, −1,323 at 31.2 h, 9 minutes after and 50 bps above the blue observed trough.
It bounces to ≈ −1,150, traces a shallow U drawn as a narrow band (down to −1,311 at
32.9 h, back to −1,180 by 34.4 h) while the blue line rebounds to −800 at 32 h and falls
to −1,164 at 34 h, meets the blue line at ≈ −955 at 36 h, and from there is the 3.1
figure (on the observed path to ≈ 45 h, flat −173 from 49 h to 69 h, into the band at
85 h).

**Judgment calls** (all in ADR-0030 §2; tests pin them): buys from every eligible tranche
in one step, deepest entry first, caps chained through the implied post-buy reserve;
redemption and exit proceeds credited pro rata to tranche stable; a single tranche's
book is the holder's own, so one tranche emits no `tranche` key and no per-tranche
snapshot (that is what makes the single-tranche run byte-identical including traced
decisions and checkpoints); with tranches, `exit_discount_pct` must exceed the deepest
tranche's discount; `Holder.entry_price` is the shallowest tranche's.

**Comparison source.** AC 4 says "single-entry values at the same multiples (from 2.6's
refinement table)". That table has no points at 0.8/0.9/1.1/1.2 × C\* and predates the
3.1 cap, so I re-ran the single entry at the exact multiples (`--at-multiples-of`, the
same code path as the fit) and show 2.6's nearest points beside them in VALIDATION.md.
Not a blocker; flagging so the reviewer can check the reading.

**Scope notes.** `fit_holder.py` gained `--at-multiples-of C` (no fit; runs `round(C × m)`
for the five multiples) so the cliff test is one reproducible command; sweep directory
names get a `-tranches-<entries>` suffix with `--tranches`. The propagated scenarios
(calibrated, 1992) keep the single entry; no ladder was carried into them.

**ADR:** [0030](../adr/0030-multi-tranche-holder-and-the-cliff.md), Proposed (finding).
Index not edited.

**Tests:** 818 passed (773 collected at `d97e51b`: +45); `ruff check .` and `ruff format --check .` clean; `make figures` 843 s; guard green. CI run [37714039078](https://github.com/tjdove/corposium-research/actions/runs/37714039078) on `70269a2`: `test` success (1 m 49 s), `figures-quick` success (20 m 0 s).

### File List

**Created:**
- `src/depeg_sim/kernel/config.py`: `Tranche` (new model in an existing file)
- `scenarios/usdc-2023-tranches.yaml`
- `tests/test_holder_tranches.py`
- `docs/adr/0030-multi-tranche-holder-and-the-cliff.md`
- `docs/figures/validation_overlay_usdc_2023_tranches.png`

**Modified:**
- `src/depeg_sim/kernel/config.py` (`HolderConfig.tranches`, validators, `content_hash`)
- `src/depeg_sim/agents/holder.py` (tranche books, chained per-tranche caps, pro-rata
  proceeds, `settle` override)
- `scripts/fit_holder.py` (`--tranches`, `--at-multiples-of`)
- `scripts/make_figures.py` (figure registered)
- `tests/test_holder.py` (the pre-3.1 test subclass overrides `_buys`, renamed from
  `_buy_amount`), `tests/test_holder_config.py`, `tests/test_reference_recovery.py`
  (new scenario pinned where added), `tests/test_figures.py` (18 figures),
  `tests/test_scripts.py`
- `docs/calibration/VALIDATION.md` (3.7 section), `docs/calibration/SOURCES.md` (tranche
  and capital rows), `docs/figures/README.md` (row, caption), `docs/figures/manifest.json`
  and regenerated PNGs, `docs/REPRODUCIBILITY.md`, `README.md` (figure counts, timings)
- `docs/stories/3-7-multi-tranche-holder.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-07
**Outcome:** **APPROVE** ✅ — the closest the model has come to March 2023, with the
assumption that got it there named as one.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest` → `818 passed`;
`ruff check .` → `All checks passed!`; `ruff format --check .` → `94 files already
formatted`; `make figures-check` → ok, 18 figures, code hash matches. `usdc-2023-tranches`
hash `da3383d4e156`, trough **−1,323.3 at 31.15 h** (observed −1,373.3 at 31.0 h);
`usdc-2023` unchanged at −1,137.8 / `2c3aeaa9825d`. **Ladder B fit re-run** (1m04s):
C\* = 10,833,333 by the same path (refine 2 between 10M and 15M). **Cliff test re-run**
at 1.0 / 1.1 / 1.2: −1,323.3 / −1,007.8 / −1,006.7, matching. Overlay read: the two
troughs sit on top of each other; the simulated descent is a staircase (−220, −510,
−1,005) where the observed hourly points pass through the same levels.

### Rulings

1. **ADR-0030 → Accepted (finding, amended).** The four judgment calls (equal-share buying
   across eligible tranches, proportional return of proceeds, single tranche writes no
   per-tranche fields, exit deeper than the deepest tranche) are accepted as pinned.
   Amendment: the cliff verdict is "staircase" and F-09 is **narrowed, not resolved** —
   the model matches March 2023's depth to the spacing of a ladder no public data pins
   down, which is the limitation sentence the builder wrote and the note will use.
2. **Re-running the single entry at exact multiples** instead of using 2.6's table
   (which predates the fill cap and has no points at those multiples) → correct; the
   comparison is like-for-like now.
3. **Which overlay the note shows.** Both, in §3, in this order: the single-entry overlay
   first (one fitted number, 17% short, the clean claim), then the ladder-B overlay (one
   fitted number plus an assumed four-step ladder, best of three fixed ladders, within 4%
   and nine minutes). The reader sees what one parameter buys and what an assumption adds.
   Added to NOTE.md's open decisions as a question for Tim: which of the two is the hero
   image on the README and the site page.
4. **Trough timing moved 3.1 h earlier to within 9 minutes** without re-fitting pace —
   the deeper tranches absorb later, so the trough arrives when the attacker's selling
   ends rather than when the single buyer runs dry. Recorded in the F-09 refinement as
   the mechanism; pace stays as fitted in 2.5.
5. **Ladder A on the too-deep side at the same distance as the single entry** —
   recorded; a front-loaded ladder behaves like the single entry.
6. **`--at-multiples-of` on `fit_holder.py`** → accepted; it is the reproducible form of
   the cliff test.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | `tranches` with validators; per-tranche cap; pooled stable; `tranche` in the decision record; hashes unchanged |
| 2 | ✅ | three-tranche test; single-tranche byte-identity on usdc-2023; validators |
| 3 | ✅ | three ladders, three fit tables; C\* in three units; B reproduced here |
| 4 | ✅ | cliff table at 0.8–1.2 vs single entry re-run at its own multiples; reproduced at 1.0–1.2 |
| 5 | ✅ | `usdc-2023-tranches.yaml`; replay; own overlay figure; VALIDATION 3.7 row; SOURCES assumption row |
| 6 | ✅ | verdict and limitations sentence |
| 7 | ✅ | ADR-0030 |
| 8 | ✅ | figure registered; `make figures` 843 s; guard ok; 818 tests; both CI jobs green (70269a2) |

**8 of 8 ACs met.**

### Key Findings

- **F-09 narrowed:** with believers at a ladder of entry prices (2/5/10/20%, equal shares)
  and one fitted total capital ($2.54B, 0.94× the attack), the replay comes within 3.6% of
  the observed depth and within nine minutes of its timing. The cliff becomes a
  staircase: depth sits at a tranche's entry while that tranche still has money and jumps
  when it runs out; the largest step is 677 bps per 10% of capital, about the single
  entry's 659, over a range half as wide. Depth is set by where the believers' money sits
  on the price ladder, and no public data says where that was.
- The single-entry and ladder results together make the validation claim honest in both
  directions: one parameter gets within 17%; one parameter plus a stated assumption gets
  within 4%.

### Learnings for Story 3.8

- An assumption that moves a result from 17% to 4% is an assumption to show, not to hide
  or to promote: both overlays, both captions.
- Timing results that improve without re-fitting are more convincing than depth results
  that improve with fitting; say which is which.

## Change Log

- 2026-10-07: Story drafted by dev manager after Story 3.6 review (second Epic 3 stretch story)
- 2026-10-07: Implemented (Claude Code, Opus 5.5). Tranche config and holder; three
  ladder fits (B best: C\* 10,833,333, −1,323.3 bps, 31.2 h); cliff test: a staircase, not a
  curve (F-09 narrowed); `usdc-2023-tranches.yaml`, replay, overlay figure; VALIDATION.md,
  SOURCES.md; ADR-0030 Proposed. Status → review
- 2026-10-07: Senior review APPROVE; ADR-0030 accepted (finding, amended); F-09 narrowed; both overlays in the note; Status done
