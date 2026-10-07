# Contributing

This project is built one story at a time, and every number it publishes has to be
reproducible from the repo by someone who was not there. This page is the short version
of [`docs/PROCESS.md`](docs/PROCESS.md) and the working rules in [`CLAUDE.md`](CLAUDE.md).

## The story process

- **The story file is the contract.** Work arrives as `docs/stories/N-M-slug.md` (plus a
  `.context.xml`). Its numbered acceptance criteria are what gets built. Nothing else: no
  extra features, and nothing from the Out list in [`docs/CHARTER.md`](docs/CHARTER.md) §4
  (no lending, liquidations, SQL, composite metrics or web UI), even if it would be easy.
  If the story and any other instruction disagree, the story wins.
- **Roles.** The *builder* (Claude Code) implements one assigned story: sets
  `Status: in-progress`, works the tasks in order with tests alongside the code, pastes
  real command output into the Dev Agent Record, sets `Status: review`, pushes and stops.
  The *dev manager* writes the stories, reviews each one by reproducing it independently,
  rules on every judgment call, and sets `Status: done`. Tim Dove, the owner, decides.
- **Blocked means blocked.** If the story contradicts itself or the code, the builder
  writes the problem under `## Blockers`, sets `Status: blocked` and stops. It does not
  guess at scope or invent a requirement.
- **Decisions are written down.** A judgment call later work will depend on (an
  interface the spec left open, a semantic the ACs did not pin, an observed model
  behaviour) becomes a `Proposed` ADR in [`docs/adr/`](docs/adr/README.md), using the
  template there and the next free number. The builder never edits the ADR index; the
  dev manager accepts, amends or rejects. Accepted findings are narrated in
  [`docs/FINDINGS.md`](docs/FINDINGS.md).
- **Never claim a number you did not run.** Test counts, coverage, run outputs and
  timings in a story file are pasted command output.
- **Before `Status: review`:** `pytest`, `ruff check .` and `ruff format --check .` pass
  (`make test lint`). Commit messages are `story N.M: <what changed>`.

## The determinism rule

Same seed + same scenario YAML gives byte-identical `timeseries.parquet`, `summary.json`,
`events.jsonl` and `decisions.jsonl` (the run manifest differs only in `created_utc`).
So:

- every random draw goes through the run context's `numpy.random.Generator` (`ctx.rng`);
  never `random`, never a module-level `np.random.*` function, never a time-based seed;
- the nine step phases live in `src/depeg_sim/kernel/scheduler.py` and change only with
  a bump of `PHASE_ORDER_VERSION`;
- the kernel orchestrates and holds no trading or mechanism logic; that lives in
  `protocol/` and `agents/`;
- tests use seeded Generators too, so a failing case names its seed and reruns exactly.

A change that alters any committed output on purpose updates its pinned test once and
shows the before/after diff in the story's Debug Log.

## Adding a scenario

One file per scenario in `scenarios/` (variants of one scenario in a subdirectory, as
`scenarios/policies/`). Conventions:

- **Header.** A comment block: a title line saying what the scenario stands for and
  which story introduced it; then, for every value that is not a default, where it
  comes from. Calibrated values cite `docs/calibration/SOURCES.md` or
  `docs/BACKGROUND.md`; a variant says "identical to `<base>.yaml` except ..." and lists
  the differences.
- **Status lines.** Each sourced parameter gets one line, `path  value  status  source /
  reasoning`, with status from the vocabulary in `SOURCES.md`: `verified`, `secondary`
  or `assumption` (combined, e.g. `secondary + assumption`, when a sourced number is
  scaled by an assumed factor). See `scenarios/soros-1992.yaml`.
- **Body.** `version: 1` is required; `name` must be unique across the scenarios a sweep
  can run (it names the run directory).
- **Hash pin.** Add a test asserting `load_scenario(path).content_hash()[:12]` equals the
  current value, with a comment naming the story (see
  `tests/test_calibrated_scenarios.py`). Any later change to the file or to the schema
  then fails a test instead of silently moving a published number. A schema addition
  must leave every existing scenario's hash unchanged: a new field enters
  `content_hash()` only when it is set away from its default (see its docstring in
  `src/depeg_sim/kernel/config.py`).

Run it with `python run.py scenarios/<file>.yaml`.

## Adding a sweep

One file per sweep in `sweeps/`: `version: 1`, `name` (the output directory under
`output/`), `base` (a scenario file), `axes` (and `linked_axes` for parameters that move
together), optional `overrides` applied to every cell, `seeds` and `max_steps`. The header
comment says what question the sweep answers, the base, every axis value and override
with where it comes from, the metric, and the run count (grid points × seeds).

```bash
python -m depeg_sim.sweep sweeps/<file>.yaml --mc --workers 12
```

writes `output/<name>/sweep.parquet` (one row per run), `mc.parquet` (one row per grid
point: means, percentiles and outcome probabilities over seeds) and `manifest.json`
(with `spec_hash`, which changes if the spec file or its base scenario changes). Sweeps
are disk-heavy, about 2 GB per 200 runs; see `docs/REPRODUCIBILITY.md` for `TMPDIR`.

## Adding a figure

Every committed chart lives in `docs/figures/` and is regenerated from a named source:

1. Write `plot_<name>(sweep_dir) -> Path` (or a run-directory function for a scenario
   figure) in `src/depeg_sim/analysis/charts.py`. It reads only `mc.parquet` and the
   sweep manifest, follows the house conventions at the top of that module, and prints
   the sweep footer (`sweep=<name> spec_hash=<12> base_hash=<12>`). Test it on a small
   synthetic sweep directory in `tests/test_charts.py`.
2. Register it in `FIGURES` in `scripts/make_figures.py` (file name, source, function)
   and update the registry test in `tests/test_figures.py`. If it needs a new sweep, add
   the spec to `SWEEPS` in the `Makefile`.
3. Add a row and a caption to `docs/figures/README.md`.
4. Commit the code, then run `make figures`. It writes the PNGs and
   `docs/figures/manifest.json`, which records each figure's source hash and the
   package's `code_hash`. Commit those.

`make figures-check` (CI runs it on every push) **fails** if any figure's scenario or
sweep has changed since it was drawn, and **warns** without failing if the package code
has changed (`code_hash`), since a docstring edit does not move a number. The warning is
cleared, and the hard gate passed, by the freeze checklist in `docs/REPRODUCIBILITY.md`.
