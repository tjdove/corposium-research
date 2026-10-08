# Calibration

- [`SOURCES.md`](SOURCES.md): every calibrated parameter, its public source and the
  arithmetic from source to number, or "assumption".
- [`VALIDATION.md`](VALIDATION.md): the USDC March-2023 replay against the observed series.
- [`fits/`](fits/): the four fitted numbers as fit records (below).

## Fit records

Four parameters are fitted, not sourced. Each fit script takes `--write`, and `make
figures` re-runs all four with it after drawing the figures. A record holds the script
path and its sha256, the inputs (scenario path and `content_hash()`, data file and sha256,
the arguments that set the fit) and the result, including every point the fit ran. It has
no timestamp, so a re-run on unchanged inputs writes the same bytes.

`make figures-check` checks every record. It **fails** when a scenario or data file no
longer hashes as recorded, or when an input is missing. It **warns** when the fit script
itself has changed, as it does for the package code hash. Clearing that warning is a
freeze-checklist item ([`docs/REPRODUCIBILITY.md`](../REPRODUCIBILITY.md)).

| Record | Command | Fits | Inputs | Result | Used by |
|---|---|---|---|---|---|
| [`fits/depth.json`](fits/depth.json) | `python scripts/fit_depth.py --write docs/calibration/fits/depth.json` | aggregate pool depth D\* to the observed trough (−1,300 bps, Chainalysis $0.87) | `scenarios/calibrated-baseline.yaml` | **D\* = 16,666,667** (trough −1,253.2 bps) | every calibrated scenario's `amm` reserves |
| [`fits/holder-single.json`](fits/holder-single.json) | `python scripts/fit_holder.py --write docs/calibration/fits/holder-single.json` | the par-expecting buyer's capital C\*, one entry at 2% below par | `scenarios/usdc-2023.yaml`, `data/usdcusd_1h_stress_2023-03-10_2023-03-13.csv` | **C\* = 9,166,667** (≈ $2.15B; trough −1,137.8 bps) | `usdc-2023`, the calibrated scenarios' holder |
| [`fits/holder-ladder-b.json`](fits/holder-ladder-b.json) | `python scripts/fit_holder.py --tranches 2:0.25,5:0.25,10:0.25,20:0.25 --write docs/calibration/fits/holder-ladder-b.json` | the same capital with believers spread over four entry prices (ladder B, an assumption) | as above | **C\* = 10,833,333** (≈ $2.54B; trough −1,323.3 bps at step 9,346) | `usdc-2023-tranches` |
| [`fits/reversion.json`](fits/reversion.json) | `python scripts/fit_reversion.py --write docs/calibration/fits/reversion.json` | the calm reference's mean reversion (AR(1) to par, hourly) | `data/usdcusd_1h_calm_2023-02-27_2023-03-03.csv` | **κ_step = 0.00163402** (φ 0.6123 ± 0.0728; half-life 1.41 h) | `calibrated-baseline-ou`, `calibrated-baseline-lp` and the OU sweeps |

The holder fits run on `usdc-2023.yaml` with the holder entry replaced. The scenario's
hash covers its replay series' sha256, and the record also carries the series file's own
hash. The depth fit's target comes from a published figure, not a data file, so its
`data` is null. The rules that pick each number are in each script's docstring and in
`SOURCES.md`.
