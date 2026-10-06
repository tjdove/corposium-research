# Story 3.2: Defender Policy Comparison

Status: ready-for-dev

## Story

As a **researcher**,
I want four defender policies compared under the same attacks at calibrated scale,
so that the note can say which defense survives, at what cost, and how fast (charter chart 5).

## Acceptance Criteria

1. `DefenderConfig` gains `buy: bool = True` (when `False` the defender never buys on the AMM; it may still widen the spread — the "spread-only" policy) and `max_spread_bps: int | None = None` (an explicit cap; default keeps `MAX_SPREAD_BPS`); every existing scenario `content_hash()` unchanged (test); `Defender.decide` honours `buy=False` (rule `defend_spread_widen` or `defend_idle`, never `defend_buy`)
2. Four policy scenario files in `scenarios/policies/`, each `calibrated-baseline.yaml` with only the defender block changed and the file header stating the policy in one line:
   - `early-aggressive.yaml`: `threshold_pct 0.5`, `spend_pace 0.5`
   - `late-conservative.yaml`: `threshold_pct 2.0`, `spend_pace 0.1`
   - `spread-only.yaml`: `buy false`, `spread_adjust_bps 200`, `threshold_pct 1.0`
   - `no-defense.yaml`: defender removed (the file keeps the holder and arbitrageur)
   plus the calibrated baseline itself as the fifth policy ("calibrated": 1.0%, pace 0.2, no spread)
3. `sweeps/policy-comparison-mc.yaml`: a `policy` axis is not expressible as a config path, so the sweep runs **five sub-sweeps** (one per base file) sharing `overrides: {termination.peg_recovered.reference: oracle}`, `axes: {agents[type=attacker].capital: [ratio 0.5, 0.7, 1.0] × 179,454,391}`, 16 seeds from 1000, `max_steps 18000`; a thin `scripts/run_policy_comparison.py` runs the five and writes `output/policy-comparison-mc/<policy>/` plus a combined `policies.parquet` (one row per policy × ratio with the mc columns and a `policy` column) and a manifest listing the five spec hashes. If `SweepSpec` can take a `base` axis cleanly instead, propose it in the ADR and do that; do not build both
4. `plot_policy_comparison(sweep_dir) -> Path` writes `policy_comparison.png`: three panels sharing the ratio x-axis — (a) median time-to-parity in hours from run start, one line per policy, "never" plotted at the top with a marker; (b) defender spend mean with p05–p95 band, one line per policy (no-defense at 0); (c) `p_stays_broken` with Wilson bars, one line per policy; the calibrated policy drawn heavier; reads only the parquet and manifest
5. For each policy at ratio 1.0 the Completion Notes give: defender spend, holder bought, redemption paid, arbitrageur redeemed, time-to-parity median, `p_stays_broken` — one table — and answer in one paragraph: which policy gets back fastest, which gets back cheapest per hour saved against no-defense, and whether spread-only ever recovers (F-07 dead zone)
6. The 1992 analogue is **not** re-run here (3.3 owns it)
7. A `Proposed` ADR: the two config fields, the sub-sweep design (or the `base` axis), the policy result, and a finding candidate if one policy dominates or if spread-only produces the dead zone at calibrated scale
8. `make figures` with the new figure added to `make_figures.py` and `docs/figures/README.md`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [ ] Config and defender (AC: 1)
  - [ ] `buy`, `max_spread_bps`; `decide`; tests; hash test
  - [ ] Commit separately: `story 3.2: defender buy flag and spread cap`
- [ ] Policy scenarios and sweep (AC: 2, 3)
- [ ] Chart (AC: 4)
- [ ] Results, ADR, figures, close out (AC: 5, 6, 7, 8)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 3.2: defender policy comparison`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.1 (Status: done)**

- The holder and the defender trade absorption one for one (3.1: holder −1.8M bought,
  defender +1.65M spent). Every policy row must report both, plus redemption paid and
  arbitrageur redeemed, or "cheaper" will mean "someone else paid".
- Define timing metrics over the stretch the agent controls; here time-to-parity from run
  start (as 2.9) is the comparable number.
- `make figures` after every agent change; the guard cannot yet see code changes.

[Source: docs/stories/3-1-holder-fill-price-limit.md#Senior-Developer-Review, F-12]

### Why a `buy` flag and not a zero budget

A zero budget fails `DefenderConfig` validation (`gt=0`) and would still try to buy. The
spread-only policy is a defender that chooses not to buy; it keeps a budget so the
field semantics stay the same across policies.

### Why five sub-sweeps

`SweepSpec` varies config paths within one base. A "policy" is a different base file.
The simplest honest design is five sweeps with identical axes and a combining script;
the chart reads one combined parquet. If a `base` axis is cleaner and keeps existing
specs expanding identically, propose it — but do not build both.

### Predictions (to be checked)

- Early-aggressive gets back fastest at every ratio and spends the most; at 1.0 it spends
  close to its whole budget.
- Late-conservative spends least among the buyers and is the slowest buyer; at 1.0 it
  may be "clock" (F-11).
- Spread-only never recovers at any ratio (the F-07 dead zone at calibrated scale: the
  spread deters redemption, nothing buys, the price sits below the band).
- No-defense: the holder alone; time-to-parity between late-conservative and spread-only.
- Per hour saved against no-defense, calibrated is cheaper than early-aggressive.

### Cost

5 policies × 3 ratios × 16 seeds = 240 runs × ≤ 18,000 steps: about a minute on 10
workers. Report real time.

### References

- [Source: docs/epics.md#Story-3.2]
- [Source: docs/FINDINGS.md] — F-07, F-11 refinement, F-12
- [Source: src/depeg_sim/agents/defender.py] — rules and spread lever
- [Source: docs/stories/2-9-committed-figures.md] — time-to-parity semantics

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-2-defender-policy-comparison.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output: sweep runs with wall time, combined table, `make figures`, guard, tests, lint)_

### Completion Notes List

_(include: the ratio-1.0 policy table; the three answers; chart description; predictions checked; ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-05: Story drafted by dev manager after Story 3.1 review
