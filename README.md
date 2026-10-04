# Corposium Research — Stablecoin Depeg Simulator

A deterministic, agent-based simulator of stablecoin peg defense, modeled on the
1992 Soros/ERM event. A peg is a price promise; this project asks under what
combination of pool depth, oracle delay, attacker capital and defense policy the
defender's reserves exhaust before the peg recovers.

**Status:** pre-alpha, under active development. Publication target: 2026-11-01.

## Quick start

```bash
git clone https://github.com/tjdove/corposium-research.git
cd corposium-research
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python run.py scenarios/soros-baseline.yaml
```

which prints:

```
depeg-sim: scenario=soros-baseline seed=42 hash=2e09f431ce74
run: steps=192 terminated_by=peg_recovered max_depeg_bps=-573.2 reserves_exhausted=False
wrote: output/soros-baseline-42-2e09f431
```

and writes one directory per run, named `<scenario>-<seed>-<hash[:8]>`:

```
output/soros-baseline-42-2e09f431/
  manifest.json          provenance: scenario hash, seed, versions, files, resolved config
  summary.json           headline numbers (max depeg, recovery, reserves, PnL)
  timeseries.parquet     one row per step: prices, reserves, agent balances and PnL
  events.jsonl           every event, one JSON object per line
  decisions.jsonl        every agent decision with its rule (when trace_decisions)
  checkpoints/step-000192.json
  peg_trajectory.png     the chart
```

Options: `--seed N` overrides the scenario seed, `--output DIR` sets the parent
directory (default `output/`), `--no-chart` skips the PNG. Re-running the same scenario
and seed replaces that run's directory.

Every chart in the research note is reproduced by `python run.py scenarios/<name>.yaml`.
Same seed + same scenario = byte-identical output (everything except
`manifest.json`'s `created_utc`).

Scenarios: `soros-baseline.yaml` (flat reference price; the seed doesn't change the
result) and `soros-volatile.yaml` (the same plus a noisy reference price).

## Layout

```
src/depeg_sim/
  kernel/       engine, clock, scheduler, run context, checkpoints
  protocol/     AMM, oracle, redemption modules
  agents/       attacker, arbitrageur, defender
  environment/  external price process, shocks
  experiments/  single-run runner and output writer (sweeps: Epic 2)
  analysis/     metrics, charts
scenarios/      versioned YAML scenario definitions
tests/          pytest
docs/           charter, epics, stories, retrospectives, calibration sources
output/         run artifacts (gitignored)
```

## Documentation

- `docs/FINDINGS.md` — what the model has shown so far, in the order we learned it
- `docs/BACKGROUND.md` — the 1992 ERM crisis and how it maps to the simulator
- `docs/adr/` — architecture and research decision records
- `docs/CHARTER.md` — mission, scope, roles, timeline
- `docs/epics.md` — build plan broken into stories
- `docs/stories/` — one file per story with acceptance criteria and dev record
- `CLAUDE.md` — working rules for coding agents

## License

MIT. See `LICENSE`.
