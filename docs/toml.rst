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

Third-party dependencies
------------------------

The ``<third_party>`` keyword is also supported in TOML configuration:

.. code-block:: toml

    [tool.importlinter]
    root_package = "mypackage"
    include_external_packages = true

    [[tool.importlinter.contracts]]
    name = "Domain layer must not import third-party libraries"
    type = "forbidden"
    source_modules = ["mypackage.domain"]
    forbidden_modules = ["<third_party>"]

.. code-block:: toml

    [tool.importlinter]
    root_package = "mypackage" 
    include_external_packages = true

    [[tool.importlinter.contracts]]
    name = "Core modules forbidden from third-party and legacy"
    type = "forbidden"
    source_modules = [
        "mypackage.core",
        "mypackage.business",
    ]
    forbidden_modules = [
        "<third_party>",
        "mypackage.legacy",
        "mypackage.deprecated",
    ]
    ignore_imports = [
        "mypackage.core.config -> mypackage.legacy.settings",
    ]

Contract ids
------------

You can optionally provide an ``id`` key for each contract. This allows
you to make use of the ``--contract`` parameter when :ref:`running the linter<usage:Running the linter>`.
