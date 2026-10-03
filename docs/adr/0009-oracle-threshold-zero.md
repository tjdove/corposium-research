# ADR-0009: `deviation_threshold_pct: 0` means a zero-lag oracle

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.5 review

## Context
AC 9 and the Dev Notes disagreed; the builder followed the AC.

## Decision
With threshold 0 the `>=` rule publishes every step (reason `deviation`), including when the price is flat. This is the "perfect oracle" endpoint of the oracle-lag sweep.

## Consequences
Epic 2 sweeps include 0 as the no-lag control. Docstring states it.
