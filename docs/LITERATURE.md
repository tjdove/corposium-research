# LITERATURE.md — lead log for the research note's related work

Every outside source anyone has pointed at, with its claim, how it reached us, whether we
have verified it, and which finding it touches. The note's related-work and next-questions
sections are written from this file. **Nothing is cited in the note until its status is
`verified`** (dev manager has read the primary source and confirmed the claim).

Status values: `unverified lead` · `verified` · `not found` · `rejected`.

| # | Source | Claim as relayed | Reached us via | Status | Touches |
|---|---|---|---|---|---|
| L-1 | Krugman (1979); Flood & Garber (1984) | First-generation crisis: attack timing follows from reserve drain | Tim, BACKGROUND §5 | verified (BACKGROUND) | F-02, F-06 |
| L-2 | Obstfeld (1994, 1996) | Second-generation: self-fulfilling crises, cost of defending | Tim, BACKGROUND §5 | verified (BACKGROUND) | F-07, F-08 |
| L-3 | Morris & Shin (1998), "Unique Equilibrium in a Model of Self-Fulfilling Currency Attacks" | Global games: a critical mass of attackers set by private signals | Muse relay 2026-10-04 (as background to L-4) | unverified lead (well-known paper; dev manager to confirm the citation and its fit) | F-08, F-09 (belief distribution) |
| L-4 | Gupta, A. & Gupta, G. (2025). "Stablecoin Economics and Speculative Attacks: A Game-Theoretic Approach." *IJSR* 14(2), DOI 10.21275/SR25215203310. [PDF](https://www.ijsr.net/archive/v14i2/SR25215203310.pdf) | Critical attack fraction γ\*: the share of participants whose simultaneous dumping/redemption collapses the peg; set by reserve backing, redemption clarity and speed, confidence, governance-token value, reserve transparency. Builds on KFG, Obstfeld, Morris–Shin; cases USDC, DAI, Terra | Muse relay 2026-10-04; primary located by Muse 2026-10-05; dev manager read the primary 2026-10-04 | **verified**. Caveat: IJSR is a low-prestige venue and the authors are a company CEO and intern; cite as "one recent synthesis," not as the authority. The value is the framing (γ\* as the object), not the derivation | F-02 (γ\* is our capital-vs-resources ratio), F-06 ("redemption speed" is our throughput term), F-08/F-09 (confidence = the holder's belief) |
| L-5 | Renmin University FinTech Institute, LLM-agent depeg simulation; reportedly *Journal of International Money and Finance*; phrase "cognitive depegging". Secondary: [TechFlowPost 2026-09-07](https://www.techflowpost.com/en-US/newsletter/135216) | Threshold dynamics: arbitrage absorbs moderate narrative pressure; past a severity line the system cascades (fear → thinning liquidity → retail selling → arbitrageur withdrawal); at top severity the story's content stops mattering | Muse relay 2026-10-04; Muse found only the secondary 2026-10-05 | unverified lead — **secondary only**; primary title/DOI not yet pinned. Search ScienceDirect for "cognitive depegging" before Epic 4 | F-08/F-09 (belief threshold); the "arbitrageurs pull out" step is the F-07/1992 switch-sides mechanism; a shock-intensity sweep is out of scope before Nov 1 |
| L-6 | Wan, S., Liu, D. & Zhang, L. (2026). "StableEval Arena: A Cost-Aware Agentic Benchmark for Stablecoin Price Stability Prediction." [arXiv:2609.18949](https://arxiv.org/abs/2609.18949) | Six LLM-backed agent configurations on 120 stress-enriched + 507 natural cases over a hidden 7-day horizon: "agents reliably produce valid structured outputs at modest measured cost, but still miss most rare severe-stress and sustained-depeg cases" (abstract, verbatim) | Muse relay 2026-10-04; primary located by Muse 2026-10-05; dev manager read the abstract at arXiv 2026-10-04 | **verified** (abstract). Read the body before Epic 4 for how they define "sustained depeg" — it may be a usable external definition for our recovery criterion | Positioning: predictive agents fail exactly on the sustained-depeg cases a mechanistic, replicable simulator is built to explain. One paragraph in the note's framing |
| L-7 | USDe, 2026-09-22: ~8% drop to $0.92 on Binance, recovered within minutes; ~$8M sell into a thin book while deep pools stayed calm | A venue-microstructure depeg, not a reserve one; a test of the oracle module (heartbeat + deviation, multi-venue, TWAP) | Muse relay 2026-10-02 (Tim's suggestion) | unverified lead; event is recent and should be easy to source (exchange data, Ethena statement) | F-05 (single-venue limitation), F-10 (oracle lag irrelevant under deviation triggering — this case needs a *venue* price feeding the oracle, which the model does not have). Next-questions section, not Nov 1 scope |
| L-8 | Abracadabra / MIM, 2026-09-30: liquidation at ~$0.04/token against ~$21M unbacked debt | Insolvency is a different chapter from attack/liquidity mechanics | Muse relay 2026-10-02 | unverified lead | Taxonomy paragraph in the note: attack vs liquidity vs insolvency |
| L-9 | "June research synthesis on the USDC 2023 depeg" — four-scenario stress library; time-to-parity as headline metric | Time-to-parity | Muse relay 2026-10-02 | **not found**: Muse searched the briefs folder, workspace, memory and Open Brain 2026-10-05 — no such document exists; the Oct 1 briefing links only L-4/L-5/L-6. Possibly a conflation with L-4's USDC case. Treated as **our own** idea unless a source turns up | F-11 still stands on its own data; "time-to-parity" is a good name for `steps_to_sustained_recovery` in the note regardless |

## Open requests

- ~~Tim / Muse: the URLs behind L-4, L-5, L-6, L-9.~~ Done 2026-10-05 (Muse): L-4 and L-6
  primaries found and verified; L-5 secondary only; L-9 does not exist.
- Muse: the L-5 primary (JIMF; try "cognitive depegging" on ScienceDirect).
- Dev manager: confirm L-3 citation; read L-6's body for its "sustained depeg" definition;
  source L-7 and L-8 from primary reporting before the note's taxonomy paragraph (Epic 4).

## Change Log

- 2026-10-04: Created by dev manager after reviewing Open Brain `[muse-ops]` relays; L-1/L-2 lifted from BACKGROUND; L-3–L-9 logged as leads.
- 2026-10-05: Muse located primaries; dev manager verified L-4 (full PDF) and L-6 (abstract) at source; L-5 secondary only; L-9 not found.
