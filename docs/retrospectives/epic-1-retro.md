# Epic 1 Retrospective — Kernel and First Scenario

**Date:** 2026-10-02 (Epic ran Oct 2, 07:30 – 20:25 ET, one calendar day)
**Planned:** Oct 2–6 · **Actual:** Oct 2 · **Stories:** 8/8 done
**Tests:** 3 → 328 · **CI:** green on every story commit · **ADRs:** 14

## What was delivered

A deterministic agent-based simulator that, from one command, runs a Soros-style attack
on a stablecoin peg and writes a reproducible timeseries, summary, event log, decision
trace, manifest and chart. Kernel, config, AMM, oracle, environment, redemption, three
agents, metrics, writer, one chart type, two scenarios.

First result: `soros-baseline` — 300k attack on a 1M/1M pool, trough −573 bps at minute
10, defender spends half of 400k, arbitrageur redeems 91k of 500k reserves, peg recovers
into a ±60 bps band by minute 38.

First finding (ADR-0010): a defended peg can park permanently a few bps off peg in a dead
zone where no actor has an incentive to act. Candidate headline for the note.

## What worked

- **Story file as contract.** The builder followed the story over a mismatched kickoff
  prompt in 1.2 and never needed telling again. Four real spec defects (1.3 queue-clear,
  1.3 view-protocol location, 1.4 mixed-unit fees, 1.5 threshold-0 semantics) were caught
  by the builder reading intent and flagging the contradiction instead of building it.
- **Independent review that re-runs everything.** Every AC was reproduced on a second
  machine with a different Python version. Determinism held across 3.12/3.13/3.14 every
  time, which is now evidence rather than a claim.
- **Builder flags → rulings → ADRs.** Every judgment call got a written ruling in the
  story and, from 1.7, an ADR. Nothing is decided only in chat.
- **Carry-over task as task 1, committed separately.** Small fixes from the previous
  review landed first, green, before new work started. Zero regressions across the epic.
- **One story per fresh session.** Context stayed clean; the largest stories (1.3, 1.7)
  finished in one session each.
- **Findings get regression tests.** The ADR-0010 dead zone is pinned by a test that keeps
  the old tolerance.

## What to change for Epic 2

1. **Check Dev Notes against ACs before publishing a story.** Both 1.3 contradictions and
   the 1.5 one were Dev-Notes-vs-AC disagreements written by the dev manager. A
   five-minute pass would have caught them.
2. **Allow-lists name intent.** Said in 1.5's review; now standing rule in CLAUDE.md.
3. **Predictions in tests are not required.** 1.7 asked for a reasoning comment before
   running; the builder ran first and said so. Findings belong in Completion Notes and
   ADRs, and the test asserts the truth.
4. **Builders propose ADRs.** Added to CLAUDE.md after 1.7; 1.8 produced two good ones.
5. **Recovery metric was underspecified** (ADR-0013 amendment). Epic 2 fixes the
   definition before any sweep uses it.

## Carry-overs into Epic 2

| Item | Origin | Lands in |
|---|---|---|
| `steps_to_first_band_entry` / `steps_to_sustained_recovery` | ADR-0013 | 2.1 |
| Manifest config round-trip test | ADR-0014 | 2.1 |
| Tolerance must track fee + arb band in sweeps | ADR-0013 | 2.1 sweep design |
| ADR-0010 options 2–3 as sweep axes | 1.8 review | 2.1, 2.5 |
| `Oracle.price` type hint `float | None` | 1.5 review | first touch of oracle.py |

## Numbers

| Story | Tests after | New | Builder flags | Spec defects found |
|---|---|---|---|---|
| 1.1 | 3 | 0 | 0 | 0 |
| 1.2 | 32 | 29 | 2 | 0 |
| 1.3 | 92 | 60 | 4 | 2 |
| 1.4 | 139 | 47 | 4 | 1 |
| 1.5 | 193 | 54 | 5 | 1 |
| 1.6 | 232 | 39 | 5 | 0 |
| 1.7 | 296 | 64 | 6 | 0 |
| 1.8 | 328 | 32 | 5 | 0 |

Builder model throughout: Claude Opus 5.5 via Claude Code on Seoul. Reviewer: Claude
Fable 5.1 (chat). Owner: Tim Dove.
