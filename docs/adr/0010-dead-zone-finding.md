# ADR-0010: The baseline parks in a dead zone no agent rule covers

**Status:** Accepted (finding) · **Date:** 2026-10-02 · **Deciders:** Claude · **Origin:** story 1.7 AC 10

## Context
Baseline: 1M/1M pool, 30 bps fee; attacker 300k from step 50 at pace 0.1; defender 400k, −1% trigger, pace 0.2; arbitrageur 200k, 20 bps min profit, latency 1; `peg_recovered` tolerance 10 bps for 100 steps. Observed (builder and reviewer, independently): spot bottoms at 0.943 (step 50), last defender buy at step 77, then settles at 0.99817 (−18.3 bps) and stays there to step 5000. Only 91k of 500k reserves paid.

## Finding
−18 bps is inside the arb band (30 + 20 = 50 bps), above the defender trigger (−100 bps), and outside the recovery tolerance (10 bps). No actor has an incentive or a rule to close the last 18 bps. The run can only end by `max_steps`. Separately, before the attack the pool sits exactly at peg, so `start_step >= for_steps` ends the run by `peg_recovered` before the attacker acts.

## Decision
This is a property of the model, not a defect. It constrains Story 1.8 and Epic 2:
1. `peg_recovered.tolerance` must be ≥ the effective arbitrage band for "recovery" to be reachable, **or** the scenario must document that it is testing permanent partial depeg.
2. The baseline for the first chart is retuned so that at least one non-`max_steps` termination is reachable (1.8 records which lever it pulled).
3. "A peg can be permanently slightly broken with no actor incentivised to fix it" is a candidate headline observation for the research note.

## Consequences
The first public chart shows a real dynamic, not a flat line. Calibration (Epic 2) must choose tolerance relative to real fee + arb thresholds, not arbitrarily.
