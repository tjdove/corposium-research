# Validation: the USDC depeg of 10–14 March 2023

Story 2.5. Does the calibrated model reproduce the shape of a real depeg? Short answer:
**it gets the timing of the trough (which was fitted) and the return to the band after
the bank reopening; it does not get the depth of the trough, and much of the later
agreement is the input series showing through.** Details below, in the order: what
matches, what does not, why.

## Setup

- **Scenario:** `scenarios/usdc-2023.yaml` (seed 42, hash `73db527c8ddf`). Calibrated-baseline
  parameters (`SOURCES.md`) with the observed reference series, the episode-flow attacker
  and the re-fitted depth D\* = 16,666,667 (≈ $3.91B per side), with five changes listed
  in the YAML header.
- **Reference:** Bitstamp USDC/USD hourly closes, 2023-03-10 00:00 → 2023-03-13 23:00 UTC
  (`data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv`), linearly interpolated to 12 s
  steps and held at the last close (0.99553) for the final 17 h.
- **Timestamps** (hours from series start, 2023-03-10 00:00 UTC):

  | event | time | step | hours |
  |---|---|---|---|
  | attack start: Circle's SVB disclosure | 2023-03-10 22:00 ET = 03-11 03:00 UTC | 8100 | 27.0 |
  | observed trough (Chainalysis "by 2am"; also the CSV minimum) | 03-11 02:00 ET = 07:00 UTC | 9300 | 31.0 |
  | redemption capacity change: banks reopen | 03-13 09:00 ET (EDT) = 13:00 UTC | 25500 | 85.0 |
  | end of run | 03-14 12:00 ET = 16:00 UTC | 33600 | 112.0 |

- **Attacker:** 11,540,596 model units = the net USDC supply change 10 → 13 March
  ($2,707,423,804, DefiLlama), selling from step 8100 at the **fitted pace 0.002** per step
  (closest trough timing to step 9300 among [0.001 … 0.1]; `sweeps/usdc-2023-pace.yaml`).
- **Defender:** inactive (`threshold_pct` 99.0). Circle did not buy USDC on AMMs.
- **Redemption:** 605.79 per step (the calibrated observed throughput) until step 25500,
  then 19,181.59 per step (the whole reserve in one day).
- **Band:** 31 bps, the ADR-0013 band of the calibrated scenarios. `peg_recovered` is off
  in this scenario so the replay covers the whole window. Band statistics are measured
  from the series.
- **Par, not the oracle (Story 2.8):** the replay keeps measuring against par. It has no
  `peg_recovered.reference: oracle` and its band statistics use `peg_deviation`, because
  here the reference *is* the observed depeg, and measuring the venue against it would
  hide the very deviation being validated.

## Comparison

| quantity | observed (Bitstamp hourly close) | simulated (AMM spot) |
|---|---|---|
| trough depth | **−1,373 bps** (0.86267; Chainalysis $0.87 ≈ −1,300) | **−5,769 bps** (0.4231) |
| trough time | **31.0 h** (03-11 07:00 UTC) | **31.6 h** (step 9488; fitted via pace) |
| deviation at the capacity change (85 h) | −36 bps | −52 bps |
| first time back in the band after the capacity change | 86.0 h (+1.0 h) | 85.3 h (+0.3 h) |
| last time outside the band | ≥ 95.0 h: censored (the series ends at −45 bps, outside again after re-entering at 86 h) | 85.3 h (in band to the end; final −27 bps) |
| recovery direction and timing vs the capacity change | upward into the band within 1 h | upward into the band within 0.3 h; the 0.96M redemption queue clears in ≈ 50 steps |
| weekend path | partial rebound to −150 … −500 bps by 45–55 h, a dip near 55 h, ≈ −100 by 72 h | linear rebound at redemption capacity from −5,769, meets the observed path at 63.3 h, then within −45 … +64 bps of it |

## What matches

- **Trough timing.** Simulated 31.6 h vs observed 31.0 h, inside the ±2 h target. This
  was *fitted* (pace is the one free timing parameter), so it shows that the attack can be
  given a plausible speed. It is not evidence for the model.
- **Return to the band at the bank reopening.** Both paths re-enter the 31 bps band
  within about an hour of 85 h, and the model's mechanism is the right one: a redemption
  queue that built up under weekend throughput clears once capacity rises. That is the
  F-06 "stays broken until the channel reopens" shape. The model has not reproduced the
  deep plateau, though (see below): by 85 h both series are already within ~50 bps of peg.
- **Plateau level from 63 h on.** The simulated price sits on the observed one (within
  −45 … +64 bps). This is mostly the input showing through, not a match (see Why).

## What does not match

- **Trough depth: −5,769 vs −1,373 bps, 4.2× too deep.** This is the main failure.
- **Weekend shape.** The observed price rebounded quickly to −150 … −500 bps and wobbled
  with the news. The simulated price climbs back in a straight line at the speed of
  redemption throughput and reaches the observed path only after 36 hours. Intra-weekend
  wobbles cannot be reproduced by this model (no news, no expectations).
- **Last time outside the band.** Not comparable: the observed series ends outside the
  band (−45 bps at 95 h, after re-entering at 86 h). The model is inside from 85.3 h on.

## Why

- **The depth was fitted with an AMM defender that the replay does not have.** D\* comes
  from `calibrated-baseline`, where the defender's 41.3M budget (Circle's cash share) buys
  stable on the AMM. In the fit at D\* it spends 10,261,334 against an 11,540,596 attack,
  i.e. it puts back ~89% of the attack's size in reference. The replay follows the history: Circle did not buy on AMMs, so
  the defender is off, and the whole flow lands in the pool. Re-running the same fit rule
  on the replay scenario (diagnostic only, not applied) gives D = 133,333,333
  (−1,324.7 bps), ≈ **$31.3B per side**, about 72% of USDC's supply. That is not a physical
  depth either. The real absorber, as far as one can tell, was **buyers of discounted USDC
  who expected par**: market makers, funds and traders who were not Circle. The model has
  no such agent. In the calibrated baseline the "defender" stands in for them, and the
  replay removes it.
- **The reference is the observed USDC price, and the arbitrageur trades toward it.** The
  arbitrageur buys on the AMM only when the AMM is below the oracle minus its band, and the
  oracle follows the observed series. While the simulated price is below the observed one,
  the arbitrageur buys and redeems (throughput-bound), lifting the price at a constant rate.
  Once the price reaches the observed path (63.3 h), the arbitrageur stops buying above
  it. From then on the simulated price is pinned to the input, so the plateau and the
  post-backstop agreement are not independent evidence.
- **Weekend throughput nearly matches the attack.** At 605.79 per step for the 17,400
  weekend steps the channel can pay 10.54M, against an 11.54M attack. So in the model most
  of the attack is redeemed before the backstop (10.54M of 11.52M paid by step 25500), and
  the capacity change only clears the last 0.96M. The calibrated capacity is the 11–15 March
  average, which includes Monday's catch-up. If the weekend channel was slower, the model
  would sit further below peg into Monday, and the backstop would matter more.
- **What the model can and cannot be asked for.** One constant-product venue, no CEX books,
  no rotation into other stablecoins, no bank, no expectations. It can plausibly match the
  trough depth (once the absorbing side is modelled), the trough timing (via pace) and the
  "broken until the channel reopens" mechanism. It cannot match news-driven wobbles or the
  exact recovery slope.

## Figure

`output/usdc-2023-42-73db527c/validation_overlay.png` (from `plot_validation_overlay`, which
re-reads the CSV named in the run's manifest and checks its sha256). Committed figures are
Story 2.7. One panel, hours on x. The observed hourly closes (blue, dotted markers) dip to
−1,373 at 31 h, wobble between −150 and −1,150 through Saturday, settle near −400 from
~55 h, step up to about −100 at 70 h and into the band at 86 h. The simulated AMM price
(black) falls almost vertically from 27 h to −5,769 at 31.6 h, climbs back in a straight
line, meets the blue line at ~63 h and follows it from there, entering the band just after
the "redemption capacity changes" marker at 85 h and holding −27 bps to 112 h.

---

## Story 2.6: with the par-expecting buyer

Everything above is the Story 2.5 replay and stays as written. Story 2.6 adds the missing
counterparty F-08 named: a `holder` that buys below $0.98 at 5% of its remaining reference
per step and redeems in tranches (`min(stable, capacity × 10)`) whenever the redemption
queue is empty. Its capital is the one fitted parameter: **C\* = 9,166,667 model units
(≈ $2.15B, 0.79× the attacker's episode net burn)**, chosen by `scripts/fit_holder.py` as
the grid/refinement point closest to −1,373 bps, with D\* = 16,666,667 and pace 0.002 held.
Scenario hash `2c3aeaa9825d`; run `output/usdc-2023-42-2c3aeaa9/`.

| quantity | observed | 2.5 (no holder) | 2.6 (holder, C\*) |
|---|---|---|---|
| trough depth | −1,373 bps | −5,769 bps | **−1,138 bps** (17% shallower than observed) |
| trough time (±2 h target) | 31.0 h | 31.6 h (within; fitted via pace) | **34.2 h** (+3.2 h, outside; pace was fitted in 2.5 without the holder and is not re-fitted) |
| deviation at the capacity change (85 h) | −36 bps | −52 bps | −52 bps |
| first back in band after the capacity change | 86.0 h | 85.3 h | 85.3 h |
| last time outside the band | ≥ 95.0 h, censored | 85.3 h | 85.3 h |
| recovery direction and timing vs the capacity change | upward into the band within 1 h | upward within 0.3 h | upward within 0.3 h |
| weekend path | rebound to −150 … −500 bps by 45–55 h, dip near 55 h, ≈ −100 by 72 h | straight-line climb from −5,769, meets the observed path at 63 h | climbs from −1,138 and sits on the observed path from ≈ 35 h; flat at −170 bps from 49 h to 69 h while the observed price dips to −520 |
| who absorbed the attack's 11.54M | (market buyers) | arbitrageur buys + redemption at weekend capacity | holder bought 9.50M stable with 9.42M reference (its 9.17M plus recycled redemptions); arbitrageur redeemed 2.02M |
| holder redemptions | n/a | n/a | 6.69M before the capacity change (85 h), 2.80M after; holder PnL +82.5k |

**What the buyer fixed.** The trough depth: from 4.2× too deep to 17% too shallow, with
one fitted parameter at a size ($2.15B) that is plausible for the weekend's discount
buyers and smaller than the flow they absorbed. The weekend recovery shape also improved:
the simulated price now rebounds from the trough at about the speed the observed one did,
and sits on the observed path from ≈ 35 h, instead of climbing in a straight line until 63 h.

**What it didn't fix, and what it added.**
- **The trough is late.** 34.2 h vs 31.0 h. The holder holds the price near its entry for
  the first ~3.5 h of the attack, and the trough comes only once its reference runs out.
  Pace (0.002) was fitted in 2.5 against a model with no buyer, so it is now tuned to the
  wrong mechanism. Re-fitting it is not in scope (story Rulings 3).
- **The fit cannot land on −1,373.** The trough as a function of capital is close to
  bimodal: 7.5M → −2,207, 8.33M → −1,653, 9.17M → −1,138, 10M → −225. Below the cliff the
  buyer runs out of reference before the attack ends and the attacker sets the trough;
  above it the buyer outlasts the attack and the trough sits at about its 2% entry. A
  single entry price makes the trough jump between the two. Real buyers came in at a
  spread of prices (Proposed ADR-0021).
- **A sawtooth at the start of the attack.** From 27 h to ≈ 30.5 h the simulated price
  swings between ≈ +310 and −220 bps. Each holder buy is 5% of its reference, ≈ 450k at
  first, into a 16.7M pool, so it overshoots par before the attacker pushes the price back
  down. This is a model artefact (the buyer has no price limit on its own fills); the
  hourly series cannot show whether anything like it happened within the hour.
- **Most of the holder's redemption happens over the weekend, not on Monday.** The
  weekend channel (605.79 × 17,400 steps ≈ 10.5M) was big enough for 6.69M of the holder's
  9.50M. As in 2.5, the calibrated weekend capacity is the 11–15 March average, so this
  probably overstates what the weekend channel could pay.
- **From 63 h on, the agreement is still the input.** Same caveat as 2.5: the arbitrageur
  trades the AMM toward the oracle, which follows the observed series. The flat −170 bps
  stretch from 49 h to 69 h is the other side of it: the AMM can follow the observed
  price up, but nothing sells stable to follow it back down.

**Figure** (`output/usdc-2023-42-2c3aeaa9/validation_overlay.png`; committed figures are
Story 2.8). The black simulated line leaves 0 at the 27 h marker and fills a dense band
between ≈ +310 and −220 bps until ≈ 30.5 h. It then drops to ≈ −1,060 at 31.5 h, bounces
to −900 and reaches its trough at −1,138, 34.2 h, about 3 h after and 235 bps above the
blue observed trough (−1,373 at 31 h). From 35 h the two lines overlap, stepping up
through −500 at 40 h to about −280 at 45 h. The black line then holds at −170 from 49 h
to 69 h while the blue line dips to −520 at 55 h and comes back. Both step up near 70 h,
and both enter the grey band at the 85 h capacity marker. The black line holds −27 bps to
112 h.

---

## Story 3.1: the holder's fill-price limit

Story 3.1 caps each holder buy at the reference that lifts AMM spot to its entry price
($0.98): `min(pace × reference, cap)`, with `cap` from the arbitrageur's
`_reference_to_reach` (fee ignored, so spot lands < 0.1 bps under $0.98). `fit_holder.py`
was re-run unchanged and picks the same point: **C\* = 9,166,667** (scenario hash
`2c3aeaa9825d`, unchanged). The curve around it moved (8.33M: −1,652.8 → −1,608.6 bps;
10M: −224.6 → −954.2 bps), but 9,166,667 is still the closest point to −1,373.

| replay | trough depth | trough time | first in band after 85 h | sawtooth amplitude, steps 8,100–9,150 (max − min of deviation) |
|---|---|---|---|---|
| observed | −1,373 bps | 31.0 h | 86.0 h | n/a (hourly closes) |
| 2.5 (no holder) | −5,769 bps | 31.6 h | 85.3 h | 5,669.9 bps: no sawtooth; the window is the crash from −28 to −5,698 |
| 2.6 (holder, C\* 9,166,667) | −1,137.8 bps | 34.2 h (step 10,255) | 85.3 h | **662.9 bps** (+314.7 … −348.3) |
| **3.1 (capped holder, C\* 9,166,667)** | **−1,137.8 bps** | **34.2 h** (step 10,269) | **85.3 h** | **384.5 bps** (−27.6 … −412.1) |

The 3.1 amplitude as defined spans two things that are not the sawtooth: the window's
first steps, where the attack takes the price from −28 to −200 bps before the holder can
act, and its last ~50 steps (from step 9,098), where the holder's reference is almost
spent (a 1,956 buy at step 9,080 is 5% of ~39k left, against the attacker's 3.2k dump)
and the price starts its fall to the trough (−412 at step 9,150). Between them,
over steps 8,400–9,000, the amplitude is **10.2 bps** (−204.4 … −214.7) against
**265.2 bps** (+53.8 … −211.4) in 2.6. The price no longer goes above the holder's entry
price at any step. At whole hours (27, 28, 29, 30 h) the simulated deviation is −28,
−213, −208, −204 bps (2.6: −28, −171, −197, −196). What is left is a slow drift from −215
to −204 bps. Each step the attacker sells 0.2% of its remaining stable (23k at step 8,100,
3.2k by step 9,080), and the holder buys back toward $0.98. In this stretch its 5% buys are
mostly the binding term, so the price ends each step just under its entry, not on it.
The 10 bps drift is a third of the 31 bps band and invisible at hourly resolution.

Everything else in the 2.6 table is unchanged to the bps: −52 bps at the capacity change,
back in band at 85.3 h and in band to 112 h. The weekend path from 35 h is identical
(−913 at 35 h, −173 flat from 49 h to 69 h). The holder bought 9.42M stable with 9.21M
reference (2.6: 9.50M with 9.42M). It redeemed 6.49M before the capacity change and 2.93M
after (2.6: 6.69M / 2.80M), and its PnL is +209.4k (2.6: +82.5k). It no longer pays above
$0.98 for anything. The trough is still 3.2 h late: pace was not re-fitted (2.6 Rulings 3).

**Figure** (`docs/figures/validation_overlay_usdc_2023.png`, regenerated by `make figures`).
**Before (2.6):** from the 27 h marker to ≈ 30.5 h the black simulated line filled a
dense band between ≈ +315 and −220 bps. The y-axis had to reach +400 to hold it, so the
picture's first impression was of a price swinging *above* par during a depeg.
**After (3.1):** the black line drops almost vertically at 27 h to ≈ −220 bps, then runs as
a single thin line easing from −215 to −204 bps until ≈ 30.3 h. It then plunges to
≈ −1,100 at 31.5 h and continues as before. Nothing in the figure is above zero after the
attack starts, and the y-axis now tops out at +100. From 31.5 h on, the figure is
unchanged.

---

## Story 3.7: a holder with a ladder of entry prices

Story 3.7 replaces the single 2% entry with a ladder: the holder's capital is split into
tranches, each buying only below its own entry price, from its own share, with the 3.1
fill-price cap applied per tranche. Redeem and exit rules are unchanged and act on the
pooled stable. Three ladders were fixed before any run (assumptions, not fitted):
**A** 1/2/5% at 50/30/20%, **B** 2/5/10/20% at 25% each, **C** 1/2/5/10/15% at 20% each.
For each, `scripts/fit_holder.py --tranches …` fitted total capital `C*` with the
unchanged two-pass rule. The closest is **B: C\* = 10,833,333 (−1,323.3 bps)**, which is
now `scenarios/usdc-2023-tranches.yaml` (hash `da3383d4e156`). `usdc-2023.yaml` is untouched.

| fit (`C*`, units / $ at s / × attacker net burn) | trough at `C*` | distance from −1,373 | trough time |
|---|---|---|---|
| single 2% entry (2.6 / 3.1): 9,166,667 / $2.15B / 0.79× | −1,137.8 bps | +235.2 bps (17.1% shallow) | 34.2 h (step 10,269) |
| A 1/2/5%: 8,333,333 / $1.95B / 0.72× | −1,602.7 bps | −229.7 bps (16.7% deep) | 32.8 h (step 9,831) |
| **B 2/5/10/20%: 10,833,333 / $2.54B / 0.94×** | **−1,323.3 bps** | **+49.7 bps (3.6% shallow)** | **31.2 h (step 9,346)** |
| C 1/2/5/10/15%: 10,000,000 / $2.35B / 0.87× | −1,489.0 bps | −116.0 bps (8.4% deep) | 32.8 h (step 9,836) |

| replay | trough depth | trough time | at the capacity change (85 h) | first in band after 85 h | holder bought / spent | holder redeemed before / after 85 h | arbitrageur redeemed | holder PnL |
|---|---|---|---|---|---|---|---|---|
| observed | −1,373 bps | 31.0 h | −36 bps | 86.0 h | n/a | n/a | n/a | n/a |
| 3.1 (single entry, C\* 9,166,667) | −1,137.8 bps | 34.2 h | −52 bps | 85.3 h | 9.42M / 9.21M | 6.49M / 2.93M | 2.10M | +209.4k |
| **3.7 (ladder B, C\* 10,833,333)** | **−1,323.3 bps** | **31.2 h** | **−52 bps** | **85.3 h** | **8.66M / 8.14M** | **6.47M / 2.19M** | **2.85M** | **+522.6k** |

**The cliff test.** Trough at `C* × {0.8 … 1.2}` for ladder B, beside the single entry at
the same multiples of its own `C*` (run now with the 3.1 capped holder, `fit_holder.py
--at-multiples-of`; 2.6's refinement table had no points at these multiples and predates
the cap, so its nearest points are given for reference):

| multiple | ladder B capital | ladder B trough | single-entry capital | single-entry trough (3.1 holder) | 2.6 table, nearest point (uncapped) |
|---|---|---|---|---|---|
| 0.8 | 8,666,666 | −2,003.1 | 7,333,334 | −2,257.6 | 7.5M (0.82×): −2,206.7 |
| 0.9 | 9,750,000 | −2,000.8 | 8,250,000 | −1,662.3 | 8.33M (0.91×): −1,652.8 |
| 1.0 | 10,833,333 | −1,323.3 | 9,166,667 | −1,137.8 | 9.17M: −1,137.8 |
| 1.1 | 11,916,666 | −1,007.8 | 10,083,334 | −885.1 | 10M (1.09×): −224.6 |
| 1.2 | 13,000,000 | −1,006.7 | 11,000,000 | −225.9 | none (12.5M, 1.36×: −215.8) |

**The cliff is not gone; it is a staircase.** Over ±20% of `C*` the ladder's trough spans
996 bps against the single entry's 2,032, but it does not move smoothly: it sits flat on
a tread at or near each tranche's entry price (−2,000 at 0.8–0.9×, −1,007 at 1.1–1.2×; the
fit tables show the others near −500, −200 and −130 bps) and jumps between them. The
largest step per 10% of `C*` is **677 bps** for ladder B (0.9 → 1.0×) against **659 bps** for
the single entry (1.1 → 1.2×). A tread is a tranche that still has reference when the
attack ends, holding spot at its entry; a riser is the capital range in which the
shallower tranche runs out before the attack does and the attacker sets the trough, the
same mechanism as F-09 at a quarter of the size. `C*` lands on a riser: at −1,323 the 10%
tranche has spent its whole share (2.71M) and the 20% tranche has not yet bought.

**What the ladder fixed.** The trough depth, to 3.6% (one fitted number, as before; the
ladder is an assumption and the best of three fixed ones). The trough time: 31.2 h
against 31.0 h observed, where the single entry was 3.2 h late. With one buyer at 2% the
price parked at −200 bps for 3.5 h before falling; with the ladder it steps down through
the entries (−1,000 by 28.6 h) and the 10% tranche runs out at ≈ 30.6 h, so the fall to
the trough comes when the observed one did. Pace (0.002) was not re-fitted.

**What it didn't fix.** The fit still cannot land on −1,373 by construction of the rule;
it lands within the riser that contains it. Which riser, and the trough on it, depend on
where the ladder puts its entries, which no public source pins down. From ≈ 48.6 h the
path agrees with 3.1 to within 0.05 bps (−173 flat from 49 h to 69 h, −52 at the capacity
change, back in band at 85.3 h). The holder's PnL more than doubles (+522.6k) because the deep
tranches bought at 5–10% discounts, and the arbitrageur redeems more (2.85M vs 2.10M)
because the holder no longer holds the price at $0.98.

**Figure** (`docs/figures/validation_overlay_usdc_2023_tranches.png`, its own figure; the
single-entry overlay is unchanged). The black simulated line leaves 0 at the 27 h marker
and steps down a staircase: a short tread at ≈ −220 bps, one at ≈ −510 bps by 27.6 h, and
a long flat tread at −1,005 bps from 28.6 h to 30.6 h. It then drops to its trough,
−1,323 at 31.2 h, 9 minutes after and 50 bps above the blue observed trough (−1,373 at
31.0 h). It bounces to ≈ −1,150 and then traces a shallow U drawn as a narrow band (≤ 43 bps
peak to peak over 4 steps), down to −1,311 at 32.9 h and back to −1,180 by 34.4 h, while
the blue line rebounds to −800 at 32 h and falls back to
−1,164 at 34 h, then climbs to meet the blue line at ≈ −955 at 36 h. From there it is
the 3.1 figure: on the observed path to ≈ 45 h, flat at −173 from 49 h to 69 h, into the
grey band at the 85 h capacity marker.

---

## Par-reference replay (Story 5.1)

Every replay above feeds the observed USDC/USD series to the model as its reference
price: the oracle follows it and the arbitrageur trades the AMM against the oracle. Story
5.1 removes that input. `scenarios/usdc-2023-par.yaml` (hash `7f3d0c583694`) and
`scenarios/usdc-2023-tranches-par.yaml` (hash `32a610a514f2`) are `usdc-2023.yaml` and
`usdc-2023-tranches.yaml` with `price_series_path` removed, `base_price` 1.0,
`volatility_per_step` 0.0 and no `mean_reversion_per_step`. Read in
`price_process.py`: with no series, σ = 0 and κ = 0 the reference stays at `base_price`
every step and nothing is drawn from `ctx.rng`; the test checks reference and oracle are
1.0 at every step. Attacker, holder, arbitrageur, defender, capacity schedule, `max_steps`
and seed are unchanged. Nothing was re-fitted: D\*, pace, both C\* and the ladder are
the values above. The observed series is used only to evaluate the runs.

What the change touches: the **oracle** (now 1.0 throughout) and so the **arbitrageur**,
which buys on the AMM when spot is below oracle × (1 − band). The **holder** is not
affected by the change itself. Its entry test is against `redemption.peg_price ×
(1 − entry_discount_pct/100)` (`agents/holder.py`; ADR-0021, ADR-0024), not the oracle.
Its fills can still differ, because the arbitrageur's trades move the same pool.

A sensitivity pair, `usdc-2023-ou.yaml` (`77fc93f2f784`) and `usdc-2023-tranches-ou.yaml`
(`b219b783b6a3`), uses the calm mean-reverting reference of `calibrated-baseline-ou.yaml`
instead (σ 3.086e-05, κ 0.001634, seed 42).

`python scripts/replay_table.py` (six runs, 14 s on Seoul):

| replay | hash | trough bps | trough step | trough h | first back in band after trough, h | hours in band, 27–96 h | holder bought | holder redeemed | holder PnL | arb redeemed |
|---|---|---|---|---|---|---|---|---|---|---|
| observed (Bitstamp hourly close) | | −1,373.3 | n/a | 31.0 | 86.0 | 8.0 | n/a | n/a | n/a | n/a |
| observed ref, single entry | `2c3aeaa9825d` | −1,137.8 | 10,269 | 34.2 | 85.3 | 10.7 | 9,418,433 | 9,418,433 | 209,360 | 2,098,246 |
| observed ref, ladder B | `da3383d4e156` | −1,323.3 | 9,346 | 31.2 | 85.3 | 10.7 | 8,662,811 | 8,662,811 | 522,643 | 2,853,889 |
| **par ref, single entry** | `7f3d0c583694` | **−607.2** | 9,886 | **33.0** | **37.2** | **58.8** | 9,372,636 | 9,372,636 | 205,969 | 2,161,592 |
| **par ref, ladder B** | `32a610a514f2` | **−1,279.2** | 9,850 | **32.8** | **40.4** | **55.6** | 8,646,604 | 8,646,604 | 521,604 | 2,890,043 |
| OU ref, single entry | `77fc93f2f784` | −607.2 | 9,886 | 33.0 | 37.2 | 58.8 | 9,372,636 | 9,372,636 | 205,969 | 2,154,338 |
| OU ref, ladder B | `b219b783b6a3` | −1,279.2 | 9,850 | 32.8 | 40.4 | 55.6 | 8,646,604 | 8,646,604 | 521,604 | 2,891,844 |

Definitions (also in the script's docstring). The band is the ADR-0013 ±31 bps. "First
back in band" is the first time after the trough with |deviation| ≤ 31 bps. "Hours in
band" covers the attack start (27 h) to the end of the observed series (its last close,
95 h, standing for 95–96 h): one hour per hourly close for the observed row, steps × 12 s
for the simulated rows. The two are sampled differently (hourly close against 12 s spot),
so that column compares time in band, not paths point for point. Amounts are model units
(1M = $234.6M). The observed-reference rows reproduce the Story 3.1 and 3.7 tables above.

**Ladder B against the observed trough (AC 6).** The par-reference ladder B trough is
**−1,279.2 bps**, 94.1 bps (6.9%) shallower than the observed −1,373.3. That is
**within ±10%** of the observed trough. It is 44.1 bps shallower than the
observed-reference replay (−1,323.3). It comes at 32.8 h, 1.8 h after the observed trough
(31.0 h), where the observed-reference replay was 0.2 h after.

**The single entry against the observed trough.** The par-reference single-entry trough
is **−607.2 bps**, 766.1 bps (55.8%) shallower than observed and 530.6 bps shallower than
its observed-reference replay (−1,137.8). It is not within ±10%. It comes at 33.0 h
(observed-reference replay 34.2 h).

**What moved.**
- **Recovery.** With the par reference, both replays are back inside the band at 37.2 h
  (single) and 40.4 h (ladder B), 4.2 h and 7.6 h after their troughs. The
  observed-reference replays and the observed price are back at 85.3 h and 86.0 h, after
  the 85 h capacity change. After re-entry the single-entry price stays inside the band
  to the end of the run (112 h; lowest −21.1 bps at 37.4 h, within ±6.3 bps from 40.5 h).
  Ladder B leaves the band once more, for 7 steps (40.40–40.42 h, down to −37.4 bps), and
  is inside from 40.43 h to 112 h (within ±3.4 bps from 41 h). Neither tracks the
  observed weekend path (−150 … −524 bps from 41 h to 69 h; −716 bps at 40 h). Hours in band over 27–96 h: 58.8 and 55.6,
  against 10.7 for both observed-reference replays and 8.0 observed. Final deviation
  at 112 h: −6.3 bps (single) and −3.4 bps (ladder B), against −27.3 bps in both
  observed-reference replays.
- **The arbitrageur's buying during the attack.** With the par oracle the arbitrageur
  buys at every opportunity from the attack start. From 27 h to 31 h (steps 8,100–9,300)
  it spends 923,919 of reference on the AMM in 400 buys, in both par replays. With the
  observed-series oracle it spent 398,699 (111 buys, single entry) and 678,574 (265 buys,
  ladder B): as the oracle fell with the observed price, spot was less often below oracle
  × (1 − band). 923,919 is about its 200,000 capital plus the 724,525 the redemption
  channel paid it over steps 8,100–9,299 (no one else was paid in that window). It never
  sells on the AMM in any of the six runs.
- **The single-entry trough** (−1,137.8 → −607.2) moves much more than ladder B's
  (−1,323.3 → −1,279.2).
- **Trough time** for ladder B: 31.2 h → 32.8 h.

**What did not move** (par against observed reference, same holder):
- Holder bought: 9.42M → 9.37M (single), 8.66M → 8.65M (ladder B). The holder redeems
  everything it bought in every run.
- Holder PnL: 209.4k → 206.0k (single), 522.6k → 521.6k (ladder B).
- Arbitrageur redeemed: 2.10M → 2.16M (single), 2.85M → 2.89M (ladder B).
- The ladder B staircase down to the −1,005 bps tread. At 27.5, 28.0 and 28.6 h the
  par-reference price is −231.0, −514.0 and −1,008.9 bps, against −230.6, −511.9 and
  −1,006.8 with the observed reference. The two paths differ from the first attack step
  (27.0 h) by up to 77 bps at single steps. The tread spans −1,000.8 … −1,008.5 bps over
  28.7–30.5 h (observed reference: −1,002.7 … −1,008.5).

**OU against par.** The calm OU reference gives the same trough (to 0.03 bps), trough
step, re-entry time, hours in band and holder numbers as the constant par reference.
Only the arbitrageur's redemptions differ, by 7,254 (single) and 1,801 (ladder B).

**Figures.** `docs/figures/validation_overlay_usdc_2023_par.png` and
`validation_overlay_usdc_2023_tranches_par.png`: observed hourly closes (blue), the
observed-reference replay (grey, dashed) and the par-reference replay (black).
- **Single entry.** The black line drops at 27 h to ≈ −220 bps and eases to ≈ −200 until
  ≈ 30.5 h (−225.8 … −201.1 bps). The grey line spans −409.0 … −203.9 over the same
  stretch. It then falls to its trough of −607 bps at 33.0 h,
  where the grey line falls to −1,138 at 34.2 h. It climbs back to the band by 37.2 h,
  touches −21 bps just after, comes up to zero by ≈ 40 h and lies on it to 112 h. The
  blue line is at −716 bps at 40 h.
- **Ladder B.** The black line follows the grey staircase (−220, −510, −1,005 bps) to
  ≈ 30.6 h. It reaches its trough of −1,279 bps at 32.8 h, inside the grey line's
  shallow U, then rises in a near-straight line to the band at 40.4 h and lies on zero
  from there to 112 h.
