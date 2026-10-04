# ADR-0021: The par-expecting holder: semantics, fitted capital C*, and what it moves

**Status:** Accepted (finding, amended in review 2026-10-04: finding candidate promoted to F-09; the 1992 zero-edge round trip is recorded as a parametric coincidence of entry 2% = spread 200 bps, not a finding; sawtooth to be fixed by a fill price limit in Epic 3)
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.6 AC 8

## Context
F-08: the USDC replay fell to −5,769 bps against −1,373 observed because the model had no
buyer of the discounted promise. The calibrated baseline hid this: its AMM defender
absorbed 89% of the attack (10.26M reference against an 11.54M attack). The replay
correctly has no defender. Story 2.6 adds the missing agent and fits its size with D\*,
the attacker and pace held. The redeem rule was amended mid-story (Rulings 1). The
original rule was `capacity ≥ 0.1 × stable`, which a holder of fitted size could never
satisfy.

## Decision

1. **Holder semantics** (`agents/holder.py`). Starts with `capital` reference. One action
   per step, in order: `hold_buy` if AMM spot < `peg × (1 − entry_discount_pct/100)` and it
   has reference, swap `pace × reference`; else `hold_redeem` if `redeem_when_capacity` and
   the redemption queue is empty, redeem `min(available stable, capacity_per_step ×
   redeem_horizon_steps)` with `redeem_horizon_steps = 10` (constructor default, not
   config); else `hold_wait` while it holds stable (queued or not); else `hold_done`.
   Consequences of the rule as written:
   - A tranche normally takes several steps to pay, and the holder's own tranche keeps
     the queue non-empty, so it redeems about one tranche per `redeem_horizon_steps`
     steps, not one per step.
   - Redemption proceeds are reference, and the holder spends them again whenever the
     price is below its entry. It **recycles** capital through the redemption channel
     (spent 9.42M from 9.17M capital in the replay; 11.52M in soros-1992).
   - `hold_done` is not terminal. It never sells on the AMM and never draws from `ctx.rng`.
   - The entry price is relative to `peg_price` (1.0 in every scenario).
2. **`HolderConfig`** joins the `AgentConfig` union with four fields. Every pre-2.6
   scenario hash is unchanged with holders removed (`tests/test_holder_config.py` pins all
   seven).
3. **C\* = 9,166,667 model units** (trough −1,137.8 bps at step 10255):
   - **≈ $2,150,500,078** at `s` (units × 234.6);
   - **0.79×** the attacker's episode net burn (11,540,596 units, $2.71B);
   - **0.22×** Circle's $9.7B cash;
   - **0.55×** D\*.

   Fit rule (AC 4, amended): log grid 1M…100M. Pick the grid point closest to −1,373 and
   refine with 5 linear points strictly between its two neighbours. Re-pick over every
   distinct point run so far and refine again between the new pick's neighbours. Closest
   wins; ties go to the smaller capital. As run:
   - grid: 5M → −3,784.8 and 10M → −224.6, so the pick is 10M;
   - refine 1 between 5M and 20M: 7.5M → −2,206.7 is the new pick;
   - refine 2 between 5M and 10M: 8,333,333 → −1,652.8, 9,166,667 → −1,137.8.

   The first refinement's linspace repeats the pick (10M) as one of its five points. The
   rule was applied as written.
4. **Propagation.** Every other scenario gets `capital = C* × depth / D*`, the same
   `entry_discount_pct 2.0`, `pace 0.05` and `redeem_when_capacity true`. All four
   propagated scenarios sit at D\*, so each gets 9,166,667.

## Consequences

**The redeem-rule change moved the trough.** Rulings 1 expected it not to. Under the
original rule, 10M gave −1,052.1 bps at step 10361 and the fit picked 10M (2.6 Blockers).
Under the tranche rule, 10M gives −224.6 bps at step 8140. Weekend tranches (≤ 6,058 per
clear-queue step) return reference that the holder spends again below $0.98. Near the
cliff that recycled ~0.9M is enough to outlast the attack. C\* moved from 10M to 9.17M.

**Finding candidate: a single-entry buyer makes trough depth bimodal.** Trough against
holder capital, replay:

| capital | 5M | 5.83M | 6.67M | 7.5M | 8.33M | 9.17M | 10M | 20M |
|---|---|---|---|---|---|---|---|---|
| trough (bps) | −3,785 | −3,317 | −2,788 | −2,207 | −1,653 | −1,138 | −225 | −220 |

Below the cliff the buyer runs out of reference before the attack ends, and the attacker
sets the trough. Above it the buyer outlasts the attack, and the trough sits at about its
entry discount (−200 bps plus its own 1 bp fee and price impact). The observed −1,373 lies
on the steep side. Real discount buyers entered at a spread of prices, and a single
`entry_discount_pct` cannot land on the observation exactly. This motivates a later
multi-tranche holder, which this story does not build.

**Replay before/after** (VALIDATION.md has the full table):
- trough −5,769 → **−1,138 bps** (observed −1,373);
- trough time 31.6 h → **34.2 h**, outside the ±2 h target (pace was fitted in 2.5
  without the holder and is not re-fitted);
- back in the band at 85.3 h in both runs.

The holder absorbs most of the flow: it buys 9.50M stable against the 11.54M attack
(82%), where the calibrated defender put back 89%. It redeems 6.69M before the Monday
capacity change and 2.80M after; PnL +82.5k. Its 5%-of-reference buys overshoot par for
the first ~3.5 h of the attack, a sawtooth between +310 and −220 bps (a model artefact).

**Calibrated baseline / stress.** The outcome is unchanged: `peg_recovered` at step 7024
(baseline) and 7225 (stress), trough −1,253.2 and −1,231.0 at step 50. The trough is set
by the attacker's first 10% dump before anyone acts. The defender's spend falls by 41%:

| run | defender spent | holder spent | holder redeemed | holder PnL |
|---|---|---|---|---|
| baseline, before | 10,261,334 | n/a | n/a | n/a |
| baseline, after | 6,054,986 | 4,461,031 | 3,935,212 | +198,965 |
| stress, before | 10,261,842 | n/a | n/a | n/a |
| stress, after | 6,055,420 | 4,461,031 | 4,048,495 | +201,938 |

The holder absorbs first at −2% and the defender triggers at −1%. The defender still
does most of the work at the bottom, because the holder stops buying above $0.98.

**F-06 (boundary) moves out.** `probe_boundary.py`, calibrated baseline, 8 seeds:

| | all seeds recover through | first mixed | 50% recover | still mixed at |
|---|---|---|---|---|
| 2.5 | 0.325 | 0.35 | ≈ 0.39 | 0.45 (none at 0.475) |
| 2.6 | 0.425 | 0.45 | 0.50 | 0.60 (25% recover) |

The shift (+0.11 at the 50% point) is about twice the holder's face value as a share of
`budget + reserves` (9.17M / 179.45M = 0.051): it recycles its capital through redemption
and buys below par. Same direction as F-03 and the 2.5 F-06 refinement: a resource that
buys at a discount absorbs more than its face value. Nothing exhausts reserves in the
probe, with or without the holder.

**F-07 (1992 flip, dead zone).** Multiple scan 4.0–7.0 by 0.1 on `soros-1992`. Without
the holder it reproduces 2.5's table exactly. With it:
- **The flip stays at 5.7 (ratio 1.206).**
- **5.1 and 5.2 no longer exhaust**, so the boundary is now clean.
- **4.0–5.6 still stall at `max_steps`**, final −143 … −178 bps: the F-07 dead zone
  persists.
- In the dead zone the holder becomes the main redeemer at low multiples: 62.1M stable
  redeemed at 4.0 against the arbitrageur's 3.6M, falling to 12.9M against 87.8M at 5.6.
  It **loses money at every multiple** (−1.02M at 4.0 … −0.16M at 5.6). The defender's 200 bps spread makes the payout exactly $0.98, the
  holder's entry price, so every round trip loses the price impact of its own buy.
- At 6.0 the arbitrageur redeems 100,347,952 with the holder vs 102,758,495 without.
  Reserves exhaust at step 9549 vs 9550 (`steps_run` 9550 vs 9551). The holder is left
  with 9,219,585 stable it can no longer redeem, PnL −64,942 marked at spot (more if the
  broken promise is priced in).

On `soros-1992-no-defense` every multiple 4.0–7.0 exhausts with and without the holder.

**The holder is too small to matter to the 1992 verdict.** At C\*/D\* it is 3.6% of the
6× attacker (9.17M vs 255.8M), so it cannot test BACKGROUND §4's "convergence traders had
to switch sides": reserves exhaust at the same multiples whether or not a buyer who never
switches is present. What the model does show is narrower. Under a defended spread the
believer's redemption arbitrage pays nothing, it competes with the arbitrageur for the
same reserves, and it is left holding the broken promise.

## Alternatives considered
- **Keep the balance-scaled threshold (`capacity ≥ 0.1 × stable`).** At fitted size it
  never fires in any scenario; ruled out (Rulings 1, PROCESS L-13).
- **Redeem the whole balance when the queue is empty.** That puts one multi-million
  request at the head of the queue for days and starves the arbitrageur. The tranche
  bounds it to what the channel pays in ~10 steps.
- **Re-fit pace with the holder present.** The trough is now 3.2 h late, but pace is a 2.5
  parameter and re-fitting it would be two parameters fitted to one path. Ruled out of
  scope (Rulings 3).
- **A price limit on the holder's own buys** (stop at its entry price instead of `pace ×
  reference`). This would remove the sawtooth and make the holder cheaper. It is a new
  rule beyond AC 1; noted for the multi-tranche holder.
- **Interpolate C\* between 9.17M and 10M to hit −1,373 exactly.** That is hand-picking,
  and the curve is a cliff there; ruled out (Rulings 2).
