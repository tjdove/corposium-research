# ADR-0016: The outcome boundary is set by attacker capital vs defense resources, not pool depth

**Status:** Accepted (finding; amended in review)
**Date:** 2026-10-03
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.1, first run of `sweeps/pool-depth-x-attacker.yaml`

## Context
The first sweep crosses pool depth {250k, 500k, 1M, 2M} (both reserves) with attacker
capital {100k, 300k, 600k, 1.2M}, on the retuned baseline (defender 400k at −1%,
redemption 500k at 25k/step, arbitrageur 200k, seed 42, flat reference price,
`max_steps` 2000). The Dev Notes expected the `terminated_by` flip to run along a
diagonal: "100k into 2M recovers; 1.2M into 250k exhausts".

## Finding
`terminated_by` depends on attacker capital only:

| pool depth \ capital | 100k | 300k | 600k | 1.2M |
|---|---|---|---|---|
| 250k | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
| 500k | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
| 1M   | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |
| 2M   | peg_recovered | peg_recovered | peg_recovered | reserves_exhausted |

Pool depth sets *how bad and how long*, not *whether*:
- max depeg (bps): −753 → −187 at 100k, −5430 → −1206 at 1.2M (shallow → deep).
- `steps_to_sustained_recovery`: 45 → 22 at 100k, 62 → 39 at 600k.

The max depeg is mostly a function of the capital/depth ratio. That is the
constant-product price impact of the first dump: −2025 bps at 300k/250k, 600k/500k and
1.2M/1M, and −1098 at 300k/500k, 600k/1M. The exception is 1.2M into 2M (−1206 vs
−1098 at the same ratio): its trough is at step 51, not 50, so it compounds two dumps.

Mechanism, from the event logs: the only redeemer is the arbitrageur. The attacker's
stable reaches the redemption facility through it. The arbitrageur buys stable below
the band and redeems at 0.999 (17 redeem requests in the 250k/600k cell). The dumped
stable is conserved whatever the pool depth. What the defender doesn't absorb (its
budget is 400k reference; it spent 353–394k at 600k and 397–400k at 1.2M) is eventually redeemed.
Exhaustion follows when that remainder exceeds 500k of reserves. 600k − ~400k fits;
1.2M − ~400k does not. Exhaustion arrives fast (step 74–85, ~25–35 steps after the
attack starts), with the attacker not yet finished selling.

This is the first-generation (Krugman / Flood–Garber) result in miniature. The attack
succeeds when speculative capital exceeds the reserves that can be thrown at it
(defender budget + redemption reserves ≈ 900k here). Market depth changes the path, not
the verdict.

## Decision
Treat this as a model property to test, not a defect:
1. Story 2.2 (Monte Carlo) and 2.5 should refine the capital axis between 600k and 1.2M
   and add `defender.budget` and `redemption.reserves` as axes. The prediction to test
   is that the boundary tracks `capital ≈ budget + reserves` (in stable units at the
   prices paid), independent of depth.
2. Sensitivity charts should plot `terminated_by` against capital / (budget + reserves),
   with pool depth as a secondary dimension, not the other way round.

## Consequences
- The headline "deeper pools resist attack" is wrong in this model: deeper pools soften
  the trough and speed recovery, but don't change whether reserves exhaust. That's a
  candidate observation for the note, alongside ADR-0010.
- The conclusion depends on the arbitrageur being the only redeemer, with enough
  capital to recycle. An arbitrageur with tiny capital, or a redemption gate, could put
  depth back into the verdict. Worth an axis in 2.5.
- Only seed 42 on a flat reference price; no noise yet. 2.2 must confirm the boundary
  holds across seeds on the volatile scenario.

## Alternatives considered
- Reading the flip as diagonal and widening the grid until one appears: the data show a
  column boundary at every depth; widening the depth range won't create a diagonal
  unless another mechanism enters.

## Review amendment (2026-10-03, dev manager)

Accepted. Reviewer reproduced the 4×4 on a separate machine. Two sharpenings:

1. **State the conservation law explicitly.** In this model the attacker's stable has
   exactly two sinks: the defender's AMM buys and (via the arbitrageur) redemption. Pool
   depth is not a sink; it is a price. So `terminated_by` is decided by
   `attacker_capital ≷ defender_budget + redemption_reserves` (adjusted for the prices
   paid), and depth cannot enter unless a third sink exists. Candidate third sinks, each a
   future axis: an LP that absorbs stable by staying in the pool (Epic 3 stretch), a
   redemption gate/queue that strands stable (`capacity_per_step` small), or an
   arbitrageur too small to recycle. This reframes 2.6's "threshold surface": the headline
   chart's primary axis is `capital / (budget + reserves)`; depth is the secondary axis
   that governs trough and recovery time, not outcome.
2. **The 1.2M/2M anomaly is a timing artefact, not a second mechanism.** The two-dump
   trough at step 51 is the attacker's pace (0.1) interacting with a pool large enough
   that the first dump doesn't trigger the defender. Note it; don't chase it.

Headline candidate for the note, alongside ADR-0010: *"Liquidity depth determines how
far the peg falls; defense resources determine whether it comes back."*
