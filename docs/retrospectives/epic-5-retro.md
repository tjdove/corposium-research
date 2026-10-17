# Epic 5 Retrospective — What the Referee Asked For

**Drafted by the builder (Story 5.7 AC 6); amended by the dev manager 2026-10-17 (section "Dev manager's amendments" at the end).**

**Date:** 2026-10-17 (Epic ran 2026-10-15 – 2026-10-17; planned Oct 15–25)
**Stories:** 7/7 (5.1–5.6 done, 5.7 in review) · **Tests:** 907 at the first freeze → 1,033
at the second · **ADRs:** 32 → 38 accepted, ADR-0039 proposed · **Findings:** F-16, F-17 new;
F-09, F-13 refined; F-15 revised; F-17 refined
**Figures:** 19 → 25 committed, fit records 4 → 6, all re-frozen at `v0.95-freeze`
**Reviews:** one round per story, every verdict APPROVE, no story returned or blocked

## The stories

Built in the order 5.1, 5.2, 5.5, 5.6, 5.3, 5.4, 5.7. 5.5 was drafted from the 5.1
review (ruling 5) and 5.6 from the 5.5 review (ruling 4).

| Story | Drafted | Implemented | Reviewed | What it answered |
|---|---|---|---|---|
| 5.1 Par-reference replay | 10-15 | 10-15 | 10-15 | the observed price no longer fed in as the reference (F-16) |
| 5.2 Joint identification of D\* and C\* | 10-15 | 10-15 | 10-15 | depth × capital surface, ladders A/B/C, a continuous ladder (F-09 refined) |
| 5.5 Closed weekend channel | 10-15 | 10-16 | 10-16 | redemption closed until Monday 13:00 UTC (F-17) |
| 5.6 Closed-channel capital scan | 10-16 | 10-16 | 10-16 | C\* with the channel closed (F-17 refined) |
| 5.3 Policy under a gradual attack, with a cost of discount | 10-15 | 10-16 | 10-16 | attacker pace as an axis; `discount_bps_hours` (F-13 refined) |
| 5.4 LP that disposes of what it withdrew | 10-15 | 10-17 | 10-17 | sell / redeem the withdrawn stable (F-15 revised) |
| 5.7 Re-freeze | 10-17 | 10-17 | — | figures, manifest and fits regenerated at `v0.95-freeze` |

## Predictions

The story asks for "the seven predictions and how many held". I find six prediction
blocks, one in each of 5.1–5.6; 5.7 has none, and `docs/epics.md` lists none. Some blocks
make several claims, and only the 5.3 and 5.4 reviews count them. Per block, as the
reviews (or, for 5.6, the builder and ADR) put it:

| Story | Prediction | Verdict (review) |
|---|---|---|
| 5.1 | the trough moves little; recovery stops tracking the observed series | half right: right for the ladder, wrong for the single entry (−1,138 → −607 bps); recovery faster, not tracking |
| 5.2 | a thin diagonal ±5% band, deeper pools need more capital; the cliff below the band | slope backwards; cliff held — "half wrong" |
| 5.3 | five claims (triggers separate; early buyer above $0.90; it may lose on discount; slow defender's lead shrinks; discount may reverse) | "five predictions, two right" |
| 5.4 | four claims (sell deepens one step behind; sell back to 0/8; redeem leaves trough; redeem's recovery effect open) | "four predictions, two right, one half" |
| 5.5 | trough unchanged; price sits at the last entry until 85 h; slow lands between | "half wrong (trough moved)" |
| 5.6 | closed-channel C\* 1.1–1.3× the open one | held for the number (1.23×; ADR-0036); the review gives no verdict |

**Count:** one block of six held whole (5.6), and none of the other five did. By claim,
17 were written: 5.3's two right and 5.4's two and a half come from the reviews; the rest
are the builder's reading of the verdicts above, about 8½ of 17. As in Epic 3, every miss
was a result: the single-entry trough on the par reference, the slope of the
identification band, the triggers that never separate, the LP that sells 190 steps late.

## What the referee asked for and who answered

Referee review `docs/reviews/2026-10-15-outside-review-1-finance-professor.md`, §5. Items
the review's Part 4 marked as wording only are left to the note's v2 rewrite and are not
listed one by one: §5.1–5.5, 5.7, 5.8, 5.12, 5.13, 5.17–5.20, 5.24, 5.27–5.32.

| §5 | Asked | Answered by | How fully |
|---|---|---|---|
| 6 | the observed price fed in as the reference | 5.1 (ADR-0033) | fully: par reference, F-16 |
| 14 | the arbitrageur values against that reference | 5.1 | fully |
| 9 | D\*, C\*, pace identified jointly | 5.2 (ADR-0034) | D\* × C\* only; pace not swept |
| 10 | the ladder choice is calibration | 5.2 (ladders A/B/C) | fully |
| 11 | discrete reservation prices | 5.2 (continuous ladder) | fully |
| 15 | weekend capacity from the weekday average | 5.5 (ADR-0035), 5.6 (ADR-0036) | fully; upgraded from wording by the 5.1 review |
| 16 | the Monday capacity jump | 5.5 | cited; the reopening rate was not changed |
| 21 | every defender spends everything | 5.3 (ADR-0037) | cited; the sweep still compares full-budget rules |
| 22 | the first sale crosses every trigger | 5.3 | not resolved: no cell separates the triggers, and the trigger claim is withdrawn (F-13) |
| 23 | no cost of the interim discount | 5.3 (`discount_bps_hours`) | fully |
| 25 | the LP holds what it withdraws | 5.4 (ADR-0038) | fully: F-15 revised |
| 26 | phase order is an economic assumption | 5.4 | cited, not tested (no scheduler change) |

## What worked

- **Each referee item became one story with one question.** Six builder stories in three
  days (15–17 October), each answering one or two §5 items, each with its own sweep, figure and
  calibration write-up.
- **Reviews ruled; follow-ons came from the rulings.** 5.5 and 5.6 were not in the plan.
  Both came from review rulings, and both changed a finding (F-17 and its refinement).
- **Hash discipline held across a growing agent set.** Every story that added a config
  field (5.3, 5.4, 5.5) left every existing scenario and sweep hash unchanged, by dropping
  the default from `content_hash`. The pinned summary was re-pinned with a layered check,
  not overwritten.
- **The guard caught the freeze state.** Epic 5's figures were drawn under a code-hash
  warning, and the re-freeze clears it in one regeneration. All 25 figures and 6 fit
  records were byte-identical to the ones the stories committed (Story 5.7 Debug Log).

## What I want the dev manager to hear

- **Numbers in write-ups, checked by code.** In 5.4, three numbers in my first draft of
  `LP_DISPOSAL.md` were wrong, and one provenance was wrong. I caught them only by
  recomputing every quoted number with a script before review. Every story should do
  that as a task, not as the builder's own habit.
- **Prediction blocks with several claims need a scorecard.** The 5.3 and 5.4 reviews
  counted their claims; the others gave a one-word verdict, and 5.6's review gave none.
  That is why this retro cannot state "seven predictions, N held" cleanly. A fixed
  scorecard line in the review template would fix it.
- **Story ACs that touch a guard should be checked against the guard when drafted.**
  5.7's "change only the header line" conflicted with `check_note.py`'s one-tag rule. I
  asked and Tim chose (ADR-0039), so there was no block, but it was foreseeable.
- **Docs that count things go stale silently.** The README, `REPRODUCIBILITY.md` and the
  note's §9 all still said "nineteen figures, four fits, fifteen minutes" until this
  story. A test could pin the counts to the manifest.
- **The full `make test` is now about 4 minutes** (1,029 tests; it was 38 s at the first
  freeze), mostly from story tests that run real sweeps. Worth a `slow` marker before
  Epic 6.

## Carry-overs

- **Trigger-separation sweep.** A cell where the attacker's first sale does not cross every
  trigger (5.3; §5.22 unresolved). 5.3 says this is logged in the Epic 3 retro
  carry-overs, but it is not there; it is logged here.
- **Belief as a process.** A holder whose entry prices or capital move with the price path,
  rather than a fixed ladder (F-17: what moves inside the bracket is belief).
- **Multi-venue structure** (F-05; still open from Epic 3).
- **Pace in joint identification** (§5.9; ADR-0034 did not sweep it).
- **LP disposal variants** (ADR-0038): disposal interleaved with withdrawal, other paces,
  a price-limited sale, sell-and-redeem mixed, several LPs.
- **Phase order as an assumption** (§5.26): cited by 5.4, not tested.
- **Housekeeping found while drafting:**
  - Two broken ADR links in `docs/FINDINGS.md` (the F-13 and F-15 entries name
    `0037-policy-gradual-attack.md` and `0038-lp-disposal.md`).
  - The "headline candidates" and the open questions in FINDINGS.md still say "the trigger
    does nothing".
  - PROCESS.md's Change Log omits L-21, and §8 still says "Freeze Oct 21".
  - `epics.md` says "Epic 5 Complete: four stories done".
  - The 5.2 ruling-2 docstring note in `summary.py` (`steps_to_first_band_entry` null on
    replays) appears undone.

## Numbers

| | end of Epic 4 (`v0.9-freeze`) | end of Epic 5 (`v0.95-freeze`) |
|---|---|---|
| tests | 907 | 1,033 |
| ADRs | 32 | 38 (+ 0039 proposed) |
| findings | F-01…F-15 | F-01…F-17 (+ 3 refinements, 1 revision) |
| scenarios | 10 + 4 policy files | 16 + 4 policy files |
| sweep specs | 15 | 18 |
| committed figures / fit records | 19 / 4 | 25 / 6 |
| `make figures`, Seoul 12 workers | 934 s | 1,299 s |

## Dev manager's amendments (2026-10-17)

- **Predictions count.** The story's "seven" was the dev manager's miscount; six blocks is
  right. The builder's 8½ of 17 is accepted as the Epic 5 score. Epic 3 was 18 of 37. Two
  epics in a row the misses were the results, which is the argument for keeping the
  predictions.
- **The epic ran in three days against a planned eleven.** Same pattern as Epics 2 and 3.
  The plan was not too loose; the stories were small and the builder is fast. The
  calendar's slack now goes to note v2, the second review round and the human readers.
- **All three "what I want the dev manager to hear" items are accepted** and are
  PROCESS.md L-22, L-23 and L-24. The `slow` test marker is a carry-over for Epic 6.
- **Housekeeping fixed in the closing PR:** the two ADR links in FINDINGS.md; the headline
  candidates block rewritten for v2 (the "trigger does nothing" line is gone); PROCESS §8
  and change log; `epics.md` Epic 5 Complete line. The `summary.py` docstring note from
  the 5.2 ruling is left for the builder in Epic 6 (code is frozen).
- **What the referee asked for, answered:** of the §5 items the dev manager marked
  "experiment" on 2026-10-15, all are answered or explicitly left open with the reason;
  §5.22 (triggers) is the one left open, and the note says so.
- **Epic 5 is closed.** Note v2 is written against `v0.95-freeze`.
