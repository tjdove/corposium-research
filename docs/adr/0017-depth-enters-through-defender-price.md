# ADR-0017: Depth enters the verdict through the price the defender pays

**Status:** Accepted (finding; refines ADR-0016; amended in review)
**Date:** 2026-10-03
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.2 AC 9, `sweeps/capital-vs-resources-mc.yaml`

## Context
ADR-0016 (amended) predicts `terminated_by` is set by
`attacker_capital ≷ defender_budget + redemption_reserves` "adjusted for the prices paid".
It also predicts that pool depth cannot shift the boundary unless a third sink exists.
Story 2.2 tests this on `soros-volatile` (5 bps per-step reference noise). Grid: capital
{600k…1.2M step 100k} × budget {200k, 400k, 600k} × reserves {250k, 500k, 750k} ×
`pool_depth` {500k, 2M}; 16 seeds per point (1000–1015); `max_steps` 1500. That's 126
grid points and 2016 runs.

## Result

Nominal ratio `r = capital / (budget + reserves)`, binned. Pooled
`p_reserves_exhausted` with Wilson 95% bounds on the pooled runs (this treats runs
from different grid points in one bin as one sample):

**pool_depth = 500k**

| ratio bin | points | runs | exhausted | p | lo | hi |
|---|---|---|---|---|---|---|
| [0.40, 0.60) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [0.60, 0.70) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.70, 0.80) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.80, 0.90) | 8 | 128 | 0 | 0.000 | 0.000 | 0.029 |
| [0.90, 1.00) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [1.00, 1.10) | 8 | 128 | 1 | 0.008 | 0.001 | 0.043 |
| [1.10, 1.25) | 6 | 96 | 80 | 0.833 | 0.746 | 0.895 |
| [1.25, 1.50) | 8 | 128 | 128 | 1.000 | 0.971 | 1.000 |
| [1.50, 2.00) | 7 | 112 | 112 | 1.000 | 0.967 | 1.000 |
| [2.00, 2.80) | 4 | 64 | 64 | 1.000 | 0.943 | 1.000 |

**pool_depth = 2M**

| ratio bin | points | runs | exhausted | p | lo | hi |
|---|---|---|---|---|---|---|
| [0.40, 0.60) | 5 | 80 | 0 | 0.000 | 0.000 | 0.046 |
| [0.60, 0.70) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.70, 0.80) | 6 | 96 | 0 | 0.000 | 0.000 | 0.038 |
| [0.80, 0.90) | 8 | 128 | 0 | 0.000 | 0.000 | 0.029 |
| [0.90, 1.00) | 5 | 80 | 2 | 0.025 | 0.007 | 0.087 |
| [1.00, 1.10) | 8 | 128 | 76 | 0.594 | 0.507 | 0.675 |
| [1.10, 1.25) | 6 | 96 | 96 | 1.000 | 0.962 | 1.000 |
| [1.25, 1.50) | 8 | 128 | 128 | 1.000 | 0.971 | 1.000 |
| [1.50, 2.00) | 7 | 112 | 112 | 1.000 | 0.967 | 1.000 |
| [2.00, 2.80) | 4 | 64 | 64 | 1.000 | 0.943 | 1.000 |

Per grid point, `p_reserves_exhausted` (rows budget/reserves, columns attacker capital):

| 500k depth | 600k | 700k | 800k | 900k | 1000k | 1100k | 1200k |
|---|---|---|---|---|---|---|---|
| 200k/250k | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/500k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| 400k/250k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 400k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| 400k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 600k/250k | 0.00 | 0.00 | 0.00 | 0.06 | 1.00 | 1.00 | 1.00 |
| 600k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 600k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

| 2M depth | 600k | 700k | 800k | 900k | 1000k | 1100k | 1200k |
|---|---|---|---|---|---|---|---|
| 200k/250k | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/500k | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 200k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| 400k/250k | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 400k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| 400k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.75 |
| 600k/250k | 0.00 | 0.00 | 0.12 | 1.00 | 1.00 | 1.00 | 1.00 |
| 600k/500k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| 600k/750k | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Answers to the four questions

1. **Does the 0.5 crossing sit near ratio 1.0?** Yes, just above it. In nominal ratio it
   crosses at about **1.10 at 500k depth** (p = 0 up to 1.091, p = 1 from 1.111) and
   about **1.03 at 2M** (p = 0 at all three 1.000 points, 0.75 at 1.043, 1 from 1.053).
   The first-generation picture holds to within ~10%.
2. **Does depth shift it? Yes, contradicting ADR-0016's "depth cannot enter".** Six grid
   points (nominal ratio 1.04–1.11) flip from p ≤ 0.06 at 500k to p ≥ 0.75 at 2M; one
   more (ratio 0.94) goes from 0 to 0.12. The direction is the opposite of the usual intuition: **the deeper
   pool is easier to break.** The mechanism is not a third sink. It's the "adjusted for
   prices paid" clause in ADR-0016 itself, and depth controls that adjustment:
   - The defender spends nearly its whole budget at both depths (mean spend 94.7% of
     budget at 500k, 95.4% at 2M). But in a 500k pool the attack drives spot far lower, so each reference unit
     buys more stable. Measured over all runs, the defender absorbs **1.19 stable per
     budget unit at 500k vs 1.02 at 2M**. At (1.2M, 600k, 500k) it pays an average
     0.78 at 500k depth vs 0.92 at 2M.
   - Check: 600k × 1.28 + 500k / 0.999 ≈ 1.27M > 1.2M → survives (observed p = 0);
     600k × 1.08 + 500.5k ≈ 1.15M < 1.2M → exhausts (observed p = 1).
   - The **price-adjusted** ratio `capital / (stable the defender bought + reserves /
     payout_per_unit)` separates all 2016 runs at a single threshold of **1.005** with 5
     misclassified runs, against 93 for the nominal ratio at its best threshold (1.045).
     At 500k depth it separates perfectly (exhausted min 1.0042 > survived max 1.0027).
     Caveat: "stable the defender bought" is an outcome of the run, so this confirms
     the two-sink conservation law but doesn't predict the verdict from parameters alone.
3. **Does the budget/reserves split matter?** Yes, mildly, and through the same channel.
   Budget is worth more than its face value whenever the defender buys below peg (×1.19
   at 500k, ×1.02 at 2M). Reserves are worth exactly `1 / payout_per_unit` stable per
   reference unit (redemption pays 0.999 regardless of AMM price). So at the same nominal
   ratio, budget-heavy splits survive longer in shallow pools. One irregularity, the
   600k/250k split, exhausts at a *lower* nominal ratio (0.94: p = 0.12 at 2M, 0.06 at
   500k): with small reserves the redemption facility runs dry before the defender's
   buying is done.
4. **Transition band width (p = 0.05 → 0.95).** Within one depth the transition is
   essentially a step at this grid resolution. Only 3 of 126 points have 0 < p < 1, and
   seeds barely matter at 5 bps noise. In nominal ratio the band is ≤ ~0.05 wide at each
   depth (500k: from 1.059, p = 0.06, to 1.111, p = 1; 2M: 1.000 → 1.053), but the two
   depths' bands are disjoint. Pooled over depths the nominal band runs ~1.00 → 1.11.

`sweeps/pool-depth-x-attacker-mc.yaml` (the 2.1 grid, 32 seeds, volatile) reproduces the
2.1 column result exactly: `p_reserves_exhausted` is 0 for capital ≤ 600k and 1 at 1.2M
at every depth. Its capital steps are too coarse to see the shift above.

## Decision
1. Restate the ADR-0016 law with the adjustment made explicit: the verdict is set by
   `capital ≷ budget / avg_defender_price + reserves / payout_per_unit`. Depth enters
   through `avg_defender_price`; the deeper the trough, the cheaper the stable the
   defender buys.
2. Story 2.6's headline chart keeps `capital / (budget + reserves)` on the primary axis
   (parameters only, readable), but shows the two depths as separate curves. The shift
   is the finding, not noise.
3. The amended headline needs a qualifier. "Liquidity depth determines how far the peg
   falls; defense resources determine whether it comes back" stays true to first order,
   but a deeper pool *lowers* the capital needed to break the peg by ~7% here, because
   it makes the defender's buying dearer.

## Consequences
- Second-order depth effects scale with the defender's threshold and pace: a defender
  that buys earlier (closer to peg) loses the cheap-stable bonus. Candidate axis for 2.5
  (defender policy variants).
- Monte Carlo at 5 bps noise adds almost no spread to the verdict. Noise mostly shows up
  in `p_max_steps` (6–25% of runs in the recovering region), where reference-price drift
  keeps the AMM outside the 60 bps band for 100 consecutive steps within 1500. That
  belongs to the noise calibration in 2.3, not to the boundary.
- Wilson bounds on pooled bins treat runs from different grid points as one sample. They
  are descriptive, not a test.

## Alternatives considered
- Reading the depth shift as noise: rejected. The shifted points are p = 0 vs p = 1
  across all 16 seeds, and the price-adjusted accounting predicts them.
- A third sink (pool residue): measured pool stable excess at the end is ~3.5k (500k)
  and ~16k (2M) at the flipped point, too small to explain a 100k+ difference in
  redeemed stable. The defender's purchase price explains it.

## Review amendment (2026-10-03, dev manager)

Accepted. Reviewer reproduced the critical cell independently (48-run slice at ratio
1.111: 500k depth p=0, 2M depth p=1). This refines, not overturns, ADR-0016: the
conservation law stands; the "prices paid" term was the whole story, and depth sets it.

**Reframing for the note.** The intuitive claim "deeper pools are safer" is wrong in this
model, and the reason is clean enough to be the headline: *a shallow pool makes the attack
look worse (deeper trough) but makes the defense cheaper (each unit of budget buys more
stable at the crashed price). A deep pool keeps the price up, so the defender pays nearly
par and its budget absorbs less.* Depth trades trough severity against defense efficiency.
Updated headline candidate:

> *"Shallow liquidity makes a depeg deeper but a defense cheaper. The attack succeeds
> when speculative capital exceeds the stable the defense can absorb, and a deep pool
> raises the price of absorbing it."*

**Consequences for Epic 2:**
- 2.6's primary axis stays `capital / (budget + reserves)`; the chart gets two panels or
  two lines (500k, 2M) to show the shift, with the band width noted.
- The price-adjusted ratio is a *diagnostic*, not a predictor (builder's caveat is right).
  A parameter-only predictor would need the expected trough, which is itself a function
  of capital/depth. Possible closed form for the note's appendix; not a story.
- The 600k/250k irregularity (reserves run dry before the defender finishes) is the
  redemption-capacity channel; it becomes an axis in 2.6 only if time allows.
- 5 bps per-step noise barely moves outcomes; 6–25% of recovering runs hit `max_steps`
  instead. 2.3 must set volatility from a real stablecoin stress series and revisit
  `peg_recovered.for_steps` under noise.
