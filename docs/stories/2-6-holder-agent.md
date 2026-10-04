# Story 2.6: Par-Expecting Buyer Agent

Status: in-progress

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

- [ ] Fit (AC: 4, 5, 6)
  - [x] `scripts/fit_holder.py`; run; `C*`
  - [ ] Update `usdc-2023.yaml`; re-run; overlay; `VALIDATION.md` before/after; `SOURCES.md` holder section
  - [ ] Look at the new overlay and describe it

- [ ] Propagate (AC: 7)
  - [ ] Add holder to the four scenarios at `C*/D*`; re-run all; re-scan 1992; re-probe

- [ ] ADR, tests, close out (AC: 8, 9)
  - [ ] Proposed ADR; `tests/test_scripts.py` dry-run for `fit_holder.py` (dry-run test done)
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.6: par-expecting buyer agent`, push to `main`

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

`python scripts/fit_holder.py --workers 8` (real 0m6.742s):

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

### Completion Notes List

_(include: C* in three units, before/after overlay description, VALIDATION.md table, what moved in F-06/F-07, ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.5 review (F-08); inserted into Epic 2
- 2026-10-04: Config, agent, tests and fit script implemented; C* = 10,000,000 fitted. Blocked: the normative redeem condition (`redeem_fraction_min` 0.1) never lets the holder redeem at C* in any scenario, contradicting the Dev Notes' "redeem Monday" intent (see Blockers)
- 2026-10-04: Dev manager ruled on Blockers (option 3 tranche redeem rule; second refinement pass; record timing and cliff). AC 1, AC 4 and Dev Notes amended. Status back to in-progress.
