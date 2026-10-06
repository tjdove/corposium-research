# Story 3.2: Defender Policy Comparison

Status: done

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

- [x] Config and defender (AC: 1)
  - [x] `buy`, `max_spread_bps`; `decide`; tests; hash test
  - [x] Commit separately: `story 3.2: defender buy flag and spread cap` (`c4279df`)
- [x] Policy scenarios and sweep (AC: 2, 3) — `base_axis` design, not sub-sweeps (ADR-0025 §2)
- [x] Chart (AC: 4)
- [x] Results, ADR, figures, close out (AC: 5, 6, 7, 8)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.2: defender policy comparison`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

**Commits.** `c4279df story 3.2: defender buy flag and spread cap` (config + defender +
tests only); `36bc938 story 3.2: policy scenarios, base axis, policy chart` (committed
before `make figures` so the figure manifest records a clean commit); final
`story 3.2: defender policy comparison` (figures, ADR, docs).

**Hashes.** Every scenario `content_hash()` and every existing sweep `sweep_spec_hash`
printed before any change (at `14aed1e`) and after each commit; `diff` empty except the
new spec:

```
scenarios/calibrated-baseline.yaml 44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a
scenarios/calibrated-stress.yaml 17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414
scenarios/soros-1992-no-defense.yaml 516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b
scenarios/soros-1992.yaml f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270
scenarios/soros-baseline.yaml 2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85
scenarios/soros-volatile.yaml 84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b
scenarios/usdc-2023.yaml 2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531
(+ 8 sweep spec hashes, all unchanged)
$ diff hashes_before.txt <(python hashes.py)      # after the final change
10a11
> sweeps/policy-comparison-mc.yaml 3e0793936a37544badfbbab0e5df36aab92787f23f8d3f497a4c67f1c084b2ba
```

Pinned in `tests/test_config.py::test_defender_buy_and_spread_cap_defaults_leave_every_scenario_hash_unchanged`.
`PHASE_ORDER_VERSION = 1`. `git diff 14aed1e --stat -- src/depeg_sim/kernel src/depeg_sim/protocol`
→ `src/depeg_sim/kernel/config.py | 16 +++++++++++++++-` only (AC 1 requires the
`DefenderConfig` fields there; no engine, scheduler or protocol change).

**Existing specs expand identically.** For all eight existing sweep specs, a dump of
`(index, seed, axis_values, cell content_hash)`, `sweep_spec_hash`, the resolved base hash
and the manifest `axes` list, run with the pre-change `sweep.py` (git worktree of `c4279df`
on `PYTHONPATH`) and with the new one:

```
sweeps/budget-x-depth-mc.yaml 200 72464b71437a25cb b3359c3fbb148ebb aa83d1a08fa8 927cf420ddcf
sweeps/capital-vs-resources-mc.yaml 2016 77375582bec4d2ff 19103151db95fa27 84ad0b810807 875a81e20e41
sweeps/oracle-lag-mc.yaml 640 bcc5fc86ab6d9dae 18c9c46f05fe9212 17b24b458e47 741530a8a92a
sweeps/pool-depth-x-attacker-mc.yaml 512 5765ce7a04ac911b 27c6cffa9113b2b2 84ad0b810807 e129442b8272
sweeps/pool-depth-x-attacker.yaml 16 835f0e5adc507661 0bce50074dbfdaac 2e09f431ce74 e129442b8272
sweeps/threshold-surface-mc.yaml 640 8f2e0a1ab944a964 74cb63b6a9653272 44ac03c60e5f 3c58eb7a4e90
sweeps/threshold-surface-ref-mc.yaml 640 99a78003efee6b8b 8ade9cb3fee88b37 85f4b9b21f82 3c58eb7a4e90
sweeps/usdc-2023-pace.yaml 7 601def4f8ab55299 918db271fbb88c22 2c3aeaa9825d 564d9e1ec74c
EXPANSION-IDENTICAL
```

**Policy files vs `calibrated-baseline.yaml`** (`diff`, header comment lines omitted;
each file's first line states the policy, then three lines pointing at the baseline):

```
== scenarios/policies/early-aggressive.yaml
< name: calibrated-baseline
> name: policy-early-aggressive
<   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 1.0, spend_pace: 0.2 }
>   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 0.5, spend_pace: 0.5 }
== scenarios/policies/late-conservative.yaml
< name: calibrated-baseline
> name: policy-late-conservative
<   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 1.0, spend_pace: 0.2 }
>   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 2.0, spend_pace: 0.1 }
== scenarios/policies/no-defense.yaml
< name: calibrated-baseline
> name: policy-no-defense
<   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 1.0, spend_pace: 0.2 }
== scenarios/policies/spread-only.yaml
< name: calibrated-baseline
> name: policy-spread-only
<   - { type: defender, id: defender-1, budget: 41_346_974, threshold_pct: 1.0, spend_pace: 0.2 }
>   - type: defender
>     id: defender-1
>     budget: 41_346_974
>     threshold_pct: 1.0
>     spend_pace: 0.2
>     spread_adjust_bps: 200
>     buy: false
```

`name` differs too (`policy-<name>`): a file called `early-aggressive.yaml` whose runs are
named `calibrated-baseline` would be misleading, and every sweep cell overwrites `name`
anyway. `tests/test_policy_comparison.py` diffs the dumped configs (everything but
`name` and the defender equal; the defender differs in exactly the AC 2 fields).

**Sweep** (`python -m depeg_sim.sweep sweeps/policy-comparison-mc.yaml --mc --workers 12`):

```
sweep: policy-comparison-mc cells=240 workers=12
wrote: output/policy-comparison-mc/sweep.parquet
mc: policy-comparison-mc grid_points=15 seeds=16 runs=240
wrote: output/policy-comparison-mc/mc.parquet

real	1m12.659s
user	13m42.403s
sys	0m6.069s
```

**Table** (`python scripts/policy_table.py`, 7.6 s; identical md5 `091ad07b…` before and
after `make figures` re-ran the sweep):

```
           policy  ratio defender_spent defender_bought holder_bought redemption_paid arb_redeemed holder_redeemed     ttp_h entered  p_broken     p_lo     p_hi  hours_saved spent_per_hour_saved
       calibrated    0.5     41,346,974      72,050,524    13,042,647       8,568,785    4,613,393       3,955,392 18.266667   16/16    0.0625 0.011119 0.283293       31.130            1,328,203
 early-aggressive    0.5     41,346,974      71,423,278    13,108,706       8,951,122    5,174,816       3,776,306 20.201667   16/16    0.1875 0.065915 0.430094       29.195            1,416,235
late-conservative    0.5     41,346,974      74,930,413    12,906,877       5,893,217    1,865,584       4,027,633  6.596667   16/16    0.0000 0.000000 0.193613       42.800              966,051
       no-defense    0.5              0               0    69,124,510      10,871,507   10,871,507               0 49.396667   16/16    1.0000 0.806387 1.000000        0.000                  NaN
      spread-only    0.5              0               0    69,127,093      10,690,073   10,690,073               0 50.396667   16/16    1.0000 0.806387 1.000000       -1.000                  NaN
       calibrated    0.7     41,346,974      93,447,300    20,283,977      10,866,775   10,866,775               0 37.071667   16/16    0.8750 0.639767 0.965023       17.435            2,371,493
 early-aggressive    0.7     41,346,974      89,044,924    22,260,521      10,871,507   10,871,507               0 41.421667   16/16    1.0000 0.806387 1.000000       13.085            3,159,876
late-conservative    0.7     41,346,974     102,863,701    17,493,523       8,672,341    5,239,518       3,432,823 19.206667   16/16    0.1250 0.034977 0.360233       35.300            1,171,302
       no-defense    0.7              0               0    99,476,851      10,871,507   10,871,507               0 54.506667   16/16    1.0000 0.806387 1.000000        0.000                  NaN
      spread-only    0.7              0               0    99,480,831      10,671,136   10,671,136               0 55.666667   16/16    1.0000 0.806387 1.000000       -1.160                  NaN
       calibrated    1.0     41,346,974     128,135,541    32,068,682      10,871,507   10,871,507               0 48.166667   16/16    1.0000 0.806387 1.000000       10.930            3,782,889
 early-aggressive    1.0     41,346,974     115,422,327    40,337,509      10,871,507   10,871,507               0 53.076667   16/16    1.0000 0.806387 1.000000        6.020            6,868,268
late-conservative    1.0     41,346,974     146,071,727    24,074,623      10,120,756    9,285,258         835,498 29.871667   16/16    0.3125 0.141644 0.555961       29.225            1,414,781
       no-defense    1.0              0               0   146,562,361      10,871,507   10,871,507               0 59.096667   16/16    1.0000 0.806387 1.000000        0.000                  NaN
      spread-only    1.0              0               0   146,568,546      10,654,327   10,654,327               0       NaN    1/16    1.0000 0.806387 1.000000          NaN                  NaN
```

Means over 16 seeds; `redemption_paid` = `arb_redeemed` + `holder_redeemed` (from
`redeem_fulfilled.paid_reference` by requester in each cell's `events.jsonl`); `ttp_h` =
median hours from run start to first re-entry (NaN = "never", fewer than half the seeds
re-enter); `hours_saved` against no-defense at the same ratio.

**Mechanism checks** (seed 1000):

```
ratio 1.0          trough            attacker 90% sold   defender 99% spent   avg price paid   attacker pnl
calibrated         -8151.2 @ 84      @ 71                @ 72                 0.323            -120,000,838
early-aggressive   -8698.1 @ 78      @ 71                @ 62                 0.358            -119,107,603
late-conservative  -7681.2 @ 50      @ 71                @ 94                 0.283            -123,328,249
first dump (step 50) deviation, all three: -7681 bps; step 51: -2742 / -2357 / -6353

spread-only vs no-defense, ratio 0.5: spread 0->200 at step 51, restored at 15029
  spread-only: first step above -2%: 14888, above -1%: 15028 (140 steps in -2..-1%)
  no-defense:  first step above -2%: 14591, above -1%: 14729 (138 steps)
  ratio 1.0:   spread-only 17837 -> 17977 (140);  no-defense 17480 -> 17621 (141)
  redemption_queued_total at -2%: 11.44M (spread-only), 11.62M (no-defense)
```

**`make figures`** (full, 12 workers), then the guard:

```
sweep: policy-comparison-mc cells=240 workers=12
mc: policy-comparison-mc grid_points=15 seeds=16 runs=240
...
drew: policy_comparison.png <- sweeps/policy-comparison-mc.yaml
wrote: 11 figures and docs/figures/manifest.json (commit 36bc93819e1f)
make figures: wall time 512 s (12 workers)

$ make figures-check
figures-check: ok, 11 figures match their sources
```

The ten existing PNGs regenerated byte-identical (`git status` shows only
`manifest.json` and the new `policy_comparison.png`).

**Tests and lint** (final tree):

```
$ python -m pytest
578 passed in 8.98s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
89 files already formatted
exit=0
```

559 at Story 3.1 + 19 new (defender 5, config 4, policy comparison 10).

### Completion Notes List

**Design: `base_axis`, not five sub-sweeps (AC 3 alternative; ADR-0025 §2).** The figure
pipeline (guard, `make figures`, `--quick`) assumes one spec file is one `SweepSpec` with
one `mc.parquet`. A five-sub-sweep source would need a second source type in all three.
With `base_axis` the policy sweep is an ordinary spec; the AC 3 "combined
`policies.parquet`" is the sweep's own `mc.parquet` (one row per policy × ratio, a
`policy` column, every mc column) and its manifest lists every base's hash
(`base_hashes`) and folds them into `spec_hash`. There is no
`scripts/run_policy_comparison.py`. Existing specs expand byte-identically (Debug Log).
Only one design was built.

**`buy=False` semantics.** In defense: `defend_spread_widen` on the widening step,
`defend_idle` otherwise; never `defend_buy` or `defend_budget_exhausted`.
`defend_spread_restore` still fires when the price comes back above the trigger (it
restores, it does not buy). I read AC 1's "rule `defend_spread_widen` or `defend_idle`"
as the in-defense rules. The widen test is now `target > base` (was `!=`), so a cap at
or below the current spread means no widen; equivalent under the default cap.

**Ratio-1.0 table (AC 5).** Means over 16 seeds; time to parity = median hours from run
start to first step within ±31 bps of the oracle.

| policy | defender spent | holder bought | redemption paid | arbitrageur redeemed | time to parity | p_stays_broken [Wilson 95%] |
|---|---:|---:|---:|---:|---:|---:|
| calibrated | 41.35M | 32.07M | 10.87M | 10.87M | 48.2 h | 1.00 [0.81, 1.00] |
| early-aggressive | 41.35M | 40.34M | 10.87M | 10.87M | 53.1 h | 1.00 [0.81, 1.00] |
| late-conservative | 41.35M | 24.07M | 10.12M | 9.29M | 29.9 h | 0.31 [0.14, 0.56] |
| spread-only | 0 | 146.57M | 10.65M | 10.65M | never (1/16 re-enter) | 1.00 [0.81, 1.00] |
| no-defense | 0 | 146.56M | 10.87M | 10.87M | 59.1 h | 1.00 [0.81, 1.00] |

**The three answers.** *Fastest:* late-conservative, at every ratio (6.6 / 19.2 / 29.9 h
at 0.5 / 0.7 / 1.0), and at 1.0 the only policy that recovers at all (11 of 16 seeds).
*Cheapest per hour saved against no-defense:* also late-conservative, at every ratio
(0.97M / 1.17M / 1.41M of budget per hour saved; calibrated 1.33M / 2.37M / 3.78M;
early-aggressive 1.42M / 3.16M / 6.87M). It is not cheaper because someone else pays:
every buyer spends the full 41.35M at every ratio, and under late-conservative the
holder absorbs less (24.1M stable vs 32.1M calibrated) and redemption pays less (10.12M
vs 10.87M). The difference is the price paid: the same budget buys 146M stable at an
average 0.283 against 128M at 0.323 (calibrated) and 115M at 0.358 (early-aggressive).
*Does spread-only ever recover?* No: `p_stays_broken` = 1.0 at every ratio. But it is not
the F-07 dead zone. With redemption throughput-bound, an ~11.4M backlog queued while the
price was far down drains at capacity through −2% … −1% (140 steps there, vs 138 for
no-defense). The 200 bps spread acts as a 2% tax on the arbitrage loop, so the climb runs
2% slower (297 steps, ~1 h, at 0.5). Spread-only is no-defense plus an hour; no-defense is
itself lost on the clock (49–59 h, all after the 37 h deadline), and at 1.0 the extra hour
pushes the first re-entry past 60 h in 15 of 16 seeds.

**Why late beats early.** All three buyers exhaust their budget in the first ~12–44 steps
of the attack (seed 1000, ratio 1.0: 99% spent at step 62 / 72 / 94 for early /
calibrated / late; the attacker has sold 90% by step 71). A fast defender lifts the pool
back toward par while the attacker still has most of its capital. The attacker sells into
the restored price, and once the budget is gone its tail sets a new, deeper trough
(−8,698 bps at step 78). A defender whose budget outlasts the dump keeps buying the tail
cheaply; its trough is the first dump (−7,681 at step 50). This is F-03 inside the policy
dimension. The sweep cannot separate trigger from pace (late-conservative changes both);
both triggers are crossed on the first dump, so pace is the likely lever. Follow-up
suggested in the ADR.

**Predictions checked.**

1. *Early-aggressive fastest at every ratio and spends the most; ≈ whole budget at 1.0.*
   **Missed.** It is the slowest buyer at every ratio (20.2 / 41.4 / 53.1 h) and the worst
   buyer on `p_stays_broken` at 0.5 and 0.7 (0.19 / 1.00). It does spend its whole budget,
   but so does every buyer at every ratio: spend does not separate the policies.
2. *Late-conservative spends least among buyers and is the slowest; at 1.0 may be clock.*
   **Missed.** It spends the same 41.35M as the others and is the fastest policy at every
   ratio. At 1.0 its median (29.9 h) is before the 37 h deadline; 5 of 16 seeds still
   break.
3. *Spread-only never recovers, by the F-07 dead zone.* **Outcome held, mechanism
   missed.** It never recovers (p = 1.0 at every ratio), but there is no stall between
   −2% and −1%: the redemption backlog carries the price through. It is the clock, with
   the spread slowing the climb by ~2%.
4. *No-defense time to parity between late-conservative and spread-only.* **Held as
   stated** (late < no-defense < spread-only at every ratio), but not for the predicted
   reason: late-conservative is the fastest policy, not the slowest buyer, so "between"
   spans almost the whole range.
5. *Per hour saved, calibrated cheaper than early-aggressive.* **Held** (1.33M vs 1.42M,
   2.37M vs 3.16M, 3.78M vs 6.87M); late-conservative is cheaper than both.

**Chart (`docs/figures/policy_comparison.png`).** Three panels over attacker capital 0.5 /
0.7 / 1.0× ($21.05B / $29.47B / $42.10B), one line per policy, calibrated in heavy black.
(a) Time to parity: late-conservative (orange squares) sits far below the rest, rising
from 6.6 h to 29.9 h and staying under the dashed 37 h deadline. Calibrated (black) and
early-aggressive (blue) start near 18–20 h and cross the deadline at 0.7×, with
early-aggressive above calibrated throughout. No-defense (amber diamonds) and spread-only
(green triangles) run together near the top, 49→59 h and 50→56 h, and spread-only ends
on an open "never" marker at the 60 h horizon line at 1.0×. (b) Defender spend: three
buyer markers sit on the $9.70B budget line at every ratio, with bands of no visible
width; spread-only and no-defense lie on zero. (c) p(stays broken) with Wilson bars:
late-conservative climbs 0 → 0.13 → 0.31. Calibrated goes 0.06 → 0.88 → 1.0 and
early-aggressive 0.19 → 1.0 → 1.0; spread-only and no-defense sit at 1.0 throughout.
Points are dodged sideways per policy so coinciding series stay visible.

**Finding candidates (ADR-0025 §4).** (1) F-13: when the budget is always spent, the
defense is decided by pace; a defender that spends slower than the attacker sells beats
one that spends faster, and late-conservative dominates on all six columns. (2) F-07
refinement: the spread dead zone needs redemption that is not throughput-bound; at
calibrated scale the backlog carries the price through, and the spread costs ~2% of the
climb's speed.

**AC 6.** The 1992 analogue was not run (`soros-1992*.yaml` were drawn by `make figures`
as their committed scenario figures and came out byte-identical; that is the figure
pipeline, not a re-analysis).

**ADR:** [ADR-0025](../adr/0025-defender-policies-and-base-axis.md) (Proposed; index not
edited).

**Out-of-scope notes.** No `arbitrageur_redeemed` summary key was added: it would change
every summary JSON for one table. `scripts/policy_table.py` reads it from events instead.

### File List

**Created:**

- `scenarios/policies/early-aggressive.yaml`
- `scenarios/policies/late-conservative.yaml`
- `scenarios/policies/spread-only.yaml`
- `scenarios/policies/no-defense.yaml`
- `sweeps/policy-comparison-mc.yaml`
- `scripts/policy_table.py`
- `tests/test_policy_comparison.py`
- `docs/adr/0025-defender-policies-and-base-axis.md`
- `docs/figures/policy_comparison.png`

**Modified:**

- `src/depeg_sim/kernel/config.py` — `DefenderConfig.buy`, `.max_spread_bps`; hash drops defaults
- `src/depeg_sim/agents/defender.py` — `buy=False`, `max_spread_bps` cap, widen only upward
- `src/depeg_sim/experiments/sweep.py` — `BaseAxis`, `SweepSpec.base_axis`, `base_paths`, `manifest_axes`; expansion, hash, manifest, CLI
- `src/depeg_sim/analysis/charts.py` — `plot_policy_comparison`
- `scripts/make_figures.py` — registers `policy_comparison.png`
- `Makefile` — policy sweep in `SWEEPS`
- `docs/figures/README.md`, `docs/figures/manifest.json`
- `tests/test_defender.py`, `tests/test_config.py`, `tests/test_figures.py`
- `docs/stories/3-2-defender-policy-comparison.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-05
**Outcome:** **APPROVE** ✅ — charter chart 5 delivered, and the result inverts the
Dev Notes' predictions with a clean mechanism.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest` → `578 passed in
27.54s`; `ruff check .` → `All checks passed!`; `ruff format --check .` → `89 files already
formatted`; `make figures-check` → `ok, 11 figures`. **Policy sweep re-run in full** (240
runs, 2 workers, 8m30s): `scripts/policy_table.py` reproduces every cell of the ratio-1.0
table — defender spent 41,346,974 for all three buyers; holder bought 32.07M / 40.34M /
24.07M / 146.57M / 146.56M; time-to-parity 48.2 / 53.1 / 29.9 / never (1 of 16) / 59.1 h;
`p_stays_broken` 1.0 / 1.0 / 0.3125 / 1.0 / 1.0 — and the 0.5 and 0.7 rows. Chart
regenerated and read.

### Rulings

1. **ADR-0025 → Accepted (finding, amended).** F-13 and the F-07 refinement promoted to
   FINDINGS. Amendment: F-13 is stated in terms of *price paid*, which the data gives
   directly (0.283 / 0.323 / 0.358 per stable for late / calibrated / early), rather than
   "pace decides", which the sweep cannot yet separate from trigger (builder's own caveat).
2. **`base_axis` on `SweepSpec` instead of five sub-sweeps → accepted**; the right call for
   the figure pipeline, and the eight existing specs expand identically (tested).
3. **Pace × trigger confound → folded into Story 3.4** as a second small sweep (D\*, ratio
   1.0, pace {0.05, 0.1, 0.2, 0.5} × trigger {0.5, 1, 2, 4}%, 8 seeds), with attacker pace
   as a third factor at two levels. No new story.
4. **Panel (b) of the chart is flat by construction** (every buyer spends its whole
   budget). For the note, panel (b) becomes *average price paid per stable* — the quantity
   that differs. Epic 4 figure pass; the committed figure stands as the record.
5. **`scripts/policy_table.py` reads arbitrageur redemptions from `events.jsonl`** because
   the summary lacks them → accepted; 3.5 adds `arbitrageur_redeemed` to `summarize` so the
   table can come from parquet alone.
6. **Policy file names differ (`name: policy-<x>`)** → accepted; necessary for distinct run
   dirs, and tested.
7. **CI result not in the Debug Log** → recorded here: both jobs green on 14ce26c.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | `buy`, `max_spread_bps`; `decide` honours both; hashes unchanged |
| 2 | ✅ | four policy files + baseline; diffs in Debug Log; test pins the diff |
| 3 | ✅ | `base_axis` (allowed alternative, proposed in ADR); one spec, one parquet |
| 4 | ✅ | three-panel chart; reads parquet + manifest |
| 5 | ✅ | ratio-1.0 table with all six columns; three answers |
| 6 | ✅ | 1992 not re-run |
| 7 | ✅ | ADR-0025 |
| 8 | ✅ | figure registered; `make figures` 512 s; guard ok; 578 tests; CI green |

**8 of 8 ACs met.**

### Key Findings

- **F-13:** when every defender spends its whole budget, the defense is decided by the
  price it pays. The fast defender is dry within 12–44 steps, before the attacker has
  finished selling; it bought near par and the attacker's remaining stock sets a new low.
  The slow defender's budget outlasts the selling and buys at 0.283 instead of 0.358. At
  ratio 1.0 it is the only policy that recovers (11 of 16 seeds; 29.9 h vs 48–59 h).
- **F-07 refinement:** at calibrated scale there is no spread dead zone. Capacity-limited
  redemption queued while the price was deep keeps paying out through the band; the 200 bps
  spread costs about an hour. Spread-only fails on the clock, like no-defense.
- All five predictions in the Dev Notes were wrong or right for the wrong reason. Recorded
  as L-15 working.

### Learnings for Story 3.3

- Name policies by what they do (pace), not when they start (trigger).
- A flat panel is a result; say what it means in the caption rather than hiding it.
- 1992 is the natural home for F-13: the Bank of England spent fast at the floor.

## Change Log

- 2026-10-05: Story drafted by dev manager after Story 3.1 review
- 2026-10-05: Implemented by Claude Code (Opus 5.5): defender `buy` flag and spread cap
  (hash-neutral); four policy scenarios; `base_axis` on `SweepSpec` in place of five
  sub-sweeps; `policy-comparison-mc` (240 runs, 73 s); `plot_policy_comparison`; ADR-0025
  (Proposed) with two finding candidates; `make figures` 512 s, guard green; 578 tests.
  Status → review.
- 2026-10-05: Senior review APPROVE; ADR-0025 accepted (finding, amended); F-13 and F-07 refinement added; pace × trigger → 3.4; Status done
