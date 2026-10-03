# ADR-0007: AMM owns `PegView`; deviation is negative under stable selling

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** stories 1.4, 1.5

## Context
Termination and the defender both need "how far off peg is the market." Several modules carry prices.

## Decision
`ConstantProductAMM.peg_deviation = spot_price / peg_price − 1.0`, with `spot_price` in reference per stable. Selling stable pushes it negative. The oracle publishes a lagged reference price and explicitly does not implement `PegView`. Agents compare AMM spot to the oracle price; termination compares AMM spot to peg.

## Consequences
One definition of deviation; one sign convention; tests enforce `isinstance(oracle, PegView) is False`.

## Alternatives considered
Oracle as PegView: would make "recovery" depend on a stale price.
