"""Fit records: a fit script's inputs and result in one JSON file (Story 4.1 AC 3).

``scripts/fit_depth.py``, ``fit_holder.py`` and ``fit_reversion.py`` take ``--write
<path>`` (``docs/calibration/fits/<name>.json``) and write::

    {
      "script": "scripts/fit_depth.py",
      "script_sha256": "<sha256 of the script file>",
      "inputs": {
        "scenario": "scenarios/calibrated-baseline.yaml",   # or null
        "scenario_hash": "<content_hash()>",                # or null
        "data": "data/....csv",                              # or null
        "data_sha256": "<sha256 of the data file>",          # or null
        "args": {...}                                        # the arguments that set the fit
      },
      "result": {...}
    }

No timestamp and no machine detail, so re-running a fit on unchanged inputs writes the
same bytes. ``scripts/check_figures.py`` reads every ``*.json`` in ``FITS`` with
``check_fit``: a changed scenario hash, data hash or a missing input is a problem (the
guard fails); a changed script hash only warns, as the package code hash does for figures.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FITS = Path("docs/calibration/fits")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scenario_hash(path: Path) -> str:
    from depeg_sim.kernel.config import load_scenario

    return load_scenario(Path(path)).content_hash()


def fit_record(
    script: Path, scenario: Path | None, data: Path | None, args: dict, result: dict
) -> dict:
    """The record for one fit. Paths are stored as given (relative to the repo root)."""
    return {
        "script": Path(script).as_posix(),
        "script_sha256": sha256_file(script),
        "inputs": {
            "scenario": None if scenario is None else Path(scenario).as_posix(),
            "scenario_hash": None if scenario is None else scenario_hash(scenario),
            "data": None if data is None else Path(data).as_posix(),
            "data_sha256": None if data is None else sha256_file(data),
            "args": args,
        },
        "result": result,
    }


def write_fit(path: Path, record: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return path


def script_path(file: str) -> Path:
    """``__file__`` of a fit script as ``scripts/<name>`` when run from the repo root."""
    p = Path(file).resolve()
    try:
        return p.relative_to(Path.cwd().resolve())
    except ValueError:
        return p


def check_fit(path: Path) -> tuple[list[str], list[str]]:
    """``(problems, warnings)`` for one fit file; inputs resolve against the working
    directory (the repo root)."""
    path = Path(path)
    name = path.name
    record = json.loads(path.read_text(encoding="utf-8"))
    inputs = record["inputs"]
    problems, warnings = [], []
    for key, hash_key, digest in (
        ("scenario", "scenario_hash", scenario_hash),
        ("data", "data_sha256", sha256_file),
    ):
        source = inputs.get(key)
        if source is None:
            continue
        if not Path(source).is_file():
            problems.append(f"{name}: {key} {source} is missing")
            continue
        recorded, now = inputs[hash_key], digest(source)
        if now != recorded:
            problems.append(
                f"{name}: STALE, {key} {source} changed (fit {recorded[:12]}, now {now[:12]}); "
                f"re-run the fit with --write {path.as_posix()}"
            )
    script = Path(record["script"])
    if not script.is_file():
        problems.append(f"{name}: script {script} is missing")
    elif sha256_file(script) != record["script_sha256"]:
        warnings.append(
            f"WARNING: {name} was written by another version of {script} (script_sha256 "
            f"{record['script_sha256'][:12]}, now {sha256_file(script)[:12]}); the result "
            "may differ: re-run the fit before the freeze"
        )
    return problems, warnings


def check_fits(fits_dir: Path = FITS) -> tuple[list[str], list[str], int]:
    """``check_fit`` over every ``*.json`` in ``fits_dir``: problems, warnings, count."""
    problems, warnings = [], []
    files = sorted(Path(fits_dir).glob("*.json")) if Path(fits_dir).is_dir() else []
    for f in files:
        p, w = check_fit(f)
        problems += p
        warnings += w
    return problems, warnings, len(files)
