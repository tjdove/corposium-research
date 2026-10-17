# Defender policies under a gradual attack (Story 5.3)

The question (referee §5.21–5.23) is whether F-13's "spend slower than the attacker sells"
holds when the attack does not crash the price in its first step, and when the policies
are also judged on what the discount costs while it lasts. In the Story 3.2 sweep the
attacker sells 10% of its stock in its first 12 s step, so spot is near 0.23 before any
trigger can act, and nothing in the model charged for the hours spent below par.

All numbers below come from one run of the sweep (720 runs, 4 min 29 s on Seoul with 12
workers; the command and its output are in the story's Debug Log).

## What was run

- **Metric** `discount_bps_hours` (`src/depeg_sim/analysis/summary.py`): the area
  between the venue price and par while below par, in bps·hours, from the attacker's
  first executed sale (step 50 in every run here) to the end of the run. For each recorded
  step it adds `max(0, −peg_deviation_bps) × 12 s / 3600`. It is always measured against
  par, whatever recovery criterion the run uses. It is in `SUMMARY_KEYS` and in
  `mc.parquet` (mean, std, p05, p50, p95). No scenario hash changed.
- **Sweep** `sweeps/policy-comparison-gradual-mc.yaml` (spec hash `712e3cd96851`). This is
  `policy-comparison-mc.yaml` with one more axis, the attacker's pace (the share of its
  remaining stable it sells each step) over {0.1, 0.02, 0.01}. The five policies, the
  attack ratios 0.5 / 0.7 / 1.0 × (defender budget + redemption reserves), seeds
  1000–1015, the 18,000-step (60 h) horizon and the oracle recovery criterion are all
  unchanged. 5 × 3 × 3 × 16 = 720 runs.
- **Tables** `python scripts/policy_table.py --sweep output/policy-comparison-gradual-mc`
  and `python scripts/trigger_table.py`. **Figure** `docs/figures/policy_comparison_gradual.png`.

Definitions, as in Story 3.2:
- **Time to parity:** the median over seeds of the hours from the start of the run to
  the first re-entry into ±31 bps of the oracle price. It is "never" when fewer than
  half the seeds re-enter.
- **Price paid:** the defender's spend divided by the stable it bought, averaged over
  seeds.
- **P(never recovers):** the share of runs that do not hold the band for 6,900 steps by
  the horizon.

## Results

The pace-0.1 rows reproduce the Story 3.2 sweep exactly. All 240 of its runs match the
Story 3.2 runs on every shared summary column (only the scenario name and hash differ).

The seeds barely move these numbers. At pace 0.01 every seed in a cell gives the same
result (the range over the 16 seeds is 0.0 for every metric above). The widest range of
`discount_bps_hours` within a cell is 297 bps·h at pace 0.02 and 1,965 at pace 0.1.

**Attacker pace 0.1.**

| policy | time to parity, h (0.5 / 0.7 / 1.0×) | re-entered (of 16) | price paid | discount, bps·h | P(never recovers) |
|---|---|---|---|---|---|
| calibrated | 18.3 / 37.1 / 48.2 | 16 / 16 / 16 | 0.574 / 0.442 / 0.323 | 34,191 / 129,491 / 208,755 | 0.06 / 0.88 / 1.00 |
| early-aggressive | 20.2 / 41.4 / 53.1 | 16 / 16 / 16 | 0.579 / 0.464 / 0.358 | 41,379 / 158,882 / 247,837 | 0.19 / 1.00 / 1.00 |
| late-conservative | 6.6 / 19.2 / 29.9 | 16 / 16 / 16 | 0.552 / 0.402 / 0.283 | 5,242 / 37,884 / 87,082 | 0.00 / 0.12 / 0.31 |
| spread-only | 50.4 / 55.7 / never | 16 / 16 / 1 | — / — / — | 223,009 / 265,144 / 304,496 | 1.00 / 1.00 / 1.00 |
| no-defense | 49.4 / 54.5 / 59.1 | 16 / 16 / 16 | — / — / — | 218,593 / 259,889 / 298,463 | 1.00 / 1.00 / 1.00 |

**Attacker pace 0.02.**

| policy | time to parity, h (0.5 / 0.7 / 1.0×) | re-entered (of 16) | price paid | discount, bps·h | P(never recovers) |
|---|---|---|---|---|---|
| calibrated | 58.5 / never / never | 16 / 0 / 0 | 0.834 / 0.748 / 0.640 | 291,050 / 390,109 / 436,307 | 1.00 / 1.00 / 1.00 |
| early-aggressive | 58.7 / never / never | 16 / 0 / 0 | 0.840 / 0.766 / 0.678 | 293,170 / 392,353 / 438,094 | 1.00 / 1.00 / 1.00 |
| late-conservative | 57.5 / never / never | 16 / 0 / 0 | 0.813 / 0.692 / 0.546 | 282,570 / 380,920 / 428,725 | 1.00 / 1.00 / 1.00 |
| spread-only | never / never / never | 0 / 0 / 0 | — / — / — | 394,998 / 427,518 / 451,981 | 1.00 / 1.00 / 1.00 |
| no-defense | never / never / never | 0 / 0 / 0 | — / — / — | 389,862 / 422,782 / 447,575 | 1.00 / 1.00 / 1.00 |

**Attacker pace 0.01.**

| policy | time to parity, h (0.5 / 0.7 / 1.0×) | re-entered (of 16) | price paid | discount, bps·h | P(never recovers) |
|---|---|---|---|---|---|
| calibrated | never / never / never | 0 / 0 / 0 | 0.908 / 0.856 / 0.784 | 322,503 / 412,467 / 454,494 | 1.00 / 1.00 / 1.00 |
| early-aggressive | never / never / never | 0 / 0 / 0 | 0.911 / 0.864 / 0.803 | 323,115 / 413,120 / 455,063 | 1.00 / 1.00 / 1.00 |
| late-conservative | never / never / never | 0 / 0 / 0 | 0.899 / 0.826 / 0.720 | 320,055 / 409,817 / 452,147 | 1.00 / 1.00 / 1.00 |
| spread-only | never / never / never | 0 / 0 / 0 | — / — / — | 420,473 / 448,794 / 469,616 | 1.00 / 1.00 / 1.00 |
| no-defense | never / never / never | 0 / 0 / 0 | — / — / — | 415,686 / 444,378 / 465,501 | 1.00 / 1.00 / 1.00 |

| attacker pace | ratio | minimises discount_bps_hours | bps·h | minimises time to parity | h | agree |
|---|---|---|---|---|---|---|
| 0.1 | 0.5 | late-conservative | 5,242 | late-conservative | 6.6 | yes |
| 0.1 | 0.7 | late-conservative | 37,884 | late-conservative | 19.2 | yes |
| 0.1 | 1 | late-conservative | 87,082 | late-conservative | 29.9 | yes |
| 0.02 | 0.5 | late-conservative | 282,570 | late-conservative | 57.5 | yes |
| 0.02 | 0.7 | late-conservative | 380,920 | none | never | - |
| 0.02 | 1 | late-conservative | 428,725 | none | never | - |
| 0.01 | 0.5 | late-conservative | 320,055 | none | never | - |
| 0.01 | 0.7 | late-conservative | 409,817 | none | never | - |
| 0.01 | 1 | late-conservative | 452,147 | none | never | - |
**Which policy minimises each measure** (`policy_table.py`, second table). A tie would
be printed as "a=b"; there are none. "none" means no policy re-enters.

| attacker pace | ratio | minimises discount_bps_hours | bps·h | minimises time to parity | h | agree |
|---|---|---|---|---|---|---|
| 0.1 | 0.5 | late-conservative | 5,242 | late-conservative | 6.6 | yes |
| 0.1 | 0.7 | late-conservative | 37,884 | late-conservative | 19.2 | yes |
| 0.1 | 1 | late-conservative | 87,082 | late-conservative | 29.9 | yes |
| 0.02 | 0.5 | late-conservative | 282,570 | late-conservative | 57.5 | yes |
| 0.02 | 0.7 | late-conservative | 380,920 | none | never | - |
| 0.02 | 1 | late-conservative | 428,725 | none | never | - |
| 0.01 | 0.5 | late-conservative | 320,055 | none | never | - |
| 0.01 | 0.7 | late-conservative | 409,817 | none | never | - |
| 0.01 | 1 | late-conservative | 452,147 | none | never | - |
## When the triggers bind (AC 5)

`python scripts/trigger_table.py` (pace 0.01, ratio 1.0, seed 1000; nothing is re-run;
it reads the sweep's per-run events and timeseries):
- **binds:** the step of the defender's first act, which is its first AMM buy, or its
  spread change for spread-only.
- **price seen:** the AMM price at the end of the step before, which is the price the
  trigger read.
- **attacker sold:** the share of the attacker's capital sold by then.

| policy | trigger | binds at step | h | act | price seen | first buy at | attacker sold | trough bps (step) |
|---|---|---|---|---|---|---|---|---|
| calibrated | 1.0% | 51 | 0.17 | buy | 0.8150 | 0.7584 | 1.0% | −9,798.3 (457) |
| early-aggressive | 0.5% | 51 | 0.17 | buy | 0.8150 | 0.7584 | 1.0% | −9,801.5 (454) |
| late-conservative | 2.0% | 51 | 0.17 | buy | 0.8150 | 0.7584 | 1.0% | −9,785.2 (463) |
| spread-only | 1.0% | 51 | 0.17 | spread | 0.8150 | — | 1.0% | −9,851.2 (427) |
| no-defense | none | never | | | | | | −9,850.8 (427) |

- The attacker's first sale at pace 0.01 is 1% of 179.5M, which is 1.79M against a
  16.7M pool side. It takes spot to 0.815, past every trigger (0.5%, 1%, 2%), so all
  four defenders act on the same step.
- With the same seed, the price seen is 0.9004 at ratio 0.5 (first buy 0.8621), 0.6770
  at pace 0.02 and ratio 1.0, and 0.2319 at pace 0.1 and ratio 1.0. In every one of those
  runs all four defenders also act at step 51 (`trigger_table.py --ratio 0.5`,
  `--pace 0.02`, `--pace 0.1`; output in the Debug Log).
- **No cell of this sweep separates the triggers.** The smallest first sale in it
  (ratio 0.5, pace 0.01) already moves the price 10%.

## Against the story's prediction

- **"At pace 0.01 the triggers bind at different steps":** they do not. All bind at
  step 51 (above).
- **"The early-aggressive defender buys above $0.90 before the attacker is a tenth
  done":** not above $0.90. All three buyers make their first buy at 0.862 (ratio 0.5)
  or 0.758 (ratio 1.0), with 1% of the attack sold. Their average prices over the whole
  budget are 0.899–0.911 at ratio 0.5 and 0.720–0.803 at ratio 1.0.
- **"It may still lose on discount_bps_hours":** among the buying policies,
  early-aggressive has the largest discount in all 9 pace × ratio cells.
- **"The slow defender's advantage on time to parity should shrink":** where it can be
  measured, it does. At pace 0.1 and ratio 0.5, late-conservative is back 11.7 h before
  calibrated (6.6 vs 18.3 h). At pace 0.02 and ratio 0.5 the gap is 1.0 h (57.5 vs
  58.5 h), and none of those re-entries holds to the horizon. In the other five slow
  cells no policy re-enters.
- **"On discount_bps_hours it may reverse":** it does not. Late-conservative has the
  smallest discount in all 9 cells. The margin shrinks with the attacker's pace: at ratio
  1.0 it is 87,082 against 208,755 (calibrated) at pace 0.1, and 452,147 against 454,494
  at pace 0.01.

## Other numbers the tables show

- **Nobody recovers against the slow attacker.** At paces 0.02 and 0.01, P(never
  recovers) is 1.00 for every policy at every ratio, including 0.5×. At pace 0.1 it is
  0.00–0.31 for late-conservative.
- **The slow attack is deeper and costs more.**
  - Mean trough (`mc.parquet`): with a buying defender, −5,774 to −8,698 bps at pace 0.1,
    against −8,504 to −9,727 at pace 0.02 and −8,797 to −9,802 at pace 0.01.
  - With no defense: −8,908 to −9,497 at pace 0.1, against −9,557 to −9,851 at pace
    0.01.
  - The discount with a buying defender is 5,242–247,837 bps·h at pace 0.1 and
    320,055–455,063 at pace 0.01.
- **What defending buys against the slow attack.** At pace 0.01 the buyers' discount is
  22–23% below no-defense at ratio 0.5 (320,055–323,115 against 415,686) and 2.2–2.9% below
  at ratio 1.0 (452,147–455,063 against 465,501). At pace 0.1 and ratio 1.0 it is 17–71%
  below (87,082–247,837 against 298,463).
- **Spread-only** has the largest discount in every cell, 0.9–2.0% above no-defense.
