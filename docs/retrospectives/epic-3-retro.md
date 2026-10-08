# Epic 3 Retrospective — What the Model Asked For

**Date:** 2026-10-08 (Epic ran Oct 5, 19:04 – Oct 8, 09:24 ET; planned Oct 6–20)
**Stories:** 8/8 done (5 core + 3 stretch) · **Tests:** 552 → 886 · **Coverage:** agents 98.8%,
protocol 99.4% · **CI:** green on every pushed story commit · **ADRs:** 23 → 31 ·
**Findings:** F-12 … F-15, F-04 resolved, F-07 / F-09 / F-11 / F-13 refined, F-03 qualified
**Figures:** 10 → 19 committed, all under the source-hash guard with a code-hash warning
**Reviews:** every AC reproduced on a second machine; six full sweep re-runs (240, 200, 256, 120, 288, 112 runs) and three slices

## What was delivered

Everything the findings asked for at the Epic 2 retro, in the order they asked for it, plus
all three stretch items: the holder's fill-price cap (figure 1 is clean), the defender
policy comparison (charter chart 5), the holder exit rule and the 1992 switch-sides test,
budget vs attack and pace vs trigger, a repo a stranger can reproduce, a reference price
that reverts to par at a fitted rate, believers at a ladder of prices (replay within 4%
and nine minutes), and liquidity providers who flee.

Every stretch story changed a headline. 3.6 made the clock result the model's own and
retired the oracle-criterion workaround. 3.7 took validation from 17% to 4% with one stated
assumption. 3.8 inverted the charter's "core Soros dynamic": liquidity that flees and sits
still absorbs the attack.

## What worked

- **Predictions in every story, checked in every review.** Of 37 written predictions, 19
  missed. Every miss produced the story's result: F-13 (the slow defender wins), the
  withdrawn budget-vs-depth clause, the 1992 flip moving, the LP helping the defender.
  Writing them down is what made the misses visible.
- **Mapping by what an action touches, not its name.** 3.3's "switch sides" was mapped to
  the wrong exit; the builder's caveat became F-14 and corrected BACKGROUND. The rule is
  now in PROCESS and in the note's methods.
- **One parameter fitted, the rest assumed and labelled.** Three ladders (3.7), three
  LP settings (3.8), one κ (3.6): the fits are reproducible and the assumptions are named.
- **The guard.** Nineteen figures regenerated eight times; every regeneration reported
  which figures changed and which came out byte-identical. The code-hash warning caught
  what the source hash cannot.
- **Builders flag, reviewers rule, nobody guesses.** Three blocks (3.1 sizing helper, and
  two interface-name collisions), four judgment-call lists in ADRs, all ruled in review.
  Zero stories returned.
- **Pace.** Eight stories in 62 hours, reviewed, against a 15-day plan.

## What to change for Epic 4

- **No new mechanics.** The retro carry-overs below are the next project's backlog, not
  this one's. The freeze is proposed for **Oct 9** (charter decision for Tim).
- **The note is the product now.** Epic 4 is writing and figure polish; the builder's
  stories are small and specific (figure pass, site page build).
- **One condition per finding, stated first.** F-15's "and sits on what it withdrew" and
  F-14's two exits are the pattern: the note leads every mechanism sentence with the
  condition it depends on.
- **Read the exit code, not the pipe's** (L-17).
- **Outside reader by Oct 15** — still open; Tim/Muse.

## Carry-overs (post-Nov 1 backlog)

- An LP that dumps or redeems what it withdraws (F-15's condition inverted).
- Several LPs with different thresholds (cascade test; one LP cannot cascade).
- Budget vs attack at 4× D\* and at the slow attack (3.4 tested 2× D\*, fast attack).
- Stress-volatility surfaces under OU (3.6 tested calm only).
- A second validation event (UST May 2022 or USDe Sept 2026 — LITERATURE L-7).
- Multi-venue structure (F-05): the USDe case needs a venue price feeding the oracle.
- A second-generation defender with a cost function (BACKGROUND item 2).
- Fit-script outputs under the guard (3.5 review ruling 6) — do in the Epic 4 figure pass.
- Renmin primary (L-5), USDe and MIM primaries (L-7, L-8) for the note's taxonomy paragraph.

## Numbers

| | start of Epic 3 | end |
|---|---|---|
| tests | 552 | 886 |
| coverage (agents / protocol) | — | 98.8% / 99.4% |
| ADRs | 23 | 31 |
| findings | F-01…F-11 | F-01…F-15 (+ 9 refinements, 1 resolution, 1 correction) |
| scenarios | 8 | 14 (incl. 4 policy files) |
| sweep specs | 8 | 15 |
| committed figures | 10 | 19 |
| validation (USDC trough) | 17% short, 3.2 h late | 4% short, 9 min late (ladder); single entry unchanged |
| predictions written / missed | — | 37 / 19 |

Wall time, Seoul (12 workers): `make figures` 893 s. Review box (2 cores): largest single
sweep re-run 14 min.
