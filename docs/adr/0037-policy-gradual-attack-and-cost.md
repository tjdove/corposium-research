# ADR-0037: Policies under a gradual attack: against a 2%/1%-per-step attacker no policy recovers, every trigger still binds on the first sale, and the slow defender still has the smallest discount, by a shrinking margin; `discount_bps_hours`

**Status:** Accepted (finding + interface; review 2026-10-16, unamended; F-13 second refinement)
**Date:** 2026-10-16
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.3 (referee §5.21–5.23; F-13 and its refinement)

## Context

The referee made two points about F-13. In the Story 3.2 policy sweep the attacker sells
10% of its stock in its first step, so spot is near 0.23 before any trigger can act and
the triggers are inert by design of the shock. And the model charged nothing for time
spent below par, so a defender that waits and buys the bottom wins by construction.
Story 5.3 adds a cost-of-discount metric and reruns the five policies with the attacker
selling 2% and 1% of its remaining stock per step.

## Decision

1. **`discount_bps_hours`** (summary key, `mc.parquet` aggregate):
   `sum(max(0, -peg_deviation_bps) * record_every * interval_seconds / 3600)` over the
   recorded steps from the attack start to the end of the run.
   - **Attack start:** the step of the first attacker's first executed AMM sale
     (`swap_executed` with that agent as `source`), not its configured `start_step`.
     That step's row already shows the price after the sale.
   - **Against par always,** whatever `peg_recovered.reference` is.
   - **`None`** when the world has no attacker or the attacker never sells.
   - **NaN deviations** add nothing.
   - Each recorded row stands for `record_every` steps, which is exact at the default
     of 1.
   - Summary columns are not in the scenario hash, so no scenario hash changes; the
     pinned-hash tests confirm it.
2. **Sweep** `sweeps/policy-comparison-gradual-mc.yaml`: `policy-comparison-mc.yaml` plus
   an `agents[type=attacker].pace` axis over {0.1, 0.02, 0.01}, 720 runs. It is added to
   the Makefile's `SWEEPS`.
3. **Chart interface.** `plot_policy_comparison` draws a sweep with an attacker-pace axis
   through `_plot_policy_by_pace` into `policy_comparison_gradual.png`. That chart has
   one row per pace and a fourth panel (d), `discount_bps_hours`. Its time to parity
   comes from `policy_cells`, which takes the per-run median from `sweep.parquet`, so it
   does not need the trough step to be the same for every seed (`time_to_parity_hours`
   does). A sweep without a pace axis is drawn exactly as before; `policy_comparison.png`
   is byte-identical.
4. **Scripts.**
   - `policy_table.py` gains `--sweep` (the positional argument still works), price paid
     and `disc_bps_h` columns, and a second table naming the policy that minimises each
     measure, with `agree` (yes / no / "-").
   - New `scripts/trigger_table.py` reads the sweep's per-run events and timeseries
     without rerunning anything. It reports the step the trigger binds, the price the
     trigger read and how much the attacker had sold by then.
5. **Finding** (`docs/calibration/POLICY.md`):
   - **The slow attacker beats every policy.** At paces 0.02 and 0.01, P(never recovers)
     is 1.00 for all five policies at 0.5, 0.7 and 1.0×. Only at pace 0.02, 0.5× does any
     buyer re-enter, at 57.5–58.7 h, after the 37 h deadline.
   - **The slow attack goes deeper.** With a buying defender the mean trough is −8,797
     to −9,802 bps at pace 0.01, against −5,774 to −8,698 at pace 0.1.
   - **The defenders pay more.** The buyers pay 0.720–0.911 per stable at pace 0.01,
     against 0.283–0.579 at pace 0.1.
   - **The triggers are still inert.** At pace 0.01, ratio 1.0, seed 1000, all four
     defenders act at step 51, on the price left by the attacker's first sale (0.815; 1%
     of the attack sold). At ratio 0.5 that price is 0.900, still past the 2% trigger.
     No cell of this sweep separates the triggers.
   - **Late-conservative still minimises `discount_bps_hours`** in all 9 pace × ratio
     cells. It also minimises time to parity in the 4 cells where any policy re-enters,
     so the two measures never disagree in this sweep. At 1.0× the margin over
     calibrated is 58% at pace 0.1 (87,082 against 208,755 bps·h) and 0.5% at pace 0.01
     (452,147 against 454,494).
   - **Early-aggressive has the largest discount of the buyers** in all 9 cells.
   - **At pace 0.01 the seeds do not matter:** every seed in a cell gives the same
     result.

## Consequences

- "Spend slower than the attacker sells" survives the cost-of-discount test in sign
  everywhere in this sweep. Against the gradual attacker it no longer decides recovery,
  because nothing recovers, and its advantage in cost shrinks to under 1%. What the note
  says about this is the dev manager's call (L-19).
- The referee's trigger point stands, now with numbers: at the calibrated pool depth even
  a 1%-per-step attacker's first sale moves the price 10–19%. The sweep cannot separate
  0.5%, 1% and 2% triggers. That would take a first sale that moves the price less than
  0.5%: about 42k stable into a 16.7M side (spot falls by about 2x / reserve), which
  is 0.02% of the stock per step at 1.0× and 0.05% at 0.5×. This is arithmetic from
  the constant-product pool, not a run.
- The code hash changes (summary, mc, charts), so the `v0.9-freeze` warning in
  `note-check` remains. `make_figures.py` was run on the existing sweeps; the 23
  existing PNGs are byte-identical.

## Alternatives considered

- **Lower bound at the attacker's configured `start_step`.** Rejected: an attacker that
  waits, or has nothing to sell, would start the clock. The two coincide in every run
  here (step 50).
- **Integrate from step 0.** Rejected by the story's Dev Notes. It would also charge calm
  noise before the attack.
- **A separate chart function for the gradual figure.** Rejected: AC 3 asks
  `plot_policy_comparison` to gain the facet. The dispatch on the pace axis keeps the
  existing figure's code path as it was.
- **A slower pace (0.001) to separate the triggers.** Not run: the story fixes the
  sweep at {0.1, 0.02, 0.01}, and that would be a new sweep.
