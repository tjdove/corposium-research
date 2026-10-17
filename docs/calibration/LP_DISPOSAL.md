# The fleeing LP that disposes of what it withdrew (Story 5.4)

F-15 found that liquidity which flees a depeg helps the defender, on one condition: the
LP holds the stable it withdraws. The referee (§4, §5.25–5.26) asked what happens if it
does not. An LP that dumped its withdrawn stable on the venue would be a second attacker;
one that redeemed it would be a second redeemer. This story builds both and reruns the
flight grid.

All numbers below come from one run of the sweep (216 runs, 51 s on Seoul with 12
workers). The no-LP rows come from the 24 runs that `lp_flight_table.py` reruns
(`lp-flight-nolp`). The commands and their output are in the story's Debug Log.

## What was run

- **Agent** (`src/depeg_sim/agents/lp.py`). `after_withdrawal` is `hold`, `sell` or
  `redeem`, and `disposal_pace` is 0.1. Each step the LP takes at most one action:
  - **Withdraw first.** While spot is below its panic price and it still has pool shares,
    it withdraws, as in Story 3.8.
  - **Then dispose.** On any other step, `sell` swaps 0.1 of its undisposed withdrawn
    stable on the AMM. `redeem` queues 0.1 of it at the back of the redemption queue that
    the holder and arbitrageur use.
  - **Holding is unchanged.** `hold` is Story 3.8's LP.
  - **No re-adding.** The reference it gets back is held, never added to the pool again.

  In practice the LP disposes only after its withdrawals stop. At 1.0×, share 0.5, seed
  1000 it withdraws on steps 51–241 and disposes on steps 242–594.
- **Sweep** `sweeps/lp-flight-disposal-mc.yaml` (spec hash `e15e1c4adcab`). This is the
  `lp-flight-mc` grid with the panic-threshold axis dropped (the threshold is inert at these
  attacks, ADR-0031, so it stays at 5%) and `after_withdrawal` added:
  - attack ratio 0.5 / 0.7 / 1.0 × (defender budget + redemption reserves);
  - LP share 0.25 / 0.5 / 0.75;
  - mode hold / sell / redeem;
  - seeds 1000–1007, 60 h horizon, par criterion, OU reference.

  3 × 3 × 3 × 8 = 216 runs.
- **Table** `python scripts/lp_flight_table.py --sweep output/lp-flight-disposal-mc`.
  **Figure** `docs/figures/lp_flight_disposal.png`. **New summary keys:**
  `lp_sold_stable`, `lp_redeemed_stable` and `lp_pnl`.

**Hours** are the median over seeds from the start of the run to the first re-entry into
±31 bps of par; "never" means fewer than half the seeds re-enter. A run counts as
**recovered** if it holds the band for 6,900 steps by the horizon, so a first re-entry
after 37 h cannot recover. Every seed in a cell gives the same hours and the same trough,
so the medians and means below are exact for every seed.

## Results

`hold` reproduces the Story 3.8 sweep at the 5% threshold exactly: every trough, every
hour figure and every recovered count in ADR-0031's table.

Recovered runs (of 8) and median hours to first re-entry:

| ratio | no LP | share | hold | sell | redeem |
|---|---|---|---|---|---|
| 0.5 | 8/8, 18.3 h | 0.25 | 8/8, 11.5 h | 8/8, 25.8 h | **0/8**, 38.2 h |
| | | 0.5 | 8/8, 3.8 h | 8/8, 26.1 h | 8/8, 34.2 h |
| | | 0.75 | 8/8, 0.4 h | 8/8, 17.4 h | 8/8, 0.4 h |
| 0.7 | 0/8, 37.0 h | 0.25 | 8/8, 27.2 h | 8/8, 36.2 h | 0/8, 57.6 h |
| | | 0.5 | 8/8, 17.0 h | 8/8, 30.6 h | 0/8, never |
| | | 0.75 | 8/8, 6.7 h | 8/8, 19.4 h | 0/8, never |
| 1.0 | 0/8, 48.2 h | 0.25 | 8/8, 35.4 h | **0/8**, 42.4 h | 0/8, never |
| | | 0.5 | 8/8, 22.5 h | 8/8, 33.4 h | 0/8, never |
| | | 0.75 | 8/8, 9.5 h | 8/8, 20.1 h | 0/8, never |

Mean trough in bps, with the change against no LP at the same ratio:

| ratio | no LP | share | hold | sell | redeem |
|---|---|---|---|---|---|
| 0.5 | −5,774 | 0.25 | −5,774 (+0.0%) | −5,930 (+2.7%) | −5,774 (+0.0%) |
| | | 0.5 | −5,774 (+0.0%) | −7,961 (+37.9%) | −5,774 (+0.0%) |
| | | 0.75 | −5,774 (+0.0%) | −9,181 (+59.0%) | −5,774 (+0.0%) |
| 0.7 | −6,886 | 0.25 | −6,927 (+0.6%) | −7,635 (+10.9%) | −6,927 (+0.6%) |
| | | 0.5 | −6,914 (+0.4%) | −8,755 (+27.1%) | −6,914 (+0.4%) |
| | | 0.75 | −6,748 (−2.0%) | −9,613 (+39.6%) | −6,748 (−2.0%) |
| 1.0 | −8,151 | 0.25 | −8,191 (+0.5%) | −8,432 (+3.4%) | −8,191 (+0.5%) |
| | | 0.5 | −8,226 (+0.9%) | −9,143 (+12.2%) | −8,226 (+0.9%) |
| | | 0.75 | −8,196 (+0.6%) | −9,721 (+19.3%) | −8,196 (+0.6%) |

Where the money went, at 1.0×, means over seeds in millions:

| share | mode | defender spent | channel paid, total | to the arbitrageur | LP's stable redeemed | LP sold on AMM | LP PnL |
|---|---|---|---|---|---|---|---|
| — | no LP | 41.35 | 10.87 | 10.87 | — | — | — |
| 0.5 | hold | 41.35 | 8.23 | 8.23 | 0 | 0 | +1.91 |
| 0.5 | sell | 41.35 | 10.21 | 10.21 | 0 | 13.01 | −9.10 |
| 0.5 | redeem | 41.35 | 10.87 | 1.35 | 9.52 | 0 | +0.03 |
| 0.75 | sell | 41.35 | 7.79 | 7.79 | 0 | 19.15 | −14.58 |
| 0.75 | redeem | 41.35 | 10.87 | 1.28 | 9.59 | 0 | +0.82 |

The defender spends its whole 41.35M budget in every cell except 0.5× at share 0.75 under
`hold` and `redeem` (39.88M). It buys the same stable in `hold` and `redeem` in every cell:
its buying is over before the LP's first redemption is paid. The full per-mode tables,
with all nine cells and the LP's redemption payout taken from each run's events, are the
script's output in the Debug Log.

## Reading

Numbers first, then what they say about F-15.

- **`sell`: recovery holds; the trough reverses.**
  - **Recovery.** At 0.7× and 1.0×, 5 of the 6 sell cells recover 8 of 8, against 0 of 8
    with no LP. The exception is 1.0× at share 0.25: 0 of 8, re-entering at 42.4 h, past
    the deadline (no LP re-enters at 48.2 h).
  - **But slower.** Every sell cell is slower than the same cell under hold, by 7.0–13.6 h
    at 0.7× and 1.0×. At 0.5×, shares 0.25 and 0.5 take longer than with no LP at all
    (25.8 and 26.1 h against 18.3 h).
  - **Trough.** It deepens by 2.7–59.0% against no LP, most where the flighty share is
    large and the attack small. F-15's "deepens the trough by at most 0.9%" does not
    survive selling.
  - **Timing.** The sell trough comes at steps 283–295, during the LP's own selling, not
    at the attacker's first dump (steps 50–86). The LP is a second attacker that starts
    selling once its withdrawals stop, about 190 steps after the first dump (step 242 at
    1.0×, share 0.5, seed 1000), not one step behind.
  - **Who absorbs it.** The arbitrageur takes everything the channel pays (10.21M at 1.0×,
    share 0.5): it buys the LP's stable cheaply and redeems it. The LP loses 9.10M where
    holding made it 1.91M.
- **`redeem`: the trough holds; recovery reverses.**
  - **Trough.** Identical to hold in every cell. The LP's first request comes after its
    withdrawals stop (step 242 at 1.0×, share 0.5, seed 1000), after the trough.
  - **Recovery.** 0 of 8 at 0.7× and 1.0× at every share, which is the no-LP result. At
    0.5×, share 0.25, it is worse than no LP: 0 of 8, re-entering at 38.2 h, against 8 of 8
    at 18.3 h with no LP. At 0.5× with shares 0.5 and 0.75 it recovers. At 0.75 the run is
    back in 0.4 h, as under hold, before most of the LP's tranches are paid (3.70M).
  - **The channel.** It pays its full throughput over the horizon (10.87M) in every 0.7×
    and 1.0× redeem cell, but mostly to the LP: 9.52M of it at 1.0×, share 0.5, and 1.35M
    to the arbitrageur, against 8.23M to the arbitrageur under hold.
  - **Why, in the builder's reading.** The LP's 13.0M is queued ahead of every later
    request. At 605.79 per step it would take about 21,500 steps (72 h) to clear, longer
    than the horizon. The arbitrageur's buy-and-redeem loop, which is what lifts the pool
    back to par after the defender's budget is spent, waits behind it.
  - **The LP itself** roughly breaks even (+0.03M), against +1.91M holding.
- **So the sign of F-15 splits between the two:**
  - Selling keeps the recovery (5 of 6 cells at 0.7× and 1.0×) and reverses the trough.
  - Redeeming keeps the trough and reverses the recovery, back to no LP's 0/8 at 0.7× and
    1.0×, and below it at 0.5×, share 0.25.
  - Holding is the only one of the three that helps on both counts. "Liquidity that flees
    helps the defender" is a statement about an LP that sits still.
- **The cost of the discount** (`discount_bps_hours`, Story 5.3) says the same:
  - hold is 28–98% below no LP in every cell;
  - sell is above no LP in 5 of 9 cells (−42% to +239%);
  - redeem is above no LP in 5 of 9 cells (−98% to +120%).

The prediction in the story, checked:
- **Sell deepens the trough:** yes, by 2.7–59.0% against no LP. But the LP is not "one
  step behind" the attacker: it sells only after it stops withdrawing, about 190 steps
  later.
- **Sell turns the 0.7× and 1.0× cells back toward 0/8:** no. Only 1.0× at share 0.25 is
  0/8; the other five such cells recover 8 of 8.
- **Redeem leaves the trough alone:** yes, exactly, in every cell.
- **Redeem's effect on recovery (left open):** it hurts. Every 0.7× and 1.0× cell is 0/8,
  and so is 0.5× at share 0.25.

## Limits

- **Two pacing assumptions, neither swept.** The LP disposes only on steps it does not
  withdraw (the story's one-action rule), and at one pace, 0.1. A faster disposal, or one
  interleaved with the withdrawals, would sell or queue earlier.
- **Disposal ignores the price.** The LP sells or queues every step until its withdrawn
  stable is gone, whatever spot is. No price limit (the story's spec).
- **One LP; `sell` and `redeem` are not mixed.** An LP that sells part and redeems part is
  not modelled.
- **Redeem's result depends on the channel's throughput:** 605.79 per step, calibrated to
  USDC's net burn over 11–14 March 2023 (`docs/calibration/SOURCES.md`), which caps the
  channel at about 10.9M in 60 h. A channel that widened under load would change it.
