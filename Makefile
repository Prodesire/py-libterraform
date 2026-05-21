# Env
export PYTHONDONTWRITEBYTECODE=1
TEST_PATH=./tests
UV_PYTHON_FLAG=$(if $(PY),--python $(PY),)

help:
	@echo "\033[32minit\033[0m"
	@echo "    Init environment for libterraform."
	@echo "\033[32mtest\033[0m"
	@echo "    Run pytest. Please run \`make build\` first."
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

init:
	uv sync $(UV_PYTHON_FLAG)

test: clean-pyc
	uv run $(UV_PYTHON_FLAG) pytest --color=yes $(TEST_PATH)

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
	uv run ruff check --fix libterraform tests
	uv run ruff format libterraform tests
