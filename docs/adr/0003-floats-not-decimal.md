# ADR-0003: Token amounts are floats in token units

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.4

## Context
On-chain math is integer wei. Research-grade for this project means reproducible and explainable, not wei-exact.

## Decision
All amounts, reserves and prices are Python floats in whole-token units. Determinism is guaranteed by seeding, not by integer arithmetic. Assertions use `math.isclose` with explicit tolerances.

## Consequences
Simpler code and tests. Last-digit differences vs on-chain execution are expected and acceptable. The Epic 3 Anvil replay is where integer exactness is checked against a real pool.

## Alternatives considered
`Decimal`: slower, noisier, no research benefit. Integer wei: correct but hostile to readers.
