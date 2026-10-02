# Story 1.1: Project Foundation Setup

Status: review

## Story

As a **developer**,
I want the Python project configured with packaging, testing and linting,
so that every later story builds on one verified toolchain.

## Acceptance Criteria

1. `pyproject.toml` defines package `depeg_sim` under `src/`, Python ≥3.12, dependencies pydantic, pyyaml, numpy, pandas, pyarrow, matplotlib; dev extras pytest, pytest-cov, ruff
2. `pip install -e ".[dev]"` succeeds in a clean venv
3. Package layout exists: `src/depeg_sim/{kernel,protocol,agents,environment,experiments,analysis}/__init__.py`
4. `src/depeg_sim/cli.py` exposes `main(argv)`; `python run.py scenarios/soros-baseline.yaml` exits 0 and prints the scenario path
5. `tests/test_smoke.py` passes; `pytest` exits 0
6. `ruff check .` exits 0
7. `.gitignore` excludes `.venv`, `output/*`, `.env`, caches; `output/.gitkeep` kept
8. GitHub Actions workflow `.github/workflows/ci.yml` runs `pytest` and `ruff check .` on push and PR, Python 3.12

## Tasks / Subtasks

- [x] Verify the scaffold the dev manager committed (AC: 1, 3, 7)
  - [x] Read `pyproject.toml`, confirm dependencies and dev extras match AC 1
  - [x] Confirm all six subpackages have `__init__.py`
  - [x] Confirm `.gitignore` contents match AC 7

- [x] Install and verify in a clean venv (AC: 2)
  - [x] `python -m venv .venv && source .venv/bin/activate`
  - [x] `pip install -e ".[dev]"`; paste the final lines of output into Debug Log
  - [x] `python -c "import depeg_sim; print(depeg_sim.__version__)"` prints `0.1.0`

- [x] Verify CLI stub (AC: 4)
  - [x] `python run.py scenarios/soros-baseline.yaml` exits 0, prints scenario path
  - [x] `python run.py scenarios/missing.yaml` exits 2 with an error on stderr
  - [x] `depeg scenarios/soros-baseline.yaml` (console script) behaves identically

- [x] Tests and lint (AC: 5, 6)
  - [x] `pytest` — paste summary line into Debug Log
  - [x] `ruff check .` — exits 0; fix anything it flags
  - [x] `ruff format --check .` — exits 0; run `ruff format .` if not

- [x] CI workflow (AC: 8)
  - [x] Create `.github/workflows/ci.yml`: trigger on push and pull_request, ubuntu-latest, Python 3.12, `pip install -e ".[dev]"`, `ruff check .`, `pytest`
  - [x] Validate YAML parses (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`)

- [x] Close out
  - [x] Fill Dev Agent Record below
  - [x] Set `Status: review`
  - [x] Commit: `story 1.1: project foundation verified, CI added`

## Dev Notes

### What already exists

The dev manager scaffolded the repo before this story. Most of ACs 1, 3, 4, 5, 7 should
already pass. This story is about **verifying** them in a clean environment on Seoul and
adding CI, not re-creating files. If something the scaffold claims does not work, fix it
and note what was wrong in the Debug Log.

### Architecture Alignment

**Package layout (fixed for the project):**
```
src/depeg_sim/
  __init__.py       __version__
  cli.py            main(argv) — Story 1.8 wires it to the engine
  kernel/           Story 1.2 config, Story 1.3 engine/clock/scheduler/context/checkpoint
  protocol/         Story 1.4 amm, 1.5 oracle, 1.6 redemption
  agents/           Story 1.7
  environment/      Story 1.5 price_process
  experiments/      Story 1.8 writer; Epic 2 sweep/mc
  analysis/         Story 1.8 metrics/summary/charts
```

**Toolchain decisions:**
- `src/` layout with hatchling so tests import the installed package, not the working tree by accident
- ruff for both lint and format (one tool, fast); rules `E, F, I, B, UP`, line length 100
- pytest with `-q` default; coverage via pytest-cov when a story asks for it
- No pre-commit hooks for now; CI is the gate

**Why no Playwright / vitest equivalents:** this is a batch simulator with no UI. All
verification is `pytest` + running scenarios.

### CI workflow reference

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
```

### Prerequisites

None — first story in Epic 1.

### References

- [Source: docs/CHARTER.md#4-Scope]
- [Source: docs/epics.md#Story-1.1]
- [Source: CLAUDE.md#Hard-rules]

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-1-project-foundation-setup.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code on Seoul.

### Debug Log References

Environment: Seoul, Arch Linux, system Python 3.14.7 (the only interpreter installed; satisfies
`requires-python = ">=3.12"`). CI runs on 3.12.

**Clean venv + install (AC 2)**

```
$ python -m venv .venv && source .venv/bin/activate && python --version
Python 3.14.7
$ pip install -e ".[dev]"
...
Successfully built depeg-sim
Installing collected packages: typing-extensions, six, ruff, pyyaml, pyparsing, pygments, pyarrow, pluggy, pillow, packaging, numpy, kiwisolver, iniconfig, fonttools, cycler, coverage, annotated-types, typing-inspection, python-dateutil, pytest, pydantic-core, contourpy, pytest-cov, pydantic, pandas, matplotlib, depeg-sim

Successfully installed annotated-types-0.8.0 contourpy-1.4.0 coverage-7.16.2 cycler-0.12.1 depeg-sim-0.1.0 fonttools-4.66.1 iniconfig-2.3.0 kiwisolver-1.5.1 matplotlib-3.11.2 numpy-2.5.3 packaging-26.3 pandas-3.0.6 pillow-12.3.0 pluggy-1.6.0 pyarrow-25.0.1 pydantic-2.13.5 pydantic-core-2.46.5 pygments-2.21.0 pyparsing-3.3.3 pytest-9.1.1 pytest-cov-7.1.0 python-dateutil-2.9.0.post0 pyyaml-6.0.3 ruff-0.16.10 six-1.17.0 typing-extensions-4.16.0 typing-inspection-0.4.4
exit=0
$ python -c "import depeg_sim; print(depeg_sim.__version__)"
0.1.0
```

**CLI stub (AC 4)**

```
$ python run.py scenarios/soros-baseline.yaml
depeg-sim: scenario=scenarios/soros-baseline.yaml output=output seed=None
kernel not implemented yet (see docs/epics.md, Story 1.3)
exit=0
$ python run.py scenarios/missing.yaml
error: scenario not found: scenarios/missing.yaml
exit=2
$ depeg scenarios/soros-baseline.yaml
depeg-sim: scenario=scenarios/soros-baseline.yaml output=output seed=None
kernel not implemented yet (see docs/epics.md, Story 1.3)
exit=0
$ depeg scenarios/missing.yaml
error: scenario not found: scenarios/missing.yaml
exit=2
$ python run.py scenarios/missing.yaml 2>/dev/null (stdout only)
exit=2
```

The last run prints nothing when stderr is discarded, which confirms the error goes to stderr.

**Tests and lint (AC 5, 6)**

```
$ pytest
...                                                                      [100%]
3 passed in 0.01s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
16 files already formatted
exit=0
```

**CI YAML (AC 8)**

```
$ python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
exit=0
$ python -c "import yaml; print(yaml.safe_load(open('.github/workflows/ci.yml')))"
{'name': 'ci', True: ['push', 'pull_request'], 'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': [{'uses': 'actions/checkout@v4'}, {'uses': 'actions/setup-python@v5', 'with': {'python-version': '3.12'}}, {'run': 'pip install -e ".[dev]"'}, {'run': 'ruff check .'}, {'run': 'pytest'}]}}}
```

### Completion Notes List

- **AC 1:** `pyproject.toml` matches. Package `depeg-sim` / `depeg_sim` under `src/` (hatchling,
  `packages = ["src/depeg_sim"]`), `requires-python = ">=3.12"`, runtime deps pydantic, pyyaml,
  numpy, pandas, pyarrow, matplotlib; dev extras pytest, pytest-cov, ruff. Minimum versions match the context XML.
- **AC 2:** Clean venv install succeeded (output above).
- **AC 3:** All six subpackages (`kernel`, `protocol`, `agents`, `environment`, `experiments`,
  `analysis`) have `__init__.py`, confirmed by `git ls-files`.
- **AC 4:** `main(argv: list[str] | None = None) -> int` exists. It returns 0 on the baseline
  scenario and prints the path, and returns 2 with a stderr message on a missing path. `run.py` and
  the `depeg` console script behave the same.
- **AC 5:** 3 smoke tests pass.
- **AC 6:** `ruff check .` passes with no changes. `ruff format --check .` also passes. Ruff
  skips `.venv`. The 16 formatted files are the 10 `.py` files plus 6 Markdown files, which ruff
  0.16 also formats.
- **AC 7:** `.gitignore` covers `.venv/` (and `venv/`), `output/*` with `!output/.gitkeep`,
  `.env` / `.env.*`, and `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.coverage`, `htmlcov`.
  `output/.gitkeep` is tracked.
- **AC 8:** `.github/workflows/ci.yml` was already in the scaffold and matches the Dev Notes
  reference line for line: push + pull_request, ubuntu-latest, Python 3.12, install, `ruff check .`,
  `pytest`. The task says "Create", but the file already met the AC, so I left it unchanged. The
  YAML parses. PyYAML (YAML 1.1) reads the `on:` key as boolean `True`, which is a known quirk.
  GitHub's parser treats it as `on`, so no change is needed.
- **Nothing was fixed.** The scaffold met every AC as committed. No files outside this story file changed.
- Local verification used Python 3.14.7 because it is the only interpreter on Seoul. The CI
  workflow covers 3.12.
- PR #1 (PR template) is left open and unmerged. The assignment said merging was optional.
- An untracked `0001-tjdove-urls.patch` is in the working tree. It is the same change as commit
  `aee8514`. I left it untracked and did not touch it.

### File List

**Created:**

- (none)

**Modified:**

- `docs/stories/1-1-project-foundation-setup.md` (status, task checkboxes, Dev Agent Record, Change Log)

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md; scaffold committed alongside
- 2026-10-02: Story implemented by Claude Code (Opus 5.5) on Seoul. All 8 ACs verified, scaffold needed no fixes, CI workflow already present and matched AC 8. Status set to review.
