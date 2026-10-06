# ADR-0025: Defender buy flag and spread cap; the base file as a sweep axis; a defender that spends slower than the attack beats one that spends faster (finding candidate); no spread dead zone at throughput-bound redemption (finding candidate)

**Status:** Accepted (finding, amended in review 2026-10-05: F-13 stated as price paid, not pace; pace × trigger sweep → Story 3.4; chart panel (b) → average price paid in the Epic 4 figure pass)
**Date:** 2026-10-05
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.2

## Context

Story 3.2 compares five defender policies (calibrated; early-aggressive 0.5%/0.5;
late-conservative 2.0%/0.1; spread-only 1.0% + 200 bps, never buys; no-defense) under the
same attacks at calibrated scale: attacker capital 0.5, 0.7, 1.0 × (budget + reserves),
16 seeds, recovery measured against the oracle (ADR-0023). Two pieces of machinery were
missing: a defender that does not buy, and a way to sweep over *scenario files* rather
than config paths. The story's predictions were that early-aggressive is fastest and
spends most, late-conservative spends least and is slowest, spread-only never recovers
because of the F-07 dead zone, and calibrated is cheaper per hour saved than
early-aggressive.

## Decision

### 1. Two `DefenderConfig` fields, hash-neutral at their defaults

- `buy: bool = True`. With `False` the defender never buys; in defense its rule is
  `defend_spread_widen` on the widening step and `defend_idle` otherwise (never
  `defend_buy` or `defend_budget_exhausted`). `defend_spread_restore` still fires when
  deviation comes back inside the threshold: restoring is not buying. A budget is still
  required (`gt=0`), so field semantics stay the same across policies.
- `max_spread_bps: int | None = None` (0–9,999). `None` keeps `MAX_SPREAD_BPS`. The widen
  test changed from `target != base` to `target > base`, so a cap at or below the current
  spread means "no widen" instead of lowering it. With the default cap the two tests are
  equivalent (`base + adjust ≥ base`, cap ≥ any legal `base`).
- `content_hash()` drops `buy` when `True` and `max_spread_bps` when `None` (the 2.8
  pattern). Every existing scenario hash and every sweep spec hash is unchanged (test
  pins all seven scenarios).

`kernel/config.py` is the only kernel file touched, as the story's AC 1 requires; the
engine, scheduler and `PHASE_ORDER_VERSION` (1) are untouched.

### 2. `base_axis` on `SweepSpec` instead of five sub-sweeps

```yaml
base: scenarios/calibrated-baseline.yaml      # the reference base; must be one of bases
base_axis:
  name: policy                                # the column name
  bases: {calibrated: scenarios/calibrated-baseline.yaml, no-defense: ..., ...}
```

Chosen over five sub-sweeps plus a combining script because the Story 2.9 figure pipeline
assumes *one spec file = one sweep directory with `mc.parquet` + manifest*: the stale-figure
guard hashes a spec with `sweep_spec_hash`, `make figures` runs each spec with
`python -m depeg_sim.sweep --mc`, `--quick` rewrites a spec's seeds. A spec that is not a
`SweepSpec` would need a second code path in all three. With the base axis the policy
sweep is an ordinary spec and every one of those works unchanged; the "combined
`policies.parquet`" of AC 3 is the sweep's own `mc.parquet` (one row per policy × ratio,
a `policy` column, all mc columns), and no `run_policy_comparison.py` exists. Only one
design was built.

Semantics: the base axis expands outermost (before linked axes, axes, seeds); each cell
starts from its label's file, then `overrides`, axis values, `max_steps`, `seed`, `name`.
`base` must be one of the labelled files and stays the *reference*: the manifest's
`base_config` / `base_scenario_hash` describe it (charts need a defender budget to label
"× resources", which no-defense lacks). The manifest lists the base axis first in `axes`
(`{"name", "paths": [], "values": [labels], "bases": {...}}`, so `mc.axis_columns` groups
by it) and adds `base_hashes: {label: content_hash}`. `sweep_spec_hash` appends every
label's `content_hash()` when a base axis exists, so the figure guard goes stale if any
policy file changes. The ADR-0013 guard runs against every base.

Specs without `base_axis` expand identically: for all eight existing specs the
`(index, seed, axis_values, cell content_hash)` list, `sweep_spec_hash`, resolved base and
manifest `axes` are byte-for-byte what the 3.1 code produced (checked against a worktree
of the previous commit; Story 3.2 Debug Log).

### 3. The policy result (`sweeps/policy-comparison-mc.yaml`, 240 runs, 73 s on 12 workers)

At ratio 1.0 (means over 16 seeds; time to parity = median hours from run start to the
first step within ±31 bps of the oracle; "never" when fewer than half the seeds re-enter):

| policy | defender spent | holder bought | redemption paid | arb redeemed | time to parity | p(stays broken) |
|---|---:|---:|---:|---:|---:|---:|
| calibrated | 41.35M | 32.07M | 10.87M | 10.87M | 48.2 h | 1.00 [0.81, 1.00] |
| early-aggressive | 41.35M | 40.34M | 10.87M | 10.87M | 53.1 h | 1.00 [0.81, 1.00] |
| late-conservative | 41.35M | 24.07M | 10.12M | 9.29M | 29.9 h | 0.31 [0.14, 0.56] |
| spread-only | 0 | 146.57M | 10.65M | 10.65M | never (1/16) | 1.00 [0.81, 1.00] |
| no-defense | 0 | 146.56M | 10.87M | 10.87M | 59.1 h | 1.00 [0.81, 1.00] |

**Late-conservative dominates.** At every ratio it is the fastest policy (6.6 / 19.2 /
29.9 h against calibrated 18.3 / 37.1 / 48.2 h), the only buyer that recovers at all at
1.0, has the lowest `p_stays_broken` (0.00 / 0.13 / 0.31), and is the cheapest per hour
saved against no-defense (0.97M / 1.17M / 1.41M per hour, against calibrated 1.33M /
2.37M / 3.78M and early-aggressive 1.42M / 3.16M / 6.87M). It is not cheaper because
someone else pays: every buying policy spends the full 41.35M budget at every ratio, and
under late-conservative the holder absorbs *less* (24.1M stable against 32.1M), and
redemption pays out less (10.12M against 10.87M).

**Why.** All three buyers exhaust the same budget within the first ~45 steps of a
60-hour run (seed 1000, ratio 1.0: 99% spent at step 62 / 72 / 94 for early / calibrated /
late; the attacker has sold 90% of its capital by step 71). The policies differ only in
*when* within the dump the money goes in. A fast defender lifts the pool back toward
par each step while the attacker still has most of its capital, so the attacker sells
into a restored price (average price the defender paid per stable: 0.358 early, 0.323
calibrated, 0.283 late) and, once the budget is gone, the attacker's tail sets a new and
deeper trough (−8,698 bps at step 78 early; −8,151 at step 84 calibrated). A defender
whose budget outlasts the dump keeps buying the tail: the trough is the first dump
(−7,681 bps at step 50) and the same budget absorbs 146M stable instead of 115M. That
leaves less stable for redemption to drain at its fixed throughput, and the price gets
back sooner (F-06, F-11: recovery at calibrated scale is a speed question). It is the
F-03 mechanism inside the policy dimension: the defense is cheaper per unit the lower
the price it buys at, and spending slowly is how a defender buys low.

**Spread-only never recovers, but not because of a dead zone.** `p_stays_broken` is 1.0
at every ratio, as predicted. The mechanism is not F-07: in seed 1000 the price crosses
−2% … −1% in 140 steps under spread-only and 138 under no-defense. With redemption
throughput-bound, an ~11.4M request backlog queued while the price was far below par
keeps draining at capacity through the band where a fresh redemption would not pay. What
the spread does is tax the arbitrage loop by 2%: the arbitrageur gets 0.98 reference per
stable redeemed, buys ~2% less stable back from the pool, and the climb runs ~2% slower
(seed 1000 at 0.5: −2% reached at step 14,888 vs 14,591, 297 steps = 2.0%). Spread-only is
no-defense plus one hour; at 1.0 that hour pushes first re-entry (no-defense 59.1 h) past
the 60 h horizon in 15 of 16 seeds. No-defense itself is lost on the clock at every ratio
(49.4 / 54.5 / 59.1 h, all after the 37 h deadline).

### 4. Finding candidates

**F-13 candidate: when the budget is always spent, the defense is decided by pace, and a
defender that spends slower than the attacker sells beats one that spends faster.** At
calibrated scale against a front-loaded attack, a 2% trigger with 10% pace recovers
faster, more often and more cheaply per hour saved than the calibrated 1%/20% policy, and
an aggressive 0.5%/50% policy is the worst buyer, at every ratio tested. For the note:
"defend early and hard" is the intuitive policy and it is wrong when the attack is still
selling; the issuer's budget buys the most when it is still there after the attacker
has finished. The 1992 parallel is direct: the Bank of England spent its reserves in a
morning into an attack that had not finished.

**F-07 refinement candidate: the spread dead zone needs redemption that is not
throughput-bound.** At calibrated scale the redemption backlog carries the price through
the band the spread prices out; the spread lever costs ~2% of the climb's speed instead
of stranding the peg. F-07's stall (1992 analogue) is a property of unconstrained
redemption, where no backlog exists.

## Consequences

- Policy files are `scenarios/policies/*.yaml`; any future policy is one more file and one
  more `base_axis` label.
- `late-conservative` changes two parameters (trigger and pace). The mechanism points at
  pace (both triggers are crossed on the first dump step, which takes seed 1000 to
  −7,681 bps), but this sweep cannot separate them. A pace × trigger sweep against
  attacker pace (hypothesis: the operative quantity is defender pace relative to attacker
  pace) is the natural Epic 3 follow-up.
- The early/late labels describe the trigger; the result is about the spending rate.
  The note should name the policies by pace when it quotes F-13.
- Time to parity for `no-defense` is the benchmark for "hours saved"; it is finite at every
  ratio (the price comes back on redemption alone, after the deadline).
- `scripts/policy_table.py` reproduces the table (it reads each cell's `events.jsonl` for
  who redeemed, which the summary does not carry).

## Alternatives considered

- **Five sub-sweeps and `scripts/run_policy_comparison.py`** (the story's default).
  Rejected: needs a non-`SweepSpec` source type in the figure guard, `make figures` and
  `--quick`, and a second manifest format. The base axis is ~90 lines in `sweep.py` and
  leaves every other consumer unchanged.
- **A zero budget for spread-only.** Rejected in the story: fails validation and would
  still try to buy.
- **An `arbitrageur_redeemed` summary key.** Not added: it would change every summary
  JSON's bytes for one table; the script reads it from events.
