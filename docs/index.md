<style>
    .md-content .md-typeset h1 { display: none; }
    .md-sidebar--primary,
    .md-sidebar--secondary { display: none !important; }
    h2.slogan { text-align: center; font-size: 2em; margin-bottom: 2em; }
    .logo-wrapper { text-align: center; }
    .centered { text-align: center; }
</style>

<div class="logo-wrapper" markdown>
![Import Linter](img/import-linter-logo-text.png#only-dark)
![Import Linter](img/import-linter-logo-text-white.png#only-light)
</div>

<h2 class="slogan">Lint your Python architecture.</h2>

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

---

<div class="centered" markdown>
**Import Linter** allows you to impose constraints on the imports between your Python modules.

It also provides a browser-based user interface for exploring the architecture of any Python package.

[Get started](get_started/install.md){ .md-button .button-center }
[Try the Interactive UI](ui.md){ .md-button .button-center }
</div>

---

## How it works

Let's say your Python project looks like this:

```text
myproject
├── __init__.py
├── blue/
└── green/
```

After [installation](get_started/install.md), create a file called `.importlinter`:

```ini
# .importlinter

[importlinter]
root_package = myproject

[importlinter:contract:one]
name = Green must not import blue
type = forbidden
source_modules = myproject.green
forbidden_modules = myproject.blue
```

Then, running `lint-imports` will error if any modules in `myproject.green` import from `myproject.blue`.

That's just a simple example: Import Linter supports lots of different contract types, and you can even create your own!

## Contract types

<div class="flowcard" markdown>
:material-block-helper:{ .lg .middle } __Forbidden__

---

Prevent one set of modules being imported by another.

[:octicons-arrow-right-24: Read more](contract_types/forbidden.md)
</div>

<div class="flowcard" markdown>
:material-folder-arrow-left:{ .lg .middle } __Protected__

---

Prevent modules from being directly imported, except by modules in an allow-list.

[:octicons-arrow-right-24: Read more](contract_types/protected.md)
</div>

<div class="flowcard" markdown>
:material-layers-triple:{ .lg .middle } __Layers__

---

Enforce a 'layered architecture'.

[:octicons-arrow-right-24: Read more](contract_types/layers.md)
</div>

<div class="flowcard" markdown>
:fontawesome-solid-grid-horizontal:{ .lg .middle } __Independence__

---

Prevent a set of modules depending on each other.

[:octicons-arrow-right-24: Read more](contract_types/independence.md)  
</div>

<div class="flowcard" markdown>
:material-graph-outline:{ .lg .middle } __Acyclic siblings__

---

Forbid dependency cycles between siblings.

[:octicons-arrow-right-24: Read more](contract_types/acyclic_siblings.md)
</div>

<div class="flowcard" markdown>
:material-set-square:{ .lg .middle } __Custom contract types__

---

Design your own architecture.

[:octicons-arrow-right-24: Read more](custom_contract_types.md)
</div>
