Changelog
=========

2.7 (2025-11-19)
----------------

* Print using rich instead of click.
* Remove pluggable Printer class.
* Add ascii art logo.
* Add progress animations when building graph and checking contracts.

2.6 (2025-11-10)
----------------

* Add `acyclic_siblings` contract type.
* Add contract field `IntegerField`.
* Drop support for Python 3.9.

2.5.2 (2025-10-09)
------------------

* Fix build issue with PyPI description.

2.5.1 (2025-10-09)
------------------

* Correct documentation that incorrectly stated that protected modules
  are allowed to import each other.
* Officially support Python 3.14.

2.5 (2025-09-15)
----------------

* Add protected contract type.

2.4 (2025-08-15)
----------------

* Fix incorrect handling of unicode characters in TOML files on Windows.
* Change pre-commit hook to use the system virtualenv and to run whenever
  any file changes, not just a Python file.
* Fix RecursionError when running repr on a ModuleExpression.
* Fix messages being always colored white on Windows.
* Upgrade latest tox requirements (fixing error with `tox -echeck`).
* Rename default Git repository branch to 'main'.
* Increase accuracy of timings when using --show-timings.

2.3 (2025-03-11)
----------------

* Add as_packages field to forbidden contracts.
* Improve performance of parsing module / import expressions.

2.2 (2025-02-07)
----------------

* Add support for wildcards in layers contract containers.
* Improve performance of `helpers.pop_imports`.

2.1 (2024-10-8)
---------------

* Add support for wildcards in forbidden and independence contracts.
* Formally support Python 3.13.
* Drop support for Python 3.8.

2.0 (2024-1-9)
--------------

* Add support for non-independent sibling modules in layer contracts.
* In `importlinter.contracts.layers`, `Layer` and `LayerField` 
  have changed their API slightly. This could impact custom
  contract types depending on these classes. 

1.12.1 (2023-10-30)
-------------------

* Add ability to exclude imports made in type checking guards via ``exclude_type_checking_imports`` setting.
* Update to Grimp 3.1.

1.12.0 (2023-09-24)
-------------------

* Officially support Python 3.12.
* Fix error when using `click` version 6.0 and 7.0 (#191).
* Allow extra whitespace around the module names in import expressions.
* Ignore blank lines in multiple value fields.
* Fix bug with allow_indirect_imports in forbidden contracts.
  Prior to this fix, forbidden contracts with allow_indirect_imports
  only checked imports between the source/forbidden modules specified,
  not the descendants of those modules.

1.11.1 (2023-08-21)
-------------------

* Fix bug that was preventing sibling layers being used in a containerless contract.

1.11.0 (2023-08-18)
-------------------

* Update to Grimp 3.0.

1.11b1 (2023-08-17)
-------------------

* Update to Grimp 3.0b3.
* Use Grimp's find_illegal_dependencies_for_layers method in independence contracts.
* Add ability to define independent siblings in layers contracts.

1.10.0 (2023-07-06)
-------------------

* Recursive wildcard support for ignored imports.
* Drop support for Python 3.7.
* Use grimp.ImportGraph instead of importlinter.domain.ports.graph.ImportGraph.
* Use Grimp's find_illegal_dependencies_for_layers method in layers contracts.

1.9.0 (2023-05-13)
------------------

* Update to Grimp 2.4.
* Forbidden contracts: when include_external_packages is true, error if an external subpackage is
  a forbidden module.

1.8.0 (2023-03-03)
------------------

* Add caching.

1.7.0 (2023-01-27)
------------------

* Switch from optional dependency of ``toml`` to required dependency of ``tomli`` for Python versions < 3.11.
* Use DetailedImport type hinting made available in Grimp 2.2.
* Allow limiting by contract.

1.6.0 (2022-12-7)
-----------------

* Add exhaustiveness option to layers contracts.

1.5.0 (2022-12-2)
-----------------

* Officially support Python 3.11.

1.4.0 (2022-10-04)
------------------

* Include py.typed file in package data to support type checking
* Remove upper bounds on dependencies. This allows usage of Grimp 2.0, which should significantly speed up checking of
  layers contracts.
* Add --verbose flag to lint-imports command.
* Improve algorithm for independence contracts, in the following ways:
    - It is significantly faster.
    - As with layers contracts, reports of illegal indirect imports reports now include multiple start
      and end points (if they exist).
    - Illegal indirect imports that are via other modules listed in the contract are no longer listed.

1.3.0 (2022-08-22)
------------------

* Add Python API for reading configuration.
* Add support for namespace packages.

1.2.7 (2022-04-04)
------------------

* Officially support Python 3.10.
* Drop support for Python 3.6.
* Add support for default Field values.
* Add EnumField.
* Support warnings in contract checks.
* Add unmatched_ignore_imports_alerting option for each contract.
* Add command line argument for showing timings.

1.2.6 (2021-09-24)
------------------

* Fix bug with ignoring external imports that occur multiple times in the same module.

1.2.5 (2021-09-21)
------------------

* Wildcard support for ignored imports.
* Convert TOML booleans to strings in UserOptions, to make consistent with INI file parsing.

1.2.4 (2021-08-09)
------------------

* Fix TOML installation bug.

1.2.3 (2021-07-29)
------------------

* Add support for TOML configuration files.

1.2.2 (2021-07-13)
------------------

* Support Click version 8.

1.2.1 (2021-01-22)
------------------

* Add allow_indirect_imports to Forbidden Contract type
* Upgrade Grimp to 1.2.3.
* Officially support Python 3.9.

1.2 (2020-09-23)
----------------

* Upgrade Grimp to 1.2.2.
* Add SetField.
* Use a SetField for ignore_imports options.
* Add support for non `\w` characters in import exceptions.

1.1 (2020-06-29)
----------------

* Bring 1.1 out of beta.

1.1b2 (2019-11-27)
------------------

* Update to Grimp v1.2, significantly increasing speed of building the graph.

1.1b1 (2019-11-24)
------------------

* Provide debug mode.
* Allow contracts to mutate the graph without affecting other contracts.
* Update to Grimp v1.1.
* Change the rendering of broken layers contracts by combining any shared chain beginning or endings.
* Speed up and make more comprehensive the algorithm for finding illegal chains in layer contracts. Prior to this,
  layers contracts used Grimp's find_shortest_chains method for each pairing of layers. This found the shortest chain
  between each pair of modules across the two layers. The algorithm was very slow and not comprehensive. With this
  release, for each pair of layers, a copy of the graph is made. All other layers are removed from the graph, any
  direct imports between the two layers are stored. Next, the two layers in question are 'squashed', the shortest
  chain is repeatedly popped from the graph until no more chains remain. This results in more comprehensive results,
  and at significantly increased speed.

1.0 (2019-17-10)
----------------

* Officially support Python 3.8.

1.0b5 (2019-10-05)
------------------

* Allow multiple root packages.
* Make containers optional in Layers contracts.

1.0b4 (2019-07-03)
------------------

* Add https://pre-commit.com configuration.
* Use find_shortest_chains instead of find_shortest_chain on the Grimp import graph.
* Add Forbidden Modules contract type.

1.0b3 (2019-05-15)
------------------

* Update to Grimp v1.0b10, fixing Windows incompatibility.

1.0b2 (2019-04-16)
------------------

* Update to Grimp v1.0b9, fixing error with using importlib.util.find_spec.

1.0b1 (2019-04-06)
------------------

* Improve error handling of modules/containers not in the graph.
* Return the exit code correctly.
* Run lint-imports on Import Linter itself.
* Allow single values in ListField.

1.0a3 (2019-03-27)
------------------

* Include the ability to build the graph with external packages.

1.0a2 (2019-03-26)
------------------

* First usable alpha release.

1.0a1 (2019-01-27)
------------------

* Release blank project on PyPI.
