# Story 2.9: Committed Figures, Time-to-Parity, and `make figures`

Status: review

## Story

As a **reader**,
I want every chart in the note regenerable by one command and committed, with a chart that separates "lost the price" from "lost the clock",
so that the README and the note show figures without running code, and no figure can silently go stale against the scenario it claims to show.

## Acceptance Criteria

1. `plot_time_to_parity(sweep_dir) -> Path` writes `time_to_parity.png`: heatmap over the sweep's two axes of **median hours from run start to first re-entry** into the recovery band (`(step_of_max_depeg + steps_to_first_band_entry) × interval / 3600`, both from the same run, aggregated as the median across seeds; **amended 2026-10-05** — `steps_to_first_band_entry` is counted from the trough, not from step 0; add a check that the trough step is identical across seeds in a cell and label the axis "hours from run start"), cells where fewer than half the seeds ever re-enter (`steps_to_first_band_entry_n < n/2`) hatched and labelled "never"; a dashed contour at the latest start that can still hold `for_steps` by `max_steps` (`(max_steps − for_steps) × interval / 3600`, here 37 h) so the clock boundary is visible; heading states the criterion; reads only `mc.parquet` + manifest; synthetic-parquet test
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

- [x] Time-to-parity chart (AC: 1)
  - [x] `plot_time_to_parity`; test; run on `threshold-surface-ref-mc`; look and describe
  - [x] Commit separately: `story 2.9: time-to-parity chart`
- [x] Figure script and manifest (AC: 2)
  - [x] `sweep_spec_hash`; `make_figures.py`; overlay y-limit fix; `--quick`
- [x] Make targets, guard, CI (AC: 3, 4, 7)
- [x] Regenerate, commit, document (AC: 5, 6)
- [x] Close out (AC: 7)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.9: committed figures and make figures`, push to `main`

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

`steps_to_first_band_entry` under the oracle criterion counts steps **from the trough**
(`step_of_max_depeg`) to the first step the AMM is within 31 bps of the published oracle
price (summary.py). Time-to-parity for the chart is measured from run start, so add the
trough step (amended 2026-10-05, Rulings 1). "Never" = no re-entry by `max_steps`. The dashed
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

## Blockers

**AC 1 measures time-to-parity from the trough; its 37 h contour and the Dev Notes measure
it from step 0.**

- AC 1 plots `steps_to_first_band_entry_p50 × interval / 3600` and draws the clock
  boundary at `(max_steps − for_steps) × interval / 3600` = 37 h. The Dev Notes describe
  the metric as "the first step the AMM is within 31 bps of the published oracle price"
  and the 37 h line as the latest re-entry from which `peg_recovered` can still finish.
- The code disagrees with the Dev Notes: `src/depeg_sim/analysis/summary.py:9` defines
  `steps_to_first_band_entry` as steps **from `step_of_max_depeg`** to the first later
  in-band step (`summary.py:118`: `first_entry = int(after.iloc[0]) - step_of_max`).
  The 37 h deadline is in absolute steps (11,100 = 18,000 − 6,900). So the AC's quantity
  and the AC's contour have different origins. FINDINGS' F-11 refinement already adds the
  trough step: its "step 12,560–16,943" at D\* is `step_of_max_depeg_p50` (82–85) +
  `steps_to_first_band_entry_p50` (12,475–16,861).
- Size, on `output/threshold-surface-ref-mc` (real output): `step_of_max_depeg` is 50–85
  steps (0.17–0.28 h) with zero seed spread (`p05 == p95` in all 40 cells). No cell's
  from-trough median lies within 85 steps of 11,100 (nearest 9,100.5 below, 12,475 above),
  so **no cell changes clock/not-clock either way on this sweep**. The choice matters for
  what the axis is labelled and for any future sweep with a later trough.

**Options** (I have not chosen):

- **(a) Absolute time** (recommended): plot
  `(step_of_max_depeg_p50 + steps_to_first_band_entry_p50) × interval / 3600`, "hours from
  run start to first re-entry", contour at 37 h. Consistent with the Dev Notes, the
  contour and the F-11 refinement's numbers. The sum of medians equals the median of the
  sum only when the trough step has no seed spread; the function would check
  `step_of_max_depeg_p05 == step_of_max_depeg_p95` per cell and raise (or footnote) if
  not. Reads only `mc.parquet` + manifest, as AC 1 requires.
- **(b) AC 1 literally:** plot from-trough hours, label the axis "hours after the trough",
  draw the contour at 37 h, and state in the caption that the line is approximate by the
  trough time (≤ 0.28 h here).
- **(c) From-trough hours with a per-cell deadline:** contour at
  `37 h − trough time`. Exact, but a contour of a varying level is harder to read.

**Two smaller points; I will do as stated unless the ruling says otherwise:**

1. AC 2's `--quick` writes a `quick-ok` marker into `docs/figures/`, while the context's
   constraint says `docs/figures/` holds PNGs, `manifest.json` and `README.md` only. I
   will gitignore `docs/figures/quick-ok`, so the committed directory meets the
   constraint.
2. "Keep every figure's footer hash equal to the manifest's source hash": the sweep
   charts' footers print `base_hash` (the base scenario's `content_hash()`), but the
   manifest's sweep source hash is `sweep_spec_hash(spec)`, a different number, and
   the sweep's own `manifest.json` does not record the spec bytes. I will have
   `run_sweep` write `spec_hash` (= `sweep_spec_hash`) into the sweep manifest, have
   `_sweep_footer` print `sweep=<name> spec_hash=<12> base_hash=<12>`, and have
   `make_figures.py` refuse to plot a sweep directory whose `spec_hash` differs from the
   spec on disk. That changes the footer of all four sweep figures. Scenario footers
   already print `content_hash()[:12]`.

## Rulings

**2026-10-05 (dev manager), on the Blockers above.**

1. **Option (a).** Measure from run start: `(step_of_max_depeg + steps_to_first_band_entry)`
   per run, median across seeds, with a check that the trough step is the same for every
   seed in a cell (fail loudly if not). Axis "hours from run start"; the 37 h deadline is
   then on the same origin. AC 1 and Dev Notes amended. The mixed origin was my drafting
   error; the F-11 refinement's numbers already used the correct sum, so no finding
   changes. On this sweep no cell switches category (trough at step 50–85); say so in the
   ADR-free Completion Notes.
2. **`quick-ok` marker → gitignored**, accepted.
3. **Sweep hash in `run_sweep` manifest and in the footer next to the base hash;
   `make_figures.py` refuses a sweep output whose hash doesn't match its spec** — accepted.
   That is the right place for it and it makes the footer and the manifest agree. All
   four sweep figures change footer; note it in Completion Notes.

Resume at Task 1.

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-9-committed-figures.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

Full regeneration (`make figures` on the committed code, commit `c7185dc`; 12 workers):

```
sweep: threshold-surface-ref-mc cells=640 workers=12
wrote: output/threshold-surface-ref-mc/mc.parquet
sweep: threshold-surface-mc cells=640 workers=12
wrote: output/threshold-surface-mc/mc.parquet
sweep: budget-x-depth-mc cells=200 workers=12
wrote: output/budget-x-depth-mc/mc.parquet
sweep: oracle-lag-mc cells=640 workers=12
wrote: output/oracle-lag-mc/mc.parquet
wrote: 10 figures and docs/figures/manifest.json (commit c7185dc1f0be)
make figures: wall time 443 s (12 workers)
```

(An earlier full run on `06682a1` took 435 s; it was redone after the footer fix below so
that the manifest's commit is the code that drew the figures.)

`make figures-quick` (12 workers, before the full run):

```
quick sweep: budget-x-depth-mc (13 s)
quick sweep: oracle-lag-mc (7 s)
quick sweep: threshold-surface-mc (18 s)
quick sweep: threshold-surface-ref-mc (18 s)
quick: ok, 10 figures drawn; wrote docs/figures/quick-ok only
make figures-quick: wall time 63 s (12 workers)
```

Guard on a scratch branch (`scratch/guard-proof`, one commit changing
`scenarios/calibrated-baseline.yaml` `tolerance: 0.0031` → `0.0035`; branch deleted after):

```
$ make figures-check
python scripts/check_figures.py
figures-check: budget_depth: STALE, sweeps/budget-x-depth-mc.yaml or its base scenario changed (manifest b3359c3fbb14, now 8adc04dbca22); regenerate with `make figures`
figures-check: peg_trajectory_calibrated: STALE, scenarios/calibrated-baseline.yaml changed (manifest 44ac03c60e5f, now 644723327c6b); regenerate with `make figures`
figures-check: threshold_surface: STALE, sweeps/threshold-surface-ref-mc.yaml or its base scenario changed (manifest 8ade9cb3fee8, now 4dce1e792071); regenerate with `make figures`
figures-check: threshold_surface_par: STALE, sweeps/threshold-surface-mc.yaml or its base scenario changed (manifest 74cb63b6a965, now 622b9f16a4d9); regenerate with `make figures`
figures-check: time_to_parity: STALE, sweeps/threshold-surface-ref-mc.yaml or its base scenario changed (manifest 8ade9cb3fee8, now 4dce1e792071); regenerate with `make figures`
figures-check: FAIL, 5 problem(s) in 10 figures
make: *** [Makefile:28: figures-check] Error 1
exit=2
$ git checkout main && git branch -D scratch/guard-proof && make figures-check
figures-check: ok, 10 figures match their sources
```

The five stale figures are exactly those built on `calibrated-baseline`; the four
untouched (`soros-baseline`, both 1992, `usdc-2023`, `oracle-lag-mc` on `calibrated-stress`)
pass. (make's exit 2 wraps the script's exit 1.)

Close-out on `main` with the figures in the tree:

```
$ pytest -o addopts="" -q
552 passed in 8.61s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
87 files already formatted
exit=0
$ make figures-check
figures-check: ok, 10 figures match their sources
exit=0
```

537 tests passed at `829156d` (story start); +15 here (5 charts, 3 sweep, 7 figures).

CI, GitHub run 37317017478 on this commit's tree (pushed to the scratch branch
`story/2-9-ci` before `main`, since deleted):

```
test: success (2026-10-05T13:28:09Z → 2026-10-05T13:29:04Z)
  All checks passed!
  87 files already formatted
  552 passed in 23.90s
  figures-check: ok, 10 figures match their sources
figures-quick: success (2026-10-05T13:28:10Z → 2026-10-05T13:34:32Z)
  quick sweep: budget-x-depth-mc (74 s)
  quick sweep: oracle-lag-mc (44 s)
  quick sweep: threshold-surface-mc (106 s)
  quick sweep: threshold-surface-ref-mc (111 s)
  quick: ok, 10 figures drawn; wrote docs/figures/quick-ok only
  make figures-quick: wall time 350 s (4 workers)
```

### Completion Notes List

**Time-to-parity chart (AC 1).** `plot_time_to_parity` plots
`(step_of_max_depeg_p50 + steps_to_first_band_entry_p50) × 12 / 3600` per cell, via
`time_to_parity_hours`, which raises if any cell's trough step varies across seeds
(`p05 != p95` or `std > 0`). On `threshold-surface-ref-mc` the trough step is identical
across seeds in all 40 cells (50–85 steps, 0.17–0.28 h), and every cell has
`steps_to_first_band_entry_n` of 0 or 16, so the median over re-entering seeds that
`mc.parquet` stores is also the all-seed median. **No cell switches category against the
from-trough reading** (Rulings 1). The 37 h boundary is drawn along cell edges, not as an
interpolated contour (a smooth contour cut through cells and read worse); "never" counts
as beyond it.

What it shows, row by row (columns are attacker capital 0.3×–1.5× nominal resources):

- **0.25× D\***: 0.4 h everywhere up to 1×, then 6.8 h and 12.2 h. All price-safe, no clock.
- **0.5× D\***: 0.4 h up to 0.5×, then 8.6, 20.9, 25.5, 28.1, 30.5 h. Slower with capital
  but all inside 37 h; no clock, no price.
- **1× D\***: 0.3–30.1 h up to 0.6×; at ≥ 0.8× the four cells are **clock** (41.9, 48.2,
  52.2, 56.5 h): back in the band, too late to hold it.
- **2× D\***: 0.3, 1.9, 23.9 h up to 0.5×; 0.6× is **clock** (42.6 h); ≥ 0.8× are
  **price** ("never", all 16 seeds).
- **4× D\***: 0.2, 0.2, 3.5, 26.2 h up to 0.6×; ≥ 0.8× are **price** ("never").

So the boundary is clock at 1× D\* and one cell at 2×; price at 2× and 4× D\* above 0.6×,
as the F-11 refinement says.

**Ten PNGs, nine figure bullets.** AC 2's third bullet names two files (1992 with and
without defense), so `docs/figures/` has ten PNGs; "all nine figures" in the prompt counts
bullets.

**Manifest format.** `docs/figures/manifest.json` is `{figure: {file, source, source_hash,
function, commit}}` as in the context interface, keyed by file stem. `commit` is HEAD at
draw time (`c7185dc`, the code that drew them), with a `-dirty` suffix if `src`,
`scenarios`, `sweeps`, `scripts`, `data` or `pyproject.toml` differ from HEAD; it is not
the commit that adds the PNGs, which cannot know its own hash. `f243c0d` after it changes
only the guard's message wording.

**Sweep hash (Rulings 3).** `run_sweep(..., spec_path=)` records
`spec_hash = sweep_spec_hash(spec_path)` in the sweep manifest (`null` when a sweep is
built in code without a file, e.g. `scripts/probe_boundary.py`); the CLI passes it.
`make_figures.py` refuses a sweep directory whose `spec_hash` is missing or differs,
before writing anything. The guard's source hash and every footer now agree.

**Figures whose look changed.**

- All four sweep figures: footer now `sweep=<name> spec_hash=<12> base_hash=<12>`, and a
  2.5% bottom strip is reserved so the longer footer clears the x label (it overlapped
  on `oracle_sensitivity` and on the 10-wide time-to-parity panel). Content unchanged:
  the regenerated sweeps reproduce the FINDINGS numbers (F-10 trough range −1,253.2 …
  −1,242.5 bps; budget log–log slope 0.47; threshold-surface cells as in the F-11
  refinement).
- `validation_overlay_usdc_2023.png`: y-axis bottom lowered from the autoscaled ≈ −1,460 to −1,587
  bps so the observed-trough label (−1,373 bps at 31.0 h) is inside the axes
  (2.6 review ruling 4). `_include_texts` lowers the limit until every annotation box
  fits; tested.
- The four peg trajectories: unchanged code; first time committed.

**README section text (AC 6)**, as committed:

> **Validation: USDC, March 2023.** Observed USDC/USD hourly closes (blue) and the
> simulated AMM price (black), in bps from par. With one par-expecting buyer fitted to the
> replay, the simulated trough is −1,138 bps against −1,373 bps observed, and from 35 h to
> 49 h the two paths lie on each other. Without that buyer the model's trough is four times
> too deep: the depth of a depeg is set by the attacker against everyone who believes the
> promise. See F-08 and its confirmation.
>
> **Price or clock.** Median hours from run start until the pool is back within ±31 bps of
> the oracle price, over pool depth (rows, × the fitted depth D\*) and attacker capital
> (columns). Cells outside the dashed outline re-enter before 37 h, early enough that the
> pool can still hold the band for the 23 h the criterion asks by the 60 h horizon. At
> calibrated depth (1× D\*) large attacks are lost on the **clock**: the issuer wins the
> price back, but after 41.9–56.5 h, too late. At 2× and 4× D\* they are lost on the
> **price** (hatched, "never"): no seed gets back within the band. Pools at or below half
> of D\* re-enter within 31 h at every attack tested, and at least 12 of 16 seeds recover.
> See F-11 and its refinement.

The README's Layout block also gains `sweeps/`, `scripts/` and `docs/figures/`, and the
"every chart is reproduced by `run.py`" sentence now points at `make figures`.

**Other judgment calls (no ADR; none constrains later stories beyond what Rulings 3 fixed):**

- `make lint` runs `ruff check .` and `ruff format --check .`; CI's main job runs
  `make lint test figures-check` (so CI now also enforces formatting; the tree was clean).
- `make figures` uses `nproc` workers (`WORKERS=` overrides).
- `soros-1992-no-defense` supports no finding of its own; its README row says it is the
  counterfactual to `soros-1992` (ADR-0019, ADR-0021) rather than inventing one.
- `make_figures.py` exits via `os._exit` after flushing, as `depeg_sim.sweep`/`mc` do
  (pyarrow teardown abort on CI runners).

### File List

**Created:**

- `Makefile`
- `scripts/make_figures.py`
- `scripts/check_figures.py`
- `tests/test_figures.py`
- `docs/figures/README.md`, `docs/figures/manifest.json`
- `docs/figures/{peg_trajectory_baseline, peg_trajectory_calibrated, peg_trajectory_1992, peg_trajectory_1992_no_defense, validation_overlay_usdc_2023, threshold_surface, time_to_parity, threshold_surface_par, budget_depth, oracle_sensitivity}.png`

**Modified:**

- `src/depeg_sim/analysis/charts.py` (`plot_time_to_parity`, `time_to_parity_hours`,
  `_include_texts` for the overlay, sweep footer with `spec_hash` and bottom strip)
- `src/depeg_sim/experiments/sweep.py` (`sweep_spec_hash`; `run_sweep(spec_path=)` writes
  `spec_hash`; CLI passes it)
- `tests/test_charts.py`, `tests/test_sweep.py`
- `.github/workflows/ci.yml` (main job `make lint test figures-check`; new
  `figures-quick` job)
- `.gitignore` (`docs/figures/quick-ok`)
- `README.md` ("Results so far", Layout, figures sentence)
- `docs/stories/2-9-committed-figures.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.8 review; time-to-parity chart added per review ruling 3
- 2026-10-04: Blocked by builder (Claude Code, Opus 5.5) before Task 1: time-to-parity origin (trough vs step 0) contradicts the 37 h contour; see Blockers
- 2026-10-05: Dev manager ruled on Blockers: time-to-parity from run start (option a); marker gitignored; sweep hash in manifest and footer. Status back to in-progress
- 2026-10-05: Implemented by builder (Claude Code, Opus 5.5): time-to-parity chart, make_figures/check_figures, Makefile, CI figures jobs, ten figures regenerated in full and committed. Status review
