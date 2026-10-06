# Story 3.5: Test Hardening, Repo Polish, and the Pace-Ratio Sweep

Status: ready-for-dev

## Story

As a **reader**,
I want to clone the repo and reproduce every figure and number without asking anyone,
so that the note's claims are auditable by a stranger — and the last uncommitted result (the pace ratio) is in the record.

## Acceptance Criteria

1. **Pace-ratio sweep** (3.4 review ruling 3): `sweeps/pace-ratio-mc.yaml` — base `calibrated-baseline.yaml`, oracle criterion, attacker ratio 1.0, trigger 1%; axes `agents[type=defender].spend_pace ∈ {0.0025, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1}` × `agents[type=attacker].pace ∈ {0.02, 0.1}`; 8 seeds; `plot_pace_ratio(sweep_dir)`: one panel, median time-to-parity (hours from run start) against defender pace / attacker pace on a log x-axis, one line per attacker pace, "never" at the top with open markers, the 37 h deadline dashed; registered as a figure; Completion Notes state the ratio at which each line crosses 37 h
2. **Summary fields:** `summarize` gains `arbitrageur_redeemed` (3.2 review ruling 5); `scripts/policy_table.py` reads it from the summary instead of `events.jsonl`; run-vs-rerun byte tests unchanged in intent (fixtures updated once, with the diff shown)
3. **Guard:** `docs/figures/manifest.json` gains `code_hash` (sha256 over the sorted contents of `src/depeg_sim/**/*.py`); `scripts/check_figures.py` **warns** (exit 0, message naming the hash) on a code-hash mismatch and **fails** on a source mismatch; `make figures` writes the current code hash; `docs/REPRODUCIBILITY.md` has a "before the freeze" checklist that includes `make figures` and a clean guard
4. **Makefile:** `PYTHON` defaults to `.venv/bin/python` when it exists, else `python`; documented in the README make section (2.9 review ruling 6)
5. **Coverage ≥ 85%** on `src/depeg_sim/protocol/` and `src/depeg_sim/agents/` (`pytest --cov`, report pasted); property-style tests (plain pytest parametrisation is fine, no new dependency): AMM `k` non-decreasing over random trade sequences from a seeded `Generator`, redemption accounting (requested = paid + queued + rejected) over random request sequences, both termination criteria at their edges (exactly `for_steps` in band; one step short; `reference: oracle` with no oracle registered)
6. **README** rewritten for a stranger: what this is in three sentences; quick start with expected output; "Results so far" kept; scenario reference table (every file in `scenarios/` and `scenarios/policies/`, one line each: name, what it is, `content_hash()` first 12); sweep reference table (every file in `sweeps/`, runs, wall time on Seoul); make targets; figure index pointing at `docs/figures/README.md`; links to FINDINGS, NOTE outline, BACKGROUND, ADR index, PROCESS, LITERATURE; license
7. **`CONTRIBUTING.md`**: the story process in one page (story file is the contract; builder/dev-manager roles; blocked means blocked), the determinism rule, how to add a scenario (header conventions, status lines, hash pin), how to add a sweep, how to add a figure (manifest, guard)
8. **`docs/REPRODUCIBILITY.md`**: Python version, install on a clean 3.12 venv with timing, every command that produces a figure with wall time on a named machine (Seoul, 12 workers) and on CI (4 workers), the hashes that must match, the `TMPDIR` note (sweeps write ~2 GB per 200 runs; use `output/`, set `TMPDIR` to a large disk for agent sessions), the "before the freeze" checklist
9. **Dependency pins** reviewed; `pyproject.toml` upper bounds where a major version would break (numpy, pandas, pyarrow, matplotlib, pydantic); CI unchanged
10. `make figures` (pace-ratio added); guard green with the new code hash; `pytest` and `ruff check .` pass; both CI jobs green; Proposed ADR only if a design decision was made (the guard semantics qualify)

## Tasks / Subtasks

- [ ] Pace-ratio sweep and chart (AC: 1)
  - [ ] Commit separately: `story 3.5: pace-ratio sweep`
- [ ] Summary field and policy table (AC: 2)
- [ ] Guard and Makefile (AC: 3, 4)
- [ ] Coverage and property tests (AC: 5)
- [ ] README, CONTRIBUTING, REPRODUCIBILITY, pins (AC: 6, 7, 8, 9)
- [ ] Close out (AC: 10)
  - [ ] `pytest --cov`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.5: hardening, polish, pace-ratio`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.4 (Status: done)**

- A committed grid that reads all-"never" is not the figure; AC 1 commits the probe that
  shows the gradient.
- Every "outcome" candidate turned out to be conservation; the README's results section
  quotes inputs (depth, budget, attack, pace) only.
- `make figures` after any agent or chart change; after this story the guard will at least
  warn when code changed.

[Source: docs/stories/3-4-budget-vs-attack.md#Senior-Developer-Review, F-11 and F-13 refinements]

### Why warn, not fail, on code hash

A code change that does not touch a figure's numbers (a docstring, a test) would otherwise
block CI until a 7-minute regeneration; a change that does touch them is caught at the
freeze by the checklist. The warning is loud and names the hash so a reviewer can't miss
it; the freeze checklist is the hard gate.

### What the README is for

A crypto researcher lands on it from the launch thread. In thirty seconds they should know
what the thing is, see one figure, and know the one command that regenerates everything.
Everything else is a link. No story numbers, no ADR numbers in the README body.

### Cost

Pace-ratio: 14 cells × 8 seeds = 112 runs, ≈ 1 min on 10 workers. Coverage run: the test
suite plus `--cov` ≈ 2 min. The rest is writing.

### References

- [Source: docs/epics.md#Story-3.5]
- [Source: docs/stories/2-9-committed-figures.md] — guard design
- [Source: docs/PROCESS.md] — the process CONTRIBUTING.md summarises
- [Source: docs/adr/0027-*.md] — the slow-attack probe table AC 1 commits

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-5-hardening-and-polish.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: pace-ratio sweep, coverage report, `make figures` time, guard with the code hash, CI)_

### Completion Notes List

_(include: 37 h crossing ratios; coverage numbers per package; README outline; anything in the repo a stranger still couldn't reproduce)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-06: Story drafted by dev manager after Story 3.4 review
