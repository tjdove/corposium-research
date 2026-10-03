# ADR-0012: Latency plans keep first-seen step and latest size

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.7 review

## Context
"A new observation replaces an unexecuted plan" would reset the latency clock every step for a persistent opportunity, so with latency ≥ 1 the arbitrageur would never act.

## Decision
A pending plan keeps the step at which the opportunity was first seen and updates its size to the latest observation. It executes when `first_seen + latency_steps <= step`. If the opportunity disappears before execution, the plan is dropped. Stable already queued for redemption is excluded from new redeem plans.

## Consequences
Latency means "reaction time," as intended. No double-redeem.
