# Story 5.1: Par-Reference Replay

Status: done

## Story

As a **reader who doubts the replay**,
I want the USDC March 2023 replay run with nothing from the observed price series fed to the model,
so that whatever agreement remains between the simulated and observed paths cannot be the input showing through.

## Why (read this first)

Outside review 1 (`docs/reviews/2026-10-15-outside-review-1-finance-professor.md`, §1 and
§5.6/§5.14) made one objection that matters more than the rest: in `usdc-2023.yaml` the
reference price **is** the observed USDC/USD series, the oracle follows it, and the
arbitrageur trades against that oracle, so the simulated venue is anchored to the thing we
are comparing it with. VALIDATION.md already says the later path is "the input series
showing through." This story removes the input and reports what is left. **The result
decides how note v2 describes the replay.** Do not tune anything to make the result look
better. A trough that moves away from the observation is a result.

## Acceptance Criteria

1. Two new scenarios, hashes recorded:
   - `scenarios/usdc-2023-par.yaml`: `usdc-2023.yaml` with `price_series_path` removed,
     `base_price 1.0`, `volatility_per_step 0.0`, `mean_reversion_per_step` absent (constant
     par reference). Everything else byte-identical in meaning (same attacker, holder,
     capacity schedule, max_steps, seed).
   - `scenarios/usdc-2023-tranches-par.yaml`: the same change applied to
     `usdc-2023-tranches.yaml` (ladder B, C\* 10,833,333).
   Header comments say what changed and cite this story.
2. A third pair with the calm OU reference instead of constant par (`volatility_per_step
   3.086e-05`, `mean_reversion_per_step 0.001634`, from `calibrated-baseline-ou.yaml`), as
   `usdc-2023-ou.yaml` and `usdc-2023-tranches-ou.yaml`. Seed 42. These are a sensitivity
   check; the par pair is the primary result.
3. `scripts/replay_table.py` runs the six replay scenarios (observed-reference ×2, par ×2,
   OU ×2) and prints one table: trough bps, trough step and hour, first band re-entry hour,
   hours in band, holder bought / redeemed / PnL, arbitrageur redeemed. Observed row at the
   top (−1,373 bps, 31.0 h, from the CSV). Deterministic; runnable on Seoul in < 5 min.
4. `plot_validation_overlay` gains an optional second simulated series: new figures
   `validation_overlay_usdc_2023_par.png` and `validation_overlay_usdc_2023_tranches_par.png`
   show observed (blue), observed-reference replay (grey, dashed) and par-reference replay
   (black). Captions in `docs/figures/README.md` lead with what was fed in. Added to
   `make figures`, the manifest and the note's figure list (figure-set test updated).
5. `docs/calibration/VALIDATION.md` gains a section "Par-reference replay (Story 5.1)" with
   the AC 3 table and a plain statement of what moved and what did not, **in the builder's
   words, without interpretation of what it means for the note** (the dev manager does
   that in review).
6. If the par-reference trough is within ±10% of the observed trough for ladder B, say so.
   If it is not, say so. Either way, record the number. Do not re-fit C\* or pace in this
   story.
7. Tests: scenario hashes pinned; `replay_table.py` smoke test on a shortened `max_steps`;
   overlay with two simulated series renders. `pytest`, `ruff check .`, `make figures-check`
   (code hash will change: this epic lifts the freeze; record the new hash in the Dev Agent
   Record).

## Tasks / Subtasks

- [x] Scenarios: par pair, OU pair (AC: 1, 2)
- [x] `replay_table.py` (AC: 3)
- [x] Overlay with second series; figures; manifest; figure list (AC: 4)
- [x] VALIDATION.md section (AC: 5, 6)
- [x] Tests, lint, figures-check (AC: 7)
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 5.1: par-reference replay`, push branch `story/5-1-par-reference-replay`

## Dev Notes

### Learnings from Previous Story

**From Story 4.1/4.2 and the outside review**

- The freeze is lifted for Epic 5 only. Change what the ACs name; nothing else under `src/`.
- Every result in this epic goes into the note as a number first and a sentence second.
  Write the number down before deciding what it means (PROCESS L-19).
- `price_process.py`: with `price_series_path` absent, `volatility_per_step 0` and no
  `mean_reversion_per_step`, the reference is constant `base_price`. Confirm by reading the
  module, not by assuming (L-2).
- The holder's entry test is against `peg_price × (1 − entry_discount_pct/100)`, not the
  oracle (ADR-0021, ADR-0024), so the holder is unaffected by this change; the arbitrageur
  (oracle-relative) and the oracle module are what change. Say so in VALIDATION.md.

### What to expect (dev manager's prediction, to be checked, not aimed at)

The trough is set in the first four hours by the attacker against the holder, with the
arbitrageur capacity-bound at 605.79/step; it should move little. The recovery path after
~35 h will no longer track the observed series. Whether it recovers faster (par oracle,
arbitrageur always buying below 0.998) or slower is the open question. Record whichever.

### References

- [Source: docs/reviews/2026-10-15-outside-review-1-finance-professor.md §1, §5.6, §5.14, §7]
- [Source: docs/calibration/VALIDATION.md] — current replay record
- [Source: scenarios/usdc-2023.yaml, usdc-2023-tranches.yaml, calibrated-baseline-ou.yaml]
- [Source: src/depeg_sim/environment/price_process.py]
- [Source: src/depeg_sim/analysis/charts.py#plot_validation_overlay]

## Dev Agent Record

### Context Reference

- [Story Context XML](./5-1-par-reference-replay.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

**Setup.** The story was on `origin/main` (merge `d0737cf`, PR #41), not on the local
checkout (`story/4-2-check-note`); branched `story/5-1-par-reference-replay` from the
fast-forwarded `main`.

**Constant reference confirmed by reading `environment/price_process.py`** (L-2): with
`price_series_path` absent, `from_config` builds `ReferencePrice(base_price, sigma, shocks,
kappa)`; in `on_phase`, `kappa == 0` takes the random-walk branch and `sigma == 0` skips
the draw, so `p = prev = base_price` every step and `ctx.rng` is never touched.
`mean_reversion_per_step` defaults to 0.0 (`kernel/config.py:90`). Test
`test_par_reference_is_constant_one`: `reference_price` and `oracle_price` are 1.0 at
every step of a 9,000-step par run. Holder entry test is `peg_price × (1 − d/100)`
(`agents/holder.py:13, 163, 167`), arbitrageur's is `spot < oracle × (1 − band)`
(`agents/arbitrageur.py:117`).

**AC 3: `python scripts/replay_table.py` (12.7 s wall; 14.3 s on the first run):**

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
band ±31 bps; in band h over 27-96 h; model units (1M = $234.6M)
```

Two consecutive runs diffed: identical. Exact troughs from `summary.json`: par single
−607.2054411354267, OU single −607.2287695144429, par ladder B −1279.1714339490268, OU
ladder B −1279.1922110030907.

**Arbitrageur during the attack** (`swap_executed` from `arb-1`, steps 8,100–9,299):
observed ref single 111 buys / 398,699 reference; observed ref ladder B 265 / 678,574;
par and OU, both holders, 400 / 923,919. Redemption paid to `arb-1` in that window under
par: 724,525 (nobody else paid). `sell_stable` by `arb-1`: 0 in all six runs.

**Path checks behind the VALIDATION.md prose** (from the par runs' timeseries): single
entry 27–30.5 h −225.8 … −201.1 bps (observed ref −409.0 … −203.9); after 37.2 h lowest
−21.1 at 37.37 h, |dev| ≤ 6.3 from 40.5 h. Ladder B after 40.4 h: 7 steps outside the
band (40.403–40.423 h, min −37.4), |dev| ≤ 3.4 from 41 h; at 27.5 / 28.0 / 28.6 h
−231.0 / −514.0 / −1,008.9 (observed ref −230.6 / −511.9 / −1,006.8); max per-step
difference before 30.6 h 77.0 bps. Three draft claims were wrong and corrected before
commit: "the ladder stays inside the band", "the ladder path is identical to 28.6 h",
"726,948 redeemed" (it is 724,525).

**`make figures`, first attempt: failed** (my bug): `FileNotFoundError:
/tmp/make-figures-2xt0vupb/runs/usdc-2023-42-2c3aeaa9/validation_overlay.png`. The par
overlay re-runs `usdc-2023` into the same work directory and `run_scenario` deletes an
existing run directory, so the first overlay's PNG was gone before the copy. Fixed in
`f02e90c` (one run directory per figure) with a regression test that fails without it
(`test_figures_sharing_a_scenario_keep_both_pngs`).

**`make figures`, second attempt (clean tree at `f02e90c`):**

```
sweep sweeps/threshold-surface-ref-mc.yaml: wall time 143 s
sweep sweeps/threshold-surface-mc.yaml: wall time 131 s
sweep sweeps/budget-x-depth-mc.yaml: wall time 49 s
sweep sweeps/oracle-lag-mc.yaml: wall time 111 s
sweep sweeps/policy-comparison-mc.yaml: wall time 75 s
sweep sweeps/holder-exit-1992-mc.yaml: wall time 18 s
sweep sweeps/budget-x-attack-mc.yaml: wall time 57 s
sweep sweeps/pace-x-trigger-mc.yaml: wall time 89 s
sweep sweeps/pace-ratio-mc.yaml: wall time 24 s
sweep sweeps/threshold-surface-ou-mc.yaml: wall time 126 s
sweep sweeps/lp-flight-mc.yaml: wall time 51 s
drew: validation_overlay_usdc_2023_par.png <- scenarios/usdc-2023.yaml + scenarios/usdc-2023-par.yaml
drew: validation_overlay_usdc_2023_tranches_par.png <- scenarios/usdc-2023-tranches.yaml + scenarios/usdc-2023-tranches-par.yaml
wrote: 21 figures and docs/figures/manifest.json (commit f02e90c32f1d, code_hash 555833b72e0d)
D* = 16666667 (trough -1253.2 bps)
C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
C* = 10833333 (trough -1323.3 bps) ≈ $2,541,499,922 at s = 0.0042625746 units/$
half_life_h = 1.413
fits: wall time 25 s
make figures: wall time 922 s (12 workers)
```

The 19 existing PNGs and the four fit records came out byte-identical (`git status` shows
only `manifest.json` modified and the two new PNGs added).

**New code hash: `555833b72e0dbe565106ff13c3f2e7042d127715867712c2a490edb764aaa207`**
(was `a0ae9594e7a4…`, the `v0.9-freeze` hash; the change is `analysis/charts.py`).

**Gates:**

```
$ make figures-check
figures-check: ok, 21 figures match their sources (code_hash matches)
figures-check: ok, 4 fits match their inputs (script hashes match)
$ ruff check . && ruff format --check .
All checks passed!
103 files already formatted
$ make test
TOTAL                                    956      9    99%
Required test coverage of 85% reached. Total coverage: 99.06%
921 passed in 60.21s (0:01:00)
```

(`pytest -q` alone exits 0; its summary line does not print in this setup, so the count
is from `make test`.)

### Completion Notes List

- **AC 6, the number.** Ladder B with a constant par reference: **−1,279.2 bps at
  32.8 h**, 94.1 bps (6.9%) shallower than the observed −1,373.3, **within ±10%**, 1.8 h
  after the observed trough. Single entry: **−607.2 bps at 33.0 h**, 55.8% shallower,
  **not within ±10%**. Nothing was re-fitted.
- **Recovery** with the par reference: back in the band at 37.2 h (single) and 40.4 h
  (ladder B), against 86.0 h observed and 85.3 h in the observed-reference replays.
  The dev manager's prediction said the recovery after ~35 h would no longer track the
  observed path. It does not; it recovers faster.
- **The trough moved more than predicted for the single entry** (−1,137.8 → −607.2). The
  prediction said "should move little". For ladder B it moved 44.1 bps. With the par
  oracle the arbitrageur buys from the first attack step, to the limit of its capital
  plus redemption (923,919 in 27–31 h vs 398,699 / 678,574). It never sells in any run.
  Recorded, not interpreted (AC 5).
- **OU = par** to 0.03 bps on the trough. Every other column matches, except the
  arbitrageur's redemptions (< 0.4% apart).
- **Judgment calls**, also in Proposed **ADR-0033**:
  1. AC 3's "first band re-entry" and "hours in band" were not defined. I used the first
     time after the trough within the ADR-0013 band, and in-band time over 27–96 h
     (attack start to the end of the observed series), hourly closes against 12 s steps.
  2. A figure can now have two sources: `Figure.second`, with `second_source` and
     `second_source_hash` in the manifest, both checked by the guard.
  3. In `plot_validation_overlay(run_dir, second_run_dir)` the first argument is the
     run that was fed the series (it carries the CSV and its sha256). The manifest's
     `source` for the par figures is therefore the observed-reference scenario and
     `second_source` is the par one.
- **Outside the named files**, needed for the ACs: four existing tests list every
  scenario file and gained the four new names in their "pinned elsewhere" sets.
  `check_figures.py` gained the second-source check. `make_figures.py` gained one run
  directory per figure (bug fix). `docs/figures/README.md` gained one sentence on
  two-source figures. Nothing else under `src/` changed besides `analysis/charts.py`.
- **For the dev manager:** `docs/NOTE.md` figure list rows 1c and 1d are added and marked
  "placement for v2 is the dev manager's"; the note text is not edited. The unmerged
  `scripts/check_note.py` (Story 4.2) would count these two as listed but uncited.

### File List

- `scenarios/usdc-2023-par.yaml` (new)
- `scenarios/usdc-2023-tranches-par.yaml` (new)
- `scenarios/usdc-2023-ou.yaml` (new)
- `scenarios/usdc-2023-tranches-ou.yaml` (new)
- `scripts/replay_table.py` (new)
- `src/depeg_sim/analysis/charts.py` (modified: `plot_validation_overlay` second series,
  `validation_comparison(observed_from=)`, `_observed_series`, `_reference_kind`)
- `scripts/make_figures.py` (modified: `Figure.second`, two new figures, per-figure run dir)
- `scripts/check_figures.py` (modified: checks `second_source`)
- `docs/figures/validation_overlay_usdc_2023_par.png` (new)
- `docs/figures/validation_overlay_usdc_2023_tranches_par.png` (new)
- `docs/figures/manifest.json` (regenerated; new code hash)
- `docs/figures/README.md` (two rows, two captions, one sentence)
- `docs/NOTE.md` (figure list rows 1c, 1d; change-log line)
- `docs/calibration/VALIDATION.md` (new section "Par-reference replay (Story 5.1)")
- `docs/adr/0033-par-reference-replay.md` (new, Proposed)
- `tests/test_par_replay.py` (new)
- `tests/test_figures.py` (second-source guard test, registry count 21, shared-scenario
  regression test)
- `tests/test_holder_config.py`, `tests/test_holder_tranches.py`,
  `tests/test_reference_recovery.py` (new scenarios added to the "pinned elsewhere" sets)
- `docs/stories/5-1-par-reference-replay.md` (this record)

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager) · **Date:** 2026-10-15 · **Verdict: APPROVE**

Reproduced on the review box at `7b4df32`: `pytest -q` → all pass (exit 0); `ruff check .`
clean; `make figures-check` → `ok, 21 figures … (code_hash matches)`, `ok, 4 fits`.
`python scripts/replay_table.py` run twice → byte-identical output (35 s on 2 cores),
every number matching the table in VALIDATION.md and ADR-0033: par ref ladder B
−1,279.2 bps at step 9,850 (32.8 h), back in band 40.4 h; single entry −607.2 at 33.0 h,
back 37.2 h; OU pair identical to par within 0.03 bps. Scenario diff checked:
`usdc-2023-tranches-par.yaml` differs from its base only in `name` and `environment`.
Overlay figure read: the black line follows the ladder staircase, troughs inside the grey
U, climbs straight to the band by 40 h while the blue line sits at −150 … −524 for two
more days. The builder's three self-corrections to VALIDATION.md and the `make_figures`
run-directory bug (caught, tested, fixed) are what the process is for.

**What the result means (the dev manager's call, per AC 5).** Recorded as finding F-16.

1. *The trough is the believers', not the input's.* Ladder B lands at −1,279 bps with
   nothing from the observed series fed in, 6.9% from the observed −1,373, using a C\*
   fitted on the observed-reference replay and not re-fitted. The referee's objection
   §5.6/§5.14 (the input anchors the venue) is answered for the trough: the descent is the
   ladder's staircase and the bottom is the attacker running out of stock against the
   last tranche. This is still calibration, not validation (L-19): C\* was fitted to this
   trough, in a different configuration. What it shows is that the fit transferred when
   the oracle anchor was removed. Note v2 says exactly that.
2. *The single-entry fit was on the cliff.* −1,138 → −607 when the arbitrageur gains
   525k of extra buying from a par oracle. F-09's bimodality was never a curiosity; the
   single-entry C\* sat on the steep side and a small change in who else absorbs tips it
   over. Note v2 drops the single-entry replay as a fit and keeps it as the illustration
   of the cliff. The ladder is the result.
3. *The model reproduces the depth of the fall, not the length of the weekend.* Without
   the input, both replays are at par from ~40 h; the real price sat 150–524 bps below par
   until 69 h. Everything that holds the model down is a fixed stock of selling that ends
   by 31 h; once it ends, a holder who buys every dip below 0.98 and an arbitrageur
   recycling 605.79/step through the channel take the price home in eight hours. The
   weekend plateau needs something the model does not have: selling that continues after
   the first wave, a redemption channel that is closed rather than slow (referee §5.15),
   or belief that is a distribution rather than a switch. **This is the honest
   reposition the referee asked for in §7, and it is a better sentence than the one it
   replaces.**
4. *The arbitrageur is the lever the oracle touches.* 924k bought in 27–31 h under par
   against 399k/679k under the observed oracle, in both replays; never sells. The
   oracle's only role in the replay was to throttle the arbitrageur. That sharpens F-10.

**Rulings**

1. **ADR-0033 accepted (finding + interface).** Index row added. F-16 added to FINDINGS.
2. **Figure placement.** 1d (ladder B, par) becomes the note's Figure 1 in v2; the
   observed-reference overlay (1b) becomes the "with the input" comparison beside it; 1a
   (single entry) moves to the record set with the cliff table; 1c (single entry, par) is
   kept as a committed figure, cited from the limitations. Rows 1c/1d stay in the list;
   until v2 cites them they are marked † (supporting), see ruling 4.
3. **Metric definitions** ("first back in band after the trough", "hours in band
   27–96 h") stand; `replay_table.py` is the reference implementation and Story 5.2 reuses
   it.
4. **Story 4.2 (`check_note.py`) unblocked by this review.** Ruling: figure-list rows
   marked † (supporting) are exempt from the listed-but-uncited check; every non-† row
   must be cited in the body. The dev manager marks 1c/1d † and links 5b
   (`peg_trajectory_1992_no_defense.png`) in the note body now; the builder narrows the
   check on `story/4-2-check-note` after rebasing on main, and re-runs it against the
   note at that commit.
5. **Follow-up story 5.5 added to Epic 5: closed weekend channel.** Referee §5.15 and
   point 3 above: rerun the par replay with weekend capacity 0 (and 10% of calibrated)
   until the 85 h reopening. If the plateau appears, the weekend is a redemption-channel
   story; if the price still goes to par, it is a selling or belief story. One scenario
   pair, `replay_table.py` gains the rows.

**Lessons:** the story's prediction ("the trough should move little") was half right
(ladder) and wrong (single entry), and the builder recorded the miss without
interpreting it, which is what AC 5 asked. L-15 holds: rulings' expectations are
predictions.

## Change Log

- 2026-10-15: Story drafted by dev manager from outside review 1 (Epic 5)
- 2026-10-15: Implemented by Claude Code (Opus 5.5): par and OU replay scenarios,
  `replay_table.py`, two-series overlay and figures, VALIDATION.md section, ADR-0033
  proposed. Ladder B par trough −1,279.2 bps (within ±10%); single entry −607.2 (not);
  recovery to the band at 37–40 h. Status: review.
- 2026-10-15: Reviewed by dev manager — APPROVE; ADR-0033 accepted; F-16; Status: done
