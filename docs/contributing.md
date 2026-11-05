# Contributing

We welcome contributions to Import Linter.

## Bug reports

When [reporting a bug](https://github.com/seddonym/import-linter/issues) please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

## Feature requests and feedback

The best way to send feedback is to file an issue at https://github.com/seddonym/import-linter/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible.
* Remember that this is a volunteer-driven project.

## Submitting pull requests

Before spending time working on a pull request, we highly recommend filing a Github issue and engaging with the
project maintainer (David Seddon) to align on the direction you're planning to take. This can save a lot of your
precious time!

This doesn't apply to trivial pull requests such as spelling corrections.

For merging, you should:

1. Include passing tests (run `just test-all`).
2. Update documentation when there's new API, functionality etc.
3. Add a note to `docs/release_notes.md` about the changes.
4. Add yourself to `docs/authors.md` (in alphabetical order).

## Development

### System prerequisites

Make sure these are installed first.

- [git](https://github.com/git-guides/install-git)
- [uv](https://docs.astral.sh/uv/#installation)
- [just](https://just.systems/man/en/packages.html)

### Setup

You don't need to activate or manage a virtual environment - this is taken care in the background of by `uv`.

1. Fork [import-linter](https://github.com/seddonym/import-linter)
   (look for the "Fork" button).
2. Clone your fork locally:

    ```console
    git clone git@github.com:your_name_here/import-linter.git
    ```

3. Change into the directory you just cloned:

    ```console
    cd import-linter
    ```

4. Set up pre-commit. (Optional, but recommended.):

    ```console
    just install-precommit
    ```

You will now be able to run commands prefixed with `just`, providing you're in the Import Linter directory.
To see available commands, run `just`.

### Formatting code

```console
just format
```

### Running linters

```console
just lint
```

### Running tests

When you're developing a feature, you'll probably want to run tests quickly, using just the latest supported Python version:

```console
just test
```

You can also pass a specific Python version, e.g. `just test --python=3.13`.

If you want to invoke pytest directly, e.g. to run a specific test, just use `uv run pytest`, e.g.:

```console
uv run pytest tests/unit/contracts
```

Finally, you can run all the tests under all supported Python versions with `just test-all`. This gives a more complete
picture of whether the changes are compatible with all supported versions. Additionally, it will run tests under the
*lowest* versions of dependencies specified in `pyproject.toml`, with the lowest supported Python version. 

### Before you push

It's a good idea to run `just check` before getting a review. This will run linters, docs build and tests under
every supported Python version.

### Building documentation

To view docs locally: 

```console
just serve-docs
```

Or, if you just want to build them:

```console
just build-docs
```

## Supported Python versions

The set of supported Python versions is driven by the
`Programming Language :: Python :: 3.X` classifiers in `pyproject.toml`. `noxfile.py` reads these (via
`nox.project.python_versions`) to decide which versions to test under, so CI and `just test-all` pick up
changes automatically. The lower bound is also declared once in `requires-python`, which ruff uses to infer
its target version.

### Supporting a new Python version

1. Add a `"Programming Language :: Python :: 3.X"` classifier for the new version in `pyproject.toml`.
2. Update the default in the `test` recipe in `justfile` (e.g. `test python="3.14"`) to the new version, so
   that `just test` runs under the latest supported version.
3. Add a note to `docs/release_notes.md` in the form "Officially support Python 3.x."

### Dropping support for an old Python version

1. In `pyproject.toml`:

     - Bump `requires-python` in `pyproject.toml` to the new lowest version (e.g. `">=3.11"` → `">=3.12"`).
     - Remove the `"Programming Language :: Python :: 3.X"` classifier for the dropped version.
     - Update `python_version` under `[tool.mypy]` to the new lowest version. (Unlike ruff, mypy has no
       inference from `requires-python`, so this must be set explicitly.)
     - Remove any dependencies carrying a `python_version < '3.x'` marker for the old version.

2. Across the code base, remove any redundant `sys.version_info` checks that reference the unsupported Python version.
3. Run `just upgrade-python 312` (pass the new lowest version, without the dot).
   This will modernize the code for the new floor.
4. Run `just test-all`.
5. Run `uv lock`.
6. Add a note to `docs/release_notes.md` in the form "Drop support for Python 3.x."

## Releasing to Pypi

(Only maintainers can do this.)

1. Choose a new version number (based on [semver](https://semver.org/)).
2. `git pull origin main`
3. Update `docs/release_notes.md` with the new version number.
4. Update the `__version__` variable in `src/importlinter/__init__.py` with the new version number.
5. Update `project.version` in `pyproject.toml` with the new version number.
6. ``uv lock`` to sync ``uv.lock`` with the new version.
7. `git commit -am "Release v{new version number"`
8. `git push`
9. Wait for tests to pass on CI.
10. `git tag v{new version number}`
11. `git push --tags`
12. This should kick start the Github `release` workflow which releases the project to PyPI.
