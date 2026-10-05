# ADR-0023: Reference-relative recovery via a `ReferenceView`; the oracle criterion removes the wander but not the clock; the defending budget does not scale with depth

**Status:** Accepted (finding, amended in review 2026-10-04: §4–§5 refine F-11; the "budget scales with depth" clause is withdrawn; time-to-parity chart added to Story 2.9; ADR-0007 extended, not amended)
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.8 AC 8

## Context
F-11 and the F-04 refinement: against par, "stays broken" at ≤ 1× D\* mostly measured a
driftless reference wandering out of the ±31 bps band. Story 2.7's post-hoc filter
(AMM more than 31 bps below the reference *at the last step*) suggested nothing at ≤ 1×
D\* breaks. F-11 hypothesised that the price-defense boundary is budget against depth.
Story 2.8 makes the criterion explicit, re-runs the surface through it, and tests the
hypothesis with a budget × depth sweep. ADR-0007 says termination reads the market
through `PegView`, which the AMM owns, and that the oracle is not a `PegView`.

## Decision

1. **`termination.peg_recovered.reference: par | oracle`** (default `par`). With
   `oracle`, the in-band test is `|PegView.spot_price / ReferenceView.published_price −
   1| ≤ tolerance`. A step with no published price yet, or with no `ReferenceView`
   registered, is out of band.
   - `content_hash` drops `reference` when it is `par`, so every existing scenario
     keeps its hash (pinned by test). soros-baseline's `summary.json`, timeseries,
     events and decisions are byte-identical. usdc-2023 is still `2c3aeaa9825d`.
   - `steps_to_first_band_entry` and `steps_to_sustained_recovery` follow the criterion
     (`amm_price / oracle_price − 1` from the timeseries; `oracle_price` NaN = out of
     band). `max_depeg_bps` and `final_depeg_bps` stay against par.

2. **Protocol views, no `protocol/` import.**
   - `PegView` gains `spot_price`, which the AMM already had; the termination test stub
     gains it too.
   - New `ReferenceView.published_price: float | None` (Story 2.8 Rulings 1). The Oracle
     satisfies it as an alias of its existing `price`. `Oracle.reference_price` keeps its
     Story 1.5 meaning, the raw source pass-through.
   - `published_price` exists nowhere else, so `Registry.find(ReferenceView)` can only
     return the oracle. It returns the first registered if there were several.
   - **ADR-0007 is extended, not amended**: the AMM still owns `PegView`, the oracle
     still is not one (tested), and `par` remains the default. ADR-0007's rejected
     alternative, "recovery depending on a stale price", is now opt-in; F-10 bounds the
     staleness cost at Chainlink's settings (≤ 0.5 bps on the trough).

3. **The sweep manifest's `base_config` is the base after `overrides`** (Rulings 3), so a
   chart reads the criterion a sweep actually ran. `base_scenario_hash` stays the base
   file's own hash. When overrides exist, `content_hash(base_config)` therefore differs
   from it, by design. `plot_threshold_surface` puts `reference=…` in its heading;
   `plot_budget_depth` is new.

4. **Finding: the oracle criterion removes the wander but not the clock.** Per-row 0.5
   crossings on nominal ratio (linear interpolation), par → oracle:
   - 0.25× D\*: not reached → not reached (max 0.06)
   - 0.5× D\*: 0.93 → not reached (max 0.25)
   - 1× D\*: 0.57 → **0.68**
   - 2× D\*: 0.50 → 0.54
   - 4× D\*: 0.60 → 0.69

   The 1× D\* row still goes to 1.0 from ratio 0.8. The price comes back to the market
   there (no run fails to re-enter the oracle band; median final −9.5 bps at 1.5), but
   its first re-entry is at a median step of 12,560–16,943, after step 11,100. That is
   the last start from which 6,900 in-band steps can still finish by step 18,000. Of the
   237 runs that stay broken: 128 never re-enter the band (all in 2× / 4× D\* at ratio ≥
   0.8, final −3,486 / −4,062 bps), 80 re-enter after step 11,100, and 29 re-enter
   earlier but do not hold it. Story 2.7's last-step filter overstated recovery at D\*.
   The prediction that "≤ 1× D\* goes to ≈ 0" holds at 0.25× and 0.5× D\* and **fails at
   1× D\*** (the clock: redemption-speed recovery, F-06). At ≥ 1× D\* the contour still
   runs along capital (0.54–0.69); along depth it sits between 0.5× and 1× D\*.

5. **Finding: the defending budget does not scale with depth (F-11's hypothesis not
   supported).** Attacker fixed at ratio 1.0 (179.5M), oracle criterion, 8 seeds.
   - The 0.5-crossing budgets are below 0.25× calibrated (holds at every budget) at
     0.25× and 0.5× D\*, then **1.57×** at 1× D\*, **1.80×** at 2× D\* and **3.00×** at
     4× D\*.
   - The least-squares log–log slope over the three crossing rows is **0.47**; the
     segments are 0.20 and 0.74. Budget/depth at the crossing is 3.90, 2.23 and 1.86,
     not constant.
   - Sharper, on the price alone (runs that never re-enter the oracle band): at 2× and
     4× D\* the price fails in all 8 seeds at 1× calibrated budget and holds in all 8 at
     2×. The boundary lies in the same budget interval while depth doubles.
   - The same budget/depth ratio (1.24) fails at 2× D\* (41.3M) and holds at 4× D\*
     (82.7M), so the operative quantity at this attack is the budget itself, not
     budget/depth.
   - Shallow pools (≤ 0.5× D\*) hold at every budget tested, as F-11 said: a dump
     that crashes the price is cheap to buy back.
   - The grid is a factor of 2 per step with 8 seeds, so the slope is coarse. Its
     direction (well below 1) is not in doubt.

6. **Which surface the note uses: the oracle-criterion surface** (`threshold-surface-ref-mc`),
   stated with §4. It is the only one that separates "the attack beat the defense"
   (never re-enters, 2×/4× D\* at ≥ 0.8) from "the defense won but slowly" (1× D\*). The
   par surface (2.7) stays as the record of F-11. The AC 6 sentence's Z is not supported
   (§5); X ≈ 0.7 and Y = 1 are (story Completion Notes).

## Consequences
- Every scenario keeps `par` and its hash. The new criterion is opt-in per sweep through
  `overrides`.
- "Stays broken" now has two causes the note must name: price (deep pools, attack ≥ 0.8×
  resources) and clock (D\*, recovery starting after ~37 h). A criterion that
  distinguishes them, such as "AMM below the oracle at the horizon" or time-to-re-entry as
  a metric, would make the surface say one thing; that is an Epic 3 candidate.
- F-11's "budget against depth" should be restated as "budget against the attack, once
  the pool is deep enough not to crash" (§5). The budget × depth sweep has one attack
  size, so this is a hypothesis for the next sweep, not a result.

## Alternatives considered
- **Import the Oracle in `termination.py`:** forbidden (CLAUDE.md, no domain logic in
  the kernel); the Protocol view costs one property.
- **Environment reference instead of the oracle:** unobservable in the model's own
  terms, and F-10 shows the two within 0.5 bps.
- **Repurpose `Oracle.reference_price`:** rejected in Rulings 1; it would change Story
  1.5's interface and three tests.
- **Keep the absorbed-ratio panel off the new surface:** AC 4 changes only the heading.
  The panel is kept as a conservation check, not a result (2.7 review).
