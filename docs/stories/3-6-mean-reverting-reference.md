# Story 3.6 (stretch): Mean-Reverting Reference

Status: ready-for-dev

## Story

As a **researcher**,
I want the calm reference price to revert to par the way an off-venue stablecoin price does,
so that the surface can be measured against par again and the note can say whether "D\* breaks on the clock" is the model or the random walk.

## Acceptance Criteria

1. `EnvironmentConfig` gains `mean_reversion_per_step: float = Field(default=0.0, ge=0, lt=1)`; when > 0 the per-step update becomes `log p ← log p + κ·(log base − log p) + σ·z` (κ = `mean_reversion_per_step`, σ = `volatility_per_step`, one `standard_normal` draw per step as now); κ = 0 reproduces the current random walk byte-for-byte (test); incompatible with `price_series_path` (validator names the rule); every existing scenario `content_hash()` unchanged
2. **Calibrate κ** from `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv`: `scripts/fit_reversion.py` fits an AR(1) on hourly log deviations from 1.0 (`x_{t+1} = φ x_t + ε`), converts to the 12-s step (`κ_step = 1 − φ^(1/300)`), prints φ, κ_step, the implied half-life in hours, and the stationary sd; a `--dry-run`; the result goes in SOURCES.md with status `fitted` and the caveat that 13 zero-volume hours and isolated prints inflate the calm series (SOURCES.md note)
3. `scenarios/calibrated-baseline-ou.yaml`: `calibrated-baseline.yaml` plus κ, header stating the fit; `python run.py` on it; `peg_recovered.reference` stays `par`
4. `sweeps/threshold-surface-ou-mc.yaml`: `threshold-surface-mc.yaml` (the par-criterion surface of 2.7) with the OU base; run; `plot_threshold_surface` and `plot_time_to_parity` on it; per-row 0.5 crossings beside the 2.7 (par, random walk) and 2.8 (oracle criterion) tables
5. Completion Notes answer: with a reference that reverts, does the par criterion still show D\* breaking on the clock (median re-entry after 37 h at ≥ 0.8× resources)? Does the above-par "stays broken" population (F-11: 68 runs ending > +31 bps) disappear? Do the ≥ 2× D\* rows still lose the price? One sentence on whether the oracle criterion (ADR-0023) is still needed for sweeps or was a workaround for the random walk
6. A `Proposed` ADR: the OU update, κ and its fit, what moved in the surface, and the verdict on F-04's root cause; a finding candidate if the clock result changes
7. Figures registered (`threshold_surface_ou.png`, `time_to_parity_ou.png`); `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] OU update and validator (AC: 1)
  - [ ] Commit separately: `story 3.6: mean-reverting reference`
- [ ] Fit κ and scenario (AC: 2, 3)
- [ ] OU surface and charts (AC: 4)
- [ ] Verdict, ADR, figures, close out (AC: 5, 6, 7)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.6: mean-reverting reference and OU surface`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.5 (Status: done)**

- The guard now warns on code changes; this story changes `environment/`, so `make
  figures` regenerates and the manifest's code hash moves — expected.
- Predictions below are predictions.

[Source: docs/stories/3-5-hardening-and-polish.md#Senior-Developer-Review, F-04 refinement, F-11 refinement]

### Why this story exists

F-04 (and its refinement from 2.7): the calm reference is a driftless random walk, so over
6,900 steps it wanders ≈ 26 bps — the band width — and a par criterion fails late
recoveries and counts above-par drift as "broken". 2.8 worked around it with the oracle
criterion. A real off-venue stablecoin price mean-reverts through redemption arbitrage.
This story puts that in, calibrated from the same calm series σ came from, and re-asks
the question the oracle criterion answered. If D\* still breaks on the clock under OU +
par, the clock result is the model's; if not, part of it was the random walk.

### The fit, and its caveat

The calm series is thin (Bitstamp; 13 zero-volume hours; isolated prints to 0.99636). An
AR(1) on 120 hourly points gives a rough φ; report its standard error. If φ is not
significantly below 1, say so — then the data cannot distinguish OU from a random walk at
this horizon and the story's answer is "undetermined from this series", which is still an
answer. Do not tune κ to make the surface look right.

### Predictions (to be checked)

- φ ≈ 0.7–0.9 hourly (half-life a few hours); κ_step ≈ 0.001–0.002; stationary sd ≈ 5–10
  bps, inside the band.
- With OU + par: the above-par population vanishes; ≤ 0.5× D\* back in time at every
  ratio; D\* still clock at ≥ 0.8× (median re-entry 42–56 h is the redemption channel,
  not the reference); ≥ 2× D\* still never re-enters at ≥ 0.8×.
- Verdict: the oracle criterion was a workaround, and both criteria now agree at
  calibrated scale; the note can use par throughout, which is simpler to explain.

### Cost

Surface 640 runs (≈ 2.5 min on 10 workers). Fit: seconds.

### References

- [Source: docs/epics.md#Story-3.6]
- [Source: docs/FINDINGS.md] — F-04 (+ refinement), F-11 (+ refinements)
- [Source: docs/adr/0023-reference-relative-recovery.md] — what this story re-tests
- [Source: docs/calibration/SOURCES.md#environment]
- [Source: src/depeg_sim/environment/price_process.py]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-6-mean-reverting-reference.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: fit output with standard error, OU surface run with wall time, crossings table, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: φ, κ, half-life, stationary sd; the three-way crossings table; the AC 5 answers; chart descriptions; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.5 review (first Epic 3 stretch story)
