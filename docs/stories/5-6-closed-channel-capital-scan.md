# Story 5.6: Closed-Channel Capital Scan

Status: review

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

- [x] Two fits with records (AC: 1, 2)
- [x] Table (AC: 3)
- [x] Docs (AC: 4)
- [x] Tests, gates (AC: 5)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.6: closed-channel capital scan`, push `story/5-6-closed-channel-capital-scan`

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

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log

Fits (`fit_holder.py` unchanged; output trimmed to the passes and the result):

```
$ python scripts/fit_holder.py --scenario scenarios/usdc-2023-tranches-par-closed.yaml \
    --tranches 2:0.25,5:0.25,10:0.25,20:0.25 --workers 6 --output $SCRATCH/fit-closed \
    --write docs/calibration/fits/holder-ladder-b-closed.json
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -6,152.1              23156     max_steps      33600
        2000000       -5,813.2              23157     max_steps      33600
        5000000       -4,480.3              23208     max_steps      33600
       10000000       -2,002.4               9160     max_steps      33600
       20000000       -1,000.1              10834     max_steps      33600
       50000000         -225.9               8117     max_steps      33600
      100000000         -225.9               8117     max_steps      33600
refine pass 1 between 10,000,000 and 50,000,000 (pick 20,000,000):
       16666667       -1,003.6               9035     max_steps      33600
       23333333         -510.1               8545     max_steps      33600
       30000000         -506.8               8743     max_steps      33600
       36666667         -503.4               9109     max_steps      33600
       43333333         -307.9              23489     max_steps      33600
refine pass 2 between 10,000,000 and 20,000,000 (pick 16,666,667):
       11666667       -2,000.1              10740     max_steps      33600
       13333333       -1,007.0               8696     max_steps      33600
       15000000       -1,005.4               8837     max_steps      33600
       16666667       -1,003.6               9035     max_steps      33600
       18333333       -1,001.9               9368     max_steps      33600
C* = 13333333 (trough -1007.0 bps) ≈ $3,127,999,922 at s = 0.0042625746 units/$
wrote docs/calibration/fits/holder-ladder-b-closed.json
real	0m10.602s

$ python scripts/fit_holder.py --scenario scenarios/usdc-2023-tranches-par.yaml \
    --tranches 2:0.25,5:0.25,10:0.25,20:0.25 --workers 6 --output $SCRATCH/fit-par \
    --write docs/calibration/fits/holder-ladder-b-par.json
grid pass (target -1373 bps):
        1000000       -5,420.1               9529     max_steps      33600
        2000000       -5,033.7               9568     max_steps      33600
        5000000       -3,500.0               9703     max_steps      33600
       10000000       -1,860.7               9814     max_steps      33600
       20000000         -511.4               8487     max_steps      33600
       50000000         -225.8               8118     max_steps      33600
      100000000         -225.8               8118     max_steps      33600
refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
        7500000       -2,005.0               8787     max_steps      33600
       10000000       -1,860.7               9814     max_steps      33600
       12500000       -1,007.2               8686     max_steps      33600
       15000000       -1,004.3               8950     max_steps      33600
       17500000         -877.9               9871     max_steps      33600
refine pass 2 between 10,000,000 and 15,000,000 (pick 12,500,000):
       10833333       -1,279.2               9850     max_steps      33600
       11666667       -1,008.1               8625     max_steps      33600
       12500000       -1,007.2               8686     max_steps      33600
       13333333       -1,006.3               8758     max_steps      33600
       14166667       -1,005.3               8844     max_steps      33600
C* = 10833333 (trough -1279.2 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
wrote docs/calibration/fits/holder-ladder-b-par.json
real	0m11.584s
```

Table 4 (`time python scripts/identification_table.py --workers 6`; tables 1–3 unchanged
from Story 5.2, 1m12.8s in all):

```
4. ladder B's C* by fit, with a 5-point scan at the second refinement's spacing; ±10% range (-1,510.6 to -1,236.0 bps), linear between scan points
fit                                        C*    $B trough bps    gap     h re-entry h      step  scan troughs, k = -2..2 (bps)         ±10% range (capital)    inside
observed reference, channel open   10,833,333  2.54   -1,323.3  +3.6%  31.2       85.3   833,333  -2,002 -1,859 -1,323 -1,069 -1,007    10,541,654-11,119,473   1 of 5
par reference, channel open        10,833,333  2.54   -1,279.2  +6.9%  32.8       40.4   833,333  -2,002 -1,861 -1,279 -1,008 -1,007    10,501,679-10,966,140   1 of 5
par reference, channel closed      13,333,333  3.13   -1,007.0 +26.7%  29.0       85.1 1,666,667  -2,002 -2,000 -1,007 -1,005 -1,004    12,488,146-12,949,109   0 of 5
  observed reference, channel open (holder-ladder-b.json) scan: 9,166,667 -> -2,002.3 at 30.6 h; 10,000,000 -> -1,858.6 at 32.7 h; 10,833,333 -> -1,323.3 at 31.2 h; 11,666,667 -> -1,069.0 at 34.5 h; 12,500,000 -> -1,007.2 at 29.0 h
  par reference, channel open (holder-ladder-b-par.json) scan: 9,166,667 -> -2,002.3 at 30.6 h; 10,000,000 -> -1,860.7 at 32.7 h; 10,833,333 -> -1,279.2 at 32.8 h; 11,666,667 -> -1,008.1 at 28.8 h; 12,500,000 -> -1,007.2 at 29.0 h
  par reference, channel closed (holder-ladder-b-closed.json) scan: 10,000,000 -> -2,002.4 at 30.5 h; 11,666,667 -> -2,000.1 at 35.8 h; 13,333,333 -> -1,007.0 at 29.0 h; 15,000,000 -> -1,005.4 at 29.5 h; 16,666,667 -> -1,003.6 at 30.1 h
```

One-off between the closed fit's neighbours (scratch `cliff_scan.py`, not committed: the
closed scenario with `agents[type=holder].capital` set to each of
`np.linspace(11_666_667, 13_333_333, 11)[1:-1]`, `run_scenario`, `summary.json`):

```
 11,833,333  -1,936.0 bps at  78.0 h
 12,000,000  -1,819.5 bps at  78.0 h
 12,166,666  -1,700.5 bps at  78.0 h
 12,333,333  -1,578.9 bps at  78.1 h
 12,500,000  -1,454.6 bps at  78.1 h
 12,666,666  -1,327.5 bps at  78.1 h
 12,833,333  -1,197.5 bps at  78.1 h
 12,999,999  -1,064.6 bps at  78.2 h
 13,166,666  -1,007.2 bps at  28.9 h
```

The 12,500,000 run's timeseries at selected hours (peg_deviation in bps, attacker_stable,
redemption_queued_total): 31 h −1,002.1, 1,042,337, 201,339; 35 h −1,364.4, 94,332;
40 h −1,450.1, 4,682; 50 h −1,454.6, 12; 60–85 h −1,454.6, 0, 201,339 (182,158 at 85 h);
85.5 h −15.7.

Gates:

```
$ time make test
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
980 passed in 192.11s (0:03:12)
$ make lint
All checks passed!
111 files already formatted
$ make figures-check
figures-check: ok, 23 figures match their sources (code_hash matches)
figures-check: ok, 6 fits match their inputs (script hashes match)
$ make note-check
note-check: ok: figures: 7 cited figures exist and are in the manifest
note-check: ok: cited: all 7 listed figures not marked † are cited; none of the 4 record-only figures is
note-check: ok: freeze: v0.9-freeze is 76e7a1cf6a03 (code differs, see warning)
note-check: ok: numbers: 8 fitted values quoted as their records round them
```

### Completion Notes List

- **AC 1–2.** Both fits ran with `fit_holder.py` unchanged; the closed scenario needed no
  script change. Closed: **C\* = 13,333,333 ≈ $3.13B (1.23× the open C\*), trough
  −1,007.0 bps (+26.7%)**. Open, par reference: 10,833,333 (−1,279.2), the same capital as
  the observed-reference fit. `make figures` now also re-writes the two records (Makefile,
  not a script).
- **Knife-edge (Dev Notes).** The closed pick's neighbours are 11,666,667 → −2,000.1 and
  13,333,333 → −1,007.0, one on each tread; the rule takes the second (366 bps from the
  target against 627). No capital the rule ran is within ±10% of −1,373.
- **AC 3, table 4.** "5-point linear scan around the pick (same spacing as the refinement)"
  is read as C\* + k × the second refinement's spacing, k = −2…2, recomputed from the
  record's runs by replaying the rule (no change to `fit_holder.py` or the existing
  records). "±10% capital range" is read as the capital over which the trough is within
  ±10% of the observed trough, linear between scan points, as table 2 does for ±5%. The
  closed range, 12,488,146–12,949,109, comes from interpolating between two scan points;
  no scan point is inside.
- **Beyond the ACs, flagged.** One one-off run of nine capitals across the closed step
  (Debug Log): between the treads the trough is close to linear in capital, and 12.5M and
  12.67M are inside ±10%. In those runs the trough is a level the price reaches by 40–50 h
  and holds until 85 h (the recorded step is 78 h only because the level creeps by
  < 0.1 bps), not a 31 h low. So, with the channel shut, no ladder-B capital gives both
  the depth and the shape. That is in VALIDATION.md and ADR-0036 as context; it is not a
  fit, and the record holds the rule's 13,333,333.
- **Prediction** (1.1–1.3×, $2.8–3.3B): the number is in range (1.23×); the trough at the
  pick is on the −1,000 tread, not at the target. Recorded, not aimed at.
- **ADR-0036 Proposed** (finding + the table-4 scan definition). Index and FINDINGS.md not
  edited. No `src/` change, so the code hash and figures are unchanged.

### File List

- `docs/calibration/fits/holder-ladder-b-par.json` (new)
- `docs/calibration/fits/holder-ladder-b-closed.json` (new)
- `scripts/identification_table.py` (table 4: `FITS`, `refine_step`, `scan_capitals`, `fit_scan`)
- `Makefile` (`figures` re-writes the two records)
- `tests/test_fit_record.py` (records listed and pinned; byte re-run of both fits)
- `tests/test_identification.py` (scan lattice tests; smoke test covers table 4)
- `docs/calibration/VALIDATION.md` ("Closed-channel C\* (Story 5.6)")
- `docs/calibration/SOURCES.md` (ladder-B capital row)
- `docs/adr/0036-closed-channel-capital-scan.md` (new, Proposed)
- `docs/stories/5-6-closed-channel-capital-scan.md`

## Change Log

- 2026-10-16: Story drafted by dev manager (5.5 review, ruling 4)
- 2026-10-16: Implemented by Claude Code (Opus 5.5): two par-reference ladder-B fit records, table 4 in `identification_table.py`, VALIDATION.md section, ADR-0036 proposed. Closed-channel C\* 13,333,333 ($3.13B, 1.23×) on the −1,000 tread (−1,007.0); no run within ±10% of −1,373. Status: review.
