=====
Usage
=====

Configuration file location
---------------------------

Before running the linter, you need to supply configuration in a file.
If not specified over the command line, Import Linter will look in the current directory for one of the following files:

- ``setup.cfg`` (INI format)
- ``.importlinter`` (INI format)
- ``pyproject.toml`` (TOML format)


Top level configuration
-----------------------

Your file must contain an ``importlinter`` section providing top-level (i.e. non-contract based) configuration:

.. code-block:: ini

    [importlinter]
    root_package = mypackage
    # Optional:
    include_external_packages = True

Or, with multiple root packages:

.. code-block:: ini

    [importlinter]
    root_packages=
        packageone
        packagetwo
    # Optional:
    include_external_packages = True

**Options:**

- ``root_package``:
  The name of the Python package to validate. For regular packages, this must be the top level package (i.e. one with no
  dots in its name). However, in the special case of `namespace packages`_, the name of the `portion`_ should be
  supplied, for example ``'mynamespace.foo'``.
  This package must be importable: usually this means it is has been installed using pip, or it's in the current
  directory. (Either this or ``root_packages`` is required.)
- ``root_packages``:
  The names of the Python packages to validate. This should be used in place of ``root_package`` if you want
  to analyse the imports of multiple packages, and is subject to the same requirements. (Either this or
  ``root_package`` is required.)
- ``include_external_packages``:
  Whether to include external packages when building the import graph. Unlike root packages, external packages are
  *not* statically analyzed, so no imports from external packages will be checked. However, imports *of* external
  packages will be available for checking. Not every contract type uses this.
  For more information, see `the Grimp build_graph documentation`_. (Optional.)

.. _the Grimp build_graph documentation: https://grimp.readthedocs.io/en/latest/usage.html#grimp.build_graph

Contracts
---------

Additionally, you will want to include one or more contract configurations. These take the following form:

.. code-block:: ini

    [importlinter:contract:one]
    name = Contract One
    type = some_contract_type
    (additional options)

    [importlinter:contract:two]
    name = Contract Two
    type = another_contract_type
    (additional options)

Notice each contract has its own INI section, which begins ``importlinter:contract:`` and ends in a
unique id (in this example, the ids are ``one`` and ``two``). These codes can be used to
to select individual contracts when running the linter (see below).

Every contract will always have the following key/value pairs:

    - ``name``: A human-readable name for the contract.
    - ``type``: The type of contract to use (see :doc:`contract_types`.)

Each contract type defines additional options that you supply here.

Running the linter
------------------

Import Linter provides a single command: ``lint-imports``.

Running this will check that your project adheres to the contracts you've defined.

**Arguments:**

- ``--config``:
  The configuration file to use. This overrides the default file search strategy.
  By default it's assumed that the file is an ini-file unless the file extension is ``toml``.
  (Optional.)
- ``--contract``:
  Limit the check to the contract with the supplied id. In INI files, a contract's id is
  the final part of the section header: for example, the id for a contract with a section
  header of ``[importlinter:contract:foo]`` is ``foo``. In TOML files, ids are supplied
  explicitly with an ``id`` key. This option may be provided multiple
  times to check more than one contract. (Optional.)
- ``--show_timings``:
  Display the times taken to build the graph and check each contract. (Optional.)
- ``--verbose``:
  Noisily output progress as it goes along. (Optional.)

**Default usage:**

.. code-block:: text

    lint-imports

**Using a different filename or location:**

.. code-block:: text

    lint-imports --config path/to/alternative-config.ini

**Checking only certain contracts:**

.. code-block:: text

    lint-imports --contract some-contract --contract another-contract

**Showing timings:**

.. code-block:: text

    lint-imports --show-timings

.. _verbose-mode:

**Verbose mode:**

.. code-block:: text

    lint-imports --verbose

.. _namespace packages: https://docs.python.org/3/glossary.html#term-namespace-package
.. _portion: https://docs.python.org/3/glossary.html#term-portion