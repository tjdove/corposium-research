# ADR-0014: The run manifest embeds the resolved scenario config

**Status:** Accepted
**Date:** 2026-10-02
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 1.8 AC 5/6

## Context
`plot_peg_trajectory(run_dir)` takes only a run directory, but the chart needs scenario
parameters: the `peg_recovered.tolerance` band, the step interval, and the ids of the
attacker and defender for event markers. None of the AC 5 artifacts held them. The
scenario hash identifies the config but cannot be inverted.

## Decision
`manifest.json` carries one extra key beyond the AC 5 list: `config`, the full resolved
scenario (`ScenarioConfig.model_dump(mode="json")`). Analysis code that starts from a
run directory reads parameters from `manifest["config"]`, never from the YAML path.

## Consequences
- A run directory is self-describing. Charts and later analyses (Epic 2 aggregation)
  can be rebuilt from `output/<run_id>/` alone, even if the YAML has since changed.
- `ScenarioConfig.model_validate(manifest["config"])` round-trips, and its
  `content_hash()` equals `manifest["scenario_hash"]`.
- Manifests grow by ~1.5 kB. Still deterministic except `created_utc`.

## Alternatives considered
- A separate `scenario.json` / copy of the YAML in the run dir: one more file in the
  ADR-0004 tree for the same information.
- Passing the config into `plot_peg_trajectory`: breaks "every chart reproducible from
  the run directory".
