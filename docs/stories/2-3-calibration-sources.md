# Story 2.3: Calibration Sources

Status: review

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

- [x] Gather and verify (AC: 1–9)
  - [x] Chainlink heartbeat (primary: data.chain.link USDC/USD or docs addresses page)
  - [x] Curve 3pool fee (primary: curve.fi pool page or contract `fee()`)
  - [x] Circle redemption fee schedule (primary: circle.com docs)
  - [x] USDC net burn March 11–14 2023 (name the dashboard; screenshot or CSV under `data/` if ≤ 1 MB)
  - [x] USDC/USD candles, calm week and stress window; compute both sds; commit the CSVs
  - [x] Write SOURCES.md with the five-column rows and status marks

- [x] Scenarios (AC: 9, 10)
  - [x] `scenarios/calibrated-baseline.yaml`, `scenarios/calibrated-stress.yaml`
  - [x] Run both; record outcomes; if either ends by `max_steps`, revisit `for_steps`/tolerance first (LOW-2 from 2.2), then attacker ratio, and record what you changed and why

- [x] Data README and ADR (AC: 11, 12)
  - [x] `data/README.md`; `Proposed` ADR for the judgment calls

- [x] Tests, lint, close out (AC: 13)
  - [x] `tests/test_calibrated_scenarios.py`: both load, hash, run short
  - [x] `pytest`, `ruff check .`, `ruff format --check .` with `exit=N`
  - [x] Dev Agent Record, Change Log, `Status: review`
  - [x] Commit `story 2.3: calibration sources`, push to `main`

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

Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code

### Debug Log References

```
$ pytest; echo exit=$?
417 passed in 4.01s
exit=0

$ ruff check .; echo exit=$?
All checks passed!
exit=0

$ ruff format --check .; echo exit=$?
74 files already formatted
exit=0

$ python run.py scenarios/calibrated-baseline.yaml; echo exit=$?
depeg-sim: scenario=calibrated-baseline seed=42 hash=e3252a1ffa5b
run: steps=7051 terminated_by=peg_recovered max_depeg_bps=-9972.1 reserves_exhausted=False
wrote: output/calibrated-baseline-42-e3252a1f
exit=0

$ python run.py scenarios/calibrated-stress.yaml; echo exit=$?
depeg-sim: scenario=calibrated-stress seed=42 hash=546d28330e87
run: steps=7067 terminated_by=peg_recovered max_depeg_bps=-9972.1 reserves_exhausted=False
wrote: output/calibrated-stress-42-546d2833
exit=0
```

CI on push of `b67fe61`:

```
completed	success	story 2.3: calibration sources	ci	main	push	37208088626	1m21s	2026-10-04T14:07:21Z
```

Verification reads (2026-10-04):

```
# Chainlink feed directory (reference-data-directory.vercel.app/feeds-mainnet.json), "USDC / USD":
path usdc-usd      proxy 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6  heartbeat 82800  threshold 0.25
path usdc-usd-svr  proxy 0xfB6471ACD42c91FF265344Ff73E88353521d099F  heartbeat 86400  threshold 0.25

# Curve 3pool fee(), eth_call (eth.drpc.org; 1rpc.io agrees at 16,793,344); FEE_DENOMINATOR 10**10
11000000 2020-10-06T04:17:04+00:00 4000000 4 bps
14000000 2022-01-13T22:59:55+00:00 3000000 3 bps
15500000 2022-09-09T01:39:42+00:00 1000000 1 bps
16793344 2023-03-09T21:34:47+00:00 1000000 1 bps
16800000 2023-03-10T20:08:47+00:00 1000000 1 bps
16820000 2023-03-13T15:36:47+00:00 1000000 1 bps
latest (publicnode)                0x16e360 = 1500000 = 1.5 bps

# Bitstamp USDC/USD hourly, log-return sd (data/*.csv)
calm   2023-02-27..03-03  rows 120  sd_hourly=0.0005345425225988582  sd_step=3.086182693157524e-05
stress 2023-03-10..03-13  rows 96   sd_hourly=0.01309650361013093   sd_step=0.0007561269884751998

# DefiLlama USDC supply: 2023-03-11 42,200,261,242 -> 2023-03-15 38,107,230,325
net burn 4,093,030,917 / 4 days = 1,023,257,729.25 /day -> 142,119.13 $/step -> 605.79 model/step
```

32-seed check of each committed scenario (seeds 1..32, `python -m depeg_sim.sweep … --mc`):

```
calibrated-baseline  {'peg_recovered': 31, 'max_steps': 1}   sustained median 101  range 101..7342
calibrated-stress    {'max_steps': 27, 'peg_recovered': 5}   sustained median 3359 range 122..7012
```

Attacker-ratio probe (calm, seed 42, scratch sweep over `agents[type=attacker].capital`):

```
ratio  terminated_by   steps_run  max_depeg_bps  defender_spent  redemption_paid  sustained
 1.0   peg_recovered   7051       -9972.1        16,119,549.5    4,238,712.6      101
 2.0   peg_recovered   7061       -9992.7        19,325,500.8    4,244,770.5      111
 4.0   peg_recovered   7066       -9998.1        22,574,303.0    4,247,799.5      116
 8.0   peg_recovered   7076       -9999.5        25,845,429.7    4,253,857.4      126
16.0   peg_recovered   7077       -9999.9        29,132,433.3    4,254,463.2      127
```

405 → 417 tests (+12, `tests/test_calibrated_scenarios.py`).

### Completion Notes List

- **Outcomes (seed 42):**

  | scenario | terminated_by | steps_run | max_depeg_bps | steps_to_sustained_recovery |
  |---|---|---|---|---|
  | calibrated-baseline | peg_recovered | 7051 | −9972.1 | 101 |
  | calibrated-stress | peg_recovered | 7067 | −9972.1 | 117 |

  Neither needed the fix order (for_steps/tolerance → attacker ratio). Both terminate by
  `peg_recovered` as committed. But see the stress finding: that's seed luck.
- **Volatility:** calm (27 Feb – 3 Mar 2023) **sd_step = 3.086e-05**; stress (10–13 Mar
  2023) **sd_step = 7.561e-04**. That's 24.5×, not the ~100× guessed. Bitstamp's thin book
  inflates the calm figure, and the stress figure is mostly the depeg itself, which the
  model applies to the *reference* price (a double count, stated in SOURCES.md).
- **Finding (for the dev manager to decide on a FINDINGS entry): under realised stress
  volatility the recovery criterion is mostly unreachable.** At the ADR-0013 tolerance
  (31 bps) and `for_steps` = one heartbeat (6,900), 5 of 32 seeds recover. The rest run to
  `max_steps` (calm: 31 of 32). Over one `for_steps` window the reference wanders
  σ√6900 ≈ 7.56e-4 × 83 ≈ 6.3%, twenty times the band, and AMM deviation is measured
  against the fixed peg. "Under realised stress volatility, the recovery criterion itself
  must widen", or deviation should be measured against the reference, not the peg. Seed
  42 happens to be a recovering seed. The committed stress scenario meets AC 10, but the
  result isn't robust, and the scenario header says so.
- **Finding: the calibrated attacker isn't on the ADR-0017 boundary.** With sourced
  ratios the attacker is 179× pool depth (ADR-0017 measured capital/depth 0.1–2.4). The
  first dump crashes spot to 0.0028. The defender buys the dump back almost for free
  (F-03 at its limit), spends 16.1M of 41.3M, and the peg recovers. Raising the attacker
  to 16× (budget + reserves) still recovers. A never-stopping attacker at this scale
  can't win. The boundary at calibrated scale needs a `stop_below_price` assumption (a
  rational seller doesn't dump at 0.003) or multi-venue depth. Proposed in ADR-0018 as a
  consequence for 2.5/2.6, not changed here: the story fixes pace/start_step and sets no
  stopping rule.
- **Finding: redemption is throughput-bound.** At the observed net burn (605.79/step =
  $1.02B/day), the facility pays at most 10.9M (7.9% of reserves) in 18,000 steps, so
  `reserves_exhausted` can't fire. That matches March 2023: reserves were ample; the
  banking rails were shut.
- **Two expected figures were wrong in the story; I used the verified values.**
  - Curve 3pool fee in March 2023 was **1 bp**, read on-chain at three blocks spanning
    9–13 March 2023. 4 bps is the 2020 launch fee; today it is 1.5 bps.
  - Chainlink USDC/USD (`usdc-usd`) heartbeat is **82,800 s** → `heartbeat_steps =
    6900` (not 86,400 / 7200). 86,400 s belongs to the separate `usdc-usd-svr` feed.
    data.chain.link returned 403 to automated fetches. I read Chainlink's own feed
    directory JSON, which docs.chain.link renders. These are today's parameters; the March
    2023 values were not checked.
  - Consequences: arb band = 1 + 20 = 21 bps, tolerance 0.0031 (band + 10 bps, ADR-0013);
    `for_steps` 6900.
- **Rows still `secondary` (8):** `steps.max_steps` (episode length from press),
  `amm.reserve_stable` / `amm.reserve_reference` (CoinDesk TVL/share, pre-verified by the
  dev manager), `redemption.spread_bps` (March 2023 fee-free inferred from Circle's
  1:1 statement plus later press; the current schedule page is JS-rendered and was read via
  the search index), `redemption.capacity_per_step` (DefiLlama aggregate; primary =
  Circle/on-chain supply), `redemption.reserves` and `agents[type=defender].budget`
  (21Shares, pre-verified), `agents[type=attacker].capital` (design ratio; 1992 anchors
  pending BACKGROUND verification). Policy/behaviour rows are `assumption`. Everything
  else is `verified`.
- **Proposed ADR-0018** (pool anchor, reserves split, attacker ratio, plus the three
  calibrated-run observations and their consequences for 2.5/2.6).
- **Data:** three CSVs under `data/` (7.5–9.1 KB each), all produced by
  `python data/fetch.py` (stdlib, no keys). `data/README.md` gives URL, window, rows,
  columns and sha256 for each, plus the sources tried and rejected (CoinGecko needs a paid
  key for 2023; Coinbase has no USDC-USD book; Kraken serves only the last 720 candles).
  `data/fetch.py` is a retrieval script, not simulator source.
- **Tests (`tests/test_calibrated_scenarios.py`, 12):** both scenarios load and follow
  ADR-0013 / heartbeat / ADR-0010 rules; attacker = budget + reserves; content hashes
  pinned (a calibration change must update the test); stress differs from baseline only
  in name and volatility; 500-step runs complete; headers point at every SOURCES.md
  section; every SOURCES.md parameter row has six non-empty cells and a status in the
  vocabulary; every YAML leaf parameter has a row; data files < 1 MB, named and
  checksummed in `data/README.md`.
- `metrics.checkpoint_every: 6900` (one per heartbeat) and `trace_decisions: false` for
  the 18,000-step scenarios; listed as `assumption` rows.
- No schema or source changes; no Blockers.

### File List

**Created:**

- `docs/calibration/SOURCES.md` (replaces `docs/calibration/.gitkeep`)
- `scenarios/calibrated-baseline.yaml`, `scenarios/calibrated-stress.yaml`
- `data/README.md`, `data/fetch.py`
- `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv`,
  `data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv`,
  `data/usdc_supply_defillama_2023-03-01_2023-03-20.csv`
- `docs/adr/0018-calibration-judgment-calls.md` (Proposed)
- `tests/test_calibrated_scenarios.py`

**Modified:**

- `docs/stories/2-3-calibration-sources.md`

**Deleted:**

- `docs/calibration/.gitkeep`

## Change Log

- 2026-10-03: Story drafted by dev manager after Story 2.2 review; dev manager pre-verified the Chainlink deviation threshold and the Curve/Chainalysis/21Shares figures cited above
- 2026-10-04: Implemented by Claude Code (Opus 5.5); 417 tests pass; both calibrated scenarios end peg_recovered (stress only in 5/32 seeds); ADR-0018 proposed; status → review
