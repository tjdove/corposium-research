# Story 2.5: USDC March-2023 Validation

Status: in-progress

## Story

As a **researcher**,
I want the model to reproduce the shape of a real depeg,
so that the note's claims rest on more than internal consistency.

## Acceptance Criteria

### Part A — re-anchor the attacker and re-fit depth (ADR-0019 amendment)

1. `docs/calibration/SOURCES.md` attacker row becomes `secondary`: `capital` = net USDC supply change from 2023-03-10 to 2023-03-13 computed from the committed `data/usdc_supply_defillama_2023-03-01_2023-03-20.csv` (show the two supply figures and the difference), converted by `s`; the peak-hour CEX outflow ($1.2B/h, Chainalysis) is stated as a cross-check, not an input; the "ratio 1.0" row is removed and its removal noted
2. `scripts/fit_depth.py` re-run on the re-anchored `calibrated-baseline.yaml` with the original grid (1M…500M); the AC 2 rule from 2.4 applies unchanged; `D*` reported as model units, as `market_depth_multiple`, **and as dollars per side at `s`**, alongside the Curve USDC leg ($234.6M) for comparison; both calibrated YAMLs updated; the `market_depth_multiple` row updated with the new value and "re-fit after attacker re-anchor (ADR-0019 amendment)"
3. `scripts/probe_boundary.py` re-run at the new `D*` on ratios `[0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 1.0]` with `deliverable reserves` printed alongside; Completion Notes state where the F-06 flip sits now and whether the F-06 formula still predicts it
4. `scenarios/soros-1992.yaml` and `-no-defense.yaml` re-run at the new `D*`; the 5.3× flip re-scanned (step 0.1× between 4.0 and 7.0); new values in both YAML headers; Completion Notes say whether F-07's conclusion holds
5. Commit Part A separately: `story 2.5: re-anchor attacker to episode flow; re-fit D*`

### Part B — observed-series environment and the replay

6. `EnvironmentConfig` gains `price_series_path: Path | None = None` (relative to the scenario file's directory); when set, `volatility_per_step` must be `0` and `shocks` empty (validator), and `ReferencePrice.from_config` loads the CSV (columns `unix, close` required), linearly interpolates `close` to 12-second steps from the first timestamp, and uses that as the reference price; past the end of the series the last value holds; `price_series_hash` (sha256 of the file) is included in `ScenarioConfig.content_hash()` via a validator that reads the file at load time (so a changed CSV changes the hash)
7. `ReferencePrice` emits `price_updated` as before; a test loads a 5-row synthetic CSV and checks interpolation at known steps and the hold-last behaviour; a second test shows two scenarios identical except for the CSV contents have different `content_hash()`
8. `scenarios/usdc-2023.yaml`: calibrated-baseline parameters, `environment.price_series_path: ../data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv`, `start_step` at the step corresponding to 2023-03-10 22:00 ET (Circle's disclosure; compute from the series' first timestamp and state it), attacker `capital` from AC 1, `pace` **fitted** so the simulated trough's timing lands within ±2 hours of the observed trough (2023-03-11 ~02:00 ET per Chainalysis; state the step) — scan `pace` over `[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]` and pick the closest, `assumption`; defender budget as calibrated but **`threshold_pct` set so the defender does not act** (Circle did not buy USDC on AMMs; `assumption`, cite 21Shares/Chainalysis silence) — or budget 1, whichever is cleaner, state which; redemption capacity: calibrated throughput until the step for **2023-03-13 09:00 ET** (banks reopen / Circle's statement), then a scheduled change to a capacity that clears the queue within one day (new `RedemptionConfig.capacity_schedule: list[{step, capacity_per_step}]`, applied in `PROTOCOL_EVENTS`; validator: steps ascending); `max_steps` covering 2023-03-10 22:00 ET to 2023-03-14 12:00 ET
9. `plot_validation_overlay(run_dir)`: one panel, elapsed hours on x (origin = series start), **observed** reference price (from the manifest's `price_series_path`, re-read) and **simulated** AMM price on the same axis in bps from peg; vertical markers at attack start and at the capacity-schedule step; annotations for observed trough (value, time) and simulated trough (value, time); chart conventions apply; footer with hash
10. Quantitative comparison in Completion Notes **and** written into `docs/calibration/VALIDATION.md`: observed vs simulated trough depth (bps) and time (hours after series start); observed vs simulated time at which the price is last outside the ADR-0013 band; the direction and timing of recovery relative to the capacity-schedule step; one paragraph on what matches and what does not, and why
11. `tests/test_usdc_2023.py`: scenario validates; hash includes the CSV; short run (`max_steps` 500) completes; `plot_validation_overlay` produces a PNG on a tiny run
12. A `Proposed` ADR for: the episode-flow attacker anchor as applied, the new `D*`, the fitted `pace`, the defender-inactive assumption, and the capacity-schedule semantics; a findings write-up in Completion Notes for anything new (candidates: whether `D*` is now physical; what the overlay shows about the model's recovery vs the real one)
13. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Part A (AC: 1–5)
  - [x] Compute net burn from the committed CSV; SOURCES.md attacker row; remove ratio-1.0 row
  - [x] Re-fit `D*`; update YAMLs and SOURCES.md; report three units
  - [x] Re-probe boundary; re-run and re-scan 1992
  - [x] Commit Part A

- [ ] Schema and environment (AC: 6, 7)
  - [ ] `EnvironmentConfig.price_series_path`; validator; hash inclusion
  - [ ] `RedemptionConfig.capacity_schedule`; validator
  - [ ] `ReferencePrice.from_config` series loading + interpolation; `RedemptionModule` schedule application in `PROTOCOL_EVENTS` (emit `capacity_changed`)
  - [ ] Tests per AC 7 plus a capacity-schedule test (queue drains after the step)

- [ ] Replay scenario (AC: 8)
  - [ ] Compute `start_step`, backstop step, `max_steps` from the series timestamps; put the arithmetic in the YAML header
  - [ ] Scan `pace`; pick; record
  - [ ] Run; record three CLI lines

- [ ] Overlay and validation doc (AC: 9, 10)
  - [ ] `analysis/charts.py::plot_validation_overlay`
  - [ ] `docs/calibration/VALIDATION.md`; look at the PNG and describe it

- [ ] ADR, tests, close out (AC: 11, 12, 13)
  - [ ] Proposed ADR; `tests/test_usdc_2023.py`
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.5: usdc march-2023 validation`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.4 (Status: done)**

- **The attacker ratio was the wrong input, not the depth grid.** D\* at $430B/side was
  the model absorbing a $42B attacker when the episode's net burn was ~$4B. Part A fixes
  the input and re-fits. Expect D\* in the low billions of dollars; report it in dollars
  so a reader can judge it against the Curve leg.
- Pace doesn't move the trough; it moves the trough's *timing*. That's why AC 8 fits pace
  to timing after depth is set.
- F-06: with throughput-bound redemption the far side of the boundary is "stays broken,"
  and recovery needs an outside backstop. AC 8's capacity schedule is that backstop.
- F-07: sequential defenses strand the price between them. The USDC replay has no AMM
  defender, so this doesn't arise here; it's a 1992 phenomenon.
- Builder may merge an approved-but-unmerged story branch into `main` before starting;
  the dev manager will confirm merges before prompts from now on.

[Source: docs/stories/2-4-depth-fit-and-1992.md#Senior-Developer-Review, docs/FINDINGS.md F-05 correction, F-06, F-07]

### Why this story allows schema changes

Two fields are required by the validation itself: an observed reference series, and a
scheduled change in redemption capacity (the banking-weekend-then-backstop mechanism).
Both are data-only additions to existing config models with validators, both default to
"absent" so every existing scenario and hash is unchanged. Nothing in kernel/ changes.
This is the one story in Epic 2 with a schema edit; say so in the ADR.

### Series interpolation

Hourly candles → 12 s steps means 300 steps per candle. Linear interpolation of `close`
between consecutive candle timestamps; step `k` is at `unix_0 + 12k`. Store the
interpolated array once at construction (≈ 20k floats for the stress file). The
environment still emits one `price_updated` per step. `volatility_per_step` must be 0 and
`shocks` empty when a series is set: the series *is* the environment.

### Timestamps to compute (state them in the YAML header)

- Series start: first `unix` in the stress CSV (2023-03-10 00:00 UTC per the filename).
- Attack start: 2023-03-10 22:00 ET = 2023-03-11 03:00 UTC → `(1678503600 − unix_0) / 12`.
- Observed trough: ~2023-03-11 02:00 ET = 07:00 UTC (Chainalysis "by 2am").
- Backstop / banks reopen: 2023-03-13 09:00 ET = 13:00 UTC. (The Fed/Treasury/FDIC
  statement was Sunday evening 2023-03-12; Circle's "100% safe" statement and the repeg
  were Monday morning. Use Monday 09:00 ET and say why.)
- End: 2023-03-14 12:00 ET = 16:00 UTC.

If the stress CSV ends before 2023-03-14, hold-last applies and the header says so.

### What "matches" should mean in VALIDATION.md

Be specific and modest. The model has one venue, no CEX, no cross-stablecoin rotation,
no bank. It can plausibly match: trough depth (by construction, via D\*), trough timing
(via pace), and the *shape* of the plateau (stays broken until the backstop). It cannot
match: intra-weekend wobbles driven by news, or the exact recovery slope (which depended
on how fast real redemptions cleared). Say which is which.

### Defender in the replay

Circle did not intervene on AMMs; the "defense" was the redemption promise and, after
Monday, honouring it. Simplest faithful encoding: keep the defender agent (so the
scenario schema is the calibrated one) but set `threshold_pct` to a value it never
reaches (e.g. 99.0) and note it. Setting budget to 1 also works; pick one and state it.

### References

- [Source: docs/epics.md#Story-2.5]
- [Source: docs/adr/0019-fitted-depth-1992-and-boundary.md] — review amendment
- [Source: docs/FINDINGS.md] — F-05 correction, F-06
- [Source: docs/calibration/SOURCES.md] — attacker, capacity, pool sections
- [Source: data/README.md] — stress and supply CSVs
- Chainalysis (trough by 2am ET Mar 11; $1.2B/h): https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/
- 21Shares (repeg Mar 13; reserves split): https://www.21shares.com/en-eu/insights/newsletter-issue-193

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-5-usdc-validation.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output; fit table, probe table, pace scan, 1992 re-scan, replay CLI lines)_

### Completion Notes List

_(include: net burn figure, new D* in three units, F-06 flip location, F-07 status, fitted pace, overlay description, VALIDATION.md summary, ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.4 review; Part A added per ADR-0019 amendment
