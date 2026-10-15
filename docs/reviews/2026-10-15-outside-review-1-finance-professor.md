# Outside Review 1: finance-professor persona (model), 2026-10-15

**What this is.** The first outside read of the research note (v1.0, written against the
`v0.9-freeze` figures). Reviewer: a frontier language model (ChatGPT) run by Tim with
`PROMPT-1-finance-professor` from the review pack: a currency-crisis economist refereeing for
a journal, given the note, the two background documents, the findings log, the validation
record and the six figures, blind to what we hoped to hear. The report is reproduced verbatim
in Part 1. The dev manager's assessment is Part 2. Tim's decision is Part 3. Part 4 maps
every point to what we do about it.

**Why it is in the repo.** So the next version of this project does not make the same
mistakes. Read it before writing any public claim.

**Caveat.** The reviewer is a model. Its arguments stand or fall on their own; its factual
corrections (Fed research notes, DAI's backing share, 1992 details) are leads to verify at
the primary, not rulings. Marked as such in Part 4.

---

## Part 1 — The report (verbatim)

Referee Report

Manuscript: What breaks a peg: a 1992 currency attack, replayed on-chain

1. The central claim

Verdict: The March 2023 exercise is an in-sample calibration with a useful model-diagnostic failure, not independent empirical validation.

The authors write:

“The depth of a depeg is set by the attacker against everyone who believes the promise.”

That is a plausible economic proposition. The difficulty is that the experiment does not establish it empirically.

The authors have effectively used the same episode to determine the attack size, infer aggregate market depth, fit the attacker’s pace, introduce a previously missing class of buyers, estimate those buyers’ capital, and select a distribution of their entry prices.

Three fitted quantities matter:

* D* ($3.91 billion per side) was selected using the observed trough under a baseline containing an issuer buying on the venue.
* Pace (0.002 per step) was selected to reproduce the observed trough’s timing.
* C* ($2.54 billion for the selected ladder) was selected to minimize the difference between the simulated and observed trough.

The ladder is also selected from three alternatives after their performance is observed. Calling its spacing an assumption rather than a fitted parameter does not eliminate this model-selection problem.

The authors write:

“The trough is −1,323 bps at 31.2 h against −1,373 at 31.0 h: within 4%, and within nine minutes, with the timing improving without pace being touched.”

The nine-minute match is more interesting than the depth match because the pace was not re-estimated after adding the ladder. But it is still not an independent prediction. The pace was already calibrated against the same event, and the ladder was selected after comparing outcomes against that event.

There is a second, more consequential problem: the observed USDC price is supplied to the model as its reference price.

The authors write:

“Fed the observed USDC/USD series as its reference…”

The arbitrageur trades against an oracle following that series. Consequently, some agreement between the simulated and observed trajectories is induced by the model’s inputs.

The internal validation record explicitly acknowledges this. It states that agreement after approximately hour 63 in the original replay is mostly the input series showing through. In the revised replay, the trajectories begin converging earlier, but the same identification problem remains.

What evidence survives the fitting?

There are three potentially informative observations.

First, the original model failed substantially. Removing an issuer buyer that had absorbed 89% of the modeled attack caused the price to fall to approximately $0.42 rather than $0.86. This demonstrates that a model containing almost no private demand for discounted USDC cannot reproduce the event under the chosen depth assumption.

That is evidence of a missing absorption mechanism. It does not establish that the missing mechanism consisted of $2.54 billion of par-expecting capital with the modeled entry schedule.

Second, the single-buyer and ladder experiments reveal a nonlinear relationship between buyers’ capital and the minimum price. The internal validation tables show large jumps in the trough when capital crosses particular thresholds.

That is a genuine result about the simulator’s mechanics. The authors could derive and explain it without treating the USDC replay as a successful empirical test.

Third, the simulation can produce a sharp decline followed by recovery, consistent with the broad temporal pattern of March 2023. But the event timing, changing redemption capacity, and observed reference series were supplied as inputs. This evidence is weak.

The note also has no independently measured buyer-capital series, buyer entry-price distribution, or gross directional selling series against which to test the proposed mechanism.

Is the evidence enough?

Enough for a computational demonstration of a plausible mechanism; not enough for the causal or quantitative claim being made.

A defensible conclusion would be that, conditional on an assumed market depth and selling schedule, adding price-sensitive buyers substantially changes the model’s depeg depth, and one calibrated configuration can reproduce the observed trough.

The stronger claim—that the authors have identified what determined the March 2023 trough—is not established.

The important distinction is between discovering that a model needs an economically meaningful counterparty and demonstrating that the modeled counterparty explains the historical event.

The paper achieves the first. It has not achieved the second.

2. Rank the findings

Ranked by how defensible the claim is as written, not by how interesting it sounds.

Rank	Claim	Classification	Assessment
1	(d) Redemption throughput, not reserves. “What fails is time.”	(ii) Known in theory, shown mechanically.	The cleanest result. The capacity constraint genuinely determines outcomes within the specified horizon. It is not novel, but the implementation makes the distinction visible.
2	(b) Deep liquidity protects price but raises defense cost. “Deep liquidity protects the price and makes the defense unaffordable.”	(ii) Known market mechanics, illustrated usefully.	The price-impact arithmetic is sound under the assumed AMM and fixed budget. “Unaffordable” overstates a conditional cost result.
3	(a) Attacker versus believers. “The depth of a depeg is set by the attacker against everyone who believes the promise.”	(ii) Known in theory, shown mechanically.	Countervailing demand determines a market-clearing price. The simulation demonstrates the mechanism but does not identify that demand independently.
4	(c) Spend slower than the attacker. “Spend slower than the attacker sells.”	(ii) Known execution trade-off, demonstrated under restrictive assumptions.	The simulations support the conditional result, not the universal prescription. The policy conclusion is much stronger than the evidence.
5	(e) Two exits. “Only the second breaks the peg.”	(iii) A specialist already knows the distinction.	Primary versus secondary markets is elementary stablecoin market structure. Worse, the final sentence is false under the paper’s own definition of a broken peg.

The distinction between (ii) and (iii) matters.

A result is not automatically uninteresting because its mechanism is known. A transparent simulation can reveal nonlinearities, interactions, and boundaries that are difficult to appreciate from verbal theory.

But it must actually reveal something.

For (e), distinguishing primary-market redemption from secondary-market selling is standard. A 2024 Federal Reserve research note is explicitly devoted to primary and secondary stablecoin markets and examines March 2023. It is a more relevant benchmark than much of the literature cited by the authors.

The authors’ contribution cannot be the discovery that selling USDC on an exchange does not directly draw down Circle’s reserves.

For (b), I would retain the result but demand a more precise formulation. The mechanism is essentially the constant-product inventory and execution-cost relationship. The model’s contribution would have to be the quantified interaction with finite defense budgets, not the mere observation that buying closer to par costs more.

3. The weakest claim

The weakest claim, judged literally, is (e): that only redemption breaks the peg.

The authors write:

“Selling on the venue breaks the price and spares the reserves; redeeming spares the price and drains the reserves. Only the second breaks the peg.”

Hostile referee paragraph

The authors have confused the exhaustion of an issuer’s reserves with the failure of a market-price peg, despite defining the latter as the central object of the paper. Their own calibration event is a counterexample to their conclusion: USDC traded at approximately $0.86 while primary-market redemption was severely constrained. A market-price peg had plainly broken without issuer reserve exhaustion. The distinction between secondary-market selling and primary-market redemption is neither theoretically novel nor an empirical discovery; it is a basic institutional feature of redeemable stablecoins. Moreover, the two mechanisms are not independent. Secondary-market discounts induce arbitrage and redemption whenever primary-market access becomes available, and redemption can affect secondary prices through circulating supply and the marginal availability of arbitrage capital. The proposed 1992 contrast is similarly misconceived: holders of sterling could sell in the foreign-exchange market without individually transacting with the Bank of England, even though official intervention ultimately absorbed selling pressure. The authors have mistaken a restriction they imposed on their model’s accounting for an economic distinction between the two historical episodes. The claim should not appear as a principal finding.

The narrower claim is valid: secondary-market selling does not mechanically debit issuer reserves at the moment of sale, whereas direct redemption does.

That is a useful distinction to implement correctly. It is not a discovery about what breaks a peg.

4. Theory

First-generation currency crises

The analogy is useful, but the theoretical characterization is too crude.

The authors write:

“The first-generation theory says a peg breaks when the attack exceeds the reserves.”

Not quite.

Krugman’s 1979 model is not simply an accounting exercise in which speculative capital exceeds reserves. It concerns an inconsistent macroeconomic policy regime, reserve depletion under that regime, and an anticipated speculative attack that occurs before reserves would otherwise be exhausted.

Flood–Garber makes the timing of the attack explicit, including the relationship between the fixed exchange rate and the shadow floating rate.

The distinction is important: the model’s attack is exogenously scheduled, whereas the timing of the attack is an equilibrium object in the canonical theory.

The note’s comparison:

“A ratio of attack to resources of 1.04, within 4% of the first-generation formula.”

is not a meaningful validation of first-generation theory. Near equality between a modeled attack stock and modeled absorbing resources follows largely from the simulator’s conservation mechanics.

It does not reproduce Krugman’s crisis mechanism.

I would describe this as a finite-inventory price-defense model inspired by first-generation currency-crisis theory, rather than an implementation or confirmation of that theory.

Second-generation currency crises

The paper invokes Obstfeld but does not model the defining mechanism.

The authors acknowledge:

“The defender has no cost function and never gives up.”

That single sentence rules out the central second-generation mechanism.

In Obstfeld’s framework, the government’s decision to maintain the peg depends on the endogenous cost of defending it. Market expectations can alter that cost, creating the possibility of multiple equilibria.

Here, the defender executes a programmed policy until its budget is depleted or the simulation stops.

There is no endogenous abandonment decision, no political or output cost of raising interest rates, and no equilibrium selection.

The absence matters particularly because the 1992 crisis is most interesting as a contest over British policymakers’ willingness to continue defending an exchange-rate commitment under domestic economic pressure.

The authors do not need to implement a full Obstfeld model. They do need to stop presenting their current model as evidence about that mechanism.

Reflexivity

The authors write:

“In the model, liquidity providers who flee a depeg and sit on what they withdrew take the attacker’s stablecoin out of the venue with them.”

This is a conditional inventory-transfer result, not a general test of Soros-style reflexivity.

Reflexivity requires a feedback between market behavior and the fundamentals or policy choices that participants are evaluating. Soros’s 1992 account concerns selling pressure, interest-rate defense, deterioration in economic conditions, and diminishing policy credibility.

The modeled LP reacts to price, removes inventory, and then becomes inert. It cannot create the most obvious adverse feedback because it is expressly prohibited from disposing of its inventory.

The experiment therefore tests a particular mechanical response to a price signal. It does not establish that liquidity flight is stabilizing in an economic system with adaptive agents.

This is a legitimate result about that agent specification, but the claimed implication for reflexivity is unwarranted.

Is the 1992 analogue doing analytical work?

Very little. I would remove it from the results and retain 1992 in the introduction as intellectual motivation.

The authors write:

“The model’s Black Wednesday needs the convergence traders.”

This has not been established historically.

The simulated threshold moves from 5.7× Quantum without believers to 4.9× with believers sized at 0.9× the attacker. That is a comparative static inside the model.

It does not show that convergence traders caused sterling’s exit from the ERM, that their aggregate positions had the imposed size, or that they corresponded to the arbitrage and redemption behavior of stablecoin traders.

More fundamentally, the model replaces the Bank’s interest-rate decisions with a redemption spread:

“The two rate rises as a redemption spread of 200 bps…”

A policy-rate increase affects the return to holding sterling, the cost of borrowing sterling, the term structure, and economic activity. A redemption fee does not reproduce those channels.

Even the sign of the incentive is not generally equivalent.

The numerical 1992 experiment therefore cannot explain the 1992 decision to abandon the peg. It demonstrates that an assumed intervention budget and redemption mechanism can eventually be exhausted.

This is not an argument for building a large macroeconomic model. The current model can still answer a narrower on-chain microstructure question. The authors should simply stop treating its artificial 1992 environment as an empirical analogue with explanatory force.

Is “two exits” a genuine correction?

It corrects the authors’ initial mapping, not the currency-crisis literature.

The authors write:

“In 1992 a holder of sterling who lost faith had one way out: sell to the Bank at the floor…”

That is historically and institutionally misleading. Sterling traded in a decentralized foreign-exchange market with many counterparties. Official support of the ERM floor was a commitment to intervene, not a requirement that every exiting holder transact directly with the Bank of England.

The comparison also obscures the mechanism that makes stablecoin arbitrage work. Secondary-market purchasers with primary-market access can convert discounted tokens into redemption claims, transmitting selling pressure from the venue to the issuer.

The primary/secondary distinction is important. The assertion that stablecoins have two exits whereas sterling had one is not.

Finally, Diamond–Dybvig belongs here principally as a theory of liquidity transformation, coordination, and incentives to run. The model has no endogenous expectations or depositor coordination. Its fixed redemption queue is a useful representation of constrained payout capacity, but not a Diamond–Dybvig equilibrium.

5. Method

The following choices require justification, correction, or sensitivity analysis before publication. Several are acceptable abstractions individually. Their interaction is the problem.

A. Identification and empirical design

1. One event for specification, calibration, and validation. The authors concede, “One event; one venue standing in for all venues.” The same March 2023 event influences the model’s structure and determines its key parameters. There is no independent test. The minimum correction is to call this an in-sample historical replay and reserve the word validation for an independent prediction.

2. A fitted D* with no independently measured aggregate depth. The note says, “Pool depth is anchored to the Curve 3pool’s USDC leg.” In fact, D* is approximately 16.7 times that leg, representing $3.91 billion per side. That multiplier is inferred, not observed. It is economically decisive and should be reported as a model calibration, not a market measurement.

3. A constant-product AMM representing Curve and the wider USDC market. The note specifies, “A constant-product pool of stablecoin against a reference asset.” Curve 3pool uses the StableSwap invariant, which deliberately produces different price-impact behavior from . Centralized exchanges use order books, and their depth is not captured by simply multiplying AMM reserves. I would accept a constant-product pool as a stylized experiment, but not the present claim of having calibrated its price impact to Curve without demonstrating equivalence over the relevant trade sizes.

4. Net supply contraction as gross selling pressure. The authors write, “The attacker is sized to the episode’s net USDC burn, $2.71B.” Net supply reduction is not net selling into exchanges, and neither is total gross sell volume. Those quantities are linked through arbitrage and issuance/redemption but are not identical. This is especially serious when the missing buyer’s capital is inferred from the resulting modeled imbalance.

5. Attacker pacing fitted to the observed trough. The note acknowledges fitting “the attacker’s pace.” The internal record specifies 0.2% of remaining inventory every 12 seconds. This creates a declining geometric execution schedule, not a constant-rate sale. Both that execution rule and its calibration to the observed timing need justification.

6. The observed price used as the model’s reference price. The authors write, “Fed the observed USDC/USD series as its reference.” This is the clearest source of outcome leakage. The decisive test is a replay with an independently specified dollar reference, ideally fixed at $1 for the relevant experiment, and no use of the observed USDC price except for evaluation. It requires changing an input, not expanding the model.

7. Incommensurable price observations. Figure 1 compares “Observed hourly closes” with “the simulated venue price.” The former is a sampled transaction-based price; the latter is an instantaneous AMM spot price. The model should be sampled at identical observation times and with a comparable pricing convention. In particular, an intrahour minimum cannot be directly validated against an hourly close.

8. The nine-minute timing claim exceeds the data’s resolution. The note reports a simulated trough “within nine minutes.” The observed trough is identified from hourly closes. The exact intrahour trough time is not established by that series. The result is within the observed trough hour, not independently validated to nine-minute accuracy.

9. Joint parameter identification. The authors write, “Three numbers are fitted, each to one observation by a stated rule.” The implication that three separate fitting rules provide three independent pieces of information is incorrect. D*, C*, and pace interact. They should report a joint objective function, parameter trade-offs, and the range of combinations capable of reproducing the trough. A single best-fitting triple does not establish identification.

10. Selection of the entry-price ladder. The authors acknowledge, “one of three fixed ladders we tried.” The internal tables show different outcomes for all three. The selected ladder moves the trough closer to the observed one. The three alternatives and their complete outcomes belong in the manuscript, with the selection explicitly counted as part of calibration.

11. Arbitrary buyer entry prices and demand elasticity. The selected discounts are 2%, 5%, 10%, and 20%, equally weighted. There is no evidence that real aggregate demand was concentrated at those levels. The resulting staircase is generated by the assumed discrete reservation prices. A continuous demand schedule would be an inexpensive robustness check within the current model.

12. Believer capital versus cumulative purchases. The note says the believer “buys below an entry discount” and “redeems whenever the queue is clear.” The internal record shows that redemption proceeds are recycled into additional buying. The relationship between initial capital, gross purchases, net inventory, and cumulative redemption needs explicit accounting. Otherwise C* is easily misinterpreted as the amount of independent capital simultaneously supporting the market.

13. The believer’s buying rate and redemption privileges. The internal validation specifies purchases at 5% of remaining capital per step and redemptions when the queue is available. Those choices affect the trough and the amount of capital recycled. A real buyer’s redemption eligibility, expected settlement delay, credit risk, and opportunity cost would also affect willingness to buy. The authors do not need strategic agents to test sensitivity to these quantities.

B. Market-clearing and issuer mechanics

14. The arbitrageur’s valuation rule. The note states, “An arbitrageur buys on the venue when the price is below the oracle by more than fees and redeems.” Why should a trader with an enforceable $1 redemption claim use the observed secondary-market USDC price as its reservation value? Redemption value, redemption uncertainty, delay, transaction costs, and queue access belong in that decision. The chosen oracle-based rule is central to the output leakage.

15. Redemption throughput inferred from an inappropriate window. The note says the redemption channel is calibrated “to the weekend’s observed capacity.” The internal record reveals that the slow capacity comes from the average net burn over March 11–15, including Monday’s reopening and subsequent catch-up. That is not an observation of weekend capacity. It systematically risks overstating how much the issuer could actually pay during the closure.

16. The artificial Monday capacity jump. The replay changes capacity to an amount sufficient to process the modeled reserves in one day. The authors write that “on Monday banks reopened and redemptions resumed.” The capacity schedule needs to be based on actual post-reopening throughput, rather than a convenient acceleration imposed at a known historical event time.

17. Queue discipline and the distinction between redemption requests and completed settlements. The model says “the issuer pays par, less a spread, from reserves, through a queue.” It should specify who enters the queue, how priority works, how the holder and arbitrageur compete for capacity, and whether queued requests can be canceled. This matters directly to the alleged throughput result.

18. Circle’s cash share treated as an AMM-defense budget. The authors acknowledge that the calibrated baseline contains “the issuer’s own buying,” although Circle did not perform that role in the historical replay. Cash backing reserves and discretionary market-intervention budgets are not equivalent economic resources. The baseline fit of D* therefore requires reconsideration.

19. No government backstop or external credit support. The model has no lender of last resort. That is acceptable for a model of an isolated stablecoin, but not innocuous when the principal validation event was resolved following the US government’s protection of SVB depositors. The actual news changed the perceived value and accessibility of the redemption promise. The replay imposes a capacity change without modeling the intervention that helped restore confidence.

20. The defense policy has no abandonment or welfare criterion. The note acknowledges that “the defender has no cost function and never gives up.” This prevents claims about optimal defense, credibility, or the economic logic of Black Wednesday. An endogenous government cost function is unnecessary if the authors limit their claim to comparing fixed execution rules. It becomes necessary only if they insist that those rules explain a policymaker’s decision to surrender a peg.

C. Policy experiments and simulations

21. A policy comparison in which all defenders spend everything. The authors write, “Every buying defender spends its whole budget.” This reduces the experiment principally to a comparison of execution prices. It does not evaluate policies with different expenditure totals, contingencies, or terminal inventory values.

22. The attack overwhelms every intervention threshold immediately. The note says, “The attacker’s first sale puts the price near $0.23, which crosses every trigger up to 4% on the first step.” That is a model of a market already suffering a 77% instantaneous collapse. It cannot meaningfully identify the merits of intervention thresholds near par. The finding that the trigger does nothing is largely built into this shock design.

23. No cost of allowing the peg to collapse while waiting. The recommendation to spend slowly is judged chiefly by eventual re-entry and how many tokens the budget buys. There is no explicit penalty for the interim discount, resulting liquidations, depositor flight, reputational damage, or abandonment of the promise. Those costs are central to the actual defense problem. Without them, purchasing assets after a crash will predictably look attractive.

24. The attacker cannot adapt to the defense. The model specifies, “An attacker sells a fixed stock of stablecoin at a pace.” It does not choose when to attack in response to observed defense, optimize execution, withhold inventory, or adjust to buyer demand. That is acceptable for a stress test. It is not a strategic speculative-attack model in the Obstfeld sense.

25. The liquidity provider’s behavior after withdrawal. The note acknowledges, “The liquidity provider holds what it withdraws.” In the internal results, the LP acquires a large amount of stablecoin after the dump and then becomes inert. The result that liquidity flight helps the defender depends on precisely this restriction. The authors correctly identify this qualification, but its prominence in §7 still overstates generality. Testing redemption or resale of withdrawn inventory is essential before making conclusions about liquidity flight.

26. The timing of the liquidity withdrawal. The LP responds after the price-moving sale. This ordering makes it difficult for withdrawal to deepen the same sale’s trough. The nine-phase sequence is therefore an economic assumption, not merely a software implementation detail. The authors must show whether the result survives alternative execution orderings.

27. The recovery definition. The paper defines recovery as holding within ±31 bps for 6,900 steps in a 60-hour horizon. The choice effectively creates a 37-hour deadline for first re-entry. Neither the band nor the 23-hour persistence requirement follows from first-generation crisis theory. The authors should distinguish first re-entry, sustained recovery, and terminal survival and demonstrate robustness across reasonable horizons.

28. The calm reference’s mean-reversion fit. The note states, “The calm reference price reverts to par with a half-life of 1.4 h, fitted from the calm USDC series.” This is another empirical fit that affects the recovery criterion. The calibration period, uncertainty, stationarity assumption, and sensitivity to alternative reference processes should be reported. The exact agreement of first re-entry times under two processes is interesting but not a substitute for those checks.

29. Combining calm and stress scenarios in general conclusions. The limitations acknowledge, “Stress-volatility surfaces were run under the random-walk reference, calm ones under the reverting one.” The comparisons should make clear which findings are structural and which are conditional on the reference regime. In particular, the claim that time to parity is reference-independent should be confined to the reported sweeps, not generalized.

30. Oracle-lag sensitivity tests only a restricted transmission mechanism. The note concludes, “Oracle lag is not a depeg risk factor at Chainlink’s settings.” In the model, oracle lag matters principally through one arbitrageur’s trading condition. Other oracle-dependent liquidation, collateral, and risk-management mechanisms are absent. A null result for this particular arbitrage rule is not evidence of general oracle safety.

31. Monte Carlo interpretation. The paper calls the simulator deterministic but reports probabilities and results such as “11 of 16 seeds.” This is not inherently contradictory: a deterministic simulator can be run with multiple seeded stochastic reference paths. But the authors should specify which shocks vary, how runs are sampled, how non-recovery cases enter median calculations, and provide uncertainty intervals. A difference between 11/16 and 0/16 is informative in that scenario, but sixteen replications provide limited precision.

32. The 1992 parameterization. The authors write, “Quantum’s position as the attacker’s unit.” Neither Quantum’s position nor the Bank’s war chest uniquely determines the aggregate speculative pressure, intervention flow, available credit, or effective exchange-market liquidity. The 4.9× threshold is therefore a simulation threshold, not an estimated historical crisis threshold.

What I would actually require

I would not demand an elaborate new agent-based model, a calibrated macroeconomic government, or a full network of decentralized exchanges.

Before publication, I would require four tests using the existing architecture: remove the observed-price oracle input; replace the net-supply proxy with defensible selling-flow assumptions; show joint sensitivity to D*, C*, and entry-price distributions; and evaluate defense policies using an explicitly stated objective that accounts for temporary peg failure.

The present model is capable of answering those narrower questions. The authors have mostly chosen not to ask them.

6. Facts

I distinguish wrong, misleading, and check. A request to check is not an allegation of error.

I reviewed the factual claims against the supporting documents and, where appropriate, outside sources. The most consequential external checks are the Bank of England’s contemporary record, Circle’s March 2023 disclosures, Curve’s documentation, and Federal Reserve research published in 2024 and 2025.

A. The research note

1. Wrong — two interest-rate increases.

“On 16 September 1992 the Bank of England spent its reserves and raised rates twice in a day to keep sterling inside its ERM band, and lost.”

The rate was increased from 10% to 12%. A further increase to 15% was announced but never implemented. The sentence also risks implying that the Bank exhausted its reserves, which it did not. The Bank of England’s own history and monetary-policy records establish the sequence.

2. Wrong — reserve transparency.

“They also have things 1992 did not: public reserves, an automated market maker whose price impact is exact, an oracle, and a redemption channel with a throughput limit.”

For a fiat-backed coin such as USDC, token supply is visible on-chain, but custody-bank deposits, Treasury holdings, and operational access to those assets are not continuously visible on-chain. Reserve attestations and disclosures are different from publicly observable reserves. Circle’s reporting practices make that distinction clear.

3. Misleading — exact AMM price impact.

The same sentence describes “an automated market maker whose price impact is exact.”

Price impact is deterministic conditional on the invariant, reserves, fees, transaction ordering, and pool state. The note uses a constant-product invariant even though Curve 3pool uses StableSwap. Exact calculation under the wrong invariant is not exact representation of the historical venue.

4. Wrong as an empirical classification — net burn equated with selling.

“The attacker is sized to the episode’s net USDC burn, $2.71B.”

The observed reduction in circulating supply is not a measurement of gross selling pressure during the crash. It is a stock change reflecting issuance and redemption activity over the selected dates. Federal Reserve research explicitly measures primary issuance and redemption separately from secondary-market trading.

5. Check — the assumed absence of Circle market buying.

“Without an issuer buying on venues (Circle did not)…”

I know of no evidence that Circle conducted a discretionary exchange-market defense during that weekend, and the statement is plausible. But the assertion that it did not trade anywhere should be supported by issuer disclosures or narrowly qualified as no publicly documented intervention.

6. Check — the Chainlink settings.

“The oracle to Chainlink’s USDC/USD feed (0.25% deviation, 82,800 s heartbeat)…”

These parameters are consistent with published feed specifications. The authors must nevertheless establish that they describe the particular feed, chain, and historical configuration being calibrated. A current feed configuration is not automatically evidence of its March 2023 settings.

7. Wrong as a general conclusion — oracle lag.

“Oracle lag is not a depeg risk factor at Chainlink’s settings.”

The simulations establish only that the modeled arbitrageur’s behavior is largely insensitive to the tested update settings. They cannot establish that oracle lag is generally irrelevant to depegs, particularly when oracle-dependent liquidations and collateral mechanisms are absent.

8. Misleading — the reserve constraint.

“At issuer scale the reserves cannot run out; the clock can.”

Reserves do not run out under the modeled attack sizes, capacity constraints, and horizon. The statement is not a general property of issuer-scale stablecoins. It should say that reserves are not exhausted in these experiments.

9. Misleading — the timing of the historical trough.

“The trough is −1,323 bps at 31.2 h against −1,373 at 31.0 h: within 4%, and within nine minutes…”

The numerical comparison is internally consistent, allowing for rounding. The empirical time resolution is not. The observation is an hourly close, so the nine-minute precision should not be presented as empirically verified.

10. Wrong — sterling’s only exit.

“In 1992 a holder of sterling who lost faith had one way out: sell to the Bank at the floor — which is, in the model’s terms, a redemption.”

Sterling holders could transact through the foreign-exchange market with other private counterparties. The Bank’s obligation to defend the ERM floor was not a direct redemption obligation owed to every sterling holder.

11. Wrong — only redemption breaks a peg.

“Only the second breaks the peg.”

This contradicts the note’s own definition and historical example of a market-price depeg. The second mechanism drains issuer reserves. It is not the only mechanism through which a market-price peg can fail.

12. Check — the historical interpretation of convergence traders.

“The 1992 account says the peg broke when the convergence traders ‘switched sides.’”

Convergence-trade unwinding is a credible part of the historical interpretation. But the amount, timing, and net currency exposures of these positions need sourcing before they can support the quantitative role attributed to them. They should not be identified with the simulator’s believer-redemption flow without evidence.

13. Check — the size of the fitted aggregate market.

“Pool depth is anchored to the Curve 3pool’s USDC leg…”

The figures imply approximately $235 million in the observed leg and $3.91 billion per side after fitting. The precise pool snapshot, block number, date, composition, and price-impact conversion should be supplied. A token reserve balance is not itself a measurement of effective trading depth.

14. Check — the claimed literature comparison.

“A game-theoretic treatment of stablecoin attacks (Gupta & Gupta 2025) names the critical attack fraction this model computes…”

The Gupta and Gupta paper exists, but it is a three-page 2025 article. The authors must identify the exact proposition or equation they are comparing with their own result. The fact that both papers discuss critical attack conditions is not sufficient to establish equivalence.

15. Verified, but needs a proper citation — StableEval Arena.

“StableEval Arena (Wan, Liu & Zhang 2026) reports that LLM-backed peg-risk agents ‘still miss most rare severe-stress and sustained-depeg cases.’”

The paper exists and its abstract supports this characterization. It is nevertheless an unusual benchmark for a currency-crisis/microstructure paper: predictive performance by LLM agents is not the main standard against which this deterministic simulator should be evaluated.

16. Check — September 2026 USDe comparison.

“Ethena’s USDe single-venue print of September 2026…”

Contemporary reports describe a September 22, 2026, Binance-specific fall near $0.92 followed by a rapid recovery. That is consistent with the description, but an exchange trade record and contemporaneous cross-venue prices are necessary if the authors want to use it as a validation event.

B. The USDC background

17. Misleading — the completeness of the data.

“The price on every venue, the token supply day by day, the issuer’s statements, the reserve breakdown, the government’s response.”

Not every historical execution, order-book state, OTC transaction, or private trading intention is publicly available. The market is relatively data-rich, but the missing data are precisely those needed to identify the modeled believers’ capital and demand schedules.

18. Check — the claim that the issuer was solvent.

“March 2023 was a bank run on an issuer that turned out to be solvent but could not prove it, or pay out, until the banks reopened.”

Ex post, Circle received the benefit of the government’s protection of SVB deposits. Ex ante, those deposits were uninsured and a shortfall was possible. The Federal Reserve’s 2025 retrospective explicitly identifies both potential solvency and liquidity concerns. The statement should distinguish realized solvency after government intervention from the counterfactual position without it.

19. Check — the categorical absence of an attack.

“Nobody attacked USDC.”

The episode was predominantly a run rather than a documented coordinated speculative attack. That does not establish that no participant deliberately traded to profit from or exacerbate the dislocation. State what is known: there was no identified Soros-style coordinated attacker.

20. Misleading — the fate of the three banks.

“So by Sunday all three banks the crypto industry relied on most were gone: Silvergate winding down, SVB and Signature closed.”

Silvergate had announced a voluntary wind-down; SVB and Signature had been closed by regulators. These are distinct states. The broader claim about the industry’s three principal banks also needs support and qualification by business function.

21. Check — the meaning of exchange outflows.

“Outflows of USDC from centralised exchanges peak at about $1.2 billion an hour.”

The relevant Chainalysis source should be cited with its definition of outflow. Transfers out of exchanges are not necessarily sales, net sales, or primary redemptions. They cannot be substituted for the attack-flow input without reconciliation.

22. Wrong as an inference — buyers’ motives identified from the price path.

“We can see that they existed, because the price stopped falling while the selling was still going on.”

The inference that transactions have counterparties is trivial. The price path does not establish that buyers had the specified capital, believed in par, or intended to redeem. Falling selling intensity, liquidity replenishment, arbitrage, and changes in expectations can all affect the path.

23. Misleading — interpretation of the supply decline.

“Every one of those tokens was a customer leaving.”

Net supply contraction is not a count of customers or gross redemptions. Tokens are fungible, and issuance can offset redemptions. A decrease in circulating supply is properly described as a decrease in net outstanding liabilities.

24. Check — DAI’s backing share.

“DAI, then about a third backed by USDC, lost its own peg with it…”

Contemporaneous reports give different proportions—approximately 36% in one account and 54.5% in another—apparently depending on definition and time of measurement. The authors should specify the date and denominator and preferably use MakerDAO’s collateral records.

25. Misleading — the government announcement as the sole cause.

“The Sunday announcement was what ended the run.”

The federal backstop was unquestionably important and was followed by a sharp recovery. But Circle’s commitments and the subsequent restoration of redemptions also affected expectations and prices. The Federal Reserve’s detailed retrospective distinguishes the Sunday rebound from full recovery after primary-market operations resumed.

26. Check — actual recovery duration.

“It recovered.”

This is broadly true, but the authors should specify whether recovery means first return within a tolerance, sustained close to par, or recovery of direct redemption operations. Their own validation record shows the observed series leaving the narrow ±31 bps band again after first re-entry.

27. Misleading — the redemption-capacity calibration.

“Redemption over the weekend, banks closed” mapped to “the observed average burn rate.”

The average is calculated over a longer interval that includes Monday’s catch-up. The internal validation record explicitly warns about this. It should not be described as observed weekend capacity.

C. The Black Wednesday background

28. Wrong — two implemented rate increases.

“On 16 September 1992 the British government spent a large share of its foreign-exchange reserves and raised interest rates twice in one day to keep the pound inside the European Exchange Rate Mechanism (ERM).”

As above: one rate increase took effect, and the second was announced for the following day but canceled. The note should consistently distinguish announced policy from implemented policy.

29. Misleading — reserve capacity as the sole reason for failure.

“The event is the cleanest historical example of a price promise that ran out of capacity under adversarial pressure.”

It is a powerful example of a defended exchange-rate commitment being abandoned under pressure. But Britain did not simply exhaust its ability to purchase sterling. The economic and political costs of continuing were central. The Bank of England’s official history explicitly emphasizes the expense of maintaining the commitment.

30. Wrong as a literal description — one central-bank exit.

“A holder of sterling who lost faith in 1992 had one way out: sell to the Bank of England at the floor, which drained the reserves.”

This repeats the erroneous characterization of the foreign-exchange market. The Bank absorbed pressure through intervention, but private market transactions remained possible.

31. Check — intervention speed.

“The Bank of England bought pounds with its reserves, at times reportedly around £2 billion an hour.”

The source provided does not establish this exact rate from contemporaneous dealing records. The authors themselves flag it as unverified. It should not survive into publication without a primary or reliably documented contemporaneous source.

32. Check — gross intervention spending.

“Gross reserves spent in defending the pound are widely reported as £27 billion, based on the same Treasury papers.”

The authors correctly flag this as needing verification. Gross purchases of sterling, the depletion of reserve assets, trading losses, and the eventual net Treasury cost are different accounting measures. The £3.3 billion estimated net cost is substantially better documented than the precise gross number.

33. Check — Quantum’s position and profit.

“By Black Wednesday the fund was short roughly $10 billion of sterling, and its profit is usually put at about $1 billion.”

These are conventional historical estimates and plausible in magnitude. They should be attributed to a named contemporaneous account or documented fund history, rather than presented as audited transaction-level measurements. The precise position matters because it becomes the unit of the simulated threshold.

34. Check — the causal role of one large player.

“The attack worked because a large, visible actor gave the rest of the market a reason to move together.”

This is one interpretation, related to large-player coordination theory, not a settled historical fact. The model does not test whether Soros coordinated other traders or merely participated in a broader repricing of sterling.

35. Check — the Bath meeting.

“The meeting ended with neither a German rate cut nor a realignment of parities, so the overvalued currencies had no relief and the markets had no reassurance.”

The no-realignment and no-immediate-rate-cut portions are consistent with contemporary reporting. The final inference about reassurance is too categorical: contemporary accounts initially described some relief from Germany’s indication that it would not raise rates further. The outcome should be presented with that nuance.

36. Misleading — German monetary policy mechanically dictated British rates.

“Every currency pegged to the mark had to follow, whatever its own economy needed.”

The ERM constrained domestic monetary policy but did not mechanically force identical rate moves. The Bank of England’s contemporary account notes that UK base rates fell from 15% to 10% during the initial period of ERM membership despite increases in German rates. The constraint became more acute as sterling approached its lower band.

What does not require correction

The essential chronology of SVB’s closure, Circle’s disclosed $3.3 billion exposure, the Sunday federal backstop, and the Monday restoration of USDC operations is supported by primary sources. The same is true of the broad Black Wednesday chronology, sterling’s ERM membership, the failure of intervention, and the abandonment of the commitment.

The draft’s historical problem is not that it has invented the two crises. It is that it repeatedly converts reasonable descriptions of events into sharper mechanistic claims than either the historical records or the simulator establish.

7. Would you read it?

As a referee, yes. As a stranger choosing what to read, probably not to the end.

I would read the abstract and continue into §3 because the claim of an initially failed historical replay corrected by introducing a missing class of buyers is potentially interesting.

I would stop at:

“Fed the observed USDC/USD series as its reference…”

At that point I would look for a careful identification discussion. The note instead proceeds toward:

“The depth of a depeg is set by the attacker against everyone who believes the promise.”

and subsequently emphasizes the fit to within 4%.

That is where I would lose confidence in the empirical argument.

The authors have recognized a potentially important modeling omission, but they have confused correcting that omission with establishing a historical explanation.

The subsequent claims about defense policy and Black Wednesday would not restore my confidence. They become progressively broader while the model’s economic mechanisms remain narrow.

The one change that would most improve the paper

Replace the headline historical-validation claim with one genuinely independent test of the buyer-absorption mechanism.

Keep the current model.

Do not feed the observed USDC price back into the simulation. Calibrate the necessary parameters on separately observed market information or an earlier sample, fixing the specification before examining the target outcome. Then use the March 2023 trough and recovery as an actual test.

If buyer capital and demand schedules cannot be independently identified well enough to do this, the authors should abandon the empirical-validation claim and reposition the work as a computational demonstration of how market depth, finite buyer capital, and constrained redemption interact.

Either approach would be substantially more credible than reporting a fitted trough as validation.

The second route may actually produce the better paper.

The authors have a set of clearly specified experiments capable of illustrating nonlinear liquidity and inventory effects. They should build a paper around the conclusions the experiments can support, rather than fitting a collection of mechanisms into a historical narrative.

8. Verdict

Do not publish in this form.

The manuscript’s central empirical result is in-sample fitting presented as validation, with additional dependence on the observed price series being supplied to the model itself. The defense-policy prescription is not supported outside a restrictive execution experiment, and the 1992 analogy attributes economic meaning to a simulated reserve-exhaustion threshold that lacks a credible historical mapping. The supposedly novel distinction between primary and secondary exits is already established in the literature and is overstated to the point of becoming incorrect. These are not cosmetic defects: they concern identification, causal interpretation, theoretical positioning, and the scope of the principal conclusions. A publishable paper may exist within the current experiments, especially around finite demand, AMM depth, and redemption throughput, but it would require substantially narrower claims, an independent empirical test or explicit abandonment of validation language, and a more accurate treatment of the currency-crisis literature. The authors do not need a larger simulator. They need a better match between the questions they claim to answer and the evidence their existing simulator actually produces.


---

## Part 2 — Dev manager's assessment (2026-10-15, written before Tim's notes)

Short version: **the model is sound; the story written about it overreaches in four places,
and a handful of cheap experiments fix the biggest one.** Take the slip.

### What it gets right, and the dev manager should have caught

1. **"Validation" is the wrong word.** D\*, the attacker's pace and C\* were fitted to the
   same event, the ladder was picked because it fit best, and the match was then called
   validation. That is calibration. The honest claim: *a model with no discount buyer fell
   four times too far; adding one lets it reproduce the event.* That is evidence a mechanism
   was missing, not evidence we identified what it was. The dev manager wrote the framing.
2. **The observed price is fed into the model during the replay.** Known and flagged in
   VALIDATION.md, but the note leaned on the match anyway. The referee's test is the right
   one and cheap: rerun with the reference fixed at $1, feed nothing from the real series,
   see whether the trough still lands near 87 cents. One story.
3. **"Only redemption breaks the peg" is wrong by our own definition.** The peg is the
   market price; USDC broke on the market while redemption was closed. The intended sentence
   was "only redemption drains the issuer." And "in 1992 a holder had one way out" is
   institutionally wrong: sterling traded in a deep FX market; the Bank was the buyer at the
   floor, not the only counterparty. The real point survives (at the floor, net selling
   landed on the Bank's reserves; on-chain, venue selling never touches the issuer) but it
   corrects *our* mapping, not the literature, and is not a headline.
4. **The 1992 analogue is motivation, not a result.** "Within 4% of the first-generation
   formula" is conservation arithmetic inside the model. The 4.9× Quantum threshold is a
   simulation threshold. 1992 moves to the introduction and the "where the analogy breaks"
   section; the replay stops being presented as explaining Black Wednesday.
5. **"Spend slower" is conditional on two unstated things.** The attacker dumps 10% of its
   stock in the first step, so the price is at 23 cents before any trigger matters: "triggers
   are inert" is partly built in. And nothing is charged for sitting at a 70% discount while
   the slow defender waits, so buying the bottom looks free. Fixable: a gentler attacker in
   the policy sweep, and a cost-of-discount metric beside time-to-parity.
6. **Smaller but real:** nine-minute timing precision from hourly data; net supply burn is
   not gross selling; weekend redemption capacity comes from an average that includes
   Monday; constant-product is not StableSwap and "calibrated to Curve" overclaims; C\* is
   initial capital that recycles through redemption; D\* was fitted with a defender active
   and used in a replay with it off (to check).
7. **Facts.** "Raised rates twice" is wrong in the note (15% announced, never implemented;
   BACKGROUND.md has it right). "Public reserves" overstates: supply is on-chain, reserves
   are attested. "Nobody attacked USDC" becomes "no identified attacker." "Every token was a
   customer leaving" is sloppy.

### Where it overstates

- It applies a journal's bar to a 3,000-word public note. The verdict to take is "do not
  publish *these claims*," not "do not publish."
- The Federal Reserve 2024/2025 notes on primary and secondary stablecoin markets are a
  model's recollection. Lead to verify today; if they exist they are the right benchmark and
  we cite them.
- DAI backing share (36% vs 54.5%) and several 1992 nuances: check, not wrong.
- It underweights what is clean. Findings (b) liquidity cost and (d) throughput-not-reserves
  it ranks top and calls "known in theory, shown mechanically." For a small lab's first
  public piece, that is a fine thing to be.

### What the dev manager proposed

Unfreeze for one short epic, four stories on the existing code: (1) par-reference replay;
(2) joint D\* × C\* surface and all three ladders reported; (3) policy sweep with a gentler
attacker plus a cost-of-discount metric; (4) an LP that dumps or redeems what it withdrew.
Then rewrite the note: "replay," not "validation"; findings ranked the referee's way
(throughput, liquidity, believers, pace, exits); 1992 as frame; every "cannot" narrowed to
"did not in these experiments"; the fact fixes. Re-freeze ~Oct 26, note v2 ~Oct 30,
hostile-referee pass on v2, publish mid-November.

The numbers were never the problem; every number reproduces. What did not hold up was the
distance between the numbers and the sentences wrapped around them.

---

## Part 3 — Tim's decision (2026-10-15)

- The first-run work stands; the outside read is how we improve it before others see it.
- One epic added. Timeline re-evaluated; the final date moves, the project does not slip.
  "A better product on first launch is just that: a better product."
- Tim's own correction, recorded at his request: he pushed the 1992 event harder than it
  deserved as the project went on. It was the launching point and gave the model its
  question; it should not have been enforced as core to the results. The principle "the
  analogy is a tool, not a thesis" (2026-10-06) was right and is now applied to the note.
- Tim will look for additional human readers (Twitter). The trader and hostile-referee
  prompts still to be run.
- This document and the review pack stay in the repo.

---

## Part 4 — Disposition of every point

Legend: **wording** = fix in the note/backgrounds; **experiment** = new story (Epic 5);
**verify** = check at the primary before use; **disagree** = we keep it, with reason.

| # | Referee point | Disposition | Where |
|---|---|---|---|
| §1 | In-sample calibration presented as validation | wording + experiment | note §3 rewrite; 5.1 |
| §1 | Observed price fed as reference | experiment | 5.1 |
| §1 | Ladder selection is model selection | wording | note §3 reports all three ladders |
| §2 | Ranking: (d) > (b) > (a) > (c) > (e) | wording | note restructured in that order |
| §2/§3 | "Only redemption breaks the peg" false by own definition | wording | note §7: "drains the issuer"; demoted from headline |
| §3 | 1992 "one exit" institutionally wrong | wording | note §7, BACKGROUND §"Where the analogy breaks" item 7 |
| §2 | Fed 2024 note on primary/secondary markets | verify | LITERATURE.md lead L-10 |
| §4 | First-gen characterisation crude; 1.04 ratio is conservation | wording | note §1, §7: "finite-inventory defence model inspired by…" |
| §4 | Second-gen mechanism absent; don't present as evidence about it | wording | note §1, §8 |
| §4 | LP result is not a reflexivity test | wording + experiment | note §7; 5.4 |
| §4 | 1992 analogue has no explanatory force | wording | 1992 to intro + "where it breaks"; Figure 5 to record |
| §5.1 | One event for spec, calibration and validation | wording | "replay" throughout |
| §5.2 | D\* is a calibration, not a measurement | wording | note §3 |
| §5.3 | Constant-product ≠ StableSwap | wording | note §2, §8; SOURCES.md note |
| §5.4 | Net burn ≠ gross selling | wording | note §3 |
| §5.5 | Attacker pace fitted; geometric schedule | wording | note §3 |
| §5.6 | Observed price as reference | experiment | 5.1 |
| §5.7–8 | Hourly close vs instantaneous spot; nine-minute claim | wording | note §3: "within the observed trough hour" |
| §5.9 | Joint identification of D\*, C\*, pace | experiment | 5.2 |
| §5.10–11 | Ladder selection; discrete reservation prices | wording + experiment | note §3; 5.2 adds a continuous-demand check if cheap |
| §5.12–13 | C\* recycling; believer pace/eligibility | wording | note §3 states gross buying vs capital |
| §5.14 | Arbitrageur's valuation rule anchors to oracle | experiment | 5.1 (par reference removes the anchor) |
| §5.15–16 | Weekend capacity from 11–15 average; Monday jump | wording | note §3, USDC-2023.md mapping table |
| §5.17 | Queue discipline unspecified | wording | note §2 one sentence; README |
| §5.18 | D\* fitted with defender active, replay without | verify + wording | check fit_depth inputs; disclose |
| §5.19 | No government backstop | wording | already in §8; sharpen |
| §5.20 | No abandonment criterion | wording | note §5, §8 |
| §5.21–23 | Policy comparison: all spend everything; shock design makes triggers inert; no cost of interim discount | experiment | 5.3 |
| §5.24 | Attacker cannot adapt | wording | note §8 |
| §5.25–26 | LP holds inventory; phase order is an economic assumption | experiment + wording | 5.4; note §7 |
| §5.27 | Recovery definition creates a 37 h deadline | wording | note §2 states it |
| §5.28–29 | OU fit uncertainty; calm vs stress regimes | wording | note §2, §8 |
| §5.30 | Oracle null is for one arb rule only | wording | note §6 narrowed |
| §5.31 | Monte Carlo: 16 seeds, what varies | wording | note §5 |
| §5.32 | 1992 parameterisation | wording | 1992 demoted |
| §6.1, 28 | "Raised rates twice" | wording (wrong) | note §1, BACKGROUND short version |
| §6.2 | "Public reserves" | wording (wrong) | note §1 |
| §6.3 | "Exact price impact" | wording | note §1 |
| §6.5 | Circle did not buy: qualify | wording | "no publicly documented intervention" |
| §6.6 | Chainlink settings as of March 2023 | verify | SOURCES.md |
| §6.7–8 | Oracle and reserves generalisations | wording | note §4, §6 |
| §6.14 | Gupta & Gupta: name the proposition | verify | LITERATURE.md L-4 |
| §6.15 | StableEval Arena is an odd benchmark | wording | keep one line, reframe as "why mechanistic" |
| §6.17–27 | USDC background: data completeness, solvency ex post, "nobody attacked", three banks, $1.2B/h definition, buyers' motives, "customer leaving", DAI share, Sunday as sole cause, recovery definition, capacity | wording + verify | USDC-2023.md |
| §6.29–36 | 1992 background nuances | wording + verify | BACKGROUND.md |
| §7 | Headline change: independent test or reposition as computational demonstration | experiment then decide | 5.1 decides which |
| §8 | "Do not publish in this form" | accepted as "not these claims" | Epic 5 + note v2 |

### Lessons recorded in PROCESS.md

- **L-18** Run the outside review *before* the freeze, not after it. One model pass costs an
  hour and would have reshaped Epic 3's last stories.
- **L-19** A fitted number is not a prediction. The word "validation" is reserved for a test
  whose target was not used in fitting. Everything else is "replay" or "calibration."
- **L-20** The frame stays in the introduction. If a historical analogy appears in a results
  section, ask what experiment it is reporting; if the answer is "none," move it.
