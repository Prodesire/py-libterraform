# Env
export PYTHONDONTWRITEBYTECODE=1
TEST_PATH=./tests
PY3=python3

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
	$(PY3) -m pip install poetry pytest

test: clean-pyc
	$(PY3) -m pytest --color=yes $(TEST_PATH)

build:
	$(PY3) -m poetry build -f wheel

publish:
	$(PY3) -m poetry publish

clean: clean-pyc clean-build

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-build:
	rm -rf build dist *.egg-info .eggs
	find . -name '*.h' -exec rm -f {} +
