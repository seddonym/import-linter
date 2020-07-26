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

1.0b5 (2019-10-5)
-----------------

* Allow multiple root packages.
* Make containers optional in Layers contracts.

1.0 (2019-17-10)
----------------

* Officially support Python 3.8.

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

1.1b2 (2019-11-27)
------------------

* Update to Grimp v1.2, significantly increasing speed of building the graph.

1.1
---

* Bring 1.1 out of beta.


latest
------

* Upgrade Grimp to 1.2.2.
* Add SetField
* Use a SetField for ignore_imports options
