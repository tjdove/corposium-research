# Story 5.4: Liquidity Provider That Disposes of Withdrawn Inventory

Status: review

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

- [x] Config and agent (AC: 1, 2)
- [x] Sweep, table, columns (AC: 3)
- [x] Figure (AC: 4)
- [x] Write-up, ADR (AC: 5, 6)
- [x] Tests, gates (AC: 7)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.4: LP disposes of withdrawn inventory`, push `story/5-4-lp-disposes-withdrawn-inventory`

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

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log

Hashes against main (d775a38), via a worktree on `PYTHONPATH`: all 16 scenario
`content_hash()` and all 17 existing sweep spec hashes identical (`differ: []`). Run
output of `calibrated-baseline-lp` and `soros-baseline` (seed in YAML): timeseries,
events and checkpoints byte-identical; only `summary.json` (the new keys) and the LP
scenario's `manifest.json` (`"after_withdrawal": "hold", "disposal_pace": 0.1` in the dumped
config) differ.

First build: `redeem` at 1.0x, share 0.5, seed 1000 made 17,758 `redeem_requested`, the
last at step 17,999 with `amount_stable` 1.86e-10 (residue of `balances - queued_redeem`).
After the `undisposed_stable` counter: 353 requests, steps 242-594 (same as `sell`'s 353
swaps); summary unchanged to the last digits (`redemption_paid_total` 10871507.33999682
-> 10871507.339996815).

```
$ python -m depeg_sim.sweep sweeps/lp-flight-disposal-mc.yaml --mc --workers 12
sweep: lp-flight-disposal-mc cells=216 workers=12
wrote: output/lp-flight-disposal-mc/sweep.parquet
mc: lp-flight-disposal-mc grid_points=27 seeds=8 runs=216
wrote: output/lp-flight-disposal-mc/mc.parquet
wall 51 s

$ python scripts/lp_flight_table.py --sweep output/lp-flight-disposal-mc --workers 12
hold: LP holds its withdrawn stable (8 seeds per cell; means in millions; no LP rows are the same in every block)
 ratio share recovered hours  trough_bps vs_hold  defender_M  arb_redeemed_M lp_pnl_M lp_paid_M lp_sold_M lp_redeemed_M
   0.5 no LP       8/8  18.3     -5774.3               41.35            4.61                                           
   0.5  0.25       8/8  11.5     -5774.3               41.35            2.98      0.1       0.0       0.0           0.0
   0.5   0.5       8/8   3.8     -5774.3               41.35            1.23      0.2       0.0       0.0           0.0
   0.5  0.75       8/8   0.4     -5774.3               39.88            0.60     0.36       0.0       0.0           0.0
   0.7 no LP       0/8  37.0     -6885.7               41.35           10.87                                           
   0.7  0.25       8/8  27.2     -6927.3               41.35            8.74     0.38       0.0       0.0           0.0
   0.7   0.5       8/8  17.0     -6913.6               41.35            5.49     0.72       0.0       0.0           0.0
   0.7  0.75       8/8   6.7     -6748.3               41.35            2.34     0.93       0.0       0.0           0.0
   1.0 no LP       0/8  48.2     -8151.2               41.35           10.87                                           
   1.0  0.25       8/8  35.4     -8191.1               41.35           10.58     0.98       0.0       0.0           0.0
   1.0   0.5       8/8  22.5     -8225.8               41.35            8.23     1.91       0.0       0.0           0.0
   1.0  0.75       8/8   9.5     -8196.1               41.35            3.82     2.62       0.0       0.0           0.0

sell: LP sells its withdrawn stable (8 seeds per cell; means in millions; no LP rows are the same in every block)
 ratio share recovered hours  trough_bps vs_hold  defender_M  arb_redeemed_M lp_pnl_M lp_paid_M lp_sold_M lp_redeemed_M
   0.5 no LP       8/8  18.3     -5774.3               41.35            4.61                                           
   0.5  0.25       8/8  25.8     -5930.0   +2.7%       41.35            7.83    -2.15       0.0      4.85           0.0
   0.5   0.5       8/8  26.1     -7961.3  +37.9%       41.35            8.89    -5.43       0.0       9.7           0.0
   0.5  0.75       8/8  17.4     -9181.2  +59.0%       41.35            7.30    -8.43       0.0     14.76           0.0
   0.7 no LP       0/8  37.0     -6885.7               41.35           10.87                                           
   0.7  0.25       8/8  36.2     -7634.5  +10.2%       41.35           10.73     -3.5       0.0      5.53           0.0
   0.7   0.5       8/8  30.6     -8755.0  +26.6%       41.35            9.71    -7.77       0.0     10.98           0.0
   0.7  0.75       8/8  19.4     -9612.5  +42.4%       41.35            7.67   -12.98       0.0     16.23           0.0
   1.0 no LP       0/8  48.2     -8151.2               41.35           10.87                                           
   1.0  0.25       0/8  42.4     -8432.0   +2.9%       41.35           10.87    -4.28       0.0      6.55           0.0
   1.0   0.5       8/8  33.4     -9142.7  +11.1%       41.35           10.21     -9.1       0.0     13.01           0.0
   1.0  0.75       8/8  20.1     -9721.2  +18.6%       41.35            7.79   -14.58       0.0     19.15           0.0

redeem: LP redeems its withdrawn stable (8 seeds per cell; means in millions; no LP rows are the same in every block)
 ratio share recovered hours  trough_bps vs_hold  defender_M  arb_redeemed_M lp_pnl_M lp_paid_M lp_sold_M lp_redeemed_M
   0.5 no LP       8/8  18.3     -5774.3               41.35            4.61                                           
   0.5  0.25       0/8  38.2     -5774.3   +0.0%       41.35            2.98     0.11      4.85       0.0          4.85
   0.5   0.5       8/8  34.2     -5774.3   +0.0%       41.35            0.68     0.21      9.67       0.0          9.67
   0.5  0.75       8/8   0.4     -5774.3   +0.0%       39.88            0.55     0.36       3.7       0.0           3.7
   0.7 no LP       0/8  37.0     -6885.7               41.35           10.87                                           
   0.7  0.25       0/8  57.6     -6927.3   +0.0%       41.35            5.35     0.38      5.53       0.0          5.53
   0.7   0.5       0/8 never     -6913.6   +0.0%       41.35            0.96     0.26      9.92       0.0          9.92
   0.7  0.75       0/8 never     -6748.3   +0.0%       41.35            0.90     0.11      9.97       0.0          9.97
   1.0 no LP       0/8  48.2     -8151.2               41.35           10.87                                           
   1.0  0.25       0/8 never     -8191.1   +0.0%       41.35            4.33     0.99      6.55       0.0          6.55
   1.0   0.5       0/8 never     -8225.8   +0.0%       41.35            1.35     0.03      9.52       0.0          9.52
   1.0  0.75       0/8 never     -8196.1   +0.0%       41.35            1.28     0.82      9.59       0.0          9.59
wall 20 s   (includes rerunning lp-flight-nolp, 24 runs)

$ python scripts/make_figures.py --workers 12
...
drew: lp_flight.png <- sweeps/lp-flight-mc.yaml
drew: lp_flight_disposal.png <- sweeps/lp-flight-disposal-mc.yaml
drew: identification_surface.png <- sweeps/usdc-par-depth-x-capital.yaml
wrote: 25 figures and docs/figures/manifest.json (commit d775a38f195c, code_hash 446e73ef88a9)
wall 26 s
(md5 of docs/figures/*.png before/after: only lp_flight_disposal.png added; the 24 others identical)

$ make test
TOTAL                                    988     10    99%
Required test coverage of 85% reached. Total coverage: 98.99%
1029 passed in 242.96s (0:04:02)

$ make lint
All checks passed!
114 files already formatted

$ make figures-check
figures-check: ok, 25 figures match their sources (code_hash matches)
figures-check: ok, 6 fits match their inputs (script hashes match)

$ make note-check
note-check: WARNING: freeze: v0.9-freeze (76e7a1cf6a03) manifest has code_hash a0ae9594e7a4..., the working tree's has 446e73ef88a9...
note-check: ok: figures: 7 cited figures exist and are in the manifest
note-check: ok: cited: all 7 listed figures not marked † are cited; none of the 4 record-only figures is
note-check: ok: freeze: v0.9-freeze is 76e7a1cf6a03 (code differs, see warning)
note-check: ok: numbers: 8 fitted values quoted as their records round them
```

### Completion Notes List

- **AC 1.** `LPConfig.after_withdrawal` (default `hold`) and `disposal_pace` (default 0.1,
  `0 < x <= 1`); `content_hash` drops each at its default. All 16 scenarios pinned as of
  main in `tests/test_lp_disposal.py` (the existing Story 3.7 pins cover 9).
- **AC 2.** Order `lp_withdraw` > `lp_sell` / `lp_redeem` > `lp_done` / `lp_hold`, one
  action per step, no `ctx.rng` (tested on the generator state). Judgment calls, all in
  ADR-0038:
  - disposal does not look at the price, so it starts only once withdrawals stop;
  - an LP with no shares left keeps disposing even below its panic price;
  - the amount is a share of the LP's own `undisposed_stable` counter, not
    `available_stable`, because of the float residue in the Debug Log;
  - the redeem tranche uses `disposal_pace`, not the holder's rule, and queues whatever
    the queue depth.
- **AC 3.** Sweep 216 runs (the panic-threshold axis dropped: inert, ADR-0031).
  `lp_flight_table.py --sweep` prints the per-mode tables. Summary columns
  `lp_sold_stable`, `lp_redeemed_stable`, **plus `lp_pnl`**: the table needs LP PnL and no
  run output had it. The soros-baseline summary pin is re-captured, layered like Story 5.3's.
- **AC 4.** `plot_lp_flight` dispatches on the `after_withdrawal` axis; `lp_flight.png`
  byte-identical.
- **AC 5.** `docs/calibration/LP_DISPOSAL.md` (linked from README), not VALIDATION.md,
  which is the USDC replay record. The sign of F-15 **splits**:
  - **sell** keeps recovery (8/8 in 5 of the 6 cells at 0.7x and 1.0x; 1.0x at share
    0.25 is 0/8) and reverses the trough (2.7-59.0% deeper than no LP);
  - **redeem** keeps the trough (identical to hold) and reverses recovery (0/8 in every
    0.7x and 1.0x cell, and at 0.5x share 0.25, where no LP is 8/8).
- **Prediction:** sell deepens the trough, yes, but about 190 steps behind the attacker, not
  one. Sell back to 0/8: only 1 of the 6 cells at 0.7x and 1.0x. Redeem leaves the trough
  alone: yes. Redeem's effect on recovery: it hurts.
- **AC 6.** ADR-0038 Proposed. FINDINGS.md and the ADR index not edited.
- **No scheduler change**; the LP acts in the agent phase as before.
- Every seed in a cell gives the same trough and hours (min = max over seeds).

### File List

- `src/depeg_sim/kernel/config.py` (modified)
- `src/depeg_sim/agents/lp.py` (modified)
- `src/depeg_sim/analysis/summary.py` (modified)
- `src/depeg_sim/experiments/mc.py` (modified)
- `src/depeg_sim/analysis/charts.py` (modified)
- `sweeps/lp-flight-disposal-mc.yaml` (new)
- `scripts/lp_flight_table.py` (modified)
- `scripts/make_figures.py` (modified)
- `Makefile` (modified)
- `tests/test_lp_disposal.py` (new)
- `tests/test_lp.py`, `tests/test_summary.py`, `tests/test_reference_recovery.py`,
  `tests/test_figures.py` (modified)
- `docs/calibration/LP_DISPOSAL.md` (new), `README.md` (modified)
- `docs/adr/0038-lp-disposes-withdrawn-inventory.md` (new)
- `docs/figures/lp_flight_disposal.png` (new), `docs/figures/manifest.json`,
  `docs/figures/README.md`, `docs/NOTE.md` (figure list only) (modified)
- `docs/stories/5-4-lp-disposes-withdrawn-inventory.md` (this file)

## Change Log

- 2026-10-15: Story drafted by dev manager (Epic 5)
- 2026-10-17: Implemented (builder); sweep run once into output/; ADR-0038 proposed; status review
