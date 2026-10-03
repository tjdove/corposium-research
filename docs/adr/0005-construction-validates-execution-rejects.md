# ADR-0005: Construction validates and raises; execution rejects and emits

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.4 review

## Context
Protocol modules receive invalid parameters (zero reserves) and invalid actions (negative swap) through different paths with different consequences.

## Decision
Constructors validate invariants and raise `ValueError`. `execute()` and `on_phase()` never raise for domain conditions; they return `ExecutionResult(ok=False, detail=...)` and emit a `*_rejected` event with a reason string. `KernelError` is reserved for kernel misuse (unknown action target).

## Consequences
A broken object cannot exist; a bad action is data, visible in the event log, and agents can adapt. Tests assert on reason strings.

## Alternatives considered
Raising on bad actions: would crash a 10,000-run sweep on one edge case.
