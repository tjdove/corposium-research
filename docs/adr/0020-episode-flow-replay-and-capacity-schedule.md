# ADR-0020: Episode-flow attacker, re-fitted D*, fitted pace, inactive defender, and capacity-schedule semantics

**Status:** Proposed
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.5 AC 12

## Context
ADR-0019's amendment replaced the ratio-1.0 attacker with the observed episode flow and
scheduled a re-fit of D\*. Story 2.5 applies that, then replays March 2023 against the
observed USDC/USD series. That needed the one schema change in Epic 2: two data-only fields
(`environment.price_series_path`, `redemption.capacity_schedule`) in `kernel/config.py`.
Nothing else in `kernel/` changed; `PHASE_ORDER_VERSION` stays 1.

## Decision

1. **Episode-flow attacker, as applied.** `capital` = net USDC supply change from
   2023-03-10 to 2023-03-13 (00:00 UTC, DefiLlama CSV): 43,176,044,700 − 40,468,620,896 =
   $2,707,423,804, × `s` = 11,540,596 (status `secondary`). The AC's 10→13 window was used.
   The amendment's "≈ $4.0B" is the 11→15 change behind redemption capacity, which includes
   post-backstop redemptions. capital / (budget + reserves) = 0.064. The $1.2B/h peak CEX
   outflow is a cross-check only (the episode flow ≈ 2.3 peak hours).
2. **D\* = 16,666,667** (`market_depth_multiple` 16.67, **≈ $3.91B per side**, 16.7× the
   $234.6M Curve USDC leg), trough −1253.2 bps. Fitted by the 2.4 rule on the original grid
   (20M is the first to reach −1300, at −1061.3; 10M misses, at −1962.2; refined between
   them). This is physical-looking, but see Consequences: it holds only with the
   calibrated AMM defender absorbing most of the flow.
3. **Fitted pace = 0.002** (`assumption`). Scanned over [0.001, 0.002, 0.005, 0.01, 0.02,
   0.05, 0.1] on the replay. The rule is the closest `step_of_max_depeg` to step 9300 (the
   observed trough, 2023-03-11 07:00 UTC). 0.002 gives step 9488 (+0.63 h); 0.005 gives
   8821 (−1.33 h). Applies to the replay only; the calibrated scenarios keep 0.1.
4. **Defender inactive in the replay: `threshold_pct` 99.0**, budget kept at the calibrated
   41.3M (`assumption`; Circle did not buy USDC on AMMs, and 21Shares and Chainalysis report
   no such purchases). Chosen over `budget: 1` so the replay's schema matches the
   calibrated one parameter for parameter.
5. **Capacity-schedule semantics.** `redemption.capacity_schedule: list[{step,
   capacity_per_step}]` with steps strictly ascending (validator), default `[]`. At the
   start of `PROTOCOL_EVENTS` on a listed step, before `process()`, capacity becomes the new
   value and `capacity_changed {step, old, new}` is emitted once. The new capacity persists
   until the next entry. In the replay: 605.79 → 19,181.59 (reserves / 7,200, the whole
   reserve payable in a day) at step 25500 (2023-03-13 09:00 ET, banks reopen).
   Companion field: `environment.price_series_path` (relative to the scenario file,
   stored resolved). It is interpolated to steps and held past the end, and it requires
   volatility 0 and no shocks. Both fields enter `content_hash()` only when used: the
   series as its file sha256 (not its path, so the hash does not depend on the machine),
   the schedule only when non-empty. Every existing scenario's hash is unchanged.
   The replay also drops `peg_recovered`: its 8,100 steps of pre-attack calm would count
   as recovery (ADR-0010).

## Consequences
- **D\* is identified jointly with the absorbing side.** At D\* the calibrated defender
  spends 10.26M against the 11.54M attack. The replay faithfully has no AMM defender, and
  its trough is −5,769 bps vs −1,373 observed. The same fit rule applied to the replay would
  need D = 133,333,333 (≈ $31.3B per side), which is not physical. The missing agent is a
  discount buyer who expects par (market makers and funds, not the issuer). Until the model
  has one, "D\* is physical" holds only with the calibrated defender standing in for it.
- **The observed series as reference couples the AMM to the input** through the
  arbitrageur's oracle band. Validation statistics after the simulated price meets the
  observed path (63.3 h) are not independent evidence (VALIDATION.md).
- F-06 at the new D\*: the flip sits at nominal ratio ≈ 0.39 (0.30: all recover; 0.475: none),
  against the formula's 0.291. With a shallow pool the defender buys far below par (F-03),
  so its budget absorbs more than its face value. The formula is a lower bound unless
  price-adjusted. 2.6's x-axis may need the F-03 adjustment.
- 1992 at the new D\* (provisional per ADR-0019 amendment): multiple 6 still exhausts. The
  flip is no longer clean: 5.1 and 5.2 exhaust, 5.3–5.6 stall in the F-07 dead zone, and
  every multiple ≥ 5.7 (ratio 1.206) exhausts.

## Alternatives considered
- **Net burn over 11→15 March ($4.09B):** matches the amendment's figure, but it includes
  post-backstop redemptions the attacker did not drive. The AC fixes 10→13.
- **Re-fit D\* on the replay instead of calibrated-baseline:** gives a $31.3B-per-side
  depth and hides the missing absorber. Reported as a diagnostic, not applied.
- **Keep `peg_recovered` and raise `for_steps` above 8,100:** a recovery criterion bent to
  fit one scenario. Measuring the band from the series is cleaner.
- **Price-series hash by path:** machine-dependent hashes, so CI and local runs would
  disagree.
