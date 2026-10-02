"""Entry point: python run.py scenarios/<name>.yaml

Thin wrapper around depeg_sim.cli so the README command works without
installing the console script.
"""

from depeg_sim.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
