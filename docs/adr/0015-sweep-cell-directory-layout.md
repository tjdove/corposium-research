# ADR-0015: Sweep cells live at `<sweep>/<index:04d>-<seed>-<hash8>/`

**Status:** Accepted
**Date:** 2026-10-03
**Deciders:** Tim Dove, Claude (dev manager)
**Origin:** story 2.1 AC 5 / AC 7 (spec conflict)

## Context
AC 5 names each cell's config `f"{spec.name}/{index:04d}"`. `run_scenario` names its
directory `run_id = f"{cfg.name}-{seed}-{hash[:8]}"` under `output_dir` (1.8). AC 7 asks
for each cell at exactly `output_dir/<spec.name>/<index:04d>/`. That path can't come out
of `run_scenario` unchanged. The Dev Notes worker (`output_dir=out / f"{index:04d}"`)
would produce `<sweep>/0000/<sweep>/0000-42-<hash8>/`: the sweep name and index twice.

## Decision
The worker calls `run_scenario(cell.config, output_dir=<output_dir>, chart=False)`. The
slash in the cell's name puts the run directory inside the sweep directory:

```
output/pool-depth-x-attacker/
  manifest.json
  sweep.parquet
  0000-42-e79a8ca8/      an ordinary run directory (ADR-0004 tree, no chart)
  0001-42-16c78f7c/
  ...
```

The cell directory is found from the cell alone: `output_dir / run_id_for(cfg, seed)`
(`sweep.cell_run_dir`). `run_scenario` is unchanged apart from the `chart` flag. The
per-run `manifest.json` records `run_id` as `pool-depth-x-attacker/0000-42-e79a8ca8`.

## Consequences
- One level of nesting. Directories sort by index. Each name says which seed and config
  produced it.
- With several seeds (Story 2.2), cells of the same grid point differ only in seed and
  hash, so `ls` groups them by index, not by grid point. Use `sweep.parquet` to group.
- `run_sweep` replaces `<output_dir>/<spec.name>/` wholesale on rerun, like
  `run_scenario` does for a run.

## Alternatives considered
- Follow the Dev Notes literally: duplicated nesting for no information gain.
- Add a `run_dir=` override to `run_scenario` to hit `<index:04d>/` exactly: a second way
  to name run directories, and outside 2.1's stated scope (`chart` flag only).
- Drop the slash from the cell name: contradicts AC 5.
