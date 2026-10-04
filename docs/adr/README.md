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
| [0018](0018-calibration-judgment-calls.md) | Calibration judgment calls: pool anchor, reserves split, attacker ratio, market-depth multiple | Accepted (amended) | 2026-10-04 |

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
