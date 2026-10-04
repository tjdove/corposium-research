"""Entry point: python -m depeg_sim.sweep sweeps/<name>.yaml [--workers N] [--output DIR]

Thin wrapper around depeg_sim.experiments.sweep.main. The ``__main__`` guard also keeps
``spawn`` workers, which re-import the main module, from re-running the CLI.

Exits via ``os._exit`` after flushing stdio, for the same reason as ``depeg_sim.mc``:
pyarrow's C++ thread pool can abort during interpreter teardown on some CI runners, after
all output and files are already final.
"""

import os
import sys

from depeg_sim.experiments.sweep import main

if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)
