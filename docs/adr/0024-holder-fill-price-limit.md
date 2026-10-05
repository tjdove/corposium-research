# ADR-0024: The holder's fill-price limit: C\* unchanged, sawtooth gone, 1992 flip moves to 5.2

**Status:** Proposed
**Date:** 2026-10-05
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 3.1 (ADR-0021 Consequences and Alternatives: "a price limit on the holder's own buys")

## Context

ADR-0021's holder bought `pace × reference` whenever AMM spot was below its entry price
($0.98), however far that buy moved the price. At C\* in a 16.7M pool the first buys were
~450k, so each one lifted the price past par. The overlay's first 3.5 h became a sawtooth,
measured as defined in Story 3.1 at **662.9 bps** (+314.7 … −348.3 over steps 8,100–9,150).
ADR-0021 described it by eye as +310 … −220, and Story 3.1's Dev Notes used ~530. The
holder also paid above $0.98, and above par, for some of its stable. That is not how a
buyer with an entry price behaves.

## Decision

1. **Fill rule** (`agents/holder.py`). Each `hold_buy` spends
   `min(pace × reference, cap)`, where `cap = _reference_to_reach(amm.k,
   amm.reserve_reference, entry_price)`. That is the arbitrageur's closed-form sizing
   (Story 1.7), imported and **reused unchanged**.
   - It ignores the AMM fee, so with a fee the buy lands spot slightly **below**
     `entry_price` and never above it. The undershoot is `f·x / sqrt(k·p)`. At the
     calibrated 1 bp fee it is under 0.1 bps (0.015–0.08 bps over buys from $0.95 to
     $0.83 at D\*); at 30 bps from $0.95 it is 0.46 bps.
   - If the smaller term is ≤ `DUST`, the holder does not buy and falls through to its
     redeem / `hold_wait` / `hold_done` rules.
   - Rule names, `HolderConfig` and every scenario hash are unchanged (pinned in
     `tests/test_holder_config.py`).
2. **C\* stays 9,166,667.** `fit_holder.py` re-run under the two-pass rule (unchanged):
   - grid: 5M → −3,763.5, 10M → −954.2 (was −224.6), pick 10M;
   - refine 1 between 5M and 20M: 7.5M → −2,147.4, 10M stays the pick;
   - refine 2 between 7.5M and 12.5M: 8,333,333 → −1,608.6, **9,166,667 → −1,137.8**,
     10M → −954.2.

   **C\* = 9,166,667 model units ≈ $2,150,500,078 ≈ 0.79× the attacker's episode net
   burn** (11,540,596 units), as before. The search path differs from 2.6's: refine 2 ran
   between 7.5M and 12.5M, not 5M and 10M, because 10M is now closer than 7.5M. It lands
   on the same point. No scenario's `capital` changes.

## Consequences

**Replay** (VALIDATION.md, Story 3.1 section):
- Trough −1,137.8 bps at step 10,269 (34.2 h); was −1,137.8 at step 10,255.
- Back in band at 85.3 h; −52 bps at the capacity change; weekend path from 35 h
  identical.
- Holder PnL +209.4k (was +82.5k). It bought 9.42M stable with 9.21M reference (was 9.50M
  with 9.42M).

**The sawtooth is reduced, not gone, as measured; gone as a phenomenon.** Over steps
8,100–9,150 the amplitude is **384.5 bps** (−27.6 … −412.1), against 662.9 bps.
Story 3.1 predicted ≤ 60 bps; **that prediction missed.** The window holds three things:
- the attack's first steps (−28 → −200 bps, before the holder can act);
- a plateau over steps 8,400–9,000, amplitude **10.2 bps** (−204.4 … −214.7; was 265.2);
- the start of the fall to the trough from step 9,098, when the holder's reference is
  nearly spent (5% of ~39k at step 9,080 against the attacker's 3.2k dump).

Nothing in the window is above the holder's entry price any more. What remains on the
plateau is not the attacker's "10%-of-remaining" dumps, as the story's AC 6 put it: the
replay's attacker sells 0.2% of its remaining stable per step (pace 0.002; 23k at
step 8,100, 3.2k by step 9,080). Those dumps alternate with holder buys whose pace term,
not the cap, mostly binds there, so the price drifts from −215 to −204 bps. That is a
third of the 31 bps band. At whole hours the simulated price reads −213, −208, −204 bps
(was −171, −197, −196), so the residual is far inside what the hourly series can resolve.

**Calibrated baseline and stress: same outcome, the defender pays more.** Both still end
`peg_recovered` at step 7024 / 7225, trough −1,253.2 / −1,231.0 at step 50, final −19.9 /
−3.7 bps. The holder no longer buys past $0.98, so it absorbs less and the defender
spends more:

| run | defender spent | holder bought | holder PnL | redemption paid |
|---|---|---|---|---|
| baseline, 2.6 rule | 6,054,986 | 4,661,440 | +198,965 | 4,221,810 |
| baseline, 3.1 rule | **7,699,787** (+27%) | 2,887,234 | +154,691 | 3,173,906 |
| stress, 2.6 rule | 6,055,420 | 4,663,199 | +201,938 | 4,344,815 |
| stress, 3.1 rule | **7,702,127** (+27%) | 2,867,036 | +136,380 | 3,168,263 |

ADR-0021's "the defender's spend falls by 41%" is now "falls by 25%" (10.26M → 7.70M).

**Finding candidate: the 1992 flip moves from 5.7 to 5.2.** Story 3.1 predicted it would
stay at 5.7; **it does not.** `soros-1992`, attacker multiple 4.0–7.0 by 0.1 with the
holder, pre-3.1 and 3.1 code side by side. The pre-3.1 column reproduces ADR-0021's table
exactly.

| multiple (ratio) | 2.6 rule | 3.1 rule |
|---|---|---|
| 4.0–4.9 (0.847–1.037) | `max_steps` (final −143 … −178) | `max_steps` (final −148 … −199) |
| 5.0 (1.058) | `max_steps` | **exhausted**, `steps_run` 14,287 (113 before the cap) |
| 5.1 (1.079) | `max_steps` | `max_steps`, 96.0M of 100.7M paid |
| 5.2–5.6 (1.100–1.185) | `max_steps`, 92.8M–98.7M paid | **exhausted**, `steps_run` 10,506–13,965 |
| 5.7–7.0 (1.206–1.481) | exhausted, `steps_run` 9,661 → 9,269 | exhausted, `steps_run` 9,663 → 9,268 |

Every multiple from **5.2 (ratio 1.100)** upward now exhausts; 5.0 exhausts just before
the cap and 5.1 does not. The non-monotone 5.0/5.1 pair is the same kind of boundary
noise 2.5 saw at 5.1/5.2. From 5.7 up, `steps_run` is within ±3 of before.

Mechanism (diagnostic at 5.5, scratch script, not committed):
- **2.6 rule:** the holder's overshoots kept AMM spot at or above the $0.98 redemption
  payout in 7,945 of the 11,399 steps after step 3,000, with a max of 1.034. Above the
  payout the arbitrageur does not redeem. The holder kept buying stable above $0.98 at a
  loss (bought 16.1M; PnL −238k) and redeemed 15.8M; the arbitrageur redeemed 81.7M.
  97.6M was paid by step 14,400, so the reserves did not exhaust.
- **3.1 rule:** the holder spends about its own capital (bought 9.41M; PnL +51.6k) and
  redeems 9.2M. The price never goes above 0.988 after step 3,000, so the arbitrageur
  redeems 91.5M and the reserves exhaust (`steps_run` 12,353).

The 2.6 holder was acting as a second, loss-making defender of the floor, funded by
overpaying for its own fills. Without it, the F-07 dead zone shrinks from 4.0–5.6 to
4.0–4.9 plus 5.1. The 1992 analogue now exhausts at ratio 1.10, closer to F-02's 1.0 for
unconstrained redemption. The holder is profitable at every multiple (+28.5k … +180k;
was −1.02M … −6.5k). So ADR-0021's losing "zero-edge round trip" came mostly from the
overshoot, not from the 2% entry = 200 bps spread coincidence alone. Capped at its entry,
the holder buys only below $0.98 and redeems at $0.98.

`soros-1992` at its own multiple (6×) and `soros-1992-no-defense` both still exhaust.
`soros-1992` exhausts at `steps_run` 9,553 (was 9,550) with trough −5,975.4 (was −5,982.4).
The no-defense run exhausts at `steps_run` 7,805 (was 7,807) with trough −7,689.8 (was −7,692.4).

**Figures.** `make figures` regenerated all ten (433 s on 12 workers); seven PNGs
changed. The verdict surfaces are unchanged cell for cell: `threshold_surface`,
`threshold_surface_par`, `budget_depth` and `oracle_sensitivity` (trough range −1,253.2 …
−1,242.5 bps, p 0.69–0.75) all have the same p(stays broken) as before. Only the
surfaces' right-hand absorbed-ratio panels move slightly, because the holder buys less.
`time_to_parity` changes in three cells, all fast recoveries well inside 37 h (4× D\* at
0.3× and 0.4× attack: 0.2 → 0.3 h and 0.2 → 3.6 h; 2× D\* at 0.4×: 1.9 → 2.0 h). No cell
changes between in-time, clock and price, so F-11's refinement stands as written. The
overlay loses its sawtooth (VALIDATION.md, Story 3.1). The calibrated and both 1992
trajectories change as above. `budget_depth`, `oracle_sensitivity` and
`peg_trajectory_baseline` are byte-identical.

**The stale-figure guard did not see this change.** C\* did not move, so no scenario or
sweep hash moved, and `make figures-check` was green *before* the figures were
regenerated. The guard (Story 2.9) keys on source hashes by design. A behaviour change in
agent code with unchanged inputs is invisible to it. Here it was caught only because the
story said to re-run `make figures`. If that matters, a later story could add a code hash
(e.g. of `src/depeg_sim/`) to the manifest; this ADR does not propose it.

## Alternatives considered

- **A fee-exact sizing formula** (root of `(1−f)x² + (2−f)R·x + R² − k·p = 0`) for the
  holder only, or for both agents. Rejected (Story 3.1 Rulings 1): the holder-only
  version gives two formulas for one trade, and the shared one moves every arbitrageur
  trade and every scenario's output for < 0.1 bps.
- **Re-fit pace with the capped holder.** The trough is still 3.2 h late. Out of scope,
  as in 2.6 Rulings 3: two parameters fitted to one path.
- **Measure the sawtooth over steps 8,400–9,000 only.** That would match the phenomenon
  (10.2 bps), but the story fixed the window at 8,100–9,150. Both numbers are reported.
- **A multi-tranche holder** (several entry prices, F-09). Still the fix for the
  bimodal fit; Epic 3 stretch (3.7).
