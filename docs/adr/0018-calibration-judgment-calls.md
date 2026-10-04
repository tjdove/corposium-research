# ADR-0018: Calibration judgment calls (pool anchor, reserves split, attacker ratio)

**Status:** Proposed
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.3 AC 12

## Context
Story 2.3 traces every parameter of `scenarios/calibrated-baseline.yaml` and
`calibrated-stress.yaml` to a source (`docs/calibration/SOURCES.md`). Most rows are
measurements. Three are choices that a different reasonable researcher could make
differently, and every later calibrated result depends on them. Two observations from
running the calibrated scenarios also change how ADR-0017's boundary should be read.

## Decision

1. **Pool anchor: raw USDC-leg TVL as constant-product depth.** `D = 1,000,000` per side
   stands for Curve 3pool's USDC leg on 2023-03-10 ($510M × 46% = $234.6M). Every dollar
   figure is scaled by `s = 1e6 / 234.6e6`. No amplification (A = 2000) scaling: stableswap
   liquidity near peg is far deeper than constant-product, but the A-equivalence collapses
   beyond ~1–2% deviation, which is where depegs live. Consequence: simulated troughs are
   upper bounds on depeg depth (one venue, constant-product).
2. **Reserves split: T-bills = redemption reserves, cash = defender budget.** Circle's
   March 2023 reserves were $32.4B T-bills (77%) and $9.7B cash (23%) (21Shares). Cash is
   what can be deployed into the market immediately (the defender's AMM buys); T-bills
   back 1:1 redemption. So `budget : reserves = 23 : 77`, and both are scaled by `s`:
   reserves 138,107,417 (138× pool depth), budget 41,346,974 (41×). Redemption *throughput*
   is calibrated separately, from the observed net burn (605.79 per step, i.e. $1.02B/day).
3. **Attacker ratio: `capital / (budget + reserves) = 1.0`.** A design choice that puts the
   attacker exactly where ADR-0017 located the outcome boundary. It is anchored to, but not
   measured from, the two historical ratios: 1992, Quantum ≈ $10B against ≈ £27B gross
   intervention (secondary); 2023, peak CEX outflow $1.2B/hour ≈ 2.9% of $42.1B reserves,
   stranded SVB deposit $3.3B = 8%. `pace` (0.1) and `start_step` (50) are unchanged
   from `soros-baseline`.

## What the calibrated runs show (for the dev manager's review)

- **Ratio 1.0 isn't on the boundary at calibrated scale.** Decision 2 makes the attacker
  179× pool depth, far outside the capital/depth range 0.1–2.4 where ADR-0017 measured
  the boundary. The first dump (10% of 179M into a 1M pool) drives spot to 0.0028 (−9972
  bps). The defender then buys stable for almost nothing, which is F-03's "defense gets
  cheaper as the trough deepens" at its limit. It spends 16.1M of its 41.3M budget and
  the peg recovers. A probe at attacker / (budget + reserves) = 1, 2, 4, 8, 16 (seed 42,
  calm vol) recovers every time, with defender spend rising only from 16.1M to 29.1M.
  At calibrated depth ratios the boundary lies above 16×, if it exists at all for an
  attacker that keeps selling at any price.
- **`reserves_exhausted` is unreachable at calibrated capacity.** 605.79 per step × 18,000
  steps = 10.9M ≈ 7.9% of reserves. The redemption channel is throughput-bound, as it
  was in March 2023 (banks shut over the weekend). Outcomes are `peg_recovered` or
  `max_steps`.
- **Under stress volatility the recovery criterion is mostly unreachable.** With
  `volatility_per_step` = 7.561e-4 the reference price wanders ~6.3% (σ√6900) over one
  `for_steps` window. Holding a 31 bps band for 6,900 consecutive steps succeeds in 5 of
  32 seeds (calm: 31 of 32). Details in the story's Completion Notes.

## Consequences
- 2.5 (USDC-2023 replay) inherits a model that cannot reproduce the observed ~−1300 bps
  trough with a never-stopping attacker at 179× depth. The levers are
  `stop_below_price` (a rational seller stops dumping at some price; no source yet, so an
  assumption) and multi-venue depth (out of scope). One of them is needed before the
  replay's trough can be compared with the observed one.
- 2.6's headline sweep should stay in the capital/depth range where the boundary exists
  (ADR-0017), and state that the calibrated point lies outside it, or add capital/depth
  as an explicit axis.
- If the dev manager prefers the calibrated baseline to sit *on* a boundary, the
  minimal change is a `stop_below_price` assumption, not a different reserves split. The
  split is sourced; the stopping rule is not.
- The stress result supports widening the recovery criterion under realised volatility,
  or measuring deviation against the reference price rather than the fixed peg. Either
  is a model change for a later story.

## Alternatives considered
- **A-scaled depth** (D ≈ A × leg TVL near peg): accurate for small deviations only, and
  it would make every depeg in the model shallower than the observed one.
- **Total reserves as redemption reserves, no budget**: drops the defender channel that
  ADR-0016/0017 showed decides the outcome.
- **Budget = the stranded SVB deposit ($3.3B)**: confuses what was at risk with what
  could be deployed.
- **Attacker anchored to realised flows** (e.g. $1.2B/hour × hours of stress): gives an
  attacker of the same order as reserves anyway, and imports CEX flows the single-venue
  model can't route.
