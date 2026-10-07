# ADR-0029: Mean-reverting (OU) reference; κ fitted from the calm series; the clock is the model's, the wander was the random walk

**Status:** Accepted (finding, amended in review 2026-10-07: re-entry time is reference-independent; F-04 resolved; ADR-0023 amended to a sensitivity check for calm sweeps; the note uses OU + par)
**Date:** 2026-10-07
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.6 (F-04 refinement, ADR-0023)

## Context

The calm reference price has been a driftless log random walk. Over one 6,900-step
recovery window it wanders by about 26 bps (σ√6900), the width of the ±31 bps band, so a
par criterion fails late recoveries and counts above-par drift as "stays broken"
(F-04 refinement, F-11). Story 2.8 worked around this by measuring recovery against the
oracle's published price (ADR-0023). A real off-venue stablecoin price mean-reverts to
par through redemption arbitrage. This story puts that in the environment, fits it from
the same calm series σ came from, and re-asks the par question.

## Decision

1. **The update.** `EnvironmentConfig.mean_reversion_per_step` (κ, default 0, `ge=0,
   lt=1`). With κ > 0, once per step in `ENVIRONMENT_UPDATE`:
   `log p ← log p + κ·(log base − log p) + σ·z`, one `standard_normal` draw when σ > 0
   and none when σ = 0, then shocks as before (a shock decays back like any deviation).
   - κ = 0 takes the old code path unchanged. soros-baseline, soros-volatile (which draws
     every step) and calibrated-baseline produce byte-identical timeseries, summary,
     events and checkpoints; the run manifest's resolved config gains
     `"mean_reversion_per_step": 0.0`.
   - `content_hash()` drops the field at 0, so every existing scenario hash is unchanged
     (pinned).
   - κ > 0 with `price_series_path` is rejected: "mean_reversion_per_step must be 0: the
     observed series is the whole environment and does not revert".
   - `ReferencePrice` itself accepts κ ∈ [0, 1]; κ = 1 pins the price to base plus that
     step's noise (tested). The config field stops below 1, as the AC specifies.
   - The change is in `environment/` and `kernel/config.py` only; `PHASE_ORDER_VERSION`
     is still 1.
2. **The fit** (`scripts/fit_reversion.py`, status `fitted` in SOURCES.md):
   - Model: AR(1) through the origin on hourly `x = ln(close / 1.0)` of
     `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv` (120 points, 119 pairs).
   - **φ = 0.6123 ± 0.0728** (95% CI 0.470–0.755). The unit-root statistic
     (φ − 1)/se = −5.33 is below the Dickey–Fuller 5% critical value for no constant,
     −1.95, so φ is significantly below 1: the series is not a random walk at this
     horizon.
   - κ_step = 1 − φ^(1/300) = 0.00163402 → **0.001634** (4 significant figures, as σ).
   - Half-life **1.41 h**. Stationary sd **5.40 bps** in the model (σ 3.086e-05 with κ);
     6.07 bps in the data (sd(e)/√(1 − φ²)). Both are well inside the 31 bps band.
   - σ is not refitted. It was the sd of hourly returns scaled by √300 under the
     random-walk assumption; the model's stationary sd with the fitted κ (5.4 bps) is
     close to the data's sample sd (5.0 bps), so the pair is consistent.
   - Caveat: Bitstamp's thin calm book (13 zero-volume hours, isolated prints).
   - Sensitivity, not used: an AR(1) with a constant, which reverts to the series mean
     (−3.4 bps) rather than par, gives φ = 0.43 ± 0.08.
3. **`scenarios/calibrated-baseline-ou.yaml`** (`741f1bdd0012`) is calibrated-baseline
   plus κ; `sweeps/threshold-surface-ou-mc.yaml` is the 2.7 par surface with that base.
   `peg_recovered.reference` stays `par`.

## Finding: what moved

Per-row 0.5 crossings on nominal ratio (linear | logistic; 16 seeds; current code for all
three):

| depth | par, random walk (2.7) | oracle, random walk (2.8) | par, OU (3.6) |
|---|---|---|---|
| 0.25× D\* | not reached (max 0.19) \| 1.74 | not reached (max 0.06) | not reached (max 0.00) |
| 0.5× D\* | 0.93 \| 1.20 | not reached (max 0.25) \| 1.77 | not reached (max 0.00) |
| 1× D\* | 0.57 \| 0.56 | 0.68 \| 0.65 | **0.70** \| 0.70 |
| 2× D\* | 0.50 \| 0.50 | 0.54 \| 0.52 | **0.55** \| 0.55 |
| 4× D\* | 0.60 \| 0.60 | 0.69 \| 0.62 | **0.70** \| 0.70 |

- **The surface becomes 0/1.** Every one of the 40 cells has p_stays_broken exactly 0
  or 1.
- **The wander is gone.** Runs ending more than 31 bps *above* par: 68 → 0. Runs that
  re-enter before the deadline and fail to hold: 46 (par) and 29 (oracle) under the random
  walk → 0.
- **≤ 0.5× D\*: nothing breaks at any attack.** All 256 runs recover.
- **1× D\*: the clock, unchanged.** At ≥ 0.8× all 64 runs re-enter (first re-entry
  steps 12,557–16,931, every one after step 11,100) and none recover. Median hours
  41.9 / 48.2 / 52.2 / 56.4. The median final deviation against par is in band
  (−16 bps).
- **≥ 2× D\* at ≥ 0.8×: the price, unchanged.** All 128 runs never re-enter; final
  −3,486 / −4,062 bps at 1.5×, the same as both random-walk surfaces. 2× D\* at 0.6× is
  clock (42.5 h).
- **Time to first re-entry does not depend on the reference.** It is the random-walk
  surface's in every cell. The reference process changes what happens *after*
  re-entry, not when re-entry happens.

**Verdict on F-04's root cause.** At calm volatility the par criterion's spurious
"broken" runs (above-par endings, early re-entries that drift out) were the random walk,
as the F-04 refinement said: an anchored reference removes all of them. The clock result
at D\* and the price result at ≥ 2× D\* are the model's: they are identical under a
reference that cannot wander. **The oracle criterion was a workaround for the random
walk.** With an OU reference, par agrees with the oracle criterion's linear crossings
to within 0.02 at every depth. The logistic crossings differ by up to 0.08 (4× D\*:
0.70 vs 0.62) only because the oracle surface keeps a few early-failing runs that OU +
par does not. OU + par is cleaner than random walk + oracle, so calm-volatility sweeps
can use par.

## Consequences

- F-11's clock statement ("at calibrated depth the issuer wins the price and loses the
  clock") is now shown without the oracle criterion. The note can state it against par,
  which needs no explanation of oracles.
- Earlier oracle-criterion sweeps (2.8 onward) stand. Their linear crossings match
  OU + par within 0.02, so nothing published moves. Re-running them on the OU base is not needed
  for the claims they support.
- Not tested: the stress volatility (calibrated-stress, F-04's original case) with κ.
  Over 60 h the OU stationary sd at stress σ would be ≈ 132 bps, still above the band,
  so the stress question is not answered by this ADR.
- usdc-2023 is unaffected: an observed series cannot take κ.

## Alternatives considered

- **Fit with a constant** (revert to the sample mean): rejected, since the model's
  reference reverts to `base_price`. Reported as sensitivity: φ 0.43 ± 0.08, faster
  reversion, which would only strengthen the result.
- **Fit on minutes, or another venue's series:** no committed data; the calm hourly
  series is the one σ came from.
- **Tune κ until the surface looks right:** forbidden by the story, and not done. κ comes
  from the fit rule alone.
- **Revert in price rather than log price:** equivalent to first order at deviations of
  a few bps; log keeps the price positive and matches the existing log-normal update.
