# Story 2.6: Par-Expecting Buyer Agent

Status: ready-for-dev

## Story

As a **researcher**,
I want an agent that buys the discounted stablecoin because it expects redemption at par,
so that the replay can reproduce the observed trough and the note can say what decided March 2023.

## Acceptance Criteria

1. `src/depeg_sim/agents/holder.py`: `Holder(agent_id, capital, entry_discount_pct, pace, redeem_when_capacity)` extending `Agent`; starts `balances = {stable: 0, reference: capital}`; each step: if `amm.spot_price < 1 − entry_discount_pct/100` and `reference > 0` → `swap buy_stable` with `pace × reference_balance` (rule `hold_buy`); else if `redeem_when_capacity` and `stable > 0` and `redemption.queue_depth == 0` and `redemption.capacity_per_step >= stable × redeem_fraction_min` (see Dev Notes) → `redeem` all stable (rule `hold_redeem`); else if `stable > 0` → `hold_wait`; else `hold_done`; never sells on the AMM
2. `HolderConfig(type: "holder", id, capital gt 0, entry_discount_pct ge 0, pace gt 0 le 1, redeem_when_capacity: bool = True)` added to `config.py` and the `AgentConfig` discriminated union; `build_agents` dispatches it; every existing scenario's `content_hash()` unchanged (test)
3. Holder unit tests mirror 1.7's pattern (real AMM/oracle/redemption, manual phases): waits above the discount; buys below it at `pace`; redeems only when the queue is empty and capacity suffices; `hold_done` once out of both; PnL positive after a full buy-then-redeem-at-par cycle; one decision record per step when tracing
4. `scripts/fit_holder.py`: on `scenarios/usdc-2023.yaml` with D\* fixed, adds a holder (`entry_discount_pct 2.0`, `pace 0.05`, `redeem_when_capacity true`) and sweeps `capital` over `[1M, 2M, 5M, 10M, 20M, 50M, 100M]` model units, picks the value whose `max_depeg_bps` is closest to −1,373, refines with 5 points between the neighbours, prints the table and `C* = … (trough …)` and the dollar figure at `s`; `--dry-run` supported
5. `scenarios/usdc-2023.yaml` gains the fitted holder (`status: assumption, fitted to observed trough, this story`); replay re-run; overlay regenerated; `docs/calibration/VALIDATION.md` gains a **before/after** table (2.5 vs 2.6: trough depth, trough time, last-outside-band, recovery direction) and a paragraph on what the buyer fixed and what it didn't
6. `SOURCES.md` gains a holder section: `capital` (assumption, fitted, with the dollar figure next to the episode net burn and the $9.7B cash figure for scale), `entry_discount_pct` and `pace` (assumption, reasoning), `redeem_when_capacity` (assumption: the weekend buyers redeemed once Circle reopened)
7. `scenarios/calibrated-baseline.yaml`, `calibrated-stress.yaml`, `soros-1992.yaml`, `soros-1992-no-defense.yaml` each gain a holder at the **same capital-to-depth ratio** as the replay (`C* / D*`); all four re-run; outcomes before/after in Completion Notes; the 1992 flip re-scanned (4.0–7.0 by 0.1); `scripts/probe_boundary.py` re-run on the calibrated baseline
8. A `Proposed` ADR: holder semantics, `C*` in three units, and what moved in F-06 (boundary) and F-07 (1992 flip, dead zone) with the buyer present; a finding write-up in Completion Notes if the buyer changes which actor decides the outcome
9. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [ ] Config and factory (AC: 2)
  - [ ] `HolderConfig`; union; `build_agents`; hash-stability test
  - [ ] Commit separately: `story 2.6: holder config`

- [ ] Agent (AC: 1, 3)
  - [ ] `agents/holder.py`; `tests/test_holder.py`

- [ ] Fit (AC: 4, 5, 6)
  - [ ] `scripts/fit_holder.py`; run; `C*`
  - [ ] Update `usdc-2023.yaml`; re-run; overlay; `VALIDATION.md` before/after; `SOURCES.md` holder section
  - [ ] Look at the new overlay and describe it

- [ ] Propagate (AC: 7)
  - [ ] Add holder to the four scenarios at `C*/D*`; re-run all; re-scan 1992; re-probe

- [ ] ADR, tests, close out (AC: 8, 9)
  - [ ] Proposed ADR; `tests/test_scripts.py` dry-run for `fit_holder.py`
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
arbitrageur). Rule: redeem when `queue_depth == 0` and the facility's per-step capacity
is at least `redeem_fraction_min` (default 0.1) of its stable balance, i.e. it can be
paid out within ~10 steps. Expose `redeem_fraction_min` as a constructor default, not a
config field (keeps `HolderConfig` to the four fields in AC 2).

Before the capacity schedule fires in the replay, capacity is 605.79/step against a
holder that may hold millions of stable, so it will wait (`hold_wait`) all weekend and
redeem Monday. That is the intended behaviour and it is the March-2023 story.

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

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-6-holder-agent.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output; fit table, replay CLI lines before/after, four propagated runs, 1992 re-scan, probe)_

### Completion Notes List

_(include: C* in three units, before/after overlay description, VALIDATION.md table, what moved in F-06/F-07, ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.5 review (F-08); inserted into Epic 2
