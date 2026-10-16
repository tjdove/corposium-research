# ADR-0034: Joint identification on the par replay: the ±5% band runs from 1.06× C\* at half depth to 0.84× at twice depth (opposite the predicted slope); 2 of 40 cells within ±10%; ladder A is closest under par

**Status:** Accepted (finding + interface; review 2026-10-15, unamended; F-09 second refinement)
**Date:** 2026-10-15
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.2 (outside review 1, §5.9–5.11)

## Context

D\*, C\* and pace were fitted one at a time, and the ladder was chosen after the fits.
The referee asked whether the fitted triple is one point of a wide family. Story 5.2
sweeps depth × believers' capital on the par-reference ladder-B replay, where nothing
from the observed series is fed in (F-16). It also runs the three ladders and a
continuous ladder side by side. Pace is not swept, and nothing is re-fitted.

## Decision

1. **Sweep** `sweeps/usdc-par-depth-x-capital.yaml`, with base
   `usdc-2023-tranches-par.yaml`. Both axes are linked axes whose values are multiples
   (0.5–2) and whose `scales` are D\* = 16,666,667 and C\*(B) = 10,833,333. The column
   therefore holds the multiple, and the config gets value × scale. The grid is 40 cells
   at seed 42, full length. Cell (1, 1) reproduces Story 5.1's −1,279.2 bps.
2. **Finding** (numbers from `scripts/identification_table.py`, VALIDATION.md
   "Identification (Story 5.2)").
   - **Cells.** 2 of 40 cells are within ±10% of −1,373.3: (1, 1) at −1,279.2 and
     (1.5× D\*, 0.9× C\*) at −1,452.0. None is within ±5%.
   - **The ±5% band** comes from linear interpolation along capital. It is thin and
     slopes down with depth: 1.057–1.071, 1.029–1.052, 0.977–0.996, 0.902–0.933 and
     0.822–0.856 × C\* at 0.5, 0.75, 1, 1.5 and 2 × D\*. **Deeper pools reach the observed
     trough with less believers' capital.** The story predicted the opposite slope.
   - **Treads and steps.** The surface is ADR-0030's staircase in two dimensions:
     treads at about −2,000, −1,000 and −500 bps (the 20%, 10% and 5% entries), with
     steps between them. Every ±5% range lies between two grid points, on a step. The
     −2,000 tread (F-09's cliff) lies below the band at every depth.
   - **Ladders under par, each at its own C\*:** A −1,409.2 (−2.6%), B −1,279.2
     (+6.9%), C −1,498.0 (−9.1%). All three are within ±10%, and A is the closest. With
     the observed reference (ADR-0030) they were −1,602.7, −1,323.3 and −1,489.0.
   - **Ladders at ladder B's C\*:** A −503.2, C −1,006.8, and continuous (2, 4, …, 20% at
     10%) −1,583.0 (−15.3%).
   - **Recovery.** The own-C\* ladders are back in band at 41.1, 40.4 and 41.5 h (A, B,
     C); every run in table 3 is back between 36.6 and 41.9 h.
3. **Re-entry comes from `replay_table.simulated_row`, not the sweep summary.** These
   scenarios have no `peg_recovered` condition, so `steps_to_first_band_entry` is null in
   `sweep.parquet` and `mc.parquet`. AC 1 lists that column, and it is there but empty.
   `identification_table.py` computes "first back in band", hours in band and holder
   redeemed from each cell's run directory with `replay_table`'s functions (ADR-0033
   ruling 3). Adding `peg_recovered` to the sweep would end the runs early and change
   them. Adding holder redeemed to the summary would touch `src/` for a number one
   script needs.
4. **Target.** Tables use `replay_table.observed_row`'s trough (−1,373.3, from the CSV).
   The figure uses `charts.OBSERVED_TROUGH_BPS = -1373.3`, and a test checks that it
   matches the CSV to 0.05 bps. ±x% means |trough − target| ≤ x · |target|.
5. **Interface.** `plot_identification_surface(sweep_dir, target_bps, usd_per_unit)`
   reads `mc.parquet` (`max_depeg_bps_mean`, n = 1) and the manifest, and takes the axis
   units from the linked axes' `scales`. Depth and capital are drawn on log axes, with
   contours linear in the axis values.

## Consequences

- At D\* the ±5% range is 0.977–0.996 × C\*. Across the swept depths (0.5–2×) the ±5%
  ranges together span 0.822–1.071 × C\*. What that means for the note is the dev
  manager's call (L-19: numbers first).
- New committed figure `identification_surface.png` (22 figures), marked † in the note's
  figure list. `make figures` now runs twelve sweeps.

## Alternatives considered

- **Seed-averaging (`seeds: {count: N}`).** Rejected: with a constant reference no run
  draws from `ctx.rng`, so every seed gives the same run.
- **Absolute axis values (units) in the spec.** Rejected for multiples × `scales`: the
  table and figure read "× D\*" and "× C\*" directly, and the units stay one product
  away.
- **Contours in grid-index space** (as `imshow` heatmaps elsewhere). Rejected: the
  capital grid is uneven (0.9, 1, 1.1 are close together), and index-space interpolation
  would disagree with the table's interpolation in capital.
