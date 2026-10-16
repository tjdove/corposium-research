# Story 5.5: Closed Weekend Channel

Status: ready-for-dev

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

- [ ] Scenarios (AC: 1)
- [ ] Table rows (AC: 2)
- [ ] Figure (AC: 3)
- [ ] VALIDATION.md (AC: 4, 5)
- [ ] Tests, gates (AC: 6)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.5: closed weekend channel`, push `story/5-5-closed-weekend-channel`

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

## Change Log

- 2026-10-15: Story drafted by dev manager (5.1 review, ruling 5)
