# Compuertas de calidad del proyecto.
#
# Estos mismos targets los invoca el CI, para que los comandos no puedan
# divergir entre una maquina y el pipeline. Si el comando anda aca, anda alla.
#
# En local las herramientas se toman del virtualenv del proyecto. En CI, que
# instala en el Python del runner y no crea un venv, se usan las del PATH.

VENV    := .venv
ifneq ($(wildcard $(VENV)/bin/python),)
  BIN   := $(VENV)/bin/
else
  BIN   :=
endif

PY      := $(BIN)python
PIP     := $(BIN)pip
RUFF    := $(BIN)ruff
MYPY    := $(BIN)mypy
PYTEST  := $(PY) -m pytest

SRC     := app.py router.py doc_selector.py groq_client.py pdf_utils.py tabla_utils.py ingesta.py
PATHS   := $(SRC) scripts tests

.DEFAULT_GOAL := help
.PHONY: help venv install install-e2e run test test-cov test-e2e lint format format-check typecheck check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtualenv if it does not exist
	@test -d $(VENV) || python3 -m venv $(VENV)

install: venv ## Install runtime and development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install-e2e: install ## Install the Chromium browser Playwright drives
	$(VENV)/bin/playwright install --with-deps chromium

run: ## Start the Streamlit app locally
	$(VENV)/bin/streamlit run app.py

test: ## Run the unit test suite (excludes end-to-end tests)
	$(PYTEST)

test-cov: ## Run unit tests with a coverage report
	$(PYTEST) --cov --cov-report=term-missing --cov-report=xml

test-e2e: ## Run end-to-end tests against a real browser
	$(PYTEST) -m e2e

lint: ## Report lint violations
	$(RUFF) check $(PATHS)

format: ## Rewrite files to the canonical format and fix safe lint issues
	$(RUFF) format $(PATHS)
	$(RUFF) check --fix $(PATHS)

format-check: ## Fail if any file is not canonically formatted
	$(RUFF) format --check $(PATHS)

typecheck: ## Run static type checking
	$(MYPY) $(SRC) scripts

check: lint format-check typecheck test ## Run every gate CI runs

clean: ## Remove build, cache and coverage artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" -exec rm -rf {} +
