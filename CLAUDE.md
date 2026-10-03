# CLAUDE.md — working rules for coding agents

This repo is Corposium Research's stablecoin depeg simulator. Read `docs/CHARTER.md`
once, then `docs/epics.md`. Work is done one story at a time from `docs/stories/`.

## Roles

- **Tim Dove** — owner. Final decisions.
- **Claude (chat, dev manager)** — writes epics, stories and context; assigns stories;
  reviews and closes them. Lives outside this repo.
- **You (Claude Code on Seoul)** — implement the assigned story. Nothing else.
- **Muse** — business ops. Never touches this repo.

## Story workflow

1. Open the story file you were assigned (`docs/stories/N-M-slug.md`). Read it fully,
   including Dev Notes and the "Learnings from previous story" section.
2. Set `Status: in-progress` in the story file.
3. Work the Tasks/Subtasks in order, ticking boxes as you go. Each task maps to ACs.
4. Write tests alongside code, not after.
5. When every AC is met: fill in the Dev Agent Record (model used, debug log, completion
   notes, file list), append to Change Log, set `Status: review`.
6. Stop. Do not start the next story. The dev manager reviews and marks `done`.

## Hard rules

- **Determinism.** Same seed + same scenario YAML must produce byte-identical parquet
  and summary JSON. Every random draw goes through the run context's `numpy.random.Generator`.
  Never call `random`, `np.random.*` module functions, or `time`-based seeds.
- **Phase order is versioned.** The nine step phases live in one place
  (`kernel/scheduler.py`) and never change silently. Changing them bumps `PHASE_ORDER_VERSION`.
- **No domain logic in the kernel.** Engine/scheduler orchestrate; protocol and agent
  modules own all trading and mechanism logic.
- **Scope.** The Out list in `docs/CHARTER.md` §4 is binding. No lending, liquidations,
  SQL persistence, named composite metrics, web UI. If a story seems to need one of these,
  stop and say so in the story file instead of building it.
- **Python 3.12+, plain and inspectable.** No frameworks, no async, no message queues.
  pydantic for config, numpy/pandas for numbers, pyarrow for output, matplotlib for charts.
- **Tests must pass** (`pytest`) and **lint must pass** (`ruff check .`) before `Status: review`.
- **Never claim a number you did not run.** Test counts, coverage, run outputs: paste the
  actual command output into the Debug Log.
- **No secrets** in the repo. No RPC keys, no API keys. `.env` is gitignored.

## Commands

```bash
pip install -e ".[dev]"
pytest
pytest --cov=depeg_sim --cov-report=term-missing
ruff check . && ruff format .
python run.py scenarios/soros-baseline.yaml
```

## Conventions

- `src/depeg_sim/` package layout is fixed (see README).
- Tests in `tests/`, named `test_<module>.py`.
- Scenario YAML in `scenarios/`, one file per scenario, `version:` field required.
- Output goes to `output/<run_id>/` and is gitignored.
- Commit messages: `story 1.3: <what changed>`.

## When stuck

Write what is blocking you in the story file under a `## Blockers` heading, set
`Status: blocked`, and stop. Do not guess at scope or invent requirements.

## Decisions

`docs/adr/` holds Architecture Decision Records. Read the index before starting a story;
several ADRs constrain how modules are built (floats, construction-vs-execution, ctx-first,
PegView ownership). When you make a judgment call that future stories will depend on —
an interface the spec left ambiguous, a semantic the ACs did not pin down, an observed
model behaviour that changes what should be built next — write it up in Completion Notes
**and** add a `Proposed` ADR file using the template in `docs/adr/README.md` (next free
number, do not edit the index). The dev manager accepts, amends or rejects it in review.
