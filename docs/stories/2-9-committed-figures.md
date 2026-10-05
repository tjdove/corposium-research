# Story 2.9: Committed Figures, Time-to-Parity, and `make figures`

Status: ready-for-dev

## Story

As a **reader**,
I want every chart in the note regenerable by one command and committed, with a chart that separates "lost the price" from "lost the clock",
so that the README and the note show figures without running code, and no figure can silently go stale against the scenario it claims to show.

## Acceptance Criteria

1. `plot_time_to_parity(sweep_dir) -> Path` writes `time_to_parity.png`: heatmap over the sweep's two axes of **median hours to first re-entry** into the recovery band (`steps_to_first_band_entry_p50 × interval / 3600`), cells where fewer than half the seeds ever re-enter (`steps_to_first_band_entry_n < n/2`) hatched and labelled "never"; a dashed contour at the latest start that can still hold `for_steps` by `max_steps` (`(max_steps − for_steps) × interval / 3600`, here 37 h) so the clock boundary is visible; heading states the criterion; reads only `mc.parquet` + manifest; synthetic-parquet test
2. `scripts/make_figures.py [--quick]` regenerates every figure in `docs/figures/` from its named source and writes `docs/figures/manifest.json`: for each figure its file, source (scenario path or sweep path), the source's hash (`content_hash()` for a scenario; for a sweep, sha256 of the spec file bytes + the base scenario's `content_hash()` — define this once as `sweep_spec_hash(spec_path)` in `experiments/sweep.py`), the generating function, and the git commit. Figures:
   - `peg_trajectory_baseline.png` ← `scenarios/soros-baseline.yaml`
   - `peg_trajectory_calibrated.png` ← `scenarios/calibrated-baseline.yaml`
   - `peg_trajectory_1992.png` and `peg_trajectory_1992_no_defense.png`
   - `validation_overlay_usdc_2023.png` ← `scenarios/usdc-2023.yaml` (**y-limits include both trough annotations**; the 2.6 figure clipped the observed one)
   - `threshold_surface.png` ← `sweeps/threshold-surface-ref-mc.yaml` (oracle criterion)
   - `time_to_parity.png` ← same sweep
   - `threshold_surface_par.png` ← `sweeps/threshold-surface-mc.yaml` (the F-11 record; caption says why it exists)
   - `budget_depth.png` ← `sweeps/budget-x-depth-mc.yaml`
   - `oracle_sensitivity.png` ← `sweeps/oracle-lag-mc.yaml`
   `--quick` runs each sweep with `seeds: {count: 2}` into a temp dir and writes nothing to `docs/figures/` except a `quick-ok` marker: it is a smoke test, not a regeneration
3. `Makefile` with targets `figures` (full: runs every sweep, then the script; prints wall time), `figures-quick`, `figures-check` (the guard in AC 4), `test`, `lint`
4. **Stale-figure guard:** `scripts/check_figures.py` recomputes every source hash and compares to `docs/figures/manifest.json`; exit 1 naming each stale figure. CI runs `make lint test figures-check` and, on a separate job, `make figures-quick`. The guard does not run sweeps and does not compare PNG bytes (matplotlib output is not byte-stable across platforms)
5. All nine figures regenerated in full on Seoul and committed with the manifest; `docs/figures/README.md` lists each figure, its source, its regenerating command, the finding(s) it supports, and a one-sentence caption that names what the reader is looking at (for the surfaces: which cells are price and which are clock)
6. README gains a "Results so far" section: the validation overlay and the time-to-parity chart, each with its caption and a link to FINDINGS.md
7. `pytest` and `ruff check .` pass; CI green on both jobs; a deliberate edit to a scenario's tolerance in a scratch branch makes `figures-check` fail (show the output in the Debug Log, then discard the branch)

## Tasks / Subtasks

- [ ] Time-to-parity chart (AC: 1)
  - [ ] `plot_time_to_parity`; test; run on `threshold-surface-ref-mc`; look and describe
  - [ ] Commit separately: `story 2.9: time-to-parity chart`
- [ ] Figure script and manifest (AC: 2)
  - [ ] `sweep_spec_hash`; `make_figures.py`; overlay y-limit fix; `--quick`
- [ ] Make targets, guard, CI (AC: 3, 4, 7)
- [ ] Regenerate, commit, document (AC: 5, 6)
- [ ] Close out (AC: 7)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.9: committed figures and make figures`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.8 (Status: done)**

- "Stays broken" has two causes (price at ≥ 2× D\*, clock at D\*); every surface figure
  needs the time-to-parity panel beside it or a caption that says which is which.
- The full oracle-criterion surface takes ~2.5 min on 8 workers and 17 min on 2; `--quick`
  exists so CI never runs a full sweep.
- The overlay clip from 2.6 is still open (review ruling 4).

[Source: docs/stories/2-8-reference-recovery.md#Senior-Developer-Review, docs/FINDINGS.md F-11 refinement]

### Why the guard keys on source hashes, not pixels

A figure is stale when the scenario or sweep it was made from has changed, which the
manifest records exactly. PNG bytes differ across matplotlib versions and platforms, so a
byte comparison would fail CI for no reason. The guard therefore never re-runs anything;
`figures-quick` is the separate smoke test that the pipeline still executes.

### Time-to-parity semantics

`steps_to_first_band_entry` under the oracle criterion is the first step the AMM is within
31 bps of the published oracle price. "Never" = no re-entry by `max_steps`. The dashed
37 h contour is `(18000 − 6900) × 12 s`: a run that first re-enters after it cannot
satisfy `peg_recovered` even if it never leaves the band again. Cells above that line but
finite are "clock"; "never" cells are "price". Say this in the caption.

### Figure conventions

As in `charts.py` (10×6 per panel, 150 dpi, footer with source and hash). Keep every
figure's footer hash equal to the manifest's source hash so a reader can match them.

### References

- [Source: docs/epics.md#Story-2.9]
- [Source: docs/FINDINGS.md] — F-08 confirmation, F-10, F-11 (+ refinement)
- [Source: docs/adr/0014-manifest-embeds-resolved-config.md]
- [Source: docs/stories/2-6-holder-agent.md#Senior-Developer-Review] — ruling 4 (overlay clip)

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-9-committed-figures.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: `make figures` wall time, the guard failing on the scratch edit, CI job results, tests, lint)_

### Completion Notes List

_(include: time-to-parity chart description — which cells are clock and which are price; any figure whose look changed; README section text)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.8 review; time-to-parity chart added per review ruling 3
