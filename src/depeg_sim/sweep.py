"""Entry point: python -m depeg_sim.sweep sweeps/<name>.yaml [--workers N] [--output DIR]

Thin wrapper around depeg_sim.experiments.sweep.main. The ``__main__`` guard also keeps
``spawn`` workers, which re-import the main module, from re-running the CLI.
"""

from depeg_sim.experiments.sweep import main

if __name__ == "__main__":
    raise SystemExit(main())
