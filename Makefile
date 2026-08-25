.PHONY: unit-test test lint help

# Shared virtualenv lives in the sibling core checkout (same-folder layout).
PYTHON ?= ../ce-mongo-x-ray/.venv/bin/python

# Run the unit tests (excludes integration tests)
unit-test:
	@echo "Running unit tests..."
	$(PYTHON) -m pytest -m "not integration"
	@echo "\033[32m✓ All unit tests passed!\033[0m"

test: unit-test

# Run ruff lint and format checks
lint:
	@echo "Running ruff check..."
	$(PYTHON) -m ruff check src tests
	@echo "Running ruff format check..."
	$(PYTHON) -m ruff format --check src tests
	@echo "\033[32m✓ No lint errors found!\033[0m"

help:
	@echo "mongo-x-ray-risk-register Makefile"
	@echo ""
	@echo "  make unit-test  - Run the unit tests"
	@echo "  make test       - Alias for unit-test"
	@echo "  make lint       - Run ruff check and ruff format check"
