.PHONY: install uninstall run stop test lint format help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install as desktop application
	@case "$$(uname -s)" in \
	  Linux)  bash install.sh ;; \
	  Darwin) bash install-macos.sh ;; \
	  *)      echo "Unsupported OS. Run install.sh, install-macos.sh, or install.ps1 manually." ;; \
	esac

uninstall: ## Remove desktop entry (keeps project files)
	@case "$$(uname -s)" in \
	  Linux)  bash uninstall.sh ;; \
	  Darwin) bash uninstall-macos.sh ;; \
	  *)      echo "Unsupported OS." ;; \
	esac

run: ## Start the server directly (foreground)
	./run.sh

stop: ## Stop a running instance
	.venv/bin/python launcher.py --stop

test: ## Run tests with coverage
	pytest --cov=app --cov-report=term-missing

lint: ## Lint and check formatting
	ruff check app tests
	ruff format --check --diff app tests

format: ## Auto-format code
	ruff format app tests
	ruff check --fix app tests

dev: ## Install dev deps
	.venv/bin/pip install -r requirements-dev.txt
