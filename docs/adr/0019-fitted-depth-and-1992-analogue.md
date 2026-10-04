# ADR-0019: Fitted aggregate depth D*, the 1992 analogue's split and multiple, and the boundary at calibrated depth

**Status:** Accepted (amended in review: decision 1 superseded, see below)
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.4 AC 12

## Context
ADR-0018's amendment made the calibrated pool stand for aggregate USDC depth, with
`market_depth_multiple` back-solved from the observed March-2023 trough (−1300 bps). Story
2.4 fits it, re-asks ADR-0017's boundary question at that depth, and builds a 1992
analogue that shares only the depth. Four results need a decision or a record.

## Decision

1. **D\* = 1,833,333,333 (`market_depth_multiple` = 1833.33), achieved trough −1327.8 bps.**
   Chosen by the AC 2 rule with no hand-picking (`scripts/fit_depth.py`). No point on the
   specified grid (1M…500M) reached −1300 (500M: −3676.8). The context's constraint
   ("extend by one decade only") was applied: 1B −2213.9, 2B −1229.3, 5B −525.4. Five
   refined points between 1B and 2B; the closest to −1300 is 1,833,333,333. The Dev Notes
   instead suggested "note it and pick the grid point closest to −1300 rather than extend
   the grid" for D\* > 200M. That would give 500M at −3676.8, 2,377 bps off the
   observation, which is not a fit. The constraint was followed and the conflict is
   flagged here for review.
2. **D\* is not a physical depth, and pace does not set it.** At `s` it is ≈ $430B per side,
   ≈ 10× USDC's supply. The trough is the conservation residual against depth: the
   attacker sells at any price, the defender absorbs ≤ 41.3M, redemption ≤ 10.9M in 60 h,
   and the remaining ~127M sits in the pool. A 10% first dump into D\* moves the price only
   −193 bps. Changing `pace` 0.1 → 0.01 → 0.001 moves the trough −1327.8 → −1341.1 →
   −1308.2 and its timing step 145 → 830 → 5598. So D\* absorbs the ratio-1.0 attacker
   size (≈ $42B of selling vs ≈ $4B observed net burn), not a too-fast pace. Pace is then
   free to be fitted to trough *timing* in 2.5 without disturbing D\*.
3. **Boundary probe at D\*: no ADR-0017-style boundary on the specified ratios.**
   At ratio 0.5–2.0 × (budget + reserves) every run (6 × 8 seeds) ends `max_steps`; no
   run recovers or exhausts reserves. An extra probe at 0.1–0.4 finds the boundary at
   nominal ratio **0.25–0.30** (0.25: 5/8 recover; 0.30: 0/8). Predicted 0.291 =
   (budget + capacity × max_steps) / (budget + reserves) = (41.3M + 10.9M) / 179.5M. With
   throughput-bound redemption the operative resource is the reserve the channel can
   *deliver within the horizon*, not the reserve held, and the outcome on the far side is
   `max_steps` (the peg stays broken without the reserves running out), not
   `reserves_exhausted`.
4. **1992 analogue: budget : reserves = 50 : 50 of £27bn gross; attacker = 6 × Quantum
   ($10bn); ratio 1.270; flip at 5.3 × (ratio 1.122).** Units: same `s` as the USDC
   scenarios, GBP→USD 1.75, depth D\* (depth : defense = 9.10). The run ends
   `reserves_exhausted` at step 9,932 with no adjustment. Scanning the multiple with
   everything else fixed: ≤ 5.2 ends `max_steps` within two days, ≥ 5.3 exhausts. The
   flip sits above ratio 1.0 because the widened redemption spread (200 bps) keeps the
   last ~10% of reserves unreachable: redemption opens only below −200 bps, and with 5.0 ×
   and a six-day horizon the run stalls at −196 bps with 90.7M of 100.7M paid.

## Consequences
- 2.5 compares the replay with the observed trough using D\* as fitted. Trough *timing*
  is a separate lever (pace), and recovery is not reachable in the calibrated scenario
  without an outside backstop (both calibrated runs end `max_steps` at about −1218 bps
  after 60 h).
- 2.6's headline sweep: at calibrated parameters the boundary is at nominal ratio ≈ 0.29.
  Either the x-axis becomes `capital / (budget + deliverable reserves)` with deliverable =
  min(reserves, capacity × horizon), or capacity is an explicit axis.
- 1992 says the market had to be about 5.3× Quantum for the reserve-exhaustion story to
  hold in this model. The figure is sensitive to the unverified £27bn, the 50:50 split and
  the FX rate.
- The spread lever makes a dead zone like F-01's between −100 bps (defender trigger) and
  −200 bps (redemption opens once the spread is widened). The defender also widens and
  restores the spread on every sawtooth (57 `spread_changed` events in soros-1992),
  because it has no hysteresis.

## Alternatives considered
- **D\* = 500M (closest specified grid point):** follows the Dev Note, misses the
  observation by 2,377 bps.
- **Lower the calibrated attacker ratio instead of fitting depth:** would also hit the
  trough at a more physical depth, but the ratio is a sourced design choice (ADR-0018) and
  the amendment said to fit depth.
- **1992 defense sized to USDC's defense/depth ratio** (0.0979 instead of 0.110): nearly
  the same numbers. A shared `s` is simpler to explain.
- **Budget : reserves from the £3.3bn net cost:** a loss, not a deployable amount.

## Review amendment (2026-10-04, dev manager)

Accepted, with decision 1 superseded. The builder followed the rule as written and the
result is the correct consequence of a wrong input: **ADR-0018's attacker ratio of 1.0 was
the error, not the depth grid.** Decision 2 proves it: D\* absorbs the attacker's size, not
its pace. A ratio-1.0 attacker sells ≈ $42B against a market that saw ≈ $4B of net burn in
the whole episode (SOURCES.md, DefiLlama). Fitting depth to one observation while holding
an attacker ten times too large forces a depth ten times too large. $430B per side is the
model telling us the attacker is wrong.

**Decision (supersedes ADR-0018 §3 and ADR-0019 §1):**
- The calibrated attacker's `capital` is **anchored to the observed episode flow**, status
  `secondary`: the net USDC burn over 10–13 March 2023 (≈ $4.0B, DefiLlama) plus the
  peak-hour CEX outflow as a cross-check ($1.2B/h, Chainalysis). This replaces the
  "ratio 1.0" design choice. The 1992 Quantum anchor stays as narrative, not as the
  calibration.
- `D*` is **re-fitted in Story 2.5** against the observed trough with the episode-sized
  attacker, same AC 2 rule, same grid (1M…500M). The expectation is that D\* lands in the
  low billions of dollars (single-digit `market_depth_multiple` × 10), which is a
  defensible aggregate-depth figure. If it does not, that is a finding, and 2.5 reports it.
- The 1992 analogue keeps its own ratios and the *current* D\* until 2.5 re-fits; 2.5 then
  re-runs `soros-1992` at the new depth and records whether the 5.3× flip moves. The 1992
  conclusions below are provisional until then.
- SOURCES.md: the attacker row changes from `assumption (ratio 1.0)` to `secondary
  (episode net burn)`; the `market_depth_multiple` row is marked "re-fit pending 2.5".

**Rulings on the other decisions:**
- **§3 (boundary at calibrated depth ≈ 0.29, operative resource = deliverable reserves):**
  Accepted as **F-06**. The builder's prediction formula
  `(budget + capacity × horizon) / (budget + reserves)` is the right generalisation of
  ADR-0016/0017 for throughput-bound redemption, and the far-side outcome being
  `max_steps` (stays broken) rather than `reserves_exhausted` is exactly March 2023. 2.6's
  axis becomes `capital / (budget + deliverable reserves)`.
- **§4 (1992 analogue):** Accepted provisionally. The sequential-defense dead zone between
  the −100 bps defender trigger and the −200 bps widened spread is **F-07**, and the
  no-hysteresis spread chatter (57 events) is a known defender limitation already noted in
  1.7's Dev Notes; a `restore_threshold_pct` is a one-line Epic 3 improvement.
- The Dev-Notes-vs-constraint conflict on grid extension was mine; the context file was the
  stricter and the builder chose correctly. Moot now that the attacker changes.
