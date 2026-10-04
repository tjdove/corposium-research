"""Entry point: python -m depeg_sim.mc <sweep_dir>

Thin wrapper around depeg_sim.experiments.mc.main: aggregates an existing sweep's
``sweep.parquet`` into ``mc.parquet``.
"""

from depeg_sim.experiments.mc import main

if __name__ == "__main__":
    raise SystemExit(main())
