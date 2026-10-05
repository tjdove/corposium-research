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
| L-4 | "Gupta & Gupta (2025)" — peg-attack model on the crisis literature; critical attack fraction γ\* set by reserve ratio, redemption friction, backstop value | γ\* is the share of participants dumping/redeeming that breaks the peg | Muse relay 2026-10-04, from a 2026-10-01 briefing "The Depeg Sim's Blueprint" | **not found** on first search 2026-10-04 (no arXiv/SSRN hit); needs a URL from the briefing before it can be used | F-02 (γ\* ≈ capital/resources), F-06 (redemption friction = throughput) |
| L-5 | Renmin University FinTech Institute, LLM-agent depeg simulation | Threshold dynamics: arbitrage absorbs moderate narrative pressure; past a severity line the system cascades; at top severity the story's content stops mattering | Muse relay 2026-10-04 | unverified lead; needs a URL | F-08/F-09 (belief); suggests a shock-intensity sweep — out of scope before Nov 1 |
| L-6 | "StableEval Arena" benchmark (announced Sept 2026) | LLM peg-risk agents miss rare severe-stress and sustained-depeg cases; replicable simulation tooling is the thin part of the field | Muse relay 2026-10-04 | **not found** 2026-10-04; nearest real item is CryptoBench (arXiv 2512.00417), a general crypto-agent benchmark, not a depeg arena | positioning of the artifact; do not cite until found |
| L-7 | USDe, 2026-09-22: ~8% drop to $0.92 on Binance, recovered within minutes; ~$8M sell into a thin book while deep pools stayed calm | A venue-microstructure depeg, not a reserve one; a test of the oracle module (heartbeat + deviation, multi-venue, TWAP) | Muse relay 2026-10-02 (Tim's suggestion) | unverified lead; event is recent and should be easy to source (exchange data, Ethena statement) | F-05 (single-venue limitation), F-10 (oracle lag irrelevant under deviation triggering — this case needs a *venue* price feeding the oracle, which the model does not have). Next-questions section, not Nov 1 scope |
| L-8 | Abracadabra / MIM, 2026-09-30: liquidation at ~$0.04/token against ~$21M unbacked debt | Insolvency is a different chapter from attack/liquidity mechanics | Muse relay 2026-10-02 | unverified lead | Taxonomy paragraph in the note: attack vs liquidity vs insolvency |
| L-9 | "June research synthesis on the USDC 2023 depeg" — four-scenario stress library incl. oracle-deviation + AMM-spiral; proposes time-to-parity as the headline metric | Time-to-parity | Muse relay 2026-10-02 | unverified lead; needs a URL | **F-11** (at issuer scale the clock is the binding constraint) — independent support for the 2.8 reference-relative criterion and for reporting `steps_to_sustained_recovery` |

## Open requests

- Tim / Muse: the URLs behind L-4, L-5, L-6, L-9 (the 2026-10-01 briefing presumably has
  them). Without a primary source they stay leads.
- Dev manager: confirm L-3 citation; source L-7 and L-8 from primary reporting before the
  note's taxonomy paragraph is written (Epic 4).

## Change Log

- 2026-10-04: Created by dev manager after reviewing Open Brain `[muse-ops]` relays; L-1/L-2 lifted from BACKGROUND; L-3–L-9 logged as leads.
