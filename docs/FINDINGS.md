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

## F-04 · Under realised stress volatility, "recovery to peg" is mostly unreachable — the reference itself wanders more than the band

**Date:** 2026-10-04 · **ADR:** [0018](adr/0018-calibration-judgment-calls.md) (amendment) · **Story:** 2.3
**Reproduce:** run `scenarios/calibrated-stress.yaml` over seeds 1000–1031 (a 1×32 sweep);
count `terminated_by == "peg_recovered"`

**Expected.** With sourced parameters, the stress scenario (March 10–13 2023 realised
volatility, 7.561e-4 per 12 s step) would recover like the calm one.

**Observed.** 5 of 32 seeds recover; 27 run to `max_steps`. The calm scenario (3.086e-5)
recovers in 31 of 32. Seed 42 happens to be one of the five, so the story's AC passed by
luck; the builder said so.

**Why.** `peg_recovered` requires the AMM price within 31 bps of **par** for 6,900
consecutive steps (one Chainlink heartbeat). Over 6,900 steps at stress volatility the
*reference price itself* drifts σ√6900 ≈ 6.3%, twenty times the band. The pool can track
the reference perfectly and still never satisfy "at par for a day."

**What it changed.** The recovery criterion conflates two questions: "is the pool tracking
the dollar?" and "is the dollar reference itself stable?" ADR-0018's amendment schedules a
`peg_recovered.reference: peg | oracle` option so each question can be asked separately.
Until then, headline sweeps use calm volatility and the note states the limitation.

**For the note.** This is a measurement finding, not a market finding, but it matters for
how anyone reads a "time to recovery" number: under real stress, the recovery clock
depends on what you measure recovery against. March 2023 USDC "recovered" when it tracked
the dollar again, not when the dollar stopped moving.

---

## F-05 · A single-venue model cannot be calibrated to a market-scale event without an aggregate-depth assumption

**Date:** 2026-10-04 · **ADR:** [0018](adr/0018-calibration-judgment-calls.md) · **Story:** 2.3
**Reproduce:** `python run.py scenarios/calibrated-baseline.yaml` → `max_depeg_bps −9972`

**Expected.** Anchoring pool depth to Curve 3pool's USDC leg ($235M) and scaling Circle's
reserves ($42B) and an attacker at ratio 1.0 would give a calibrated baseline near the
ADR-0017 boundary.

**Observed.** The attacker is 179× pool depth. Its first 10% dump drives the pool to
$0.003 (−9972 bps). The defender then buys stable almost for free and the peg "recovers"
with the attacker never near exhausting anything. Probing attacker ratios 1–16× all
recover. The ADR-0017 boundary does not exist in this regime.

**Why.** Circle's reserves and the March-2023 selling pressure were spread across the
whole USDC market (dozens of venues plus OTC), while the model has one pool. Scaling
market-wide balances against one venue's depth is a venue-aggregation error, not a
calibration. The observed trough of $0.87 against ~$1.2B/hour of selling implies aggregate
effective depth in the billions, not $235M.

**What it changed.** A fourth judgment call, `market_depth_multiple` (status
`assumption`), fitted in Story 2.4 by back-solving the depth at which the calibrated
attacker's first dump reproduces the observed ≈ −1300 bps trough. One parameter fitted to
one observation, stated as such; everything else stays sourced.

**For the note.** State it as a limitation up front: the model is one constant-product
venue standing in for a market. The fitted aggregate depth is the price of that
simplification, and the F-03 trade-off (shallow = deeper trough, cheaper defense) is the
reason the choice matters.

---

## F-06 · When redemption is throughput-bound, the operative defense resource is what can be delivered within the horizon, and the far side of the boundary is "stays broken," not "runs dry"

**Date:** 2026-10-04 · **ADR:** [0019](adr/0019-fitted-depth-and-1992-analogue.md) §3 · **Story:** 2.4
**Reproduce:** `python scripts/probe_boundary.py --ratios 0.1,0.2,0.25,0.3,0.4 --seeds 8`
on the calibrated baseline

**Expected.** At calibrated parameters an ADR-0017-style boundary at
`capital / (budget + reserves) ≈ 1`, with `reserves_exhausted` beyond it.

**Observed.** No boundary anywhere in 0.5–2.0: every run ends `max_steps`, none exhausts
reserves. Probing lower, the recover/not-recover flip sits at nominal ratio 0.25–0.30.

**Why.** Calibrated redemption capacity (605.79 per step, from the observed $1.02B/day net
burn) can deliver only 10.9M of the 138M reserves within the 60-hour horizon. The
attacker's stable can be absorbed by the defender's budget plus *deliverable* reserves,
and nothing else. The builder's formula `(budget + capacity × horizon) / (budget +
reserves)` = 0.291 predicts the observed flip. Beyond it the price simply stays below peg
until the clock runs out; reserves are never touched because they can't be reached.

**What it changed.** 2.6's primary axis becomes `capital / (budget + deliverable
reserves)` with `deliverable = min(reserves, capacity × horizon)`. The three-way outcome
(recover / stay broken / exhaust) replaces the two-way one.

**For the note.** This is March 2023 exactly: Circle's reserves were never at risk; the
redemption channel was shut by the banking weekend, so the price stayed broken until an
outside event (the FDIC backstop) reopened it. The model reproduces that regime without
being told to. In 1992 terms: it is the difference between running out of reserves and
being unable to deploy them fast enough.

---

## F-07 · Sequential defenses leave a dead zone between them

**Date:** 2026-10-04 · **ADR:** [0019](adr/0019-fitted-depth-and-1992-analogue.md) §4 · **Story:** 2.4
**Reproduce:** `python run.py scenarios/soros-1992.yaml`; look at `spread_changed` and
`redeem_fulfilled` events against the price

**Expected.** The 1992 analogue would exhaust reserves at an attacker ratio near 1.0, as
F-02 predicts for unconstrained redemption.

**Observed.** The flip is at ratio 1.12 (5.3× Quantum). Below it the run stalls at about
−196 bps with ~10% of reserves unpaid, forever.

**Why.** The defender widens the redemption spread by 200 bps when it enters defense
(standing for the rate rises). Redemption then only pays out below −200 bps. The defender's
own trigger is −100 bps. Between −100 and −200 bps nobody acts: the defender has spent its
budget, and redemption is priced out. It is F-01's dead zone again, created this time by
the defense's own second lever.

**What it changed.** The defender's spread policy needs a restore condition that isn't
"back in band" (a `restore_threshold_pct`, Epic 3). The 1992 flip multiple is provisional
until 2.5 re-fits depth.

**For the note.** A defense with two levers can strand itself between them. The BoE's
rate rises made holding sterling attractive but did nothing for anyone already selling;
in the model, widening the exit price protects reserves at the cost of leaving the peg
permanently a little broken.

---

## Correction to F-05 (2026-10-04)

2.4's first depth fit produced D\* ≈ $430B per side, ten times USDC's supply. That is not
an aggregate depth; it is the model absorbing an attacker sized at `ratio 1.0` (≈ $42B of
selling) when the episode's net burn was ≈ $4B. ADR-0018's attacker ratio was the wrong
input. 2.5 re-anchors the attacker to the observed episode flow and re-fits D\*. F-05's
claim stands (a single-venue model needs an aggregate-depth assumption); the first number
attached to it does not.

---

## F-08 · The replay fails validation: the model has no buyer of the discounted promise

**Date:** 2026-10-04 · **ADR:** [0020](adr/0020-episode-flow-replay-and-capacity-schedule.md) · **Story:** 2.5
**Reproduce:** `python run.py scenarios/usdc-2023.yaml` then
`plot_validation_overlay(run_dir)`; compare with `data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv`

**Expected.** With the attacker sized to the episode's net burn ($2.71B), depth fitted to
the observed trough on the calibrated baseline (D\* ≈ $3.9B/side), pace fitted to trough
timing, no AMM defender (Circle did not buy on AMMs), and a redemption-capacity step on
Monday morning, the simulated price would track the observed USDC/USD path.

**Observed.** Trough timing matches (31.6 h vs 31.0 h). Trough depth does not: −5,769 bps
simulated vs −1,373 bps observed, four times too deep. The simulated price then climbs in
a straight line at redemption speed and meets the observed path at 63 h; agreement after
that is the oracle following the input series, not the model.

**Why.** D\* was fitted on the calibrated baseline, where the AMM defender absorbed 89% of
the attack. The replay correctly removes the defender, and nothing takes its place. The
same fit rule on the replay would need D ≈ $31B per side, 72% of USDC's supply, which is
not a depth. The missing counterparty is a **buyer who purchases discounted USDC
expecting par**: market makers and funds who bought at $0.88 on the weekend because they
expected Circle to redeem at $1.00 on Monday. The model's only discount buyers are the
issuer (the defender, correctly absent) and a 200k fee-band arbitrageur.

**What it changed.** Scope: Story 2.6 adds a par-expecting buyer agent, sized by
back-solving from this replay with D\* held fixed. Charts move to 2.7, figures to 2.8.
Epic 2 ends Oct 15 instead of Oct 13.

**For the note.** This is the model's clearest limitation and its clearest lesson. A
depeg's depth is set not by the attacker against the pool but by the attacker against
*everyone who believes the promise*. In 1992 those were the convergence traders
(BACKGROUND §4), and when their belief broke they switched sides. In 2023 they held, and
the peg came back. The simulator cannot reproduce March 2023 without them, which is
itself evidence for what decided March 2023.

---

## F-06 refinement (2026-10-04, from 2.5)

At the re-fitted D\* the F-06 flip sits at nominal ratio ≈ 0.39, above the formula's 0.29.
Cause: F-03. In a shallow pool the defender buys far below par, so its budget absorbs more
than face value. The formula is a lower bound; the price-adjusted version (budget valued
at what it actually bought) is the x-axis for 2.7's headline chart.

---

## F-08 confirmation (2026-10-04, from 2.6)

**Reproduce:** `python run.py scenarios/usdc-2023.yaml` (hash `2c3aeaa9825d`) then
`plot_validation_overlay(run_dir)`; `python scripts/fit_holder.py` for the fit.

One par-expecting buyer, sized by back-solving the replay with D\* held, takes the
trough from −5,769 to **−1,138 bps** against −1,373 observed: from 4.2× too deep to 17%
too shallow with one fitted parameter. **C\* = 9,166,667 model units ≈ $2.15B**, 0.79×
the attacker's episode net burn ($2.71B), 0.22× Circle's cash. The buyer absorbed 82% of
the attack's flow; the calibrated defender it replaces had absorbed 89%. From 35 h to
49 h the simulated path lies on the observed one; the trough is 3.2 h late (pace was
fitted without the buyer and is not re-fitted). The hypothesis in F-08's last paragraph
is now quantitative: the depeg's depth was set by the attacker against roughly $2B of
capital that believed the promise.

---

## F-09 · A single-entry-price buyer makes depeg depth bimodal

**Date:** 2026-10-04 · **ADR:** [0021](adr/0021-par-expecting-holder.md) · **Story:** 2.6
**Reproduce:** `python scripts/fit_holder.py --workers 8` (≈ 10 s); read the two refinement
tables.

**Expected.** Trough depth would fall smoothly as buyer capital rises, so the fit rule
would land within a few bps of −1,373.

**Observed.** Trough against holder capital on the replay: 5M → −3,785; 7.5M → −2,207;
8.33M → −1,653; 9.17M → −1,138; 10M → −225; 20M → −220. A cliff between 9.17M and 10M.
The observed −1,373 sits on the cliff face, and no single capital lands on it.

**Why.** Below the cliff the buyer runs out of reference before the attack ends, and the
attacker sets the trough. Above it the buyer outlasts the attack and the trough stops at
about the buyer's entry discount (−200 bps plus fee and impact). One entry price means one
of two regimes. The tranche redeem rule sharpens the cliff: weekend redemptions return
reference the buyer spends again, so near the edge a small capital increment is worth
much more than its face value (what moved C\* from 10M to 9.17M when the rule changed).

**What it changed.** The fit is accepted at −1,138 and the 17% gap is stated. A holder
with a distribution of entry prices (several tranches at 1%, 2%, 5%, 10%) is the natural
next model and goes to Epic 3 behind the fill-price-limit fix. The note states the fit as
"one buyer, one price, within 17%" rather than tuning toward the observation.

**For the note.** The real market's trough was set by the *shape* of belief, not just its
size: how much capital would buy at 1%, at 5%, at 12%. A single believer gives a cliff;
many believers at different prices give a curve. The March-2023 price found the point on
that curve where the attacker's selling met the buyers' bids.

---

## F-06 refinement (2026-10-04, from 2.6)

With the holder present at `C*/D*`, the calibrated-baseline probe's 50% point moves from
nominal ratio ≈ 0.39 to **≈ 0.50**; every seed recovers through 0.425 (was 0.325). The
+0.11 shift is about twice the holder's face-value share of `budget + reserves` (0.051),
by the same mechanism as F-03 and the 2.5 refinement: a resource that buys below par and
recycles through redemption absorbs more than its face value.

---

## F-07 refinement (2026-10-04, from 2.6)

Re-scan 4.0–7.0 by 0.1 on `soros-1992` with the holder present. **The flip stays at 5.7×
(ratio 1.206).** The 5.1/5.2 anomaly (exhausted while 5.3–5.6 did not) is gone; the
boundary is clean. The dead zone (4.0–5.6 stall at `max_steps`, final −143 … −178 bps)
persists. At 4.0–4.2 the holder flattens the trough to −222 (buyer-set regime, F-09); at
4.3 and above the attacker sets it. The holder loses at every multiple because the
defender's 200 bps spread sets its redemption payout at exactly its 2% entry — a
coincidence of two dev-manager assumptions, not a finding. At 3.6% of the 6× attacker the
holder is too small to test BACKGROUND §4's "convergence traders had to switch sides";
that test needs a holder with a sell rule, and goes to Epic 3.

---

## F-10 · Oracle lag does not matter under deviation-triggered updates at Chainlink's cadence

**Date:** 2026-10-04 · **ADR:** [0022](adr/0022-threshold-surface-metric-and-oracle-lag.md) · **Story:** 2.7
**Reproduce:** `python -m depeg_sim.sweep sweeps/oracle-lag-mc.yaml --mc --workers 8` (≈ 2 min);
`plot_oracle_sensitivity(output/oracle-lag-mc)`. Quick check (48 runs): heartbeat {300, 6900}
× threshold {0, 0.25, 1.0}, 8 seeds.

**Expected.** A slower oracle would let the AMM fall further before the arbitrageur acts,
so trough depth would grow with heartbeat and threshold.

**Observed.** On the stress base at the episode attack, the mean trough across all 20
(heartbeat, threshold) cells lies in −1,253.2 … −1,242.5 bps. The calibrated oracle
(6,900 steps, 0.25%) is within 0.5 bps of zero-lag. Heartbeats ≥ 300 steps give identical
results at every threshold. Only the 1% threshold moves the trough, by 10.2 bps, and
identically in every seed.

**Why.** Under stress volatility the reference moves a quarter percent within a few steps,
so a deviation-triggered oracle updates almost continuously whatever its heartbeat; the
heartbeat is a backstop that never binds. The arbitrageur's band (fee + min profit) is
wider than any lag the oracle introduces. The trough is set by the attacker against the
pool, the defender and the holder, not by when the arbitrageur learns the price.

**For the note.** Chart (3) is a flat line, and that is the result: "oracle lag" is not a
depeg risk factor at Chainlink's settings. It becomes one only with a wide deviation
threshold and a long heartbeat together.

---

## F-11 · At calibrated depth the defender wins the price and loses the clock: "stays broken" against par measures recovery speed, and a fixed budget beats any attack the pool is shallow enough to crash

**Date:** 2026-10-04 · **ADR:** [0022](adr/0022-threshold-surface-metric-and-oracle-lag.md) · **Story:** 2.7
**Reproduce:** `python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc --workers 8`
(≈ 2.5 min on 8 workers, 17 min on 2); then from `sweep.parquet` take per-depth medians of
`defender_spent` and `final_depeg_bps` at the 1.5 column.

**Expected.** `p_stays_broken` would rise with attacker capital at every depth and the
0.5 contour would mark where the attack beats the defense.

**Observed.** (1) The contour exists (D\* row crosses at nominal 0.56), but of the 279
non-recovering runs, 68 end *above* +31 bps and 43 end inside the band without holding it
for 6,900 steps; in those the AMM tracks the reference within 10 bps. Counting only runs
that end more than 31 bps below the reference, nothing at ≤ 1× D\* breaks (≤ 2/16 at any
ratio up to 1.5), and the 0.5 crossing appears only at 2× and 4× D\* (nominal ≈ 0.69–0.70).
(2) At ratio 1.5 the defender spends its whole 41.3M budget in every row; final deviation
is −9.5 bps at ≤ 1× D\* and −3,486 / −4,062 bps at 2× / 4× D\*.

**Why.** Two things. First, the par criterion: the calm reference is a random walk with no
anchor, its own spread over one 6,900-step window (≈ 26 bps) is the band width, so a
recovery that starts late cannot finish against par before the horizon. That is F-04 at
calm volatility and it is why "stays broken" is mostly the clock at ≤ D\*. Second, the
price: in a constant-product pool the cost of buying the dump back is what the attacker
was paid for it. A pool at or below D\* is shallow enough that a $42B-equivalent dump
crashes the price to a fraction of a cent, and $9.7B-equivalent of budget buys all of it
back; a pool at 2× D\* pays the attacker more per unit and the same budget cannot. The
price-defense boundary is set by budget against depth, nearly independently of attacker
size once the attack exceeds the pool. **Hypothesis for 2.8**: with a reference-relative
criterion, the surface's contour runs along depth, not along capital.

**What it changed.** Story 2.8 inserted: `peg_recovered.reference: par | oracle`, the
surface re-run under `oracle`, and a budget × depth probe. The AC 9 headline sentence from
2.7 is not quoted. Committed figures move to 2.9.

**For the note.** This is F-03 taken to its conclusion and it inverts the DeFi intuition
twice. Deep liquidity protects the *price* during the attack and makes the *defense*
unaffordable; an issuer defending on a shallow venue is cheap to defend and terrifying to
watch. And the thing the issuer cannot buy is time: at Circle's redemption throughput the
reserves are not the binding constraint, the clock is.

---

## F-04 refinement (2026-10-04, from 2.7)

The stress-base surface (run before the base was changed) put `p_stays_broken` ≥ 0.6875
in all 40 cells; 11 of 16 seeds never re-enter the band in any cell, and the median final
deviation is +215 bps *above* par with the AMM tracking the reference. Root cause stated:
the reference process is a driftless random walk with no anchor at par, so over a 60 h
horizon it wanders by more than the band even at calm volatility (σ√6900 ≈ 26 bps). Real
off-venue stablecoin prices mean-revert through redemption arbitrage. Two fixes, both Epic
3 candidates: a mean-reverting (OU) reference calibrated from calm-period autocorrelation,
or the reference-relative recovery criterion Story 2.8 builds. 2.8 takes the second
because it answers the sweep question directly; the replay keeps par because there the
reference *is* the observed depeg.

---

## Headline candidates (ranked, 2026-10-04, revised after 2.7)

1. **"A depeg's depth is set by the attacker against everyone who believes the promise."**
   (F-08, confirmed) — validation chart; lead.
2. **"Deep liquidity protects the price and makes the defense unaffordable."** (F-03 +
   F-11) — the mechanism; the 2.8 surface is its chart if the contour runs along depth.
3. **"At issuer scale the binding constraint is not reserves but the clock."** (F-06 +
   F-11) — throughput; explains why validation needed the buyer and why "recovery" is a
   speed question.
4. **"Oracle lag is not a depeg risk factor at Chainlink's settings."** (F-10) — short,
   quotable, a flat chart.
5. **"A peg can be permanently slightly broken with no one incentivised to fix it."**
   (F-01, F-07) — methods.
6. **"One believer gives a cliff; many believers at different prices give a curve."**
   (F-09) — limitations.

The note leads with 1 (overlay as figure 1), gives 2 and 3 as the two mechanisms with the
2.8 surface, states 4 in one paragraph with its chart, uses 5 in methods and closes on 6
and the 1992 open question.

---

## Open questions the next findings should answer

- ~~Does the F-03 boundary survive calibrated parameters (2.3)?~~ Not at single-venue depth
  (F-05); re-asked in 2.4 with the fitted aggregate depth.
- ~~Under realised stress volatility, does `peg_recovered` remain reachable?~~ No (F-04);
  criterion to gain a `reference` option after 2.6.
- ~~Does the 1992-analogue scenario reproduce reserve exhaustion with the historical ratios?~~
  Yes at 5.3× Quantum, provisionally (F-07); re-run after the 2.5 depth re-fit.
- Does D* land at a physical aggregate depth once the attacker is episode-sized? (2.5)
- ~~Does the model's USDC-2023 trajectory match the observed trough and recovery timing?~~
  Timing yes, depth no (F-08). ~~Re-asked in 2.6 with the par-expecting buyer.~~ With one
  buyer at $2.15B: depth within 17%, timing 3.2 h late, weekend path matches from 35 h
  (F-08 confirmation, F-09).
- ~~Does the F-03 collapse hold at calibrated scale with the buyer present?~~ Within ±0.04
  on the absorbed ratio, but that crossing at ≈ 1 is conservation; the result is the
  nominal per-depth crossings and saturation above D\* (F-11).
- ~~Does oracle lag matter under deviation-triggered updates?~~ No (F-10).
- Under a reference-relative recovery criterion, does the surface's 0.5 contour run along
  depth rather than capital — is the price-defense boundary budget vs depth? (2.8)
- Does the holder have to switch sides (sell) for the 1992 analogue to exhaust at the
  historical multiple? (Epic 3: holder sell rule)
- Does a fill price limit on the holder remove the sawtooth without moving C\* much?
  (Epic 3)
- Does D* land at a physical aggregate depth once the attacker is episode-sized? Yes on the
  calibrated baseline ($3.9B/side), but only because the defender stands in for the missing
  buyer (F-08).
- Is there a parameter-only predictor of the F-03 boundary (a closed form for expected
  defender absorption as a function of capital/depth)? (note appendix, not a story)
