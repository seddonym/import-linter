# Import Linter - AI Agent Guide

This guide helps AI coding agents understand the Import Linter codebase architecture and development practices.

## Project Overview

Import Linter is a command-line tool that enforces architectural constraints on imports between Python modules. It allows developers to define contracts that specify which modules can import from which other modules.

**Key capabilities:**
- Multiple contract types: forbidden, layers, independence, protected, acyclic_siblings
- Configuration via `.importlinter` files (INI or TOML format)
- Built on top of [Grimp](https://github.com/seddonym/grimp) for import graph analysis
- Supports custom contract types via plugin system

## Architecture

The project follows a **hexagonal (ports and adapters) architecture**:

```
src/importlinter/
├── domain/              # Core business logic, no external dependencies
│   ├── contract.py      # Base Contract class
│   ├── fields.py        # Field definitions for contracts
│   ├── imports.py       # Import-related domain objects
│   └── helpers.py       # Domain helper functions
├── application/         # Use cases and application logic
│   ├── use_cases.py     # Main lint_imports use case
│   ├── contract_utils.py # Contract loading and validation
│   ├── ports/           # Interfaces for external dependencies
│   └── ...
├── adapters/            # Implementations of ports
│   ├── building.py      # Graph building adapter
│   ├── filesystem.py    # File system operations
│   ├── timing.py        # Performance timing
│   └── user_options.py  # Configuration parsing
├── contracts/           # Built-in contract implementations
│   ├── forbidden.py     # Forbidden imports contract
│   ├── layers.py        # Layered architecture contract
│   ├── independence.py  # Module independence contract
│   ├── protected.py     # Protected modules contract
│   └── acyclic_siblings.py # Acyclic dependencies between siblings
├── cli.py               # Command-line interface
├── configuration.py     # Configuration file handling
└── api.py              # Public Python API
```

### Key Architectural Patterns

1. **Dependency Rule**: Dependencies flow inward only
   - Domain has no dependencies
   - Application depends on domain
   - Adapters depend on application and domain

2. **Ports and Adapters**: External dependencies are abstracted
   - Ports defined in `application/ports/`
   - Adapters implement ports in `adapters/`

3. **Contract Pattern**: All contracts inherit from `Contract` base class
   - Must implement `check()` method
   - Define fields using the fields system
   - Return `ContractCheck` result

## Contract System

### Creating a Contract

All contracts inherit from `importlinter.domain.contract.Contract` and must:

1. Define a `type_name` class attribute
2. Define fields using the field system (e.g., `StringField`, `ListField`)
3. Implement the `check(graph, verbose)` method

Example structure:

```python
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck

class MyContract(Contract):
    type_name = "mycontract"

    source_modules = fields.ListField(subfield=fields.StringField())
    forbidden_modules = fields.ListField(subfield=fields.StringField())

    def check(self, graph, verbose):
        # Implementation here
        return ContractCheck(kept=True, metadata={})
```

### Field Types

Available in `importlinter.domain.fields`:
- `StringField`: Single string value
- `ListField`: List of values (specify subfield type)
- `SetField`: Set of values
- `EnumField`: Choice from predefined options
- `BooleanField`: True/False value

Fields support:
- `required=True/False`: Whether field must be present
- `default`: Default value if not specified
- Validation and type coercion

### Contract Result

The `check()` method returns a `ContractCheck` object:

```python
ContractCheck(
    kept=True/False,      # Whether contract was satisfied
    warnings=[],          # List of warning messages
    metadata={}           # Additional data for rendering
)
```

## Common Development Tasks

### Running Tests

```bash
just test          # Fast tests with current Python version
just test-3-13     # Tests with Python 3.13
just test-all      # All tests across all Python versions (parallel)
```

### Code Quality

```bash
just format        # Format code with ruff
just lint          # Run all linters (ruff, mypy)
just check         # Full check before pushing (lint + docs + test-all)
```

### Documentation

```bash
just serve-docs    # View docs locally at http://localhost:8000
just build-docs    # Build docs without serving
```

### Adding a New Contract Type

1. Create file in `src/importlinter/contracts/`
2. Inherit from `Contract` class
3. Define `type_name` and fields
4. Implement `check()` method
5. Add to `__all__` in `src/importlinter/contracts/__init__.py`
6. Write unit tests in `tests/unit/contracts/`
7. Add integration tests using test assets in `tests/assets/`
8. Document in `docs/contract_types/`

### Working with Import Graphs

The `graph` parameter in `check()` is a Grimp `ImportGraph` object:

```python
# Check if chain exists
chain = graph.find_shortest_chain(
    importer="mypackage.a",
    imported="mypackage.b"
)
if chain:
    # Chain exists

# Get all imports
imports = graph.get_imports()

# Get descendants of a module
descendants = graph.find_descendants("mypackage.utils")
```

## Testing Strategy

### Unit Tests
- Located in `tests/unit/`
- Test individual functions and classes in isolation
- Use test doubles for dependencies
- Mock adapters available in `tests/adapters/`

### Integration Tests
- Use test packages in `tests/assets/`
- Test packages:
  - `testpackage/`: Main test package with various scenarios
  - `namespacepackages/`: Tests for namespace package support
- Configuration files use `.ini` or `.toml` format

### Test Helpers

Mock adapters available in `tests/adapters/`:
- `FakeFileSystem`: Mock file system operations
- `FakeUserOptions`: Mock configuration
- `FakePrinter`: Capture output

## Configuration Files

Import Linter reads configuration from `.importlinter` files (or custom paths).

**INI format example:**
```ini
[importlinter]
root_package = mypackage

[importlinter:contract:1]
name = Layer contract
type = layers
layers =
    high
    medium
    low
```

**TOML format example:**
```toml
[tool.importlinter]
root_package = "mypackage"

[[tool.importlinter.contracts]]
name = "Layer contract"
type = "layers"
layers = ["high", "medium", "low"]
```

## Key Files to Understand

1. **src/importlinter/cli.py**: Entry point for CLI
2. **src/importlinter/application/use_cases.py**: Main `lint_imports()` function
3. **src/importlinter/domain/contract.py**: Base `Contract` class
4. **src/importlinter/contracts/**: Built-in contract implementations
5. **src/importlinter/configuration.py**: Config file parsing
6. **src/importlinter/application/contract_utils.py**: Contract loading/registration

## Development Guidelines

1. **Follow the architecture**: Respect dependency directions (domain ← application ← adapters)
2. **Test thoroughly**: Unit tests for logic, integration tests for contracts
3. **Type hints**: All code should have type hints (checked with mypy)
4. **No over-engineering**: Keep solutions simple and focused on the immediate need
5. **Update docs**: Add documentation for new features in `docs/`
6. **Update release notes**: Add entry to `docs/release_notes.md`

## Useful Commands

```bash
# See all available commands
just

# Install pre-commit hooks
just install-precommit

# Run specific Python version tests
just test-3-10
just test-3-11
just test-3-12
just test-3-13

# Check Import Linter on itself
lint-imports
```

## External Dependencies

- **grimp**: Import graph analysis library (>=3.14)
- **click**: CLI framework (>=6)
- **rich**: Terminal formatting (>=14.2.0)
- **tomli**: TOML parsing for Python <3.11
- **typing-extensions**: Type hint backports (>=3.10.0.0)

## Resources

- [Documentation](https://import-linter.readthedocs.io/)
- [GitHub Repository](https://github.com/seddonym/import-linter/)
- [Contributing Guide](docs/contributing.md)
- [Custom Contract Types Guide](docs/custom_contract_types.md)
