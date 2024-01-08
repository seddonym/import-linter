============
TOML support
============


While all the examples are in INI format, Import Linter also supports TOML.

The TOML configuration is very similar to the others with a few differences:

    - the sections must start with ``tool.``
    - contracts are defined by ``[[tool.importlinter.contracts]]``

The basic configuration layout looks like:

.. code-block:: toml

    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Contract One"

    [[tool.importlinter.contracts]]
    name = "Contract Two"

Following, an example with a layered configuration:

.. code-block:: toml

    [tool.importlinter]
    root_packages = [
        "high",
        "medium",
        "low",
    ]

    [[tool.importlinter.contracts]]
    name = "My three-tier layers contract (multiple root packages)"
    type = "layers"
    layers = [
        "high",
        "medium",
        "low",
    ]

Contract ids
------------

You can optionally provide an ``id`` key for each contract. This allows
you to make use of the ``--contract`` parameter when :ref:`running the linter<usage:Running the linter>`.
