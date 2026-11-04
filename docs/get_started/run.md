# Run the linter

To check that your project adheres to the contracts you've defined, run:

```console
lint-imports
```

(Or you can use the alias `import-linter lint` if you prefer.)

**Arguments:**

- `CONFIG_FILES`:
  One or more configuration files to check, in a single run. This overrides the default file search strategy.
  See [Using more than one configuration file](#using-more-than-one-configuration-file). (Optional.)

**Options:**

- `--config`:
  The configuration file to use. This overrides the default file search strategy.
  By default it's assumed that the file is an ini-file unless the file extension is `toml`.
  If configuration files are also passed as arguments, this file is checked first.
  (Optional.)
- `--contract`:
  Limit the check to the contract with the supplied id. In INI files, a contract's id is
  the final part of the section header: for example, the id for a contract with a section
  header of `[importlinter:contract:foo]` is `foo`. In TOML files, ids are supplied
  explicitly with an `id` key. If more than one configuration file uses the same id, prefix the id with the
  filename and a colon, e.g. `--contract=path/to/config.ini:foo`. This option may be provided multiple
  times to check more than one contract. (Optional.)
- `--cache-dir`:
  The directory to use for caching. Defaults to `.import_linter_cache`. See [Caching](../caching.md). (Optional.)
- `--no-cache`:
  Disable caching. See [Caching](../caching.md). (Optional.)
- `--debug`:
  Run in debug mode. Exceptions are not swallowed at the top level, so the full stack
  trace can be seen — useful when investigating or reporting a bug. (Optional.)
- `--show-timings`:
  Display the times taken to build the graph and check each contract. (Optional.)
- `--no-logo`:
  Hide the logo at startup. (Optional.)
- `--verbose`:
  Noisily output progress as it goes along. (Optional.)
- `--version`:
  Display the version of Import Linter and exit. (Optional.)

#### Default usage

```console
lint-imports
```

#### Using a different filename or location

```console
lint-imports --config path/to/alternative-config.ini
```

#### Using more than one configuration file

Contracts can be split across several files (for example, so that different teams can own their own contracts)
and checked in a single run:

```console
lint-imports main.ini extra_contracts/*.ini
```

Each file is a complete configuration file, with its own [top level configuration](configure.md#top-level-configuration).
Building the import graph is usually the slowest part of a run, so Import Linter only builds it once for all
the files that share the same top level configuration (`root_packages`, `include_external_packages` and
`exclude_type_checking_imports`). Files with a different top level configuration get a graph of their own.

Import Linter doesn't expand globs itself: in the example above, the shell does that. Any file that is
passed more than once is only checked once.

#### Checking only certain contracts

```console
lint-imports --contract some-contract --contract another-contract
```

If you're using more than one configuration file and the same id appears in more than one of them, include the
filename (relative to the current working directory) to say which one you mean:

```console
lint-imports main.ini extra_contracts/*.ini --contract=extra_contracts/two.ini:some-contract
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

#### Debug mode

Run in debug mode, showing full stack traces:

```text
lint-imports --debug
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
