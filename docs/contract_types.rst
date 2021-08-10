==============
Contract types
==============

Shared options
--------------

The following options can be used in all contracts.

- ``ignore_imports``: Optional list of imports, each in the form ``mypackage.foo.importer -> mypackage.bar.imported``.
  These imports will be ignored: if the import would cause a contract to be broken, adding it to the list will cause the
  contract be kept instead.

  Wildcards are supported as well.
  These can stand in for a module name or part of a name, but they do not extend to subpackages.
  For example, "mypackage.*" refers to every child subpackage of mypackage.
  It does not, however, include more distant descendants such as mypackage.foo.bar.



Forbidden modules
-----------------

*Type name:* ``forbidden``

Forbidden contracts check that one set of modules are not imported by another set of modules.

Descendants of each module will be checked - so if ``mypackage.one`` is forbidden from importing ``mypackage.two``, then
``mypackage.one.blue`` will be forbidden from importing ``mypackage.two.green``. Indirect imports will also be checked.

External packages may also be forbidden.

**Examples:**

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:1]
    name = My forbidden contract (internal packages only)
    type = forbidden
    source_modules =
        mypackage.one
        mypackage.two
        mypackage.three.blue
    forbidden_modules =
        mypackage.four
        mypackage.five.green
    ignore_imports =
        mypackage.one.green -> mypackage.utils
        mypackage.two -> mypackage.four

.. code-block:: ini

    [importlinter]
    root_package = mypackage
    include_external_packages = True

    [importlinter:contract:1]
    name = My forbidden contract (internal and external packages)
    type = forbidden
    source_modules =
        mypackage.one
        mypackage.two
    forbidden_modules =
        mypackage.three
        django
        requests
    ignore_imports =
        mypackage.one.green -> sqlalchemy

**Configuration options**

Configuration options:

    - ``source_modules``:    A list of modules that should not import the forbidden modules.
    - ``forbidden_modules``: A list of modules that should not be imported by the source modules. These may include
      root level external packages (i.e. ``django``, but not ``django.db.models``). If external packages are included,
      the top level configuration must have ``internal_external_packages = True``.
    - ``ignore_imports``: See above
    - ``allow_indirect_imports``: If ``True``, allow indirect imports to forbidden modules without interpreting them
      as a reason to mark the contract broken. (Optional.)

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
    - ``ignore_imports``: See above


Layers
------

*Type name:* ``layers``

Layers contracts enforce a 'layered architecture', where higher layers may depend on lower layers, but not the other
way around.

They do this by checking, for an ordered list of modules, that none higher up the list imports anything from a module
lower down the list, even indirectly.

Layers are required by default: if a layer is listed in the contract, the contract will be broken if the layer
doesn't exist. You can make a layer optional by wrapping it in parentheses.

You may also define a set of 'containers'. These allow for a repeated pattern of layers across a project. If containers
are provided, these are treated as the parent package of the layers.

**Examples**

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:1]
    name = My three-tier layers contract
    type = layers
    layers=
        mypackage.high
        mypackage.medium
        mypackage.low

This contract will not allow imports from lower layers to higher layers. For example, it will not allow
``mypackage.low`` to import ``mypackage.high``, even indirectly.

.. code-block:: ini

    [importlinter]
    root_packages=
        high
        medium
        low

    [importlinter:contract:1]
    name = My three-tier layers contract (multiple root packages)
    type = layers
    layers=
        high
        medium
        low

This contract is similar to the one above, but is suitable if the packages are not contained within a root package
(i.e. the Python project consists of several packages in a directory that does not contain an ``__init__.py`` file).
In this case, ``high``, ``medium`` and ``low`` all need to be specified as ``root_packages`` in the
``[importlinter]`` configuration.

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
      An ordered list with the name of each layer module. If containers are specified, then these names must be
      *relative to the container*. The order is from higher to lower level layers. Layers wrapped in parentheses
      (e.g. ``(foo)``) will be ignored if they are not present in the file system.
    - ``containers``:
      List of the parent modules of the layers, as *absolute names* that you could import, such as
      ``mypackage.foo``. (Optional.)
    - ``ignore_imports``: See above



Custom contract types
---------------------

If none of the built in contract types meets your needs, you can define a custom contract type: see
:doc:`custom_contract_types`.
