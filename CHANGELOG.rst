Changelog
=========

latest
------

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
