# ADR-0013: Recovery tolerance sits just outside the arbitrage band

**Status:** Accepted (amended in review: see Consequences)
**Date:** 2026-10-02
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 1.8 AC 8 (baseline retune)

## Context
ADR-0010 found that with `peg_recovered.tolerance` (10 bps) inside the arbitrageur's
no-trade band (AMM `fee_bps` + `min_profit_bps` = 50 bps), a defended peg parks at about
−18 bps and the run can only end by `max_steps`. Story 1.8 tried the ADR-0010 levers in
order. Option 1 (tolerance 0.006 = 60 bps) was enough on its own: the baseline ends
`peg_recovered` at step 192, with max depeg −573.2 bps at step 50. Attack, defense, pool
and `max_steps` are unchanged.

## Decision
"Recovered" means "back within the band where no rational actor trades". For every
scenario with a `peg_recovered` condition, set
`tolerance >= (amm.fee_bps + min arbitrageur min_profit_bps) / 10_000` plus a small
margin. The baseline uses band + 10 bps. A scenario that deliberately sets it tighter
must say in its header comment that it is testing permanent partial depeg.

## Consequences
- `peg_recovered` becomes reachable in every scenario that follows the rule.
- Sweeps that vary `fee_bps` or `min_profit_bps` (Epic 2) must move the tolerance with
  them, or the termination reason becomes an artefact of the band, not of the defense.
- `time_to_recovery_steps` measures first entry into this band after the trough. In the
  baseline that entry is a brief overshoot (2 steps after the trough), not the
  sustained recovery. Readers wanting the sustained recovery should use `steps_run`
  under `terminated_by == "peg_recovered"`: the band was then held for `for_steps`.

## Alternatives considered
- Stronger attack (600k) or a smaller pool (500k/500k): these change the experiment
  rather than its measuring stick. Kept as Epic 2 sweep seeds.
- Raising `max_steps`: forbidden by the story, and it changes nothing; the dead zone
  persists to step 5000.
- Validating tolerance ≥ band in the config model: possible later, but it would reject
  deliberate permanent-depeg scenarios.

## Review amendment (2026-10-02, dev manager)

Accepted. One change for Epic 2: `time_to_recovery_steps` as "first touch of the band after
the trough" is a misleading number (2 steps in the baseline is the overshoot, not recovery).
Story 2.1 renames it `steps_to_first_band_entry` and adds `steps_to_sustained_recovery` =
`steps_run − for_steps − step_of_max_depeg` when `terminated_by == "peg_recovered"`, else
null. Both are kept; the note will quote the sustained one.
