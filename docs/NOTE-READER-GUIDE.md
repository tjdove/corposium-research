# A reader's guide to the research note

**Companion to *What breaks a peg* ([NOTE.md](NOTE.md), draft v2.0)**

This guide is for readers who are curious but aren't finance or crypto specialists. It
does not change, replace or reinterpret anything in the note. It explains the words the
note uses, in the order the note uses them, so you can read the note with this open
alongside it. Where the note gives a number, this guide uses that same number as its
example.

Sections are added as we go. **Section 2, "The model in one page," is covered first.**

---

## Before you start: five words that come up everywhere

**Stablecoin.** A digital token that is meant to be worth exactly one US dollar at all
times. USDC, the one studied in the note, is issued by a company called Circle, which
holds real-world assets (mostly short-term US government debt, called T-bills) to back
every token.

**Peg.** The promise that the token's price stays fixed at $1.00. A "depeg" is when the
market price slips away from that promise, for example when USDC traded at $0.87 in
March 2023.

**Par.** Face value: the price the token is *supposed* to be worth. For a dollar
stablecoin, par is $1.00. "Below par" means trading for less than a dollar; "back at
par" means the price has returned to $1.00.

**Basis points (bps).** A way of measuring small price differences. One basis point is
one hundredth of one percent (0.01%). So 100 bps = 1%, and for a $1.00 token, 1 bp is
one hundredth of a cent. The note's −1,373 bps means 13.73% below par, or about $0.86.

**The model / the simulator.** A computer program that imitates a stablecoin market,
with simple rules for each participant, so we can watch what happens to the price under
pressure and repeat the experiment as many times as we like.

---

## Section 2, term by term

### The opening paragraph

**Discrete-step model.** The simulation moves forward in fixed ticks of the clock rather
than continuously, like frames in a film. Each tick is called a **step**.

**12 seconds per step.** Each step represents 12 seconds of real time, roughly the rhythm
at which the Ethereum blockchain adds a new block of transactions. A 60-hour weekend is
18,000 steps.

**Nine ordered phases per step.** Inside each 12-second step, things happen in a fixed
sequence of nine stages (for instance, prices are published before participants react
to them). Because the order never changes, the same inputs always lead to the same
result.

**Versioned.** The rules and their order carry a version label, so any result can be tied
to the exact rules that produced it.

**Seed.** Some parts of the simulation involve randomness (the background price wobbling,
for example). A seed is the starting number for that randomness. Same seed, same
"random" sequence.

**Scenario file.** A settings file that lists every input for one experiment: how much
money each participant has, how deep the market is, and so on.

**Byte-identical output.** Run the same seed and scenario file twice, on any machine, and
the results match down to the last digit. That is what lets anyone check the note's
numbers for themselves.

### Venue

**Venue.** The marketplace where the stablecoin is bought and sold and where its price is
set. In the real world there are many venues (exchanges and on-chain trading pools). In
the model, a single pool plays the part of all of them.

**Pool / automated market maker.** Instead of buyers and sellers placing orders with each
other, an on-chain pool holds a stock of two assets, and anyone can trade against it. A
formula, not a person, decides the price.

**Constant-product pool.** A pool whose formula keeps the two stocks multiplied together
at a constant value. In plain terms: the more stablecoins people sell into the pool, the
fewer dollars each extra stablecoin fetches. Small sales barely move the price; large
sales move it sharply.

**Reference asset.** The thing the stablecoin trades against in the pool, standing in for
the US dollar.

**Fee on input.** A small charge the pool takes from whatever a trader puts in.

**Spot price.** The price the pool is offering right now, for the next small trade. The
note treats this as *the* price of the stablecoin.

**Curve's 3pool and the StableSwap invariant.** Curve is a real on-chain trading venue,
and the 3pool was one of the largest pools for dollar stablecoins in 2023. Its formula
("StableSwap") is designed to keep prices flatter near $1.00 than a constant-product pool
does. The model uses the simpler formula and adjusts the pool's size to compensate.

**Pool depth.** How much is in the pool. A deep pool can absorb large sales without much
price movement; a shallow one moves a lot. The note's fitted depth is written **D\***.

**"A calibration, not a measurement."** The pool depth wasn't read off a real-world
record; it was set so the model's results line up with what actually happened. The note
is being honest that it was tuned, not observed.

### Oracle

**Oracle.** A service that brings outside information onto the blockchain. Here it
publishes the reference price (what a dollar is "really" worth), which other participants
use to decide whether the pool's price is out of line.

**Reference price.** The outside "true value" the oracle reports, which in calm times
sits at par.

**Deviation threshold.** The oracle publishes a new price whenever the true value moves
by more than a set amount. In the note's calibration, that is 0.25%.

**Heartbeat.** The oracle also publishes on a timer even if nothing has moved, so the
price never goes stale. In the calibration, that is every 82,800 seconds (23 hours).

**Chainlink.** The real-world oracle network whose settings the model copies.

### Redemption

**Redemption.** Handing your stablecoins back to the issuer and receiving dollars from its
reserves. This is the issuer's side of the promise: bring us a token, we pay you par.

**Issuer.** The company behind the stablecoin (Circle, for USDC).

**Reserves.** The assets the issuer holds to pay redemptions. In the calibration,
$32.4 billion in T-bills.

**Spread.** A deduction from par when you redeem. If the spread is 1%, you hand in a
token and get $0.99 back.

**First-in, first-out (FIFO) queue.** Redemption requests wait in a single line and are
paid in the order they arrive, like a bank counter with one teller.

**Per-step capacity.** The teller can only pay out so much every 12 seconds. When more
requests arrive than the channel can pay, the line grows. This turns out to matter a
great deal (sections 4 and 7 of the note).

**"Any agent may join the queue; none has priority."** Everyone waits their turn, and the
only way to reach the reserves is through this line.

### Agents

An **agent** is a simulated participant following a fixed set of rules. The model has
five kinds.

#### Attacker

The seller putting pressure on the price. In the March 2023 replay it stands in for many
frightened holders selling at once, not a single villain.

- **Fixed stock.** The attacker starts with a set number of stablecoins to sell and gets
  no more.
- **Pace.** How fast it sells: a fixed share of whatever it still has, every step. A pace
  of 10% means it sells 10% of its remaining stock each step, so it starts big and tapers
  off. A pace of 1% is slow and steady. Section 6 of the note shows that the slow,
  patient seller is the hardest to beat.
- **"No motive and does not adapt."** It doesn't try to profit, and it doesn't change its
  behaviour in response to what others do. It just keeps selling on schedule.

#### Defender (the issuer)

The issuer stepping into the market to support its own price.

- **Buys on the venue.** It spends money buying stablecoins from the pool, which pushes
  the price back up.
- **Trigger.** The price level that sets it off. A trigger of 1% means it starts buying
  once the price falls more than 1% below par (below $0.99).
- **Pace.** How fast it spends: a share of its remaining budget each step. The note
  compares 50% (spend fast), 20% (the calibrated case) and 10% (spend slowly).
- **Budget.** The pot of money set aside for buying on the venue. This is separate from
  the reserves, which are only reached through the redemption queue. Section 4 of the
  note adds the two together when it talks about the defender's total resources.
- **Widening the redemption spread.** Increasing the deduction on redemptions, so
  someone handing in a token gets less than before (say $0.98 instead of $0.99). It makes
  leaving through the issuer more expensive and slows the drain on reserves. The note
  uses it as the on-chain counterpart of the Bank of England raising interest rates in
  1992, and finds it buys about an hour.
- **"No cost function and never gives up."** It doesn't weigh whether defending is worth
  it; it follows its rules until the money runs out. A real issuer would decide.

#### Arbitrageur

A trader who profits from price gaps and, in doing so, pulls the price back toward par.

- **Arbitrage.** Buying something where it is cheap and cashing it in where it is worth
  more. Here: buy the stablecoin on the venue below par, then redeem it with the issuer
  for par.
- **The venue.** The trading pool described above, the place where the stablecoin's price
  is set. The arbitrageur buys there because that is where the discount shows up.
- **"Below the oracle by more than fees."** It only acts when the pool's price is far
  enough under the oracle's price that the gap still pays after trading costs.
- **Redeems.** It then joins the redemption queue to collect par. If the queue is long,
  its profit (and its price-restoring buying) is delayed.

#### Holder (the believer)

Someone who trusts the issuer will eventually pay $1.00 and sees a discount as a
bargain.

- **Par.** $1.00, what the believer expects to get back in the end.
- **Entry discount.** How far below par the price must fall before the believer starts
  buying. An entry discount of 2% means it buys once the price drops below $0.98; 20%
  means it waits until below $0.80. Its money then holds the price at that level until
  the money runs out.
- **Redeems when the queue is clear.** It cashes in at par once the redemption line is
  empty.
- **Tranches.** Slices of the believers' money, each with its own entry discount. The
  note's best-fitting version splits the money equally across four tranches entering at
  2%, 5%, 10% and 20% below par. That is the "ladder" in section 3, and why the price
  falls in a staircase.

#### Liquidity provider

The party whose deposits make up the pool.

- **Its share of the pool.** Each provider owns a portion of the pool's two stocks and can
  take that portion out.
- **Panic threshold.** The price at which it pulls its money out.
- **Holds, sells or redeems.** What it does with the stablecoins it withdrew: keep them,
  sell them elsewhere, or hand them to the issuer. Section 7 of the note shows each choice
  leads to a very different outcome.

### Recovery

How the model decides whether the peg survived.

- **Band (±31 bps of par).** "Back at par" means within 0.31% of $1.00, between roughly
  $0.9969 and $1.0031.
- **Horizon (60 h).** Each experiment watches 60 hours, about the length of the March 2023
  weekend.
- **6,900 steps (23 h).** To count as recovered, the price must stay inside the band for
  23 hours straight before the 60 hours are up.
- **"First re-entry by 37 h."** 60 minus 23 is 37, so if the price hasn't got back into
  the band by hour 37, there isn't time left to stay there for 23 hours. Hour 37 is the
  real deadline.
- **Calm reference.** The background "true value" in calm conditions.
- **Reverts to par with a half-life of 1.4 h.** When the background value drifts away
  from $1.00, it is pulled back so that half of any gap closes every 1.4 hours. That rate
  was measured from USDC's own price in quiet times.
- **Time to parity.** Hours until the price first gets back inside the band. It is
  measured on the pool's price only, so it doesn't depend on how the background value is
  modelled.

### The closing paragraph

**Monte Carlo.** Running the same experiment many times, each with a different random
seed, to see how much the results vary by chance.

**Cells.** Individual experiments in a grid of settings (for example, one pool depth
paired with one attack size).

**16 seeds (8 in the liquidity sweeps).** Each cell is run 16 times with different seeds,
or 8 times in the experiments that vary pool depth.

**Reference path.** The track the background "true value" follows over the 60 hours. The
seeds change only this, and the note reports that in most cells it barely moves the
results.

---

*This guide explains the note's vocabulary only. For what the model found, read the note.*
