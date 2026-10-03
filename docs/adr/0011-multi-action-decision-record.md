# ADR-0011: Multi-action steps record `{"actions": [...]}`

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.7 review

## Context
`DecisionTrace.record` wraps `action` in `dict()`; the defender's widen-and-buy step produces two actions. Kernel changes were out of 1.7's scope.

## Decision
A single-action step records the action dict; a multi-action step records `{"actions": [a, b, ...]}`. The widen step's rule is `defend_spread_widen`; its `actions` list carries the buy. Consumers check for the `actions` key.

## Consequences
`interventions` (buy count) can exceed `defend_buy` record count by one per defense episode. Story 1.8 widens `record`'s type to `dict | list | None` as a one-line cleanup; this encoding stays.
