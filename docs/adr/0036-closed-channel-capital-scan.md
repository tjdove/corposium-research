# ADR-0036: Closed-channel C\*: the rule picks 13,333,333 ($3.13B, 1.23× the open C\*) on the −1,000 tread; nothing it runs is within ±10% of −1,373, and the capital between the treads gives the depth as a 40–85 h plateau; table 4's scan

**Status:** Accepted (finding; review 2026-10-16, unamended; F-17 refinement)
**Date:** 2026-10-16
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.6 (F-17; Story 5.5 review, ruling 4)

## Context

F-17: with the weekend channel shut, the par-reference ladder-B replay's trough falls to
−2,001 at C\* = 10,833,333, because the arbitrageur no longer recycles the channel's
payments into buying during 27–31 h. Story 5.6 re-fits ladder B's capital with
`scripts/fit_holder.py`, its rule unchanged, on the open and closed par-reference
scenarios, and puts the three C\* in one table with a ±10% range from a 5-point scan.

## Decision

1. **Fit records** `docs/calibration/fits/holder-ladder-b-par.json` and
   `holder-ladder-b-closed.json`, written by `fit_holder.py --scenario <par scenario>
   --tranches 2:0.25,5:0.25,10:0.25,20:0.25 --write …`. `fit_holder.py` is unchanged.
   `make figures` re-writes them, `make figures-check` covers them (6 fits), and
   `tests/test_fit_record.py` re-runs both and compares bytes. The par scenarios have no
   series, so `data` is null.
2. **Table 4 of `identification_table.py`.** For each of the three ladder-B records
   (`FITS`), the scan is C\* + k × step, k = −2…2, where step is the record's
   second-refinement spacing. It is recomputed by replaying `fit_holder`'s rule on the
   record's runs (`refine_step`, which raises if the runs are not the rule's).
   `scan_capitals` anchors on C\*'s point of that lattice when C\* is on it, so k = ±1
   are capitals the fit itself ran. Each scan capital is run through `fit_holder.with_holder`, as
   the fit ran it. The ±10% range is `capital_ranges` (linear between scan points, as
   table 2). The row also gives how many scan points are inside.
3. **Finding** (VALIDATION.md "Closed-channel C\* (Story 5.6)"):
   - Open channel, par reference: C\* = 10,833,333, the same as the observed-reference
     fit (trough −1,279.2 against −1,323.3).
   - Closed: **C\* = 13,333,333 ≈ $3.13B, 1.23×**, trough **−1,007.0 (+26.7%)**. The
     neighbour below, 11,666,667, gives −2,000.1 (−45.7%). No capital the rule ran, and
     no scan point, is within ±10% of −1,373. The interpolated ±10% range is
     12,488,146–12,949,109.
   - A one-off of nine capitals between 11,666,667 and 13,333,333 (Debug Log) puts the
     trough between the treads at −1,936 … −1,065, close to linear in capital; 12,500,000
     (−1,454.6) and 12,666,666 (−1,327.5) are inside ±10%. In those runs the price passes
     −1,000 at about 31 h, falls while the attacker sells its last stable, and sits at
     its trough from about 40–50 h until the 85 h reopening. The observed trough is a
     low at 31 h, followed by recovery. With the channel shut, no ladder-B capital gives
     both the depth and the shape.

## Consequences

- The prediction's range (1.1–1.3×, $2.8–3.3B) holds for the number (1.23×, and about
  1.16× for the capital that reaches −1,373). The trough at the rule's pick is on a
  tread, not at the target. Whether v2 quotes 13,333,333 (the rule's output), about
  12.6M (the depth), or the condition alone, is the dev manager's call.
- The closed-channel rule is a knife-edge between treads, like the 5.2 surface (ADR-0034):
  the grid and both refinements miss the 1.7M-wide step between −2,000 and −1,000.
- `identification_table.py` runs 15 more replays (73 s in all with 6 workers).

## Alternatives considered

- **A finer refinement or a third pass for the closed fit.** Rejected: AC 1 fixes the
  rule, and changing it for one scenario would make the three C\* incomparable. The
  one-off runs are reported as context, not as a fit.
- **Store the refinement spacing in the fit record.** Would change `fit_holder.py` and
  re-write the four existing records; replaying the rule from the record's runs gives
  the same number with no change.
- **Scan around C\* by ±10% of C\*** (another reading of "±10%"). Rejected: AC 3 says the
  scan has the refinement's spacing, and ±10% is the trough tolerance used in table 1.
