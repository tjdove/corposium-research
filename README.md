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

Every chart in the research note is reproduced by `python run.py scenarios/<name>.yaml`.
Same seed + same scenario = byte-identical output.

## Layout

```
src/depeg_sim/
  kernel/       engine, clock, scheduler, run context, checkpoints
  protocol/     AMM, oracle, redemption modules
  agents/       attacker, arbitrageur, defender
  environment/  external price process, shocks
  experiments/  sweep runner, Monte Carlo, manifests
  analysis/     metrics, charts
scenarios/      versioned YAML scenario definitions
tests/          pytest
docs/           charter, epics, stories, retrospectives, calibration sources
output/         run artifacts (gitignored)
```

## Documentation

- `docs/CHARTER.md` — mission, scope, roles, timeline
- `docs/epics.md` — build plan broken into stories
- `docs/stories/` — one file per story with acceptance criteria and dev record
- `CLAUDE.md` — working rules for coding agents

## License

MIT. See `LICENSE`.
