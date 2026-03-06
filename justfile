# List available recipes.
help:
    @just --list

# Set up Git precommit hooks for this project (recommended).
install-precommit:
    @uv run pre-commit install

# Run nox.
nox *args:
    @uv run --group nox nox {{args}}

# Runs tests under the supplied Python version.
test python="3.14":
    @just nox --python {{python}}

# Runs tests under all supported Python versions.
test-all:
    @uv run --group nox nox


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
    @echo Linting imports...
    @uv run lint-imports
    @echo
    @echo '👍 {{GREEN}} Linting all good.{{NORMAL}}'

# Fix any ruff errors
autofix:
    @uv run ruff check --fix

# Build docs.
build-docs:
    @uv run --group=docs mkdocs build --site-dir dist/docs

# Serve docs in a browser.
serve-docs:
    @uv run --group=docs mkdocs serve --open

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
