# Story 5.4: Liquidity Provider That Disposes of Withdrawn Inventory

Status: ready-for-dev

## Story

As a **reader who does not believe a panicking LP sits on what it withdrew**,
I want the liquidity provider to be able to sell or redeem the stablecoin it pulls out of the pool,
so that F-15 ("liquidity that flees helps the defender") is tested against the two behaviours that could reverse it.

## Why

Referee §4 and §5.25–5.26: the LP result depends on the provider holding its withdrawn
inventory; an LP that dumped or redeemed it would be a second attacker or a second
redeemer. F-15 itself says so. This story builds the two alternatives and reruns the
flight sweep.

## Acceptance Criteria

1. `LPConfig.after_withdrawal: Literal["hold", "sell", "redeem"] = "hold"` and
   `disposal_pace: float = 0.1` (share of held stable disposed of per step, `0 < x ≤ 1`).
   Default `hold` with the field absent, so every existing scenario's hash is unchanged
   (pinned tests).
2. Agent behaviour, one action per step after the withdrawal decision, in this order:
   `lp_withdraw` (as now) else, if holding stable and `after_withdrawal != hold`:
   `lp_sell` swaps `disposal_pace × held_stable` on the AMM (sell side, fee on input,
   no price limit), or `lp_redeem` queues `min(held_stable, disposal_pace × held_stable)`
   through the redemption module (same queue the holder and arbitrageur use; no priority).
   `lp_hold` otherwise. Decision labels in the trace. No `ctx.rng` draws. Reference
   received from a sale or redemption is held (the LP never re-adds liquidity, ADR-0031).
3. `sweeps/lp-flight-disposal-mc.yaml`: the `lp-flight-mc.yaml` grid (share × attack
   ratio, 8 seeds) × `after_withdrawal` ∈ {hold, sell, redeem} at `disposal_pace` 0.1.
   `scripts/lp_flight_table.py --sweep` prints, per disposal mode: recovered fraction,
   median time to parity, trough, defender spent, LP PnL, and **redemption paid to the LP**
   and **LP sold on AMM** (two new per-run summary columns, `lp_sold_stable`,
   `lp_redeemed_stable`).
4. `plot_lp_flight` gains a disposal-mode facet; `docs/figures/lp_flight_disposal.png`;
   the existing `lp_flight.png` unchanged.
5. VALIDATION.md or FINDINGS-ready notes: the table and, in the builder's words, whether
   the sign of F-15 (recovery fraction at 0.7× and 1.0×; trough) holds, reverses, or
   splits between `sell` and `redeem`. Numbers first.
6. ADR proposed for the interface (disposal semantics, queue sharing) — the finding is the
   dev manager's to write.
7. Tests: config default and hash pins; `sell` reduces AMM price and `redeem` enters the
   queue on a two-step scenario; sweep spec hash; figure renders. `pytest`, `ruff`,
   `make figures-check`.

## Tasks / Subtasks

- [ ] Config and agent (AC: 1, 2)
- [ ] Sweep, table, columns (AC: 3)
- [ ] Figure (AC: 4)
- [ ] Write-up, ADR (AC: 5, 6)
- [ ] Tests, gates (AC: 7)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.4: LP disposes of withdrawn inventory`, push `story/5-4-lp-disposes-withdrawn-inventory`

## Dev Notes

### Learnings from Previous Story

- `agents/lp.py` docstring has the share accounting; withdrawn balances are already
  tracked (`balances`). Disposal acts on the stable side only; the reference side stays.
- The redemption queue is FIFO with per-step capacity (protocol/redemption.py); the LP
  joins it like any other agent. Say in the ADR whether its tranche rule mirrors the
  holder's `min(stable, capacity × 10)` or uses `disposal_pace`; this story says
  `disposal_pace` so the two modes are comparable.
- Phase order: the LP acts in the agent phase as now; no scheduler change. If you find
  you need one, stop and block (CLAUDE.md).
- `lp-flight-mc.yaml` is ~1 min at 8 workers; ×3 modes is fine.

### Prediction (to be checked, not aimed at)

`sell` deepens the trough (the LP becomes a second attacker one step behind the first)
and turns the 0.7×/1.0× cells back toward 0/8 recovered. `redeem` leaves the trough alone
but competes with the holder and arbitrageur for the channel; whether it helps or hurts
recovery is open. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §4, §5.25–5.26]
- [Source: docs/FINDINGS.md#F-15, docs/adr/0031-lp-withdrawal-and-liquidity-flight.md]
- [Source: src/depeg_sim/agents/lp.py, src/depeg_sim/kernel/config.py#LPConfig]

## Dev Agent Record

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
