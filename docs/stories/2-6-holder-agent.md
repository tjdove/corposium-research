# Story 2.6: Par-Expecting Buyer Agent

Status: done

## Story

As a **researcher**,
I want an agent that buys the discounted stablecoin because it expects redemption at par,
so that the replay can reproduce the observed trough and the note can say what decided March 2023.

## Acceptance Criteria

1. `src/depeg_sim/agents/holder.py`: `Holder(agent_id, capital, entry_discount_pct, pace, redeem_when_capacity)` extending `Agent`; starts `balances = {stable: 0, reference: capital}`; each step: if `amm.spot_price < 1 − entry_discount_pct/100` and `reference > 0` → `swap buy_stable` with `pace × reference_balance` (rule `hold_buy`); else if `redeem_when_capacity` and `stable > 0` and `redemption.queue_depth == 0` → `redeem` `min(stable, redemption.capacity_per_step × redeem_horizon_steps)` (rule `hold_redeem`; **amended 2026-10-04, see Rulings**); else if `stable > 0` → `hold_wait`; else `hold_done`; never sells on the AMM
2. `HolderConfig(type: "holder", id, capital gt 0, entry_discount_pct ge 0, pace gt 0 le 1, redeem_when_capacity: bool = True)` added to `config.py` and the `AgentConfig` discriminated union; `build_agents` dispatches it; every existing scenario's `content_hash()` unchanged (test)
3. Holder unit tests mirror 1.7's pattern (real AMM/oracle/redemption, manual phases): waits above the discount; buys below it at `pace`; redeems only when the queue is empty and capacity suffices; `hold_done` once out of both; PnL positive after a full buy-then-redeem-at-par cycle; one decision record per step when tracing
4. `scripts/fit_holder.py`: on `scenarios/usdc-2023.yaml` with D\* fixed, adds a holder (`entry_discount_pct 2.0`, `pace 0.05`, `redeem_when_capacity true`) and sweeps `capital` over `[1M, 2M, 5M, 10M, 20M, 50M, 100M]` model units, picks the value whose `max_depeg_bps` is closest to −1,373, refines with 5 points between the neighbours, **then refines once more with 5 points between the new neighbours** (amended 2026-10-04), prints the table and `C* = … (trough …)` and the dollar figure at `s`; `--dry-run` supported
5. `scenarios/usdc-2023.yaml` gains the fitted holder (`status: assumption, fitted to observed trough, this story`); replay re-run; overlay regenerated; `docs/calibration/VALIDATION.md` gains a **before/after** table (2.5 vs 2.6: trough depth, trough time, last-outside-band, recovery direction) and a paragraph on what the buyer fixed and what it didn't
6. `SOURCES.md` gains a holder section: `capital` (assumption, fitted, with the dollar figure next to the episode net burn and the $9.7B cash figure for scale), `entry_discount_pct` and `pace` (assumption, reasoning), `redeem_when_capacity` (assumption: the weekend buyers redeemed once Circle reopened)
7. `scenarios/calibrated-baseline.yaml`, `calibrated-stress.yaml`, `soros-1992.yaml`, `soros-1992-no-defense.yaml` each gain a holder at the **same capital-to-depth ratio** as the replay (`C* / D*`); all four re-run; outcomes before/after in Completion Notes; the 1992 flip re-scanned (4.0–7.0 by 0.1); `scripts/probe_boundary.py` re-run on the calibrated baseline
8. A `Proposed` ADR: holder semantics, `C*` in three units, and what moved in F-06 (boundary) and F-07 (1992 flip, dead zone) with the buyer present; a finding write-up in Completion Notes if the buyer changes which actor decides the outcome
9. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Config and factory (AC: 2)
  - [x] `HolderConfig`; union; `build_agents`; hash-stability test (`build_agents` branch
    landed with the agent in the second commit: it needs the `Holder` class)
  - [x] Commit separately: `story 2.6: holder config`

- [x] Agent (AC: 1, 3)
  - [x] `agents/holder.py`; `tests/test_holder.py`

- [x] Fit (AC: 4, 5, 6)
  - [x] `scripts/fit_holder.py`; run; `C*`
  - [x] Update `usdc-2023.yaml`; re-run; overlay; `VALIDATION.md` before/after; `SOURCES.md` holder section
  - [x] Look at the new overlay and describe it

- [x] Propagate (AC: 7)
  - [x] Add holder to the four scenarios at `C*/D*`; re-run all; re-scan 1992; re-probe

- [x] ADR, tests, close out (AC: 8, 9)
  - [x] Proposed ADR; `tests/test_scripts.py` dry-run for `fit_holder.py`
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.6: par-expecting buyer agent`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.5 (Status: done)**

- The replay fell to −5,769 bps vs −1,373 observed because nothing in it buys the discount.
  D\* was fitted with the defender absorbing 89% of the attack; the replay correctly has no
  defender. This story adds the missing counterparty and re-fits *its* size with D\* held.
- Fit rule discipline: one parameter, one observation, log grid then 5-point refinement,
  closest wins, no hand-picking. Same as `fit_depth.py`.
- Post-63 h agreement in the overlay is the oracle following the input; judge the fit on
  the trough and the plateau, not the tail.
- F-06 refinement: budget absorbs more than face value in a shallow pool. The holder will
  do the same; expect the probe boundary to move again.

[Source: docs/stories/2-5-usdc-validation.md#Senior-Developer-Review, docs/FINDINGS.md F-08]

### Who this agent is

The spec's "holder" family: "preserve value; passive under stability; sell under depeg."
Ours is the mirror image, the holder who *buys* under depeg because the redemption
promise makes discounted stable worth par to anyone with the patience to redeem. In March
2023 these were market makers, hedge funds and treasuries; in 1992, before their belief
broke, they were the convergence traders (BACKGROUND §4). Name the class `Holder` to keep
the spec's taxonomy; the sign is a parameter choice (`entry_discount_pct > 0` means "buy
below"), and a future panic-seller is the same class with a sell rule.

### Redeem condition

The holder should not redeem into a queue it can't clear (it would just sit behind the
arbitrageur). **Rule (amended 2026-10-04, replaces the original):** when `queue_depth == 0`
and `stable > 0`, redeem `min(stable, capacity_per_step × redeem_horizon_steps)`, with
`redeem_horizon_steps` a constructor default of 10 (not a config field; `HolderConfig`
keeps its four fields). The holder redeems in tranches the channel can pay within ~10
steps, re-queuing each step the queue is clear. The original rule
(`capacity ≥ redeem_fraction_min × stable`) scaled the condition to the holder's own
balance, so a large holder could never redeem; that was a drafting error, see Blockers
and Rulings. `redeem_fraction_min` is removed.

Before the capacity schedule fires in the replay, capacity is 605.79/step, so over the
weekend the holder can redeem at most ~6,058 per clear-queue step against a balance in the
millions; the bulk is paid out after the Monday capacity change. That is the March-2023
story. Report how much the holder redeems before and after the schedule fires.

### Expected fit

Holder capital on the order of the episode net burn (11.5M model units ≈ $2.7B) would
absorb the whole attack and flatten the trough; capital of ~2–5M should land near −1,373.
If `C*` comes out above the attack size, the buyer alone explains the trough and the F-08
claim is confirmed quantitatively; say so.

### What to watch in the propagation (AC 7)

- Calibrated baseline: the defender's spend should fall (the holder absorbs first at the
  2% discount, the defender triggers at 1%). Record both.
- 1992: the holder is the convergence trader *before* the belief breaks. With it present,
  reserves may no longer exhaust at 6×; that would be the model saying "the convergence
  traders had to switch sides for Black Wednesday to happen," which is BACKGROUND §4's
  claim. Record the flip and the holder's PnL (it loses if reserves exhaust before it
  redeems).

### References

- [Source: docs/epics.md#Story-2.6]
- [Source: docs/adr/0020-episode-flow-replay-and-capacity-schedule.md] — amendment
- [Source: docs/FINDINGS.md] — F-03, F-06 refinement, F-07, F-08
- [Source: docs/BACKGROUND.md#4-The-attackers] — convergence trades
- [Source: docs/stories/1-7-agents.md] — agent pattern and tests

## Blockers

**2026-10-04 — the normative redeem condition contradicts the intended behaviour; at C\*
the holder can never redeem in any of the five scenarios.**

The Dev Notes make the redeem rule normative (context XML: "The redeem condition and fit
rule in Dev Notes are normative"): redeem only when `queue_depth == 0` and
`capacity_per_step >= redeem_fraction_min × stable`, default `redeem_fraction_min = 0.1`.
The same section says the holder "will wait (`hold_wait`) all weekend and redeem Monday.
That is the intended behaviour and it is the March-2023 story." Both cannot hold at the
fitted size.

**What I ran.** `python scripts/fit_holder.py --workers 8` (full table in Debug Log) gives
**C\* = 10,000,000** model units (trough −1,052.1 bps; ≈ $2.346B at `s`; 0.87× the
attacker's 11,540,596 episode net burn). In the replay at C\* the holder spends all its
capital between steps 8117 and 9959 (719 buys) and ends holding **10,068,775 stable**. The
rule needs `capacity ≥ 0.1 × stable`, so the largest balance it can ever redeem is
`capacity / 0.1`:

| scenario | holder capital at C\*/D\* | capacity per step | largest redeemable balance |
|---|---|---|---|
| usdc-2023 (weekend → Monday) | 10,000,000 | 605.79 → 19,181.59 | 6,058 → 191,816 |
| calibrated-baseline / -stress | 10,000,000 | 605.79 | 6,058 |
| soros-1992 / -no-defense | 10,000,000 | 13,986.57 | 139,866 |

(All four propagated scenarios sit at D\* = 16,666,667, so `C* × depth / D*` = 10,000,000
in each.) At C\* the holder never redeems anywhere: `redeem_when_capacity` is inert, it
holds ~10.07M stable to `max_steps` in every scenario, and the Monday redemption the story
describes does not happen.

**Diagnostic (in-process override, not committed): what the choice changes.**
`redeem_fraction_min` overridden to 0.001 on the same runs:

| run | `redeem_fraction_min` | trough (step) | final | holder redeem requests | holder paid | holder PnL (mark-to-market) |
|---|---|---|---|---|---|---|
| usdc-2023 | 0.1 | −1,052.1 (10361) | −27.3 | none | 0 | 41,307 |
| usdc-2023 | 0.001 | −1,052.1 (10361) | −27.3 | step 25501: 10,068,775 | 10,068,775 | 68,775 |
| soros-1992 | 0.1 | −6,029.2 (3302) | −143.1, reserves exhausted | none | 0 | −77,592 |
| soros-1992 | 0.001 | −5,932.1 (3377) | −144.3, reserves exhausted | from step 2202 | 6,573,268 | 819,796 |

So **C\* itself does not depend on the redeem rule** (the trough is identical: nothing the
holder holds is redeemable at weekend capacity either way). The replay's post-Monday path
is also identical. What depends on it is AC 7: in 1992 the holder either sits on its stable
(and loses when reserves exhaust) or redeems during the attack, competes with the
arbitrageur for reserves, and profits. That is exactly the "does the buyer change who
decides 1992" question AC 7 and AC 8 ask, so I can't pick the rule myself.

**Options I can see (dev manager's call):**
1. Keep the rule as written (`0.1`). The holder is a pure absorber that never redeems at
   fitted size; drop the "redeem Monday" expectation from the story and VALIDATION text.
2. Lower the default `redeem_fraction_min` (e.g. 0.001, ~1,000 steps ≈ 3.3 h to pay out).
   Gives the Monday redemption in the replay; changes 1992 as above.
3. Change the rule's shape, e.g. redeem when the queue is empty, sized to what the channel
   can pay soon (`min(stable, capacity × N)`), rather than all-or-nothing. A new rule;
   needs AC 1 amended.

**Other things the dev manager should see before deciding** (facts from the fit, not
blockers):
- The fit misses the target by 321 bps (−1,052.1 vs −1,373). The trough is a cliff in
  capital: 7.5M → −2,206.7, 10M → −1,052.1, 12.5M → −215.8 (once the holder can absorb the
  attack, the price stops at about its 2% entry). The AC 4 refinement (5 points between the
  pick's neighbours 5M and 20M) lands on 7.5M, 10M (the pick again), 12.5M, 15M, 17.5M, so
  it does not resolve the 7.5M–12.5M cliff. The rule was applied as written; C\* = 10M.
- Trough timing moves from 31.6 h (2.5) to 34.5 h (step 10361) with the holder: outside
  2.5's ±2 h target. Pace is not re-fitted (out of scope).
- C\* < attack size (0.87×), so per the Dev Notes the buyer alone does not explain the
  trough by that test.

**Done so far:** `HolderConfig` + hash-stability test (commit `957cec2`); `Holder` agent,
factory branch, `tests/test_holder.py`, `scripts/fit_holder.py` + dry-run test (next
commit). `pytest`: 494 passed; `ruff check .` and `ruff format --check .` clean.
**Not done (waiting on the ruling):** scenario YAML changes, replay re-run, overlay,
VALIDATION.md / SOURCES.md, propagation, 1992 re-scan, probe, ADR.

## Rulings

**2026-10-04 (dev manager), on the Blockers above.**

1. **Redeem rule → option 3.** The balance-scaled threshold was a drafting error: it made a
   holder's willingness to redeem depend on its own size, and at C\* it made
   `redeem_when_capacity` dead code. Replace with the tranche rule now in AC 1 and Dev
   Notes: when the queue is empty, redeem `min(stable, capacity_per_step × 10)`. Rename the
   constructor default `redeem_fraction_min` → `redeem_horizon_steps = 10`. Update
   `tests/test_holder.py` accordingly (a large holder with an empty queue redeems one
   tranche per step; a non-empty queue → `hold_wait`). Whatever this does to 1992 is the
   answer to AC 7/8, not a problem to tune away: if the holder redeeming mid-attack
   starves the arbitrageur or brings exhaustion forward, record it; that is the
   "convergence traders switch sides" mechanism from BACKGROUND §4 appearing in the model.
2. **Fit miss and the cliff → one more refinement pass, then accept.** AC 4 amended: after
   the first 5-point refinement, refine again with 5 points between the new neighbours
   (here 7.5M–12.5M). Take whatever is closest to −1,373 and stop. Do not hand-pick. The
   cliff itself (7.5M → −2,207, 10M → −1,052, 12.5M → −216) is a model observation: a
   buyer with a single entry price makes depth bimodal — attacker-set when the buyer is
   exhausted, buyer-set (≈ entry discount) when it isn't — and the real trough sits
   between the modes. Write this up in the Proposed ADR as a finding candidate ("real
   buyers entered at a spread of prices; a single `entry_discount_pct` cannot land on
   −1,373 exactly"). It is the natural motivation for a later multi-tranche holder; do
   not build that here.
3. **Trough timing 31.6 h → 34.5 h → record, do not re-fit pace.** Put both in the
   VALIDATION.md before/after table with the ±2 h target and state that pace was fitted
   without the holder in 2.5.
4. **C\* < attack size → record as stated.** The Dev Notes' "above the attack size" test
   was a crude proxy; the better statement is in the ADR: C\* in model units, dollars,
   and as a fraction of the attacker's episode net burn, with the holder's absorbed volume
   next to the defender's share from the calibrated baseline.
5. **`build_agents` branch in the agent commit, not the config commit → accepted.** Right
   call; the commit split was mine.

Resume at the Fit task: re-run `fit_holder.py` under the amended AC 4 (the rule change
should not move the trough; confirm), then continue to Propagate, ADR, close out as
written. Set `Status: review` when done. Builder report should include the holder's
redeemed volume before/after the capacity change in the replay, and in 1992 the holder's
PnL, the arbitrageur's redeemed volume with and without the holder, and the step at which
reserves exhaust.

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-6-holder-agent.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul

### Debug Log References

_(real command output; fit table, replay CLI lines before/after, four propagated runs, 1992 re-scan, probe)_

**Pre-ruling (original redeem rule, one refinement pass; superseded).** `python scripts/fit_holder.py --workers 8` (real 0m6.742s):

```
fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 entry_discount_pct=2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,455.3               9524     max_steps      33600
        2000000       -5,108.7               9560     max_steps      33600
        5000000       -3,784.8               9681     max_steps      33600
       10000000       -1,052.1              10361     max_steps      33600
       20000000         -219.6               8163     max_steps      33600
       50000000         -210.7               8231     max_steps      33600
      100000000         -210.5               8116     max_steps      33600

refine pass between 5,000,000 and 20,000,000 (grid pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -2,206.7               9793     max_steps      33600
       10000000       -1,052.1              10361     max_steps      33600
       12500000         -215.8               8205     max_steps      33600
       15000000         -215.8               8262     max_steps      33600
       17500000         -214.6               8157     max_steps      33600

C* = 10000000 (trough -1052.1 bps) ≈ $2,346,000,000 at s = 0.0042625746 units/$
```

Checks before blocking: `pytest` → `494 passed in 6.06s` (exit=0); `ruff check .` → `All checks passed!`; `ruff format --check .` → `83 files already formatted` (exit=0).


**Post-ruling (tranche redeem rule, two refinement passes).** `python scripts/fit_holder.py --workers 8` (real 0m9.896s):

```
fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 entry_discount_pct=2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,455.3               9524     max_steps      33600
        2000000       -5,108.7               9560     max_steps      33600
        5000000       -3,784.8               9681     max_steps      33600
       10000000         -224.6               8140     max_steps      33600
       20000000         -219.6               8163     max_steps      33600
       50000000         -210.7               8231     max_steps      33600
      100000000         -210.5               8116     max_steps      33600

refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -2,206.7               9793     max_steps      33600
       10000000         -224.6               8140     max_steps      33600
       12500000         -215.8               8205     max_steps      33600
       15000000         -215.8               8262     max_steps      33600
       17500000         -214.6               8157     max_steps      33600

refine pass 2 between 5,000,000 and 10,000,000 (pick 7,500,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        5833333       -3,316.8               9716     max_steps      33600
        6666667       -2,788.4               9754     max_steps      33600
        7500000       -2,206.7               9793     max_steps      33600
        8333333       -1,652.8               9829     max_steps      33600
        9166667       -1,137.8              10255     max_steps      33600

C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
```

Replay and the four propagated scenarios, **before** (current main, no holder) — `python run.py scenarios/<name>.yaml`:

```
depeg-sim: scenario=usdc-2023 seed=42 hash=73db527c8ddf
run: steps=33600 terminated_by=max_steps max_depeg_bps=-5768.5 reserves_exhausted=False
depeg-sim: scenario=calibrated-baseline seed=42 hash=0ef967d36e34
run: steps=7024 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
depeg-sim: scenario=calibrated-stress seed=42 hash=d7fe2f1626b8
run: steps=7225 terminated_by=peg_recovered max_depeg_bps=-1231.0 reserves_exhausted=False
depeg-sim: scenario=soros-1992 seed=42 hash=329eda7c2118
run: steps=9551 terminated_by=reserves_exhausted max_depeg_bps=-6332.2 reserves_exhausted=True
depeg-sim: scenario=soros-1992-no-defense seed=42 hash=1badaed6cf4a
run: steps=7806 terminated_by=reserves_exhausted max_depeg_bps=-7800.9 reserves_exhausted=True
```

**After** (holder at C\* × depth / D\* = 9,166,667):

```
depeg-sim: scenario=usdc-2023 seed=42 hash=2c3aeaa9825d
run: steps=33600 terminated_by=max_steps max_depeg_bps=-1137.8 reserves_exhausted=False
wrote: output/usdc-2023-42-2c3aeaa9
depeg-sim: scenario=calibrated-baseline seed=42 hash=44ac03c60e5f
run: steps=7024 terminated_by=peg_recovered max_depeg_bps=-1253.2 reserves_exhausted=False
wrote: output/calibrated-baseline-42-44ac03c6
depeg-sim: scenario=calibrated-stress seed=42 hash=17b24b458e47
run: steps=7225 terminated_by=peg_recovered max_depeg_bps=-1231.0 reserves_exhausted=False
wrote: output/calibrated-stress-42-17b24b45
depeg-sim: scenario=soros-1992 seed=42 hash=f4e26ae66440
run: steps=9550 terminated_by=reserves_exhausted max_depeg_bps=-5982.4 reserves_exhausted=True
wrote: output/soros-1992-42-f4e26ae6
depeg-sim: scenario=soros-1992-no-defense seed=42 hash=516edaef4795
run: steps=7807 terminated_by=reserves_exhausted max_depeg_bps=-7692.4 reserves_exhausted=True
wrote: output/soros-1992-no-defense-42-516edaef
```

Per-agent detail (scratch `holder_detail.py`, body below; in-process `build_world` + `Engine`, reads agent balances and `redeem_fulfilled` events), before:

```
== BEFORE calibrated-baseline
terminated_by: peg_recovered
steps_run: 7024
trough: -1253.2
trough_step: 50
final: -19.9
defender_spent: 10261333.654867772
paid_total: 299543.7250358083
exhausted_step: None
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -1008644, 'stable': 0, 'reference': 10531952}
arb-1: {'redeemed': 299544, 'paid': 299544, 'pnl': 44417, 'stable': 0, 'reference': 244417}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 939735, 'stable': 11223378, 'reference': 31085640}
== BEFORE calibrated-stress
terminated_by: peg_recovered
steps_run: 7225
trough: -1231.0
trough_step: 50
final: -3.7
defender_spent: 10261841.828275736
paid_total: 306114.13635428564
exhausted_step: None
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -1006948, 'stable': 0, 'reference': 10533648}
arb-1: {'redeemed': 306114, 'paid': 306114, 'pnl': 36337, 'stable': 0, 'reference': 236337}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 964241, 'stable': 11230280, 'reference': 31085132}
== BEFORE soros-1992
terminated_by: reserves_exhausted
steps_run: 9551
trough: -6332.2
trough_step: 3054
final: -138.8
defender_spent: 100703324.99999999
paid_total: 100703325.0000005
exhausted_step: 9550
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -57223030, 'stable': 14609587, 'reference': 184124668}
arb-1: {'redeemed': 102758495, 'paid': 100703325, 'pnl': 52858455, 'stable': 35980411, 'reference': 17577524}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 145237, 'stable': 102268246, 'reference': 0}
== BEFORE soros-1992-no-defense
terminated_by: reserves_exhausted
steps_run: 7806
trough: -7800.9
trough_step: 1391
final: -134.5
defender_spent: 0.9999999953683162
paid_total: 100703324.99999972
exhausted_step: 7805
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -134461491, 'stable': 25526853, 'reference': 96109524}
arb-1: {'redeemed': 100703325, 'paid': 100703325, 'pnl': 132347862, 'stable': 129396552, 'reference': 4891979}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 0, 'stable': 1, 'reference': 0}
```

after:

```
== AFTER calibrated-baseline
terminated_by: peg_recovered
steps_run: 7024
trough: -1253.2
trough_step: 50
final: -19.9
defender_spent: 6054985.772283431
paid_total: 4221809.9805236785
exhausted_step: None
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -753977, 'stable': 0, 'reference': 10786619}
arb-1: {'redeemed': 286598, 'paid': 286598, 'pnl': 31471, 'stable': 0, 'reference': 231471}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 506814, 'stable': 6574869, 'reference': 35291988}
holder-1: {'redeemed': 3935212, 'paid': 3935212, 'pnl': 198965, 'stable': 726228, 'reference': 8640848, 'spent': 4461031, 'bought': 4661440}
== AFTER calibrated-stress
terminated_by: peg_recovered
steps_run: 7225
trough: -1231.0
trough_step: 50
final: -3.7
defender_spent: 6055420.184413487
paid_total: 4344815.449785374
exhausted_step: None
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -752355, 'stable': 0, 'reference': 10788241}
arb-1: {'redeemed': 296321, 'paid': 296321, 'pnl': 26544, 'stable': 0, 'reference': 226544}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 518981, 'stable': 6576859, 'reference': 35291554}
holder-1: {'redeemed': 4048495, 'paid': 4048495, 'pnl': 201938, 'stable': 614704, 'reference': 8754131, 'spent': 4461031, 'bought': 4663199}
== AFTER soros-1992
terminated_by: reserves_exhausted
steps_run: 9550
trough: -5982.4
trough_step: 3337
final: -127.8
defender_spent: 100703324.99999999
paid_total: 100703325.00000116
exhausted_step: 9549
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -48019343, 'stable': 14614260, 'reference': 193307697}
arb-1: {'redeemed': 100347952, 'paid': 98347427, 'pnl': 43806836, 'stable': 26798273, 'reference': 17551143}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 256821, 'stable': 102267499, 'reference': 0}
holder-1: {'redeemed': 2377717, 'paid': 2355898, 'pnl': -64942, 'stable': 9219585, 'reference': 0, 'spent': 11522565, 'bought': 11597302}
== AFTER soros-1992-no-defense
terminated_by: reserves_exhausted
steps_run: 7807
trough: -7692.4
trough_step: 1543
final: -153.7
defender_spent: 0.9999999953683162
paid_total: 100703324.99999957
exhausted_step: 7806
attacker-1: {'redeemed': 0, 'paid': 0, 'pnl': -125359775, 'stable': 25518691, 'reference': 105268173}
arb-1: {'redeemed': 99864131, 'paid': 99864131, 'pnl': 122880277, 'stable': 120009216, 'reference': 4915323}
defender-1: {'redeemed': 0, 'paid': 0, 'pnl': 0, 'stable': 1, 'reference': 0}
holder-1: {'redeemed': 839194, 'paid': 839194, 'pnl': 67601, 'stable': 9378392, 'reference': 0, 'spent': 10005861, 'bought': 10217587}
```

replay after, redemptions split at the capacity change (step 25500):

```
holder-1: {'redeemed': 9497562, 'paid': 9497562, 'pnl': 82521, 'stable': 0, 'reference': 9249188, 'redeemed_before': 6693374, 'redeemed_after': 2804188, 'spent': 9415041, 'bought': 9497562}
arb-1: {'redeemed': 2019110, 'paid': 2019110, 'pnl': 127482, 'stable': 0, 'reference': 327482, 'redeemed_before': 1998260, 'redeemed_after': 20850}
```

Replay overlay comparison (`validation_comparison(output/usdc-2023-42-2c3aeaa9)`): simulated trough −1137.8 bps at 34.18 h; observed −1373.3 at 31.0 h; simulated last outside band 85.32 h (observed 95.0 h, censored); at the capacity change −52.2 (observed −36.4); first in band after the change 85.32 h (observed 86.0 h).

1992 multiple re-scan, `soros-1992` (scratch `scan1992_holder.py`, body below; 4.0..7.0 step 0.1, with and without the holder; the WITHOUT rows reproduce 2.5's table):

```
--- scenarios/soros-1992.yaml WITHOUT holder
 multiple  ratio      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  paid_total  arb_redeemed
      4.0    0.8          max_steps      14400       -2,260.2           -162.0    62876446      64159639
      4.1    0.9          max_steps      14400       -2,622.6           -161.7    65791866      67134557
      4.2    0.9          max_steps      14400       -2,962.3           -145.8    70786696      72231322
      4.3    0.9          max_steps      14400       -3,279.1           -144.3    72771832      74256971
      4.4    0.9          max_steps      14400       -3,571.9           -158.0    71312139      72767489
      4.5    1.0          max_steps      14400       -3,845.4           -163.6    79624783      81249779
      4.6    1.0          max_steps      14400       -4,098.5           -155.2    88097659      89895571
      4.7    1.0          max_steps      14400       -4,334.3           -150.9    78809330      80417684
      4.8    1.0          max_steps      14400       -4,553.5           -147.3    85261813      87001850
      4.9    1.0          max_steps      14400       -4,759.3           -152.2    91848124      93722576
      5.0    1.1          max_steps      14400       -4,950.8           -148.6    98470204     100479800
      5.1    1.1 reserves_exhausted      12676       -5,129.8           -146.9   100703325     102758495
      5.2    1.1 reserves_exhausted      13701       -5,298.4           -158.2   100703325     102758495
      5.3    1.1          max_steps      14400       -5,456.0           -157.2    85731538      87481161
      5.4    1.1          max_steps      14400       -5,604.4           -156.4    89879662      91713941
      5.5    1.2          max_steps      14400       -5,743.2           -146.0    94055424      95974922
      5.6    1.2          max_steps      14400       -5,874.8           -162.4    98209649     100213927
      5.7    1.2 reserves_exhausted       9662       -5,999.1           -147.1   100703325     102758495
      5.8    1.2 reserves_exhausted       9624       -6,116.6           -132.4   100703325     102758495
      5.9    1.2 reserves_exhausted       9587       -6,227.4           -122.2   100703325     102758495
      6.0    1.3 reserves_exhausted       9551       -6,332.2           -138.8   100703325     102758495
      6.1    1.3 reserves_exhausted       9518       -6,432.3           -133.8   100703325     102758495
      6.2    1.3 reserves_exhausted       9487       -6,527.7           -122.6   100703325     102758495
      6.3    1.3 reserves_exhausted       9455       -6,617.8           -146.6   100703325     102758495
      6.4    1.4 reserves_exhausted       9426       -6,704.5           -135.1   100703325     102758495
      6.5    1.4 reserves_exhausted       9396       -6,786.3           -129.3   100703325     102758495
      6.6    1.4 reserves_exhausted       9368       -6,864.7           -136.1   100703325     102758495
      6.7    1.4 reserves_exhausted       9342       -6,939.8           -149.6   100703325     102758495
      6.8    1.4 reserves_exhausted       9316       -7,011.3           -130.3   100703325     102758495
      6.9    1.5 reserves_exhausted       9292       -7,080.0           -137.4   100703325     102758495
      7.0    1.5 reserves_exhausted       9269       -7,145.8           -144.9   100703325     102758495
--- scenarios/soros-1992.yaml WITH holder
 multiple  ratio      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  paid_total  arb_redeemed  holder_redeemed  holder_stable   holder_pnl
      4.0    0.8          max_steps      14400         -222.3           -162.7    64469951       3601138     62,053,794.0            0.0 -1,018,186.0
      4.1    0.9          max_steps      14400         -225.1           -151.3    68954011      15215272     55,002,558.0            0.0   -857,385.0
      4.2    0.9          max_steps      14400         -222.5           -162.2    72954008      11549060     62,793,734.0            0.0   -758,003.0
      4.3    0.9          max_steps      14400       -1,044.2           -144.3    76102125      27573035     50,001,106.0            0.0   -702,896.0
      4.4    0.9          max_steps      14400       -1,746.8           -162.3    78340725      33185406     46,673,299.0            0.0   -692,055.0
      4.5    1.0          max_steps      14400       -2,319.7           -144.4    80565444      41326692     40,804,832.0            0.0   -669,028.0
      4.6    1.0          max_steps      14400       -2,786.6           -146.2    82863077      49289470     35,201,608.0            0.0   -617,326.0
      4.7    1.0          max_steps      14400       -3,185.0           -178.0    84558673      56577488     29,641,952.0            0.0   -511,266.0
      4.8    1.0          max_steps      14400       -3,540.4           -146.4    86584675      51452071     36,826,851.0            0.0   -648,866.0
      4.9    1.0          max_steps      14400       -3,867.5           -145.6    88104434      56157777     33,668,049.0            0.0   -618,409.0
      5.0    1.1          max_steps      14400       -4,152.3           -155.3    89950326      60019856     31,695,318.0            0.0   -581,034.0
      5.1    1.1          max_steps      14400       -4,415.8           -142.8    91209855      65568686     27,430,896.0            0.0   -510,088.0
      5.2    1.1          max_steps      14400       -4,639.9           -167.7    92837046      69976380     24,691,860.0            0.0   -449,943.0
      5.3    1.1          max_steps      14400       -4,857.1           -160.3    94433289      74776125     21,523,861.0            0.0   -385,063.0
      5.4    1.1          max_steps      14400       -5,052.2           -150.1    96012879      79011345     18,909,923.0            0.0   -310,943.0
      5.5    1.2          max_steps      14400       -5,237.1           -158.8    97583092      83403959     16,127,530.0            0.0   -238,376.0
      5.6    1.2          max_steps      14400       -5,405.9           -175.4    98662131      87767040     12,868,357.0            0.0   -158,659.0
      5.7    1.2 reserves_exhausted       9661       -5,565.4           -142.0   100703325      92267556     10,452,690.0    1,691,181.0   -134,307.0
      5.8    1.2 reserves_exhausted       9623       -5,714.1           -127.2   100703325      96805060      5,917,354.0    5,954,720.0    -93,000.0
      5.9    1.2 reserves_exhausted       9589       -5,854.4           -138.2   100703325     100207801      2,517,583.0    9,221,951.0    -72,157.0
      6.0    1.3 reserves_exhausted       9550       -5,982.4           -127.8   100703325     100347952      2,377,717.0    9,219,585.0    -64,942.0
      6.1    1.3 reserves_exhausted       9518       -6,105.4           -133.8   100703325     100489816      2,237,851.0    9,230,432.0    -59,718.0
      6.2    1.3 reserves_exhausted       9486       -6,220.4           -145.8   100703325     100351233      2,377,717.0    9,243,436.0    -58,013.0
      6.3    1.3 reserves_exhausted       9454       -6,329.6           -140.6   100703325     100492385      2,237,851.0    9,245,393.0    -51,300.0
      6.4    1.4 reserves_exhausted       9422       -6,431.7           -135.2   100703325     100633107      2,097,985.0    9,250,210.0    -41,483.0
      6.5    1.4 reserves_exhausted       9396       -6,530.6           -129.3   100703325     100774400      1,958,120.0    9,258,988.0    -27,443.0
      6.6    1.4 reserves_exhausted       9365       -6,621.9           -123.3   100703325     100775256      1,958,120.0    9,263,076.0    -17,759.0
      6.7    1.4 reserves_exhausted       9339       -6,710.3           -130.0   100703325     100915122      1,818,254.0    9,261,505.0    -25,532.0
      6.8    1.4 reserves_exhausted       9316       -6,794.8           -130.3   100703325     100917333      1,818,254.0    9,272,846.0    -14,610.0
      6.9    1.5 reserves_exhausted       9291       -6,874.1           -130.6   100703325     101197137      1,538,523.0    9,281,347.0     -6,503.0
      7.0    1.5 reserves_exhausted       9269       -6,950.5           -144.9   100703325     101058582      1,678,388.0    9,288,927.0    -12,320.0
```

`soros-1992-no-defense`:

```
--- scenarios/soros-1992-no-defense.yaml WITHOUT holder
 multiple  ratio      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  paid_total  arb_redeemed
      4.0    0.8 reserves_exhausted       7806       -6,648.6           -137.7   100703325     100703325
      4.1    0.9 reserves_exhausted       7806       -6,732.4           -144.6   100703325     100703325
      4.2    0.9 reserves_exhausted       7806       -6,812.3           -151.8   100703325     100703325
      4.3    0.9 reserves_exhausted       7806       -6,888.6           -145.6   100703325     100703325
      4.4    0.9 reserves_exhausted       7806       -6,961.6           -139.0   100703325     100703325
      4.5    1.0 reserves_exhausted       7806       -7,031.3           -132.1   100703325     100703325
      4.6    1.0 reserves_exhausted       7806       -7,098.1           -154.3   100703325     100703325
      4.7    1.0 reserves_exhausted       7806       -7,162.0           -147.5   100703325     100703325
      4.8    1.0 reserves_exhausted       7806       -7,223.4           -132.6   100703325     100703325
      4.9    1.0 reserves_exhausted       7806       -7,282.2           -140.6   100703325     100703325
      5.0    1.1 reserves_exhausted       7806       -7,338.8           -148.9   100703325     100703325
      5.1    1.1 reserves_exhausted       7806       -7,393.1           -157.5   100703325     100703325
      5.2    1.1 reserves_exhausted       7806       -7,445.4           -158.2   100703325     100703325
      5.3    1.1 reserves_exhausted       7806       -7,495.7           -158.8   100703325     100703325
      5.4    1.1 reserves_exhausted       7806       -7,544.1           -150.8   100703325     100703325
      5.5    1.2 reserves_exhausted       7806       -7,590.8           -151.3   100703325     100703325
      5.6    1.2 reserves_exhausted       7806       -7,635.8           -133.9   100703325     100703325
      5.7    1.2 reserves_exhausted       7806       -7,679.3           -161.3   100703325     100703325
      5.8    1.2 reserves_exhausted       7806       -7,721.2           -143.5   100703325     100703325
      5.9    1.2 reserves_exhausted       7806       -7,761.7           -162.6   100703325     100703325
      6.0    1.3 reserves_exhausted       7806       -7,800.9           -134.5   100703325     100703325
      6.1    1.3 reserves_exhausted       7806       -7,838.7           -144.4   100703325     100703325
      6.2    1.3 reserves_exhausted       7806       -7,875.4           -154.6   100703325     100703325
      6.3    1.3 reserves_exhausted       7806       -7,910.8           -165.2   100703325     100703325
      6.4    1.4 reserves_exhausted       7806       -7,945.2           -165.8   100703325     100703325
      6.5    1.4 reserves_exhausted       7806       -7,978.4           -156.1   100703325     100703325
      6.6    1.4 reserves_exhausted       7806       -8,010.7           -156.6   100703325     100703325
      6.7    1.4 reserves_exhausted       7806       -8,042.0           -157.0   100703325     100703325
      6.8    1.4 reserves_exhausted       7806       -8,072.3           -157.5   100703325     100703325
      6.9    1.5 reserves_exhausted       7806       -8,101.8           -158.0   100703325     100703325
      7.0    1.5 reserves_exhausted       7806       -8,130.4           -158.5   100703325     100703325
--- scenarios/soros-1992-no-defense.yaml WITH holder
 multiple  ratio      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  paid_total  arb_redeemed  holder_redeemed  holder_stable  holder_pnl
      4.0    0.8 reserves_exhausted       7811       -6,373.9           -144.1   100703325      99164802      1,538,523.0    9,266,733.0   -33,469.0
      4.1    0.9 reserves_exhausted       7808       -6,472.4           -151.1   100703325      99164802      1,538,523.0    9,272,613.0   -34,202.0
      4.2    0.9 reserves_exhausted       7808       -6,566.5           -151.8   100703325      99444534      1,258,791.0    9,282,830.0   -24,730.0
      4.3    0.9 reserves_exhausted       7805       -6,655.2           -145.6   100703325      99164802      1,538,523.0    9,272,269.0   -29,377.0
      4.4    0.9 reserves_exhausted       7806       -6,740.8           -132.0   100703325      99304668      1,398,657.0    9,281,674.0    -7,494.0
      4.5    1.0 reserves_exhausted       7807       -6,821.8           -153.7   100703325      99444534      1,258,791.0    9,289,343.0   -20,102.0
      4.6    1.0 reserves_exhausted       7808       -6,899.9           -154.3   100703325      99164802      1,538,523.0    9,276,182.0   -33,643.0
      4.7    1.0 reserves_exhausted       7806       -6,972.8           -155.0   100703325      99164802      1,538,523.0    9,287,795.0   -22,817.0
      4.8    1.0 reserves_exhausted       7806       -7,042.9           -132.6   100703325      99304668      1,398,657.0    9,305,007.0    14,940.0
      4.9    1.0 reserves_exhausted       7806       -7,110.4           -132.8   100703325      99444534      1,258,791.0    9,295,606.0     5,516.0
      5.0    1.1 reserves_exhausted       7808       -7,175.3           -132.9   100703325      99444534      1,258,791.0    9,304,403.0    14,053.0
      5.1    1.1 reserves_exhausted       7807       -7,236.8           -133.1   100703325      99444534      1,258,791.0    9,308,278.0    17,726.0
      5.2    1.1 reserves_exhausted       7806       -7,295.4           -149.9   100703325      99444534      1,258,791.0    9,323,161.0    16,769.0
      5.3    1.1 reserves_exhausted       7807       -7,352.2           -158.8   100703325      99444534      1,258,791.0    9,328,935.0    14,133.0
      5.4    1.1 reserves_exhausted       7805       -7,406.2           -159.4   100703325      99444534      1,258,791.0    9,338,647.0    23,077.0
      5.5    1.2 reserves_exhausted       7807       -7,459.1           -151.3   100703325      99584399      1,118,926.0    9,327,850.0    20,060.0
      5.6    1.2 reserves_exhausted       7807       -7,509.3           -133.9   100703325      99584399      1,118,926.0    9,352,741.0    60,856.0
      5.7    1.2 reserves_exhausted       7808       -7,557.8           -143.1   100703325      99724265        979,060.0    9,345,623.0    45,180.0
      5.8    1.2 reserves_exhausted       7807       -7,604.3           -152.7   100703325      99724265        979,060.0    9,362,720.0    53,063.0
      5.9    1.2 reserves_exhausted       7806       -7,649.1           -143.8   100703325      99724265        979,060.0    9,360,517.0    59,254.0
      6.0    1.3 reserves_exhausted       7807       -7,692.4           -153.7   100703325      99864131        839,194.0    9,378,392.0    67,601.0
      6.1    1.3 reserves_exhausted       7806       -7,734.1           -134.7   100703325      99724265        979,060.0    9,378,073.0    85,102.0
      6.2    1.3 reserves_exhausted       7806       -7,774.5           -134.8   100703325      99724265        979,060.0    9,389,532.0    96,258.0
      6.3    1.3 reserves_exhausted       7805       -7,813.3           -145.1   100703325      99864131        839,194.0    9,400,221.0    97,186.0
      6.4    1.4 reserves_exhausted       7806       -7,851.2           -165.8   100703325      99724265        979,060.0    9,400,124.0    77,610.0
      6.5    1.4 reserves_exhausted       7805       -7,887.5           -156.1   100703325      99864131        839,194.0    9,416,963.0   103,307.0
      6.6    1.4 reserves_exhausted       7804       -7,922.7           -135.5   100703325      99864131        839,194.0    9,416,005.0   121,761.0
      6.7    1.4 reserves_exhausted       7805       -7,957.1           -135.6   100703325     100003997        699,328.0    9,422,847.0   128,363.0
      6.8    1.4 reserves_exhausted       7805       -7,990.1           -146.7   100703325     100003997        699,328.0    9,425,459.0   120,549.0
      6.9    1.5 reserves_exhausted       7805       -8,022.2           -158.0   100703325     100003997        699,328.0    9,430,158.0   114,497.0
      7.0    1.5 reserves_exhausted       7804       -8,053.0           -136.1   100703325     100003997        699,328.0    9,452,344.0   157,007.0
```

Boundary probe on the calibrated baseline (with the holder):

```
$ python scripts/probe_boundary.py --workers 10 --ratios 0.1,0.2,0.25,0.3,0.4,0.5,1.0; echo exit=$?
$ python scripts/probe_boundary.py --workers 10 --ratios 0.325,0.35,0.375,0.4,0.425,0.45,0.475,0.5,0.55,0.6 --output output/probe-fine; echo exit=$?
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=7 seeds=8 (1000..1007) cells=56
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.100              0.343  8                 0.000            1.000        0.000         -1,849.554       10,238,870.581
 0.200              0.687  8                 0.000            1.000        0.000         -3,229.693       21,725,811.548
 0.250              0.859  8                 0.000            1.000        0.000         -3,791.857       26,940,402.194
 0.300              1.030  8                 0.000            1.000        0.000         -4,286.803       31,863,389.113
 0.400              1.374  8                 0.000            1.000        0.000         -5,114.358       40,898,887.644
 0.500              1.717  8                 0.000            0.500        0.500         -5,774.312       41,346,974.000
 1.000              3.434  8                 0.000            0.000        1.000         -8,151.224       41,346,974.000
exit=0
probe_boundary: scenario=scenarios/calibrated-baseline.yaml budget+reserves=179,454,391 ratios=10 seeds=8 (1000..1007) cells=80
deliverable reserves = 10,904,220; F-06 predicted flip ratio = (budget + deliverable) / (budget + reserves) = 0.291
 ratio  ratio_deliverable  n  p_reserves_exhausted  p_peg_recovered  p_max_steps  max_depeg_bps_p50  defender_spent_mean
 0.325              1.116  8                 0.000            1.000        0.000         -4,512.369       34,110,282.807
 0.350              1.202  8                 0.000            1.000        0.000         -4,724.836       36,409,181.369
 0.375              1.288  8                 0.000            1.000        0.000         -4,925.198       38,614,594.806
 0.400              1.374  8                 0.000            1.000        0.000         -5,114.358       40,898,887.644
 0.425              1.460  8                 0.000            1.000        0.000         -5,293.135       41,346,974.000
 0.450              1.546  8                 0.000            0.750        0.250         -5,462.276       41,346,974.000
 0.475              1.631  8                 0.000            0.625        0.375         -5,622.461       41,346,974.000
 0.500              1.717  8                 0.000            0.500        0.500         -5,774.312       41,346,974.000
 0.550              1.889  8                 0.000            0.375        0.625         -6,055.234       41,346,974.000
 0.600              2.061  8                 0.000            0.250        0.750         -6,309.047       41,346,974.000
exit=0
```

Checks at close:

```
$ pytest; echo exit=$?
502 passed in 6.24s
exit=0
All checks passed!
exit=0
83 files already formatted
exit=0
```

(`ruff check .` and `ruff format --check .` are the second and third pairs.) CI on 10ea310: `gh run list` → `completed success story 2.6: par-expecting buyer agent ci main push 37234187066 56s 2026-10-04T20:58:46Z`. `PHASE_ORDER_VERSION` 1; no changes under `kernel/` other than `HolderConfig` in `kernel/config.py` (AC 2); none under `protocol/`.

Scratch scripts (not committed):

```python
"""Holder/arb redemption detail for one scenario config (path + optional holder capital)."""
import sys
from pathlib import Path
from depeg_sim.experiments.runner import build_world
from depeg_sim.kernel.config import load_scenario, ScenarioConfig
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.analysis.summary import summarize

def load(path, holder_capital=None, drop_holder=False, attacker_capital=None):
    d = load_scenario(Path(path)).model_dump(mode="json")
    if drop_holder:
        d["agents"] = [a for a in d["agents"] if a["type"] != "holder"]
    elif holder_capital is not None:
        d["agents"] = [a for a in d["agents"] if a["type"] != "holder"] + [
            {"type": "holder", "id": "holder-1", "capital": holder_capital, "entry_discount_pct": 2.0, "pace": 0.05}]
    if attacker_capital is not None:
        next(a for a in d["agents"] if a["type"] == "attacker")["capital"] = attacker_capital
    return ScenarioConfig.model_validate(d)

def detail(cfg, split_step=None):
    ctx = RunContext.from_config(cfg); world = build_world(cfg, ctx)
    res = Engine(ctx).run()
    s = summarize(cfg, res, world["metrics"].to_dataframe(), world)
    ev = ctx.events.all()
    out = dict(terminated_by=s["terminated_by"], steps_run=s["steps_run"], trough=round(s["max_depeg_bps"],1),
               trough_step=s["step_of_max_depeg"], final=round(s["final_depeg_bps"],1),
               defender_spent=s["defender_spent"], paid_total=s["redemption_paid_total"],
               attacker_pnl=s["attacker_pnl"], arb_pnl=s["arbitrageur_pnl"])
    ex = [e for e in ev if e.kind == "reserves_exhausted"]
    out["exhausted_step"] = ex[0].step if ex else None
    for a in (w for w in world.values() if hasattr(w, "agent_id")):
        fills = [e for e in ev if e.kind == "redeem_fulfilled" and e.payload["source"] == a.agent_id]
        red = sum(e.payload["amount_stable"] for e in fills)
        line = dict(redeemed=round(red), paid=round(sum(e.payload["paid_reference"] for e in fills)), pnl=round(a.pnl_last),
                    stable=round(a.balances["stable"]), reference=round(a.balances["reference"]))
        if split_step is not None:
            line["redeemed_before"] = round(sum(e.payload["amount_stable"] for e in fills if e.step < split_step))
            line["redeemed_after"] = round(red - line["redeemed_before"])
        if a.type == "holder":
            line.update(spent=round(a.spent_reference), bought=round(a.bought_stable))
        out[a.agent_id] = line
    return out

if __name__ == "__main__":
    path = sys.argv[1]; cap = float(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    split = int(sys.argv[3]) if len(sys.argv) > 3 else None
    for k, v in detail(load(path, cap, drop_holder=(len(sys.argv) > 2 and sys.argv[2] == "-")), split).items(): print(f"{k}: {v}")
```

```python
"""Story 2.6 AC 7: soros-1992 attacker multiple 4.0..7.0 step 0.1, with and without the holder."""
import sys
from multiprocessing import Pool
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from holder_detail import detail, load

Q = 42_625_746  # Quantum's $10bn x s
R = 2 * 100_703_325  # budget + reserves
SCEN = sys.argv[1] if len(sys.argv) > 1 else "scenarios/soros-1992.yaml"

def cell(args):
    m, with_holder = args
    d = detail(load(SCEN, drop_holder=not with_holder, attacker_capital=m * Q))
    h = d.get("holder-1", {})
    return dict(multiple=m, holder=with_holder, terminated_by=d["terminated_by"], steps_run=d["steps_run"],
                exhausted_step=d["exhausted_step"], max_depeg_bps=d["trough"], final_depeg_bps=d["final"],
                paid_total=round(d["paid_total"]), arb_redeemed=d["arb-1"]["redeemed"], arb_paid=d["arb-1"]["paid"],
                holder_redeemed=h.get("redeemed"), holder_paid=h.get("paid"), holder_stable=h.get("stable"),
                holder_pnl=h.get("pnl"))

if __name__ == "__main__":
    ms = [round(4.0 + 0.1 * i, 1) for i in range(31)]
    with Pool(10) as p:
        rows = p.map(cell, [(m, w) for w in (False, True) for m in ms])
    df = pd.DataFrame(rows)
    df["ratio"] = (df["multiple"] * Q / R).round(3)
    pd.set_option("display.width", 250)
    for w in (False, True):
        print(f"--- {SCEN} {'WITH' if w else 'WITHOUT'} holder")
        cols = ["multiple", "ratio", "terminated_by", "steps_run", "max_depeg_bps", "final_depeg_bps", "paid_total", "arb_redeemed"]
        if w: cols += ["holder_redeemed", "holder_stable", "holder_pnl"]
        print(df[df.holder == w][cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    df.to_csv(Path(__file__).parent / f"scan_{Path(SCEN).stem}.csv", index=False)
```

### Completion Notes List

**C\*** = **9,166,667 model units** = **≈ $2,150,500,078** at `s` = **0.79× the attacker's
episode net burn** (11,540,596 units, $2.71B). Also 0.22× Circle's $9.7B cash and 0.55× D\*.
Trough at C\*: −1,137.8 bps, step 10255 (34.2 h). D\* and pace are not re-fitted.

**The rule change moved the trough (Rulings asked me to confirm it wouldn't; it did).** At
10M, the original rule gave −1,052.1 at step 10361 and the tranche rule gives −224.6 at
step 8140. Mechanism: weekend tranches (≤ 6,058 stable per clear-queue step at 605.79
capacity) return reference, and the holder spends it again below $0.98 (spent 9.42M from
9.17M capital at C\*; 10.89M from 10M). Near the cliff that is enough to outlast the
attack. C\* moved from 10M to 9,166,667 under the amended two-pass rule. The second pass
ran between 5M and 10M, not the 7.5M–12.5M the Rulings anticipated: after pass 1 the
closest point was 7.5M (−2,206.7), whose neighbours in the run set are 5M and 10M.

**Replay before/after (VALIDATION.md, new 2.6 section; the 2.5 table is kept):**
- trough −5,769 → −1,138 bps (observed −1,373);
- trough time 31.6 h → 34.2 h, outside ±2 h (pace was fitted in 2.5 without the holder);
- back in band at 85.3 h, last outside 85.3 h, upward within 0.3 h of the capacity
  change: unchanged.

**Holder redemptions in the replay:** 6,693,374 before the capacity change (step 25500)
and 2,804,188 after, 9,497,562 total. Holder PnL +82,521. The arbitrageur redeems
2,019,110 (2.5: 10.54M paid before the backstop, mostly to it). The Dev Notes expected the
bulk after Monday; the weekend channel (≈ 10.5M) was large enough for most of it. That
inherits 2.5's caveat that the calibrated capacity is the 11–15 March average.

**Overlay (looked at):** a sawtooth between ≈ +310 and −220 bps from 27 h to ≈ 30.5 h
(each 5%-of-reference buy, ≈ 458k into 16.7M, overshoots par and the attacker pushes the
price back down). It drops to ≈ −1,060 at 31.5 h, bounces, then hits the trough −1,138 at
34.2 h. From ≈ 35 h it overlaps the observed line up to ≈ −280 at 45 h. It holds flat at
−170 from 49 h to 69 h while the observed price dips to −520 at 55 h (nothing sells stable
to follow it down), steps up at ≈ 70 h, enters the band at the 85 h marker and holds −27
to 112 h. Cosmetic: the "observed trough" annotation overlaps the x-axis tick labels (2.5's
chart code; charts are Story 2.7).

**Propagation (AC 7), seed 42:**

| scenario | before | after |
|---|---|---|
| calibrated-baseline | peg_recovered 7024; −1253.2 @50; defender spent 10,261,334 | peg_recovered 7024; −1253.2 @50; defender spent **6,054,986**; holder spent 4,461,031, redeemed 3,935,212, PnL +198,965 |
| calibrated-stress | peg_recovered 7225; −1231.0 @50; defender spent 10,261,842 | peg_recovered 7225; −1231.0 @50; defender spent **6,055,420**; holder spent 4,461,031, redeemed 4,048,495, PnL +201,938 |
| soros-1992 (6×) | reserves_exhausted, steps_run 9551 (event step 9550); −6332.2 @3054; arb redeemed 102,758,495 | reserves_exhausted, steps_run **9550** (event 9549); −5982.4 @3337; arb redeemed **100,347,952**; holder redeemed 2,377,717, stranded 9,219,585 stable, **PnL −64,942** |
| soros-1992-no-defense (6×) | reserves_exhausted, 7806 (event 7805); −7800.9 @1391; arb redeemed 100,703,325 | reserves_exhausted, **7807** (event 7806); −7692.4 @1543; arb redeemed **99,864,131**; holder redeemed 839,194, stranded 9,378,392, PnL +67,601 |

Holder PnL is marked at AMM spot at termination. When reserves have run out, the stranded
stable is arguably worth less than spot.

**1992 flip re-scan:** the flip stays at **5.7 (ratio 1.206)**. **5.1 and 5.2 no longer
exhaust**, so the boundary is clean. The F-07 dead zone persists: 4.0–5.6 stall at
`max_steps`, final −143 … −178 bps. In the dead zone the holder is the main redeemer at low
multiples (62.1M stable at 4.0 vs the arbitrageur's 3.6M) and **loses at every multiple**
(−1.02M at 4.0 … −0.16M at 5.6). The defender's 200 bps spread makes the payout $0.98,
equal to its entry price, so each round trip loses its own price impact. Without the
holder the scan reproduces 2.5 exactly. No-defense exhausts at every multiple with and
without it.

**F-06 probe:** with the holder, every seed recovers through ratio 0.425 (2.5: 0.325), the
first mixed ratio is 0.45 (2.5: 0.35), 50% recover at 0.50 (2.5: ≈ 0.39), and 25% still
recover at 0.60 (2.5: none at 0.475). The shift (+0.11) is ≈ 2× the holder's face value
over budget + reserves (0.051). Nothing exhausts.

**Finding write-up (does the buyer change which actor decides the outcome?).**
- **USDC replay: yes.** The holder replaces "nobody" as the absorbing side. It buys 9.50M
  of the 11.54M attack (82%; the calibrated defender's share was 89%) and is the main
  redeemer (9.50M vs the arbitrageur's 2.02M). Trough depth is now decided by the attacker
  against the holder's capital, which is F-08's claim, quantified: at 0.79× the attack,
  the buyer takes the trough from −5,769 to −1,138.
- **Calibrated baseline: partly.** The verdict is unchanged, but the defender's spend
  falls 41%; the holder takes the first −2% of the discount.
- **1992: no.** The verdict is still set by attacker vs budget + reserves. At C\*/D\* the
  holder is 3.6% of the 6× attacker, too small to test BACKGROUND §4's "convergence
  traders switched sides". It does change who drains the reserves in the dead zone, and
  under a defended spread it is a loss-making believer left holding the broken promise.
- **New finding candidate (Rulings 2, in ADR-0021): a single-entry buyer makes trough depth
  bimodal in its capital.** 7.5M → −2,207, 8.33M → −1,653, 9.17M → −1,138, 10M → −225. The
  observation sits on the cliff.

**ADR:** [0021](../adr/0021-par-expecting-holder.md), Proposed (index not edited).

**Judgment calls:**
- Entry price is relative to `peg_price` (1.0 everywhere).
- `hold_done` is not terminal; it buys again if the discount returns.
- The refinement "neighbours" are the pick's neighbours among every distinct capital run
  so far.
- `fit_holder.py` writes a holder-bearing base YAML to `<output>/fit-holder-base/` because
  sweep paths cannot add an agent; an existing holder entry is replaced.
- The redemption tranche uses `available_stable` (stable not already queued).
- I did not add holder columns to `summary.json` (that would change every run's summary
  bytes). Holder figures above come from in-process runs via the scratch scripts.

**Tests:** 502 passed (494 at the block, +8: the tranche tests replace the threshold
tests, plus propagation-ratio and no-holder checks in `tests/test_holder_config.py`).
`tests/test_usdc_2023.py::test_short_run_completes` is the short `usdc-2023` run with the
holder (500 steps).


### File List

**Created:**
- `src/depeg_sim/agents/holder.py`
- `scripts/fit_holder.py`
- `tests/test_holder.py`, `tests/test_holder_config.py`
- `docs/adr/0021-par-expecting-holder.md`

**Modified:**
- `src/depeg_sim/kernel/config.py` (`HolderConfig`, union)
- `src/depeg_sim/agents/factory.py`
- `scenarios/usdc-2023.yaml`, `calibrated-baseline.yaml`, `calibrated-stress.yaml`, `soros-1992.yaml`, `soros-1992-no-defense.yaml`
- `docs/calibration/SOURCES.md`, `docs/calibration/VALIDATION.md`
- `tests/test_scripts.py`, `tests/test_calibrated_scenarios.py`, `tests/test_1992_scenarios.py`, `tests/test_usdc_2023.py`
- `docs/stories/2-6-holder-agent.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-04
**Outcome:** **APPROVE** ✅ — the buyer takes the replay from 4.2× too deep to 17% too
shallow with one fitted parameter, and the weekend path sits on the observed one from 35 h.

### Summary

Independent reproduction on the review box (Python 3.13.15, fresh install):
`pytest` → `502 passed in 15.50s`; `ruff check .` → `All checks passed!`;
`ruff format --check .` → `83 files already formatted`. All five scenarios re-run: hashes
`2c3aeaa9825d`, `44ac03c60e5f`, `17b24b458e47`, `f4e26ae66440`, `516edaef4795` and troughs
−1,137.8 / −1,253.2 / −1,231.0 / −5,982.4 / −7,692.4 match the Debug Log exactly.
`fit_holder.py --workers 2` (1m01s) lands on C\* = 9,166,667 (−1,137.8). The builder's
scratch `holder_detail.py` re-run here gives the same per-agent figures: replay holder
redeemed 6,693,374 before / 2,804,188 after the capacity change, PnL +82,521; calibrated
baseline defender spend 10,261,334 → 6,054,986; soros-1992 arbitrageur 102,758,495 →
100,347,952, exhaustion step 9550 → 9549, holder PnL −64,942. Overlay regenerated and
inspected.

The blocker was the right call and the builder's diagnostic (C\* independent of the rule,
1992 dependent on it) was exactly what the ruling needed. The builder then caught that my
ruling's expectation ("the rule change should not move the trough") was wrong: under the
tranche rule the holder recycles ~0.9M of weekend redemption proceeds into further buying,
which near the cliff is enough to outlast the attack, so 10M went from −1,052 to −225 and
C\* moved to 9.17M. Reported plainly, with the cause. That is what the Rulings asked for.

### Rulings

1. **ADR-0021 → Accepted (finding, amended).** Amendment: the "finding candidate" section
   is promoted to F-09 in FINDINGS.md; the 1992 section's observation that the holder's
   round trip pays nothing is recorded as a parametric coincidence (entry 2% = defender
   spread 200 bps, both dev-manager assumptions), not a finding.
2. **The holder's sawtooth (±310/−220 bps for 3.5 h) is a model artefact to fix, not
   publish.** A price limit on the holder's own fills (stop buying when its own trade would
   lift the spot above its entry price) is the obvious rule. It is not in 2.7 (charts) and
   it changes C\*, so it goes in Epic 3 as a story of its own, ahead of the multi-tranche
   holder. Until then the overlay is shown with the artefact described in the caption.
3. **Pace is not re-fitted.** Confirmed. Two parameters to one path is over-fitting; the
   3.2 h lateness is stated in VALIDATION.md and the note.
4. **The overlay chart clips the observed-trough annotation** (label and leader run off the
   bottom axis). Fix in 2.8 (committed figures): y-limits must include both trough
   annotations. Added to the 2.8 ACs in `epics.md`.
5. **Holder columns in `summary.json` → deferred to 2.7.** Right not to change every
   run's output in this story. 2.7's F-03 collapse plot needs "stable absorbed by the
   peg's defenders" per cell, so 2.7 adds `defender_bought_stable`, `holder_bought_stable`
   and `holder_pnl` to the summary (None when the agent is absent) as its own first commit.
6. **Second-refinement pass landing on 5M–10M rather than 7.5M–12.5M.** The rule as
   amended says "between the new neighbours", and the new pick after pass 1 was 7.5M, so
   its neighbours were 5M and 10M. Applied correctly; my parenthetical in the ruling was a
   guess at the outcome, not part of the rule.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | `agents/holder.py` as amended; tranche rule; never sells; no `ctx.rng` (grep clean) |
| 2 | ✅ | `HolderConfig` four fields; `tests/test_holder_config.py` pins all seven pre-2.6 hashes |
| 3 | ✅ | `tests/test_holder.py`: wait/buy/redeem tranche/done/PnL/trace; real modules, manual phases |
| 4 | ✅ | two-pass fit, table in Debug Log, reproduced here; `--dry-run` tested |
| 5 | ✅ | `usdc-2023.yaml` holder entry with status line; VALIDATION.md 2.6 table + paragraphs; overlay |
| 6 | ✅ | SOURCES.md holder section with $2.15B next to $2.71B burn and $9.7B cash |
| 7 | ✅ | four scenarios at 9,166,667; before/after in Debug Log; 1992 re-scan both files; probe re-run |
| 8 | ✅ | ADR-0021; "which actor decides" in Completion Notes |
| 9 | ✅ | 502 passed; ruff clean; CI green (e18fc39) |

**9 of 9 ACs met.**

### Key Findings

- **F-08 confirmed with a number.** No buyer: −5,769. One buyer at $2.15B (0.79× the
  attack): −1,138. Observed: −1,373. The buyer absorbed 82% of the attack flow, where the
  calibrated defender had absorbed 89% — the defender was standing in for the market.
- **F-09 (new): a single-entry-price buyer makes depth bimodal.** Attacker-set below the
  cliff, buyer-set (≈ entry discount) above it; the observed trough is on the cliff face.
  Real buyers entered at a spread of prices.
- **F-06 refinement:** the probe's 50% point moves 0.39 → 0.50 with the holder; twice its
  face-value share, same mechanism as F-03 (buys below par, recycles).
- **F-07 refinement:** the 1992 flip stays at 5.7; the 5.1/5.2 anomaly is gone; the dead
  zone persists; the holder at 3.6% of the attacker cannot test the "convergence traders
  switched sides" claim — that needs a holder with a sell rule (Epic 3).

### Learnings for Story 2.7

- A ruling's stated expectation is a prediction, not a constraint. The builder was right
  to report it falsified and continue.
- The holder is now part of the calibrated model. Every sweep from here runs with it
  present at `C*/D*` of the cell's depth, which the sweep spec must be able to express.
- The F-03 price-adjusted ratio is an outcome, not a parameter: it cannot be a heatmap
  axis, but it can be the x-axis of a collapse plot across depths.

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.5 review (F-08); inserted into Epic 2
- 2026-10-04: Config, agent, tests and fit script implemented; C* = 10,000,000 fitted. Blocked: the normative redeem condition (`redeem_fraction_min` 0.1) never lets the holder redeem at C* in any scenario, contradicting the Dev Notes' "redeem Monday" intent (see Blockers)
- 2026-10-04: Dev manager ruled on Blockers (option 3 tranche redeem rule; second refinement pass; record timing and cliff). AC 1, AC 4 and Dev Notes amended. Status back to in-progress.
- 2026-10-04: Resumed per Rulings (Claude Code, Opus 5.5). Tranche redeem rule (`redeem_horizon_steps` 10); two-pass fit: C* = 9,166,667 (−1,137.8 bps, ≈ $2.15B, 0.79× net burn); the rule change moved the trough at 10M (−1,052 → −225). Holder added to five scenarios at C*/D*; replay, propagation, 1992 re-scan, probe re-run; VALIDATION.md 2.6 section; SOURCES.md holder section; ADR-0021 Proposed. Status → review
- 2026-10-04: Senior review APPROVE; ADR-0021 accepted (finding, amended); F-09 added; Status done
