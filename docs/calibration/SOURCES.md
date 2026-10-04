# Calibration Sources

Where every number in `scenarios/calibrated-baseline.yaml` and
`scenarios/calibrated-stress.yaml` comes from. Episode: the USDC depeg of 10–13 March 2023
(Silicon Valley Bank failure), with the 1992 sterling crisis as a second anchor for the
attacker ratio. Story 2.3; judgment calls are recorded in
[ADR-0018](../adr/0018-calibration-judgment-calls.md).

## Read this first: the model calibrates ratios, not absolutes

**The simulator is scale-free.** Constant-product swaps and linear redemption are both
homogeneous of degree one: multiply every balance (pool reserves, attacker capital,
defender budget, redemption reserves and capacity, arbitrageur capital) by the same factor
and every price, deviation and termination is unchanged. So the absolute size of the
pool is a free choice. **What is calibrated is the set of ratios** between attacker capital,
defender budget, redemption reserves, redemption capacity and pool depth.

We pick one absolute anchor for readability: **1,000,000 model units ↔ the USDC leg of
Curve 3pool on 10 March 2023 (≈ $234.6M)**. Every dollar figure below is converted to
model units by the same factor:

```
s = 1,000,000 / (510,000,000 × 0.46) = 1,000,000 / 234,600,000 = 0.0042625746 model units per $
```

The pool itself is **not** that Curve leg: since Story 2.4 it is a single constant-product
venue standing for aggregate USDC market depth, `D* = market_depth_multiple × 1,000,000`,
with the multiple fitted to the observed trough (Pool below, F-05, ADR-0018 amendment).

Non-balance parameters (fees, oracle settings, volatility, time) are dimensionless or in
steps and convert without `s`. One step is one Ethereum slot, 12 s.

**Status vocabulary** (last column of every table):

- `verified`: the builder opened the primary source and read the figure.
- `secondary`: figure taken from a secondary source; the primary is named; verification
  pending.
- `assumption`: policy or behavioural parameter with no empirical anchor; value stated and
  justified.

Figures marked "pre-verified by dev manager" were read by the dev manager on the stated
date and are cited as such (story 2.3 References); the builder did not re-open them.

---

## Time

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `steps.interval_seconds` | 12 | ethereum.org, "Blocks", https://ethereum.org/en/developers/docs/blocks/ (accessed 2026-10-04) | "time is divided up into twelve second units called 'slots'" | 12 s = 1 step | verified |
| `steps.max_steps` | 18000 | CNBC, 2023-03-13, https://www.cnbc.com/2023/03/13/usdc-nearly-regains-1-peg-after-circle-says-svb-deposit-is-available.html; Chainalysis (below) for the start | depeg from Fri 10 Mar ~22:00 ET to near-peg Mon 13 Mar; ≈ 60 h | 60 h × 3600 / 12 = 18,000 steps | secondary |
| `seed` | 42 | n/a | project convention | none | assumption |

## Pool

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `amm.reserve_stable` | 1833333333 | unit anchor: CoinDesk, 2023-03-10, https://www.coindesk.com/business/2023/03/10/defi-protocol-curves-500m-stablecoin-pool-hammered-as-traders-flee-usdc (pre-verified by dev manager 2026-10-03); depth: `market_depth_multiple` (next row) | 3pool TVL "more than $510 million"; USDC "more than 46%" (17:51 EST, 10 Mar 2023) | USDC leg = 510,000,000 × 0.46 = $234,600,000 ↔ 1,000,000 model units (defines `s`, secondary); pool depth D* = 1,000,000 × 1833.33 = 1,833,333,333 | assumption |
| `amm.reserve_reference` | 1833333333 | same | same | equal to `reserve_stable` so the pool starts at peg (spot 1.0) | assumption |
| `market_depth_multiple` | 1833.33 | fitted to observed trough, this story (Story 2.4, `scripts/fit_depth.py`); observed trough: Chainalysis, https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/ (pre-verified by dev manager 2026-10-03) | USDC low $0.87 → −1300 bps | smallest depth on the grid 1M…500M, extended one decade (1B, 2B, 5B), with `max_depeg_bps ≥ −1300` is 2B (−1229.3); refined between 1B and 2B, closest is 1,833,333,333 (−1327.8 bps); multiple = 1,833,333,333 / 1,000,000 = 1833.33 (≈ $430.1B per side at `s`) | assumption |
| `amm.fee_bps` | 1 | Curve 3pool contract `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7`, `fee()` via JSON-RPC `eth_call` at https://eth.drpc.org and https://1rpc.io/eth (accessed 2026-10-04); denominator from https://raw.githubusercontent.com/curvefi/curve-contract/master/contracts/pools/3pool/StableSwap3Pool.vy | `fee()` = 1000000 at blocks 16,793,344 (2023-03-09T21:34:47Z), 16,800,000 (2023-03-10T20:08:47Z) and 16,820,000 (2023-03-13T15:36:47Z); `FEE_DENOMINATOR: constant(uint256) = 10 ** 10` | 1,000,000 / 10,000,000,000 = 0.0001 = 1 bp | verified |

**Not 4 bps.** The story expected 4 bps, which is 3pool's launch fee. On-chain history read
the same way: 4,000,000 (4 bps) at block 11,000,000 (2020-10-06); 3,000,000 (3 bps) at
14,000,000 (2022-01-13); 1,000,000 (1 bp) from at least 15,500,000 (2022-09-09) through
21,000,000 (2024-10-19); 1,500,000 (1.5 bps) at `latest` on 2026-10-04. In March 2023 it was
1 bp. Curve charges the fee on the swap *output*; our AMM charges it on the *input*.
At 1 bp the difference is immaterial.

**Limitation (goes into the note).** A Curve stableswap pool is not a constant-product pool.
Near peg, stableswap (amplification A = 2000 for 3pool) is far *more* liquid than a
constant-product pool of the same TVL; far from peg it degrades towards constant-product
behaviour. We do not attempt an A-scaling: **we use the raw USDC-leg TVL as the
constant-product depth.** The constant-product pool is therefore *less* liquid than the real
pool near peg and *comparably* liquid far from peg, so **simulated depeg troughs are
conservative upper bounds on depeg depth.** The model is a **single constant-product venue standing for aggregate depth**: in March
2023 the selling was spread across Curve, Uniswap, centralised exchanges and OTC, and the
pool's depth is fitted (`market_depth_multiple`) so the model's trough matches the observed
one rather than read from any venue.

**What D* absorbs (Story 2.4).** The fitted depth is ≈ $430B per side, about 10× USDC's
total supply, so it is not a physical liquidity figure. With the attacker selling at any
price and the other sinks throughput-bound (defender budget 41.3M, redemption ≈ 10.9M over
the episode), almost all of the 179.5M attack ends up in the pool, and the trough is set
by that residual against depth, not by the first dump (a 10% first dump into D* alone moves
the price only −193 bps). The fit therefore also absorbs the ratio-1.0 attacker size
(≈ $42B of selling, against ≈ $4B net burn observed). It is one parameter fitted to one
observation; recovery timing, defender spend and redemption volume remain out-of-sample.

## Oracle

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `oracle.deviation_threshold_pct` | 0.25 | Chainlink USDC/USD, Ethereum mainnet, https://data.chain.link/feeds/ethereum/mainnet/usdc-usd (pre-verified by dev manager 2026-10-03); also `threshold: 0.25` in Chainlink's feed directory https://reference-data-directory.vercel.app/feeds-mainnet.json (accessed 2026-10-04) | deviation threshold 0.25% | percent, used as-is: 0.25 | verified |
| `oracle.heartbeat_steps` | 6900 | Chainlink feed directory (the data behind docs.chain.link's addresses page), https://reference-data-directory.vercel.app/feeds-mainnet.json (accessed 2026-10-04), entry `"name": "USDC / USD"`, `"path": "usdc-usd"`, proxy `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6` | `"heartbeat": 82800` (seconds) | 82,800 s / 12 s = 6,900 steps | verified |

**Not 86,400 s.** The story expected 86,400 s. The `usdc-usd` feed lists 82,800 s
(23 h). 86,400 s belongs to a different entry, `usdc-usd-svr` (proxy
`0xfB6471ACD42c91FF265344Ff73E88353521d099F`). data.chain.link returned HTTP 403 to an
automated fetch on 2026-10-04, so the directory JSON is the primary read. These are
today's trigger parameters; the feed's March 2023 settings were not checked.

## Redemption

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `redemption.peg_price` | 1.0 | Circle, "$3.3 Billion of USDC Reserve Risk Removed, Dollar De-peg Closes", 2023-03-13, https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes (accessed 2026-10-04) | "USDC remains redeemable 1:1 with the U.S. Dollar." | 1 USDC → 1.0 reference | verified |
| `redemption.spread_bps` | 0 | same Circle post (no fee mentioned); The Block, 2024-10-29, https://www.theblock.co/post/323626/the-scoop-circle-raises-fees-as-fed-cuts (accessed 2026-10-04); current schedule: Circle Help Center, https://help.circle.com/s/article/USDC-redemption-structure (JS-rendered; text read via search index 2026-10-04) | March 2023: 1:1, no fee stated. Fees appear in 2024 ("start at 0.03% … can reach 0.1% for redemptions over $15 million"). Current (from 2026-03-15): Standard tier 5 bps on net redemption above $2M/day free; Institutional 5 bps on gross; overage +2 bps ($40M–$100M), +5 bps (> $100M) | 0 bps for the March 2023 episode | secondary |
| `redemption.capacity_per_step` | 605.79 | DefiLlama stablecoins API, https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2 (accessed 2026-10-04), committed as `data/usdc_supply_defillama_2023-03-01_2023-03-20.csv`; primary: Circle transparency reports / per-chain on-chain `totalSupply` | total USDC supply 42,200,261,242 on 2023-03-11 and 38,107,230,325 on 2023-03-15 (00:00 UTC) | net burn over 11–14 Mar = 42,200,261,242 − 38,107,230,325 = 4,093,030,917 $ in 4 days = 1,023,257,729.25 $/day; ÷ 7,200 steps/day = 142,119.13 $/step; × s = 605.79 per step | secondary |
| `redemption.reserves` | 138107417 | 21Shares newsletter issue 193, https://www.21shares.com/en-eu/insights/newsletter-issue-193 (pre-verified by dev manager 2026-10-03) | reserves: T-bills $32.4B (77%), cash $9.7B (23%) | the redemption facility holds the T-bill share: 32,400,000,000 × s = 138,107,416.88 → 138,107,417 | secondary |

**Capacity is the binding constraint, not reserves.** At 605.79 per step, the redemption
facility can pay at most 18,000 × 605.79 ≈ 10.9M within the 60-hour window: 7.9% of
its 138.1M reserves. In the calibrated scenarios, `reserves_exhausted` can't fire within
`max_steps`. This matches March 2023: Circle's reserves were never close to exhausted; the
constraint was that redemptions ran through banks that were shut for the weekend
("Liquidity operations for USDC will resume at banking open on Monday", per Circle
2023-03-12/13 as reported by Ledger Insights, https://www.ledgerinsights.com/usdc-stablecoin-redeemable-peg-bail-out-svb/, secondary). The observed
net burn is a realised throughput, not a hard cap, and it includes Monday's catch-up.

**Why T-bills = redemption reserves and cash = defender budget.** See Defender and
ADR-0018.

## Environment

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `environment.base_price` | 1.0 | definition | reference asset is the US dollar | 1.0 | verified |
| `environment.volatility_per_step` (calibrated-baseline) | 3.086e-05 | Bitstamp USDC/USD hourly candles, https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start=1677456000&end=1677888000 (accessed 2026-10-04), committed as `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv` | 120 hourly closes, 2023-02-27 00:00Z → 2023-03-03 23:00Z; sd of 119 hourly log returns = 0.0005345425225988582 | sd_step = sd_hourly / sqrt(300) = 0.0005345425225988582 / 17.3205 = 3.0862e-05 → 3.086e-05 | verified |
| `environment.volatility_per_step` (calibrated-stress) | 0.0007561 | same endpoint, `start=1678406400&end=1678752000`, committed as `data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv` | 96 hourly closes, 2023-03-10 00:00Z → 2023-03-13 23:00Z; sd of 95 hourly log returns = 0.01309650361013093; lowest close 0.86267 | sd_step = 0.01309650361013093 / 17.3205 = 7.5613e-04 → 0.0007561 | verified |
| `environment.shocks` | [] | n/a | no scheduled shocks; the attack is the shock | none | assumption |

Stress / calm = 24.5×, not the ~100× the story guessed. Bitstamp's thin book inflates the
calm figure (13 zero-volume hours, isolated prints down to 0.99636), so the true ratio is
probably larger. **Limitation:** this is USDC's *own* realised volatility, applied in the
model to the *reference* price (the dollar the stable should track). During the stress
window most of that volatility *is* the depeg, so the stress scenario double-counts: the
attack drives the AMM price and noise moves the reference. We use it as the AC asks, as an
upper bound on environmental noise. CoinGecko (aggregated, more liquid) needs a paid key
for 2023 data; Coinbase has no USDC-USD book; Kraken serves only its last 720 candles
(see `data/README.md`).

## Attacker

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `agents[type=attacker].capital` | 179454391 | design ratio (ADR-0017, ADR-0018), anchored to: Chainalysis, https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/ (pre-verified by dev manager 2026-10-03); BACKGROUND.md §5 for 1992 | March 2023: CEX USDC outflows peaked at $1.2B/hour; $3.3B at SVB = 8% of reserves. 1992: Quantum short ≈ $10B vs ≈ £27B gross reserves spent (BACKGROUND.md, verification pending) | capital = 1.0 × (budget + reserves) = 1.0 × (41,346,974 + 138,107,417) = 179,454,391 | secondary |
| `agents[type=attacker].start_step` | 50 | unchanged from `soros-baseline` | none | 50 steps = 10 min of calm before the attack, < `for_steps` so the pre-attack calm can't count as recovery (ADR-0010) | assumption |
| `agents[type=attacker].pace` | 0.1 | unchanged from `soros-baseline` | none | 10% of remaining stable per step (12 s) | assumption |
| `agents[type=attacker].stop_below_price` | null | unchanged from `soros-baseline` | none | the attacker never stops selling | assumption |

**The ratio 1.0 is a design choice, not a measurement.** It puts the attacker exactly at
`budget + reserves`, where ADR-0017 found the outcome boundary for capital/depth ≤ 2.4.
Neither historical anchor is a measurement of that ratio. In 1992 Quantum alone was
≈ $10B against ≈ £27B of gross intervention (with many other sellers). In March 2023 the
peak hourly CEX outflow ($1.2B) was ≈ 2.9% of Circle's $42.1B reserves, and the stranded
$3.3B was 8%. **Against the single Curve leg the ratio put the attacker at 179× pool
depth** (Story 2.3, F-05); against the fitted aggregate depth D* it is 0.098× (Story 2.4).

## Defender

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `agents[type=defender].budget` | 41346974 | 21Shares newsletter issue 193 (pre-verified by dev manager 2026-10-03) | cash $9.7B (23% of reserves) | cash is what can be deployed immediately: 9,700,000,000 × s = 41,346,973.57 → 41,346,974; budget : reserves = 9.7 : 32.4 = 23.0 : 77.0 | secondary |
| `agents[type=defender].threshold_pct` | 1.0 | no public source | none | unchanged from `soros-baseline`: defend below −1% | assumption |
| `agents[type=defender].spend_pace` | 0.2 | no public source | none | unchanged: 20% of remaining budget per step at most | assumption |
| `agents[type=defender].spread_adjust_bps` | 0 | no public source | Circle did not change redemption pricing in March 2023 (Circle post above) | no spread lever | assumption |
| `agents[type=defender].max_spend` | null | no public source | none | whole budget available | assumption |

## Arbitrageur

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `agents[type=arbitrageur].capital` | 200000 | no public source | none | unchanged from `soros-baseline`: 0.2 × the 1,000,000 unit anchor (≈ $46.9M at `s`; 0.00011 × D*) | assumption |
| `agents[type=arbitrageur].min_profit_bps` | 20 | no public source | none | unchanged from `soros-baseline` | assumption |
| `agents[type=arbitrageur].latency_steps` | 1 | no public source | none | one slot (12 s) reaction time | assumption |

## Termination

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `termination.peg_recovered.tolerance` | 0.0031 | ADR-0013 rule applied to the calibrated fee | arb band = `fee_bps` + `min_profit_bps` = 1 + 20 = 21 bps | band + 10 bps margin (ADR-0013's baseline convention) = 31 bps = 0.0031 | verified |
| `termination.peg_recovered.for_steps` | 6900 | Chainlink heartbeat (Oracle above) | 82,800 s | `for_steps >= heartbeat_steps`: recovery must be visible to the oracle at least once → 6,900 | verified |
| `termination.reserves_exhausted` | true | project convention | none | keep the exhaustion condition armed | assumption |
| `termination.max_steps` | true | ADR-0006 | none | mandatory safety cap | verified |

## Run settings (not calibrated)

| parameter | value used | source (URL, accessed) | raw figure | conversion | status |
|---|---|---|---|---|---|
| `metrics.record_every` | 1 | project convention | none | one row per step | assumption |
| `metrics.trace_decisions` | false | project convention | none | 18,000-step runs; trace off to keep output small | assumption |
| `metrics.checkpoint_every` | 6900 | project convention | none | one checkpoint per heartbeat | assumption |

---

## Ratios at a glance (the calibrated quantities)

| ratio | value | from |
|---|---|---|
| pool depth / unit anchor (`market_depth_multiple`) | 1833.33 | fitted to −1300 bps trough (Story 2.4) |
| redemption reserves / pool depth | 0.0753 | 138.1M / 1,833.3M (was 138.1 against the Curve leg) |
| defender budget / pool depth | 0.0226 | 41.3M / 1,833.3M (was 41.3) |
| budget : reserves | 23.0 : 77.0 | 21Shares |
| attacker / (budget + reserves) | 1.0 | design (ADR-0017) |
| attacker / pool depth | 0.0979 | consequence of the above (was 179.5) |
| redemption capacity per step / pool depth | 3.3e-07 | 605.79 / 1,833.3M (was 0.000606) |
| redemption capacity × max_steps / reserves | 0.079 | 10.9M / 138.1M |
| arbitrageur / pool depth | 0.00011 | 200,000 / 1,833.3M, assumption (was 0.2) |
