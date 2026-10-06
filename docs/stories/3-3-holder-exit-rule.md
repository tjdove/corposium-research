# Story 3.3: Holder Sell Rule and the 1992 Switch-Sides Test

Status: review

## Story

As a **researcher**,
I want the holder to be able to lose its belief and sell,
so that the note can test BACKGROUND §4's claim that Black Wednesday needed the convergence traders to turn — and say, with numbers, whether a believer who switches sides is what breaks a peg.

## Acceptance Criteria

1. `HolderConfig` gains `exit_discount_pct: float | None = None` (`gt=0, lt=100` when set); `Holder` gains rule `hold_exit`: on the first step where `amm.spot_price < 1 − exit_discount_pct/100`, it cancels nothing already queued but sells **all** stable it holds on the AMM in one `swap sell_stable` (if that amount is ≤ `DUST`, no action), sets a one-way `exited` flag, and from then on never buys or redeems again (`hold_done`); `exit_discount_pct` must exceed `entry_discount_pct` (validator, error names the rule); every existing scenario `content_hash()` unchanged (test); decision trace records `hold_exit` once
2. `tests/test_holder.py`: exits once below the exit price; never re-enters when the price recovers; exit with nothing held records no action; validator error; PnL after a buy-then-exit cycle at a lower price is negative
3. `sweeps/holder-exit-1992-mc.yaml`: base `soros-1992.yaml` at 6× (as committed); axes `agents[type=holder].exit_discount_pct ∈ {null, 5, 10, 20, 40}` × `agents[type=holder].capital ∈ {C*, 5 C*, 25 C*}` (9,166,667; 45,833,335; 229,166,675 — the last ≈ 0.9× the attacker); 8 seeds from 1000; `max_steps` as the scenario; `sweep.parquet` gains nothing new, but the per-run summary must include `holder_pnl` (exists) and `reserves_exhausted`, `steps_run`; `null` must be expressible on an axis (if `set_path` cannot set `None`, make it able to, with a test)
4. Multiple re-scan 4.0–7.0 by 0.1 on `soros-1992`, holder at 25 C\*, with `exit_discount_pct` `null` and `10`, seed 42: the flip multiple in each; a `scripts/scan_1992.py` that does this (replacing the scratch scripts of 2.5/2.6/3.1; takes `--holder-capital`, `--exit`, `--range`), with a dry-run test
5. `plot_holder_exit(sweep_dir) -> Path`: left, heatmap of `p_reserves_exhausted` over exit × capital with the `null` column labelled "never sells"; right, mean reserves-exhausted step (or "not exhausted") and mean holder PnL as two small panels, one line per capital; reads parquet + manifest
6. Completion Notes answer, in one paragraph with numbers: at the largest holder, does the analogue exhaust *without* the holder selling? With it selling at which discount? Does the flip multiple move, and in which direction, when the holder can switch sides? What does the holder's PnL look like in the runs where reserves exhaust versus where they don't? Then one sentence on whether BACKGROUND §4's claim is supported, contradicted, or not testable at this size
7. A `Proposed` ADR: the exit rule semantics, the sweep, the verdict, and a finding candidate if the believer's exit decides the outcome
8. `make figures` with the new figure registered; guard green; `pytest` and `ruff check .` pass; both CI jobs green

## Tasks / Subtasks

- [x] Exit rule (AC: 1, 2)
  - [x] Config field + validator; `hold_exit`; tests; hash test
  - [x] Commit separately: `story 3.3: holder exit rule`
- [x] Sweep and scan (AC: 3, 4)
  - [x] `None` on an axis if needed; sweep spec; `scripts/scan_1992.py`; runs
- [x] Chart (AC: 5)
- [x] Verdict, ADR, figures, close out (AC: 6, 7, 8)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.3: holder exit rule and 1992 switch-sides test`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 3.2 (Status: done)**

- Every prediction in 3.2 missed; the mechanism (price paid) was what mattered. Below are
  predictions again, labelled as such.
- Name agents by what they do. The exit rule is "sells everything once"; the note will
  call it switching sides.
- `base_axis` exists now; not needed here (one base).

[Source: docs/stories/3-2-defender-policy-comparison.md#Senior-Developer-Review, F-12, F-13]

### Who this agent is now

F-12 showed the capped holder is a redeemer in waiting: it buys below par and redeems
whenever it can, and at 25 C\* it would be a second attacker on the redemption channel
even without selling. The exit rule adds the convergence trader's other move: dumping
sterling on the market once the peg looks lost. In the model that is a `sell_stable` on
the AMM, which pushes the price down (helps the attacker) and hands the holder reference
at the crashed price (it loses). The question is whether that sale is what exhausts the
reserves, or whether the redemption channel does it anyway.

### Why 25 C\* and why one-way

At C\* the holder is 3.6% of the attacker (ADR-0021) and cannot decide anything. 25 C\*
puts it at 0.9× the attacker — BACKGROUND §4's convergence traders were the larger pool of
capital. One-way because a believer who switches sides and then switches back is a
different agent (a momentum trader), and the note's claim is about belief breaking.

### Predictions (to be checked)

- At 25 C\* with `null` (never sells), reserves do **not** exhaust at 6×: the holder's
  redemptions compete with the arbitrageur's but its buying holds the price up.
- With exit at 10% or 20%, reserves exhaust earlier than without the holder at all (the
  dump adds to the attack).
- At 40% the holder never exits (the price never gets there at 6×), so that column equals
  `null`.
- The flip multiple at 25 C\* moves *down* with an exit rule (less attacker capital needed)
  and *up* without one.
- Holder PnL is negative in every run where it exits.

### Cost

5 × 3 × 8 = 120 runs at 14,400 steps plus 62 scan runs: a few minutes on 10 workers.

### References

- [Source: docs/epics.md#Story-3.3]
- [Source: docs/BACKGROUND.md#4-The-attackers] — the convergence trades
- [Source: docs/FINDINGS.md] — F-07 (+ refinements), F-08, F-12, F-13
- [Source: docs/adr/0021-par-expecting-holder.md, 0024-holder-fill-price-limit.md]

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-3-holder-exit-rule.context.xml)

### Agent Model Used

Claude Code, Opus 5.5 (`claude-opus-5-5`), on Seoul. Python 3.12.13 (uv venv).

### Debug Log References

Exit-rule commit `c61f0b6` (`story 3.3: holder exit rule`): `pytest` 599 passed; every
pinned scenario hash unchanged (`test_holder_config.py::test_every_scenario_hash_is_pinned_for_3_1`,
`test_1992_scenarios.py::test_content_hashes_are_pinned`); and

```
$ python run.py scenarios/soros-1992.yaml
depeg-sim: scenario=soros-1992 seed=42 hash=f4e26ae66440
run: steps=9553 terminated_by=reserves_exhausted max_depeg_bps=-5975.4 reserves_exhausted=True
```

(3.1: 9553, −5975.4: unchanged.)

**`None` on an axis.** `set_path` already set it (a leaf is validated through its parent
model); no code change, two tests in `test_set_path.py` and one in `test_sweep.py`:

```
$ python -c "...set_path(b,'agents[type=holder].exit_discount_pct',10) ... then None"
10.0 False
None True          # value, hash == base
```

**Sweep** (12 workers):

```
$ time python -m depeg_sim.sweep sweeps/holder-exit-1992-mc.yaml --mc --workers 12
sweep: holder-exit-1992-mc cells=120 workers=12
wrote: output/holder-exit-1992-mc/sweep.parquet
mc: holder-exit-1992-mc grid_points=15 seeds=8 runs=120
wrote: output/holder-exit-1992-mc/mc.parquet
real	0m17.588s
```

```
 exit  capital    n p_exh p_max  steps_run_mean steps_run_p50 holder_pnl_mean  holder_pnl_p05  holder_pnl_p95 max_depeg_p50
  5.0   9166667   8  1.0  0.0        9,541.5       9,552.0    -3,306,715.9    -3,314,684.7    -3,282,781.7      -6,488.9
  5.0  45833335   8  1.0  0.0        9,552.9       9,563.0   -33,877,978.8   -33,878,231.2   -33,877,815.5      -9,322.0
  5.0 229166675   8  1.0  0.0        9,656.4       9,658.5       566,420.0       344,486.6       950,528.5        -256.2
 10.0   9166667   8  1.0  0.0        9,541.5       9,552.0    -3,635,566.5    -3,643,129.4    -3,612,852.2      -6,524.4
 10.0  45833335   8  1.0  0.0        9,552.9       9,563.0   -34,303,065.3   -34,304,477.3   -34,302,565.6      -9,332.3
 10.0 229166675   8  1.0  0.0        9,656.4       9,658.5       566,420.0       344,486.6       950,528.5        -256.2
 20.0   9166667   8  1.0  0.0        9,541.5       9,552.0    -4,162,619.8    -4,174,386.3    -4,158,704.7      -6,615.7
 20.0  45833335   8  1.0  0.0        9,552.9       9,563.0   -35,136,955.0   -35,140,747.2   -35,135,671.8      -9,353.7
 20.0 229166675   8  1.0  0.0        9,656.4       9,658.5       566,420.0       344,486.6       950,528.5        -256.2
 40.0   9166667   8  1.0  0.0        9,541.5       9,552.0    -5,227,122.6    -5,231,700.3    -5,225,600.5      -7,109.6
 40.0  45833335   8  1.0  0.0        9,564.5       9,565.5       492,606.9       237,007.4       862,157.9      -2,794.3
 40.0 229166675   8  1.0  0.0        9,656.4       9,658.5       566,420.0       344,486.6       950,528.5        -256.2
  NaN   9166667   8  1.0  0.0        9,541.5       9,552.0       152,267.7       108,824.9       208,599.0      -5,975.4
  NaN  45833335   8  1.0  0.0        9,564.5       9,565.5       492,606.9       237,007.4       862,157.9      -2,794.3
  NaN 229166675   8  1.0  0.0        9,656.4       9,658.5       566,420.0       344,486.6       950,528.5        -256.2
```

(NaN = never sells. `p_peg_recovered` 0 everywhere.) Which runs exited (trough below the
exit price) and their PnL:

```
exit  capital    n_exited  pnl_max          exit  capital    n_exited  pnl_max
5.0   9166667    8   -3.282684e+06          20.0  9166667    8   -4.158704e+06
      45833335   8   -3.387778e+07                45833335   8   -3.513567e+07
      229166675  0    9.600030e+05                229166675  0    9.600030e+05
10.0  9166667    8   -3.612763e+06          40.0  9166667    8   -5.225600e+06
      45833335   8   -3.430256e+07                45833335   0    8.741948e+05
      229166675  0    9.600030e+05                229166675  0    9.600030e+05
exited runs 56 all pnl<0: True not exited pnl>0: True
```

Diagnostic, holder removed from `soros-1992`, 6×, seeds 1000–1007: 8/8
`reserves_exhausted`, mean steps_run 9541.0.

**Scan** (`scripts/scan_1992.py`, seed 42, 4.0–7.0 by 0.1, 12 workers; 5.5–6.4 s wall
each). Reproduction first, C\*, never sells: identical to the 3.1 table row for row
(5.0 → 14287, 5.1 `max_steps`, 5.2 → 10506, … 5.7 → 9663, 6.0 → 9553):

```
$ time python scripts/scan_1992.py --workers 12
flip: 5.2 (ratio 1.101)
exhausted below the flip: 5
real	0m6.399s
```

25 C\*, never sells, then exit 10 (the two tables are identical row for row):

```
$ python scripts/scan_1992.py --holder-capital 229166675 --exit none --workers 12   # real 0m5.463s
 multiple ratio      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  redemption_paid_total  holder_bought_stable  holder_pnl
      4.0 0.847          max_steps      14400         -225.2           -198.8           65,059,664.2          19,604,984.1    30,547.6
      4.4 0.931          max_steps      14400         -231.4           -149.4           81,575,770.5          29,530,966.0    54,849.1
      4.8 1.016          max_steps      14400         -237.7           -143.6           97,916,030.4          37,408,603.2    72,088.8
      4.9 1.037 reserves_exhausted      13046         -239.2           -150.5          100,703,325.0          39,421,215.9    79,003.8
      5.0 1.058 reserves_exhausted      10836         -240.8           -119.9          100,703,325.0          41,570,605.8    87,093.7
      5.2 1.101 reserves_exhausted      10021         -243.8           -162.7          100,703,325.0          45,715,654.3   122,876.6
      5.7 1.206 reserves_exhausted       9776         -251.6           -146.0          100,703,325.0          57,660,536.1   292,339.9
      6.0 1.270 reserves_exhausted       9659         -256.2           -132.8          100,703,325.0          65,745,974.3   449,735.1
      7.0 1.481 reserves_exhausted       9348         -271.6           -123.7          100,703,325.0          94,934,329.7   992,149.3
flip: 4.9 (ratio 1.037)
exhausted below the flip: none
$ python scripts/scan_1992.py --holder-capital 229166675 --exit 10 --workers 12     # real 0m5.800s
flip: 4.9 (ratio 1.037)
exhausted below the flip: none
```

(Rows abridged here; 4.0–4.8 all `max_steps`, 4.9–7.0 all exhausted; full tables
reproduce with the commands.) Diagnostic scans, same command shape:

```
C* exit 5 / 10 / 20      flip: 5.7 (ratio 1.206)   exhausted below the flip: 5.1, 5.2
5 C* never / exit 10     flip: 4.9 (ratio 1.037)   exhausted below the flip: none
25 C* exit 2.5           flip: 5.7 (ratio 1.206)   exhausted below the flip: 4.9, 5, 5.1, 5.2, 5.3, 5.4, 5.5
25 C* exit 2.2           flip: 5.7 (ratio 1.206)   exhausted below the flip: 5.1, 5.2
no holder (scratch)      no-holder flip (5.7, [5.1, 5.2])
```

Who redemption pays (scratch, seed 42, `redeem_fulfilled` by source):

```
5.4x cap 9,166,667 exit None: reserves_exhausted step 11474 trough -5041 pnl 47,912 paid arb-1 91,485,616, holder-1 9,217,709
5.4x cap 9,166,667 exit 10: max_steps step 14400 trough -6182 pnl -3,658,796 paid arb-1 89,901,674, holder-1 3,170
6.0x cap 9,166,667 exit None: reserves_exhausted step 9553 trough -5975 pnl 126,437 paid arb-1 100,691,106, holder-1 12,219
6.0x cap 9,166,667 exit 10: reserves_exhausted step 9553 trough -6526 pnl -3,612,850 paid arb-1 100,691,106, holder-1 12,219
5.0x cap 229,166,675 exit None: reserves_exhausted step 10836 trough -241 pnl 87,094 paid arb-1 59,973,506, holder-1 40,729,819
6.0x cap 229,166,675 exit None: reserves_exhausted step 9659 trough -256 pnl 449,735 paid arb-1 71,769,676, holder-1 28,933,649
5.6x cap 229,166,675 exit 2.5: max_steps step 14400 trough -5875 pnl -9,410 paid arb-1 98,204,836, holder-1 4,964
```

Exit timing vs the defender (seed 42, first holder `sell_stable`, last defender swap):

```
9166667 5 last defender swap 2335 exit swap 2493
9166667 40 last defender swap 2335 exit swap 2682
45833335 10 last defender swap 2335 exit swap 4519
229166675 2.5 last defender swap 2483 exit swap 2368   (5.6x)
```

**Figures** (inputs committed first as `1d74b24`, so the manifest records a clean commit;
a scratch diagnostic shared the cores for part of this run):

```
$ make figures
...
sweep: holder-exit-1992-mc cells=120 workers=12
...
drew: holder_exit.png <- sweeps/holder-exit-1992-mc.yaml
wrote: 12 figures and docs/figures/manifest.json (commit 1d74b24ebdd6)
make figures: wall time 529 s (12 workers)
$ make figures-check
python scripts/check_figures.py
figures-check: ok, 12 figures match their sources
```

**Tests and lint:**

```
$ pytest
608 passed in 10.06s
$ ruff check .
All checks passed!
$ ruff format --check .
90 files already formatted
$ python -c "import depeg_sim.kernel.scheduler as s; print(s.PHASE_ORDER_VERSION)"
1
$ git diff --stat 14ce26c -- src/depeg_sim/kernel src/depeg_sim/protocol
 src/depeg_sim/kernel/config.py | 22 ++++++++++++++++++++--
```

### Completion Notes List

**Verdict (AC 6).** At the largest holder (25 C\*, 0.90× the attacker) the 1992 analogue
exhausts reserves *without* the holder selling: 8 of 8 seeds at 6×, at mean step 9,656
(32.2 h), 115 steps *later* than with no holder at all (9,541). With it selling it never
gets the chance: the holder's own buying holds the trough at −256 bps (−225 … −272 across
the 4.0–7.0 scan), so no exit price of 5%, 10%, 20% or 40% is ever reached and every exit
column equals "never sells". Where the exit does fire (1× C\* at every discount, 5× C\*
at 5–20%) it changes nothing about the outcome at 6×: p = 1.00 and the exhaustion step
moves by at most 12 steps, because exhaustion at 6× is the redemption channel's capacity
clock (100.7M at 13,987/step = 7,200 steps after the queue saturates). The flip multiple
moves, and in the direction opposite to the claim: a believer who never sells moves it
*down*, from 5.7× (ratio 1.206) with no holder to 5.2× at C\* and 4.9× (1.037) at 5 and
25 C\*; a believer who switches sides moves it back *up* to 5.7× (C\* with exit 5/10/20;
25 C\* with a diagnostic 2.5% exit), the no-holder boundary. At 25 C\* with exit 10 the
flip is 4.9×, identical to never-sells, because the exit is never reached. The reason is
that an AMM sale is not a claim on reserves (the pool absorbs it as price: −5,975 →
−6,526 bps at 6× C\*, arbitrageur payout unchanged at 100,691,106), while a believer who
stays redeems at the floor without a profit threshold and supplies the redemption demand
that drains the F-07 residual (at 5.4× C\*: 9.2M paid to the staying holder and
exhaustion, 3k to the exited one and a stall; at 25 C\* the holder is paid 29–41M of the
100.7M). Holder PnL: every run that exits loses (56 of 56: −3.3M … −5.2M at C\*, −33.9M …
−35.1M at 5 C\*, i.e. 36–57% and 74–77% of capital); every run that does not exit gains,
and gains more where reserves exhaust than where they don't (25 C\* scan: +79k … +992k in
the exhausting 4.9–7.0 runs vs +31k … +72k in the stalled 4.0–4.8 runs; sweep: +152k /
+493k / +566k at 1/5/25 C\*, all exhausting). There is no non-exhausting cell in the
sweep to compare against. **BACKGROUND §4's claim is contradicted in this model: the
analogue breaks without the believer switching sides, and switching sides raises the
attack needed to break it — the belief that drains the reserves is the one that holds
and redeems.**

**Flip table (seed 42, 4.0–7.0 by 0.1).**

| holder | exit | flip | ratio | exhausts below flip |
|---|---|---|---|---|
| none (diagnostic) | – | 5.7 | 1.206 | 5.1, 5.2 |
| C\* | never | 5.2 | 1.101 | 5.0 |
| C\* | 5 / 10 / 20 (diagnostic) | 5.7 | 1.206 | 5.1, 5.2 |
| 5 C\* | never / 10 (diagnostic) | 4.9 | 1.037 | none |
| **25 C\*** | **never** | **4.9** | **1.037** | none |
| **25 C\*** | **10** | **4.9** | **1.037** | none (exit never reached) |
| 25 C\* | 2.5 (diagnostic) | 5.7 | 1.206 | 4.9–5.5 |
| 25 C\* | 2.2 (diagnostic) | 5.7 | 1.206 | 5.1, 5.2 |

**Predictions checked.**
1. *25 C\*, never sells, does not exhaust at 6×* — **missed.** 8/8 exhaust at mean step
   9,656. Its buying does hold the price (−256 bps), but it redeems what it buys and is
   paid 29M of the reserves.
2. *Exit at 10/20% exhausts earlier than with no holder* — **missed.** 1× C\*: 9,541.5 vs
   9,541.0 with no holder; 5× C\*: 9,552.9 (later). At 25 C\* the exit never fires.
3. *At 40% the holder never exits; column equals never-sells* — **held at 5× and 25 C\*,
   missed at 1× C\*:** there the trough reaches −5,975 bps (spot ≈ 0.40), below 0.60, so it
   exits in all 8 seeds (PnL −5.2M; trough −7,110 including its own sale);
   p_exhausted and the exhaustion step still equal never-sells.
4. *Flip at 25 C\* moves down with an exit and up without* — **missed, both halves:**
   without an exit it moves down (5.2 → 4.9); with exit 10 it does not move relative to
   never-sells (the exit is not reached), and with an exit that fires (2.5%, diagnostic)
   it moves up (to 5.7).
5. *Holder PnL negative in every run where it exits* — **held:** 56/56 exiting sweep runs
   negative, and every exiting row of the 2.5% scan (−19.7 … −9,410).

**Chart in words** (`docs/figures/holder_exit.png`). Left: a 3 × 5 heatmap of
p(reserves exhausted), holder capital (1×, 5×, 25× C\*; $2.15B / $10.75B / $53.76B; 0.04 /
0.18 / 0.90× the attacker) against exit rule ("never sells", −5, −10, −20, −40%): every
cell is the darkest blue, 1.00. Top right: mean hours to exhaustion, one line per capital,
three flat lines at 31.8–32.2 h far below the 48 h "not exhausted" line; selling does not
move the clock. Bottom right: mean holder PnL ($B, p05–p95 band): the 25× line sits just
above zero across all exits (never reached); the 1× line drops to −$0.8 … −$1.2B for every
exit; the 5× line falls to about −$8B at 5–20% and comes back to +$0.12B at −40%, which is
never reached.

**Judgment calls** (ADR-0026 Proposed):
- "Sells all stable it holds" while "cancelling nothing queued" is implemented as selling
  `available_stable` (held and not queued); the queued tranche is still paid and settles.
  Selling the queued part too would sell stable already committed to redemption.
- `hold_exit` takes priority over every other rule; an exit with ≤ DUST to sell records
  `hold_exit` with no action and still sets `exited`.
- `content_hash()` drops `exit_discount_pct` when `None`, and observation/snapshot gain
  exit fields only when the rule is configured, so outputs of existing scenarios are
  byte-identical, not just their hashes.
- `scan_1992.py` defines the flip as the smallest multiple from which every larger one
  exhausts, and lists isolated exhaustions below it separately (this matches how 3.1
  reported 5.2 with 5.0 isolated).
- The diagnostics (no holder; C\* and 5 C\* with exits; 25 C\* with 2.5% and 2.2% exits)
  are not in the committed sweep. They were run because the specified 25 C\* exits are
  never reached, so the specified runs alone could not answer "does switching sides
  matter"; they are scan commands or scratch scripts and are labelled as such.

**Finding candidate** (ADR-0026 §Consequences): the believer does not have to switch sides
for the 1992 analogue to break; the believer who stays and redeems breaks it at a lower
multiple, and one who switches returns it to the no-holder boundary. Caveat in the ADR: in
the model only redemption reaches reserves, while in 1992 sterling sold to the Bank did;
a large believer turning while the defender still has budget is untested.

**ADR:** [0026](../adr/0026-holder-exit-rule-and-switch-sides-test.md) (Proposed; index
not edited).

**Scope:** no kernel/ or protocol/ changes beyond `config.py`; `PHASE_ORDER_VERSION` 1;
every existing scenario hash unchanged; nothing from CHARTER §4 Out.

### File List

**Created:**
- `sweeps/holder-exit-1992-mc.yaml`
- `scripts/scan_1992.py`
- `docs/figures/holder_exit.png`
- `docs/adr/0026-holder-exit-rule-and-switch-sides-test.md`

**Modified:**
- `src/depeg_sim/kernel/config.py` — `HolderConfig.exit_discount_pct`, validator, hash rule
- `src/depeg_sim/agents/holder.py` — `hold_exit`, `exited`, `sold_stable`, `exit_price`
- `src/depeg_sim/analysis/charts.py` — `plot_holder_exit`
- `scripts/make_figures.py`, `Makefile` — registered the figure and its sweep
- `docs/figures/README.md`, `docs/figures/manifest.json` — row, caption, timing; regenerated
- `tests/test_holder.py`, `tests/test_holder_config.py`, `tests/test_set_path.py`,
  `tests/test_sweep.py`, `tests/test_charts.py`, `tests/test_scripts.py`,
  `tests/test_figures.py`
- `docs/stories/3-3-holder-exit-rule.md`

## Change Log

- 2026-10-05: Story drafted by dev manager after Story 3.2 review
- 2026-10-06: Implemented by builder (Claude Code, Opus 5.5): exit rule (separate commit,
  hashes unchanged); sweep (120 runs, 17.6 s); `scan_1992.py` (reproduces 3.1's 5.2 flip);
  25 C\* flip 4.9 with and without exit 10 (exit never reached); diagnostics show switching
  sides raises the flip to the no-holder 5.7; verdict: BACKGROUND §4 contradicted in the
  model; figure registered, `make figures` 529 s; ADR-0026 Proposed. Status review
