TOML support
------------

While all the examples are in INI format, Import Linter also supports TOML.

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
