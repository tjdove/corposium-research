# Story 2.9. `make figures` regenerates every committed figure in full (runs all five
# sweeps first: ~10 min on 12 cores); `make figures-check` is the stale-figure guard CI
# runs (no sweeps, no PNG comparison); `make figures-quick` is the 2-seed smoke test.

PYTHON ?= python
WORKERS ?= $(shell nproc 2>/dev/null || echo 2)
SWEEPS := sweeps/threshold-surface-ref-mc.yaml sweeps/threshold-surface-mc.yaml \
          sweeps/budget-x-depth-mc.yaml sweeps/oracle-lag-mc.yaml \
          sweeps/policy-comparison-mc.yaml

.PHONY: figures figures-quick figures-check test lint

figures:
	@start=$$(date +%s); \
	for spec in $(SWEEPS); do \
		$(PYTHON) -m depeg_sim.sweep $$spec --mc --workers $(WORKERS) || exit 1; \
	done; \
	$(PYTHON) scripts/make_figures.py --workers $(WORKERS) || exit 1; \
	end=$$(date +%s); \
	echo "make figures: wall time $$((end - start)) s ($(WORKERS) workers)"

figures-quick:
	@start=$$(date +%s); \
	$(PYTHON) scripts/make_figures.py --quick --workers $(WORKERS) || exit 1; \
	end=$$(date +%s); \
	echo "make figures-quick: wall time $$((end - start)) s ($(WORKERS) workers)"

figures-check:
	$(PYTHON) scripts/check_figures.py

test:
	$(PYTHON) -m pytest

lint:
	ruff check .
	ruff format --check .
