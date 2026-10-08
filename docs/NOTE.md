# Research note — outline (v0.1, 2026-10-06)

**Status:** outline. Drafted during Epic 3 so Epic 4 is editing, not writing. Every section
names the finding(s) it carries and the committed figure it uses. Target 2,000–3,500 words;
this outline is the budget for them. Nothing here is quoted until the figure it cites has
passed the stale-figure guard at the freeze.

**Working title:** *What breaks a peg: a 1992 currency attack, replayed on-chain*

**One-paragraph abstract (draft).** We built a deterministic agent-based simulator of a
stablecoin under speculative attack, modelled on the 1992 ERM crisis, calibrated to Curve,
Chainlink and Circle parameters, and validated against the USDC depeg of March 2023. The
replay reproduces the observed trough to within 17% only once a buyer who expects
redemption at par is added — the depth of a depeg is set by the attacker against everyone
who believes the promise. Beyond that, the model says three things the 1992 analogy does
not: deep liquidity protects the price and makes the defense unaffordable; a defender that
spends fast is defending the attacker's exit price; and a believer who loses faith has two
exits on-chain, only one of which breaks the peg. We publish the code, every parameter's
source, and one command that regenerates every figure.

---

## 1. The question (≈ 250 words)

- Why 1992: a peg is a price promise; Black Wednesday is the canonical case of a promise
  exceeding the resources behind it under reflexive pressure (BACKGROUND §1–3).
- The on-chain version of the question: under what combination of pool depth, attacker
  capital, redemption throughput and defense policy do reserves — or the clock — run out?
- **The analogy is a tool, not a thesis** (charter principle). Where the mechanism changes
  is a result. Section 7 collects them.
- Audience sentence: for people who build, trade or study pegged assets.

## 2. The model in one page (≈ 400 words)

- Nine phases, one seed, byte-identical output (ADR-0002, PHASE_ORDER_VERSION).
- Venue: constant-product AMM. Oracle: heartbeat + deviation. Redemption: throughput-
  limited queue with spread. Agents: attacker, arbitrageur, defender, holder.
- What each real-world actor maps to (BACKGROUND mapping table), and the one that mapped
  wrong until Story 3.3 (the two exits — forward reference to §7).
- Recovery criterion: ±31 bps of par for 6,900 steps. The calm reference reverts to par
  with a half-life fitted from the calm USDC series (1.4 h); measuring against the oracle
  instead changes nothing in the sweeps (ADR-0023, one sentence). Time-to-parity as the
  working metric, which 3.6 showed is independent of the reference process.
- *No figure.* A small schematic if the site page needs one.

## 3. Calibration and validation (≈ 500 words) — **Figure 1: `validation_overlay_usdc_2023.png`**

- Every number sourced (SOURCES.md): Curve 3pool anchor, Chainlink 0.25% / 82,800 s,
  Circle 77/23, attacker = episode net burn $2.71B, D\* fitted, pace fitted.
- The replay failed first: −5,769 vs −1,373 bps (F-08). What was missing and why it was
  hidden by the defender on the calibrated baseline.
- One fitted buyer at $2.15B (0.79× the attack) → −1,138 bps; the simulated path lies on
  the observed one from 35 h to 49 h; trough 3.2 h late (pace not re-fitted); first hours
  clean after the fill-price fix (ADR-0024).
- Believers at a ladder of prices (2/5/10/20%, an assumption; best of three fixed ladders)
  with one fitted capital ($2.54B, 0.94× the attack) → −1,323 bps at 31.2 h (observed
  −1,373 at 31.0). **Figure 1b: `validation_overlay_usdc_2023_tranches.png`.** Both shown:
  what one parameter buys, what a stated assumption adds (F-09 refinement).
- What validation does and does not claim: one event, one fitted parameter, the hourly
  series cannot resolve the first-hour shape; F-09 (a single-entry buyer gives a cliff).
- **Headline 1:** the depth of a depeg is set by the attacker against everyone who
  believes the promise.

## 4. Depth, resources and the clock (≈ 600 words) — **Figure 2: `time_to_parity.png`**; supporting `threshold_surface.png`, `budget_depth.png`

- F-02 → F-03: the outcome is capital against resources, and depth enters through the
  price the defender pays. Shallow pools crash harder and are cheaper to defend.
- F-06: at issuer scale the redemption channel pays 10.9M of 138M in 60 h; reserves cannot
  exhaust; the failure mode is the clock.
- F-11 (+ refinement): ≤ 0.5× D\* comes back in minutes at any attack; D\* comes back at
  42–56 h, too late to hold; ≥ 2× D\* loses the price at ≥ 0.8× resources. The defending
  budget does not scale with depth (slope 0.47); above D\* the budget has to match the
  attack (3.4 result to insert).
- **Headline 2:** deep liquidity protects the price and makes the defense unaffordable.
- **Headline 4:** the binding constraint at issuer scale is the clock, not the reserves.

## 5. Which defense survives (≈ 400 words) — **Figure 3: `policy_comparison.png`** (panel b → price paid, Epic 4 redraw)

- F-13: every buying defender spends its whole budget; the slow one pays 0.283 per stable
  and the fast one 0.358; at a full-size attack only the slow one recovers. The fast
  defender is dry before the attacker has finished selling.
- Pace vs trigger (3.4 result to insert).
- F-07 refinement: no spread dead zone at calibrated scale; spread-only fails on the clock.
- **Headline 3:** the defender that waits wins; a defense that spends before the attacker
  is done is defending the attacker's exit price. The 1992 echo: the Bank spent fast, at
  the floor, while the selling was still coming.

## 6. Oracle lag (≈ 150 words) — **Figure 4: `oracle_sensitivity.png`**

- F-10: a flat line. At Chainlink's settings the trough moves < 0.5 bps against zero-lag;
  only a 1% deviation threshold with a long heartbeat moves anything, by 10 bps.
- One paragraph; the chart is the argument.

## 7. The 1992 analogue, and where it breaks (≈ 600 words) — **Figure 5: `peg_trajectory_1992.png`** (+ no-defense); the exit sweep is a null and stays in the record

- The analogue: 6× Quantum, reserves + budget as the Bank's war chest, 200 bps spread as
  the rate rises. It exhausts at 5.7× with no believers, 5.2× with a disciplined believer
  at C\*, **4.9× with believers at 0.9× the attacker who redeem** — within 4% of the
  resources formula.
- F-12: a believer who overpays is an accidental defender; a disciplined one is a redeemer
  in waiting.
- F-14 and the mapping: in 1992 "switching sides" meant selling to the Bank at the floor —
  a redemption. On-chain there are two exits. Selling on the venue breaks the price and
  spares the reserves and costs the seller 36–77%; redeeming spares the price and drains
  the reserves. BACKGROUND §4 is supported under the right mapping and contradicted under
  the wrong one.
- **Where the analogy breaks** (BACKGROUND items 1–7, each tied to a finding where the
  model showed it): the defense lever (spread ≠ rates; F-07 refinement), no political
  cost function, transparency, no partner central bank, the promise, market structure,
  **two exits** (F-14).
- **Headline 5 (closing):** the believers who broke the Bank were not the ones who
  panicked; they were the ones who took it at its word, at par, until the word ran out.

## 8. Limitations and next questions (≈ 300 words)

- Single venue (F-05); single validation event; single-entry buyer (F-09); the reference
  is a random walk with no anchor (F-04 root cause); no LP flight; no second-generation
  defender (BACKGROUND item 2); the holder's redemption spread coincidence (ADR-0021).
- Next: multi-tranche holder; OU reference; LP withdrawal; budget vs attack at depth;
  the USDe single-venue case as an oracle-module test (LITERATURE L-7).
- Related work in one paragraph: γ\* (L-4, with the venue caveat), the Renmin threshold
  result (L-5, once sourced), StableEval Arena's "agents miss sustained depegs" (L-6) as
  the reason a mechanistic, replicable simulator is worth publishing.

## 9. Reproducibility (≈ 100 words)

- `git clone`, `pip install -e .`, `make figures`; every figure's source hash in the
  manifest; the guard in CI; expected wall times on a named machine (3.5).

---

## Figure list (committed, `docs/figures/`)

One row per figure; must match `docs/figures/README.md` one-to-one, "record only" rows
with its Record only section (`tests/test_note_figures.py`). Rows marked † were added at
the Story 4.1 figure pass so the list matches the README's note set (every committed
figure not moved to the record); the dev manager may move any of them to the record.

| # | file | section | finding(s) | status |
|---|---|---|---|---|
| 1 | `validation_overlay_usdc_2023.png` | 3 | F-08 (+confirmation), F-09 | final |
| 1b | `validation_overlay_usdc_2023_tranches.png` | 3 | F-09 refinement | final |
| — | `peg_trajectory_calibrated.png` † | 4 | F-06, F-03 | final |
| 2 | `time_to_parity_ou.png` | 4 | F-03, F-06, F-11, F-04 resolution | final |
| — | `threshold_surface_ou.png` † | 4 (supporting) | F-11, F-04 resolution | final |
| — | `budget_depth.png` | 4 (supporting) | F-11 refinement | final; may drop for length |
| — | `budget_attack.png` | 4 (supporting) | F-11 second refinement | final (3.4) |
| — | `lp_flight.png` † | 4 | F-15, F-03, F-11 | final |
| 3 | `policy_comparison.png` | 5 | F-13, F-07 refinement | final (panel (b) = price paid, 4.1) |
| — | `pace_trigger.png` | 5 (supporting) | F-13 refinement | final (3.4) |
| — | `pace_ratio.png` | 5 (supporting) | F-13 refinement | final (3.4) |
| — | `peg_trajectory_baseline.png` † | 5 | F-01 | final |
| 4 | `oracle_sensitivity.png` | 6 | F-10 | final |
| 5 | `peg_trajectory_1992.png` | 7 | F-07, F-12, F-14 | final |
| 5b | `peg_trajectory_1992_no_defense.png` | 7 | counterfactual | final |
| — | `threshold_surface_par.png` | record only | F-11 | not in the note |
| — | `threshold_surface.png` | record only | F-11, F-03 | not in the note (random-walk, oracle criterion) |
| — | `time_to_parity.png` | record only | F-11 | not in the note (random-walk) |
| — | `holder_exit.png` | record only | F-14 | not in the note |

## Word budget

250 + 400 + 500 + 600 + 400 + 150 + 600 + 300 + 100 = **3,300**. Over the 3,500 cap once
captions are counted; §4 and §7 are the candidates to tighten. Cut §6 to a figure and two
sentences if needed.

## Open decisions for Tim

1. Lead with the validation (headline 1) or with the mechanism (headline 2)? Outline
   assumes validation first: it is the thing a reader can check.
2. How much 1992 narrative in §7 — the note's own retelling, or a pointer to BACKGROUND
   published alongside?
3. Named author(s) and the Corposium Research framing in the first paragraph.
4. Hero image for the README and the site page: the single-entry overlay (one parameter,
   17%) or the ladder overlay (one parameter + an assumed ladder, 4%, timing to nine
   minutes)? The note shows both in §3 either way.

## Change Log

- 2026-10-06: Outline drafted by dev manager from FINDINGS F-01…F-14 during Epic 3 (Story 3.4 in build).
- 2026-10-08: Figure list only, Story 4.1 (builder): one row per committed figure, matching `docs/figures/README.md`; `threshold_surface.png` and `time_to_parity.png` moved to record only; rows marked † added. Outline text not edited.
