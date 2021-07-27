=====
Usage
=====

Configuration file location
---------------------------

Before running the linter, you need to supply configuration in a file.
If not specified over the command line, import linter will check the following files in the current directory in that order:
- ``setup.cfg`` (ini-file format)
- ``.importlinter`` (ini-file format)
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
  The name of the top-level Python package to validate. This package must be importable: usually this
  means it is has been installed using pip, or it's in the current directory. (Either this or ``root_packages`` is required.)
- ``root_packages``:
  The names of the top-level Python packages to validate. This should be used in place of ``root_package`` if you want
  to analyse the imports of multiple packages. (Either this or ``root_package`` is required.)
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

TOML configuration
------------------

The TOML configuration is very similar to the others with a few differences:

- the sections must start with ``tool.``
- contracts are defined by ``[[tool.importlinter.contracts]]``

.. code-block:: toml

    [tool.importlinter]
    root_package = mypackage

    [[tool.importlinter.contracts]]
    name = Contract One

    [[tool.importlinter.contracts]]
    name = Contract Two

Please note, that in order to use TOML files, you need to install the extra require ``toml``::

    pip install import-linter[toml]

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
