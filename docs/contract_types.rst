==============
Contract types
==============

Independence
------------

*Type name:* ``independence``

Independence contracts check that a set of modules do not depend on each other.

They do this by checking that there are no imports in any direction between the modules, even indirectly.

**Example:**

.. code-block:: ini

    [importlinter:contract:1]
    name = My independence contract
    type = independence
    modules =
        mypackage.foo
        mypackage.bar
        mypackage.baz
    ignore_imports =
        mypackage.bar.green -> mypackage.utils
        mypackage.baz.blue -> mypackage.foo.purple

**Configuration options**

    - ``modules``: A list of modules/subpackages that should be independent from each other.
    - ``ignore_imports``:
      A list of imports, each in the form ``mypackage.foo.importer -> mypackage.bar.imported``. These imports
      will be ignored: if the import would cause a contract to be broken, adding it to the list will cause the
      contract be kept instead. (Optional.)

Layers
------

*Type name:* ``layers``

Layers contracts enforce a 'layered architecture', where higher layers may depend on lower layers, but not the other
way around.

They do this by checking, for an ordered list of modules, that none higher up the list imports anything from a module
lower down the list, even indirectly. To allow for a repeated pattern of layers across a project, you also define
a set of 'containers', which are treated as the parent package of the layers.

Layers are required by default: if a layer is listed in the contract, the contract will be broken if the layer
doesn't exist. You can make a layer optional by wrapping it in parentheses.

**Examples**

.. code-block:: ini

    [importlinter:contract:1]
    name = My three-tier layers contract
    type = layers
    layers=
        high
        medium
        low
    containers=
        mypackage

This contract will not allow imports from lower layers to higher layers. For example, it will not allow
``mypackage.low`` to import ``mypackage.high``, even indirectly.

.. code-block:: ini

    [importlinter:contract:1]
    name = My multiple package layers contract
    type = layers
    layers=
        high
        (medium)
        low
    containers=
        mypackage.foo
        mypackage.bar
        mypackage.baz

In this example, each container has its own layered architecture. For example, it will not allow ``mypackage.foo.low``
to import ``mypackage.foo.high``. However, it will allow ``mypackage.foo.low`` to import ``mypackage.bar.high``,
as they are in different containers:

Notice that ``medium`` is an optional layer. This means that if it is missing from any of the containers, Import Linter
won't complain.

**Configuration options**

    - ``layers``:
      An ordered list with the name of each layer module, *relative to its parent package*. The order is from higher
      to lower level layers.
    - ``containers``:
      List of the parent modules of the layers, as *absolute names* that you could import, such as
      ``mypackage.foo``. If you only have one set of layers, there will only be one container.
    - ``ignore_imports``:
      A list of imports, each in the form ``mypackage.foo.importer -> mypackage.bar.imported``. These imports
      will be ignored: if the import would cause a contract to be broken, adding it to the list will cause the
      contract be kept instead. (Optional.)


Custom contract types
---------------------

If none of the built in contract types meets your needs, you can define a custom contract type: see
:doc:`custom_contract_types`.
