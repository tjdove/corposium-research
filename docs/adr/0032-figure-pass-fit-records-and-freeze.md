# ADR-0032: Figure pass, fit records under the guard, and how the freeze commit is cited

**Status:** Accepted (review 2026-10-09, unamended)
**Date:** 2026-10-08
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 4.1

## Context

Story 4.1 freezes the code behind the note's figures. The story left four choices open:
what "mean with p05–p95" of a price paid per stable means, where fit records go and what
the guard does with them, which figures make up the note's set, and which commit is "the
freeze commit" when that commit's hash also has to be written into a file in the repo.

## Decision

1. **Price paid per stable, per run.** `plot_policy_comparison` panel (b) computes
   `defender_spent / defender_bought_stable` for each run from `sweep.parquet`, then takes
   the mean and p05–p95 over seeds. `mc.parquet` holds only per-cell aggregates, and
   adding a ratio column to `experiments/mc.py` would be a change outside
   `analysis/charts.py`. A run that bought nothing has no price (NaN). A policy with no
   price in any cell (no-defense, spread-only) is left out of the panel and named in the
   legend title. On the committed sweep the per-run ratio is the same in every seed of a
   cell, so the mean of ratios equals the ratio of means that `pace_trigger.png` and the
   Story 3.2 review quote (0.283 / 0.323 / 0.358 at 1.0×), and the band has no width.

2. **Fit records** (`scripts/fit_record.py`). The schema is the one in the story context:
   `{script, script_sha256, inputs: {scenario, scenario_hash, data, data_sha256, args},
   result}`. `args` records only arguments that change the result (target, holder
   parameters, grid, refine points), not `--workers` or `--output`. `result` includes
   every point run, not just the pick. There is no timestamp, so a re-run on the same
   inputs writes the same bytes (tested for `fit_depth` and `fit_reversion`). The depth fit
   has `data: null` because its target is a published number, not a file. The holder fits
   record the replay series both inside the scenario hash and as their own `data` entry.
   `make figures` re-writes all four after drawing the figures. `check_figures.py --fits`
   (default `docs/calibration/fits`) fails on an input mismatch or a missing input, and
   warns on a changed script. A second `ok` line reports the fits.

3. **The note's set is every committed figure except the four record-only ones.** AC 2
   names exactly four record-only figures (`threshold_surface_par`, `threshold_surface`,
   `time_to_parity`, `holder_exit`), so the README's note set has fifteen. The outline's
   figure list in `docs/NOTE.md` named fewer, plus a "3.4 figures pending" row. To match
   one-to-one (AC 4), the builder edited **only the figure-list table** in NOTE.md. It
   added `validation_overlay_usdc_2023_tranches` (already Figure 1b in §3),
   `threshold_surface_ou`, `budget_attack`, `pace_trigger`, `pace_ratio`, `lp_flight`,
   `peg_trajectory_calibrated` and `peg_trajectory_baseline`, and moved `threshold_surface`
   to the record. Rows the outline text does not use are marked †. **The dev manager may
   move any of them to the record**, which means moving one row in each file;
   `tests/test_note_figures.py` keeps the two in step.

4. **The freeze commit is the figures commit; the hash is recorded in a later
   documentation-only commit.** A commit cannot contain its own hash. The freeze commit
   holds the code, the regenerated figures, `manifest.json` and the fit records. It is
   tagged `v0.9-freeze`. The next commit writes that hash into the REPRODUCIBILITY
   checklist and the story's Dev Agent Record and changes nothing under `src/`,
   `scripts/`, `scenarios/` or `sweeps/`. `code_hash` and every source hash are therefore
   the same at both commits, and `make figures-check` stays clean at both.

## Consequences

- Story 4.2's `scripts/check_note.py` can resolve a figure through `manifest.json` and a
  fitted number through `docs/calibration/fits/*.json`.
- Any change to a fit script after the freeze shows up as a guard warning until `make
  figures` re-writes the records.
- The README's "Price or clock" result still shows `time_to_parity.png`, which is now
  record only. Its numbers are correct for that figure. Swapping it for
  `time_to_parity_ou.png` is an editorial call left to the dev manager (Story 4.3 builds
  the site from the note's set).

## Alternatives considered

- **Add a `defender_price_paid` metric to `mc.py`:** cleaner, but it would mean editing
  `src/` outside `charts.py` at the freeze. Rejected.
- **Move more figures to the record to match the outline's shorter list:** contradicts
  AC 2's explicit list of four. Left to the dev manager instead.
- **Tag the documentation commit:** the tag would then name a commit whose checklist cites
  a different hash. Rejected; the tag and the recorded hash name the same commit.
