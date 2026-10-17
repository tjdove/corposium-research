# ADR-0038: The LP's disposal of withdrawn stable: `after_withdrawal` (hold / sell / redeem) at `disposal_pace`, after withdrawing, through the shared redemption queue

**Status:** Accepted (finding + interface; review 2026-10-17, unamended; F-15 revised)
**Date:** 2026-10-17
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 5.4 (referee §4, §5.25–5.26; F-15's condition)

## Context

F-15 (ADR-0031) holds on the condition that the LP holds the stable it withdraws. Story 5.4
gives the LP two other things to do with it, selling it on the AMM or redeeming it, and
reruns the flight grid. The story fixed the outline: one action per step, withdrawal
first, sell or redeem `disposal_pace × held` stable, the same queue as the holder and
arbitrageur, no `ctx.rng`. This ADR records the semantics it left open.

## Decision

1. **Config.** `LPConfig.after_withdrawal: Literal["hold", "sell", "redeem"] = "hold"` and
   `disposal_pace: float = 0.1` (`0 < x ≤ 1`). `content_hash` drops each field when it is
   at its default, so all 16 scenario hashes and all 17 earlier sweep spec hashes are
   unchanged (checked against main; pinned in `tests/test_lp_disposal.py`). The LP
   scenario's `manifest.json` and the sweeps' `base_config` show the two defaults,
   because they dump the full config. Timeseries, events and checkpoints of
   `calibrated-baseline-lp` and `soros-baseline` are byte-identical to main.
2. **Decision order** (`agents/lp.py`; rules in the trace):
   - `lp_withdraw` while spot is below the panic price and shares remain;
   - else `lp_sell` or `lp_redeem` while undisposed stable remains;
   - else `lp_done` if no shares remain, `lp_hold` otherwise.

   Under `hold` the trace is exactly Story 3.8's. Disposal does not look at the price.
   - **Consequence:** the LP disposes only once it has stopped withdrawing (steps 242–594
     at 1.0×, share 0.5, seed 1000; its withdrawals are on steps 51–241).
   - **After the shares run out,** an LP still below its panic price disposes rather than
     reporting `lp_done`.
3. **Amounts.**
   - **`sell`:** swaps `disposal_pace × undisposed` on the AMM, side `sell_stable`, fee on
     input, no price limit.
   - **`redeem`:** queues `min(undisposed, disposal_pace × undisposed)`.
   - **The tranche rule:** the redeem tranche uses `disposal_pace`, not the holder's
     `min(stable, capacity × 10)`, so that the two modes dispose of the same amounts on
     the same steps. It is 353 actions on steps 242–594 in both modes in that run.
4. **`undisposed_stable`, the LP's own counter.** It rises by each withdrawal's
   `stable_out` and falls by each executed sale's `amount_in` and each accepted request's
   `queued`.
   - **Why not `available_stable`:** `balances − queued_redeem` is a difference of two
     ~1e7 floats that keeps a few-ulp residue (7.45e-9 in the first build), above `DUST`
     forever. The first build queued 17,758 near-zero requests, the last at step 17,999.
   - **The counter decays geometrically to below `DUST`.** The results did not change: the
     same run's summary agreed to the last few digits.
5. **The queue.** A redeem request goes to the back of the redemption module's FIFO queue,
   the same one the holder and arbitrageur use, with no priority.
   - **No wait for an empty queue:** the LP queues even when the queue is not empty, unlike
     the holder, which waits for one.
   - **Queued stable stays in `balances`** until it is filled (base `Agent`), so mark to
     market is unchanged.
6. **Proceeds.** The reference from a sale or a redemption is held. The LP never re-adds
   liquidity (ADR-0031), and its withdrawn reference is never touched.
7. **Summary columns** (`SUMMARY_KEYS`, `mc.parquet`):
   - `lp_sold_stable`: executed `amount_in`;
   - `lp_redeemed_stable`: filled `amount_stable`; the reference paid equals it at the
     calibrated spread of 0;
   - `lp_pnl`: the LP's `pnl_last`.

   All three are `None` without an LP, and the first two are 0.0 for a holding LP.
   `lp_pnl` is a third column beyond the AC's two: the AC 3 table needs LP PnL and no run
   output recorded it. The soros-baseline `summary.json` pin is re-captured; without the
   three lines it is Story 5.3's capture.
8. **Snapshot.** A disposing LP's checkpoint adds `after_withdrawal`, `sold_stable`,
   `redeemed_stable`, `undisposed_stable` and `queued_redeem`. A holding LP's checkpoint
   is unchanged.
9. **Sweep, table, figure.**
   - **Sweep** `sweeps/lp-flight-disposal-mc.yaml` (216 runs; in `SWEEPS`): the
     `lp-flight-mc` grid without its panic-threshold axis (inert at these attacks;
     threshold 5%), × `after_withdrawal`.
   - **Table.** `lp_flight_table.py --sweep` prints per-mode tables when the sweep has that
     axis, with a no-LP row per ratio. `lp_paid_M` comes from `redeem_fulfilled` events.
   - **Figure.** `plot_lp_flight` dispatches on the axis to `lp_flight_disposal.png`;
     `lp_flight.png` and the 23 other PNGs are byte-identical.

## Result (for the dev manager's finding)

Full tables in `docs/calibration/LP_DISPOSAL.md`. Medians over 8 seeds; every seed in a
cell gives the same result.

- **`sell`.**
  - **Recovery:** 8 of 8 in every cell except 1.0× at share 0.25 (0 of 8, re-entry at
    42.4 h, past the 37 h deadline). No LP recovers 0 of 8 at 0.7× and 1.0×.
  - **Trough:** deeper than with no LP by 2.7–59.0%, set at steps 283–295 during the LP's
    own selling.
  - **Cost to the LP:** it loses 4.28–14.58M at 1.0×.
- **`redeem`.**
  - **Trough:** identical to hold everywhere.
  - **Recovery:** 0 of 8 at 0.7× and 1.0× at every share, and at 0.5× with share 0.25
    (where no LP recovers 8 of 8).
  - **Channel:** it pays its full 10.87M in 60 h in those cells, mostly to the LP (9.52M at
    1.0×, share 0.5, against 1.35M to the arbitrageur).
- **The sign of F-15 splits.** Selling keeps the recovery and reverses the trough;
  redeeming keeps the trough and reverses the recovery. Only holding helps on both.

## Consequences

- F-15's condition is now a tested branch, not a caveat. What the finding says is the dev
  manager's call.
- **Untested:** disposal interleaved with withdrawal, any other `disposal_pace`, a
  price-limited sale, an LP that sells part and redeems part, and several LPs.
- Every `summary.json` gains three keys; the code hash changes, so `note-check`'s
  `v0.9-freeze` warning remains.

## Alternatives considered

- **Holder's tranche rule for `redeem`** (`min(stable, capacity × 10)`, queue only when it
  is empty). Rejected for this story: it would make `redeem` wait politely and `sell` not,
  so the two modes would differ in two ways at once. The story chose `disposal_pace`.
- **Dispose and withdraw in the same step.** Rejected by AC 2 (one action per step). It
  would bring disposal forward by about 190 steps at the swept attacks.
- **Size disposal from `available_stable`.** Rejected (item 4): float residue.
