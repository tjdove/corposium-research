# ADR-0006: `steps.max_steps` is the mandatory safety cap

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.3 review

## Context
With `termination.max_steps: false` and no subsystem providing a view, a run never ends.

## Decision
`termination.max_steps` must be `true`; the config validator rejects `false` with a message naming the safety cap. The field remains for readability. No hidden cap inside the engine.

## Consequences
Every run terminates. The config boundary, not the engine, enforces it.

## Alternatives considered
Hard-coded engine cap: hides a policy decision in code and surprises users.
