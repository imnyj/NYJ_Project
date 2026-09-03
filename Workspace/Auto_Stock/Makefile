# ==============================================================================
# Auto_Stock Makefile
# ==============================================================================

PYTHON := $(if $(wildcard /home/imnyj/venv/bin/python3),/home/imnyj/venv/bin/python3,python3)
PYTEST := $(if $(wildcard /home/imnyj/venv/bin/pytest),/home/imnyj/venv/bin/pytest,pytest)

.PHONY: all test-hpo test-all hpo-run clean help

all: test-hpo

help:
	@echo "Auto_Stock Build & Test Commands:"
	@echo "  make test-hpo  : Run HPO pipeline test suite (tests/test_hpo_pipeline.py)"
	@echo "  make test-all  : Run all pytest suites"
	@echo "  make hpo-run   : Run 3-trial HPO optimization CLI"
	@echo "  make clean     : Clean temporary caches"

test-hpo:
	$(PYTEST) tests/test_hpo_pipeline.py -v

test-all:
	$(PYTEST) tests/ -v

hpo-run:
	$(PYTHON) scripts/run_hpo.py --n-trials 3 --symbol 005930 --output etc/hpo_results/baseline_hpo.csv --seed 42 --fast-mode

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__
