# Corposium Research — Soros/ERM Stablecoin Depeg Simulator
## Project Charter (v0.3 — 2026-10-02)

Owner: Tim Dove · Dev manager: Claude · Business ops: Muse (Meta)

---

## 1. Mission

Ship Corposium Research's first real-world artifact: a documented, reproducible, calibrated study of stablecoin depeg mechanics modeled on the 1992 Soros/ERM event. Public by **November 1, 2026**. Main Corposium push for Q4 2026.

**Thesis:** A peg is a price promise. The 1992 BoE defense failed because the promise exceeded reserve capacity under adversarial, reflexive pressure. The simulator asks the same question of DeFi: under what combination of pool depth, oracle delay, attacker capital and defense policy do reserves exhaust before the peg recovers?

**Audience:** crypto researchers first (X, DeFi research community); journalists second. Not hiring managers. Purpose is reputation in development and research.

**Bar:** calibrated to real-world parameters, validated against one historical depeg, with confidence bands. Not a toy sweep.

---

## 2. The Artifact — DECIDED: Option C

**Definition of done:**
- [ ] Public GitHub repo (open source): README, one-command install, `python run.py scenarios/<name>.yaml` reproduces every chart
- [ ] Research note (~2,000–3,500 words): framing, method, calibration sources, headline finding, limitations, next questions
- [ ] Charts: (1) threshold surface — reserve exhaustion over pool depth × attacker capital, (2) peg trajectory with defender intervention, with Monte Carlo bands, (3) oracle-lag sensitivity, (4) historical validation overlay (USDC Mar-2023), (5) defense-policy comparison
- [ ] Static results page on corposium site: abstract, charts, links to repo and note
- [ ] Launch thread on X, drafted and scheduled
- [ ] One-pager for media reuse

---

## 3. Roles

**Tim Dove — Owner.** Final decisions on goals, direction, business. Human interface to clients, chamber, social. Full-time through October.

**Claude (chat) — Dev manager / executive.** Writes epics, stories and story context (the BMAD SM/PM/Architect seats). Evaluates all proposals, directs all coding agents, reviews and closes stories, evaluates Muse's plans until proven. Owns build, calibration and technical write-up. Leaves build reports in Open Brain (`[claude]` tag) and emails Muse what ops needs.

**Claude Code on Seoul — Builder.** Implements one assigned story at a time per `CLAUDE.md`. Sonnet-tier builds; Opus/Fable-tier does the cold senior review.

**Muse (Meta personal agent) — Business ops.** Daily on-track check-in with Tim, time logs (one row per dev session), project email triage/drafts, social scheduling, calendar. Writes to Open Brain under `[muse-ops]` only. **Does not direct coding agents. Never holds dev credentials.**

---

## 4. Scope — MVP+ (revised after phase review, 2026-10-01)

### In
- Python 3.12, deterministic, seeded, discrete steps (configurable, default 12s)
- Scenario YAML validated by Pydantic; explicit, versioned step-phase order
- Kernel: engine, scheduler, clock, run context, JSON checkpoints
- Protocol: constant-product AMM (fees), oracle module (heartbeat + deviation threshold), redemption module (reserves, spread, per-step capacity, queue)
- Agents: Attacker, Arbitrageur, Defender (policy-parameterized: threshold, spend pace, spread adjustment)
- Environment: external reference price with stochastic shocks; oracle lag
- Experiment runner: grid sweeps, Monte Carlo over seeds, run manifest, parquet timeseries, run summaries, decision traces
- **Calibration:** pool depths from real Curve/Uniswap stable pools; oracle cadence from Chainlink heartbeat/deviation; attacker capital sized to historical events
- **Validation:** reproduce the shape of USDC March-2023 depeg (trough, recovery trigger)
- Core metrics: peg deviation, reserves remaining, time to recovery, attacker PnL, defender spend, reserves-exhausted flag
- pytest on AMM math, redemption accounting, termination conditions, determinism

### Stretch (only if Epic 2 done by Oct 14)
- LP withdrawal agent (single panic-threshold parameter) — reflexive liquidity flight, the core Soros dynamic
- Holder panic agent
- Anvil/Foundry replay of one scenario against a real Uniswap V2 pair; chart simulated vs on-chain execution price

### Out until after Nov 1
- Lending, collateral, liquidations, liquidator agent
- SQLite/SQLAlchemy persistence (files + manifest instead)
- Comparative architecture tests, fragility reports
- Named composite metrics (Promise-Capacity Ratio, Peg Pressure Index, Reflexivity Coefficient, Recovery Integrity) — derive after data exists
- Interactive web UI (Q1 2027)
- Local AI coding experiments
- Token-usage tooling (spreadsheet row per session only)

---

## 5. Phase review of the original spec (why each is in or out)

| Spec phase | By Nov 1? | Verdict |
|---|---|---|
| 1. Kernel + one protocol world | Yes, 3–5 days | Build fully as specified (Epic 1) |
| 2. Persistence + runner | Sweeps/MC/parquet/traces yes; SQL no | Files + manifest; SQL adds no value for outside reproducibility (Epic 2) |
| 3. Research experiments | Yes, ~1 week | The artifact. Calibration + historical validation is what makes results real (Epic 2–3) |
| 4. Extended mechanics | Defender policies yes; LP/holder stretch; lending no | Lending adds a second feedback loop + ~10 params; finding becomes unattributable (Epic 3) |
| 5. Anvil verification | Stretch, 2–3 days | Strong credibility signal for crypto readers if time allows |
| Named metrics | No | Define after looking at data or they read as marketing |

Principle: credibility comes from grounded parameters and a validated trajectory, not from mechanism count.

---

## 6. Timeline

- **Oct 2–6 — Epic 1, Kernel.** One scenario end to end; first chart; first build-in-public post.
- **Oct 7–13 — Epic 2, Finding.** Runner, sweeps, Monte Carlo, calibration sources documented, USDC validation run. Headline threshold identified.
- **Oct 14 checkpoint:** if no clear finding, cut scope, not time (fall back to well-documented sensitivity study).
- **Oct 14–20 — Epic 3, Depth.** Defender policy comparison. Stretch: LP agent, Anvil replay. Tests, README.
- **Oct 21 — Feature freeze.**
- **Oct 22–28 — Epic 4, Write-up.** Note, charts final, site page, one-pager, launch thread.
- **Oct 29–31 — Buffer.** Outside reader review; schedule posts.
- **Nov 1 — Publish.**

Cadence: Tim + Claude review Mondays; Muse daily check-in; one public post per milestone.

---

## 7. Coordination architecture

- **Email is the bus.** Claude drafts briefs/status to Muse's own email address; Tim cc's Muse on project threads. Muse never receives dev credentials.
- **Open Brain (Supabase)** = shared memory. Claude writes `[claude]`, Muse writes `[muse-ops]`, neither deletes or edits the other's entries.
- **Seoul** = this repo and builds. **iPhone** = Muse, Corposium line, real-world interface. **Claude project "Corposium Research Lab"** = charter and plans (mirror of `docs/`).
- **Process** = BMAD-style: `docs/epics.md` → `docs/stories/N-M-slug.md` (+ `.context.xml`) → build → senior review → retro per epic.

---

## 8. Communications & Brand

- Build in public on X: one post per milestone from real output.
- Local/chamber: light in October, message "AI engineering for local business." Ramp in November with the artifact as proof.
- Press: crypto-research readers first; one-pager for journalists after publish.

---

## 9. Principles

- One concrete question first; let friction decide what's next
- Deterministic and replayable, always
- Grounded parameters over more mechanisms
- Python first; Rust only if measured
- No live-chain dependencies in the core path (Anvil is verification only)
- Honest results over impressive architecture

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Scope creep | Section 4 Out list; Claude vetoes until Nov 1 |
| Calibration takes longer than code | Start source-gathering Oct 6 in parallel with kernel polish |
| No clear finding | Oct 14 checkpoint; sensitivity-study fallback |
| Coordination overhead | One dev manager; email bus; Muse on ops only |
| Launch to nobody | Build-in-public from Oct 5 |
| Owner pace | Bounded weeks; buffer built in |

---

## 11. Open Questions

1. Muse's email address and tier
2. Does corposium site have a Research section, or does the page need building?
3. Historical validation case: USDC Mar-2023 (recommended) vs UST May-2022 (algorithmic; different mechanics)
4. ~~GitHub org/user for the public repo~~ → github.com/tjdove/corposium-research

---

## 12. Decision Log

| Date | Decision | By |
|---|---|---|
| 2026-03-07 | MVP = 3 agents, 1 AMM, 1 redemption, CSV | Tim + Claude |
| 2026-09-30 | Reactivated; publish Nov 1 2026 | Tim |
| 2026-09-30 | Claude = dev manager; Muse = ops; Tim = owner | Tim |
| 2026-10-01 | Artifact = Option C | Tim |
| 2026-10-01 | Code open source | Tim |
| 2026-10-01 | Audience = crypto researchers, then journalists | Tim |
| 2026-10-01 | Open Brain = shared memory; email = Muse handoff | Tim + Claude |
| 2026-10-01 | Scope raised to MVP+ (calibration, MC, defender policies); lending/SQL/named metrics out | Claude, pending Tim |
| 2026-10-01 | Muse does not direct coding agents | Tim |
| 2026-10-01 | Open Brain write rules: Muse `[muse-ops]`, Claude `[claude]`, no deletes, no overwrites | Tim + Claude |
| 2026-10-02 | Engine language = Python (credibility, tooling) | Tim |
| 2026-10-02 | Process = BMAD-style epics/stories; Claude writes them, Claude Code builds | Tim + Claude |
| 2026-10-02 | New repo `corposium-research`, MIT license | Tim |
| 2026-10-04 | Epic 2 gains Story 2.6 (par-expecting buyer) after the USDC replay failed validation (F-08); Epic 2 ends Oct 15; freeze stays Oct 21 | Claude, for Tim's confirmation |
