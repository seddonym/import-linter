==========
Python API
==========

While it is usually run via the command line, Import Linter offers a Python API for certain functions.

Reading configuration
---------------------

.. code-block:: python

    >>> from importlinter import api
    >>> api.read_configuration()
    {
        "session_options": {"root_packages": ["importlinter"]},
        "contracts_options": [
            {
                "containers": ["importlinter"],
                "layers": [
                    "cli",
                    "api",
                    "configuration",
                    "adapters",
                    "contracts",
                    "application",
                    "domain",
                ],
                "name": "Layered architecture",
                "type": "layers",
            }
        ],
    }
.. py:function:: read_configuration(config_filename=None)

    Return a dictionary containing configuration from the supplied file.

    If no filename is supplied, look in the default location (see :doc:`usage`).

    This function is designed for use by external projects wishing to
    analyse the contracts themselves, e.g. to track the number of
    ignored imports.

    :param str config_filename: The path to the file containing the configuration (optional).
    :return: A dictionary with two keys:

        - ``"session_options"``: dictionary of strings passed as top level configuration. Note that
          if a single ``root_package`` is in the configuration, it will be normalised to a single-item
          list of ``root_packages``, as shown in the example above.
        - ``"contracts_options"``: list of dictionaries, one for each contract, keyed with:

            - ``"name"``: the name of the contract (str).
            - ``"type"``: the type of the contract (str).
            - Any other contract-specific configuration.
    :rtype: dict

