=====================
Custom contract types
=====================

If none of the built in contract types serve your needs, you can define a custom contract type. The steps to do
this are:

1. Somewhere in your Python path, create a module that implements a ``Contract`` class for your supplied type.
2. Register the contract type in your configuration file.
3. Define one or more contracts of your custom type, also in your configuration file.

Step one: implementing a Contract class
---------------------------------------

You define a custom contract type by subclassing ``importlinter.Contract`` and implementing the
following methods:

- ``check(graph: ImportGraph, verbose: bool) -> ContractCheck``:
    Given an import graph of your project, return a ``ContractCheck`` describing whether the contract was adhered to.

    Arguments:
        - ``graph``: a Grimp ``ImportGraph`` of your project, which can be used to inspect / analyse any dependencies.
          For full details of how to use this, see the `Grimp documentation`_.
        - ``verbose``: Whether we're in :ref:`verbose mode <verbose-mode>`. You can use this flag to determine whether to output text
          during the check, using ``output.verbose_print``, as in the example below.

    Returns:
        - An ``importlinter.ContractCheck`` instance. This is a simple dataclass with two attributes,
          ``kept`` (a boolean indicating if the contract was kept) and ``metadata`` (a dictionary of data about the
          check). The metadata can contain anything you want, as it is only used in the ``render_broken_contract``
          method that you also define in this class.

- ``render_broken_contract(check: ContractCheck) -> None``:

    Renders the results of a broken contract check. For output, this should use the
    ``importlinter.output`` module.

    Arguments:
        - ``check``: the ``ContractCheck`` instance returned by the ``check`` method above.

**Contract fields**

The following field types are available:

- ``StringField`` accepts a string value.
- ``BooleanField`` accepts a boolean value.
- ``IntegerField`` accepts an integer value.
- ``EnumField`` accepts a value from a predefined set of string options.
- ``ModuleField`` accepts a string value and validates that it refers to a valid Python module.
- ``ModuleExpressionField`` acts in a similar way as ``ModuleField``, but allows wildcard expressions.
- ``ImportExpressionField`` accepts a string value representing a specific import, module description can include wildcards. (example: ``mypackage.foo.** -> mypackage.bar``)
- ``ListField`` accepts multiple values of the field type specified in the subfield parameter. Duplicate values are allowed, and the values are returned in the order they appear in the configuration.
- ``SetField`` accepts multiple values of the field type specified in the subfield parameter. Duplicate values are not allowed, and they are not ordered.

Fields definition can be found in ``importlinter.domain.fields``.

Fields are to be added in the class definition, the base Contract constructor will parse the value from the config and inject it 
into the instance with the same name. *(this will make type checker complain about field usage)*

Example of multiple values fields usage can be found in ``importlinter.contracts.forbidden``

**Example custom contract**

.. code-block:: python

    from importlinter import Contract, ContractCheck, fields, output


    class ForbiddenImportContract(Contract):
        """
        Contract that defines a single forbidden import between
        two modules.
        """
        importer = fields.StringField()
        imported = fields.StringField()

        def check(self, graph, verbose):
            output.verbose_print(
                verbose,
                f"Getting import details from {self.importer} to {self.imported}..."
            )
            forbidden_import_details = graph.get_import_details(
                importer=self.importer,
                imported=self.imported,
            )
            import_exists = bool(forbidden_import_details)

            return ContractCheck(
                kept=not import_exists,
                metadata={
                    'forbidden_import_details': forbidden_import_details,
                }
            )

        def render_broken_contract(self, check):
            output.print_error(
                f'{self.importer} is not allowed to import {self.imported}:',
                bold=True,
            )
            output.new_line()
            for details in check.metadata['forbidden_import_details']:
                line_number = details['line_number']
                line_contents = details['line_contents']
                output.indent_cursor()
                output.print_error(f'{self.importer}:{line_number}: {line_contents}')


Step two: register the contract type
------------------------------------

In the ``[importlinter]`` section of your configuration file, include a list of ``contract_types`` that map type names
onto the Python path of your custom class:

.. code-block:: ini

    [importlinter]
    root_package_name = mypackage
    contract_types =
        forbidden_import: somepackage.contracts.ForbiddenImportContract

Step three: define your contracts
---------------------------------

You may now use the type name defined in the previous step to define a contract:

.. code-block:: ini

    [importlinter:contract:my-custom-contract]
    name = My custom contract
    type = forbidden_import
    importer = mypackage.foo
    imported = mypackage.bar

.. _Grimp documentation: https://grimp.readthedocs.io