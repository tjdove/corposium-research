# Architecture Decision Records

One file per decision, numbered, never edited after acceptance except to change `Status`
(e.g. to `Superseded by ADR-00NN`). Decisions that are *research findings* about the model
are ADRs too: they constrain what we build next. Accepted findings are also narrated, in
order, in [`docs/FINDINGS.md`](../FINDINGS.md); that file is the research note's spine.

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-python-engine.md) | Engine language is Python | Accepted | 2026-10-02 |
| [0002](0002-bmad-story-process.md) | BMAD-style epics and stories; Claude writes, Claude Code builds | Accepted | 2026-10-02 |
| [0003](0003-floats-not-decimal.md) | Token amounts are floats in token units | Accepted | 2026-10-02 |
| [0004](0004-files-not-sql.md) | Persistence is files + manifest, not SQL | Accepted | 2026-10-02 |
| [0005](0005-construction-validates-execution-rejects.md) | Construction validates and raises; execution rejects and emits | Accepted | 2026-10-02 |
| [0006](0006-max-steps-is-the-safety-cap.md) | `steps.max_steps` is the mandatory safety cap | Accepted | 2026-10-02 |
| [0007](0007-peg-view-owner-and-sign.md) | AMM owns `PegView`; deviation is negative under stable selling | Accepted | 2026-10-02 |
| [0008](0008-ctx-first-for-emitting-methods.md) | Subsystem methods that emit take `ctx` first | Accepted | 2026-10-02 |
| [0009](0009-oracle-threshold-zero.md) | `deviation_threshold_pct: 0` means a zero-lag oracle | Accepted | 2026-10-02 |
| [0010](0010-dead-zone-finding.md) | The baseline parks in a dead zone no agent rule covers | Accepted (finding) | 2026-10-02 |
| [0011](0011-multi-action-decision-record.md) | Multi-action steps record `{"actions": [...]}` | Accepted | 2026-10-02 |
| [0012](0012-arbitrageur-latency-plan.md) | Latency plans keep first-seen step and latest size | Accepted | 2026-10-02 |
| [0013](0013-recovery-tolerance-outside-arb-band.md) | Recovery tolerance sits just outside the arbitrage band | Accepted (amended) | 2026-10-02 |
| [0014](0014-manifest-embeds-resolved-config.md) | The run manifest embeds the resolved scenario config | Accepted | 2026-10-02 |
| [0015](0015-sweep-cell-directory-layout.md) | Sweep cells live at `<sweep>/<index>-<seed>-<hash8>/` | Accepted | 2026-10-03 |
| [0016](0016-outcome-set-by-capital-not-depth.md) | Outcome boundary is set by capital vs defense resources, not pool depth | Accepted (finding, amended; refined by 0017) | 2026-10-03 |
| [0017](0017-depth-enters-through-defender-price.md) | Depth enters the verdict through the price the defender pays | Accepted (finding, amended) | 2026-10-03 |
| [0018](0018-calibration-judgment-calls.md) | Calibration judgment calls: pool anchor, reserves split, attacker ratio, market-depth multiple | Accepted (amended; §3 superseded by 0019 amendment) | 2026-10-04 |
| [0019](0019-fitted-depth-and-1992-analogue.md) | Fitted depth D*, 1992 split/multiple, boundary at calibrated depth | Accepted (amended; §1 superseded, re-fit in 2.5) | 2026-10-04 |
| [0020](0020-episode-flow-replay-and-capacity-schedule.md) | Episode-flow attacker, re-fit D*, replay semantics; replay does not validate (F-08) | Accepted (amended; adds Story 2.6) | 2026-10-04 |
| [0021](0021-par-expecting-holder.md) | Par-expecting holder: tranche redeem rule, C* = 9.17M ($2.15B), replay −5,769 → −1,138; depth bimodal in holder capital (F-09) | Accepted (finding, amended) | 2026-10-04 |
| [0022](0022-threshold-surface-metric-and-oracle-lag.md) | Threshold surface: p_stays_broken, absorbed ratio, linked-axis scales; oracle lag does not matter (F-10); at calibrated depth "stays broken" is the clock (F-11) | Accepted (finding, amended; adds Story 2.8) | 2026-10-04 |
| [0023](0023-reference-relative-recovery-and-budget-depth.md) | Reference-relative recovery via ReferenceView; oracle criterion removes the wander, not the clock; defending budget does not scale with depth | Accepted (finding, amended; refines F-11) | 2026-10-04 |
| [0024](0024-holder-fill-price-limit.md) | Holder fill-price limit; C* unchanged; sawtooth gone on the plateau; 1992 flip 5.7 → 5.2: an overpaying believer was an accidental defender (F-12) | Accepted (finding, amended) | 2026-10-05 |
| [0025](0025-defender-policies-and-base-axis.md) | Defender policy comparison: buy flag, spread cap, base_axis; the slow defender wins because it pays less (F-13); no spread dead zone under capacity-limited redemption (F-07 refinement) | Accepted (finding, amended) | 2026-10-05 |
| [0026](0026-holder-exit-rule-and-switch-sides-test.md) | Holder exit rule; 1992 switch-sides test: AMM exit breaks the price not the reserves; redemption is the 1992 switch; flip 4.9× with large redeeming believers (F-14) | Accepted (finding, amended) | 2026-10-06 |
| [0027](0027-budget-vs-attack-and-pace-vs-trigger.md) | Budget vs attack at 2× D*: holding budget ≈ 0.36 × attack (slope 1.08); pace vs trigger: trigger does nothing, defender pace relative to attacker pace decides (F-11, F-13 refinements) | Accepted (finding, amended) | 2026-10-06 |

## Template

```markdown
# ADR-NNNN: Title

**Status:** Proposed | Accepted | Superseded by ADR-NNNN
**Date:** YYYY-MM-DD
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story / review / charter

## Context
## Decision
## Consequences
## Alternatives considered
```
