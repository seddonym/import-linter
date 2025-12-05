# Run the linter

Import Linter provides a single command: `lint-imports`.

Running this will check that your project adheres to the contracts you've defined.

**Arguments:**

- `--config`:
  The configuration file to use. This overrides the default file search strategy.
  By default it's assumed that the file is an ini-file unless the file extension is `toml`.
  (Optional.)
- `--contract`:
  Limit the check to the contract with the supplied id. In INI files, a contract's id is
  the final part of the section header: for example, the id for a contract with a section
  header of `[importlinter:contract:foo]` is `foo`. In TOML files, ids are supplied
  explicitly with an `id` key. This option may be provided multiple
  times to check more than one contract. (Optional.)
- `--cache-dir`:
  The directory to use for caching. Defaults to `.import_linter_cache`. See [Caching](../caching.md). (Optional.)
- `--no-cache`:
  Disable caching. See [Caching](../caching.md). (Optional.)
- `--show-timings`:
  Display the times taken to build the graph and check each contract. (Optional.)
- `--verbose`:
  Noisily output progress as it goes along. (Optional.)

#### Default usage

```console
lint-imports
```

#### Using a different filename or location

```console
lint-imports --config path/to/alternative-config.ini
```

#### Checking only certain contracts

```console
lint-imports --contract some-contract --contract another-contract
```

#### Customizing cache behavior

Using a different cache directory, or disabling caching

```console
lint-imports --cache-dir path/to/cache

lint-imports --no-cache
```

#### Showing timings

```console
lint-imports --show-timings
```

#### Verbose mode

```console
lint-imports --verbose
```

### Running using pre-commit

It is possible to run Import Linter as a [pre-commit](https://pre-commit.com) hook.
However, this must use `language: system` to allow Import Linter to analyze your packages from within
a virtual environment.

Assuming you're running pre-commit from within your virtual environment,
you can include this in your `.pre-commit-config.yaml` file:

```yaml
repos:
- repo: local
  hooks:
  - id: lint_imports
    name: "Lint imports"
    entry: "lint-imports"  # Adapt with custom arguments, if need be.
    language: system
    pass_filenames: false
```

Or, if you prefer pre-commit to install Import Linter separately, you can do this (replacing `<import linter version>`
with the version number of Import Linter you wish to use):

```yaml
- repo: https://github.com/seddonym/import-linter
  rev: <import linter version>
  hooks:
  - id: import-linter
```
