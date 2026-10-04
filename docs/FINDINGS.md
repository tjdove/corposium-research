# Findings Log

**What this is:** the running narrative of what the simulator has taught us, in the order
we learned it. One entry per finding. Each entry says what we expected, what we saw, why,
how to reproduce it, and what it changed. This file is the spine of the research note:
section 4 of the note is written from it.

**Rules:** append-only. A finding is never deleted; if a later finding refines or
overturns it, the later entry says so and the earlier entry gets a one-line
`Superseded/refined by F-NN` note. The dev manager adds an entry whenever a review
accepts a finding ADR. Every entry links its ADR, its scenario or sweep, and the exact
command that reproduces it.

**Headline candidates** are collected at the bottom and ranked; the ranking changes as
findings accumulate.

---

## F-01 · The dead zone: a peg can be permanently slightly broken with no one incentivised to fix it

**Date:** 2026-10-02 · **ADR:** [0010](adr/0010-dead-zone-finding.md) · **Story:** 1.7
**Reproduce:** `git checkout 7b4d2e1 && pytest tests/test_agents_integration.py -k dead_zone`
(the test pins the original 10 bps tolerance so the behaviour stays reproducible after the
baseline retune)

**Expected.** With a 300k attack on a 1M/1M pool, a 400k defender and a 200k arbitrageur,
the price would either recover to peg or reserves would run out.

**Observed.** Neither. The attack drives the price to −573 bps, the defender buys it back
to roughly −18 bps, and it stays there to step 5000. Run ends only by `max_steps`.

**Why.** −18 bps sits inside the arbitrageur's no-trade band (30 bps AMM fee + 20 bps
minimum profit = 50 bps), above the defender's −100 bps trigger, and outside the 10 bps
recovery tolerance. Every actor's rule says "do nothing." The remaining gap is smaller
than anyone's cost of closing it.

**What it changed.** `peg_recovered.tolerance` must sit outside the arbitrage band
(ADR-0013), or "recovered" is unreachable by construction. The baseline was retuned to
60 bps tolerance in 1.8. More importantly it reframed what "recovery" means in the model:
*back inside the band where no rational actor trades*, not "back to par."

**For the note.** This is a real property of fee-bearing markets, not a modelling
artefact: a stablecoin can trade a few bps off peg indefinitely because closing the last
gap costs more than it yields. The 1992 parallel is weak here (the ERM band was ±6%,
far wider than any arb band), but the DeFi parallel is exact: USDT and USDC routinely
trade at 99.9x for weeks.

---

## F-02 · Outcome is decided by capital vs defense resources, not by pool depth

**Date:** 2026-10-03 · **ADR:** [0016](adr/0016-outcome-set-by-capital-not-depth.md) · **Story:** 2.1
**Reproduce:** `python -m depeg_sim.sweep sweeps/pool-depth-x-attacker.yaml --workers 4`
then pivot `sweep.parquet` on `pool_depth × capital` → `terminated_by`

**Expected.** The 16-cell sweep (depth {250k…2M} × capital {100k…1.2M}) would show the
outcome flipping along a diagonal: small attack into a deep pool recovers, big attack into
a shallow pool exhausts.

**Observed.** It flips by column. At every depth, capital ≤ 600k recovers and 1.2M
exhausts reserves. Depth only sets the trough: −5430 bps at 250k vs −1206 bps at 2M for
the same 1.2M attack. The trough is a function of the capital/depth ratio (the
constant-product price impact of the first dump: 300k/250k, 600k/500k and 1.2M/1M all
give −2025 bps).

**Why.** The attacker's stable has exactly two places to go: the defender's AMM buys, and
redemption (via the arbitrageur, who buys cheap stable and redeems at 0.999). Pool depth is
not a sink; it is a price. So the verdict is `attacker_capital ≷ defender_budget +
redemption_reserves` (adjusted for prices paid), and depth cannot enter unless a third
sink exists. 600k < ~900k survives; 1.2M > ~900k does not.

**What it changed.** The headline chart's primary axis became `capital / (budget +
reserves)`, with depth as a secondary dimension. Story 2.2's grid was redesigned to test
the prediction across budget/reserves splits.

**For the note.** This is Krugman (1979) / Flood–Garber (1984) in miniature: the attack
succeeds when speculative capital exceeds the reserves that can be thrown at it, and
market structure changes the path, not the verdict. See `BACKGROUND.md` § "How economists
explain it."

*Refined by F-03: depth does enter, through the "prices paid" term.*

---

## F-03 · Shallow liquidity makes a depeg deeper but a defense cheaper

**Date:** 2026-10-03 · **ADR:** [0017](adr/0017-depth-enters-through-defender-price.md) · **Story:** 2.2
**Reproduce:** `python -m depeg_sim.sweep sweeps/capital-vs-resources-mc.yaml --mc --workers 4`
then bin `mc.parquet` by `capital / (budget + reserves)` per `pool_depth` (method in the
2.2 story Dev Notes; ~16 s on 4 cores). Quick check (48 runs): a 2×3 slice at capital
{900k, 1.0M, 1.1M}, budget 400k, reserves 500k, depths {500k, 2M}: at ratio 1.111 the
500k pool survives (p=0) and the 2M pool breaks (p=1).

**Expected.** Per F-02, the 0.5 crossing of `p_reserves_exhausted` would sit at ratio
≈ 1.0 and `pool_depth` would not move it.

**Observed.** The crossing sits just above 1.0 — but at **1.10 for the 500k pool and 1.03
for the 2M pool**. Six grid points flip from surviving at 500k to exhausting at 2M. The
deeper pool breaks at the lower ratio. Within a depth the transition is nearly a step
(3 of 126 grid points mixed); 5 bps/step noise barely matters.

**Why.** F-02's conservation law holds exactly; the "adjusted for prices paid" clause was
the whole story, and depth controls it. In a shallow pool the attack crashes the price
harder, so each unit of defender budget buys more stable (1.19 stable per budget unit at
500k vs 1.02 at 2M). A deep pool holds the price near par, so the defender pays nearly
par and its budget absorbs less. A price-adjusted ratio (`capital / (stable the defender
actually bought + reserves / 0.999)`) separates all 2016 runs at a single threshold of
1.005 with 5 errors, versus 93 errors for the nominal ratio. (Diagnostic, not predictor:
"stable bought" is an outcome.)

**What it changed.** The 2.6 chart gets two lines or panels (500k and 2M) so the shift is
visible. The reserves/budget split matters mildly through the same channel. A
600k-budget/250k-reserves irregularity (reserves run dry before the defender finishes)
points at redemption capacity as a possible future axis.

**For the note.** This is the counterintuitive result and the likely lead. "Deep
liquidity protects the peg" is the standard DeFi intuition and it is half right: depth
protects the *price* during the attack but makes the *defense* more expensive per unit,
because the defender has to buy at closer to par. The trade-off is between how bad the
depeg looks and how much the defense costs. A thin market shows a terrifying chart and
survives; a deep market shows a mild chart and runs out of money.

---

## Headline candidates (ranked, 2026-10-04)

1. **"Shallow liquidity makes a depeg deeper but a defense cheaper."** (F-03) — the
   surprise; mechanism clean; one sentence.
2. **"Liquidity depth decides how far the peg falls; defense resources decide whether it
   comes back."** (F-02, qualified by F-03) — the first-generation result, stated for DeFi.
3. **"A peg can be permanently slightly broken with no one incentivised to fix it."**
   (F-01) — true, important for how "recovery" is measured, but less novel.

The note probably leads with 1, states 2 as the framework, and uses 3 in the methods
section to justify the recovery criterion.

---

## Open questions the next findings should answer

- Does the F-03 boundary survive calibrated parameters (2.3)? The calibrated baseline is
  placed on it by design.
- Under realised stress volatility (March 2023 window), does `peg_recovered` remain
  reachable, or must the criterion widen? (2.3)
- Does the 1992-analogue scenario reproduce reserve exhaustion with the historical ratios?
  (2.4)
- Does the model's USDC-2023 trajectory match the observed trough and recovery timing?
  (2.5)
- Is there a parameter-only predictor of the F-03 boundary (a closed form for expected
  defender absorption as a function of capital/depth)? (note appendix, not a story)
