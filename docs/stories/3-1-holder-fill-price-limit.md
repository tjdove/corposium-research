# Story 3.1: Holder Fill-Price Limit

Status: done

## Story

As a **researcher**,
I want the holder to stop buying when its own fill would lift the venue price above its entry price,
so that figure 1's first hours show the market, not a model artefact (ADR-0021 sawtooth), and C\* is fitted on a buyer that behaves like one.

## Acceptance Criteria

1. `Holder.decide`: the buy amount is `min(pace × reference_balance, amount_in that moves the AMM spot exactly to entry_price)`, the second term from the arbitrageur's existing `_reference_to_reach` helper, **reused unchanged** (amended 2026-10-05: it ignores the 1 bp fee and undershoots the target by ≤ 0.1 bps, the approximation Story 1.7 accepted; "exactly" is withdrawn); if the smaller of the two terms is ≤ `DUST` the holder does not buy that step and falls through to the redeem / `hold_wait` / `hold_done` rules (amended 2026-10-05); rule names unchanged; `HolderConfig` unchanged; every scenario `content_hash()` unchanged (test)
2. `tests/test_holder.py`: a buy that would overshoot is capped so post-trade spot ≤ entry_price within 1e-9; a buy that would not overshoot is uncapped; a new two-step synthetic (attacker dump between holder buys) shows spot above par under the old rule and not under the new one (amended 2026-10-05: there was no existing sawtooth test)
3. `scripts/fit_holder.py` re-run under the two-pass rule (unchanged); new `C*` in three units; `scenarios/usdc-2023.yaml` updated; replay re-run; `validation_comparison` numbers; VALIDATION.md gains a 3.1 row in the before/after table (2.5 → 2.6 → 3.1: trough depth, trough time, first in band, sawtooth amplitude in the first 3.5 h as max − min of deviation over steps 8,100–9,150)
4. The four propagated scenarios updated to the new `C*/D*`; re-run; outcomes before/after in Completion Notes; 1992 flip re-scanned 5.5–6.0 by 0.1 (the full scan is not needed unless 5.7 moves)
5. `make figures` re-run; guard green; the overlay figure's first-3.5 h band described in words before and after
6. A `Proposed` ADR: the fill rule, new `C*`, what moved; if the sawtooth is reduced but not gone, say why (the attacker's own 10%-of-remaining dumps between holder buys) and whether it is now within the hourly series' resolution
7. `pytest` and `ruff check .` pass; CI green on both jobs

## Tasks / Subtasks

- [x] Fill rule (AC: 1, 2)
  - [x] Sizing helper; `Holder.decide`; tests; hash test
  - [x] Commit separately: `story 3.1: holder fill-price limit`
- [x] Re-fit and replay (AC: 3)
- [x] Propagate and figures (AC: 4, 5)
- [x] ADR, close out (AC: 6, 7)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 3.1: holder fill-price limit, re-fit C*`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.9 (Status: done) and the Epic 2 retro**

- Every story that changes a calibrated parameter ends with `make figures` and the guard
  green; `C*` changes here, so nine of ten figures regenerate (every scenario except
  soros-baseline carries the holder; amended 2026-10-05).
- Predictions below are predictions. Report misses as results.
- The arbitrageur already has closed-form sizing against a target price (Story 1.7); the
  holder's cap is the same computation with `entry_price` as the target. Open
  `agents/arbitrageur.py` before writing it; do not write a second version.

[Source: docs/stories/2-9-committed-figures.md#Senior-Developer-Review, docs/retrospectives/epic-2-retro.md, ADR-0021 Consequences]

### Why this changes C\*

ADR-0021: at the fitted size the holder's 5%-of-reference buys (~450k into a 16.7M pool)
overshoot par for the first 3.5 h, a sawtooth between +310 and −220 bps. Capping each
fill at the entry price removes the overshoot and makes each unit of holder capital
absorb slightly less per step early on, so the same capital reaches the trough with more
left, or the fit lands on a different `C*`. Expect `C*` to move by less than one grid
refinement (≤ 10%); if it moves more, say so.

### Predictions (to be checked)

- Sawtooth amplitude in steps 8,100–9,150: from ~530 bps to ≤ 60 bps (the attacker's own
  dumps between buys remain).
- `C*` within 8.3M–10M; trough within 100 bps of −1,138; trough time within 1 h of 34.2 h.
- 1992 flip stays at 5.7.

### References

- [Source: docs/epics.md#Story-3.1]
- [Source: docs/adr/0021-par-expecting-holder.md] — sawtooth, alternatives considered
- [Source: docs/stories/1-7-agents.md] — arbitrageur closed-form sizing
- [Source: docs/calibration/VALIDATION.md]

## Blockers

**AC 1 asks for a fee-aware closed form that reaches `entry_price` exactly, and also asks
to reuse the arbitrageur's sizing helper, which ignores the fee.** No code written.

- `src/depeg_sim/agents/arbitrageur.py:43` `_reference_to_reach(k, r, target)` returns
  `sqrt(k·target) − R`, with the docstring "(fee ignored)". The module docstring says: "With
  a fee the input is reduced before the curve, so spot slightly undershoots the target;
  this is accepted, not solved iteratively". Story 1.7's Dev Notes (`1-7-agents.md:114–120`)
  say the same: exact only at `fee_bps = 0`.
- AC 1 wants "the `amount_in` that moves the AMM spot **exactly** to `entry_price`, closed
  form on constant product **with the fee on input**", "computed the way `Arbitrageur`
  sizes its trades (reuse or share that helper)". The Dev Notes ("the same computation")
  and the prompt ("it already sizes a trade to a target price on constant product with
  fee on input … do not write a second version") make the same assumption. The helper
  cannot do both.
- **Size.** Real AMM `quote`, target 0.98 (scratch calculation, not committed):

  | pool / start spot / fee | helper `x` → spot after | fee-exact `x` → spot after |
  |---|---|---|
  | 1M-ish, 0.950, 1 bp | 14,883.4 → −0.0154 bps from 0.98 | 14,884.2 → −1e-12 bps |
  | D\*, 0.943, 1 bp | 317,928.5 → −0.0193 bps | 317,944.4 → 0 |
  | D\*, 0.826, 1 bp | 1,347,643.1 → −0.0817 bps | 1,347,710.5 → +2e-12 bps |
  | 1M-ish, 0.950, 30 bp | 14,883.4 → −0.4628 bps | 14,905.8 → 0 |

  Both satisfy AC 2's test (post-trade spot ≤ `entry_price` within 1e-9). The helper misses
  "exactly" by at most ~0.08 bps at the calibrated 1 bp fee. The fee-exact form is the root
  of `(1−f)x² + (2−f)R·x + R² − k·p = 0`:
  `x = [−(2−f)R + sqrt(f²R² + 4(1−f)k·p)] / (2(1−f))`.

**Options** (not chosen):

- **(a) Reuse `_reference_to_reach` unchanged** (recommended). The holder's cap is
  `_reference_to_reach(amm.k, amm.reserve_reference, entry_price)`, imported from
  `arbitrageur.py` or moved to `agents/base.py` with the arbitrageur importing it. The
  arbitrageur's behaviour does not change, and there is one helper. AC 1's "exactly"
  becomes "to `entry_price`, fee ignored; spot undershoots by ≤ f·x/√(k·p) (≤ 0.1 bps
  here)", the same accepted approximation as Story 1.7.
- **(b) A fee-exact helper for the holder only.** Exact as written, but it is the "second
  version" the prompt forbids, and the two agents then size the same thing two ways.
- **(c) Make the shared helper fee-exact for both agents.** One exact helper, but every
  arbitrageur trade changes, so every scenario's output moves (and every committed figure
  with it, including `soros-baseline`). That is outside this story's scope ("every scenario
  hash unchanged" still holds, but outputs do not).

**Smaller points; I will do as stated unless the ruling says otherwise:**

1. **"Old sawtooth test case" (AC 2).** `tests/test_holder.py` has no such test (19 tests,
   none about overshoot). I will write a new two-step synthetic: real AMM at the context's
   numbers, holder buy, attacker dump, holder buy. Under the old rule it shows spot above
   par after a holder buy, and under the new rule it does not.
2. **Which term is ≤ DUST, and which rule fires.** AC 1 checks only the cap term, and says
   "does not buy that step (`hold_wait`)". The context test idea ("spot 0.979 and tiny
   reference: cap ≤ DUST → `hold_wait`") makes the *pace* term tiny. At spot 0.979 on a 1M
   pool the cap term is about 500 units, not ≤ DUST. I will skip the buy when
   `min(pace × reference, cap) ≤ DUST` and fall through to the existing chain (redeem if
   the tranche rule applies, else `hold_wait` if it holds stable, else `hold_done`). Rule
   names are unchanged. That is "does not buy", and it does not invent a `hold_wait` for a
   holder with nothing to wait on.
3. **Figure count.** The Dev Notes say five figures regenerate. Every scenario except
   `soros-baseline` carries the holder, including `calibrated-stress` (`oracle-lag-mc`)
   and the calibrated and 1992 trajectories, so nine of ten source hashes change.
   `make figures` regenerates all ten either way; the guard will name nine.

## Rulings

**2026-10-05 (dev manager), on the Blockers above.**

1. **Option (a).** Reuse `_reference_to_reach` unchanged. The ≤ 0.1 bps undershoot on a
   200 bps target is immaterial and it is the approximation the project already accepted
   in 1.7; two sizing formulas for the same trade would be worse than either. "Exactly" in
   AC 1 was mine, written without opening the helper (L-2). AC 1 amended. State the
   undershoot in the ADR.
2. **New two-step sawtooth test** — accepted; AC 2 amended.
3. **Skip the buy when the smaller term is ≤ DUST and fall through** — accepted; AC 1
   amended.
4. **Nine of ten figures regenerate** — accepted; Dev Notes amended.

Resume at the Fill rule task.

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-1-holder-fill-price-limit.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

Fill rule, commit `6e83b46` (`story 3.1: holder fill-price limit`): `pytest` 559 passed,
every scenario `content_hash()` pinned unchanged (`test_every_scenario_hash_is_pinned_for_3_1`).

`python scripts/fit_holder.py --workers 12` (unchanged script and rule; 10 s):

```
fit_holder: scenario=scenarios/usdc-2023.yaml target_bps=-1373 entry_discount_pct=2 pace=0.05
grid (7): 1,000,000, 2,000,000, 5,000,000, 10,000,000, 20,000,000, 50,000,000, 100,000,000
grid pass (target -1373 bps):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        1000000       -5,454.6               9524     max_steps      33600
        2000000       -5,106.4               9560     max_steps      33600
        5000000       -3,763.5               9683     max_steps      33600
       10000000         -954.2              10929     max_steps      33600
       20000000         -225.9               8117     max_steps      33600
       50000000         -225.9               8117     max_steps      33600
      100000000         -225.9               8117     max_steps      33600

refine pass 1 between 5,000,000 and 20,000,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        7500000       -2,147.4               9797     max_steps      33600
       10000000         -954.2              10929     max_steps      33600
       12500000         -225.9               8117     max_steps      33600
       15000000         -225.9               8117     max_steps      33600
       17500000         -225.9               8117     max_steps      33600

refine pass 2 between 7,500,000 and 12,500,000 (pick 10,000,000):
 holder_capital  max_depeg_bps  step_of_max_depeg terminated_by  steps_run
        8333333       -1,608.6               9831     max_steps      33600
        9166667       -1,137.8              10269     max_steps      33600
       10000000         -954.2              10929     max_steps      33600
       10833333         -225.9               8117     max_steps      33600
       11666667         -225.9               8117     max_steps      33600

C* = 9166667 (trough -1137.8 bps) ≈ $2,150,500,078 at s = 0.0042625746 units/$
```

Replay, `python run.py scenarios/usdc-2023.yaml --output output/s31`:

```
depeg-sim: scenario=usdc-2023 seed=42 hash=2c3aeaa9825d
run: steps=33600 terminated_by=max_steps max_depeg_bps=-1137.8 reserves_exhausted=False
wrote: output/s31/usdc-2023-42-2c3aeaa9
```

`validation_comparison`, 2.6 run (`output/usdc-2023-42-2c3aeaa9`, pre-3.1 code) → 3.1 run:
trough −1137.81 @ 34.18 h → −1137.82 @ 34.23 h; at capacity change −52.15 → −52.15;
first in band after change 85.32 h → 85.32 h; last outside 85.32 h → 85.32 h.

Sawtooth amplitude, max − min of `peg_deviation` × 10⁴ over steps 8,100–9,150 (1,051
rows):

```
2.5 output/usdc-2023-42-73db527c  max  -27.6  min -5697.6  amplitude 5669.9  (no holder: the crash)
2.6 output/usdc-2023-42-2c3aeaa9  max  314.7  min  -348.3  amplitude  662.9
3.1 output/s31/usdc-2023-42-2c3aeaa9  max -27.6  min -412.1  amplitude  384.5
steps 8,400-9,000:  2.6 max 53.8 min -211.4 amp 265.2 | 3.1 max -204.4 min -214.7 amp 10.2
```

Propagated scenarios and 1992 spot multiples, pre-3.1 code (git worktree at `8522944`, via
`PYTHONPATH`) and 3.1 code, scratch `scan31.py` (not committed):

```
=== BEFORE (pre-3.1 code)
             scenario  multiple      terminated_by  steps_run  max_depeg_bps  step_of_max_depeg  final_depeg_bps  defender_spent  redemption_paid_total  holder_bought_stable  holder_pnl
  calibrated-baseline       NaN      peg_recovered       7024       -1,253.2                 50            -19.9     6,054,985.8            4,221,810.0           4,661,439.6   198,965.0
    calibrated-stress       NaN      peg_recovered       7225       -1,231.0                 50             -3.7     6,055,420.2            4,344,815.4           4,663,198.8   201,938.0
           soros-1992       NaN reserves_exhausted       9550       -5,982.4               3337           -127.8   100,703,325.0          100,703,325.0          11,597,301.5   -64,942.4
soros-1992-no-defense       NaN reserves_exhausted       7807       -7,692.4               1543           -153.7             1.0          100,703,325.0          10,217,586.7    67,601.4
=== AFTER (3.1 fill rule)
  calibrated-baseline       NaN      peg_recovered       7024       -1,253.2                 50            -19.9     7,699,786.6            3,173,906.3           2,887,233.9   154,690.5
    calibrated-stress       NaN      peg_recovered       7225       -1,231.0                 50             -3.7     7,702,126.6            3,168,262.6           2,867,035.6   136,379.5
           soros-1992       NaN reserves_exhausted       9553       -5,975.4               3344           -144.3   100,703,325.0          100,703,325.0           9,441,626.2   126,437.4
soros-1992-no-defense       NaN reserves_exhausted       7805       -7,689.8               1546           -134.5             1.0          100,703,325.0           9,630,291.2   259,787.7
```

1992 re-scan. AC 4 asked for 5.5–6.0; 5.5 and 5.6 moved from `max_steps` to exhausted,
so 5.7 is no longer the flip and the full 4.0–7.0 scan was run (scratch
`scan31_full.py`, `soros-1992` with the holder, both codes):

```
code: /tmp/claude-1000/-home-dove-code-corposium-research/f0598b05-3c33-4871-9273-96443d53fd08/scratchpad/old/src/depeg_sim/__init__.py
  scenario  multiple      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  redemption_paid_total  holder_bought_stable   holder_pnl
soros-1992       4.0          max_steps      14400         -222.3           -162.7           64,469,951.0          62,053,794.2 -1,018,185.6
soros-1992       4.1          max_steps      14400         -225.1           -151.3           68,954,011.1          55,002,557.8   -857,385.0
soros-1992       4.2          max_steps      14400         -222.5           -162.2           72,954,007.5          62,793,733.6   -758,003.5
soros-1992       4.3          max_steps      14400       -1,044.2           -144.3           76,102,125.1          50,001,105.8   -702,896.1
soros-1992       4.4          max_steps      14400       -1,746.8           -162.3           78,340,725.5          46,673,299.4   -692,054.8
soros-1992       4.5          max_steps      14400       -2,319.7           -144.4           80,565,444.1          40,804,832.3   -669,027.5
soros-1992       4.6          max_steps      14400       -2,786.6           -146.2           82,863,076.8          35,201,607.8   -617,325.9
soros-1992       4.7          max_steps      14400       -3,185.0           -178.0           84,558,673.0          29,641,952.1   -511,266.1
soros-1992       4.8          max_steps      14400       -3,540.4           -146.4           86,584,675.0          36,826,850.6   -648,866.4
soros-1992       4.9          max_steps      14400       -3,867.5           -145.6           88,104,433.5          33,668,048.7   -618,408.7
soros-1992       5.0          max_steps      14400       -4,152.3           -155.3           89,950,326.1          31,695,318.5   -581,034.5
soros-1992       5.1          max_steps      14400       -4,415.8           -142.8           91,209,855.0          27,430,896.2   -510,087.7
soros-1992       5.2          max_steps      14400       -4,639.9           -167.7           92,837,045.7          24,691,859.8   -449,943.2
soros-1992       5.3          max_steps      14400       -4,857.1           -160.3           94,433,289.3          21,523,861.0   -385,063.4
soros-1992       5.4          max_steps      14400       -5,052.2           -150.1           96,012,879.0          18,909,923.1   -310,943.0
soros-1992       5.5          max_steps      14400       -5,237.1           -158.8           97,583,092.1          16,127,530.4   -238,375.9
soros-1992       5.6          max_steps      14400       -5,405.9           -175.4           98,662,131.2          12,868,357.4   -158,658.7
soros-1992       5.7 reserves_exhausted       9661       -5,565.4           -142.0          100,703,325.0          12,143,870.6   -134,307.3
soros-1992       5.8 reserves_exhausted       9623       -5,714.1           -127.2          100,703,325.0          11,872,073.9    -92,999.5
soros-1992       5.9 reserves_exhausted       9589       -5,854.4           -138.2          100,703,325.0          11,739,534.0    -72,156.7
soros-1992       6.0 reserves_exhausted       9550       -5,982.4           -127.8          100,703,325.0          11,597,301.5    -64,942.4
soros-1992       6.1 reserves_exhausted       9518       -6,105.4           -133.8          100,703,325.0          11,468,283.5    -59,718.0
soros-1992       6.2 reserves_exhausted       9486       -6,220.4           -145.8          100,703,325.0          11,621,152.7    -58,013.0
soros-1992       6.3 reserves_exhausted       9454       -6,329.6           -140.6          100,703,325.0          11,483,243.9    -51,300.0
soros-1992       6.4 reserves_exhausted       9422       -6,431.7           -135.2          100,703,325.0          11,348,195.9    -41,483.2
soros-1992       6.5 reserves_exhausted       9396       -6,530.6           -129.3          100,703,325.0          11,217,107.8    -27,442.7
soros-1992       6.6 reserves_exhausted       9365       -6,621.9           -123.3          100,703,325.0          11,221,196.0    -17,758.9
soros-1992       6.7 reserves_exhausted       9339       -6,710.3           -130.0          100,703,325.0          11,079,759.3    -25,531.8
soros-1992       6.8 reserves_exhausted       9316       -6,794.8           -130.3          100,703,325.0          11,091,100.4    -14,610.0
soros-1992       6.9 reserves_exhausted       9291       -6,874.1           -130.6          100,703,325.0          10,819,869.9     -6,503.3
soros-1992       7.0 reserves_exhausted       9269       -6,950.5           -144.9          100,703,325.0          10,967,315.3    -12,320.2
```

```
code: /home/dove/code/corposium-research/src/depeg_sim/__init__.py
  scenario  multiple      terminated_by  steps_run  max_depeg_bps  final_depeg_bps  redemption_paid_total  holder_bought_stable  holder_pnl
soros-1992       4.0          max_steps      14400         -225.2           -198.8           65,059,664.2          19,604,984.1    30,547.6
soros-1992       4.1          max_steps      14400         -226.7           -180.1           69,176,443.8          22,186,345.2    36,249.5
soros-1992       4.2          max_steps      14400         -318.0           -159.7           73,316,572.0          23,730,709.3    46,885.3
soros-1992       4.3          max_steps      14400       -1,137.1           -153.4           76,854,350.1          14,825,828.0    32,490.0
soros-1992       4.4          max_steps      14400       -1,821.9           -158.0           81,180,908.1          13,333,830.7    32,429.7
soros-1992       4.5          max_steps      14400       -2,358.1           -156.6           81,885,236.4          12,172,595.0    31,345.7
soros-1992       4.6          max_steps      14400       -2,787.2           -148.0           84,002,245.5          11,376,998.7    30,769.6
soros-1992       4.7          max_steps      14400       -3,166.7           -149.1           87,470,013.6          10,855,679.3    31,794.6
soros-1992       4.8          max_steps      14400       -3,516.3           -159.5           87,307,110.8           9,905,933.7    28,532.8
soros-1992       4.9          max_steps      14400       -3,837.7           -152.2           96,267,973.8           9,458,954.5    29,204.9
soros-1992       5.0 reserves_exhausted      14287       -4,125.4           -149.8          100,703,325.0           9,413,166.0    32,789.0
soros-1992       5.1          max_steps      14400       -4,385.3           -142.8           96,011,875.2           9,411,610.0    36,415.1
soros-1992       5.2 reserves_exhausted      10506       -4,623.2           -127.4          100,703,325.0           9,413,282.3    40,293.6
soros-1992       5.3 reserves_exhausted      10897       -4,840.4           -120.0          100,703,325.0           9,414,880.6    44,069.2
soros-1992       5.4 reserves_exhausted      11474       -5,040.7           -157.8          100,703,325.0           9,416,405.6    47,911.5
soros-1992       5.5 reserves_exhausted      12353       -5,224.9           -162.3          100,703,325.0           9,413,686.8    51,637.4
soros-1992       5.6 reserves_exhausted      13965       -5,396.3           -144.3          100,703,325.0           9,420,168.3    56,280.0
soros-1992       5.7 reserves_exhausted       9663       -5,556.0           -126.9          100,703,325.0           9,423,201.0    73,108.4
soros-1992       5.8 reserves_exhausted       9624       -5,705.0           -132.4          100,703,325.0           9,430,495.6   105,496.9
soros-1992       5.9 reserves_exhausted       9587       -5,844.2           -127.5          100,703,325.0           9,433,215.1   137,928.3
soros-1992       6.0 reserves_exhausted       9553       -5,975.4           -144.3          100,703,325.0           9,441,626.2   126,437.4
soros-1992       6.1 reserves_exhausted       9518       -6,097.6           -133.8          100,703,325.0           9,440,303.8   140,216.6
soros-1992       6.2 reserves_exhausted       9486       -6,213.6           -145.8          100,703,325.0           9,454,892.7   133,291.3
soros-1992       6.3 reserves_exhausted       9455       -6,322.9           -146.6          100,703,325.0           9,452,365.7   136,808.8
soros-1992       6.4 reserves_exhausted       9425       -6,426.7           -129.0          100,703,325.0           9,467,239.5   158,019.9
soros-1992       6.5 reserves_exhausted       9396       -6,524.7           -129.3          100,703,325.0           9,458,483.4   162,063.8
soros-1992       6.6 reserves_exhausted       9369       -6,617.8           -142.5          100,703,325.0           9,481,864.0   154,457.6
soros-1992       6.7 reserves_exhausted       9342       -6,706.0           -149.6          100,703,325.0           9,470,757.4   152,124.8
soros-1992       6.8 reserves_exhausted       9317       -6,790.1           -130.3          100,703,325.0           9,491,433.0   175,578.1
soros-1992       6.9 reserves_exhausted       9291       -6,869.8           -130.6          100,703,325.0           9,483,795.4   179,850.2
soros-1992       7.0 reserves_exhausted       9268       -6,945.8           -137.9          100,703,325.0           9,502,003.2   177,992.1
```

`make figures` (12 workers), on commit `6e83b46`:

```
sweep: threshold-surface-ref-mc cells=640 workers=12
sweep: threshold-surface-mc cells=640 workers=12
sweep: budget-x-depth-mc cells=200 workers=12
sweep: oracle-lag-mc cells=640 workers=12
wrote: 10 figures and docs/figures/manifest.json (commit 6e83b468af51)
make figures: wall time 433 s (12 workers)
```

Close-out:

```
$ pytest -o addopts="" -q
559 passed in 8.84s
exit=0
$ ruff check .
All checks passed!
exit=0
$ ruff format --check .
87 files already formatted
exit=0
$ make figures-check
figures-check: ok, 10 figures match their sources
exit=0
```

552 tests at story start; +7 (4 fill-rule, 2 sawtooth cases, 1 hash pin).

CI, GitHub run 37387533598 on this commit's tree (scratch branch `story/3-1-ci`, deleted
after):

```
test: success (2026-10-05T23:16:27Z → 2026-10-05T23:17:07Z)
  All checks passed!
  87 files already formatted
  559 passed in 17.92s
  figures-check: ok, 10 figures match their sources
figures-quick: success (2026-10-05T23:16:27Z → 2026-10-05T23:25:20Z)
  quick: ok, 10 figures drawn; wrote docs/figures/quick-ok only
  make figures-quick: wall time 508 s (4 workers)
```

### Completion Notes List

**C\*, before → after: unchanged.** 9,166,667 model units → **9,166,667**; ≈ $2,150,500,078
→ **≈ $2,150,500,078** at `s`; 0.79× the attacker's episode net burn → **0.79×**
(11,540,596 units). The fit lands on the same point by a different path. 10M is now
−954.2 bps (was −224.6), so pass 2 refines between 7.5M and 12.5M (was 5M–10M), and
9,166,667 gives −1,137.8 bps under both rules. No capital value changes in any scenario,
so no `content_hash()` moves. The YAML headers and SOURCES.md record the re-fit in
comments and notes.

**VALIDATION.md 3.1 row:**

| replay | trough depth | trough time | first in band after 85 h | sawtooth amplitude, steps 8,100–9,150 |
|---|---|---|---|---|
| 3.1 (capped holder, C\* 9,166,667) | −1,137.8 bps | 34.2 h (step 10,269) | 85.3 h | 384.5 bps (−27.6 … −412.1) |

(2.6: −1,137.8 / 34.2 h, step 10,255 / 85.3 h / 662.9 bps.)

**Sawtooth amplitude, before → after:** 662.9 → **384.5 bps** over the AC window;
265.2 → **10.2 bps** over the held stretch (steps 8,400–9,000). The AC window starts at
the attack's first step (−28 bps, before the price reaches −200). It ends 52 steps into
the fall to the trough, when the holder's reference is nearly spent. Those two ends
dominate the number. Nothing in the window is above the holder's entry price. At whole
hours the first 3.5 h read −28, −213, −208, −204 bps (2.6: −28, −171, −197, −196).

**Predictions:**
- Sawtooth to ≤ 60 bps: **missed** as defined (384.5). Held for the plateau (10.2). The
  baseline was 662.9, not ~530: ADR-0021's +310/−220 was read off the figure.
- `C*` within 8.3M–10M: **held** (9,166,667, unchanged).
- Trough within 100 bps of −1,138: **held** (−1,137.8).
- Trough time within 1 h of 34.2 h: **held** (34.23 h, +14 steps).
- C\* moves ≤ 10%: **held** (0%).
- 1992 flip stays at 5.7: **missed.** Every multiple ≥ 5.2 (ratio 1.100) now exhausts;
  5.0 also exhausts (`steps_run` 14,287) and 5.1 stalls.
- AC 6's "attacker's 10%-of-remaining dumps": the replay attacker sells 0.2% of remaining
  per step (pace 0.002). The ADR states the actual mechanism.

**The 1992 flip moves 5.7 → 5.2 (finding candidate, ADR-0024).** Pre-3.1 code reproduces
ADR-0021's table exactly. Under the fill rule the dead zone shrinks from 4.0–5.6 to
4.0–4.9 plus 5.1. The holder is profitable at every multiple (+28.5k … +180k; was −1.02M …
−6.5k). Diagnostic at 5.5:
- 2.6 holder: its overshoots kept spot ≥ the $0.98 payout in 7,945 of 11,399 post-attack
  steps (max 1.034). The arbitrageur redeemed only 81.7M and the holder 15.8M (97.6M
  total), so reserves never ran out.
- Capped holder: the arbitrageur redeems 91.5M and the holder 9.2M, and reserves exhaust
  at `steps_run` 12,353.

The old holder was a loss-making second defender of the floor.

**Propagated scenarios:** same outcomes.
- `calibrated-baseline` / `calibrated-stress`: `peg_recovered` at 7024 / 7225, trough
  −1,253.2 / −1,231.0. The defender spends **+27%** (6.05M → 7.70M) because the capped
  holder absorbs less (bought 4.66M → 2.89M).
- `soros-1992`: `reserves_exhausted`, 9,550 → 9,553.
- `soros-1992-no-defense`: `reserves_exhausted`, 7,807 → 7,805.

**Overlay, first 3.5 h:**
- *Before:* a dense black sawtooth between ≈ +315 and −220 bps from 27 h to ≈ 30.5 h; the
  y-axis reached +400 to hold it.
- *After:* a near-vertical drop at 27 h to ≈ −220 bps, then a single thin line easing from
  −215 to −204 bps until ≈ 30.3 h, then the plunge. Nothing is above zero after the attack
  starts, and the y-axis tops out at +100. From 31.5 h on the figure is unchanged.

**Figures.** Seven PNGs changed and three are byte-identical (`budget_depth`,
`oracle_sensitivity`, `peg_trajectory_baseline`). Every p(stays broken) cell of both
threshold surfaces and of budget × depth is unchanged; F-10's trough range is unchanged.
`time_to_parity` moves in three fast cells (4× D\*: 0.2 → 0.3 h, 0.2 → 3.6 h; 2× D\*:
1.9 → 2.0 h) and no clock/price category changes. `docs/figures/README.md` captions for
the calibrated and 1992 trajectories are updated to the new numbers.

**Guard gap (no ADR of its own; noted in ADR-0024).** No source hash moved, so `make
figures-check` was already green before the regeneration. A behaviour change in agent
code with unchanged inputs is invisible to the guard by design (Story 2.9). The figures
were regenerated because the story said to.

**ADR:** `docs/adr/0024-holder-fill-price-limit.md`, Proposed. It covers the fill rule
(with the ≤ 0.1 bps undershoot), C\* unchanged, the sawtooth, the baseline defender +27%,
and the 1992 flip as a finding candidate. Index not edited.

### File List

**Created:**

- `docs/adr/0024-holder-fill-price-limit.md`

**Modified:**

- `src/depeg_sim/agents/holder.py` (fill cap via `arbitrageur._reference_to_reach`; DUST
  fall-through; docstring)
- `tests/test_holder.py` (3 tests moved to spot 0.95; 4 fill-rule tests; two-step sawtooth
  synthetic, old rule vs new)
- `tests/test_holder_config.py` (3.1 hash pin)
- `scenarios/usdc-2023.yaml`, `calibrated-baseline.yaml`, `calibrated-stress.yaml`,
  `soros-1992.yaml`, `soros-1992-no-defense.yaml` (header comments only; hashes unchanged)
- `docs/calibration/VALIDATION.md` (Story 3.1 section), `docs/calibration/SOURCES.md`
  (holder rows)
- `docs/figures/*.png` (7 changed), `docs/figures/manifest.json`, `docs/figures/README.md`
- `docs/stories/3-1-holder-fill-price-limit.md`

## Senior Developer Review (AI)

**Reviewer:** Claude (dev manager, Fable 5.1)
**Date:** 2026-10-05
**Outcome:** **APPROVE** ✅ — the artefact is gone where it matters, C\* did not move, and
the 1992 flip moving is a finding.

### Summary

Reproduced on the review box (Python 3.13.15, fresh install): `pytest` → `559 passed in
36.46s`; `ruff check .` → `All checks passed!`; `ruff format --check .` → `87 files already
formatted`; `make figures-check` → ok. Replay: −1,137.8 at `max_steps`; calibrated
baseline: −1,253.2, `peg_recovered` at 7024, defender spent 7,699,787; soros-1992 at 6×:
exhausted at `steps_run` 9553, holder PnL +126,437. Sawtooth amplitude from the committed
timeseries: **384.5 bps** over steps 8,100–9,150 (max −27.6, nothing above zero), **10.2 bps**
over the 8,400–9,000 plateau. **1992 re-scan slice** at {5.1, 5.2, 5.6, 5.7} × Quantum on
current code: 5.1 `max_steps`, 5.2 exhausted at 10,506, 5.6 at 13,965, 5.7 at 9,663 —
the flip at 5.2 reproduces.

### Rulings

1. **ADR-0024 → Accepted (finding, amended).** The 1992 section becomes **F-12**; the
   "defender spend falls 41%" figure in ADR-0021 is corrected there to 25% by reference.
2. **Sawtooth prediction "≤ 60 bps" → missed as defined, held as meant.** My window
   (8,100–9,150) included the attack's first steps and the start of the fall, which no
   fill rule can touch. The plateau is 10.2 bps against a 31 bps band; at whole hours the
   residual is unreadable in the series. The artefact is gone. Future amplitude metrics
   are defined over the stretch the agent actually controls.
3. **AC 6's "10% of remaining" → my error**; the replay attacker's pace is 0.002. The ADR
   uses the real figure. Noted.
4. **The stale-figure guard cannot see agent-code changes** — the builder's observation,
   and it is right: this story changed seven figures without any source hash moving. Story
   3.5 adds a `code_hash` (sha256 over `src/depeg_sim/**/*.py`) to the manifest;
   `figures-check` **warns** on a code-hash mismatch and **fails** on a source mismatch,
   and `make figures` is a mandatory step on the freeze checklist. Added to 3.5's ACs.
5. **C\* unchanged by a different search path → accepted.** The rule is deterministic given
   the model; the model changed, the path changed, the point did not. Recorded.

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|---|---|---|
| 1 | ✅ | cap via `_reference_to_reach`, reused; fall-through on ≤ DUST; hashes unchanged |
| 2 | ✅ | cap test; uncapped test; new two-step sawtooth test |
| 3 | ✅ | fit re-run; C\* same; VALIDATION.md 3.1 row; amplitude as defined and on the plateau |
| 4 | ✅ | four scenarios re-run; before/after table; 1992 re-scanned in full (and sliced here) |
| 5 | ✅ | `make figures` 433 s; guard ok; overlay first 3.5 h described before/after |
| 6 | ✅ | ADR-0024 with the undershoot stated and the residual explained |
| 7 | ✅ | 559 passed; ruff clean; both CI jobs green |

**7 of 7 ACs met.**

### Key Findings

- **F-12 (new): a believer who overpays is an accidental defender.** Under the 2.6 rule
  the holder's overshoots held the AMM at or above the $0.98 redemption payout for 70% of
  the steps after the attack, so the arbitrageur stopped redeeming and reserves lasted to
  the horizon; the holder lost money doing it. Capped, the holder spends its own capital
  and no more, the arbitrageur redeems 91.5M instead of 81.7M, and reserves exhaust. The
  1992 flip moves from 5.7× to **5.2× Quantum (ratio 1.100)**, closer to the F-06
  formula's 1.0. In the calibrated baseline the same change costs the defender 27% more.
  For the note: belief only helps the issuer when it is *undisciplined*; a disciplined
  believer is a redeemer in waiting.
- The replay is unchanged at the trough and from 35 h on; figure 1 now has a clean first
  three hours.

### Learnings for Story 3.2

- Define any amplitude or timing metric over the stretch the agent under test controls.
- `make figures` after every agent change, guard or no guard, until 3.5 lands the code
  hash.
- Policy comparisons must report defender spend *and* who else absorbed the attack; 3.1
  showed the holder and defender trade absorption one for one.

## Change Log

- 2026-10-05: Story drafted by dev manager at the Epic 2 retro
- 2026-10-05: Blocked by builder (Claude Code, Opus 5.5) before Task 1: the arbitrageur's sizing helper ignores the fee, AC 1 asks for fee-exact; see Blockers
- 2026-10-05: Dev manager ruled on Blockers: reuse the arbitrageur helper unchanged (option a); three implementation notes accepted; AC 1, AC 2 and Dev Notes amended; Status back to in-progress
- 2026-10-05: Implemented by builder (Claude Code, Opus 5.5): fill rule; C* re-fit (unchanged); replay, propagation, 1992 full re-scan (flip 5.7 → 5.2); figures regenerated; ADR-0024 Proposed. Status review
- 2026-10-05: Senior review APPROVE; ADR-0024 accepted (finding, amended); F-12 added; Status done
