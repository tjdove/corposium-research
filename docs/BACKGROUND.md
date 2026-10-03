# Black Wednesday, 1992: Background

**Status:** draft v0.1 (2026-10-03) · **Author:** Tim Dove with Claude
**Feeds:** research note framing section (4.1), site page (4.3), one-pager (4.4), build-in-public posts

---

## Why this project starts in 1992

On 16 September 1992 the British government spent a large share of its foreign-exchange reserves and raised interest rates twice in one day to keep the pound inside the European Exchange Rate Mechanism (ERM). By evening it gave up. Sterling left the ERM, fell sharply, and George Soros's Quantum Fund booked a profit of roughly $1 billion.

The event is the cleanest historical example of a **price promise that ran out of capacity under adversarial pressure.** A government promised a price. Markets judged the promise larger than the resources and political will behind it. Speculators sold until the defender stopped buying.

A stablecoin peg is the same kind of promise: one token will be worth one dollar. This project asks the 1992 question in DeFi terms: **under what combination of pool depth, oracle delay, attacker capital and defense policy do reserves run out before the peg recovers?**

---

## The short version

- In 1990 Britain tied the pound to the Deutsche Mark through the ERM at a central rate of DM 2.95, with a ±6% band. The floor was about DM 2.78.
- German reunification led the Bundesbank to keep interest rates high. Under the ERM, Britain had to keep its own rates high too, while its economy was in recession.
- Markets doubted Britain would keep inflicting that pain. Denmark's rejection of the Maastricht Treaty in June 1992 deepened the doubt.
- On 16 September the Bank of England bought pounds heavily and rates went from 10% to 12%, with 15% announced. Selling continued. At 7:40 pm the Chancellor announced the pound's exit from the ERM.
- The Treasury later put the net cost at about £3.3 billion. Quantum Fund's short position was about $10 billion and its profit about $1 billion.

---

## 1. The promise: sterling in the ERM

The ERM, set up in 1979, held European currencies within bands around agreed central rates. In practice the Deutsche Mark was the anchor, because the Bundesbank had the strongest anti-inflation record in Europe. Central banks were obliged to intervene when a currency reached the edge of its band.

Britain joined on 8 October 1990 with a central rate against the mark of DM 2.95, operating initially in the wider 6% band. [1][2] Most members used a ±2.25% band; Britain was expected to move to it later. The permitted range was therefore roughly DM 2.78 to DM 3.13. [3]

Many observers already thought the entry rate was too high. Britain joined partly to import German monetary discipline after the late-1980s inflation.

## 2. Why the promise became hard to keep

Several pressures built up between 1990 and 1992.

**German reunification.** Bonn financed reunification largely by borrowing. To contain the resulting inflation, the Bundesbank raised rates. Every currency pegged to the mark had to follow, whatever its own economy needed.

**Recession in Britain.** British inflation fell from over 9% in 1990 to under 4% by August 1992, but interest rates could not fall with it because of the German link. [4] Unemployment rose toward 3 million (it passed that mark in February 1993). [5][6] Most British mortgages carried variable rates, so every rate rise hit homeowners directly. Holding high rates to defend the pound carried an immediate political cost.

**Capital mobility.** By 1990 the main European economies had removed most capital controls. Money could leave a currency in hours, and the daily volume of currency trading dwarfed any one central bank's reserves.

**Rigid parities.** After 1987 the ERM stopped making the small, frequent realignments it had used before. [7] Governments came to treat their parities as fixed points of national credibility, especially with monetary union planned under the 1991 Maastricht Treaty. Price and wage differences accumulated without an outlet, leaving the pound and the Italian lira overvalued.

**Political shocks.** On 2 June 1992 Danish voters rejected the Maastricht Treaty, and France scheduled its own referendum for 20 September. The path to monetary union, which justified the pain of holding parities, suddenly looked uncertain.

**The failed Bath meeting.** On 4–5 September 1992 European finance ministers and central bankers met informally in Bath. Chancellor Lamont pressed the Bundesbank to cut German rates. The meeting ended with neither a German rate cut nor a realignment of parities, so the overvalued currencies had no relief and the markets had no reassurance. *Confirm date and outcome against a primary account.*

## 3. Black Wednesday

**15 September.** Comments by Bundesbank President Helmut Schlesinger suggesting a broader realignment of ERM currencies reached the markets. [4] Traders read them as a signal that Germany would not defend sterling indefinitely.

**16 September, morning.** Selling of sterling intensified. The Bank of England bought pounds with its reserves, at times reportedly around £2 billion an hour. [4]

**11:00.** The government raised the base rate from 10% to 12%. [8] Selling continued: markets did not believe Britain would keep rates that high in a recession.

**Afternoon.** The government announced that rates would rise to 15% the next day. [4] This also failed to stop the selling.

**19:40.** Chancellor Norman Lamont announced that Britain was suspending its ERM membership. [4] The 15% rise never took effect. [9]

**Following days.** Italy also left the ERM, and Spain devalued the peseta. The pound fell well over 10% against the mark in the weeks that followed. In August 1993 renewed attacks, chiefly on the French franc, forced the ERM to widen its bands to ±15%. [10]

## 4. The attackers

Stanley Druckenmiller, chief strategist at Soros's Quantum Fund, identified the trade. Soros pushed to size it far larger. By Black Wednesday the fund was short roughly $10 billion of sterling, and its profit is usually put at about $1 billion. [11][12] Mallaby's hedge-fund history credits Druckenmiller with most of the analysis. [11]

Quantum was the most visible seller but not the only one. Banks, corporate treasurers and other funds were selling too, many of them unwinding "convergence trades": positions that had borrowed in low-rate currencies to buy high-yielding ERM currencies on the assumption that parities would hold. When confidence broke, those positions all reversed at once. The attack worked because a large, visible actor gave the rest of the market a reason to move together.

## 5. The cost

The cost figures vary widely because they measure different things.

- **Net cost to the Treasury:** about **£3.3 billion**, the Treasury's estimate released under freedom of information in February 2005 (an earlier 1997 estimate was £3.4 billion). [13][14] It compares the actual value of the reserves with what they would have been worth with no intervention.
- **Trading losses** on intervention in August and September were about £800 million. [8]
- **Gross reserves spent** in defending the pound are widely reported as £27 billion, based on the same Treasury papers. [15] *Verify against the primary release before publication.*
- Early press estimates of £13–27 billion confused gross spending with loss.

## 6. Aftermath

The outcome is sometimes called "White Wednesday." Freed from the ERM, Britain cut interest rates quickly and in October 1992 adopted an explicit inflation target. In 1997 the Bank of England gained operational independence. The British economy recovered faster than much of continental Europe in the following years. [4] The Conservative government's reputation for economic competence never recovered. [16]

For Europe, the lesson was that a halfway regime (a peg that can be abandoned) is fragile when capital moves freely. The response was to go further: a single currency and a single central bank, which arrived as the euro in 1999.

---

## How economists explain it

Three frameworks help explain why the peg broke. The simulator draws on all three.

**First-generation models: running out of reserves.** In Krugman's 1979 model (extended by Flood and Garber, 1984), a government defends a fixed rate while its reserves steadily drain. Speculators know the peg must break when reserves hit zero, so they attack earlier, at the moment their combined selling can exhaust what is left. The timing of the crisis follows mechanically from the reserve level.

**Second-generation models: the cost of defending.** Britain in 1992 still had reserves and borrowing capacity. What it lacked was the willingness to keep rates high in a recession. Obstfeld's models (1994, 1996) treat the government as weighing the cost of defending against the cost of giving up. Doubt in the markets forces rates up, which raises the cost of defending, which makes giving up more likely. The same economy can hold its peg if markets stay calm, or lose it if they panic. The crisis can be **self-fulfilling**.

**Reflexivity.** Soros's own framework says that market participants' beliefs change the fundamentals they are trying to read. Selling a currency forces rate rises, which damage the economy, which weakens the government's resolve, which justifies the selling. The feedback loop, not the starting fundamentals, decides the outcome.

**Large players.** Standard models assume many small traders. Later work on "large players" in currency crises (Corsetti, Pesenti and Roubini, among others) shows that one big, visible speculator can coordinate the rest of the market, making an attack succeed that small traders alone would not attempt.

---

## Mapping 1992 to the simulator

| 1992 | Simulator | Config |
|---|---|---|
| ERM central rate and floor (DM 2.95 / ~2.78) | Peg price and defender trigger | `redemption.peg_price`, defender `threshold_pct` |
| Bank of England FX reserves | Redemption reserves and defense budget | `redemption.reserves`, defender `max_spend` |
| Bank buying sterling in the market | Defender buying the stablecoin in the AMM | defender `spend_pace` |
| Rate rises, 10% → 12% → 15% | Redemption spread widening (closest available lever; see below) | defender `spread_adjust_bps` |
| Quantum Fund's short | Attacker agent | attacker `capital`, `pace`, `start_step` |
| Banks and funds selling, convergence trades unwinding | Arbitrageurs; LP withdrawal agent (stretch) | arbitrageur params; `panic_threshold_pct` |
| Market depth for sterling | AMM pool depth | `amm.reserve_*` |
| Schlesinger remarks, Danish vote | Scheduled shocks to the reference price | `environment` shock events |
| Delay before official prices catch up | Oracle heartbeat and deviation threshold | `oracle.heartbeat_steps`, `deviation_threshold_pct` |

## Where the analogy breaks

Stating these up front is part of the result.

1. **The defense lever differs.** A rate rise rewards holders and raises the cost of shorting. Widening a redemption spread instead makes exit more expensive. Both raise the cost of attacking and both hurt ordinary holders, but they are not the same mechanism.
2. **No political cost function.** Our defender follows rules: a threshold, a pace, a cap. It does not weigh the pain of defending against the cost of quitting. The simulator is therefore closer to a first-generation reserve-exhaustion model, with reflexivity entering through arbitrageurs and, if built, LP flight. A second-generation defender is a natural follow-up.
3. **Transparency.** In 1992 nobody outside the Treasury knew the reserve level in real time. On-chain, reserves and pool depth are public, block by block. Attackers can calculate exactly how much capital a run needs.
4. **No partner central bank.** Sterling's fate depended partly on how much the Bundesbank would help. Most stablecoins have no lender of last resort. In March 2023 USDC recovered its peg only after US authorities guaranteed deposits at Silicon Valley Bank, an outside backstop outside the protocol.
5. **The promise is different.** ERM obligations bound governments within a negotiated system. A stablecoin redemption promise is set by the issuer's terms and its reserve custody.
6. **Market structure and time.** Currency markets in 1992 were deep, over-the-counter and slow to report. An AMM's price impact is exact, public and settles every block.

---

## Figures to verify before publication

- [ ] Gross reserves spent (£27bn): confirm in the Treasury's February 2005 FOI release, not secondary sources
- [ ] Reconcile intervention totals: the NotebookLM infographic shows £15bn, secondary sources report £27bn gross; find which figure covers which period
- [ ] Bath meeting (4–5 Sept 1992): confirm date and outcome
- [ ] Intervention rate of ~£2bn an hour: find a primary or contemporaneous source
- [ ] Size of convergence trades unwinding: the notebook cites $300bn; no source found yet, so omitted until sourced
- [ ] Pound's fall against the mark by end-September and end-1992: pull from Bank of England historical rates
- [ ] Exact times of the 15% announcement and the 17 September rate cut back to 10%

## Corrections made to the source notes

The background research supplied with this draft (NotebookLM briefing, Oct 2026) was accurate in outline. These points were corrected:

- Sterling was in the **±6%** band, not the standard ±2.25%.
- UK unemployment was about 2.8–2.9 million in September 1992; it passed 3 million in **February 1993**.
- Capital controls were removed under directives following the **1986** Single European Act, effective 1990; the notebook dated this to 1992.
- British mortgages were mainly **variable-rate**, not "indexed."
- The $300bn convergence-play figure is unsourced and left out for now.

---

## Sources

1. Bank of England, "The exchange rate mechanism of the European monetary system," *Quarterly Bulletin* 1990 Q4. https://www.bankofengland.co.uk/quarterly-bulletin/1990/q4/the-exchange-rate-mechanism-of-the-european-monetary-system
2. John Major, ERM statement to the House of Commons, 15 October 1990. https://johnmajorarchive.org.uk/1990/10/mr-majors-exchange-rate-mechanism-statement-15-october-1990/
3. Politeia, on the ERM band range. https://www.politeia.co.uk/?p=4213
4. Econlib, "Wednesday, Black and White." https://www.econlib.org/wednesday-black-and-white/
5. Wikipedia, "1993 in the United Kingdom" (unemployment timeline). https://en.wikipedia.org/wiki/1993_in_the_United_Kingdom
6. Wikipedia, "Second Major ministry." https://en.wikipedia.org/wiki/Second_Major_ministry
7. The Globalist, "European Blame Games: A 20-Year Retrospective" (2013). https://www.theglobalist.com/european-blame-games-a-20-year-retrospective/
8. AudlemOnline, "On This Day – September 16th" (summarizing the 2005 Treasury release). https://www.audlem.org/news/on-this-day-september-16th.html
9. Channel 4 FactCheck, "Early nineties economy" (2008). https://www.channel4.com/news/articles/politics/domestic_politics/factcheck%2bearly%2bnineties%2beconomy/2831672.html
10. Peterson Institute, Truman, "Mike Mussa (1944–2012): When Will They Learn?" (on the August 1993 band widening). https://www.piie.com/blogs/realtime-economics/2012/mike-mussa-1944-2012-when-will-they-learn
11. The Motley Fool, "Duquesne Family Office" (citing Mallaby, *More Money Than God*). https://www.fool.com/investing/how-to-invest/famous-investors/duquesne-family-office
12. Sebastian Mallaby, *More Money Than God* (2010), chapter on the sterling trade. *Primary citation to check.*
13. Margaret Thatcher Foundation archive, HM Treasury minute "The cost of Black Wednesday reconsidered," FOI release 9 Feb 2005. https://margaretthatcher.org/document/137077
14. Central Banking, "Cost of UK's fight to stay in ERM." https://www.centralbanking.com/node/1423239
15. Financial Times, Blitz and Newman, 10 Feb 2005 (Treasury papers), as summarized in secondary sources. *Primary to check.*
16. Unherd, Halligan, on the political aftermath (2017). https://unherd.com/2017/09/day-nearly-25-years-ago-britain-screwed-cabinet/

**Academic references for the theory section:**
- Krugman, P. (1979). "A Model of Balance-of-Payments Crises." *Journal of Money, Credit and Banking* 11(3).
- Flood, R. and Garber, P. (1984). "Collapsing Exchange-Rate Regimes: Some Linear Examples." *Journal of International Economics* 17.
- Obstfeld, M. (1994). "The Logic of Currency Crises." *Cahiers Économiques et Monétaires* 43.
- Obstfeld, M. (1996). "Models of Currency Crises with Self-Fulfilling Features." *European Economic Review* 40.
- Corsetti, G., Pesenti, P. and Roubini, N. (2002). "The Role of Large Players in Currency Crises." In Edwards and Frankel (eds.), *Preventing Currency Crises in Emerging Markets*.
- Eichengreen, B. and Wyplosz, C. (1993). "The Unstable EMS." *Brookings Papers on Economic Activity* 1993(1).
- Soros, G. (1987). *The Alchemy of Finance.*
