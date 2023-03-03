=======
Caching
=======

Import Linter uses a file-based cache to speed up subsequent linting runs.

On a large code base this can result in much faster runs.

What is cached
--------------

A run of ``lint-imports`` involves two phases:

1. *Building the graph*: in which the packages are scanned to identify all the imports between their modules, which is
   stored in a Grimp graph. (`Grimp`_ is a separate Python package used by Import Linter).
2. *Contract checking*: in which the graph is checked for compliance with each contract.

Caching is used in the first step but not the second. For more information about how this works, see `Grimp's caching documentation`_.

Location of the cache
---------------------

Cache files are written, by default, to an ``.import_linter_cache`` directory
in the current working directory. This directory can be changed by passing
a different ``cache_dir`` argument e.g.::

    lint-imports --cache-dir /path/to/cache

Disabling caching
-----------------

To skip using (and writing to) the cache, pass ``--no-cache``::

    lint-imports --no-cache

Concurrency
-----------

Caching isn't currently concurrency-safe. Specifically, if you have two concurrent processes writing to the same cache
files, you might experience incorrect behaviour.

.. _Grimp: https://pypi.org/project/grimp/
.. _Grimp's caching documentation: https://grimp.readthedocs.io/en/stable/caching.html