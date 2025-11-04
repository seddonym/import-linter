# List available recipes.
help:
    @just --list

# Set up Git precommit hooks for this project (recommended).
install-precommit:
    @uv run pre-commit install

# Runs tests under the latest supported Python version.
test:
    @uv run pytest

# Runs tests under all supported Python versions, in parallel.
[parallel]
test-all: test-3-9 test-3-10 test-3-11 test-3-12 test-3-13 test-3-14
# Note that all recipes called from this must use UV_LINK_MODE=copy,
# otherwise the parallelism can corrupt the virtual environments.

# Runs tests under Python 3.9.
test-3-9:
    @UV_LINK_MODE=copy UV_PYTHON=3.9 just test

# Runs tests under Python 3.10.
test-3-10:
    @UV_LINK_MODE=copy UV_PYTHON=3.10 just test

# Runs tests under Python 3.11.
test-3-11:
    @UV_LINK_MODE=copy UV_PYTHON=3.11 just test

# Runs tests under Python 3.12.
test-3-12:
    @UV_LINK_MODE=copy UV_PYTHON=3.12 just test

# Runs tests under Python 3.13.
test-3-13:
    @UV_LINK_MODE=copy UV_PYTHON=3.13 just test

# Runs tests under Python 3.14.
test-3-14:
    @UV_LINK_MODE=copy UV_PYTHON=3.14 just test


# Format the code.
format:
    @uv run ruff format

# Run linters.
lint:
    @echo Running ruff format...
    @uv run ruff format --check
    @echo Running ruff check...
    @uv run ruff check
    @echo Running mypy...
    @uv run mypy src/importlinter tests
    @echo Running Import Linter...
    @uv run lint-imports
    @echo
    @echo '👍 {{GREEN}} Linting all good.{{NORMAL}}'

# Fix any ruff errors
autofix:
    @uv run ruff check --fix

# Build docs.
build-docs:
    @uv run --group=docs sphinx-build -b html docs dist/docs --fail-on-warning --fresh-env --quiet

# Build docs and open in browser.
build-and-open-docs:
    @just build-docs
    @open dist/docs/index.html

# Run all linters, build docs and tests.
check:
    @UV_PYTHON=3.10 just lint  # See .github/workflows/main.yml for why.
    @just lint
    @just build-docs
    @just test-all
    @echo '👍 {{GREEN}} Linting, docs and tests all good.{{NORMAL}}'

# Upgrade Python code to the supplied version. (E.g. just upgrade 310)
upgrade-python MIN_VERSION:
    @find {docs,src,tests} -name "*.py" -not -path "tests/assets/*" -exec uv run pyupgrade --py{{MIN_VERSION}}-plus --exit-zero-even-if-changed {} +
    @just autofix
    @just format
