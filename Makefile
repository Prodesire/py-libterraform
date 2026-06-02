# Env
export PYTHONDONTWRITEBYTECODE=1
TEST_PATH=./tests
UV_PYTHON_FLAG=$(if $(PY),--python $(PY),)
PYTHON_CHECK_PATHS=src tests scripts
GIT_HOOKS_PATH=scripts/git-hooks

.PHONY: help install install-hooks test lint build publish clean clean-pyc clean-build format

help:
	@echo "\033[32minstall\033[0m"
	@echo "    Install dependencies and Git hooks for libterraform."
	@echo "\033[32minstall-hooks\033[0m"
	@echo "    Install Git hooks."
	@echo "\033[32mtest\033[0m"
	@echo "    Run pytest. Please run \`make build\` first."
	@echo "\033[32mlint\033[0m"
	@echo "    Run Ruff and ty checks."
	@echo "\033[32mformat\033[0m"
	@echo "    Format Python files with Ruff."
	@echo "\033[32mbuild\033[0m"
	@echo "    Build libterraform."
	@echo "\033[32mpublish\033[0m"
	@echo "    Publish libterraform to PyPI."
	@echo "\033[32mclean\033[0m"
	@echo "    Remove python and build artifacts."
	@echo "\033[32mclean-pyc\033[0m"
	@echo "    Remove python artifacts."
	@echo "\033[32mclean-build\033[0m"
	@echo "    Remove build artifacts."

install:
	uv sync $(UV_PYTHON_FLAG)
	$(MAKE) install-hooks

install-hooks:
	git config core.hooksPath $(GIT_HOOKS_PATH)
	@echo "Git hooks installed from $(GIT_HOOKS_PATH)."

test: clean-pyc
	uv run $(UV_PYTHON_FLAG) pytest --color=yes $(TEST_PATH)

lint:
	uv run $(UV_PYTHON_FLAG) ruff check $(PYTHON_CHECK_PATHS)
	uv run $(UV_PYTHON_FLAG) ty check $(PYTHON_CHECK_PATHS)

build:
	uv build --wheel $(UV_PYTHON_FLAG)

publish:
	uv publish

clean: clean-pyc clean-build

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-build:
	rm -rf build dist *.egg-info .eggs
	find . -name '*.h' -exec rm -f {} +

format:
	uv run $(UV_PYTHON_FLAG) ruff check --fix $(PYTHON_CHECK_PATHS)
	uv run $(UV_PYTHON_FLAG) ruff format $(PYTHON_CHECK_PATHS)
