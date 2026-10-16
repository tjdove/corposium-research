# Story 5.6: Closed-Channel Capital Scan

Status: ready-for-dev

## Story

As a **reader who knows the channel was shut on Friday night**,
I want the believers' capital that reproduces the observed trough when the weekend redemption channel is closed,
so that the note can quote C\* with the condition it depends on, and the number without it.

## Why

F-17: with the channel shut, the trough falls to −2,001 at C\* because the arbitrageur
can no longer recycle 724k of channel payments into buying during 27–31 h; that money
was doing believers' work. The real channel was shut, to a first approximation. So the
C\* that matters for the "how much believers' money" claim is the one fitted with the
channel shut.

## Acceptance Criteria

1. `scripts/fit_holder.py` run on `scenarios/usdc-2023-tranches-par-closed.yaml` with
   `--tranches 2:0.25,5:0.25,10:0.25,20:0.25` and the unchanged two-pass rule (log grid
   1M…100M, two 5-point refinements, closest to −1,373, ties to the smaller). D\* and
   pace fixed. `--write docs/calibration/fits/holder-ladder-b-closed.json`. No other
   script changes unless the closed scenario needs one; say so.
2. The same on `usdc-2023-tranches-par.yaml` (open channel, par reference) →
   `holder-ladder-b-par.json`, so the three C\* (observed-reference 10,833,333; par-open;
   par-closed) sit in one table.
3. `scripts/identification_table.py` gains a fourth table: the three C\*, each with its
   trough, trough time, re-entry, and the ±10% capital range from a 5-point linear scan
   around the pick (same spacing as the refinement). `make figures-check --fits` covers
   the two new records.
4. VALIDATION.md "Closed-channel C\* (Story 5.6)": the table, in the builder's words.
   SOURCES.md's holder row gains one line pointing at it.
5. Tests: fit records byte-stable on re-run; table smoke test. `pytest`, `ruff`,
   `make figures-check`.

## Tasks / Subtasks

- [ ] Two fits with records (AC: 1, 2)
- [ ] Table (AC: 3)
- [ ] Docs (AC: 4)
- [ ] Tests, gates (AC: 5)
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 5.6: closed-channel capital scan`, push `story/5-6-closed-channel-capital-scan`

## Dev Notes

### Learnings from Previous Story

- `fit_holder.py` already supports `--tranches` and `--write` (Stories 3.7, 4.1). Each
  replay run is ~2 s; the two-pass rule is ~12 runs per fit.
- With the channel shut the trough sits on a tread (ADR-0034), so the pick may be a
  knife-edge between two treads; report both neighbours' troughs so the reader sees it.
- Do not touch `usdc-2023.yaml` or `usdc-2023-tranches.yaml`; their C\* stays the
  observed-reference fit.

### Prediction (to be checked, not aimed at)

Closed-channel C\* lands between 1.1× and 1.3× the open one (≈ 12–14M, $2.8–3.3B), where
the 10% tranche has enough to outlast the attack's tail without the arbitrageur's help.
Record whichever.

### References

- [Source: docs/FINDINGS.md#F-17, docs/adr/0035]
- [Source: docs/stories/5-5-closed-weekend-channel.md#Senior-Developer-Review ruling 4]
- [Source: scripts/fit_holder.py, docs/calibration/fits/holder-ladder-b.json]

## Dev Agent Record

## Change Log

- 2026-10-16: Story drafted by dev manager (5.5 review, ruling 4)
