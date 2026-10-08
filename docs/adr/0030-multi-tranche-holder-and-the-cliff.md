# ADR-0030: Multi-tranche holder; ladder B fits the replay trough to 3.6% and on time; the cliff becomes a staircase, not a curve (F-09 narrowed)

**Status:** Proposed
**Date:** 2026-10-07
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** Story 3.7

## Context

F-09 (ADR-0021, ADR-0024): with one par-expecting buyer at one entry price, the replay's
trough as a function of buyer capital is close to bimodal. Below a cliff the buyer runs
out of reference and the attacker sets the trough; above it the trough sits at the
buyer's 2% entry. The fit lands at −1,137.8 bps (17% short of the observed −1,373) and
3.2 h late. F-09 proposed buyers at a spread of entry prices as the next model: "a single
believer gives a cliff; many believers at different prices give a curve."

Story 3.7 adds the ladder, fits total capital for three fixed ladders with the unchanged
rule, and tests the cliff.

## Decision

1. **Config.** `HolderConfig.tranches: list[Tranche] | None`,
   `Tranche(entry_discount_pct ≥ 0, 0 < share ≤ 1)`. Validators: exactly one of
   `entry_discount_pct` and `tranches` is set ("entry_discount_pct must be absent when
   tranches is set"); shares sum to 1 within 1e-9; entry discounts strictly increasing;
   with tranches, `exit_discount_pct` must exceed the *deepest* tranche's discount (the
   3.3 rule, generalised). `content_hash()` drops `tranches` when `None`, so every
   existing scenario hash is unchanged (pinned in `tests/test_holder_tranches.py`); when
   set it replaces the absent `entry_discount_pct`.

2. **Tranche semantics** (judgment calls the ACs left open):
   - **Books.** Each tranche keeps a reference balance (starts at `capital × share`) and the
     stable it bought. The holder's `balances` stay the pooled totals.
   - **Buys.** Every tranche whose entry price is above spot buys
     `min(pace × its reference, cap_i)` in the same step, so a step can carry several
     `hold_buy` swaps (ADR-0011 `{"actions": [...]}`, each action record with `tranche`).
     **Deepest entry first**, with **chained caps**: after tranche *i* buys *a*, the next
     sizes its cap from `reserve_reference + a` and checks its entry against the implied
     spot `(reserve_reference + a)² / k` (fee ignored, as for the 3.1 cap). No tranche
     lifts the price past its own entry, and the deep bidders fill at the lowest prices,
     as a ladder of resting bids would.
     *Alternatives:* shallowest first (the 1% bidder would take the cheap fills a 5%
     bidder was waiting for, the opposite of an order book); one pooled swap capped at the
     shallowest entry (loses per-tranche attribution and lets the 1% tranche's cap govern
     money the 5% tranche would not spend there); one tranche per step (an arbitrary
     rotation that slows the ladder by its length).
   - **Redeem and exit** are unchanged and act on the pooled stable. The reference a
     redemption pays, or an exit sale returns, is credited to tranches **pro rata to the
     stable each held** before it, and their stable falls pro rata. A tranche's recycled
     reference is spent again only below that tranche's entry.
     *Alternative:* return all proceeds to a shared pool any tranche can spend; rejected
     because it lets redemption proceeds of 10% buyers fund 2% buys, blurring the ladder.
   - **One tranche is the scalar form.** With a single tranche its book *is* the holder's
     book, no `tranche` key is recorded and the snapshot is unchanged; a single tranche at
     share 1 reproduces the scalar run on `usdc-2023.yaml` byte for byte (timeseries,
     events after `run_started`, checkpoints; and with decisions traced) — the summary
     and manifest differ only by the config hash (test).
   - Never calls `ctx.rng`. Rule names unchanged.

3. **Three ladders, fixed before any run** (assumptions, not fitted): front-loaded **A**
   1/2/5% at 50/30/20%; uniform-wide **B** 2/5/10/20% at 25%; uniform-fine **C**
   1/2/5/10/15% at 20%. They bracket plausible shapes; fitting a distribution's shape to
   one trough would be the hand-tuning the project has refused since 2.4.

4. **Fit** (`scripts/fit_holder.py --tranches …`, two-pass rule unchanged, D\* fixed):

   | ladder | C\* (units) | ≈ $ at s | × attacker net burn | trough at C\* | gap to −1,373 | trough time |
   |---|---|---|---|---|---|---|
   | single 2% (2.6/3.1) | 9,166,667 | $2.15B | 0.79× | −1,137.8 | +235.2 (17.1%) | 34.2 h |
   | A | 8,333,333 | $1.95B | 0.72× | −1,602.7 | −229.7 (16.7%) | 32.8 h |
   | **B** | **10,833,333** | **$2.54B** | **0.94×** | **−1,323.3** | **+49.7 (3.6%)** | **31.2 h** |
   | C | 10,000,000 | $2.35B | 0.87× | −1,489.0 | −116.0 (8.4%) | 32.8 h |

   B becomes `scenarios/usdc-2023-tranches.yaml`; `usdc-2023.yaml` is untouched.

5. **Cliff test** (B at `C* × m`, single entry at its own `C* × m`, both run now with the
   3.1 holder; `fit_holder.py --at-multiples-of`):

   | m | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 |
   |---|---|---|---|---|---|
   | ladder B | −2,003.1 | −2,000.8 | −1,323.3 | −1,007.8 | −1,006.7 |
   | single entry | −2,257.6 | −1,662.3 | −1,137.8 | −885.1 | −225.9 |

   **Verdict: the cliff is not gone; it becomes a staircase.** Over ±20% the range
   halves (996 vs 2,032 bps), but the response is treads and risers, not a curve: flat
   at a tranche's entry when that tranche outlasts the attack, a jump when it runs out
   first. The largest step per 10% of `C*` is 677 bps for B against 659 for the single
   entry. Each riser is F-09's cliff at a quarter of the capital. `C*` sits on the riser
   between the 10% and 20% treads: at the trough the 10% tranche has spent its whole
   share and the 20% tranche has bought nothing.

## Consequences

- **F-09 narrowed, not resolved.** "Many believers at different prices give a curve" is
  wrong in this model: they give a staircase whose treads are the entry prices. The fit
  lands near −1,373 only because one of B's risers contains it. Limitations sentence for
  the note: *With believers spread over four entry prices the replay's trough comes within
  4% of the observed depth and within ten minutes of its timing, but depth still moves
  with believer capital in steps set by the assumed entry prices, so the model matches
  March 2023's depth only to the spacing of a ladder no public data pins down.*
- **Trough timing is fixed as a by-product.** The single entry held −200 bps for 3.5 h
  before falling (trough 3.2 h late); the ladder steps through its entries and its 10%
  tranche runs out at ≈ 30.6 h, so the trough is at 31.2 h (observed 31.0 h). Pace was
  not re-fitted. From ≈ 48.6 h the path matches 3.1 to within 0.05 bps.
- Holder PnL +522.6k (single: +209.4k): deep tranches buy at 5–10% discounts. The
  arbitrageur redeems 2.85M (single: 2.10M).
- No kernel or protocol change; `PHASE_ORDER_VERSION` stays 1; every existing scenario
  hash is unchanged. The propagated scenarios (calibrated, 1992) keep the single entry;
  carrying a ladder into them is not in this story.
- New figure `validation_overlay_usdc_2023_tranches.png` (18 committed figures).

## Alternatives considered

- **Fit the ladder's shape** (entries or shares) to the trough: rejected, see Decision 3.
- **A continuous distribution of entry prices** (e.g. a density over 1–20%): the
  staircase suggests the treads move closer as entries get finer (C's treads near the
  observed trough are 500 bps apart, at −1,005 and −1,505; B's are 1,000 apart), so a
  continuum would give a curve; but a density is a shape to choose, with the same tuning
  problem. Not run here; left as an open question.
- **Comparing against 2.6's refinement table only:** that table predates the 3.1 cap and
  has no points at 0.8/0.9/1.1/1.2 × C\*; the single entry was re-run at exact multiples,
  and the 2.6 points nearest each multiple are shown beside them in VALIDATION.md.
