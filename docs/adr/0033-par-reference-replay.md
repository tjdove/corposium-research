# ADR-0033: Par-reference replay: with nothing observed fed in, ladder B's trough is −1,279 (6.9% short of −1,373, 1.8 h late); recovery to the band comes at 37–40 h, not 85 h; two-source figures

**Status:** Accepted (finding + interface; review 2026-10-15, unamended; F-16)
**Date:** 2026-10-15
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.1 (outside review 1, §1, §5.6, §5.14)

## Context

Every USDC replay so far fed the observed USDC/USD series to the model as its reference.
The oracle followed it and the arbitrageur traded the AMM against the oracle, so the
simulated venue was anchored to the thing it was compared with (VALIDATION.md: "the input
series showing through"). Story 5.1 reruns both replays (single entry, C\* 9,166,667;
ladder B, C\* 10,833,333) with a constant reference of 1.0 and, as a sensitivity check,
with the calm OU reference. Nothing is re-fitted.

## Decision

1. **Scenarios.** `usdc-2023-par.yaml`, `usdc-2023-tranches-par.yaml` (primary) and
   `usdc-2023-ou.yaml`, `usdc-2023-tranches-ou.yaml` (sensitivity). Each is its base
   replay with only `name` and `environment` changed (pinned in
   `tests/test_par_replay.py`). The base scenarios are untouched.
2. **Finding (numbers from `scripts/replay_table.py`, VALIDATION.md "Par-reference
   replay").**
   - Ladder B, par reference: trough **−1,279.2 bps at 32.8 h**. The observed trough is
     −1,373.3 at 31.0 h, so this is 94.1 bps (6.9%) shallower, **within ±10%**, and 1.8 h
     later. The observed-reference replay gave −1,323.3 at 31.2 h.
   - Single entry, par reference: trough **−607.2 bps at 33.0 h**, 55.8% shallower than
     observed. The observed-reference replay gave −1,137.8 at 34.2 h.
   - Recovery: back in the ±31 bps band at **37.2 h** (single) and **40.4 h** (ladder B),
     and inside it from then to 112 h (ladder B: one 7-step excursion to −37.4 bps at
     40.40–40.42 h). The observed price and both observed-reference replays re-enter at
     86.0 h and 85.3 h, after the 85 h capacity change. Hours in band over 27–96 h:
     58.8 / 55.6 against 10.7 / 10.7 and 8.0 observed.
   - With the par oracle the arbitrageur buys 923,919 of reference in 27–31 h, in both
     replays. With the observed-series oracle it bought 398,699 (single) and 678,574
     (ladder B). Under par its buying is bound by its capital plus what the redemption
     channel pays it (724,525 in that window). It never sells in any run.
   - Holder bought falls 0.5% (single) and 0.2% (ladder B). Holder PnL falls 1.6% and
     0.2%. Arbitrageur redeemed rises 3.0% and 1.3%.
   - The OU reference reproduces the par results: trough within 0.03 bps; same trough
     step, re-entry and hours in band; arbitrageur redemptions differ by < 0.4%.
3. **Interface: a figure may have two sources.** `make_figures.Figure.second` names a
   second scenario. `render` runs both and calls `function(run_dir, second_run_dir)`.
   The manifest entry adds `second_source` and `second_source_hash`, and
   `check_figures.stale_figures` checks the second source like the first.
   `plot_validation_overlay(run_dir, second_run_dir=None)`: the CSV comes from
   `run_dir` (which must have been fed it), the black line, markers and band from
   `second_run_dir`, and `run_dir`'s path is drawn grey and dashed.
   `validation_comparison(run_dir, observed_from=None)` reads the CSV from another
   run's manifest for a run that was not fed the series.
4. **Metric definitions used in the replay table.** These are used here for the first
   time, and a later story comparing replays should reuse them. "First back in band": the
   first time after the trough with |deviation| ≤ the ADR-0013 band. "Hours in band":
   from the attack start (27 h) to the end of the observed series (95 h close, counted to
   96 h). The observed row counts one hour per close and the simulated rows count
   12 s steps.

## Consequences

- The replay's recovery path, from the trough to 85 h, no longer agrees with the
  observed one once the series is not fed in. With the par reference the model is back
  in the band 45–49 h before the observed price.
- The ladder B trough depth stays within 10% of observed without the input. The
  single-entry trough does not.
- What this means for the note's description of the replay is the dev manager's call
  (story AC 5). This ADR records the numbers only.
- Two new overlay figures enter the committed set. `scripts/check_note.py` (Story 4.2,
  not merged) will see two more listed figures that the note body does not yet cite.

## Alternatives considered

- **Pass the par run alone to the overlay and look up the CSV by a fixed path.** Rejected:
  the overlay checks the CSV's sha256 against a run manifest, and only a run that was fed
  the series has one.
- **Record only one source for the two-run figure.** Rejected: a change to the other
  scenario would leave a stale figure that the guard does not catch.
