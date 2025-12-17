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
**Import Linter** is a command-line tool for imposing constraints on the imports between your Python modules.

[Get started](get_started/configure.md){ .md-button .button-center }
</div>

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

