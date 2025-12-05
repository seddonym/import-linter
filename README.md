<p align="center">
    <img src="docs/img/import-linter-logo.png" alt="Import Linter">
</p>

<p align="center">
    Lint your Python architecture.
</p>

<p align="center">
  <a href="https://pypi.org/project/import-linter" target="_blank">
      <img src="https://img.shields.io/pypi/v/import-linter.svg" alt="Package version">
  </a>
  <a href="https://pypi.org/project/import-linter" target="_blank">
      <img src="https://img.shields.io/pypi/pyversions/import-linter.svg" alt="Python versions">
  </a>
  <a href="https://github.com/seddonym/import-linter/actions/workflows/main.yml" target="_blank">
      <img src="https://github.com/seddonym/import-linter/actions/workflows/main.yml/badge.svg" alt="CI status">
  </a>
  <a href="https://opensource.org/licenses/BSD-2-Clause" target="_blank">
      <img src="https://img.shields.io/badge/License-BSD_2--Clause-orange.svg" alt="BSD license">
  </a>
</p>


**Import Linter** is a command-line tool for imposing constraints on the imports between your Python modules.

## 1. Install

Install `import-linter` using your favorite Python package manager (e.g. `pip install import-linter`).

## 2. Write a contract

Create a file called `.importlinter`, describing your contracts. For example:

```ini
[importlinter]
root_package = myproject

[importlinter:contract:mycontract]
name=Foo doesn't import bar or baz
type=forbidden
source_modules=
    myproject.foo
forbidden_modules=
    myproject.bar
    myproject.baz
```

## 3. Run the linter

```console
lint-imports
```

If your code violates the contract, you will see an error message that looks something like this:

![Screenshot of Import Linter output](docs/img/screenshot.png)

## Documentation

For more info, [read the docs](https://import-linter.readthedocs.io/).