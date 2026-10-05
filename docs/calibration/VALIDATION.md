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
