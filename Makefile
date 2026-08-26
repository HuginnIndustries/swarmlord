.DEFAULT_GOAL := help
.PHONY: help install check lint format fmt types test cov clean

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package and dev dependencies
	uv sync --dev

check: lint format types test  ## Run every gate CI runs

lint:  ## Lint with ruff
	uv run ruff check

format:  ## Verify formatting (does not modify files)
	uv run ruff format --check

fmt:  ## Apply formatting
	uv run ruff format

types:  ## Type-check with mypy --strict
	uv run mypy --strict src/swarmlord

test:  ## Run the test suite with coverage
	uv run pytest --cov

cov:  ## Run tests and write an HTML coverage report to htmlcov/
	uv run pytest --cov --cov-report=html

clean:  ## Remove build, cache, and coverage artifacts
	rm -rf build dist htmlcov .coverage coverage.xml
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
