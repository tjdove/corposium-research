# Story 5.2: Joint Identification of D* and C*

Status: done

## Story

As a **reader who suspects the fitted triple is one of many**,
I want the trough drawn as a surface over pool depth and believers' capital on the par-reference replay, with all three ladders beside it,
so that the note can say how wide the family of fits is instead of reporting one point.

## Why

Referee §5.9–5.11: three fitting rules do not give three independent pieces of
information; D\*, C\* and pace interact, and the ladder was chosen after seeing the fits.
Story 5.1 showed the trough survives without the observed input (F-16), so the par
replay is the right surface to draw. The pace is **not** swept here (it was fitted to the
trough's timing, and the timing is what the par replay reproduces least well; 5.5 looks
at the weekend first).

## Acceptance Criteria

1. `sweeps/usdc-par-depth-x-capital.yaml`: base `scenarios/usdc-2023-tranches-par.yaml`
   (ladder B), axes `amm.reserve_stable`/`reserve_reference` linked (`LinkedAxis`) over
   {0.5, 0.75, 1, 1.5, 2} × D\* and `agents[type=holder].capital` over
   {0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 2} × C\*(ladder B) — 40 cells, seed 42 only (the
   reference is constant, so there is nothing to average). Output `max_depeg_bps`,
   `step_of_max_depeg`, `steps_to_first_band_entry`, holder bought/redeemed/PnL.
2. `plot_identification_surface`: heatmap of trough bps over the two axes; the ±5% and
   ±10% contours around −1,373 drawn and labelled; the fitted point marked.
   `docs/figures/identification_surface.png`, in `make figures`, manifest, figure list
   (marked †), README caption leading with "on the par-reference replay, nothing from the
   observed series fed in."
3. `scripts/identification_table.py`: prints the cells inside ±10%, and for each depth the
   C\* range that lands inside ±5% (linear interpolation between grid points). Deterministic.
4. **Ladders side by side.** The same script's second table: ladders A (1/2/5% at
   50/30/20), B (2/5/10/20% at 25% each), C (1/2/5/10/15% at 20% each) on the par
   replay at D\*, each at **its own** fitted C\* from Story 3.7 (read the values from
   `docs/calibration/fits/` or the 3.7 story; do not re-fit), and also at ladder B's C\*
   so the reader sees capital held constant. Trough, trough time, re-entry.
5. If cheap (≤ 1 h): a fourth holder variant with a **continuous** entry distribution,
   uniform over 2–20% in 10 equal tranches of 10% each, same C\*. One row in the ladder
   table. If not cheap, say so and skip; do not build a new agent type.
6. `docs/calibration/VALIDATION.md` gains "Identification (Story 5.2)" with both tables and
   a plain description of the surface's shape (where the cliff is, how the ±5% region is
   oriented) — numbers and shape only, no interpretation.
7. Tests: sweep spec hash pinned; surface renders from a synthetic parquet; table script
   smoke test. `pytest`, `ruff`, `make figures-check`.

## Tasks / Subtasks

- [x] Sweep spec and run (AC: 1)
- [x] Surface figure (AC: 2)
- [x] Tables (AC: 3, 4, 5)
- [x] VALIDATION.md (AC: 6)
- [x] Tests, gates (AC: 7)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.2: joint identification`, push `story/5-2-joint-identification`

## Dev Notes

### Learnings from Previous Story

- 5.1's `replay_table.py` holds the metric definitions ("first back in band after the
  trough"); reuse its functions, do not re-implement (ADR-0033 ruling 3).
- `LinkedAxis` with `scales` (Story 2.7) is how depth is swept with both reserves
  together; D\* = 16,666,667.
- Each sweep cell on the replay is ~2 s; 40 cells is fine on Seoul with `--workers 8`.
- The holder's `tranches` config is in `scenarios/usdc-2023-tranches-par.yaml`; ladders A
  and C are defined in Story 3.7 / ADR-0030.

### Prediction (to be checked, not aimed at)

The ±5% region is a thin diagonal band: deeper pools need more believers' capital to
reach the same trough, because the attacker is paid more per unit. The cliff (F-09) runs
below the band. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §5.9–5.11]
- [Source: docs/stories/5-1-par-reference-replay.md#Senior-Developer-Review]
- [Source: docs/adr/0030-multi-tranche-holder.md] (ladders)
- [Source: sweeps/pool-depth-x-attacker-mc.yaml] (LinkedAxis example)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code.

### Debug Log References

Branch `story/5-2-joint-identification` from `main` at `e68df8b`.

`python -m depeg_sim.sweep sweeps/usdc-par-depth-x-capital.yaml --mc --workers 12`:

```
wrote: output/usdc-par-depth-x-capital/sweep.parquet
mc: usdc-par-depth-x-capital grid_points=40 seeds=1 runs=40
wrote: output/usdc-par-depth-x-capital/mc.parquet

real	0m16.486s
```

`python scripts/identification_table.py --workers 12` (39.7 s wall):

```
observed trough -1,373.3 bps at 31.0 h (the target)

1. cells inside ±10% (-1,510.6 to -1,236.0 bps)
depth xD* capital xC* trough bps    gap     h re-entry h in band h holder bought holder redeemed holder PnL
-----------------------------------------------------------------------------------------------------------
        1           1   -1,279.2  +6.9%  32.8       40.4      55.6     8,646,604       8,646,604    521,604
      1.5         0.9   -1,452.0  -5.7%  32.8       44.6      51.4     7,776,546       7,776,546    464,046
2 of 40 cells

2. capital (x ladder B's C* = 10,833,333) with the trough inside ±5% (-1,442.0 to -1,304.6 bps), linear between grid points
depth xD*  troughs at the capital grid (bps)                             C* range (x C*)
----------------------------------------------------------------------------------------
      0.5  -4,882 -2,012 -2,007 -2,003 -1,017 -1,013 -1,007 -521         1.057-1.071
     0.75  -3,890 -2,007 -2,003 -1,621 -1,011 -1,009 -1,004 -514         1.029-1.052
        1  -3,227 -2,004 -2,001 -1,279 -1,008 -1,006 -1,003 -510         0.977-0.996
      1.5  -2,401 -2,001 -1,452 -1,005 -1,005 -1,003 -1,001 -507         0.902-0.933
        2  -2,002 -1,726 -1,131 -1,004 -1,003 -1,002 -813 -505           0.822-0.856
capital grid (x C*): 0.5 0.75 0.9 1 1.1 1.25 1.5 2

3. ladders at D*, par reference
ladder, capital                                                capital trough bps    gap     h re-entry h in band h holder bought holder PnL
--------------------------------------------------------------------------------------------------------------------------------------------
A (1/2/5% at 50/30/20), own C*                               8,333,333   -1,409.2  -2.6%  32.8       41.1      55.0     8,535,377    202,044
B (2/5/10/20% at 25% each), own C*                          10,833,333   -1,279.2  +6.9%  32.8       40.4      55.6     8,646,604    521,604
C (1/2/5/10/15% at 20% each), own C*                        10,000,000   -1,498.0  -9.1%  32.8       41.5      54.5     8,412,338    412,338
A (1/2/5% at 50/30/20), ladder B's C*                       10,833,333     -503.2 +63.4%  30.4       36.6      59.4     9,467,496    174,266
B (2/5/10/20% at 25% each), ladder B's C*                   10,833,333   -1,279.2  +6.9%  32.8       40.4      55.6     8,646,604    521,604
C (1/2/5/10/15% at 20% each), ladder B's C*                 10,833,333   -1,006.8 +26.7%  29.1       39.1      56.9     8,941,432    427,258
continuous (2, 4, ..., 20% at 10% each), ladder B's C*      10,833,333   -1,583.0 -15.3%  32.8       41.9      54.1     8,287,317    703,984

gap: (trough - observed) / |observed|, + is shallower; in band h over 27-96 h; model units (1M = $234.6M)
```

Determinism: the same script with `--workers 4` and `--workers 1` gives byte-identical
output (`cmp`; sha256 `f64527bc245b…` for all three).

`make figures` (all twelve sweeps, figures, fits):

```
sweep sweeps/usdc-par-depth-x-capital.yaml: wall time 17 s
drew: identification_surface.png <- sweeps/usdc-par-depth-x-capital.yaml
wrote: 22 figures and docs/figures/manifest.json (commit e68df8b26c5b, code_hash f40a6bb933f1)
fits: wall time 24 s
make figures: wall time 993 s (12 workers)
```

The 21 existing PNGs and the 4 fit records came out byte-identical (`git diff --stat`
shows only `manifest.json` changed under `docs/figures/` and nothing under
`docs/calibration/fits/`). The manifest's `commit` is `e68df8b…-dirty` because it was drawn
before this branch's first commit, as in Story 5.1.

`ruff check .`, `ruff format --check .`, `make test`, `make figures-check`:

```
All checks passed!
106 files already formatted
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
932 passed in 90.85s (0:01:30)
figures-check: ok, 22 figures match their sources (code_hash matches)
figures-check: ok, 4 fits match their inputs (script hashes match)
```

New code hash (`charts.py` changed): `f40a6bb933f1b747384feea07d960569ea0a8186c0688792f6f03e9532da984a`.

### Completion Notes List

- **Sweep (AC 1).** `sweeps/usdc-par-depth-x-capital.yaml`, base
  `usdc-2023-tranches-par.yaml`, spec hash `bdf2a026ce52…` (pinned). Both axes are
  `LinkedAxis` with multiples as values and `scales` = D\* and C\*(B), so the columns read
  as multiples. Seed 42 only. Cell (1, 1) reproduces Story 5.1's −1,279.2 at step 9,850.
  **`steps_to_first_band_entry` is null in every cell**, because the par scenarios have no
  `peg_recovered` condition (the summary needs one). The column is in the output as AC 1
  asks, but it is empty. Re-entry, hours in band and holder redeemed (also not a summary
  key) come from each cell's run directory via `replay_table.simulated_row`, as Dev Notes
  and ADR-0033 ruling 3 ask. No change to the summary or `src/` beyond the chart.
- **Figure (AC 2).** `charts.plot_identification_surface`: `pcolormesh` on log depth ×
  log capital, each cell labelled; ±5% (orange solid) and ±10% (black dashed) contours
  linear in the axis values; the fitted cell outlined (dotted orange square). The title
  leads with "On the par-reference replay, nothing from the observed series fed in", and
  so does the README caption. It is in `make_figures.FIGURES`, the Makefile's `SWEEPS`, the
  manifest, the note's figure list as row **1e †**, and the README note table. The target
  is `charts.OBSERVED_TROUGH_BPS = -1373.3`, tested against the CSV.
- **Tables (AC 3–5).** `scripts/identification_table.py` runs the sweep and the 7 ladder
  runs, then prints: (1) cells inside ±10%, (2) the per-depth capital range inside ±5%,
  by linear interpolation along capital (`capital_ranges`, which returns several disjoint
  ranges if they occur), and (3) the ladders. The ladder C\* values are constants from
  ADR-0030 Decision 4 (only ladder B has a fit record). **AC 5 was cheap**: the continuous
  ladder is just a 10-tranche `tranches` list (2, 4, …, 20% at 0.1 each) on the existing
  holder, with no new agent type and one row, run at ladder B's C\*. The target is
  `replay_table.observed_row`'s −1,373.3; ±x% means |trough − target| ≤ x · |target|.
- **Results (recorded, not interpreted; VALIDATION.md "Identification (Story 5.2)").**
  - 2 of 40 cells are within ±10%: (1, 1) at −1,279.2 and (1.5× D\*, 0.9× C\*) at
    −1,452.0.
  - The ±5% band runs from 1.057–1.071 × C\* at 0.5× D\* to 0.822–0.856 × C\* at 2× D\*.
    **The story's prediction had the slope the other way** (deeper pools needing more
    capital). The prediction that the cliff lies below the band holds.
  - Every ±5% range lies between two grid points, on a step of ADR-0030's staircase;
    the treads are at about −2,000, −1,000 and −500 bps.
  - Under par, ladder A at its own C\* is the closest of the three (−1,409.2, −2.6%); B
    and C are at +6.9% and −9.1%.
  - At ladder B's C\*, A and C sit on the −500 and −1,000 treads, and the continuous
    ladder gives −1,583.0 (−15.3%).
- **ADR-0034 (Proposed):** the finding, the null re-entry column and where re-entry
  comes from instead, the target constant, and the surface's interface.
- Not touched: pace, D\*, C\*, every scenario, the fit records' inputs.

### File List

- `sweeps/usdc-par-depth-x-capital.yaml` (new)
- `scripts/identification_table.py` (new)
- `src/depeg_sim/analysis/charts.py` (`plot_identification_surface`,
  `OBSERVED_TROUGH_BPS`, `_geometric_edges`)
- `scripts/make_figures.py` (registry entry)
- `Makefile` (twelfth sweep)
- `tests/test_identification.py` (new); `tests/test_figures.py` (registry count 22,
  function set)
- `docs/figures/identification_surface.png` (new), `docs/figures/manifest.json`
  (regenerated)
- `docs/figures/README.md` (row and caption)
- `docs/NOTE.md` (figure list row 1e †, change-log line; text not edited)
- `docs/calibration/VALIDATION.md` (section "Identification (Story 5.2)")
- `docs/adr/0034-joint-identification.md` (new, Proposed)
- `docs/stories/5-2-joint-identification.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager) · **Date:** 2026-10-15 · **Verdict: APPROVE**

Reproduced on the review box: `pytest -q` all pass (exit 0); `ruff` clean; `make
figures-check` → 22 figures, 4 fits ok. `python scripts/identification_table.py
--workers 2` (3 m 25 s): every number in the three tables matches ADR-0034 and
VALIDATION.md — 2 of 40 cells inside ±10% ((1,1) −1,279.2; (1.5, 0.9) −1,452.0); ±5% C\*
ranges 1.057–1.071 at 0.5×D\* down to 0.822–0.856 at 2×D\*; ladders A/B/C at own C\*
−1,409 / −1,279 / −1,498; at B's C\* −503 / −1,279 / −1,007; continuous −1,583. Figure
read: the staircase is unmistakable; the ±5% seam runs along the jump between the
−1,000 and −2,000 treads.

**What the result means (the dev manager's call).** Recorded as a second refinement of
F-09 under F-16's heading in FINDINGS.

1. *The trough is a tread.* At every depth and every capital the trough sits on one of the
   ladder's entry levels (−500, −1,000, −2,000 bps) or on a jump between two. The
   observed −1,373 lies between treads, so a discrete ladder can only reach it by having
   its last active tranche run out at the right moment. That is what C\* = 10,833,333 is:
   the capital at which the 10% tranche runs dry during the attack's tail. The fit is
   real but it is a knife-edge on a staircase, and the surface shows it.
2. *Total capital is identified to a few percent at a given shape and depth; the shape is
   not.* The ±5% seam is 2–3% of C\* wide at any depth. But all three fixed ladders land
   within ±10% at their own C\* (A at −2.6% is now the closest), and the continuous
   ladder misses by 15% at B's capital. The trough tells you how much money ran out when,
   not where it sat.
3. *The slope.* Deeper pools need **less** believers' capital to reach the same trough
   (the dev manager's prediction was backwards, recorded): a deeper pool is pushed to each
   entry level later and by more of the attacker's stock, so by the time the 10% tranche
   is active there is less attacker stock left for it to absorb. Across 0.5–2× D\* the
   fitting capital spans 0.82–1.07× C\*: a 25% band, which is the honest width of the
   family.
4. *For note v2 the believers claim becomes:* a ladder of par-expecting buyers with
   $2.0–2.9B in total, entered between 1% and 20% below par, reproduces the observed
   trough within 10% on the par-reference replay across pool depths from half to twice
   D\*; the trough identifies the total to within a few percent for a given ladder and
   depth, and does not identify the ladder's shape. No sentence stronger than that.

**Rulings**

1. **ADR-0034 accepted (finding + interface).** Index row added.
2. `steps_to_first_band_entry` null on replay scenarios (no `peg_recovered` condition):
   accepted as documented; `replay_table.simulated_row` is the reference for re-entry on
   replays. A one-line note in `summary.py`'s docstring is enough; no code change.
3. Figure 1e stays †; v2 cites it from §3.
4. Ladder A being closest under par is **not** a reason to switch the note's ladder. The
   three are within ±10% and the shape is unidentified (point 2); v2 reports all three
   and keeps B as the worked example because its figures already exist. Recorded so
   nobody re-fits toward A.

**Lessons:** prediction half wrong (slope), recorded (L-15). The builder's "every ±5%
range falls on a jump between grid points; the grid doesn't show where inside the
interval the jump is" is exactly the right caveat and goes into the note verbatim.

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
- 2026-10-15: Implemented by Claude Code (Opus 5.5): depth × capital sweep on the par replay, `identification_surface.png`, `identification_table.py` (cells, ±5% ranges, ladders A/B/C and continuous), VALIDATION.md section, ADR-0034 proposed. ±5% band 1.06× → 0.84× C\* from half to twice depth (opposite the predicted slope); 2 of 40 cells within ±10%. Status: review.
- 2026-10-15: Reviewed by dev manager — APPROVE; ADR-0034 accepted; F-09 second refinement; Status: done
