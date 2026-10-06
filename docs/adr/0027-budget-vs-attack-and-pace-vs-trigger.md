# ADR-0027: At 2× D\* the price-holding budget is proportional to the attack (≈ 0.36×), not to what the attacker extracts; F-13's operative parameter is the defender's spending pace relative to the attacker's selling pace, and the trigger does nothing (finding candidates)

**Status:** Proposed
**Date:** 2026-10-06
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.4

## Context

Two hypotheses from FINDINGS were left open.

- **F-11 refinement** (Story 2.8): at a fixed attack of 1.0× resources, the budget that
  decides the price at 2× and 4× D\* is the same, so "the budget scales with depth" was
  withdrawn. The replacement was "above the crash depth the defender must out-spend
  something set by the attack". One attack size had been tested.
- **F-13** (Story 3.2): the late-conservative defender (2% trigger, 10% pace) was fastest
  to parity because it paid least per stable. Its two labels moved together, so the sweep
  could not say whether the trigger or the pace was doing the work.

Story 3.4 runs two sweeps: budget × attack at 2× D\*, where the price is what's lost
rather than the clock, and defender pace × trigger × attacker pace at D\*.

## Decision

**1. Price-loss metric for the budget × attack sweep: p(never re-enters)** =
`1 − steps_to_first_band_entry_n / n` (`charts.p_never_reenters`, Wilson bounds). It does
not count a late re-entry as a loss, so the clock cannot leak into it. Next to it,
`p_stays_broken` mixes the two in this grid. For example, at 2× budget and 1× attack,
p_never = 0 but p_stays_broken = 0.375, a median re-entry at 36.6 h, which is the clock.

**2. Sweeps.** `sweeps/budget-x-attack-mc.yaml` (200 runs) and
`sweeps/pace-x-trigger-mc.yaml` (256 runs), with numbers and origins in their headers.
The attacker's pace 0.02 is about five times slower than the base 0.1 (it sells 99% of its
stock in ≈ 228 steps against ≈ 44). The story's "500 instead of 50" was a rough figure.

**3. Charts.** `plot_budget_attack` reuses `budget_crossing` and a new `loglog_slope`
(factored out of `plot_budget_depth`, same arithmetic). `plot_pace_trigger` reuses
`time_to_parity_hours` and a new `_parity_grid` (factored out of `plot_time_to_parity`,
same drawing). The 2× D\* label uses a `D_STAR` constant, because the sweep overrides the
depth and the manifest's `base_config` no longer carries D\*. It is used for a label only.

**4. Extraction candidate (AC 3).** Extraction = `capital + attacker_pnl`, the reference
the attacker took out of the pool. Its stock is fully sold by the end of every run, so the
end PnL is reference received minus capital, with nothing marked to market. The Dev Notes
wrote "`−attacker_pnl`", which is the attacker's *loss*, i.e. the discount it gave up, not
what it extracted. `scripts/budget_attack_table.py` tests both, interpolated along the
budget column at the crossing.

## Findings

**A. The crossing budget is proportional to the attack, not to extraction.** The values
below are the 0.5 crossings of p(never re-enters). Every cell is exactly 0 or 1 (8/8
seeds), so on the 5-point story grid each crossing is the midpoint of its bracket. A
diagnostic re-run at budget steps of 0.125× (`budget-x-attack-fine`, 1,240 runs, not
committed) tightens them.

| attack (× resources) | story grid | fine probe | budget / attack (fine) |
|---|---|---|---|
| 0.5 | < 0.5× (holds at every budget) | < 0.25× | — |
| 0.8 | 1.25× | 1.10× | 0.317 |
| 1.0 | 1.75× | 1.56× | 0.360 |
| 1.5 | 2.5× | 2.55× | 0.392 |
| 2.0 | > 3× (not reached) | 3.19× | 0.367 |

Log–log slope against attack: **1.08** (story grid, 3 points) and **1.16** (fine, 4 points).
Against extraction: 1.40 / 1.39, with budget/extraction rising steadily from 0.61 to 0.82.
Against the attacker's loss: 0.84 / 1.00, with spread 20% / 17% against 11% / 21% for
attack size. The loss fits about as well as attack size, but like extraction it is an
outcome of the budget itself (more budget gives the attacker better prices). Attack size
is the only candidate that is an input. Extraction also contains the defender's own
spend (the reference the defender puts into the pool is what the attacker takes out), so
"tracks extraction" is partly circular.

**Why (conservation, F-02/F-03).** At the first holding budget in each column, the
defender, holder and redemption together absorb 96–99% of the attacker's stable. The
defender's share rises with the attack (62% → 87%) because the other two are fixed: the
holder's 18.3M of reference (26% → 9% of the attack) and capacity-limited redemption
(7.6% → 3%). The defender pays an average of 0.43–0.52 per stable. So the crossing
budget ≈ price paid × (attack − fixed absorbers), which is roughly proportional over
0.8–2×. Below about 0.5× the holder and redemption absorb enough that a 0.25× budget holds.

**F-11 sentence:** at a pool too deep to crash, holding the price against an attack of X
needs a budget of ≈ 0.36·X (0.32–0.39 over X = 0.8–2× resources), and below X ≈ 0.5×
resources the believers and redemption hold it without the defender.

**B. Trigger does nothing; pace is everything, and what matters is pace relative to the
attacker.** On the AC grid at attacker pace 0.1, time-to-parity by defender pace is
0.05 → 0.4 h, 0.1 → 29.9 h, 0.2 → 48.2 h (clock), 0.5 → 53.1 h (clock). It is the same
at every trigger 0.5–4%, except that at pace 0.05 the 2% and 4% triggers take 0.9 and
1.3 h instead of 0.4. The attacker's first sale on step 50 is 10% of 179.5M = 17.9M
stable into a 16.7M stable side, which alone puts spot near 0.23 (−7,700 bps). At pace
0.02 it is 3.6M, which puts spot near 0.67. Either way every trigger up to 4% fires on
the first step of the attack. Troughs are −7,681 to −8,698 bps (fast) and −9,440 to
−9,727 bps (slow). The 0.1 / 0.2 / 0.5 rows are exactly F-13's
late-conservative / calibrated / early-aggressive times (29.9 / 48.2 / 53.1 h), so
F-13's "late" label was the pace alone.

At attacker pace 0.02, every one of the 128 runs never re-enters: the price is lost at
every defender pace and trigger. The defender pays 0.41–0.68 per stable, against
0.26–0.36 against the fast attack. A diagnostic probe at trigger 1%
(`pace-slow-attack-probe`, 80 runs, not committed) with slower defenders:

| defender pace | vs attacker 0.02 | vs attacker 0.1 |
|---|---|---|
| 0.0025 | 2.0 h | 0.8 h |
| 0.005 | 2.0 h | 0.5 h |
| 0.01 | 7.9 h | 0.4 h |
| 0.02 | 47.1 h (clock) | 0.4 h |
| 0.03 | never | 0.4 h |
| 0.05 (AC grid) | never | 0.4 h |
| 0.1 (AC grid) | never | 29.9 h |

The best defender pace moves down with the attacker's pace by about the same factor.
At half the attacker's pace the defender is back in hours (0.4 h / 7.9 h). At equal pace
it is back late (29.9 h / 47.1 h). At 1.5–2× the attacker's pace it misses the deadline
or never re-enters. The relationship is not exact, since the hours at equal ratio differ,
but the ratio is the first-order quantity.

**F-13 sentence:** the defender that wins is the one that spends more slowly than the
attacker sells. Time to parity is set by the defender's spending pace relative to the
attacker's selling pace, and the trigger does not matter, because a fast first dump
crosses every trigger up to 4%.

## Predictions checked (story Dev Notes)

1. Crossing budget rises less than proportionally (slope 0.3–0.7): **missed.** The slope
   is 1.08 / 1.16.
2. Crossing tracks extraction more closely than attack size: **missed.** Extraction gives
   slope 1.4 with a drifting ratio.
3. Time-to-parity varies mostly along pace: **held** (along pace only).
4. Trigger matters only at 4%, where the defender starts after the attacker has finished:
   **missed.** 4% is crossed by the first dump, and the trigger moves nothing beyond ≤ 0.9 h.
5. At attacker pace 0.02 the best defender pace moves down: **held**, but only visible in
   the diagnostic probe. On the AC grid every cell at 0.02 is "never".
6. Average price paid falls monotonically with slower pace at every trigger: **held** on
   the AC grid at both attacker paces. In the probe it bottoms out at 0.005 (0.171) and
   rises again at 0.0025 (0.186).

## Consequences

- F-11 refinement gains its tested clause: proportional to the attack (≈ 0.36×) at 2× D\*.
  Headline 2's "unless it roughly doubles its budget" becomes "unless its budget is about
  a third of the attack".
- F-13 is restated around relative pace. Charter chart 5 and the note should name the
  pace, not "late". A trigger axis is not needed again at calibrated scale.
- New finding candidate: **the attacker's pace is a lever as large as its size.** The same
  1.0× attack sold five times more slowly beats every defender pace from 0.05 to 0.5 at
  every trigger. Each defender buys near par while stock is still coming (it pays
  0.41–0.68 against 0.26–0.36). This is F-13 seen from the attacker's side.
- The diagnostics suggest a defender rule keyed to observed selling (spend pace as a
  fraction of the attacker's flow) for Epic 3/4. Not built here.

## Alternatives considered

- **p_stays_broken for the budget × attack heatmap:** rejected per AC 2 and the 3.3
  learning. It counts late re-entry, and at 2× budget / 1× attack it would say 0.375
  where the price is held in every seed.
- **Committing the fine and slow-attack probes as sweeps:** not done. They are
  diagnostics for the Completion Notes. The AC grids are the committed figures, and the
  probe specs are one-line axis changes reproducible from the committed specs (Debug Log).
