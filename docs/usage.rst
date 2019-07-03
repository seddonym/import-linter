=====
Usage
=====

Configuration file location
---------------------------

Before running the linter, you need to supply configuration in a file, in INI format. Import Linter will look in the
current directory for one of the following files:

- ``setup.cfg``
- ``.importlinter``

(Different filenames / locations can be specified as a command line argument, see below.)

Top level configuration
-----------------------

Your file must contain an ``importlinter`` section providing top-level (i.e. non-contract based) configuration:

.. code-block:: ini

    [importlinter]
    # Required:
    root_package = mypackage
    # Optional:
    include_external_packages = True

**Options:**

- ``root_package``:
  The name of the top-level Python package to validate. This package must be importable: usually this
  means it is has been installed using pip, or it's in the current directory. (Required.)
- ``include_external_packages``:
  Whether to include external packages when building the import graph (see `the Grimp build_graph documentation`_ for
  more details). Not every contract type uses this. (Optional.)

.. _the Grimp build_graph documentation: https://grimp.readthedocs.io/en/latest/usage.html#grimp.build_graph

Contracts
---------

Additionally, you will want to include one or more contract configurations. These take the following form:

.. code-block:: ini

    [importlinter:contract:1]
    name = Contract One
    type = some_contract_type
    (additional options)

    [importlinter:contract:2]
    name = Contract Two
    type = another_contract_type
    (additional options)

Notice each contract has its own INI section, which begins ``importlinter:contract:`` and ends in an
arbitrary, unique code (in this example, the codes are ``1`` and ``2``). These codes are purely
to adhere to the INI format, which does not allow duplicate section names.

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
  The configuration file to use. If not supplied, Import Linter will look for ``setup.cfg``
  or ``.importlinter`` in the current directory. (Optional.)

**Default usage:**

.. code-block:: text

    lint-imports

**Using a different filename or location:**

.. code-block:: text

    lint-imports --config path/to/alternative-config.ini
