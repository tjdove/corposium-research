# ADR-0022: Threshold surface: `p_stays_broken`, the absorbed ratio, linked-axis scales; oracle lag does not matter; at calibrated depth "stays broken" is mostly the clock

**Status:** Accepted (finding, amended in review 2026-10-04: §5 collapse is a conservation check, the nominal per-depth crossings are the result; §6 → F-10; §7 → F-11 with the budget-vs-depth mechanism; stress result → F-04 refinement; AC 9 sentence not quoted; Story 2.8 inserted)
**Date:** 2026-10-04
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.7 AC 10

## Context
Story 2.7 draws the note's two sweep charts at calibrated scale with the holder present:
the threshold surface (pool depth × attacker capital) and oracle-lag sensitivity. Four
choices needed recording: which outcome the surface shows, how the F-03 collapse ratio
is defined, how a sweep moves the holder with depth, and where charts get scenario
parameters. Both sweeps also produced results that future stories depend on.

The surface was first run on `calibrated-stress` as originally specified. `p_stays_broken`
was at least 0.6875 in all 40 cells, and 11 of the 16 seeds never recovered in any cell
(F-04). The Rulings moved the surface to `calibrated-baseline` (calm volatility, per
F-04). The oracle sweep stays on stress, because oracle lag only matters when the
reference moves.

## Decision

1. **The surface metric is `p_stays_broken = 1 − p_peg_recovered`, not
   `p_reserves_exhausted`.** At calibrated scale redemption pays 605.79 stable per step:
   10.9M of the 138.1M reserves in 18,000 steps. Exhaustion is unreachable at any
   attacker size in the sweep (observed: `p_reserves_exhausted = 0` in all 40 + 20
   cells). The failure mode is "not back within ±31 bps of par for 6,900 steps by step
   18,000", which is `terminated_by != peg_recovered`. The chart computes it from
   `p_peg_recovered` (no new aggregate column). Its heading says so and cites F-06. The
   surface is at **calm volatility**, per F-04; the stress-base result is recorded in
   story 2.7's Blockers and Completion Notes.

2. **Absorbed ratio** = `capital / (defender_bought_stable + holder_bought_stable +
   redemption_paid_total)`, the three sinks for the attacker's stable at calibrated
   scale. Per grid point it uses the seed means from `mc.parquet`. It is an **outcome,
   not a parameter** (F-03): it diagnoses, it does not predict. It can sit below 1
   when the attack is fully absorbed, because the holder recycles reference through
   redemption and buys again (ADR-0021), so the sinks count more than the attacker
   sold. `summarize` gains the three fields. `Defender.bought_stable` is a new counter
   (sum of `amount_out` of executed buys) that is kept out of the snapshot, so
   timeseries and checkpoints are byte-unchanged.

3. **`LinkedAxis.scales`** (optional, one per path, all > 0, checked in `expand` with
   `SweepSpecError`): path `i` is set to `value × scales[i]`. A scale of exactly 1
   leaves the value untouched, and unscaled axes are dumped to the manifest without the
   key. Existing sweeps expand to identical cells (pinned by test). Used here to keep
   the holder at `C*/D* = 0.55` of each cell's depth.

4. **The sweep manifest embeds `base_config`**, the resolved base scenario: ADR-0014 at
   sweep level. Sweep charts read only `mc.parquet` and the manifest. The dollar scale
   `s` ($234.6 per model unit, SOURCES.md) is a chart constant (`USD_PER_UNIT`) with a
   keyword override, because it is not a config field.

5. **Collapse verdict (finding): one curve on the absorbed ratio, to within ±0.04; a
   fan in the strict sense.** The per-depth logistic 0.5 crossings on the absorbed ratio
   are 1.029 (0.25× D\*, extrapolated past its largest observed 1.017), 1.017, 0.977,
   0.953 and 0.961: mean 0.987, sd 0.034. On the nominal ratio the same rows cross at
   1.74 (extrapolated), 1.20, 0.56, 0.50 and 0.60. The pooled fit crosses at 1.005. The
   absorbed ratio improves the pooled log-likelihood from −332.2 (nominal) to −211.6. A
   likelihood-ratio test of per-depth curves against the pooled one gives 179.4 on 8 df
   (χ²₀.₉₉₉ = 26.1), so the residual depth ordering is real: deeper pools stay broken at
   a slightly lower absorbed ratio. F-03 holds at calibrated scale with the buyer
   present: nominal crossings fall from shallow to D\* (cheaper defense in a thin pool).
   But it **saturates above D\***: 2× and 4× cross at 0.50 and 0.60, not lower.

6. **Oracle lag does not matter under deviation-triggered updates (finding).** On the
   stress base at the episode attack (ratio 0.064), the mean trough across all 20
   (heartbeat, threshold) cells lies in −1,253.2 … −1,242.5 bps. The calibrated cell
   (6,900, 0.25%) gives −1,242.5, within 0.5 bps of the zero-lag oracle's −1,243.0.
   Heartbeats ≥ 300 steps give identical results at every threshold. Only the 1%
   threshold at heartbeat ≥ 300 moves the trough, by 10.2 bps, to −1,253.2 in every
   seed. `p_stays_broken` is 0.6875–0.75 everywhere: the F-04 floor. The probe at the
   base attack gives 0.688 on the same 32 seeds.

7. **At calibrated depth, "stays broken" is mostly the clock, not the attack
   (finding).** On the calm surface, 279 of 640 runs do not recover. Of these, 168 end
   below −31 bps of par, 68 end above +31 bps, and 43 end inside the band without
   having held it for 6,900 steps. In the above-band and in-band runs the AMM tracks the
   reference (median gap −9.8 and −2.6 bps). In the above-band runs the reference
   itself has drifted 43–85 bps above par. The calm reference's own spread over one
   6,900-step window is σ√6900 ≈ 26 bps, comparable to the 31-bps band. A recovery that
   starts late in the 60 h cannot accumulate 6,900 in-band steps against par. A
   reference-relative variant, "not recovered **and** AMM more than 31 bps below the
   *reference* at the end", gives 0 / 16 at 0.25× and 0.5× D\* at every ratio, ≤ 2 / 16
   at D\*, and crosses 0.5 only at 2× and 4× D\* (nominal ≈ 0.69 and 0.70). Measured that
   way, at calibrated depth and below the defender plus holder absorb attacks up to 1.5×
   resources, and the AC 9 headline's X measures recovery speed against the clock. This
   is F-04 again at calm volatility. It strengthens the case for the Epic 3
   `peg_recovered.reference: oracle` option.

## Consequences
- The headline sentence in the AC 9 form is true as stated (X = 0.56 at D\*, absorbed
  boundary 0.99 ± 0.04). It needs §7's qualification next to it, or the Epic 3
  reference option, before the note quotes X as "the attack wins".
- The F-03 collapse is a usable framing at calibrated scale. The note should quote the
  ±0.04 band and the saturation above D\*, not "one curve".
- "Oracle lag does not matter under deviation-triggered updates at Chainlink's cadence"
  is supported by the data and can be quoted.
- Older `sweep.parquet` files without the new columns aggregate to NaN for them.

## Alternatives considered
- **`p_reserves_exhausted` surface:** identically zero at calibrated throughput (F-06).
- **Absorbed ratio per run** (binned like Story 2.2): the AC fixes charts to
  `mc.parquet`, which is per grid point. Seed means are the available resolution.
- **A pydantic validator for `scales`:** it would surface as `ValidationError`, not
  `SweepSpecError`, and would split sweep-spec errors between two types.
- **Reading `budget + reserves` from the YAML in chart code:** breaks "reproducible
  from the output directory" (ADR-0014).
- **Charting §7's reference-relative variant:** out of AC scope. Left to the dev
  manager, with the diagnostic in the story Debug Log.
