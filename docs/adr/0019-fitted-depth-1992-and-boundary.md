
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
