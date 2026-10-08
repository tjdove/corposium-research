# ADR-0031: LP withdrawal agent; liquidity flight helps the defender: the fleeing LP carries the attacker's stable out of the pool, and at D* the clock goes (F-03 confirmed from the other side, qualified)

**Status:** Proposed (finding candidate)
**Date:** 2026-10-08
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.8

## Context

Every surface so far held pool depth fixed. F-03 (ADR-0017) found that a shallower pool
makes a depeg deeper but its defense cheaper, and F-11 (ADR-0022, ADR-0023, ADR-0029)
found that at calibrated depth D* the issuer wins the price and loses the clock. The
charter calls liquidity that leaves when it is needed "the core Soros dynamic". Story 3.8
makes depth respond to price: an LP who owns part of the pool and withdraws it while the
peg looks lost. The question is what that does to the thresholds, seen from F-03's other
side: does flight help or hurt the defender?

## Decision

1. **AMM action.** `ConstantProductAMM.remove_liquidity(fraction)`, `0 < fraction ≤ 1`:
   both reserves scale by `1 − fraction` (spot unchanged, `k` by `(1 − fraction)²`);
   returns `LiquidityResult(fraction, stable_out, reference_out, reserve_*_after)`.
   `execute` routes `kind == "remove_liquidity"` (`params {"fraction"}`) before the swap
   code, which is not touched, and emits `liquidity_removed` or `liquidity_rejected`.
   Drain guard: a removal that leaves a reserve at or below zero (`fraction == 1`) is
   rejected (`"would drain reserves"`). Unknown kinds still reject as `swap_rejected`, as
   before. Committed alone (`fcea3d4`) with a fingerprint of every scenario's parquet,
   events, decisions, summary and checkpoints: byte-identical before and after.
   The `k` property test is now "non-decreasing between liquidity events", with removals
   drawn from a separate generator so the swap sequence it tests is unchanged.

2. **`lp_supply` on the AMM** (an interface the spec left open). The AMM keeps the
   outstanding liquidity in units of the initial pool: 1.0 at construction, times
   `1 − f` per removal. This is the LP-token supply, and it is what lets an agent convert
   shares to a fraction of the current pool without assuming it is the only LP. Swaps
   never read it. `snapshot()` carries `lp_supply` and `liquidity_removals` only after a
   removal, so every existing checkpoint is unchanged.

3. **The agent.** `LiquidityProvider(agent_id, share, panic_threshold_pct, pace)`: state in
   shares of the initial pool; each step with `amm.peg_deviation < −threshold/100` and
   shares left it removes `removed = min(pace × share_remaining, share_remaining)` shares
   as `fraction = removed / lp_supply`. Its fraction of the pool goes from `S` to
   `(S − s)/(1 − s)`, pinned by two consecutive withdrawals (0.05 then 0.0473684…, leaving
   0.405 of 0.905). Rules `lp_hold`, `lp_withdraw`, `lp_done` (`share_remaining ≤ DUST`,
   1e-9, so a geometric pace ends). One-way; never swaps, redeems or calls `ctx.rng`.
   PnL: withdrawn reserves plus the remaining position, both at spot, against the starting
   position at peg. Judgment calls: a rejected removal is retried next step (a sole LP with
   `share 1, pace 1` is rejected forever by the drain guard); two LPs withdrawing in the
   same step each size from `lp_supply` as it was at decision time (one LP everywhere
   here).

4. **Scenario assumptions.** `calibrated-baseline-lp` = `calibrated-baseline-ou` + one LP
   with **share 0.5, panic threshold 5%, pace 0.1. None of the three has a public anchor**;
   the model's pool stands for aggregate depth (F-05), not one venue whose LP flows could
   be read. 5% sits above the holder's 2% entry and below the calibrated trough; 0.1 is the
   attacker's pace. The sweep varies share and threshold; pace is not varied.

5. **Two pool-depth metrics** (a judgment call; the dev manager may strike the second).
   The story context defines `pool_depth_at_trough = reserve_reference at the trough /
   initial`, and that is what the summary carries. But the reference reserve falls with
   price impact too: at ratio 1.0 with **no LP at all** it is 0.43 at the trough, so the
   panel the AC asks for would read as flight where there is none, and the story's
   prediction ("near 1.0 at 20%") assumes a metric that is 1.0 without flight. The summary
   therefore also carries `pool_liquidity_at_trough = sqrt(k_trough / k0)`, which swaps do
   not move and a removal of `f` scales by `1 − f`. The figure colours by the first and
   prints both. Both are in `mc.parquet`. Every existing scenario's `summary.json` gains
   the two keys; nothing else in any run output changes.

6. **Sweep.** `sweeps/lp-flight-mc.yaml`: threshold {2, 5, 10, 20}% × share {0.25, 0.5,
   0.75} × attacker {0.5, 0.7, 1.0} × resources, 8 seeds, par criterion, OU reference;
   288 runs, 49 s wall on 10 workers. `plot_lp_flight` → `docs/figures/lp_flight.png`.
   `scripts/lp_flight_table.py` reruns the same seeds with no LP and runs the threshold
   column at the episode-size attack (ratio 0.064), where the price actually hovers near
   the thresholds.

## Result

Sweep attacks, medians over 8 seeds (hours = run start to first re-entry; "recovered" =
`peg_recovered` within 60 h). The threshold columns are identical at every swept attack
(the first dump alone takes spot below 0.80, so every threshold fires), so one row per
share:

| ratio | no LP: trough / hours / recovered | LP 0.25 | LP 0.5 | LP 0.75 |
|---|---|---|---|---|
| 0.5 | −5,774 / 18.3 h / 8/8 | +0.0% / 11.5 h / 8/8 | +0.0% / 3.8 h / 8/8 | +0.0% / 0.4 h / 8/8 |
| 0.7 | −6,886 / 37.0 h / **0/8** | +0.6% / 27.2 h / 8/8 | +0.4% / 17.0 h / 8/8 | −2.0% / 6.7 h / 8/8 |
| 1.0 | −8,151 / 48.2 h / **0/8** | +0.5% / 35.4 h / 8/8 | +0.9% / 22.5 h / 8/8 | +0.6% / 9.5 h / 8/8 |

(LP cells: trough change against no LP, same seeds.) The defender spends its whole
41.35M budget in every cell except ratio 0.5 / share 0.75 (39.9–40.2M). Pool liquidity at
the trough at ratio 1.0: 0.76 / 0.52 / 0.28 by share (`pool_depth_at_trough` 0.32 / 0.22 /
0.12); at ratio 0.5 it is 1.0 in every cell, because the trough is the first dump.

Episode attack (ratio 0.064, the scenario's own attacker), 8 seeds: trough −1,253.2 bps in
every cell, LP or not (it is the first dump, at step 50, before any LP can see a price);
first re-entry 0.3 h everywhere; defender spend 7.70M with no LP, down to 7.27M (share 0.5,
5%) and 6.62M (share 0.75, 2%); flight at 20% never fires. Base scenario, seed 42: see
Story 3.8 Completion Notes.

**Mechanism: the fleeing LP is a third sink.** F-02 said depth could matter only if the
attacker's stable had a third place to go besides the defender and redemption. A
withdrawing LP is one: it leaves pro rata with the pool as it is, and after a dump the
pool is full of the attacker's stable. At ratio 1.0, share 0.5, seed 1000 the LP leaves
with 13.0M stable and 5.6M reference against the 8.3M of each it put in; redemption fills
8.2M stable instead of 10.9M; the run recovers at step 13,637 instead of never. The pool that
remains is half as deep, so the stable that must be bought or redeemed to bring it back to
par is half as much. The LP does not lose by it at large attacks (PnL +1.9M on 16.7M at
spot) and roughly breaks even at the episode attack (−0.01M).

**Self-fulfilling flight.** A withdrawal never moves spot; it only makes the next swaps
move it more. At the episode attack the LP's withdrawals keep the post-trough sawtooth
below its own threshold for longer than the same seed without it: withdrawals vs panic
steps 16/18/22 vs 14 at 2% (share 0.25/0.5/0.75), 5/7/9 vs 4 at 5%, 1 vs 1 at 10%, none at
20%. So below ≈ 10% its flight feeds its own panic, by up to 2.25×, but it is bounded (it
stops when the attacker stops), never cascades, never deepens the trough it reacts to, and
still lowers the defender's spend.

## Consequences

- **Finding candidate (F-15):** "Liquidity that flees a depeg helps the defender: it leaves
  holding the attacker's stable. At calibrated depth a half-flighty pool takes the
  1×-resources attack from never holding par to recovered in 22 h, and deepens the trough
  by under 1%, because the first dump lands before anyone can flee."
- **F-03 confirmed from the other side, and qualified.** The cheaper-defense half is
  confirmed and larger than F-03's price channel alone, because flight removes stable as
  well as depth. The deeper-depeg half barely appears (≤ 0.9%; 0 when the first dump sets
  the trough): an LP reacting to an observed price is always one step behind the dump.
- **F-11 qualified.** "At D* the issuer loses the clock" assumed fixed depth. With any
  flighty share on the grid, the 0.7 and 1.0 cells go from 0/8 to 8/8 recovered: the clock
  at D* is a property of the pool keeping the attacker's stable.
- The LP's panic threshold is inert at every attack large enough to matter (like the
  defender's trigger, F-13 refinement). Share is the operative quantity.
- Not tested: flight at deeper pools (the sweep is at D* only), LP pace, several LPs,
  re-adding liquidity, and an LP that sells the stable it withdraws (it holds it, so it
  never re-enters the market; an LP that dumps it would be a second attacker).

## Alternatives considered

- **Agent tracks pool supply itself** (`1 − its own withdrawals`): correct only with one
  LP. Rejected for `lp_supply` on the AMM, which is the pool's own state.
- **Only the context's `pool_depth_at_trough`:** contracted, kept, but it reads 0.43 with
  no flight at all at ratio 1.0. Kept alongside `sqrt(k/k0)` rather than replaced.
- **Snap a near-empty LP to zero** (withdraw everything once the remainder is dust):
  changes the AC's `min(pace × remaining, remaining)` rule; `lp_done` at 1e-9 instead.
