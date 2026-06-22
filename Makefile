# Env
export PYTHONDONTWRITEBYTECODE=1
TEST_PATH=./tests
UV_PYTHON_FLAG=$(if $(PY),--python $(PY),)
PYTHON_CHECK_PATHS=src tests scripts
GO_CHECK_PATHS=native/go
GIT_HOOKS_PATH=scripts/git-hooks
DOCS_PORT?=8000

.PHONY: help install test lint build inspect-upstream doc-build doc-serve publish clean format

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and Git hooks
	uv sync $(UV_PYTHON_FLAG)
	git config core.hooksPath $(GIT_HOOKS_PATH)
	@echo "Git hooks installed from $(GIT_HOOKS_PATH)."

test: clean ## Run pytest (run `make build` first)
	uv run $(UV_PYTHON_FLAG) pytest --color=yes $(TEST_PATH)

lint: ## Run Ruff, ty, and Go formatting checks
	uv run $(UV_PYTHON_FLAG) ruff check $(PYTHON_CHECK_PATHS)
	uv run $(UV_PYTHON_FLAG) ty check $(PYTHON_CHECK_PATHS)
	@files="$$(gofmt -l $(GO_CHECK_PATHS))"; \
	if [ -n "$$files" ]; then \
		echo "$$files"; \
		exit 1; \
	fi

build: ## Build libterraform
	uv build --wheel $(UV_PYTHON_FLAG)

inspect-upstream: ## Inspect Terraform release and bridge drift
	uv run $(UV_PYTHON_FLAG) python scripts/inspect_upstream.py --releases-url https://releases.hashicorp.com/terraform/

doc-build: ## Build the documentation site
	rm -rf site
	uv run $(UV_PYTHON_FLAG) --group docs zensical build --strict -f zensical.toml
	uv run $(UV_PYTHON_FLAG) --group docs zensical build --strict -f zensical.zh.toml

doc-serve: ## Serve the documentation site locally
	$(MAKE) doc-build
	@echo "Docs available at http://localhost:$(DOCS_PORT)/ (zh: http://localhost:$(DOCS_PORT)/zh/)"
	uv run $(UV_PYTHON_FLAG) python -m http.server $(DOCS_PORT) --bind 127.0.0.1 --directory site

publish: ## Publish libterraform to PyPI
	uv publish

clean: ## Remove python and build artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf build dist *.egg-info .eggs
	find . -name '*.h' -exec rm -f {} +

format: ## Format Python and Go files
	uv run $(UV_PYTHON_FLAG) ruff check --fix $(PYTHON_CHECK_PATHS)
	uv run $(UV_PYTHON_FLAG) ruff format $(PYTHON_CHECK_PATHS)
	gofmt -w $(GO_CHECK_PATHS)
