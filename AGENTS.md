# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

Import Linter lets users impose constraints (contracts) on the imports between Python modules, and
includes a browser-based UI for exploring a package's import graph. It uses
[grimp](https://github.com/seddonym/grimp) to build the import graph it analyses.

## Commands

Uses `uv` + `just`. Common recipes (see `justfile`):

```
just lint                  # ruff format --check, ruff check, mypy, lint-imports (self-check)
just autofix               # ruff check --fix
just format                # ruff format
just test                  # run tests via nox on default Python (3.15)
just test 3.11              # run tests on a specific Python version
just test-all               # run tests on all supported Python versions via nox
just build-docs             # build mkdocs site
just serve-docs             # serve docs locally
just check                  # lint + build-docs + test-all
```

Running a single test (bypass nox, use pytest directly in the uv env):

```
uv run pytest tests/unit/contracts/test_layers.py::test_name
uv run pytest -m "not no_ui_deps_installed"   # most tests; the default nox session's marker
uv run pytest -m "no_ui_deps_installed"       # tests specific to the `ui` extra NOT installed
```

Note: most tests assume the `ui` extra is installed; a small subset (marked `no_ui_deps_installed`)
specifically test behaviour when it isn't. When adding tests, mark them if they belong in that
latter group.

The project lints its own architecture: `lint-imports` runs against `.importlinter` in this repo,
and `just lint` will fail if a change introduces a disallowed import.

## Architecture

The codebase follows a ports-and-adapters (hexagonal) style, and this layering is itself enforced
by `.importlinter`'s `layers` contract on the `importlinter` package, from lowest to highest:

```
domain -> application -> adapters -> configuration -> contracts -> api -> ui -> cli
```

(Each layer may only be imported by layers above it in this list.)

- **`domain/`** — Core model with no external dependencies beyond `grimp`. `contract.py` defines
  the abstract `Contract` base class (fields → validation → `check()` → `render_broken_contract()`)
  and the global `ContractRegistry` (`registry`) that maps contract `type` names to classes.
  `fields.py` defines the declarative field types contracts use to parse/validate their options.
- **`application/`** — Orchestration logic, expressed against abstract **ports**
  (`application/ports/*.py`: `building`, `filesystem`, `reporting`, `timing`, `user_options`).
  `use_cases.py` is the main entry point (`lint_imports`) — it reads config, builds/shares import
  graphs across contracts that need the same graph configuration, runs each contract's `check()`,
  and renders a `Report`. `app_config.settings` is a simple runtime-configurable settings object
  used to inject different port implementations (e.g. for tests).
- **`adapters/`** — Concrete implementations of the application ports (e.g. `building.py` wraps
  grimp to build the real `ImportGraph`, `filesystem.py` wraps real file I/O, `user_options.py`
  parses actual `.ini`/`.toml` config files).
- **`configuration.py`** — Wires up adapters into `settings` at startup, and registers built-in
  contract types into the `registry`.
- **`contracts/`** — The built-in contract types (`layers`, `independence`, `forbidden`,
  `protected`, `acyclic_siblings`), each a `Contract` subclass. `_common.py` holds shared logic.
  New contract types are registered via `registry.register(contract_class, name)` and referenced
  in user config by that `type` name.
- **`api.py`** — Stable programmatic entry point for calling import-linter from other Python code.
- **`ui/`** — The FastAPI-based browser UI for exploring a graph (`server.py` routes/app,
  `explorer.py` graph-exploration logic). Depends on the optional `ui` extras group
  (`fastapi`/`uvicorn`), so code here must not be imported by lower layers.
- **`cli.py`** — Click-based CLI entry points (`lint-imports`, `import-linter ...`).

### Config and contracts

A user's `.importlinter`/`pyproject.toml` config defines one or more contracts, each with a `type`
corresponding to a registered contract class. Multiple config files/sources can be linted in one
run; `use_cases.py` builds only as many distinct `ImportGraph`s as there are distinct graph
configurations (root packages, `include_external_packages`, `exclude_type_checking_imports`), and
shares each graph across every contract that needs that configuration.

### Tests

`tests/` mirrors `src/importlinter/` (`unit/domain`, `unit/application`, `unit/contracts`,
`unit/adapters`, `unit/ui`). `tests/functional/` exercises the CLI/API end-to-end against sample
packages under `tests/assets/` (built as real importable packages for grimp to analyse).
`tests/helpers/` has shared test fixtures/utilities.
