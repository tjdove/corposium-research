# Story 3.8 (stretch): LP Withdrawal Agent

Status: review

## Story

As a **researcher**,
I want liquidity providers who pull their liquidity when the peg looks lost,
so that pool depth becomes endogenous and the note can say what reflexive liquidity flight does to the thresholds the surfaces drew with depth held fixed.

## Acceptance Criteria

1. **AMM: `remove_liquidity`.** `AMM` gains `remove_liquidity(fraction) -> LiquidityResult` (0 < fraction ≤ 1): both reserves scale by `1 − fraction` (spot price unchanged, `k` scales by `(1 − fraction)²`), returns the stable and reference withdrawn; `execute` accepts `kind == "remove_liquidity"` with `params = {"fraction": f}`, emits `liquidity_removed {source, fraction, stable_out, reference_out, reserve_stable, reserve_reference}` or `liquidity_rejected`; the drain guard (reserves never reach zero) applies; existing swap behaviour byte-identical (run-vs-rerun fixtures untouched); the `k`-non-decreasing property test is amended to "non-decreasing between liquidity events" and a new test pins the scaling
2. **Agent.** `agents/lp.py`: `LiquidityProvider(agent_id, share, panic_threshold_pct, pace)` extending `Agent`: owns `share` (0 < share ≤ 1) of the pool at start; each step while `amm.peg_deviation < −panic_threshold_pct/100` and it still has share, submits `remove_liquidity` for `min(pace × share_remaining, share_remaining)` as a fraction **of the current pool** (`fraction = removed_share / total_share_remaining_in_pool`, document the arithmetic); one-way: it never re-adds; rules `lp_hold`, `lp_withdraw`, `lp_done`; PnL marks withdrawn reserves at spot; never calls `ctx.rng`; `LPConfig(type: "lp", id, share, panic_threshold_pct, pace)` in the `AgentConfig` union; `build_agents` dispatch; every existing scenario `content_hash()` unchanged (test)
3. Tests per the 1.7 pattern: holds above the threshold; withdraws at pace below it; stops at zero share; price unchanged by a withdrawal; `k` scales; a swap after a withdrawal has larger impact; decision records
4. **Scenario:** `scenarios/calibrated-baseline-lp.yaml` — `calibrated-baseline-ou.yaml` plus an LP with `share 0.5` (half the pool is flighty), `panic_threshold_pct 5`, `pace 0.1`; header states these as assumptions and why 5% (above the holder's 2% entry, below the trough at calibrated depth); `python run.py`; before/after against `calibrated-baseline-ou` in Completion Notes (trough, time-to-parity, defender spend, pool depth at the trough)
5. **Sweep:** `sweeps/lp-flight-mc.yaml` — base the LP scenario, par criterion; axes `agents[type=lp].panic_threshold_pct ∈ {2, 5, 10, 20}` × `agents[type=lp].share ∈ {0.25, 0.5, 0.75}` × attacker ratio `{0.5, 0.7, 1.0}`; 8 seeds; `plot_lp_flight(sweep_dir)`: time-to-parity heatmaps (threshold × share) per attack ratio, "never" hatched, 37 h line, plus a small panel of **pool depth remaining at the trough** (fraction of the start) over the same grid at ratio 1.0; reads parquet + manifest (add `pool_depth_at_trough` to `summarize`, `None` when no AMM)
6. Completion Notes: does liquidity flight make the depeg deeper (by how much, at which thresholds), does it make recovery faster or slower (F-03 says a shallower pool is cheaper to defend — does flight *help* the defender?), and is there a threshold below which the LP's flight is self-fulfilling (the withdrawal itself pushes the price past the next LP's threshold — one LP here, so report whether its own withdrawals deepen the trough it reacts to); one sentence for the note; F-03 either confirmed from the other side or qualified
7. A `Proposed` ADR: the AMM action, the agent, the scenario assumptions, the sweep result, and a finding candidate
8. Figure registered; `make figures`; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [x] AMM remove_liquidity (AC: 1)
  - [x] Commit separately: `story 3.8: amm remove_liquidity` (`fcea3d4`)
- [x] LP agent, config, factory, tests (AC: 2, 3)
  - [x] Commit separately: `story 3.8: lp withdrawal agent` (`a03d062`)
- [x] Scenario and sweep (AC: 4, 5) (`5a55cec`, fix-up `6f2859d`)
- [x] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.8: lp withdrawal agent and liquidity flight`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.7 (Status: done)**

- Assumptions are shown, not hidden: the LP's share, threshold and pace are three
  assumptions with no public anchor; say so in the scenario header and the ADR.
- Predictions below are predictions.
- This is the first `protocol/` change since Epic 1. The AMM's swap path must be
  byte-identical afterwards; the fixtures will tell you.

[Source: docs/stories/3-7-multi-tranche-holder.md#Senior-Developer-Review, F-03, F-11 refinements, CHARTER §4 stretch]

### Why this is the last story before the freeze

The charter called LP flight "the core Soros dynamic": liquidity that leaves when it is
needed. Every surface so far held depth fixed. This story makes depth respond to the
price, which is the reflexive loop the 1992 narrative is built on (BACKGROUND §4:
"positions all reversed at once"). It is also the one mechanism the note would be asked
about if it were absent.

### The arithmetic to get right

The LP owns a share of the pool, not an amount. A withdrawal of share `s` from a pool in
which flighty LPs hold `S` of the total scales both reserves by `1 − s`; the LP's remaining
share of the *new* pool is `(S − s)/(1 − s)`. Keep the agent's state in share terms and
convert to a pool fraction at the moment of the action. Write the formula in the agent's
docstring and test it with two consecutive withdrawals.

### Predictions (to be checked)

- At calibrated depth and ratio 1.0, a 50% flighty LP at 5% deepens the trough by 30–60%
  and *shortens* time-to-parity (F-03 from the other side: the shallower pool is cheaper
  for the defender and the holder to buy back).
- Pool depth remaining at the trough falls below 0.6 at thresholds ≤ 5% and stays near 1.0
  at 20%.
- The LP's own withdrawals deepen the trough it reacts to (the 2% threshold column is the
  worst), but with one LP there is no cascade: the effect is bounded by `share`.
- Flight never flips a recovering cell to "never" at D\* — the clock result stands — and
  it does not change which cells lose the price at deeper pools (depth was never the
  binding quantity there).

### Cost

Sweep: 4 × 3 × 3 × 8 = 288 runs; a few minutes on 10 workers.

### References

- [Source: docs/epics.md#Story-3.8]
- [Source: docs/CHARTER.md#4-Scope] — stretch item
- [Source: docs/FINDINGS.md] — F-03, F-11 (+ refinements), F-13
- [Source: src/depeg_sim/protocol/amm.py] — `swap`, `execute`, drain guard
- [Source: docs/adr/0005-construction-validates-execution-rejects.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-8-lp-withdrawal-agent.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

All output below is pasted from the commands as run (Seoul, Python 3.12.13, `.venv`).

**Byte identity of the AMM commit.** A script ran every scenario and hashed
`timeseries.parquet`, `events.jsonl`, `decisions.jsonl`, `summary.json` and the
concatenated checkpoints, before any change and after each commit:

```
after fcea3d4 (amm remove_liquidity):   diff fp-before.json fp-after1.json -> FINGERPRINT IDENTICAL
after a03d062 (lp withdrawal agent):    diff fp-before.json fp-after2.json -> FINGERPRINT IDENTICAL
after 6f2859d (summary keys):           every scenario "differs in ['summary.json']" only
```

The last is the two new summary keys; `tests/test_reference_recovery.py` re-pins the
soros-baseline summary (`be7d3266…`) and asserts that without the two lines the bytes are
the Story 3.5 capture (`f2428bdb…`). Scenario hashes: all nine existing hashes pinned in
`tests/test_lp.py::test_existing_scenario_hashes_unchanged` (as of `24c2a6e`), green.

**Before/after (seed 42).**

```
depeg-sim: scenario=calibrated-baseline-ou seed=42 hash=741f1bdd0012
run: steps=7024 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
depeg-sim: scenario=calibrated-baseline-lp seed=42 hash=4707a65abb67
run: steps=7099 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
```

**Sweep** (`time python -m depeg_sim.sweep sweeps/lp-flight-mc.yaml --mc --workers 10`):

```
mc: lp-flight-mc grid_points=36 seeds=8 runs=288
wrote: output/lp-flight-mc/mc.parquet

real	0m49.077s
user	7m55.972s
sys	0m3.575s
exit=0
```

**Aggregate** (`python scripts/lp_flight_table.py --workers 10`, 32.8 s wall on the first run):

```
A. sweep attacks (8 seeds per cell)
 cell  ratio  trough_bps vs_no_lp hours held_h recovered  defender_M  liq_at_trough share   thr withdrawals panic_steps
no LP    0.5     -5774.3           18.3  18.27       8/8       41.35          1.000                                    
no LP    0.7     -6885.7           37.0              0/8       41.35          1.000                                    
no LP    1.0     -8151.2           48.2              0/8       41.35          1.000                                    
   LP    0.5     -5774.3    +0.0%  11.5  11.50       8/8       41.35          1.000  0.25   2.0       184.0      5196.0
   LP    0.5     -5774.3    +0.0%  11.5  11.50       8/8       41.35          1.000  0.25   5.0       184.0      4776.0
   LP    0.5     -5774.3    +0.0%  11.5  11.50       8/8       41.35          1.000  0.25  10.0       184.0      4059.0
   LP    0.5     -5774.3    +0.0%  11.4  11.42       8/8       41.35          1.000  0.25  20.0       184.0      2559.0
   LP    0.5     -5774.3    +0.0%   3.8   3.77       8/8       41.35          1.000   0.5   2.0       191.0      5196.0
   LP    0.5     -5774.3    +0.0%   3.8   3.77       8/8       41.35          1.000   0.5   5.0       191.0      4776.0
   LP    0.5     -5774.3    +0.0%   3.7   3.74       8/8       41.35          1.000   0.5  10.0       191.0      4059.0
   LP    0.5     -5774.3    +0.0%   3.8   3.84       8/8       41.35          1.000   0.5  20.0        44.0      2559.0
   LP    0.5     -5774.3    +0.0%   0.4   0.55       8/8       39.87          1.000  0.75   2.0        49.0      5196.0
   LP    0.5     -5774.3    +0.0%   0.4   0.54       8/8       39.88          1.000  0.75   5.0        36.0      4776.0
   LP    0.5     -5774.3    +0.0%   0.4   0.52       8/8       39.92          1.000  0.75  10.0        29.0      4059.0
   LP    0.5     -5774.3    +0.0%   0.4   0.44       8/8       40.22          1.000  0.75  20.0        19.0      2559.0
   LP    0.7     -6927.3    +0.6%  27.2  27.17       8/8       41.35          0.756  0.25   2.0       184.0     10827.0
   LP    0.7     -6927.3    +0.6%  27.2  27.17       8/8       41.35          0.756  0.25   5.0       184.0     10407.0
   LP    0.7     -6927.3    +0.6%  27.2  27.17       8/8       41.35          0.756  0.25  10.0       184.0      9690.0
   LP    0.7     -6927.3    +0.6%  27.2  27.17       8/8       41.35          0.756  0.25  20.0       184.0      8199.0
   LP    0.7     -6913.6    +0.4%  17.0  16.98       8/8       41.35          0.512   0.5   2.0       191.0     10827.0
   LP    0.7     -6913.6    +0.4%  17.0  16.98       8/8       41.35          0.512   0.5   5.0       191.0     10407.0
   LP    0.7     -6913.6    +0.4%  17.0  16.98       8/8       41.35          0.512   0.5  10.0       191.0      9690.0
   LP    0.7     -6913.6    +0.4%  17.0  16.98       8/8       41.35          0.512   0.5  20.0       191.0      8199.0
   LP    0.7     -6748.3    -2.0%   6.7   6.71       8/8       41.35          1.000  0.75   2.0       194.0     10827.0
   LP    0.7     -6748.3    -2.0%   6.7   6.71       8/8       41.35          1.000  0.75   5.0       194.0     10407.0
   LP    0.7     -6748.3    -2.0%   6.7   6.71       8/8       41.35          1.000  0.75  10.0       194.0      9690.0
   LP    0.7     -6748.3    -2.0%   6.7   6.71       8/8       41.35          1.000  0.75  20.0       194.0      8199.0
   LP    1.0     -8191.1    +0.5%  35.4  35.41       8/8       41.35          0.759  0.25   2.0       184.0     14172.0
   LP    1.0     -8191.1    +0.5%  35.4  35.41       8/8       41.35          0.759  0.25   5.0       184.0     13749.0
   LP    1.0     -8191.1    +0.5%  35.4  35.41       8/8       41.35          0.759  0.25  10.0       184.0     13035.0
   LP    1.0     -8191.1    +0.5%  35.4  35.41       8/8       41.35          0.759  0.25  20.0       184.0     11541.0
   LP    1.0     -8225.8    +0.9%  22.5  22.46       8/8       41.35          0.517   0.5   2.0       191.0     14172.0
   LP    1.0     -8225.8    +0.9%  22.5  22.46       8/8       41.35          0.517   0.5   5.0       191.0     13749.0
   LP    1.0     -8225.8    +0.9%  22.5  22.46       8/8       41.35          0.517   0.5  10.0       191.0     13035.0
   LP    1.0     -8225.8    +0.9%  22.5  22.46       8/8       41.35          0.517   0.5  20.0       191.0     11541.0
   LP    1.0     -8196.1    +0.6%   9.5   9.50       8/8       41.35          0.279  0.75   2.0       194.0     14172.0
   LP    1.0     -8196.1    +0.6%   9.5   9.50       8/8       41.35          0.279  0.75   5.0       194.0     13749.0
   LP    1.0     -8196.1    +0.6%   9.5   9.50       8/8       41.35          0.279  0.75  10.0       194.0     13035.0
   LP    1.0     -8196.1    +0.6%   9.5   9.50       8/8       41.35          0.279  0.75  20.0       194.0     11541.0

B. episode attack: capital 11,540,596.0 (ratio 0.064; 8 seeds per cell)
 cell  trough_bps vs_no_lp hours held_h recovered  defender_M  liq_at_trough share   thr withdrawals panic_steps
no LP     -1253.2            0.3   0.41       8/8        7.70            1.0                                    
   LP     -1253.2    +0.0%   0.3   0.35       8/8        7.43            1.0  0.25   2.0        16.0        14.0
   LP     -1253.2    +0.0%   0.3   0.35       8/8        7.55            1.0  0.25   5.0         5.0         4.0
   LP     -1253.2    +0.0%   0.3   0.73       8/8        7.61            1.0  0.25  10.0         1.0         1.0
   LP     -1253.2    +0.0%   0.3   0.41       8/8        7.70            1.0  0.25  20.0         0.0         0.0
   LP     -1253.2    +0.0%   0.3   0.36       8/8        7.10            1.0   0.5   2.0        18.0        14.0
   LP     -1253.2    +0.0%   0.3   0.66       8/8        7.27            1.0   0.5   5.0         7.0         4.0
   LP     -1253.2    +0.0%   0.3   0.73       8/8        7.56            1.0   0.5  10.0         1.0         1.0
   LP     -1253.2    +0.0%   0.3   0.41       8/8        7.70            1.0   0.5  20.0         0.0         0.0
   LP     -1253.2    +0.0%   0.3   0.50       8/8        6.62            1.0  0.75   2.0        22.0        14.0
   LP     -1253.2    +0.0%   0.3   0.58       8/8        6.95            1.0  0.75   5.0         9.0         4.0
   LP     -1253.2    +0.0%   0.3   0.40       8/8        7.60            1.0  0.75  10.0         1.0         1.0
   LP     -1253.2    +0.0%   0.3   0.41       8/8        7.70            1.0  0.75  20.0         0.0         0.0
```

**Sink diagnostic** (in-process, seed 1000, scratch script not committed):

```
ratio 1.0 share None: steps 18000 max_steps; attacker sold 179.5M; defender bought 128.1M (spent 41.3); holder bought 32.1M; redeemed 10.9M; pool stable end 16.7M
ratio 1.0 share 0.5: steps 13637 peg_recovered; attacker sold 179.5M; defender bought 134.1M (spent 41.3); holder bought 31.9M; redeemed 8.2M; pool stable end 8.3M; LP took stable 13.0M ref 5.59M, pnl 1.90M of initial 16.67M, share left 0.0000
ratio 0.064 share 0.5: steps 7099 peg_recovered; attacker sold 11.5M; defender bought 8.0M (spent 7.3); holder bought 3.1M; redeemed 3.5M; pool stable end 12.3M; LP took stable 4.4M ref 4.26M, pnl -0.01M of initial 16.67M, share left 0.2391
```

**make figures / guard** (`make figures`, 12 workers):

```
wrote: output/threshold-surface-ref-mc/sweep.parquet
wrote: output/threshold-surface-ref-mc/mc.parquet
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 138 s
wrote: output/threshold-surface-mc/sweep.parquet
wrote: output/threshold-surface-mc/mc.parquet
sweep sweeps/threshold-surface-mc.yaml: wall time 133 s
wrote: output/budget-x-depth-mc/sweep.parquet
wrote: output/budget-x-depth-mc/mc.parquet
sweep sweeps/budget-x-depth-mc.yaml: wall time 48 s
wrote: output/oracle-lag-mc/sweep.parquet
wrote: output/oracle-lag-mc/mc.parquet
sweep sweeps/oracle-lag-mc.yaml: wall time 111 s
wrote: output/policy-comparison-mc/sweep.parquet
wrote: output/policy-comparison-mc/mc.parquet
sweep sweeps/policy-comparison-mc.yaml: wall time 77 s
wrote: output/holder-exit-1992-mc/sweep.parquet
wrote: output/holder-exit-1992-mc/mc.parquet
sweep sweeps/holder-exit-1992-mc.yaml: wall time 19 s
wrote: output/budget-x-attack-mc/sweep.parquet
wrote: output/budget-x-attack-mc/mc.parquet
sweep sweeps/budget-x-attack-mc.yaml: wall time 61 s
wrote: output/pace-x-trigger-mc/sweep.parquet
wrote: output/pace-x-trigger-mc/mc.parquet
sweep sweeps/pace-x-trigger-mc.yaml: wall time 90 s
wrote: output/pace-ratio-mc/sweep.parquet
wrote: output/pace-ratio-mc/mc.parquet
sweep sweeps/pace-ratio-mc.yaml: wall time 24 s
wrote: output/threshold-surface-ou-mc/sweep.parquet
wrote: output/threshold-surface-ou-mc/mc.parquet
sweep sweeps/threshold-surface-ou-mc.yaml: wall time 130 s
wrote: output/lp-flight-mc/sweep.parquet
wrote: output/lp-flight-mc/mc.parquet
sweep sweeps/lp-flight-mc.yaml: wall time 51 s
drew: lp_flight.png <- sweeps/lp-flight-mc.yaml
wrote: 19 figures and docs/figures/manifest.json (commit 6f2859d47e44, code_hash c72e8639692a)
make figures: wall time 893 s (12 workers)
exit=0
$ make figures-check
.venv/bin/python scripts/check_figures.py
figures-check: ok, 19 figures match their sources (code_hash matches)
exit=0
```

The other 18 PNGs regenerated byte-identical (only `manifest.json` and the new
`lp_flight.png` show in `git status`).

**Tests and lint** (`make test` = pytest with the protocol/ + agents/ coverage gate):

```
make test exit=0
src/depeg_sim/agents/lp.py                71      1    99%
src/depeg_sim/protocol/amm.py            153      0   100%
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
886 passed in 33.97s
$ ruff check .
All checks passed!
ruff check exit=0
$ ruff format --check .
98 files already formatted
ruff format exit=0
```

**CI:** recorded after push (follow-up commit).

**Process note.** Commit `5a55cec` went in with 4 failing tests: my command chain checked
`pytest | tail`'s exit code, not pytest's. Fixed in `6f2859d` before anything was pushed
(new scenario added to the two "added later" lists, `summarize` tolerates a metrics frame
without reserve columns, summary byte pin re-captured). Nothing was pushed between them.
Also: copying the sweep's 2 GB of run directories into the scratchpad filled the /tmp
quota once; removed, and logs moved under `output/`.

### Completion Notes List

**AC 1–3.** `remove_liquidity` as specified, plus `lp_supply` on the AMM (outstanding
liquidity in initial-pool units; judgment call, ADR-0031 §2). `LiquidityProvider` keeps
shares of the initial pool and converts at the action: `fraction = removed / lp_supply`;
the docstring carries the formula and `test_two_consecutive_withdrawals_pin_the_share_arithmetic`
pins 0.05 → 0.0473684… → 0.405 of 0.905 = (S − s)/(1 − s). One float note: the rule is the
AC's `peg_deviation < −threshold/100`, and spot exactly 0.95 is −0.05000000000000004, so it
fires at "exactly" 5%; the hold test uses 0.9500001.

**AC 4: before/after, seed 42** (`calibrated-baseline-ou` vs `-lp`):

| | OU (no LP) | LP (share 0.5, 5%, pace 0.1) |
|---|---|---|
| trough | −1,253.2 bps at step 50 | −1,253.2 bps at step 50 |
| time to parity (first re-entry) | 87 steps = 0.29 h | 91 steps = 0.30 h |
| sustained recovery from trough | 74 steps (held from 0.41 h) | 149 steps (held from 0.66 h) |
| run ends | step 7,024, `peg_recovered` | step 7,099, `peg_recovered` |
| defender spend | 7.70M | 7.27M (−5.5%) |
| `pool_depth_at_trough` / `pool_liquidity_at_trough` | 0.935 / 1.000 | 0.935 / 1.000 |
| LP | — | 7 withdrawals (steps 51–62), leaves 0.239 of its 0.5; pool liquidity ends ≈ 0.74 |

The trough is the attacker's first sale, executed at step 50 before any LP can observe it,
so flight cannot touch it. Afterwards the shallower pool makes each attacker sale move the
price further: the sawtooth's lows in steps 52–61 sit at −5.2 … −5.3% with the LP against
−4.1 … −4.9% without, so the band is held 15 minutes later; the defender spends 5.5% less.

**AC 6: the three questions.**

1. *Does flight make the depeg deeper?* **Barely.** At the episode attack: 0.0% in every
   cell (the trough precedes flight). At the sweep's attacks: 0.0% at 0.5×, −2.0 … +0.6% at
   0.7×, +0.5 … +0.9% at 1.0× (worst: share 0.5, −8,151 → −8,226 bps), and the same at every
   threshold. A later, deeper low exists only when the attacker keeps selling into the
   shrunken pool after the LP has gone.
2. *Faster or slower recovery; does flight help the defender?* **Faster, by a lot, and yes.**
   Time to parity at 0.5×: 18.3 → 11.5 / 3.8 / 0.4 h (share 0.25 / 0.5 / 0.75); at 0.7×:
   37.0 h and 0/8 recovered → 27.2 / 17.0 / 6.7 h, 8/8; at 1.0×: 48.2 h and 0/8 → 35.4 /
   22.5 / 9.5 h, 8/8. The defender still spends its whole budget at ≥ 0.7× but buys the
   price back hours sooner; at the episode attack it spends less (7.70M → 7.27M at 0.5/5%,
   6.62M at 0.75/2%). Mechanism (ADR-0031): the fleeing LP leaves pro rata with a pool full
   of the attacker's stable, a third sink besides the defender and redemption (ratio 1.0,
   share 0.5: it takes 13.0M stable against the 8.3M it brought; redemption fills 8.2M
   instead of 10.9M), and the half-size pool that remains needs half the buying to reach par.
3. *Self-fulfilling threshold?* **Weakly, below ≈ 10%, bounded, not a cascade.** A withdrawal
   never moves spot. At the episode attack the LP's withdrawals keep the post-trough
   sawtooth below its own threshold for longer than the same seeds without it (withdrawals
   vs panic steps: 2%: 16 / 18 / 22 vs 14; 5%: 5 / 7 / 9 vs 4; 10%: 1 vs 1; 20%: 0 vs 0), so
   at ≤ 5% its flight feeds its own panic by up to 2.25×, more with a larger share. It stops
   when the attacker stops, never deepens the trough it reacts to, and still lowers
   defender spend. At the sweep's attacks the question does not arise: the price is far
   below every threshold for hours whatever the LP does, and every threshold behaves alike.

**One sentence for the note:** "Liquidity that flees a depeg helps the defender: it leaves
holding the attacker's stable, so at calibrated depth a half-flighty pool takes the
largest attack from never holding par to recovered in 22 hours, and deepens the trough by
under 1%, because the first dump lands before anyone can flee."

**F-03 verdict: confirmed from the other side, and qualified.** The cheaper-defense half
is confirmed and stronger than F-03's price channel alone, because flight removes stable
as well as depth. The deeper-depeg half barely appears (≤ 0.9%): an LP that reacts to an
observed price is one step behind the dump that sets the trough. It also qualifies F-11:
at D* the clock (0/8 recovered at 0.7× and 1.0×) becomes 8/8 with any flighty share on the
grid.

**Predictions checked.**

1. "50% LP at 5% deepens the trough by 30–60% and shortens time to parity" — **trough: miss**
   (+0.9% at 1.0×; 0.0% at the episode attack). **Shorter: held** (48.2 → 22.5 h).
2. "Pool depth at the trough below 0.6 at thresholds ≤ 5%, near 1.0 at 20%" — **miss.**
   Threshold makes no difference at any swept attack. At 1.0× the pool still there is
   0.76 / 0.52 / 0.28 by share at every threshold, 20% included (context metric 0.32 / 0.22
   / 0.12); at 0.5× it is 1.0 everywhere (the trough precedes flight).
3. "The LP's own withdrawals deepen the trough it reacts to; 2% worst; no cascade; bounded
   by share" — **partly.** They do not deepen the trough (it precedes them, or is the same
   at every threshold); they do prolong the LP's own panic below ≈ 10%, most at 2%; no
   cascade and bounded: held.
4. "Flight never flips a recovering cell to never at D*; the clock result stands; deeper
   pools unchanged" — **first half held** (no cell gets worse; all 36 recover 8/8);
   **"the clock stands": miss** — flight removes the clock at D*; **deeper pools: not
   tested** (the AC's sweep is at D* only).

**Chart in words** (`docs/figures/lp_flight.png`): three heatmaps (0.5×, 0.7×, 1.0×
resources) of median hours to first re-entry over flighty share (rows 0.25 / 0.5 / 0.75)
× panic threshold (columns 2 / 5 / 10 / 20%). Every row is a single colour: the threshold
does nothing. Hours fall with share in every panel (1.0×: 35.4 / 22.5 / 9.5 h) and rise
with attack size; no cell is hatched "never" and none lies past the 37 h deadline, so no
dashed boundary is drawn. The fourth, narrower panel shows the 1.0× pool at the trough:
colour = reference reserve / start (0.32 / 0.22 / 0.12), each cell labelled with `liq`
(0.76 / 0.52 / 0.28), again constant across thresholds.

**Judgment calls for review** (all in ADR-0031): `lp_supply` on the AMM; a second summary
key `pool_liquidity_at_trough` beside the contracted `pool_depth_at_trough`, because the
contracted one reads 0.43 with no flight at 1.0× (strike it if unwanted); `lp_done` at
1e-9 shares; a rejected removal is retried; `scripts/lp_flight_table.py` added to rerun the
no-LP counterparts and the episode-attack threshold column, which the AC 6 answers need.

**ADR:** [0031](../adr/0031-lp-withdrawal-and-liquidity-flight.md), Proposed (finding
candidate F-15). Index not edited.

**make figures:** 893 s on 12 workers (843 s at 3.7; the LP sweep adds 51 s); guard green, 19 figures.

### File List

**Created:**

- `src/depeg_sim/agents/lp.py`
- `scenarios/calibrated-baseline-lp.yaml`
- `sweeps/lp-flight-mc.yaml`
- `scripts/lp_flight_table.py`
- `tests/test_amm_liquidity.py`
- `tests/test_lp.py`
- `docs/adr/0031-lp-withdrawal-and-liquidity-flight.md`
- `docs/figures/lp_flight.png`

**Modified:**

- `src/depeg_sim/protocol/amm.py` — `remove_liquidity`, `LiquidityResult`, `lp_supply`, execute branch
- `src/depeg_sim/kernel/config.py` — `LPConfig` in the `AgentConfig` union (only kernel file touched)
- `src/depeg_sim/agents/factory.py` — dispatch
- `src/depeg_sim/analysis/summary.py` — `pool_depth_at_trough`, `pool_liquidity_at_trough`
- `src/depeg_sim/experiments/mc.py` — the two keys in `METRICS`
- `src/depeg_sim/analysis/charts.py` — `plot_lp_flight`
- `scripts/make_figures.py`, `Makefile` — figure and sweep registered
- `tests/test_properties.py` — k non-decreasing between liquidity events
- `tests/test_summary.py`, `tests/test_charts.py`, `tests/test_figures.py`, `tests/test_scripts.py`,
  `tests/test_holder_config.py`, `tests/test_holder_tranches.py`, `tests/test_reference_recovery.py`
- `docs/figures/manifest.json`, `docs/figures/*.png` (regenerated), `docs/figures/README.md`
- `docs/REPRODUCIBILITY.md`, `README.md`
- `docs/stories/3-8-lp-withdrawal-agent.md`

## Change Log

- 2026-10-07: Story drafted by dev manager after Story 3.7 review (third and last Epic 3 stretch story)
- 2026-10-08: Implemented (Claude Code on Seoul): AMM `remove_liquidity`, LP agent, `calibrated-baseline-lp`, `lp-flight-mc`, `plot_lp_flight`, ADR-0031 Proposed; Status: review
