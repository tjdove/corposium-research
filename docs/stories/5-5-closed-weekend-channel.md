# Story 5.5: Closed Weekend Channel

Status: done

## Story

As a **reader who was on a desk that weekend**,
I want the par-reference replay run with the weekend redemption channel closed, and nearly closed, until Monday's reopening,
so that we learn whether the two-day plateau the model does not reproduce (F-16) is a redemption-throughput story.

## Why

F-16: with nothing from the observed series fed in, the model is at par from 40 h while
the real price sat 150–524 bps below par until 69 h. Referee §5.15: the calibrated
weekend capacity (605.79/step) is an average over 11–15 March that includes Monday's
catch-up and probably overstates what the channel paid while banks were closed. If the
channel was effectively shut, the arbitrageur cannot recycle and the holder cannot
redeem; what the price does then is the test.

## Acceptance Criteria

1. Two scenarios from `usdc-2023-tranches-par.yaml` (ladder B), differing only in `name`
   and the redemption block: `usdc-2023-tranches-par-closed.yaml` with `capacity_per_step
   0` until step 25,500 then 19,181.59; `usdc-2023-tranches-par-slow.yaml` with 60.579
   (10% of calibrated) until 25,500 then 19,181.59. If `capacity_per_step 0` is rejected by
   the config or breaks a division somewhere, make the smallest change that allows it and
   say so; do not use a tiny positive number as a workaround without saying so.
2. `scripts/replay_table.py` gains the two rows (reuse everything; add a `--extra` list or
   extend the built-in list, builder's choice).
3. One overlay figure, `validation_overlay_usdc_2023_tranches_par_closed.png`: observed
   (blue), par-reference open channel (grey, dashed), par-reference closed channel (black),
   using the two-source mechanism of ADR-0033. Captioned, in `make figures`, manifest,
   figure list (†).
4. VALIDATION.md "Closed weekend channel (Story 5.5)": the table rows, the trough, where the
   price sits from 35 h to 85 h (min, max, mean deviation over that window, for closed,
   slow, open), and what happens at the 85 h reopening. Numbers only.
5. Also report what the holder does when it cannot redeem: how much stable it holds at
   85 h, and its PnL at 85 h and 112 h.
6. Tests: scenario hash pins; `capacity 0` path covered. `pytest`, `ruff`, `make figures-check`.

## Tasks / Subtasks

- [x] Scenarios (AC: 1)
- [x] Table rows (AC: 2)
- [x] Figure (AC: 3)
- [x] VALIDATION.md (AC: 4, 5)
- [x] Tests, gates (AC: 6)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.5: closed weekend channel`, push `story/5-5-closed-weekend-channel`

## Dev Notes

### Learnings from Previous Story

- 5.1 built everything this story needs: par scenarios, the table, two-source figures.
  This is a half-day story; keep it that way.
- The holder's `redeem_when_capacity` rule needs the queue empty and capacity > 0 to act;
  with capacity 0 it should sit in `hold_wait`. Confirm by reading `holder.py`, and say in
  VALIDATION.md what it did.
- Watch the capacity-schedule change at step 25,500 with a queue that has been
  accumulating for 58 h: the arbitrageur's queued requests may all clear at once.

### Prediction (to be checked, not aimed at)

Closed: the trough is unchanged (set before 31 h by attacker vs ladder), and from ~33 h
the price sits at the last tranche's entry (−2,000 bps?) or wherever the holder's buying
stops, until 85 h — too deep, not the observed −150…−524. Slow (10%): somewhere between.
If so, the plateau is not a throughput story alone; the real weekend had buying the model
lacks *and* a channel slower than calibrated. Record whichever.

### References

- [Source: docs/FINDINGS.md#F-16, docs/adr/0033-par-reference-replay.md]
- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §5.15–5.16]
- [Source: scenarios/usdc-2023-tranches-par.yaml, scripts/replay_table.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code.

### Debug Log References

Branch `story/5-5-closed-weekend-channel` from `main` at `3d56237`.

`capacity_per_step: 0` was rejected by `RedemptionConfig` (`Field(gt=0)`) and by
`RedemptionModule.__init__` (`> 0`). Both now accept `>= 0`; see Completion Notes.

`python scripts/replay_table.py` (22 s wall):

```
replay                             hash         trough bps   step     h re-entry h in band h holder bought holder redeemed holder PnL arb redeemed
--------------------------------------------------------------------------------------------------------------------------------------------------
observed (Bitstamp hourly close)                  -1,373.3    n/a  31.0       86.0       8.0           n/a             n/a        n/a          n/a
observed ref, single entry         2c3aeaa9825d   -1,137.8  10269  34.2       85.3      10.7     9,418,433       9,418,433    209,360    2,098,246
observed ref, ladder B             da3383d4e156   -1,323.3   9346  31.2       85.3      10.7     8,662,811       8,662,811    522,643    2,853,889
par ref, single entry              7f3d0c583694     -607.2   9886  33.0       37.2      58.8     9,372,636       9,372,636    205,969    2,161,592
par ref, ladder B                  32a610a514f2   -1,279.2   9850  32.8       40.4      55.6     8,646,604       8,646,604    521,604    2,890,043
OU ref, single entry               77fc93f2f784     -607.2   9886  33.0       37.2      58.8     9,372,636       9,372,636    205,969    2,154,338
OU ref, ladder B                   b219b783b6a3   -1,279.2   9850  32.8       40.4      55.6     8,646,604       8,646,604    521,604    2,891,844
par ref, ladder B, channel 10%     90c61264e8c2   -2,001.1   9558  31.9       85.2      10.9     9,128,561       9,128,561    619,886    2,403,544
par ref, ladder B, channel closed  c2e0f5a7cf57   -2,001.2   9485  31.6       85.3      10.7     9,370,888       9,370,888    668,573    2,168,597
band ±31 bps; in band h over 27-96 h; model units (1M = $234.6M)
```

`python scripts/closed_channel_table.py` (9 s wall):

```
1. AMM price, 35-85 h (bps from peg, every step)
weekend channel            min       max      mean in band h
------------------------------------------------------------
observed (hourly)       -955.4     -48.4    -335.4      0.00
open (605.79/step)    -1,084.3      -0.0     -66.6     44.57
10% (60.579/step)     -2,000.2  -1,060.9  -1,563.9      0.00
closed (0/step)       -2,000.2  -2,000.0  -2,000.0      0.00

2. the reopening at 85 h (capacity -> 19,181.59/step)
weekend channel        bps at    queue at queue empty deepest after  in band  queued by source at the reopening
---------------------------------------------------------------------------------------------------------------
open (605.79/step)       -3.4       3,029       85.00          -3.4    85.00  holder-1 3,029
10% (60.579/step)    -1,060.9     395,584       85.23      -1,060.9    85.16  arb-1 395,584
closed (0/step)      -2,000.0     201,339       85.38      -2,000.0    85.31  arb-1 201,339
bps at, queue at: the last step before the reopening; queue empty, in band: first hour from the reopening step on

3. the arbitrageur (reference)
weekend channel       bought 27-31 h  paid 27-31 h  bought 35-85 h  paid 35-85 h
--------------------------------------------------------------------------------
open (605.79/step)           923,919       724,525       1,013,436     1,438,570
10% (60.579/step)            272,392        72,452         908,685       908,685
closed (0/step)              200,000             0               0             0
bought: spent on AMM buy_stable swaps; paid: by the redemption channel

4. the holder (checkpoints)
weekend channel        at h      stable      queued   reference        PnL
--------------------------------------------------------------------------
open (605.79/step)     85.0     998,505       3,029  10,356,432    521,265
open (605.79/step)    112.0           0           0  11,354,937    521,604
10% (60.579/step)      85.0   9,128,561           0   2,324,659   -348,569
10% (60.579/step)     112.0           0           0  11,453,219    619,886
closed (0/step)        85.0   9,370,888           0   2,131,018 -1,205,605
closed (0/step)       112.0           0           0  11,501,906    668,573

model units (1M = $234.6M); PnL marked at AMM spot
```

Holder and arbitrageur rule counts (VALIDATION.md, ADR-0035) come from an ad-hoc run of
the three scenarios with `metrics.trace_decisions: true` and `checkpoint_every: 25500`
(nothing else changed), counting `decisions.jsonl` rules per window by `step x 12 / 3600`:

```
closed  holder 27-31 h {'hold_done': 17, 'hold_buy': 1183}
closed  holder 31-35 h {'hold_buy': 1200}
closed  holder 35-85 h {'hold_buy': 12750, 'hold_wait': 2250}
closed  holder 85-112 h {'hold_wait': 602, 'hold_redeem': 49, 'hold_done': 7449}
closed  arb    27-31 h {'arb_idle': 1187, 'arb_waiting_latency': 5, 'arb_buy_amm': 4, 'arb_redeem': 4}
closed  arb    35-85 h {'arb_idle': 15000}
closed  tranches@85h [(2.0, 0, 2777066), (5.0, 0, 2859553), (10.0, 0, 3012613), (20.0, 2131018, 721656)]
slow    holder 35-85 h {'hold_wait': 14762, 'hold_buy': 238}
slow    holder 85-112 h {'hold_wait': 546, 'hold_redeem': 48, 'hold_done': 7506}
tranches buying 35-85 h: open {}, closed {3: 12750}, slow {3: 238}   (index 3 = 20% tranche)
deviation after 85.4 h, min/max bps: open -3.4/-3.4, closed -0.0/-0.0, slow -8.85/-8.85
arb buy_amm 27-31 h: open 400, closed 4 (27.01-27.04 h), slow 400
```

`make figures` (full, 12 workers):

```
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 140 s
sweep sweeps/threshold-surface-mc.yaml: wall time 137 s
sweep sweeps/budget-x-depth-mc.yaml: wall time 50 s
sweep sweeps/oracle-lag-mc.yaml: wall time 116 s
sweep sweeps/policy-comparison-mc.yaml: wall time 77 s
sweep sweeps/holder-exit-1992-mc.yaml: wall time 19 s
sweep sweeps/budget-x-attack-mc.yaml: wall time 57 s
sweep sweeps/pace-x-trigger-mc.yaml: wall time 88 s
sweep sweeps/pace-ratio-mc.yaml: wall time 24 s
sweep sweeps/threshold-surface-ou-mc.yaml: wall time 133 s
sweep sweeps/lp-flight-mc.yaml: wall time 47 s
sweep sweeps/usdc-par-depth-x-capital.yaml: wall time 17 s
drew: validation_overlay_usdc_2023_tranches_par_closed.png <- scenarios/usdc-2023-tranches-par.yaml + scenarios/usdc-2023-tranches-par-closed.yaml + scenarios/usdc-2023-tranches.yaml
wrote: 23 figures and docs/figures/manifest.json (commit 3d56237dffb5, code_hash d44ea724c7c1)
fits: wall time 24 s
make figures: wall time 960 s (12 workers)
exit 0
```

The 22 existing PNGs and the 4 fit records are byte-identical to `main` (`git status`
shows only `manifest.json` and the new PNG). The committed PNG's sha256 matches the
render reviewed during layout (`87e4d4f5628d`).

Gates (`make test`, `make lint`, `make figures-check`):

```
src/depeg_sim/protocol/oracle.py          71      0   100%
src/depeg_sim/protocol/redemption.py     153      2    99%
----------------------------------------------------------
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
971 passed in 142.92s (0:02:22)
== lint
All checks passed!
.venv/bin/python -m ruff format --check .
111 files already formatted
== figures-check
.venv/bin/python scripts/check_figures.py
figures-check: ok, 23 figures match their sources (code_hash matches)
figures-check: ok, 4 fits match their inputs (script hashes match)
```

`make note-check`: exit 0. The one warning is the expected `v0.9-freeze` code-hash
mismatch (freeze manifest `a0ae9594…`, working tree `d44ea724…`); 4 ok lines.

### Completion Notes List

- **Capacity 0 (AC 1).** The config and the module rejected 0. The smallest change was
  `ge=0` in `RedemptionConfig.capacity_per_step` and `>= 0` in `RedemptionModule`.
  `capacity_schedule` entries still need > 0; the reopening is > 0, so allowing 0 there
  was not needed. No division uses capacity: `process` fills nothing (`cap > EPS` loop),
  and the holder's `_tranche` is `min(avail, 0 x 10) = 0`, so `decide` falls through to
  `hold_wait`. That is the behaviour Dev Notes expected, confirmed by reading `holder.py`
  and by test. The arbitrageur's redeem rule does not read capacity, so it queues. No
  tiny positive number is used.
- **Scenarios.** `usdc-2023-tranches-par-slow.yaml` (60.579) and `-closed.yaml` (0), with
  hashes `90c61264e8c2…` and `c2e0f5a7cf57…` pinned. Only `name` and
  `redemption.capacity_per_step` differ from the base (tested). They are added to the
  four "every scenario" pin lists, as 5.1 did.
- **Table (AC 2).** Two rows appended to `replay_table.REPLAYS` (built-in list).
- **AC 4-5.** `scripts/closed_channel_table.py` covers the 35-85 h window (with an
  observed row for comparison), the reopening, the arbitrageur's buying and payouts, and
  the holder at 85 h and 112 h from checkpoints. The analysis runs set
  `checkpoint_every` to 25,500, so the first checkpoint is the state after 85 h, before
  the reopening step. Rows are stamped `step x 12 s`, so "before the reopening" means
  `step < 25500`.
- **Figure (AC 3).** The figure needs three runs: the CSV can only come from a run fed
  it (ADR-0033 rejected a fixed path), and neither par run was. So
  `make_figures.Figure.observed` names a scenario that is run only for its CSV, and the
  manifest and guard record and check `observed_source` like `second_source`.
  `plot_validation_overlay(..., observed_from=)` reads the CSV from there. When the two
  drawn runs' capacities differ, the legend and title name each one's channel, the title
  wraps, and the legend sits below the axes; the first three placements covered the
  trough label or the 85 h jump. All 22 existing PNGs came out byte-identical.
- **Results (recorded; VALIDATION.md "Closed weekend channel (Story 5.5)").**
  - **The prediction was half wrong.** The trough is *not* unchanged: −1,279.2 becomes
    −2,001.1 (10%) and −2,001.2 (closed), the 20% tranche's entry, 45.7% deeper than
    observed. In 27-31 h the closed arbitrageur buys only its 200,000 of capital (open:
    923,919, with 724,525 recycled through the channel).
  - **The rest holds.** Closed, the price sits at −2,000.0…−2,000.2 for all of 35-85 h
    (observed −955…−48, mean −335). At 10% it rises from −2,000 to −1,061 (mean −1,564).
  - **The reopening.** The queue is all the arbitrageur's (201,339 closed, 395,584 at
    10%). It clears by 85.38 / 85.23 h, and the price is back in band at 85.31 / 85.16 h.
    First back in band, 85.3 / 85.2 h against 86.0 h observed; hours in band over 27-96 h,
    10.7 / 10.9 against 8.0 observed.
  - **The holder (AC 5).** Closed, it queues nothing before 85 h. It buys at the 20%
    entry on 12,750 of the 15,000 steps in 35-85 h and waits on the rest. At 85 h it holds
    9,370,888 stable, PnL −1,205,605. At 112 h it has redeemed it all, PnL +668,573 (open
    +521,604). At 10%: 9,128,561 stable, −348,569 at 85 h, +619,886 at 112 h.
- **ADR-0035 (Proposed):** finding + interface (capacity 0, `Figure.observed`,
  `observed_from`). FINDINGS.md not edited.
- Not touched: the base scenarios, every fit and fit record, pace, D\*, C\*, phase order.

### File List

- `src/depeg_sim/kernel/config.py` (`capacity_per_step: ge=0`)
- `src/depeg_sim/protocol/redemption.py` (`>= 0`, docstring)
- `src/depeg_sim/analysis/charts.py` (`plot_validation_overlay(observed_from=)`,
  `_channel`, channel labels/layout)
- `scenarios/usdc-2023-tranches-par-slow.yaml`, `scenarios/usdc-2023-tranches-par-closed.yaml` (new)
- `scripts/replay_table.py` (two rows), `scripts/closed_channel_table.py` (new)
- `scripts/make_figures.py` (`Figure.observed`, registry entry, manifest keys),
  `scripts/check_figures.py` (`observed_source`)
- `tests/test_closed_channel.py` (new); `tests/test_redemption.py`, `tests/test_holder.py`
  (capacity 0); `tests/test_figures.py` (observed-source guard, count 23);
  `tests/test_par_replay.py` (row count); `tests/test_holder_config.py`,
  `tests/test_holder_tranches.py`, `tests/test_reference_recovery.py` (pin lists)
- `docs/figures/validation_overlay_usdc_2023_tranches_par_closed.png` (new),
  `docs/figures/manifest.json` (regenerated), `docs/figures/README.md` (row, caption)
- `docs/NOTE.md` (figure list row 1f †, change-log line; text not edited)
- `docs/calibration/VALIDATION.md` (section "Closed weekend channel (Story 5.5)")
- `docs/adr/0035-closed-weekend-channel.md` (new, Proposed)
- `docs/stories/5-5-closed-weekend-channel.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager) · **Date:** 2026-10-16 · **Verdict: APPROVE**

Reproduced on the review box at `0e7e255`: `pytest -q` all pass (exit 0); `ruff` clean;
`make figures-check` → 23 figures, 4 fits ok. `python scripts/closed_channel_table.py`
(26 s) and `replay_table.py`: every number matches the story and ADR-0035 — closed
trough −2,001.2 at 31.6 h, back in band 85.3 h; 10% −2,001.1 at 31.9 h, 85.2 h; 35–85 h
mean −2,000.0 / −1,563.9 / −66.6 against −335.4 observed; arbitrageur bought 200,000 /
272,392 / 923,919 in 27–31 h; holder at 85 h 9.37M stable, PnL −1.21M, at 112 h +669k.
Config change (`capacity_per_step: ge=0`, redemption accepts 0, schedule entries still
> 0) read and is the smallest change; no tiny-positive workaround. The figure's
`observed` third source is the right design and the guard covers it.

**What the result means (the dev manager's call).** Recorded as **F-17**.

1. *The model brackets the weekend and reality is inside the bracket.* Channel open at
   the calibrated rate: back at par by 40 h (too fast). Channel shut: pinned at the last
   tranche's price, −2,000 bps, for fifty hours, then back in band at 85.3 h against
   86.0 h observed (right time, wrong depth). The real price drifted from −1,373 up
   through −500 … −150 over two days *with the channel mostly shut*. So the plateau is
   not a throughput story: a shut channel gives a floor, not a drift. What moved the real
   price between Saturday 2 am and Monday was buyers whose reservation prices rose as
   news arrived (Circle's Saturday statement; the 6:15 pm Sunday guarantee is visible in
   the blue line as the jump near 66–70 h). **Belief in the model is a switch; in the
   weekend it was a process.** That is the mechanism the model lacks, named.
2. *The trough depends on the channel paying in the first four hours.* With the channel
   shut, the arbitrageur has only its 200k and the 20% tranche takes the whole tail:
   −2,001 instead of −1,279. The 724k the channel paid the arbitrageur during 27–31 h in
   the open replay was doing believers' work. If the real channel was shut on Friday
   night — and it was, to a first approximation — then the believers' capital that
   reproduces −1,373 is **larger than C\***. The 5.2 family (0.82–1.07× C\*) is conditional
   on the open channel; Story 5.6 measures the closed-channel C\*.
3. *The believer at a pinned price.* With no redemption, the 20% tranche keeps buying at
   $0.80 for 12,750 of 15,000 steps, ends the weekend holding 9.37M stable at −1.2M PnL,
   and is +669k by Tuesday. That is the believer holding the floor at its own price and
   being paid for it on Monday — the model's version of the weekend trade.

**Rulings**

1. **ADR-0035 accepted (finding + interface).** Index row added. F-17 in FINDINGS.
2. Figure 1f stays †; v2 cites it beside 1d as the two ends of the bracket.
3. Rule counts from a one-off traced run: acceptable, since the Debug Log carries the
   command and output; if v2 quotes "12,750 of 15,000 steps" it cites the story.
4. **Story 5.6 added (tiny): closed-channel capital scan.** `fit_holder.py` rule on
   `usdc-2023-tranches-par-closed.yaml` (ladder B, D\* fixed, pace fixed): the C\* that
   lands closest to −1,373 with the channel shut, and the ±10% range. One table row, one
   fit record. No figure. This is the number v2 quotes next to C\*.

**Lessons:** prediction half wrong (trough moved), recorded (L-15). The builder's framing
"recovery timing matches and the trough depth doesn't, the reverse of the open-channel
run" is the finding in one line.

## Change Log

- 2026-10-15: Story drafted by dev manager (5.1 review, ruling 5)
- 2026-10-16: Implemented by Claude Code (Opus 5.5): closed and 10% weekend-channel scenarios (capacity 0 allowed), two replay-table rows, `closed_channel_table.py`, overlay with an observed source, VALIDATION.md section, ADR-0035 proposed. Trough deepens to −2,001 (prediction said unchanged); price sits at −2,000 until 85 h; back in band at 85.3 h (observed 86.0). Status: review.
- 2026-10-16: Reviewed by dev manager — APPROVE; ADR-0035 accepted; F-17; Story 5.6 added; Status: done
