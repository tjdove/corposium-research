# ADR-0001: Engine language is Python

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Tim Dove, Claude · **Origin:** charter

## Context
Corposium's prior work (DeFi DEX) is TypeScript. The simulator's audience is crypto researchers and quants, who read, trust and fork Python. The research toolchain (numpy, pandas, parquet, matplotlib, pytest) is strongest in Python.

## Decision
The simulation engine, experiments and analysis are Python 3.12+. The results page and any future interactive version stay TypeScript.

## Consequences
Tim reads Python rather than writing it; Claude Code writes it. Credibility signal to the target audience. Rust only if a measured bottleneck justifies it.

## Alternatives considered
TypeScript throughout: faster for Tim to read, weaker numeric tooling, reads as a web dev side project to the audience.
