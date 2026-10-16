# ADR-0035: Closed weekend channel: with redemption shut (or at 10%) until 85 h, the trough falls to the 20% tranche (−2,001) and the price stays near it until the reopening, then is back in band by 85.3 h (observed 86.0 h); capacity 0 allowed; a figure's observed source

**Status:** Proposed (finding + interface)
**Date:** 2026-10-16
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.5 (F-16; outside review 1, §5.15–5.16)

## Context

F-16: on the par-reference replay the model is back at par from about 40 h, while the
observed price stayed 150–524 bps below par until 69 h and re-entered the band at 86 h.
The referee pointed out that the calibrated weekend capacity (605.79/step) is an average
over 11–15 March that includes Monday's catch-up. Story 5.5 reruns the par ladder-B
replay with the weekend channel at 10% (60.579/step) and at 0 until the step-25,500
(85 h) reopening. Nothing is re-fitted.

## Decision

1. **Capacity 0 is allowed** (`RedemptionConfig.capacity_per_step: ge=0`,
   `RedemptionModule` `>= 0`). It was rejected before (`gt=0`, `> 0`). Nothing divides
   by capacity. `process` fills nothing while it is 0 and requests still queue. The
   holder's tranche, `min(available, capacity × redeem_horizon_steps)`, is 0, so it falls
   through to `hold_wait` (unchanged code). `capacity_schedule` entries must still be
   > 0. No tiny positive number is used anywhere.
2. **Scenarios** `usdc-2023-tranches-par-slow.yaml` and `-closed.yaml`: the base with only
   `name` and `redemption.capacity_per_step` changed (pinned in
   `tests/test_closed_channel.py`). `replay_table.py` gains the two rows (built-in list).
   `scripts/closed_channel_table.py` prints the 35–85 h window, the reopening, the
   arbitrageur's buying and the holder at 85 h and 112 h.
3. **Finding** (VALIDATION.md "Closed weekend channel (Story 5.5)"):
   - **The trough deepens.** −1,279.2 bps (open) becomes −2,001.1 at 31.9 h (10%) and
     −2,001.2 at 31.6 h (closed), the 20% tranche's entry, 45.7% deeper than the observed
     −1,373.3. In 27–31 h the arbitrageur buys 923,919 of reference on the AMM when the
     channel is open (724,525 paid back to it), 272,392 at 10% (72,452 paid), and 200,000
     closed (its capital, in four buys; nothing paid).
   - **35–85 h.** Closed: −2,000.0 to −2,000.2 bps, the whole window. 10%: −2,000.2 to
     −1,060.9, mean −1,563.9. Open: −1,084.3 to −0.0, mean −66.6. Observed hourly closes:
     −955.4 to −48.4, mean −335.4. Neither cut-channel run spends any time in band.
   - **The reopening.** The queue before it is all the arbitrageur's: 201,339 (closed) and
     395,584 (10%). It is empty by 85.38 h and 85.23 h. The price does not go lower after
     the reopening, and it is back in band at 85.31 h and 85.16 h. Over 27–96 h: first back
     in band 85.3 / 85.2 h (observed 86.0, open 40.4); hours in band 10.7 / 10.9 (observed
     8.0, open 55.6).
   - **The holder.** Closed, it queues nothing before 85 h. Over 35–85 h it buys at the
     20% entry on 12,750 of 15,000 steps (all 20% tranche) and waits on the rest. At 85 h
     it holds 9,370,888 stable and has PnL −1,205,605 (marked at 0.80). At 112 h it has
     redeemed it all, with PnL +668,573 (open: +521,604). At 10%: 9,128,561 stable and
     −348,569 at 85 h, +619,886 at 112 h.
4. **Interface: a figure's observed source.** `make_figures.Figure.observed` names a
   scenario that is run only for the CSV its manifest names and checksums. `render`
   passes its run directory as `observed_from`. The manifest entry adds
   `observed_source` and `observed_source_hash`, and `check_figures.stale_figures` checks
   them like `second_source`. `plot_validation_overlay(run_dir, second_run_dir=None,
   observed_from=None)` reads the CSV from `observed_from` when it is given (else from
   `run_dir`, as before). When the two drawn runs' starting capacities differ, it names
   each one's weekend channel in the legend and title, wraps the title, and puts the
   legend below the axes. Every existing figure's labels and layout are unchanged.

## Consequences

- New committed figure `validation_overlay_usdc_2023_tranches_par_closed.png` (23
  figures), marked † in the note's figure list.
- With the channel cut, the model matches the observed recovery time (85.3 vs 86.0 h)
  and hours in band (10.7 vs 8.0), and misses the trough by 45.7% and the 35–85 h level
  (−2,000 vs mean −335). With the channel open it is the reverse (ADR-0033). What this
  means for F-16 and the note is the dev manager's call (L-19: numbers first).
- The 85 h numbers come from checkpoints written at the reopening step
  (`metrics.checkpoint_every` set to 25,500 in the analysis runs only). The committed
  scenarios keep 6,900.

## Alternatives considered

- **A tiny positive capacity (e.g. 1e-9) instead of allowing 0.** Rejected by the story,
  and it would leave a channel that pays something.
- **Allow 0 in `capacity_schedule` entries too.** Not needed here (the reopening is > 0),
  so left out as the smaller change. A later story that closes the channel mid-run would
  need it.
- **Draw the figure from two sources** (grey = observed-reference replay). Rejected: AC 3
  wants the grey line to be the par-reference open channel, and neither par run has the
  CSV. ADR-0033 already rejected a fixed CSV path, because the sha256 check needs a run
  manifest.
- **Truncated runs at 25,500 steps for the 85 h state.** Rejected for one run per channel
  with a checkpoint at the reopening step: the 85 h and 112 h numbers then come from the
  same run.
