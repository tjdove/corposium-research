# Story 1.1: Project Foundation Setup

Status: ready-for-dev

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

- [ ] Verify the scaffold the dev manager committed (AC: 1, 3, 7)
  - [ ] Read `pyproject.toml`, confirm dependencies and dev extras match AC 1
  - [ ] Confirm all six subpackages have `__init__.py`
  - [ ] Confirm `.gitignore` contents match AC 7

- [ ] Install and verify in a clean venv (AC: 2)
  - [ ] `python -m venv .venv && source .venv/bin/activate`
  - [ ] `pip install -e ".[dev]"`; paste the final lines of output into Debug Log
  - [ ] `python -c "import depeg_sim; print(depeg_sim.__version__)"` prints `0.1.0`

- [ ] Verify CLI stub (AC: 4)
  - [ ] `python run.py scenarios/soros-baseline.yaml` exits 0, prints scenario path
  - [ ] `python run.py scenarios/missing.yaml` exits 2 with an error on stderr
  - [ ] `depeg scenarios/soros-baseline.yaml` (console script) behaves identically

- [ ] Tests and lint (AC: 5, 6)
  - [ ] `pytest` — paste summary line into Debug Log
  - [ ] `ruff check .` — exits 0; fix anything it flags
  - [ ] `ruff format --check .` — exits 0; run `ruff format .` if not

- [ ] CI workflow (AC: 8)
  - [ ] Create `.github/workflows/ci.yml`: trigger on push and pull_request, ubuntu-latest, Python 3.12, `pip install -e ".[dev]"`, `ruff check .`, `pytest`
  - [ ] Validate YAML parses (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`)

- [ ] Close out
  - [ ] Fill Dev Agent Record below
  - [ ] Set `Status: review`
  - [ ] Commit: `story 1.1: project foundation verified, CI added`

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

_(fill in)_

### Debug Log References

_(paste actual command output for install, pytest, ruff, CLI runs)_

### Completion Notes List

_(what was verified, what was fixed, anything surprising)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-02: Story drafted by dev manager from epics.md; scaffold committed alongside
