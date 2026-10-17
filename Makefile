# Story 2.9. `make figures` regenerates every committed figure in full (runs all thirteen
# sweeps first: ~15 min on 12 cores, plus 4.5 min for the gradual policy sweep),
# records the code hash and re-writes the six fit records in docs/calibration/fits/
# (Story 4.1; the two par-reference ladder-B fits are Story 5.6's); `make figures-check`
# is the stale-figure guard CI runs (no sweeps, no PNG comparison: fails on a changed source,
# warns on changed code); `make figures-quick` is the 2-seed smoke test. `make test` also
# fails if line coverage of protocol/ and agents/ (together) drops below 85% (Story 3.5).
# `make note-check` checks the figures, freeze tag and fitted numbers docs/NOTE.md cites
# against the repository (Story 4.2; CI runs it beside figures-check).

# The repo's .venv when there is one (no activation needed), else whatever `python` is.
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
WORKERS ?= $(shell nproc 2>/dev/null || echo 2)
SWEEPS := sweeps/threshold-surface-ref-mc.yaml sweeps/threshold-surface-mc.yaml \
          sweeps/budget-x-depth-mc.yaml sweeps/oracle-lag-mc.yaml \
          sweeps/policy-comparison-mc.yaml sweeps/holder-exit-1992-mc.yaml \
          sweeps/budget-x-attack-mc.yaml sweeps/pace-x-trigger-mc.yaml \
          sweeps/pace-ratio-mc.yaml sweeps/threshold-surface-ou-mc.yaml \
          sweeps/lp-flight-mc.yaml sweeps/usdc-par-depth-x-capital.yaml \
          sweeps/policy-comparison-gradual-mc.yaml
FITS_DIR := docs/calibration/fits

.PHONY: figures figures-quick figures-check note-check test lint

figures:
	@start=$$(date +%s); \
	for spec in $(SWEEPS); do \
		t0=$$(date +%s); \
		$(PYTHON) -m depeg_sim.sweep $$spec --mc --workers $(WORKERS) || exit 1; \
		echo "sweep $$spec: wall time $$(( $$(date +%s) - t0 )) s"; \
	done; \
	$(PYTHON) scripts/make_figures.py --workers $(WORKERS) || exit 1; \
	t0=$$(date +%s); \
	$(PYTHON) scripts/fit_depth.py --workers $(WORKERS) --write $(FITS_DIR)/depth.json || exit 1; \
	$(PYTHON) scripts/fit_holder.py --workers $(WORKERS) --write $(FITS_DIR)/holder-single.json || exit 1; \
	$(PYTHON) scripts/fit_holder.py --tranches 2:0.25,5:0.25,10:0.25,20:0.25 \
		--workers $(WORKERS) --write $(FITS_DIR)/holder-ladder-b.json || exit 1; \
	$(PYTHON) scripts/fit_holder.py --scenario scenarios/usdc-2023-tranches-par.yaml \
		--tranches 2:0.25,5:0.25,10:0.25,20:0.25 \
		--workers $(WORKERS) --write $(FITS_DIR)/holder-ladder-b-par.json || exit 1; \
	$(PYTHON) scripts/fit_holder.py --scenario scenarios/usdc-2023-tranches-par-closed.yaml \
		--tranches 2:0.25,5:0.25,10:0.25,20:0.25 \
		--workers $(WORKERS) --write $(FITS_DIR)/holder-ladder-b-closed.json || exit 1; \
	$(PYTHON) scripts/fit_reversion.py --write $(FITS_DIR)/reversion.json || exit 1; \
	echo "fits: wall time $$(( $$(date +%s) - t0 )) s"; \
	end=$$(date +%s); \
	echo "make figures: wall time $$((end - start)) s ($(WORKERS) workers)"

figures-quick:
	@start=$$(date +%s); \
	$(PYTHON) scripts/make_figures.py --quick --workers $(WORKERS) || exit 1; \
	end=$$(date +%s); \
	echo "make figures-quick: wall time $$((end - start)) s ($(WORKERS) workers)"

figures-check:
	$(PYTHON) scripts/check_figures.py

note-check:
	$(PYTHON) scripts/check_note.py

test:
	$(PYTHON) -m pytest --cov=depeg_sim.protocol --cov=depeg_sim.agents \
		--cov-report=term --cov-fail-under=85

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
