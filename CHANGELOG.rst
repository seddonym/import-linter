Changelog
=========

1.0a1 (2019-1-27)
-----------------

* Release blank project on PyPI.


1.0a2 (2019-3-26)
-----------------

* First usable alpha release.


1.0a3 (2019-3-27)
-----------------

* Include the ability to build the graph with external packages.


1.0b1 (2019-4-6)
----------------

* Improve error handling of modules/containers not in the graph.
* Return the exit code correctly.
* Run lint-imports on Import Linter itself.
* Allow single values in ListField.


1.0b2 (2019-4-16)
-----------------

* Update to Grimp v1.0b9, fixing error with using importlib.util.find_spec.


1.0b3 (2019-5-15)
-----------------

* Update to Grimp v1.0b10, fixing Windows incompatibility.

1.0b4 (2019-7-3)
----------------

* Add https://pre-commit.com configuration.
* Use find_shortest_chains instead of find_shortest_chain on the Grimp import graph.
* Add Forbidden Modules contract type.
