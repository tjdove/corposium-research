# Reproducibility

How to reproduce every committed figure and number from a clean checkout, how long it
takes, and which hashes must match. Measured 2026-10-06, updated 2026-10-07 for the OU surface and 2026-10-08 at the freeze; the
committed figures were drawn from code commit `ae0f39f` (tag `v0.9-freeze` is the commit
that adds them, same code hash).

## Machines

| Name | What | Used for |
|---|---|---|
| Seoul | Linux x86_64, 12 cores, Python 3.12.13 (uv-managed) | the builder; every full `make figures` |
| CI | GitHub Actions `ubuntu-24.04`, 4 cores, Python 3.12 (`actions/setup-python`) | `make lint test figures-check` and `make figures-quick` on every push |

## Python and install

Python **3.12** (`requires-python = ">=3.12"`; CI and Seoul run 3.12). On a clean venv:

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # 1 s on Seoul
pip install -e ".[dev]"                                 # 72 s on Seoul, no pip cache
pytest                                                  # 13 s on Seoul (745 tests)
```

Measured on Seoul with `--no-cache-dir`, which resolved numpy 2.5.3, pandas 3.0.6,
pyarrow 25.0.1, matplotlib 3.11.2, pydantic 2.13.5, PyYAML 6.0.3, pytest 9.1.1, ruff
0.16.10. With a warm pip cache the install takes a few seconds.

**Dependency bounds** (`pyproject.toml`): each runtime dependency has an upper bound
below its next major version (numpy < 3, pandas < 4, pyarrow < 26, matplotlib < 4,
pydantic < 3, PyYAML < 7), so a fresh install cannot pick up a major release that
changes RNG streams, dtype or copy semantics, the parquet writer, the chart backend or
validation. The lower bounds are the oldest versions the suite has passed on: on
2026-10-06 a uv venv with numpy 1.26.4, pandas 2.2.3, pyarrow 16.0.0, matplotlib
3.9.4, pydantic 2.7.4 and PyYAML 6.0.1 ran `pytest` with 745 passed. (PyYAML 6.0 itself
has no 3.12 wheel and fails to build, so the floor is 6.0.1.) Byte-identical output is
promised for the same seed, scenario and environment; across library versions it is
not promised. The one cross-version data point: the pinned `soros-baseline`
`summary.json` sha256 (below) is the same on the floor versions and the current ones;
figures were not compared.

## Commands that produce figures

`make figures` runs every figure sweep, then `scripts/make_figures.py`, which runs the
six scenario figures itself (seconds each), draws all nineteen figures and writes
`docs/figures/manifest.json`, then re-runs the four fits with `--write` into
`docs/calibration/fits/` (`fit_depth`, `fit_holder` single entry and ladder B,
`fit_reversion`; 25 s on Seoul at 12 workers). Wall times:

| Command | Figures | Runs (full) | Seoul full, 12 workers | Seoul quick, 12 workers | CI quick, 4 workers |
|---|---|---:|---:|---:|---:|
| `python -m depeg_sim.sweep sweeps/threshold-surface-ref-mc.yaml --mc` | `threshold_surface.png`, `time_to_parity.png` | 640 | 138 s | 19 s | 165 s |
| `python -m depeg_sim.sweep sweeps/threshold-surface-mc.yaml --mc` | `threshold_surface_par.png` | 640 | 136 s | 18 s | 150 s |
| `python -m depeg_sim.sweep sweeps/budget-x-depth-mc.yaml --mc` | `budget_depth.png` | 200 | 52 s | 13 s | 109 s |
| `python -m depeg_sim.sweep sweeps/oracle-lag-mc.yaml --mc` | `oracle_sensitivity.png` | 640 | 110 s | 8 s | 65 s |
| `python -m depeg_sim.sweep sweeps/policy-comparison-mc.yaml --mc` | `policy_comparison.png` | 240 | 74 s | 10 s | 89 s |
| `python -m depeg_sim.sweep sweeps/holder-exit-1992-mc.yaml --mc` | `holder_exit.png` | 120 | 19 s | 5 s | 43 s |
| `python -m depeg_sim.sweep sweeps/budget-x-attack-mc.yaml --mc` | `budget_attack.png` | 200 | 57 s | 16 s | 132 s |
| `python -m depeg_sim.sweep sweeps/pace-x-trigger-mc.yaml --mc` | `pace_trigger.png` | 256 | 92 s | 25 s | 191 s |
| `python -m depeg_sim.sweep sweeps/pace-ratio-mc.yaml --mc` | `pace_ratio.png` | 112 | 23 s | 7 s | 52 s |
| `python -m depeg_sim.sweep sweeps/threshold-surface-ou-mc.yaml --mc` | `threshold_surface_ou.png`, `time_to_parity_ou.png` | 640 | 127 s | 17 s | 144 s |
| `python -m depeg_sim.sweep sweeps/lp-flight-mc.yaml --mc` | `lp_flight.png` | 288 | 51 s | (not measured) | (not split out; whole job 1,305 s, run 37781242502) |
| `python scripts/make_figures.py` | all 19 (runs the 6 scenario figures: `peg_trajectory_*.png`, `validation_overlay_usdc_2023.png`, `validation_overlay_usdc_2023_tranches.png`) | — | ≈ 10 s | (included) | (included) |
| **`make figures`** / **`make figures-quick`** | all 19 (+ 4 fit records) | 3,977 | **934 s** | **147 s** | **1,155 s** |

Totals are from 2026-10-08 (Seoul `make figures` 934 s at `ae0f39f`, Story 4.1, the freeze
run, including the four fits, 25 s; 893 s at code `6f2859d`, Story 3.8, which
adds the 288-run `lp-flight-mc` sweep, 51 s; Story 3.7's was 843 s at `b1352c8`; `make figures-quick` 147 s at `8c5fdf3`, not re-measured; CI run
[37657607713](https://github.com/tjdove/corposium-research/actions/runs/37657607713),
`figures-quick` 1,155 s). The per-sweep rows other than `threshold-surface-ou-mc` are the
2026-10-06 measurements below; on 2026-10-07 each was within 10 s of them.

"Full" is the committed spec (8 or 16 seeds per point); "quick" is the same grid at 2
seeds (`make figures-quick`). Seoul timings: `make figures WORKERS=12` and
`make figures-quick WORKERS=12` on 2026-10-06 (per-sweep times printed by the
Makefile; the `make_figures.py` line is the total minus the sweeps). CI timings: the
`figures-quick` job of run
[37549454426](https://github.com/tjdove/corposium-research/actions/runs/37549454426)
on `7db6480` (`ubuntu-24.04`, `nproc` = 4). The full `make figures` is not run on CI; at
CI's quick-to-quick ratio (about 8×) it would take roughly two hours there
(an extrapolation, not a measurement).

`make figures-quick` (2 seeds per sweep, temporary directory, writes only the gitignored
`docs/figures/quick-ok`) is what the CI `figures-quick` job runs.

A single figure: run its sweep (`python -m depeg_sim.sweep <spec> --mc --workers N`),
then `python scripts/make_figures.py` (it redraws all figures from whatever is in
`output/`, refusing any sweep directory whose `spec_hash` does not match its spec).

## Disk and `TMPDIR`

Sweeps write every cell's full run directory: about **2 GB per 200 runs**, so a full
`make figures` writes roughly 36 GB under `output/` (gitignored). Keep `--sweeps-dir` /
`output/` on a large disk. `make figures-quick` and the tests write to the system
temporary directory; when that is a small tmpfs (agent sessions, containers), point it
at a large disk first:

```bash
mkdir -p output/tmp && export TMPDIR=$PWD/output/tmp
```

## Hashes that must match

| What | Where it is recorded | How to check |
|---|---|---|
| Each scenario's `content_hash()` | README scenario table (first 12); pinned in `tests/` | `python run.py <scenario>` prints `hash=`; `pytest` |
| Each figure's source hash (scenario `content_hash()` or sweep `sweep_spec_hash()`) | `docs/figures/manifest.json`, and in each figure's footer | `make figures-check` (fails on mismatch) |
| Package code hash, sha256 over `src/depeg_sim/**/*.py` | `docs/figures/manifest.json` `code_hash` | `make figures-check` (warns on mismatch) |
| A sweep output's spec | `output/<sweep>/manifest.json` `spec_hash` | `scripts/make_figures.py` refuses a mismatch |
| Each fit record's inputs (scenario `content_hash()`, data file sha256) and fit script sha256 | `docs/calibration/fits/*.json` ([index](calibration/README.md)) | `make figures-check` (fails on an input mismatch, warns on a script mismatch); `make figures` re-writes them |
| `soros-baseline` seed 42 `summary.json` | `tests/test_reference_recovery.py` | `pytest`; `sha256sum output/soros-baseline-42-2e09f431/summary.json` |

At that commit: `code_hash` =
`a0ae9594e7a4f6cc08e4c3e50540749dad4b24bd486a111421850f81c1c29150` (the freeze; Story 3.8's was `c72e8639…`); `soros-baseline` seed 42
`summary.json` sha256 = `be7d32669a8fe6e2efb933bfca6ed213240b9eb85c26a2ee7aef4bea6cdc2fa9`
(Story 3.8 added two keys; without those lines it is the 3.5 value `f2428bdb…`),
run directory `output/soros-baseline-42-2e09f431/`.

## Before the freeze

The feature freeze (2026-10-21) and any release of the note's numbers pass this list.
The guard's code-hash warning is soft on purpose (a docstring edit does not move a
number); this checklist is the hard gate.

- [ ] `git status` clean on `main`, at the commit the note will cite.
- [ ] Clean venv: `pip install -e ".[dev]"` succeeds on Python 3.12.
- [ ] `make test lint` passes (tests, coverage ≥ 85% on `protocol/` and `agents/`,
      `ruff check`, `ruff format --check`).
- [ ] `make figures` on a machine with ≥ 40 GB free under `output/`; record its wall time.
- [ ] Commit the regenerated `docs/figures/*.png` and `manifest.json`.
- [ ] `make figures-check` prints `ok, N figures match their sources (code_hash matches)`
      with **no** `WARNING` line.
- [ ] Every number quoted in the README, `docs/figures/README.md` captions and the note
      re-read against the regenerated figures and tables; any that moved is fixed or
      explained.
- [ ] CI green on that commit, both jobs, checked by looking at the run.
