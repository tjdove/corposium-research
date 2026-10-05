# Story 2.8: Reference-Relative Recovery and the Budget × Depth Boundary

Status: review

## Story

As a **researcher**,
I want the recovery criterion to be able to measure the venue against the market price rather than against par,
so that the threshold surface shows where the attack beats the defense rather than where the reference wandered, and the note can test whether the price-defense boundary is set by budget against depth (F-11).

## Acceptance Criteria

1. `PegRecoveredConfig` gains `reference: Literal["par", "oracle"] = "par"`; every existing scenario's `content_hash()` unchanged (test); with `"oracle"`, the in-band test in `termination.check` uses `spot / oracle_price − 1` instead of `peg_deviation`, where `spot` comes from a new `PegView.spot_price` property and `oracle_price` from a new `ReferenceView` Protocol (**`published_price: float | None`**, amended 2026-10-04 — `reference_price` already means the raw pass-through per Story 1.5 AC 8) in `kernel/interfaces.py`, implemented by the Oracle as an alias of its existing `price`; before the first oracle publish the step counts as out of band; the kernel still reads only Protocol views (no import of `protocol/`); `PHASE_ORDER_VERSION` stays 1
2. `steps_to_first_band_entry` and `steps_to_sustained_recovery` in `summarize` follow the same criterion (document in the summary docstring which deviation they use); the manifest's resolved config already records `reference`
3. Tests: par behaviour byte-identical on `soros-baseline` (run-vs-rerun fixtures untouched); with `oracle` on a synthetic run where the reference drifts +50 bps and the AMM tracks it, `par` → `max_steps` and `oracle` → `peg_recovered`; before first publish → out of band
4. `sweeps/threshold-surface-ref-mc.yaml`: identical to `threshold-surface-mc.yaml` plus `overrides: {termination.peg_recovered.reference: oracle}`; run with `--mc`; `plot_threshold_surface` reads the criterion from the manifest's `base_config` (after overrides) and puts it in the heading; the chart written as `threshold_surface.png` in that sweep's directory
5. `sweeps/budget-x-depth-mc.yaml`: base `calibrated-baseline`, `reference: oracle`; linked depth axis as in 2.7 (five values, holder at 0.55×); axis `agents[type=defender].budget` over `41,346,974 × {0.25, 0.5, 1, 2, 4}`; attacker fixed by override at ratio 1.0 (`179,454,391`); 8 seeds from 1000; `max_steps` 18000; header states origins; `plot_budget_depth(sweep_dir) -> Path`: left panel heatmap of `p_stays_broken` over depth × budget with the 0.5 contour; right panel the budget at each depth row's 0.5 crossing (linear interpolation; "not reached" marked) against depth on log–log axes with a slope-1 reference line — the F-11 hypothesis is that the crossing budget scales with depth
6. Completion Notes: (a) the two surfaces side by side as a table of per-row 0.5 crossings (par criterion from 2.7 vs oracle criterion), (b) the budget × depth crossings and whether they scale with depth, (c) the headline sentence drafted from the oracle-criterion surface in the form "At calm volatility, an attack of X× the defenders' nominal resources leaves the venue price more than 31 bps below the market price through the 60 h horizon with probability ≥ 0.5 only in pools deeper than Y × D\*; the price-defense boundary is set by budget against depth: a budget of ≈ Z × the pool's reference-side depth holds the price against any attack in the grid", with X, Y, Z from the data or "not supported" if they aren't
7. `scenarios/usdc-2023.yaml` keeps `par` (the replay's reference *is* the observed depeg); VALIDATION.md gains one sentence saying so
8. A `Proposed` ADR: the criterion option and its Protocol-view design, what the oracle criterion changed in the surface, the budget × depth result and its verdict on F-11's hypothesis, and which surface the note uses
9. `pytest` and `ruff check .` pass; CI green

## Tasks / Subtasks

- [x] Criterion option (AC: 1, 2, 3)
  - [x] `PegView.spot_price`; `ReferenceView`; Oracle implements; `PegRecoveredConfig.reference`; `termination.check`; `summarize` metrics; tests; hash test
  - [x] Commit separately: `story 2.8: peg_recovered.reference option` (1d9afde)
- [x] Reference-criterion surface (AC: 4)
  - [x] Sweep spec; run; chart heading from manifest; look and describe
- [x] Budget × depth (AC: 5)
  - [x] Sweep spec; run; `plot_budget_depth`; synthetic-parquet test; look and describe
- [x] Headline, ADR, close out (AC: 6, 7, 8, 9)
  - [x] Completion Notes tables and sentence; VALIDATION.md line; Proposed ADR (0023)
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.8: reference-relative recovery and budget x depth`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.7 (Status: done)**

- The criterion decides the chart. 2.7's surface measured the clock at ≤ D\* because the
  par criterion fails late recoveries against a wandering reference (F-11, F-04
  refinement). This story makes the criterion explicit and runs the sweep through it; no
  post-hoc filters.
- Mechanism seen in 2.7's `sweep.parquet` at ratio 1.5: the defender spends its whole
  budget in every row; final deviation −9.5 bps at ≤ D\*, −3,486 / −4,062 at 2× / 4×. A
  fixed budget buys the dump back when the pool is shallow enough to crash. AC 5 tests
  whether the crossing budget scales with depth.
- Report per-depth medians of `defender_spent` and `final_depeg_bps` from `sweep.parquet`
  for both new sweeps; they were decisive in 2.7's review.
- Conservation-shaped collapses are checks, not results; no absorbed-ratio panel here.

[Source: docs/stories/2-7-threshold-surface.md#Senior-Developer-Review, docs/FINDINGS.md F-10, F-11, F-04 refinement]

### Why a Protocol view and not an oracle import

`CLAUDE.md`: no domain logic in the kernel. `termination.check` already reads the AMM
through `PegView` (ADR-0007). The oracle's published price is the second number the
criterion needs, and it reaches the kernel the same way: a `ReferenceView` Protocol that
the Oracle satisfies, found by `ctx.registry.find(ReferenceView)`. If more than one
subsystem satisfies it, `find` returns the first registered; document that. If this
conflicts with ADR-0007's ownership statement in a way you can't resolve, propose the
amendment in the ADR rather than importing `protocol/`.

### Why `oracle` and not `environment reference`

The oracle is what the arbitrageur sees and what a reader would call "the market price";
the raw environment reference is unobservable in the model's own terms. F-10 says they
are within 0.5 bps at Chainlink's settings, so the choice does not move results; it keeps
the kernel reading a published number.

### Expected shapes (predictions, to be checked, not enforced)

- Oracle-criterion surface: the ≤ 1× D\* rows go to ≈ 0 at every ratio; 2× and 4× cross
  near nominal 0.69–0.70 as the 2.7 post-hoc filter suggested. If the contour runs along
  depth rather than capital, F-11's hypothesis is supported.
- Budget × depth: a crossing budget that rises with depth, roughly proportionally (a
  slope near 1 on log–log). Where the attack (ratio 1.0, $42B-equivalent) exceeds the
  pool by a large factor, attacker size should not matter and the crossing should be
  set by `budget / depth`. If the slope is clearly not 1, report it; that is the result.
- `usdc-2023` is untouched; its hash `2c3aeaa9825d` must not change.

### Cost

Surface: 640 runs (≈ 2.5 min on 8 workers). Budget × depth: 200 runs. Report real times.

### References

- [Source: docs/epics.md#Story-2.8]
- [Source: docs/FINDINGS.md] — F-03, F-04 (+ refinements), F-06, F-11
- [Source: docs/adr/0007-peg-view-owner-and-sign.md] — PegView ownership
- [Source: docs/adr/0022-threshold-surface-metric-and-oracle-lag.md] — §7
- [Source: src/depeg_sim/kernel/termination.py, interfaces.py]

## Blockers

**AC 1's `ReferenceView.reference_price`, "implemented by the Oracle as its published
price", collides with an existing Oracle property of the same name that means the
opposite.**

- `src/depeg_sim/protocol/oracle.py:103`: `Oracle.reference_price` already exists and
  returns `self.source.price`, the raw environment reference ("pass-through …, for
  diagnostics only"). It was specified that way by Story 1.5 AC 8: "`reference_price`
  (pass-through to `source.price`, for diagnostics)".
- Three tests pin that meaning:
  - `tests/test_oracle.py:84-86`: `oracle.reference_price == 1.0`, then `1.2` after the
    source moves, while `oracle.price is None` (unpublished).
  - `tests/test_oracle.py:152-157`: expects `(price, reference_price)` pairs
    `(1.0, 1.001), (1.0, 1.002)`. The two differ by design.
  - `tests/test_oracle_integration.py:48`: `oracle.reference_price == env.price`.
- AC 1 needs `reference_price` to be the **published** price (`None` before the first
  publish), and the Dev Notes say the kernel must read "a published number", not the
  environment reference. Satisfying AC 1 literally means redefining an accepted
  interface in `protocol/` and rewriting those three tests. If I satisfied it by
  structural accident instead, `find(ReferenceView)` would return the oracle with its
  *unpublished* price, which the Dev Notes rule out.

**Options** (I have not chosen):

- **(a) Rename the Protocol attribute** (recommended):
  `ReferenceView.published_price: float | None`, with the Oracle exposing
  `published_price` as an alias of its existing `price`. No existing semantics change and
  no existing test changes. The name is unique in the codebase, so `find(ReferenceView)`
  can only match the oracle. (Using plain `price` would also match the environment's
  `PriceSource`, which is registered first.)
- **(b) Repurpose `Oracle.reference_price`** as the published price and rename the
  diagnostic pass-through (e.g. `source_price`). The interface name matches AC 1 as
  written, but it changes Story 1.5's interface and three of its tests.

Nothing else in the story needs a ruling. Notes for the record, all implementable as
written:

- Adding `spot_price` to `PegView` means the termination test stub
  (`tests/kernel_stubs.py`) must gain `spot_price`, or `find(PegView)` stops matching it.
  This is a test-fixture edit, not a run-vs-rerun fixture.
- AC 4 needs the sweep manifest's `base_config` to be the base *after* overrides. Today
  (Story 2.7) it is before overrides. Identical for every existing sweep (none uses
  overrides), but `base_config`'s hash will then differ from `base_scenario_hash` when
  overrides exist. I'd document that in the ADR.
- AC 2: the summary can use the timeseries `amm_price` and `oracle_price` columns (the
  published price, `NaN` before the first publish, which counts as out of band).

**State.** Only the status lines changed. No code written.

## Rulings

**2026-10-04 (dev manager), on the Blockers above.**

1. **Option (a).** `ReferenceView.published_price`, the Oracle exposing it as an alias of
   `price`. `Oracle.reference_price` keeps its Story 1.5 meaning and its three tests. The
   name collision was mine. AC 1 and the context XML amended.
2. **`tests/kernel_stubs.py` gains `spot_price`** — accepted.
3. **Sweep manifest `base_config` = config after overrides** — accepted; note the hash
   consequence in the ADR as you proposed.
4. **Summary metrics from the timeseries `amm_price` / `oracle_price` columns** — accepted;
   `oracle_price` NaN before first publish is exactly "out of band until published".

Resume at the Criterion option task.

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-8-reference-recovery.context.xml)

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code on Seoul.

### Debug Log References

**Gate before the first commit** (baseline captured at b29c7c0 before any change: every
scenario `content_hash()`, and soros-baseline run artefacts in the scratchpad):

```
$ python -c "...content_hash() for scenarios/*.yaml" | diff - <scratch>/h28_before.txt && echo hashes-identical
hashes-identical
$ for f in summary.json timeseries.parquet events.jsonl decisions.jsonl; do cmp <scratch>/sb_before/*/$f <scratch>/sb_after/*/$f && echo "$f byte-identical"; done
summary.json byte-identical
timeseries.parquet byte-identical
events.jsonl byte-identical
decisions.jsonl byte-identical
PHASE_ORDER_VERSION = 1
$ python -m pytest 2>&1 | tail -1
531 passed in 7.38s
```
`summary.json` sha256 before = `ae9578ad45a35fe6986537a344d20746451d2ac74bd5a8ae331816f89fd77704`,
pinned in `tests/test_reference_recovery.py`. usdc-2023 hash
`2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531`.

**Reference-criterion surface (AC 4):**

```
$ time python -m depeg_sim.sweep sweeps/threshold-surface-ref-mc.yaml --mc --workers 10; echo exit=$?
sweep: threshold-surface-ref-mc cells=640 workers=10
wrote: output/threshold-surface-ref-mc/sweep.parquet
mc: threshold-surface-ref-mc grid_points=40 seeds=16 runs=640
wrote: output/threshold-surface-ref-mc/mc.parquet

real	2m26.230s
user	23m48.844s
sys	0m7.491s
exit=0
```

**Budget × depth (AC 5):**

```
$ time python -m depeg_sim.sweep sweeps/budget-x-depth-mc.yaml --mc --workers 10; echo exit=$?
sweep: budget-x-depth-mc cells=200 workers=10
wrote: output/budget-x-depth-mc/sweep.parquet
mc: budget-x-depth-mc grid_points=25 seeds=8 runs=200
wrote: output/budget-x-depth-mc/mc.parquet

real	0m51.096s
user	8m20.470s
sys	0m3.483s
exit=0
```

**Surfaces, crossings, per-depth medians** (`<scratch>/s28_surface.py`, repo root). The par
surface is Story 2.7's `output/threshold-surface-mc` (par behaviour is byte-identical, so
2.7's output stands):

```python
"""Story 2.8: par (2.7) vs oracle surfaces; per-row 0.5 crossings; per-depth medians."""
import numpy as np, pandas as pd
from depeg_sim.analysis.stats import fit_logistic
A = "agents[type=attacker].capital"; R = 179_454_391; D = 16_666_667
def load(name):
    mc = pd.read_parquet(f"output/{name}/mc.parquet")
    mc["ratio"] = (mc[A] / R).round(2); mc["xD"] = (mc.pool_depth / D).round(2)
    mc["p"] = 1 - mc.p_peg_recovered
    return mc
def lin_cross(x, p):
    x, p = np.asarray(x, float), np.asarray(p, float)
    hit = np.nonzero(p >= 0.5)[0]
    if hit.size == 0: return f"not reached (max {p.max():.3f})"
    i = hit[0]
    if i == 0: return f"<= {x[0]:g}"
    return f"{x[i-1] + (0.5 - p[i-1]) * (x[i] - x[i-1]) / (p[i] - p[i-1]):.3f}"
def logit_cross(g):
    k = (g.p * g.n).round().astype(int).tolist()
    if sum(k) == 0: return "n/a (all 0)"
    a, b = fit_logistic(g.ratio.tolist(), k, g.n.astype(int).tolist())
    return f"{-a/b:.3f}"
par, ora = load("threshold-surface-mc"), load("threshold-surface-ref-mc")
for name, mc in (("PAR (2.7)", par), ("ORACLE (2.8)", ora)):
    print(name, "p_stays_broken"); print(mc.pivot(index="xD", columns="ratio", values="p").round(4).to_string())
print("p_reserves_exhausted max:", par.p_reserves_exhausted.max(), ora.p_reserves_exhausted.max())
print("\nper-row 0.5 crossing (nominal ratio): linear | logistic")
for xd in sorted(par.xD.unique()):
    gp, go = par[par.xD == xd].sort_values("ratio"), ora[ora.xD == xd].sort_values("ratio")
    print(f"{xd:>5}xD*  par: {lin_cross(gp.ratio, gp.p):>22} | {logit_cross(gp):>12}   "
          f"oracle: {lin_cross(go.ratio, go.p):>22} | {logit_cross(go):>12}")
runs = pd.read_parquet("output/threshold-surface-ref-mc/sweep.parquet")
runs["xD"] = (runs.pool_depth / D).round(2); runs["ratio"] = (runs[A] / R).round(2)
print("\noracle surface, per-depth medians over all 128 runs per depth:")
print(runs.groupby("xD")[["defender_spent", "final_depeg_bps"]].median().round(1).to_string())
print("\noracle surface, per-depth medians at ratio 1.5 (16 runs per depth):")
print(runs[runs.ratio == 1.5].groupby("xD")[["defender_spent", "final_depeg_bps"]].median().round(1).to_string())
print("\noracle surface, terminated_by counts per depth:")
print(runs.pivot_table(index="xD", columns="terminated_by", values="seed", aggfunc="count", fill_value=0).to_string())
```
```
PAR (2.7) p_stays_broken
ratio  0.3  0.4    0.5     0.6    0.8     1.0     1.2     1.5
xD                                                           
0.25   0.0  0.0  0.000  0.0000  0.000  0.0000  0.1250  0.1875
0.50   0.0  0.0  0.000  0.1875  0.375  0.5625  0.5625  0.5000
1.00   0.0  0.0  0.375  0.5625  1.000  1.0000  1.0000  1.0000
2.00   0.0  0.0  0.500  1.0000  1.000  1.0000  1.0000  1.0000
4.00   0.0  0.0  0.000  0.5000  1.000  1.0000  1.0000  1.0000
ORACLE (2.8) p_stays_broken
ratio     0.3     0.4     0.5     0.6     0.8     1.0   1.2   1.5
xD                                                               
0.25   0.0625  0.0625  0.0625  0.0625  0.0625  0.0000  0.00  0.00
0.50   0.0000  0.0000  0.0625  0.0000  0.1875  0.1875  0.25  0.25
1.00   0.0625  0.0000  0.0625  0.1875  1.0000  1.0000  1.00  1.00
2.00   0.0000  0.0000  0.1250  1.0000  1.0000  1.0000  1.00  1.00
4.00   0.0000  0.0000  0.0000  0.1250  1.0000  1.0000  1.00  1.00
p_reserves_exhausted max: 0.0 0.0

per-row 0.5 crossing (nominal ratio): linear | logistic
 0.25xD*  par: not reached (max 0.188) |        1.737   oracle: not reached (max 0.062) |       -0.602
  0.5xD*  par:                  0.933 |        1.198   oracle: not reached (max 0.250) |        1.774
  1.0xD*  par:                  0.567 |        0.564   oracle:                  0.677 |        0.649
  2.0xD*  par:                  0.500 |        0.500   oracle:                  0.543 |        0.515
  4.0xD*  par:                  0.600 |        0.600   oracle:                  0.686 |        0.621

oracle surface, per-depth medians over all 128 runs per depth:
      defender_spent  final_depeg_bps
xD                                   
0.25      34180324.6             -2.8
0.50      41346974.0             -0.6
1.00      41346974.0             -8.1
2.00      41346974.0           -271.2
4.00      41346974.0           -301.6

oracle surface, per-depth medians at ratio 1.5 (16 runs per depth):
      defender_spent  final_depeg_bps
xD                                   
0.25      41346974.0              0.1
0.50      41346974.0              3.9
1.00      41346974.0             -9.5
2.00      41346974.0          -3485.6
4.00      41346974.0          -4061.5

oracle surface, terminated_by counts per depth:
terminated_by  max_steps  peg_recovered
xD                                     
0.25                   5            123
0.50                  15            113
1.00                  69             59
2.00                  82             46
4.00                  66             62
```

**When the oracle band is re-entered** (`<scratch>/s28_timing.py`):

```python
"""When does the AMM re-enter the oracle band, and is that too late to hold 6,900 steps?"""
import pandas as pd
A = "agents[type=attacker].capital"
r = pd.read_parquet("output/threshold-surface-ref-mc/sweep.parquet")
r["xD"] = (r.pool_depth / 16_666_667).round(2); r["ratio"] = (r[A] / 179_454_391).round(2)
r["entry_step"] = r.step_of_max_depeg + r.steps_to_first_band_entry   # NaN if never
r["latest_ok"] = 18_000 - 6_900                                        # last start that can finish
r["broken"] = r.terminated_by != "peg_recovered"
g = r[r.broken].copy()
g["never_entered"] = g.entry_step.isna()
g["entered_too_late"] = g.entry_step > 11_100
print("broken runs:", len(g), "| never re-entered the oracle band:", int(g.never_entered.sum()),
      "| first entry after step 11,100:", int(g.entered_too_late.sum()),
      "| entered by 11,100 but did not hold:", int((~g.never_entered & ~g.entered_too_late).sum()))
print("\nmedian first oracle-band entry step, by depth x ratio (all runs):")
print(r.pivot_table(index="xD", columns="ratio", values="entry_step", aggfunc="median").round(0).to_string())
print("\nnever re-entered (count of 16), by depth x ratio:")
print(r.assign(ne=r.entry_step.isna().astype(int)).pivot_table(index="xD", columns="ratio", values="ne", aggfunc="sum").to_string())
```
```
broken runs: 237 | never re-entered the oracle band: 128 | first entry after step 11,100: 80 | entered by 11,100 but did not hold: 29

median first oracle-band entry step, by depth x ratio (all runs):
ratio    0.3    0.4     0.5      0.6      0.8      1.0      1.2      1.5
xD                                                                      
0.25   116.0  119.0   119.0    119.0    125.0    125.0   2035.0   3664.0
0.50   107.0  112.0   114.0   2585.0   6272.0   7655.0   8440.0   9150.0
1.00    86.0  107.0  5480.0   9017.0  12560.0  14450.0  15647.0  16943.0
2.00    77.0  557.0  7156.0  12767.0      NaN      NaN      NaN      NaN
4.00    66.0   70.0  1052.0   7852.0      NaN      NaN      NaN      NaN

never re-entered (count of 16), by depth x ratio:
ratio  0.3  0.4  0.5  0.6  0.8  1.0  1.2  1.5
xD                                           
0.25     0    0    0    0    0    0    0    0
0.50     0    0    0    0    0    0    0    0
1.00     0    0    0    0    0    0    0    0
2.00     0    0    0    0   16   16   16   16
4.00     0    0    0    0   16   16   16   16
```

**Budget × depth analysis** (`<scratch>/s28_budget.py`):

```python
"""Story 2.8 budget x depth: crossing budget per depth row, log-log slope, medians."""
import numpy as np, pandas as pd
B = "agents[type=defender].budget"; D = 16_666_667; B0 = 41_346_974
mc = pd.read_parquet("output/budget-x-depth-mc/mc.parquet")
mc["p"] = 1 - mc.p_peg_recovered; mc["xD"] = (mc.pool_depth / D).round(2); mc["xB"] = (mc[B] / B0).round(2)
print("p_stays_broken (rows depth / D*, columns budget / calibrated budget)")
print(mc.pivot(index="xD", columns="xB", values="p").round(3).to_string())
def crossing(b, p):
    """Budget where p_stays_broken falls through 0.5 as budget rises (linear interp)."""
    b, p = np.asarray(b, float), np.asarray(p, float)
    if (p < 0.5).all(): return None, "holds at every budget (p < 0.5 at 0.25x)"
    below = np.nonzero(p < 0.5)[0]
    if below.size == 0: return None, "not reached (p >= 0.5 at every budget)"
    i = below[0]
    x = b[i-1] + (0.5 - p[i-1]) * (b[i] - b[i-1]) / (p[i] - p[i-1])
    return x, f"{x:,.0f} ({x / B0:.3f}x calibrated budget)"
rows = []
for xd, g in mc.sort_values(B).groupby("pool_depth"):
    x, txt = crossing(g[B], g.p)
    rows.append((xd, x)); print(f"depth {xd/D:.2f}x D* ({xd:,}): crossing budget {txt}"
          + ("" if x is None else f"; budget/depth = {x/xd:.3f}"))
pts = [(d, x) for d, x in rows if x is not None]
if len(pts) >= 2:
    ld, lb = np.log([d for d, _ in pts]), np.log([x for _, x in pts])
    slope, icpt = np.polyfit(ld, lb, 1)
    print(f"log-log least-squares slope over {len(pts)} rows: {slope:.3f}")
    for (d1, x1), (d2, x2) in zip(pts, pts[1:]):
        print(f"  segment {d1/D:.2f}->{d2/D:.2f}x D*: slope {np.log(x2/x1)/np.log(d2/d1):.3f}")
r = pd.read_parquet("output/budget-x-depth-mc/sweep.parquet")
r["xD"] = (r.pool_depth / D).round(2); r["xB"] = (r[B] / B0).round(2)
print("\nper-depth medians over all 40 runs per depth:")
print(r.groupby("xD")[["defender_spent", "final_depeg_bps"]].median().round(1).to_string())
print("\nmedian final_depeg_bps by depth x budget:")
print(r.pivot_table(index="xD", columns="xB", values="final_depeg_bps", aggfunc="median").round(1).to_string())
print("\nmedian defender_spent / budget by depth x budget:")
print((r.assign(f=r.defender_spent / r[B])).pivot_table(index="xD", columns="xB", values="f", aggfunc="median").round(3).to_string())
r["entry"] = r.step_of_max_depeg + r.steps_to_first_band_entry
print("\nnever re-entered the oracle band (count of 8):")
print(r.assign(ne=r.entry.isna().astype(int)).pivot_table(index="xD", columns="xB", values="ne", aggfunc="sum").to_string())
print("\nmedian first oracle-band entry step (> 11,100 cannot finish 6,900 steps by 18,000):")
print(r.pivot_table(index="xD", columns="xB", values="entry", aggfunc="median").round(0).to_string())
```
```
p_stays_broken (rows depth / D*, columns budget / calibrated budget)
xB     0.25   0.50  1.00   2.00   4.00
xD                                    
0.25  0.125  0.125  0.00  0.000  0.000
0.50  0.250  0.250  0.25  0.125  0.125
1.00  1.000  1.000  1.00  0.125  0.125
2.00  1.000  1.000  1.00  0.375  0.125
4.00  1.000  1.000  1.00  1.000  0.000
depth 0.25x D* (4,166,667): crossing budget holds at every budget (p < 0.5 at 0.25x)
depth 0.50x D* (8,333,334): crossing budget holds at every budget (p < 0.5 at 0.25x)
depth 1.00x D* (16,666,667): crossing budget 64,973,816 (1.571x calibrated budget); budget/depth = 3.898
depth 2.00x D* (33,333,334): crossing budget 74,424,553 (1.800x calibrated budget); budget/depth = 2.233
depth 4.00x D* (66,666,668): crossing budget 124,040,922 (3.000x calibrated budget); budget/depth = 1.861
log-log least-squares slope over 3 rows: 0.466
  segment 1.00->2.00x D*: slope 0.196
  segment 2.00->4.00x D*: slope 0.737

per-depth medians over all 40 runs per depth:
      defender_spent  final_depeg_bps
xD                                   
0.25      40196662.7             -4.1
0.50      41346974.0            -12.5
1.00      41346974.0            -19.8
2.00      41346974.0          -1767.2
4.00      41346974.0          -2001.7

median final_depeg_bps by depth x budget:
xB      0.25    0.50    1.00  2.00  4.00
xD                                      
0.25    -4.1    -4.1    -9.4  -9.4  -9.4
0.50    -9.4   -10.6   -10.6 -19.5 -19.5
1.00   -42.6   -23.8   -24.5 -12.5 -12.5
2.00 -3132.0 -2603.0 -1767.2 -11.0 -17.9
4.00 -3456.2 -2936.5 -2001.7 -24.9  -9.4

median defender_spent / budget by depth x budget:
xB    0.25  0.50   1.00   2.00   4.00
xD                                   
0.25   1.0   1.0  0.972  0.486  0.243
0.50   1.0   1.0  1.000  0.706  0.353
1.00   1.0   1.0  1.000  0.955  0.478
2.00   1.0   1.0  1.000  1.000  0.590
4.00   1.0   1.0  1.000  1.000  0.654

never re-entered the oracle band (count of 8):
xB    0.25  0.50  1.00  2.00  4.00
xD                                
0.25     0     0     0     0     0
0.50     0     0     0     0     0
1.00     0     0     0     0     0
2.00     8     8     8     0     0
4.00     8     8     8     0     0

median first oracle-band entry step (> 11,100 cannot finish 6,900 steps by 18,000):
xB       0.25     0.50     1.00     2.00   4.00
xD                                             
0.25   5234.0   4967.0    125.0    125.0  125.0
0.50   9485.0   9180.0   7656.0    122.0  122.0
1.00  16577.0  15905.0  14448.0    113.0  113.0
2.00      NaN      NaN      NaN  10985.0  108.0
4.00      NaN      NaN      NaN  14320.0   84.0
```

**Final gates** (charts re-rendered from the final code):

```
output/threshold-surface-ref-mc/threshold_surface.png 280726
output/budget-x-depth-mc/budget_depth.png 256867
$ ruff check .; ruff format --check .
All checks passed!
ruff_check_exit=0
84 files already formatted
ruff_format_exit=0
$ python -m pytest
537 passed in 7.47s
pytest_exit=0
$ grep -rn "import.*protocol\|from depeg_sim.protocol" src/depeg_sim/kernel/
(no matches: exit=1)
PHASE_ORDER_VERSION = 1
scenario hashes identical to b29c7c0 (usdc-2023 2c3aeaa9825d)
$ git diff b29c7c0 --stat -- scenarios/
```

### Completion Notes List

**(a) Two surfaces, per-row 0.5 crossings** (nominal ratio = capital / (budget +
reserves); linear interpolation | per-row logistic; 16 seeds; calm volatility):

| depth | par (2.7) | oracle (2.8) |
|---|---|---|
| 0.25× D\* | not reached (max 0.19) \| 1.74 extrap. | not reached (max 0.06) |
| 0.5× D\* | 0.93 \| 1.20 | not reached (max 0.25) \| 1.77 extrap. |
| 1× D\* | 0.57 \| 0.56 | **0.68** \| 0.65 |
| 2× D\* | 0.50 \| 0.50 | 0.54 \| 0.52 |
| 4× D\* | 0.60 \| 0.60 | 0.69 \| 0.62 |

- **What changed.** The oracle criterion removes the reference wander: the 0.25× and
  0.5× rows fall to ≤ 0.25, and the low-ratio cells stay near 0. The 2.7 0.5× D\*
  plateau (0.50–0.56, broken runs at +51 bps above par) is gone.
- **What did not change.** The **1× D\* row still goes to 1.0 from ratio 0.8. Prediction
  missed.** The price does come back to the market there (0 of 128 runs fail to
  re-enter the oracle band; median final −9.5 bps at 1.5). But the first re-entry comes
  at a median step of 12,560 (0.8) to 16,943 (1.5), after step 11,100, the last start
  that can finish 6,900 in-band steps by step 18,000. That is the clock (F-06 / F-11),
  not the price.
- **Two kinds of "broken".** Of the 237 runs that stay broken:
  - 128 **never re-enter** the oracle band: all 16 seeds at 2× and 4× D\* at ratio ≥ 0.8,
    final median −3,486 / −4,062 bps at 1.5. This is the attack winning the price.
  - 80 re-enter after step 11,100.
  - 29 re-enter earlier and do not hold it.
- **2.7's filter was wrong at D\*.** Its post-hoc last-step filter said ≤ 2/16 break at
  D\*. It counted late recoveries as recoveries.
- **Contour shape: prediction partly missed.** At ≥ 1× D\* the contour still runs along
  capital (0.54–0.69). Along depth it sits between 0.5× D\* (never ≥ 0.5) and 1× D\*.
  The predicted 2×/4× crossing "near 0.69–0.70" holds at 4× (0.69). At 2× it is 0.54,
  because at ratio 0.6 every run re-enters (median step 12,767) and then fails the clock.
- **Per-depth medians, oracle surface** (all 128 runs per depth; at ratio 1.5 in
  brackets):
  - `defender_spent`: 34.2M at 0.25× D\* [41.3M]; 41.3M at every other depth [41.3M].
    The whole budget at every depth at ratio 1.5.
  - `final_depeg_bps`: −2.8 [0.1], −0.6 [3.9], −8.1 [−9.5], −271.2 [−3,485.6],
    −301.6 [−4,061.5] for 0.25×, 0.5×, 1×, 2× and 4× D\*.
- `p_reserves_exhausted` = 0 in all cells of both sweeps.

**(b) Budget × depth: the crossing budget does not scale with depth. F-11's hypothesis
is not supported.** Attacker fixed at ratio 1.0 (179,454,391 = $42.1B), oracle criterion,
8 seeds:

| depth | 0.5-crossing budget (× calibrated 41.3M) | budget / depth at crossing |
|---|---|---|
| 0.25× D\* | not reached: holds at every budget (p ≤ 0.125 at 0.25×) | < 2.48 |
| 0.5× D\* | not reached: holds at every budget (p ≤ 0.25 at 0.25×) | < 1.24 |
| 1× D\* | **1.57×** (64.97M) | 3.90 |
| 2× D\* | **1.80×** (74.42M) | 2.23 |
| 4× D\* | **3.00×** (124.04M) | 1.86 |

- **Log–log slope** over the three crossing rows: **0.47** (segments 0.20 and 0.74),
  not 1.
- **The price alone shows it more clearly.** Counting runs that never re-enter the
  oracle band, at 2× and 4× D\* the price fails in 8/8 seeds at ≤ 1× budget and holds
  in 8/8 at 2× budget. The boundary sits in the same budget interval while depth
  doubles.
- **Counterexample.** The same budget/depth ratio 1.24 fails at 2× D\* (41.3M) and holds
  at 4× D\* (82.7M).
- **What the crossings are made of.** At 1× D\* the price is never lost at any budget
  (0 never re-enter). Its p ≥ 0.5 at ≤ 1× budget is the clock again: re-entry at median
  step 14,448–16,577.
- **Medians.** `defender_spent` per depth is 40.2M, then 41.3M ×4: the whole budget
  wherever the budget ≤ 1×. `final_depeg_bps` per depth is −4.1, −12.5, −19.8, −1,767.2
  and −2,001.7.
- **Caveats.** The grid steps budget by a factor of 2 with 8 seeds, so the slope is
  coarse but clearly below 1. There is one attack size, so "budget against the attack"
  is the next hypothesis, not a result.

**(c) Headline sentence (AC 6 form), from the oracle-criterion surface:**

> At calm volatility, an attack of **≈ 0.7×** the defenders' nominal resources leaves
> the venue price more than 31 bps below the market price through the 60 h horizon with
> probability ≥ 0.5 only in pools deeper than **1 × D\***; the price-defense boundary is
> set by budget against depth: a budget of ≈ **Z (not supported)** × the pool's
> reference-side depth holds the price against any attack in the grid.

- **X ≈ 0.7** is grid-limited to (0.6, 0.8). Read literally as "below the market
  price through the horizon", i.e. never re-entering the oracle band, the 2× and 4× D\*
  rows go from 0/16 at 0.6 to 16/16 at 0.8. The `p_stays_broken` crossings are 0.54 and
  0.69.
- **Y = 1.** Only the 2× and 4× D\* rows lose the price. At 1× D\* `p_stays_broken`
  crosses at 0.68, but that is the clock: the price is back within 31 bps of the market
  by the end, in 16/16 runs.
- **Z: not supported.** Budget/depth at the crossing is 3.90 → 2.23 → 1.86, the slope
  is 0.47, the same ratio gives opposite outcomes at 2× and 4× D\*, and the budget sweep
  has one attack, not "any attack in the grid".
- **A supported replacement for the second clause:** "at ratio 1.0, a pool at 2–4× D\*
  holds the price with between 1× and 2× the calibrated budget regardless of depth, and a
  pool at ≤ 0.5× D\* holds it with a quarter of it."

**Chart descriptions.**
- `threshold-surface-ref-mc/threshold_surface.png`. The heading names `reference=oracle`
  and "the published oracle price".
  - Left heatmap: the bottom two rows are almost white (0–0.25) across the whole capital
    range. The top three rows turn fully dark from 0.8× (1× D\* at 0.8×, 2× D\* already
    at 0.6×). The orange contour runs up from about 0.69× at 4× D\*, through 0.54× at
    2× D\* and about 0.68× at 1× D\*, then flat along the boundary between 0.5× and 1×
    D\* to the right edge. It is an L: capital sets the boundary above D\*, depth below.
  - Right (absorbed-ratio check, kept from 2.7): every point below 0.98 is ≤ 0.25 and
    every point above 1.03 is 1. The pooled logistic crosses at 1.018; the 0.5× squares
    sit at 0.19–0.25 out to 1.03.
- `budget-x-depth-mc/budget_depth.png`.
  - Left heatmap: dark in the top-left block (≥ 1× D\*, ≤ 1× budget, all 1.00), light
    elsewhere. One more dark cell at 4× D\* / 2× budget. The 0.25× row is 0–0.12 and
    the 0.5× row 0.12–0.25. The orange contour steps from the 0.5×/1× D\* boundary at
    low budget, up between 1× and 2× budget for 1× and 2× D\*, to between 2× and 4×
    budget at 4× D\*.
  - Right (log–log): three blue crossing points (1.57×, 1.80×, 3.00×) and two orange
    hollow down-triangles at 0.25× budget for 0.25× and 0.5× D\* (holds at the smallest
    budget). A dashed slope-1 line through the 2× D\* point. The blue line is visibly
    flatter than it, especially between 1× and 2× D\*. Legend: "least-squares log–log
    slope: 0.47".

**Implementation notes.**
- **Hash and config.** `content_hash` drops `peg_recovered.reference` when it is `par`
  (like the Story 2.5 fields), so every hash is unchanged. `model_dump`, and so the
  run manifest, always records it (AC 2).
- **Termination.** `_in_band` in `termination.py`: `published_price` falsy (None or 0)
  → out of band. No `ReferenceView` registered → out of band.
- **Tests.** The synthetic drift test uses the real `Oracle` (threshold 0) on a scripted
  reference walking to +50 bps, with an AMM stub that tracks it. `par` → `max_steps`
  at 400 steps; `oracle` → `peg_recovered` at 100. Also:
  - a summary test on a hand-built timeseries (an unpublished oracle step is skipped);
  - soros-baseline `oracle` = `par` at zero volatility;
  - the `summary.json` sha256 pin;
  - a hash pin over all 7 scenarios.
- **Charts.**
  - `plot_budget_depth` marks rows that hold at the smallest budget as hollow down-
    triangles and rows no budget holds as up-triangles. Neither occurs as "above" here.
  - `budget_crossing` is a public helper with its own test.
  - The absorbed-ratio panel stays on the surface chart, because AC 4 changes only its
    heading. It is a conservation check (2.7 review), not a result.
- `usdc-2023.yaml` is untouched; VALIDATION.md gains the "par, not the oracle" bullet
  (AC 7). The replay has `peg_recovered` off, and its band statistics use
  `peg_deviation` (par).
- ADR: **0023** (Proposed). It records ADR-0007 as extended, not amended.
- Wall times (10 workers, Seoul): surface **2m26.2s**, budget × depth **0m51.1s**.

### File List

**Created:**
- `sweeps/threshold-surface-ref-mc.yaml`
- `sweeps/budget-x-depth-mc.yaml`
- `docs/adr/0023-reference-relative-recovery-and-budget-depth.md`
- `tests/test_reference_recovery.py`

**Modified:**
- `src/depeg_sim/kernel/config.py` (`PegRecoveredConfig.reference`; `content_hash` drops it at `par`)
- `src/depeg_sim/kernel/interfaces.py` (`PegView.spot_price`, `ReferenceView`)
- `src/depeg_sim/kernel/termination.py` (`_in_band`)
- `src/depeg_sim/protocol/oracle.py` (`published_price` alias)
- `src/depeg_sim/analysis/summary.py` (recovery metrics follow the criterion)
- `src/depeg_sim/experiments/sweep.py` (`resolved_base`; manifest `base_config` after overrides)
- `src/depeg_sim/analysis/charts.py` (criterion in the surface heading; `plot_budget_depth`, `budget_crossing`)
- `tests/kernel_stubs.py` (`PegStub.spot_price`), `tests/test_charts.py`, `tests/test_sweep.py`
- `docs/calibration/VALIDATION.md` (AC 7)
- `docs/stories/2-8-reference-recovery.md`

## Change Log

- 2026-10-04: Story drafted by dev manager after Story 2.7 review (F-11); inserted into Epic 2; figures story renumbered to 2.9
- 2026-10-04: Blocked before implementation: `ReferenceView.reference_price` (AC 1)
  collides with the existing `Oracle.reference_price` (raw source pass-through, Story 1.5
  AC 8, pinned by three tests). Options (a) rename the Protocol attribute, (b) repurpose
  the Oracle property. Status: blocked.
- 2026-10-04: Dev manager ruled on Blockers: ReferenceView.published_price (option a); three implementation notes accepted; Status back to in-progress
- 2026-10-04: Resumed after Rulings. Criterion option (1d9afde); reference-criterion
  surface (2m26.2s) and budget × depth (0m51.1s) sweeps; `plot_budget_depth`; ADR-0023
  (Proposed). Predictions missed at 1× D\* (clock) and on the budget slope (0.47, not 1).
  537 tests pass, ruff clean. Status: review.
