"""Entry point: python -m depeg_sim.mc <sweep_dir>

Thin wrapper around depeg_sim.experiments.mc.main: aggregates an existing sweep's
``sweep.parquet`` into ``mc.parquet``.

Exits via ``os._exit`` after flushing stdio. ``main`` has already written its files and
printed its result; the only thing left is interpreter teardown, during which pyarrow's
C++ thread pool can abort ("terminate called without an active exception", SIGABRT) on
some CI runners. Skipping teardown avoids a spurious non-zero exit with no loss of
output. Seen on GitHub run 37221623945 (2026-10-04), same commit as a passing run.
"""

import os
import sys

from depeg_sim.experiments.mc import main

if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
