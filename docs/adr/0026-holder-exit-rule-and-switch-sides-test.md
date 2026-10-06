# ADR-0026: Holder exit rule; the 1992 analogue does not need the believer to switch sides — a believer who stays and redeems breaks it sooner (finding candidate)

**Status:** Proposed
**Date:** 2026-10-06
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.3

## Context

BACKGROUND §4 says Black Wednesday worked because the convergence traders, who had bought
ERM currencies on the belief that parities would hold, reversed all at once. F-08 put the
model's version of those traders in place (the par-expecting holder, ADR-0021); F-12
showed that once capped (ADR-0024) the holder is a redeemer in waiting. Story 3.3 gives it
the other move — selling everything on the market once the peg looks lost — and asks
whether that switch is what exhausts the 1992 analogue's reserves.

## Decision

**1. Exit rule semantics.** `HolderConfig.exit_discount_pct: float | None = None`
(`0 < x < 100`, must exceed `entry_discount_pct`; the validator names the rule). Rule
`hold_exit`, checked first each step: the first time AMM spot is strictly below
`peg_price × (1 − exit_discount_pct/100)` the holder sells, in one `swap sell_stable`,
its `available_stable` — everything it holds that is **not already queued for
redemption**. AC 1 says "cancels nothing already queued but sells all stable it holds";
the queued part is still paid by the redemption module and settles against the holder's
balance, so selling it too would sell stable the holder no longer has to sell. If the
amount is ≤ `DUST` the rule records `hold_exit` with no action. Either way `exited` is
set; from then on every step records `hold_done` and the holder never buys or redeems.
`None` (default) never fires. `content_hash()` drops the field when `None`, and the
holder's observation and snapshot gain `exit_price`/`exited`/`sold_stable` only when the
rule is configured, so every existing scenario hash and every existing run output is
unchanged (`soros-1992` seed 42: 9553 steps, −5,975.4 bps, as in 3.1).

**2. `None` on a sweep axis** already worked: `set_path` validates a leaf through its
parent model, so `null` in a spec sets the optional field to `None` (tests added, no code
change). In `sweep.parquet` the column holds NaN for those cells; `aggregate_mc` already
groups with `dropna=False`.

**3. Sweep** `sweeps/holder-exit-1992-mc.yaml`: exit {never, 5, 10, 20, 40} × holder
capital {1, 5, 25} × C\* on `soros-1992` at 6× (1.27× budget + reserves), seeds 1000–1007:
120 runs, 17.6 s on 12 workers.

| exit | holder capital | p_exhausted | mean exhaustion step | mean trough bps | mean holder PnL | runs that exit |
|---|---|---|---|---|---|---|
| never | 1× C\* | 1.00 | 9,541.5 | −5,975 | +152,268 | – |
| 5% | 1× C\* | 1.00 | 9,541.5 | −6,489 | −3,306,716 | 8/8 |
| 10% | 1× C\* | 1.00 | 9,541.5 | −6,524 | −3,635,567 | 8/8 |
| 20% | 1× C\* | 1.00 | 9,541.5 | −6,616 | −4,162,620 | 8/8 |
| 40% | 1× C\* | 1.00 | 9,541.5 | −7,110 | −5,227,123 | 8/8 |
| never | 5× C\* | 1.00 | 9,564.5 | −2,794 | +492,607 | – |
| 5/10/20% | 5× C\* | 1.00 | 9,552.9 | −9,322 … −9,354 | −33.9M … −35.1M | 8/8 each |
| 40% | 5× C\* | 1.00 | 9,564.5 | −2,794 | +492,607 | 0/8 |
| any | 25× C\* | 1.00 | 9,656.4 | −256 | +566,420 | 0/8 |

(Trough is the median across seeds; the 1× C\* exit troughs include the holder's own
sale.) Holder with the holder removed entirely (diagnostic): p = 1.00, mean step 9,541.0.

**4. Flip scans** (`scripts/scan_1992.py`, seed 42, 4.0–7.0 by 0.1; "flip" = smallest
multiple from which every larger one exhausts):

| holder | exit | flip (ratio) | exhausts below the flip |
|---|---|---|---|
| none (diagnostic) | – | 5.7 (1.206) | 5.1, 5.2 |
| 1× C\* | never | **5.2 (1.101)** — reproduces 3.1 row for row | 5.0 |
| 1× C\* | 5 / 10 / 20 | 5.7 (1.206) | 5.1, 5.2 |
| 5× C\* | never / 10 | 4.9 (1.037) | none |
| 25× C\* | never | **4.9 (1.037)** | none |
| 25× C\* | 10 | **4.9 (1.037)** — identical rows: never reached | none |
| 25× C\* | 2.5 (diagnostic) | 5.7 (1.206) | 4.9–5.5 |

**5. Mechanism** (diagnostic, seed 42, redemption payouts by source): at 5.4× with 1× C\*
the holder that stays is paid 9.2M by redemption and the run exhausts at 11,474; the
holder that exits at 10% is paid 3k and the run stalls at `max_steps`. At 6× with 1× C\*
the exit changes nothing the reserves see: same step 9,553, the arbitrageur paid
100,691,106 either way; the sale only deepens the trough (−5,975 → −6,526). At 25× C\* the
never-selling holder is paid 29–41M of the 100.7M reserves (6× / 5×). An AMM sale is not
a claim on reserves: the pool absorbs it as price, and only the arbitrageur's
fee-band-limited redemptions carry any of it to the channel. A holder that stays
redeems at the floor with no profit threshold and supplies the redemption demand that
drains the F-07 residual.

## Consequences

- **Finding candidate (F-14):** in the 1992 analogue the believer does not have to
  switch sides for the peg to break; at 6× reserves exhaust at every holder size whether
  or not it sells, at a time set by the redemption channel's capacity (31.8–32.2 h).
  Switching sides moves the flip **up**, back to the no-holder 5.7×; a believer who keeps
  believing and redeems at the floor moves it **down** (5.2× at C\*, 4.9× at 5–25× C\*).
  The belief that breaks a peg is the one that holds and redeems, not the one that sells.
- At 25× C\* the exit rule is untestable at discounts ≥ 5%: the holder's own buying holds
  the trough at −225 … −272 bps across the whole scan. A 2.5% exit fires (≥ 5.6×), but
  early, while the holder holds little, so the outcome is the no-holder one.
- The verdict is model-bound: the model's reserves are reachable only through
  redemption, while in 1992 a sale of sterling to the Bank *was* a draw on reserves. In
  the model that path is the defender's AMM buying, and in every sweep run that exits the
  defender's budget is already gone (seed 42: last defender buy at step 2,335; exits at
  2,493 / 2,682 for 5% / 40% at 1× C\*, 4,519 for 10% at 5× C\*). Only the 25× C\* 2.5%
  diagnostic exits while the defender is still buying (exit 2,368, last buy 2,483 at
  5.6×), and there the holder holds little. A large believer turning while the defender
  still has budget is the untested case.
- `scripts/scan_1992.py` replaces the scratch scans of 2.5/2.6/3.1.

## Alternatives considered

- **Sell `balances["stable"]` including the queued part** (literal "all stable it holds"):
  rejected; the queue would pay out stable already sold, and the agent's balance would go
  negative.
- **Exit cancels the queued tranche:** contradicts AC 1 ("cancels nothing").
- **Add a 2.5% exit to the committed sweep** so 25× C\* actually exits: kept as a
  diagnostic only; the sweep is the story's spec.
