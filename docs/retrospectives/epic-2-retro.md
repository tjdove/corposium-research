# Epic 2 Retrospective — Runner, Calibration, Validation, Headline

**Date:** 2026-10-05 (Epic ran Oct 3, 18:45 – Oct 5, 09:40 ET; planned Oct 7–13, revised to Oct 15)
**Stories:** 9/9 done (7 planned + 2 inserted by findings) · **Tests:** 328 → 552 · **CI:** green on every
story commit · **ADRs:** 14 → 23 · **Findings:** F-02 → F-11 plus eight refinements and one correction
**Reviews:** every AC reproduced on a second machine; three full sweep re-runs (640, 640, 200 runs)

## What was delivered

A sweep runner with linked axes and Monte Carlo aggregation (Wilson intervals); calibration
to Curve/Chainlink/Circle parameters with every number sourced; a fitted aggregate depth D\*
and a 1992 analogue that exhausts reserves at 5.7× Quantum; a USDC March-2023 replay that
*failed* validation, which located the missing agent (a par-expecting buyer), which once
fitted takes the replay from 4.2× too deep to within 17% and onto the observed path from
35 h to 49 h; two headline sweeps at calibrated scale; a recovery criterion that measures
against the market instead of par; ten committed figures with a stale-figure guard.

Headline (FINDINGS, ranked): *a depeg's depth is set by the attacker against everyone who
believes the promise*; *deep liquidity protects the price and makes the defense
unaffordable*; *at issuer scale the binding constraint is the clock, not reserves*; *oracle
lag is not a risk factor at Chainlink's settings*.

## What worked

- **Letting the model set the plan.** Two stories (2.6, 2.8) were inserted because a
  result said what to build next, and both produced the epic's best findings. Both went
  through the charter's decision log before drafting.
- **A failed validation treated as a result** (L-9). The replay missing by 4× was the most
  informative run of the project.
- **Builder blocks before building.** Four of the last four stories stopped at a spec
  contradiction before writing code (2.6 redeem rule, 2.7 base vs F-04, 2.8 interface
  name, 2.9 metric origin). Each cost under an hour and none reached `main` as code.
- **Predictions written into rulings and checked.** Two were falsified (2.6 "rule won't
  move the trough"; 2.8 "budget scales with depth") and reported as such (L-15).
- **Full re-runs in review.** Three sweeps re-run end to end on the review box, cheap
  per-depth medians from `sweep.parquet` found the F-11 mechanism the builder's report
  hadn't drawn out.
- **Muse as a research relay.** The literature briefing came through Open Brain, Muse
  chased primaries when asked, and said plainly which one didn't exist.

## What to change for Epic 3

- **Open the module before writing the AC** (L-2, extended twice this epic). All four
  blocks were dev-manager errors of the same kind: an AC written from memory of what a
  function, scenario or name does. The fix is a habit, not a tool: grep the name, read the
  function, check the base scenario against FINDINGS, before `ready-for-dev`.
- **One expected-shape section per story, labelled as predictions.** It worked; keep it.
- **Every story that changes a calibrated parameter ends with `make figures` green.**
- **Stop inserting stories.** Epic 3 is now planned from the findings; anything new goes
  to the Epic 3 retro, not into the epic. The freeze is Oct 21.
- **Makefile `PYTHON` default** — 3.5 (review ruling 2.9/6).

## Carry-overs into Epic 3

- Holder sawtooth artefact in figure 1 (ADR-0021) → 3.1.
- "Convergence traders had to switch sides" untested; holder has no sell rule → 3.3.
- F-11's "budget against attack once the pool doesn't crash" → 3.4.
- Reference random walk has no anchor (F-04 root cause) → 3.6 stretch.
- Single-entry buyer gives a cliff (F-09) → 3.7 stretch.
- `peg_recovered.reference: oracle` is used only in sweeps; the replay keeps `par` by
  design (VALIDATION.md).
- L-5 (Renmin) primary still unpinned; L-7/L-8 (USDe, MIM) to be sourced for the note's
  taxonomy paragraph (LITERATURE.md).

## Numbers

| | start of Epic 2 | end |
|---|---|---|
| tests | 328 | 552 |
| ADRs | 14 | 23 |
| findings | F-01 | F-01…F-11 |
| scenarios | 2 | 8 |
| sweep specs | 0 | 8 |
| committed figures | 1 (chart) | 10 + manifest + guard |
| validation | none | USDC Mar-2023, trough within 17%, path matches 35–49 h |
| story spec defects caught by builder | 4 (Epic 1) | 9 |

Wall time, review box (2 cores): full surface 17 min; `figures-quick` 8 min. Seoul (10–12
workers): full surface 2.5 min; `make figures` 7.4 min.
