# ADR-0008: Subsystem methods that emit take `ctx` first

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.6 review

## Context
`set_spread_bps` must emit `spread_changed`, which needs the event sink and the current step.

## Decision
Any subsystem method that emits an event has `ctx` as its first positional argument: `execute(ctx, action)`, `process(ctx)`, `set_spread_bps(ctx, bps, source=...)`. Callers (agents) always have `ctx`.

## Consequences
No hidden global state; every emission is traceable to a step.
