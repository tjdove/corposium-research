# What the Model Found, in Plain Words

**Status:** v0.1 (2026-10-13) · *being rewritten for note v2 after outside review 1 and Epic 5; Findings 1, 3 and 5 below carry interim corrections* · **Author:** Tim Dove with Claude
**For:** anyone who wants the findings without the equations. Tim's study guide; also the
source for the site page, the one-pager and the launch thread.
**Read with:** [`BACKGROUND.md`](BACKGROUND.md) (1992), [`USDC-2023.md`](USDC-2023.md) (the test case),
[`NOTE.md`](NOTE.md) (the research note), [`FINDINGS.md`](FINDINGS.md) (every finding, with its evidence).

---

## The project in one paragraph

A stablecoin is a promise: one token is worth one dollar. In 1992 the British government
made a similar promise about the pound and lost it to speculators. We built a small
simulator of a stablecoin under pressure, set every dial to a public number, checked it
against the one time a big stablecoin actually broke (USDC, March 2023), and then asked it
the 1992 question: what breaks a peg? It gave five answers worth publishing. One of them
says the 1992 story doesn't fit crypto the way people assume.

---

## How the model works

Think of a sandbox with three pieces of plumbing and five kinds of players.

**The plumbing**

- **The pool.** A trading pool where the stablecoin is swapped for dollars, like Curve. Its
  price is the stablecoin's price. Dump coins in and the price falls; buy coins out and it
  rises. How much it moves depends on how big the pool is.
- **The price feed.** Reports the price to the outside world, like Chainlink. It updates
  when the price moves enough or when enough time passes.
- **The redemption window.** The issuer pays one dollar per coin from its reserves, but only
  so many coins per minute. Over a weekend with banks closed, very few.

**The players**

- **The attacker.** Holds a pile of coins and sells them into the pool at a steady pace.
  It has no motive in the model. A coin sold out of fear and a coin sold for profit do the
  same thing to the price.
- **The defender.** The issuer. It can buy coins back in the pool with a budget, and it can
  make redemption more expensive.
- **The arbitrageur.** Buys coins cheap in the pool and redeems them for a dollar. That
  pushes the price back up.
- **The believer.** Buys coins at a discount because it trusts the dollar promise, then
  redeems them when the window is open.
- **The liquidity provider.** Owns part of the pool. Pulls its money out if the price falls
  too far.

**The rules of the game**

- Every step is 12 seconds, like an Ethereum block.
- The same inputs always produce exactly the same output. Anyone can rerun it and check.
- The peg has **recovered** when the price stays within about a third of a cent of a dollar
  for a full day.

---

## The test: USDC, March 2023

Full story in [`USDC-2023.md`](USDC-2023.md). The short version:

On Friday night, 10 March 2023, Circle said $3.3 billion of USDC's reserves were stuck at
Silicon Valley Bank, which had just failed. Holders panicked and sold. Banks were closed
for the weekend, so almost nobody could redeem. By 2 am Saturday USDC was at 87 cents. On
Sunday evening the government guaranteed SVB's deposits. On Monday the banks opened, Circle
paid out, and USDC was back at a dollar.

**No one has been identified as attacking USDC. It was a run.** In the model, the "attacker" stands in for the run:
all the selling added up, about $2.7 billion.

We fed the model the size of the run, the speed of the weekend redemption window, and the
public size of Circle's reserves, and turned the defender off because Circle never bought
on the market.

---

## Finding 1: The believers decide how far it falls

**What happened in the model.** The first replay crashed to 42 cents. The real one stopped
at 87. Four times too far.

**Why.** The model had nobody like the traders who looked at USDC at 90 cents on Saturday
morning and thought: "Circle has the money. It'll pay a dollar on Monday. I'll buy now."
Every coin they bought was a coin the run didn't push lower. They were a floor made of
belief.

**The fix.** We added one believer and sized it so the model matched the real low. It
landed within 17%, at about $2.15 billion of buying. Then we said real buyers don't all
jump in at the same price, and spread the money across four entry prices (2, 5, 10 and 20
cents below a dollar). It landed within 4% of the real low and within nine minutes of the
real timing.

**The claim.** How far a stablecoin falls is decided by the selling against everyone who
believes the promise. Not mainly by the issuer. Not mainly by the pool.

**The honest part.** We fitted the believers' size to the real low, so matching it isn't
proof on its own. What isn't fitted: the timing came out right, and the shape of the
recovery got better. And nobody knows where the real buyers' money sat; the four entry
prices are our assumption, stated as one.

*In the note: §3, Figures 1 and 1b.*

---

## Finding 2: Deep liquidity cuts both ways

Picture the pool as a bathtub with coins floating in it.

**Small tub.** The attacker dumps a pile of coins and the price crashes to pennies. That
sounds terrible, but it means the defender can buy them all back for pennies. A small
budget cleans it up and the price comes back.

**Big tub.** The same dump barely moves the price. Good for holders. But the attacker sold
for close to a dollar each, so the defender has to buy back at close to a dollar too. The
same budget only covers part of it. At twice the real pool size, holding the line needs a
budget about a third the size of the attack, and it grows as the attack grows.

**The claim.** Deep liquidity protects the price and makes the defense unaffordable.
Most people assume more liquidity is simply safer. It's safer for the price and harder on
whoever has to defend it.

*In the note: §4.*

---

## Finding 3: Spend slower than the attacker sells

We gave the defender one budget and tried different ways of spending it: fast and early,
medium, and slow and late.

**All of them spend every dollar.** The difference is what the dollar buys.

**The fast defender** empties its wallet in the first minute or two, buying at 90-something
cents, while the attacker still has most of its coins. Then the attacker keeps selling into
a market with nobody defending it, and the price drops to a new low. The defender's money
is gone, spent at the worst time.

**The slow defender** still has money when the attacker runs out of coins. It buys the
bottom, at about 28 cents a coin instead of 36. At a full-size attack the slow defender is
the only one where the price ever comes back.

**What doesn't matter:** how far the price has to fall before the defender starts. The
attacker's first sale crashes the price past every trigger we tried, so they all start at
the same moment.

**What does matter:** pace. How fast the defender spends compared to how fast the attacker
sells. Spend at half the attacker's pace and the price is back in hours. Spend faster than
the attacker sells and it never comes back.

**The 1992 line.** The Bank of England spent fast, at the floor, while the selling was
still coming. The model says that is the policy most likely to lose. This is the most
quotable sentence in the note, and the one people will argue with.

*In the note: §5, Figure 3.*

---

## Finding 4: The clock runs out, not the money

The 1992 story is about running out of reserves. The Bank hit its limit and gave up.

Circle was nowhere near running out. In the model, even at the biggest attacks we ran, the
reserves never hit zero inside the 60-hour window.

What runs out is time. The redemption window only pays so much per minute. Over a weekend
that is about 8% of the reserves in 60 hours. The money is there; it can't get out the door
fast enough.

So a peg can be lost two ways:

- **Lost on the price:** it never comes back.
- **Lost on the clock:** it comes back, but too late to settle before time is up.

Figure 2 in the note is a map of both. At the real pool size, bigger attacks fall into
"lost on the clock." At twice the pool size, the same attacks are lost on the price
outright.

**The catch.** This assumes the liquidity stays in the pool. If liquidity providers pull
out, the picture changes. See Finding 5.

*In the note: §4, Figure 2.*

---

## Finding 5: Two exits, not one

This is where the 1992 story stops fitting, and we made that a result instead of a
footnote.

**1992.** If you held pounds and stopped believing, you sold them in the market. At the
floor, the buyer of last resort was the Bank of England, so net selling at the floor came
out of the Bank's reserves. That is how the market, once it turned, finished off the peg.

**On-chain, there are two ways out.**

- **Sell in the pool.** Pushes the price down. Never touches the issuer's reserves.
- **Redeem with the issuer.** Doesn't move the pool price. Pulls straight from the
  reserves.

Selling breaks the *price*. Redeeming drains the *issuer*. Both are ways a peg fails, and USDC's price broke on the market that weekend while redemption was shut. What the 1992 story calls "breaking the Bank" is the second one.

**How we found it.** By getting it wrong first. We modelled "losing faith" as dumping in the
pool. The peg got *harder* to break, and the believer lost a lot of money. Then we saw that
in 1992, selling to the Bank at the floor *was* a redemption. Modelled that way, the
believers who quietly keep redeeming at a dollar are the ones who drain the reserves.

**March 2023 fits this.** Over the weekend redemption was closed, so holders who lost faith
had to use the first exit. They crashed the price and left Circle's reserves alone.

**Two smaller results next to this one:**

- **Panicking liquidity helps the defender only if it sits still.** Liquidity providers
  who pulled out of the pool took the attacker's dumped coins with them, and the peg
  recovered faster. We then let them dump or redeem what they took out (Story 5.4). Dumping
  makes the crash deeper but the peg still recovers; redeeming leaves the crash alone and
  the peg never recovers, because the provider's coins sit at the front of the redemption
  line and the arbitrage that would restore the price waits behind them. Who is at the
  front of the queue decides who recovers. 1992 had no queue.
- **A believer who overpays is a free defender.** One who buys above what the coin is worth
  holds the price up with its own losses.

*In the note: §7, Figure 5.*

---

## Smaller results worth knowing

- **Price-feed delay doesn't matter.** Across every update setting we tried, from one
  minute to 23 hours, the low moved by less than a tenth of a cent. At Chainlink's actual
  settings it is the same as a feed with no delay. (§6)
- **Triggers could not be tested.** Three thresholds in the model (when the defender
  starts, when the believer gives up, when the liquidity provider panics) never made a
  difference, because in every attack we ran the first sale crossed all of them at once.
  That means we have not tested them, not that they do nothing (Story 5.3).
- **The 1992 replay needs the believers.** Running the model as 1992, the Bank runs dry at
  about 4.9 times Quantum Fund's position when there are large believers who redeem, and at
  5.7 times without them. That ratio (attack to resources ≈ 1.04) is close to what the
  textbook reserve-exhaustion theory predicts.

---

## What the model doesn't do

Say these before anyone else does.

- **One test event.** A second one would tell us whether the believers' size generalises.
- **One pool stands in for every venue.** Real USDC traded on dozens of exchanges and pools.
- **No government.** The real USDC recovery came from a Sunday guarantee. The model's
  recovery comes from redemption reopening on Monday, which is when it happened in reality,
  but for a different reason.
- **The defender follows rules.** It never weighs the cost of defending against the cost of
  giving up, which was the whole story in 1992.
- **The liquidity provider holds what it takes out.** In reality some would dump.

---

## Words we use

| Word | Plain meaning |
|---|---|
| **Peg** | The promised price. For a dollar stablecoin, $1. |
| **Depeg** | The price falling away from the promise. |
| **bps (basis points)** | Hundredths of a percent. 100 bps = 1 cent on a dollar. −1,373 bps = 86.3 cents. |
| **Par** | Exactly the promised price. $1.00. |
| **Reserves** | The money behind the promise. For Circle, mostly T-bills. |
| **Redemption** | Handing the coin back to the issuer for a dollar. |
| **AMM / pool** | A trading pool where the price is set by a formula from what's in it (Curve, Uniswap). |
| **Oracle** | A price feed that reports the market price on-chain (Chainlink). |
| **Liquidity / depth** | How much money is in the pool; how much it takes to move the price. |
| **D\*** | Our fitted pool size: about $3.9 billion a side, the combined depth of all USDC markets. |
| **C\*** | Our fitted believer money: $2.15B at one price, $2.54B across four. |
| **Time to parity** | Hours until the price first gets back within a third of a cent of a dollar. |
| **The band** | ±31 bps around $1: close enough to count as "on the peg." |
| **Deterministic** | Same inputs, same outputs, every time. Anyone can check. |
| **Freeze** | The code stopped changing on 9 October; every figure in the note comes from that version. |
