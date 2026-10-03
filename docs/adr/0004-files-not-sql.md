# ADR-0004: Persistence is files + manifest, not SQL

**Status:** Accepted · **Date:** 2026-10-02 · **Deciders:** Tim Dove, Claude · **Origin:** charter phase review

## Context
The original spec proposed SQLite/SQLAlchemy. The artifact is an open repo an outside researcher clones and runs.

## Decision
Each run writes `output/<run_id>/` with `timeseries.parquet`, `summary.json`, `events.jsonl`, `decisions.jsonl` (if traced), `checkpoints/`, and `manifest.json` (scenario hash, seed, phase order version, package version, timestamp). Sweeps aggregate to parquet. No database.

## Consequences
`git clone && python run.py scenario.yaml` reproduces every chart with no setup. Diffable, portable, inspectable with pandas.

## Alternatives considered
SQLite: adds schema maintenance and a reader dependency for no reproducibility gain at this scale. Revisit only if multi-user or remote.
