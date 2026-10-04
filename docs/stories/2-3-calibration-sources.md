# Story 2.3: Calibration Sources

Status: in-progress

## Story

As a **researcher**,
I want every baseline parameter traced to a public source,
so that a reader can check where the numbers came from.

## Acceptance Criteria

1. `docs/calibration/SOURCES.md` exists with one section per parameter group (pool, fee, oracle, redemption, environment, attacker, defender, arbitrageur, termination); each parameter row gives: **value used**, **source** (URL, accessed date), **raw figure as the source states it**, **conversion to simulator units** (shown as arithmetic), and a **status** of `verified` (primary source read by the builder) or `secondary` (figure taken from a secondary source; primary named)
2. Every parameter in `scenarios/calibrated-baseline.yaml` has a row; no row is unmarked
3. Pool: a constant-product pool at depth `D` approximates a Curve stableswap pool of TVL `T` only near peg; SOURCES.md states the TVL used (Curve 3pool, March 10 2023: **$510M**, CoinDesk), the share attributable to the USDC leg (**~46%**), the chosen `D` and the reasoning (Dev Notes), and the limitation that constant-product overstates slippage far from peg (so simulated troughs are *conservative upper bounds* on depeg depth); `fee_bps` from Curve 3pool's fee (**4 bps**; builder verifies on curve.fi or the pool contract)
4. Oracle: Chainlink USDC/USD Ethereum mainnet feed — deviation threshold **0.25%** (data.chain.link, verified by dev manager 2026-10-03); heartbeat: builder verifies the exact value on data.chain.link or docs.chain.link addresses page (expected 86400 s) and converts: `heartbeat_steps = heartbeat_s / 12`; `deviation_threshold_pct = 0.25`
5. Redemption: `peg_price 1.0`; `spread_bps` from Circle's published redemption fee schedule (builder finds the current schedule; if redemption is fee-free up to a daily threshold, use `0` and note the threshold); `capacity_per_step` from observed USDC net burn over March 11–14 2023 (builder sources from Circle's transparency page, Etherscan supply history, or a DefiLlama/Dune dashboard; cite which) converted as `burn_per_day / 7200 steps`; `reserves` as a **ratio** to pool depth, not an absolute (Dev Notes)
6. Environment: `volatility_per_step` from the realised per-12-second log-return sd of USDC/USD during a *calm* week (e.g. Feb 27–Mar 3 2023) **and** the March 10–13 stress window, both stated; the baseline uses the calm figure and `scenarios/calibrated-stress.yaml` uses the stress figure; source: hourly or minute candles from CoinGecko/Coinbase (builder documents the retrieval command in `data/README.md`); conversion: `sd_step = sd_hourly / sqrt(300)`
7. Attacker: two anchors stated in SOURCES.md — (a) March 2023: CEX hourly outflow peak **$1.2B/hour** (Chainalysis) and the $3.3B SVB exposure (**8% of reserves**, Circle); (b) 1992: Quantum's ~$10B short vs the gross intervention figure in `docs/BACKGROUND.md` (status `secondary` until BACKGROUND's verification items close); the calibrated attacker `capital` is set as a **ratio to (defender budget + reserves)** of **1.0** so the baseline sits on the ADR-0017 boundary, with `pace` and `start_step` unchanged and justified
8. Defender: `budget` as a ratio to reserves matching Circle's position (cash share of reserves ≈ **23%** vs T-bills **77%**, 21Shares/Circle attestations): cash is what can be deployed immediately → `budget : reserves ≈ 23 : 77`; `threshold_pct`, `spend_pace` stay as baseline with a note that no public source pins them (status `assumption`, a third allowed status for policy parameters with no empirical anchor)
9. Termination: `peg_recovered.tolerance` set per ADR-0013 from the calibrated `fee_bps + min_profit_bps`; `for_steps` set so that it spans at least one Chainlink heartbeat (`for_steps >= heartbeat_steps`), with the reasoning that recovery must be visible to the oracle at least once; `steps.max_steps` long enough for the USDC episode (March 10 22:00 ET to March 13 ≈ 60 h → **18,000 steps**)
10. `scenarios/calibrated-baseline.yaml` and `scenarios/calibrated-stress.yaml` validate, run, and terminate by something other than `max_steps`; both have header comments pointing at SOURCES.md sections; `terminated_by`, `max_depeg_bps`, `steps_to_sustained_recovery` for each recorded in Completion Notes
11. `data/README.md` documents every dataset retrieval (URL, command or UI steps, date, checksum of the committed file); any raw data committed under `data/` is ≤ 1 MB per file
12. A `Proposed` ADR recording the calibration choices that are judgment calls (the `D` chosen for the pool, the reserves ratio, the attacker ratio), so they can be revisited without re-reading SOURCES.md
13. `pytest` and `ruff check .` pass; both calibrated scenarios run in tests with `max_steps` overridden to ≤ 500

## Tasks / Subtasks

- [ ] Gather and verify (AC: 1–9)
  - [ ] Chainlink heartbeat (primary: data.chain.link USDC/USD or docs addresses page)
  - [ ] Curve 3pool fee (primary: curve.fi pool page or contract `fee()`)
  - [ ] Circle redemption fee schedule (primary: circle.com docs)
  - [ ] USDC net burn March 11–14 2023 (name the dashboard; screenshot or CSV under `data/` if ≤ 1 MB)
  - [ ] USDC/USD candles, calm week and stress window; compute both sds; commit the CSVs
  - [ ] Write SOURCES.md with the five-column rows and status marks

- [ ] Scenarios (AC: 9, 10)
  - [ ] `scenarios/calibrated-baseline.yaml`, `scenarios/calibrated-stress.yaml`
  - [ ] Run both; record outcomes; if either ends by `max_steps`, revisit `for_steps`/tolerance first (LOW-2 from 2.2), then attacker ratio, and record what you changed and why

- [ ] Data README and ADR (AC: 11, 12)
  - [ ] `data/README.md`; `Proposed` ADR for the judgment calls

- [ ] Tests, lint, close out (AC: 13)
  - [ ] `tests/test_calibrated_scenarios.py`: both load, hash, run short
  - [ ] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [ ] Dev Agent Record, Change Log, `Status: review`
  - [ ] Commit `story 2.3: calibration sources`, push to `main`

## Dev Notes

### Learnings from Previous Story

**From Story 2.2 (Status: done)**

- ADR-0016/0017: outcome is set by `capital ≷ (stable the defender can absorb + reserves)`;
  depth sets the absorption price. The calibrated baseline should sit **on** that boundary
  (ratio ≈ 1.0) so the headline chart has its transition in the middle of the frame.
- 5 bps/step noise barely moved outcomes but pushed 6–25% of recovering runs to
  `max_steps` by knocking them out of the recovery band. Calibrate `volatility_per_step`
  and `peg_recovered.for_steps` together.
- The MC machinery is fast; don't shrink grids for runtime.

[Source: docs/stories/2-2-monte-carlo.md#Senior-Developer-Review, docs/adr/0017]

### Why ratios, not absolutes

The model is scale-free: doubling every balance leaves prices and outcomes unchanged
(constant product and linear redemption are both homogeneous). So the *absolute* pool
depth is a free choice; what matters is the **ratios** between attacker capital, defender
budget, reserves and pool depth. SOURCES.md should make the ratios the calibrated
quantities and pick one absolute anchor (pool depth) for readability. State this
explicitly in SOURCES.md's preamble; it is the single most useful thing a reader can know
about the model.

Suggested anchor: `D = 250,000,000` per side? No — keep numbers readable. Use
**`D = 1,000,000`** per side as before and scale everything else to Curve-3pool-March-2023
ratios. Record the real TVL it stands for.

### Pool depth reasoning (AC 3)

Curve 3pool, March 10 2023, 17:51 EST: TVL > $510M; USDC > 46%, DAI > 46%, USDT < 7%
(CoinDesk). The USDC leg ≈ $235M. For a two-asset constant-product approximation near
peg, a stableswap pool with amplification A behaves like a constant-product pool roughly
`A×` deeper for small deviations (A = 2000 for 3pool), but that approximation collapses
beyond ~1–2% deviation, which is exactly where depegs live. **Decision for the builder:**
do not attempt an A-scaling; use the raw USDC-leg TVL as the constant-product depth
equivalent, and state clearly that the constant-product pool is *less* liquid than the
real stableswap pool near peg and *comparably* liquid far from peg. Simulated troughs are
therefore upper bounds. This is an honest limitation for the note, not a defect.

### Chainlink (AC 4)

Verified by dev manager 2026-10-03 at https://data.chain.link/feeds/ethereum/mainnet/usdc-usd:
deviation threshold **0.25%**. Heartbeat not visible in the fetched excerpt; builder reads it
from the same page (the "Trigger parameters" panel) or from
https://docs.chain.link/data-feeds/price-feeds/addresses?network=ethereum (search USDC).
Expected 86400 s → `heartbeat_steps = 7200`. If the page shows a different value, use it
and note the date.

### Environment volatility (AC 6)

USDC/USD during a calm week moves a few bps a day. Per-12s sd will be tiny (order 1e-5).
That's the point: in the calibrated baseline, noise is negligible and the outcome is the
capital accounting (2.2 LOW-1). The stress scenario uses the March 10–13 realised sd,
which will be 100× larger. Report both numbers; if the stress-window sd makes
`peg_recovered` unreachable at the ADR-0013 tolerance, that's a finding for the note
("under realised stress volatility, the recovery criterion itself must widen").

### Attacker ratio (AC 7)

With `capital / (budget + reserves) = 1.0` the baseline sits on the ADR-0017 boundary.
The chart 2.6 draws will show both sides. State in SOURCES.md that this is a *design*
choice anchored to the two historical ratios (Quantum/BoE and March-2023 outflow/reserves),
not a measurement.

### Status vocabulary

- `verified` — builder opened the primary source and read the figure
- `secondary` — figure from a secondary source; primary named; verification pending
- `assumption` — policy parameter with no empirical anchor; value stated and justified

### Data retrieval

Prefer CoinGecko's public API for candles (no key for hourly data at this age) or
Coinbase's product candles endpoint. Document the exact URL. Commit the CSV. If a source
needs a key, note that and commit the CSV with a retrieval date instead of a command.

### References

- [Source: docs/epics.md#Story-2.3]
- [Source: docs/adr/0013, 0016, 0017]
- [Source: docs/BACKGROUND.md#5-The-cost] — 1992 ratio anchor and its verification status
- Chainlink USDC/USD feed: https://data.chain.link/feeds/ethereum/mainnet/usdc-usd (deviation 0.25%, accessed 2026-10-03)
- CoinDesk, 2023-03-10, "Curve's $500M stablecoin pool hammered": https://www.coindesk.com/business/2023/03/10/defi-protocol-curves-500m-stablecoin-pool-hammered-as-traders-flee-usdc
- Chainalysis, March 2023 USDC/SVB: https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/ ($0.87 at 2am Mar 11; $1.2B/h CEX outflow peak; $3.3B SVB = 8%)
- 21Shares special report on USDC: https://www.21shares.com/en-eu/insights/newsletter-issue-193 (reserves 77% T-bills $32.4B / 23% cash $9.7B; repeg Mar 13)

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-3-calibration-sources.context.xml)

### Agent Model Used

_(fill in)_

### Debug Log References

_(real command output; both calibrated runs' three CLI lines)_

### Completion Notes List

_(include: the two volatility sds, both scenarios' outcomes, which figures stayed `secondary`, the ADR number)_

### File List

**Created:**

**Modified:**

## Change Log

- 2026-10-03: Story drafted by dev manager after Story 2.2 review; dev manager pre-verified the Chainlink deviation threshold and the Curve/Chainalysis/21Shares figures cited above
