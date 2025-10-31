==============
Contract types
==============

.. _forbidden modules:

Forbidden modules
-----------------

*Type name:* ``forbidden``

Forbidden contracts check that one set of modules are not imported by another set of modules.

By default, descendants of each module will be checked - so if ``mypackage.one`` is forbidden from importing ``mypackage.two``, then
``mypackage.one.blue`` will be forbidden from importing ``mypackage.two.green``. Indirect imports will also be checked. This
descendant behaviour can be changed by setting ``as_packages`` to ``False``: in that case, only explicitly listed modules will be
checked, not their descendants.

External packages may also be forbidden.

**Examples:**

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:my-forbidden-contract]
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

    [importlinter:contract:my-forbidden-contract]
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

    - ``source_modules``:    A list of modules that should not import the forbidden modules. Supports :ref:`wildcards`.
    - ``forbidden_modules``: A list of modules that should not be imported by the source modules. These may include
      root level external packages (i.e. ``django``, but not ``django.db.models``). If external packages are included,
      the top level configuration must have ``include_external_packages = True``. Supports :ref:`wildcards`.
    - ``ignore_imports``: See :ref:`Shared options`.
    - ``unmatched_ignore_imports_alerting``: See :ref:`Shared options`.
    - ``allow_indirect_imports``: If ``True``, allow indirect imports to forbidden modules without interpreting them
      as a reason to mark the contract broken. (Optional.)
    - ``as_packages``: Whether to treat the source and forbidden modules as packages. If ``False``, each of the modules
      passed in will be treated as a module rather than a package. Default behaviour is ``True`` (treat modules as
      packages).

Acyclic siblings
----------------

*Type name:* ``acyclic_siblings``

An *acyclic siblings* contract forbids dependency cycles between siblings. The direct imports between them (and their
descendants) are treated as dependencies; if a cycle exists between these dependencies then the contract will fail. The
contract begins by checking the children of the supplied ancestors. Then it repeats down the generations,
drilling into each subpackage and checking those children for cycles.

This is easier to understand with a diagram. Take this package (the arrows represent imports):

.. image:: ./_static/images/acyclic-siblings.svg
  :align: center
  :alt: Diagram showing cycles between siblings

\

While no direct cycles exist between individual Python modules, an ``acyclic_siblings`` contract running on
``mypackage`` will detect a cycle between the children of ``mypackage``: ``blue`` depends on ``green``, which depends
on ``red``, which depends on ``yellow``, which depends on ``blue``. When it drills down a generation, it will also
find a cycle between the children of ``blue``.

How many generations are drilled down into is controlled by an optional ``depth`` argument (which defaults to 10).
If ``depth`` is 0, only children of the ancestors will be checked; in the example above, the cycle
between ``blue``, ``green``, ``red`` and ``yellow`` will be detected (assuming the supplied ancestor is ``mypackage``)
but not the cycle between ``blue``'s children. With a ``depth`` of 1, that cycle will be found too.

Drilldown can be skipped for specific descendants using the ``skip_descendants`` argument (see below).

**Important:** neither the ``depth`` or ``skip_descendants`` options prevent deeper imports from being considered when
analyzing children in earlier generations. So if ``.blue.some.deep.module`` imports ``.green.another.deep.module``, that could still
contribute to a cycle between ``.blue`` and ``.green``, even if the ``depth`` is 0 or ``.green.another`` is listed
as a skipped descendant. If you want to ignore an import altogether, use ``ignore_imports`` instead.

**Examples:**

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:my-contract]
    name = Minimal acyclic siblings contract
    type = acyclic_siblings
    ancestors = mypackage

    [importlinter:contract:my-contract]
    name = Acyclic siblings contract with more options
    type = acyclic_siblings
    ancestors =
        mypackage.foo
        mypackage.bar.*
    depth = 5
    skip_descendants =
        mypackage.foo.purple
        mypackage.foo.**.orange
    ignore_imports =
        mypackage.foo.blue.one -> mypackage.foo.green.two

**Configuration options**

    - ``ancestors``: The packages whose descendants should be checked for cycles.
      Supports :ref:`wildcards`.
    - ``depth``: How many generations of siblings to check, relative to the ancestors. A depth of 0 will only check the
      children, depth 1 will check grandchildren (as sets of siblings), etc. Can be an integer >=0. Default 10.
      (Optional.)
    - ``skip_descendants``: The ancestors of children that shouldn't be checked. For example, if
      ``mypackage.foo.purple`` is a skipped descendant, then the children of that package won't be checked for cycles,
      nor will their descendants. Supports :ref:`wildcards`. (Optional.)
    - ``ignore_imports``:  See :ref:`Shared options`. (Optional.)
    - ``unmatched_ignore_imports_alerting``: See :ref:`Shared options`. (Optional.)

**Sample output**


.. code-block:: text

    Broken acyclic_siblings contract
    --------------------------------

    No cycles are allowed in mypackage.foo.
    It could be made acyclic by removing 1 dependency:

    - .alpha -> .beta (3 imports)

    No cycles are allowed in mypackage.foo.alpha.
    It could be made acyclic by removing 11 dependencies:

    - .blue -> .green (4 imports)
    - .blue -> .yellow (11 imports)
    - .green -> .orange (1 import)
    - .purple -> .red (3 imports)
    - .purple -> .yellow (2 imports)
    (and 6 more).


Protected modules
-----------------

*Type name:* ``protected``

Protected contracts prevent certain modules from being directly imported, except by modules in an allow-list.
By default, descendants of each module will be checked too.

For example, if ``blue`` is protected, and ``green`` is the only module in the allow list,
then no module other than ``green`` (and its descendants) will be allowed to import ``blue`` (and its descendants) directly.

**Examples:**

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:simple-protected-contract]
    name = Simple protected contract
    type = protected
    protected_modules =
        mypackage.protected
        mypackage.also_protected
    allowed_importers =
        mypackage.allowed
        mypackage.also_allowed

.. code-block:: ini

    [importlinter]
    root_package = mypackage

    [importlinter:contract:models-can-only-be-imported-by-colors]
    name = Models can only be imported by colors direct descendant
    type = protected
    protected_modules =
        mypackage.**.models
    allowed_importers =
        mypackage.colors.*
    ignore_imports =
        mypackage.one.green -> mypackage.one.models
        mypackage.colors.red.foo -> mypackage.three.models
    as_packages = False

**Configuration options**

    - ``protected_modules``: The modules that must not be imported except by the list of allowed importers.
      If ``as_packages`` is ``True``, descendants of a protected module are also allowed to import each other.
      For example, in the *Simple protected contract* above, ``mypackage.protected.green`` is allowed to import
      ``mypackage.protected.blue``, but ``mypackage.red`` and ``mypackage.also_protected.yellow`` are not.
      Supports :ref:`wildcards`.
    - ``allowed_importers``: The only modules allowed to import the target modules. Supports :ref:`wildcards`.
    - ``ignore_imports``:  See :ref:`Shared options`.
    - ``unmatched_ignore_imports_alerting``: See :ref:`Shared options`.
    - ``as_packages``: Whether to treat the source and forbidden modules as packages. If ``False``, each of the modules
      passed in will be treated as a module rather than a package. Default behaviour is ``True`` (treat modules as
      packages).

Independence
------------

*Type name:* ``independence``

Independence contracts check that a set of modules do not depend on each other.

They do this by checking that there are no imports in any direction between the modules, even indirectly.

**Example:**

.. code-block:: ini

    [importlinter:contract:my-independence-contract]
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

    - ``modules``: A list of modules/subpackages that should be independent of each other. Supports :ref:`wildcards`.
    - ``ignore_imports``: See :ref:`Shared options`.
    - ``unmatched_ignore_imports_alerting``: See :ref:`Shared options`.


Layers
------

*Type name:* ``layers``

Layers contracts enforce a 'layered architecture', where higher layers may depend on lower layers, but not the other
way around.

**Configuration options**

    - ``layers``:
      An ordered list with the name of each layer module. If ``containers`` are specified too, then these names must be
      *relative to the container*. The order is from higher to lower level layers. Layers wrapped in parentheses
      (e.g. ``(foo)``) will be ignored if they are not present in the file system; otherwise, the contract will fail.
      It's also possible to include multiple layer modules on the same line, separated by either exclusively pipes
      (``|``) or exclusively colons (``:``) - see :ref:`Multi-item layers`. Does not support :ref:`wildcards`.
    - ``containers``:
      List of the parent modules of the layers, as *absolute names* that you could import, such as
      ``mypackage.foo``. See :ref:`Containers`. Supports :ref:`wildcards`. (Optional.)
    - ``ignore_imports``: See :ref:`Shared options`.
    - ``unmatched_ignore_imports_alerting``: See :ref:`Shared options`.
    - ``exhaustive``. If true, check that the contract declares every possible layer in its list of layers to check.
      See :ref:`Exhaustive contracts`. (Optional, default False.)
    - ``exhaustive_ignores``. A list of layers to ignore in exhaustiveness checks. (Optional.)

Basic usage
^^^^^^^^^^^

'Layers' is a software architecture pattern in which a list of modules/packages have a dependency direction
from high to low.

.. image:: ./_static/images/layers.png
  :align: center
  :alt: Layered architecture.

In this diagram, the Python package ``mypackage`` has a layered architecture in which its subpackage ``high`` is the
highest layer and its subpackage ``low`` is the lowest layer. ``low`` is not allowed to import from any of the layers
above it, while ``high`` can import from everything. In the middle, ``medium`` can import from ``low`` but not ``high``.
This includes indirect imports (i.e. chains of imports via other modules), so if there was a module not listed here that
imports ``high`` (say, ``utils``) then ``low`` wouldn't be allowed to import that either.

The architecture is enforced for all modules within the layers, too, so ``mypackage.low.one`` would not be
allowed to import from ``mypackage.high.two``. That said, the layers don't have to be subpackages - they could just be
individual ``.py`` modules.

Here's how the architecture shown above could be checked using a ``layers`` contract:

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = My layers contract
    type = layers
    layers =
        mypackage.high
        mypackage.medium
        mypackage.low

If a layer is listed in the contract, the contract will be broken if the layer doesn't exist. You can make a layer
optional by wrapping it in parentheses, but this is only likely to be useful if you are using
:ref:`containers<Containers>`.

Layering across root packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Layers don't have to be subpackages - they can be top-level (root) packages. We can still layer a Python project
consisting of three packages ``high``, ``medium`` and ``low``, in a directory that does not contain an
``__init__.py`` file:

.. code-block:: ini

    [importlinter]
    root_packages=
        high
        medium
        low

    [importlinter:contract:my-layers-contract]
    name = My three-tier layers contract (multiple root packages)
    type = layers
    layers =
        high
        medium
        low

In this contract, each top level package is treated as a layer. (Note, though, that they all need to be specified
as ``root_packages`` in the ``[importlinter]`` configuration, too.)

.. _Containers:

Containers
^^^^^^^^^^

Containers allow for a less repetitive way of specifying layers.

Here's a contract that layers ``mypackage.high``, ``mypackage.medium`` and ``mypackage.low`` using a single container:

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = My layers contract
    type = layers
    layers =
        high
        medium
        low
    containers =
        mypackage

Note that by using a container, we don't need to repeat the containing package in the ``layers`` section.

Containers are particularly useful if you want to specify a recurring pattern of layers in different places in the graph:

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = My multiple package layers contract
    type = layers
    layers =
        high
        (medium)
        low
    containers =
        mypackage.foo
        mypackage.bar
        mypackage.baz

In this example, each container has its own layered architecture. For example, it will not allow ``mypackage.foo.low``
to import ``mypackage.foo.high``. However, it will allow ``mypackage.foo.low`` to import ``mypackage.bar.high``,
as they are in different containers:

Notice that ``medium`` is wrapped in parentheses, making it an optional layer. This means that if it is missing from any of
the containers, Import Linter won't complain.

.. _Exhaustive contracts:

Exhaustive contracts
^^^^^^^^^^^^^^^^^^^^

If you want to make sure that *every* module in each container is defined as a layer, you can mark the contract as
'exhaustive'. This means that if a module is added to the code base in the same package as your layers, the contract
will fail. Any such modules that shouldn't cause a failure can be added to an ``exhaustive_ignores`` list.

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = My multiple package layers contract
    type = layers
    layers =
        high
        (medium)
        low
    containers=
        mypackage.foo
        mypackage.bar
        mypackage.baz
    exhaustive = true
    exhaustive_ignores =
        utils

If, say, a module existed called ``mypackage.foo.extra``, the contract will fail as it is not listed as a layer. However
``mypackage.foo.utils`` would be allowed as it is listed in ``exhaustive_ignores``.

Exhaustive contracts are only supported for layers that define containers.

.. _Multi-item layers:

Multi-item layers
^^^^^^^^^^^^^^^^^

Import Linter supports the presence of multiple sibling modules or packages within the same layer. In the diagram below,
the modules ``blue``, ``green`` and ``yellow`` are 'independent' in the same layer. This means that, in addition to not
being allowed to import from layers above them, they are not allowed to import from each other.

.. image:: ./_static/images/layers-independent.png
  :align: center
  :alt: Architecture with a layer containing independent siblings.

An architecture like this can be checked by listing the siblings on the same line, separated by pipe characters:

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = Contract with sibling modules (independent)
    type = layers
    layers =
        mypackage.high
        mypackage.blue | mypackage.green | mypackage.yellow
        mypackage.low

For a more relaxed architecture siblings can be designated as non-independent, meaning that they are allowed to import
from each other, as shown:

.. image:: ./_static/images/layers-non-independent.png
  :align: center
  :alt: Architecture with a layer containing non-independent siblings.

To allow siblings to depend on each other, use colons instead of pipes to separate them:

.. code-block:: ini

    [importlinter:contract:my-layers-contract]
    name = Contract with sibling modules (independent)
    type = layers
    layers =
        mypackage.high
        mypackage.blue : mypackage.green : mypackage.yellow
        mypackage.low

Note: you are not allowed to mix different kinds of separators on the same line. This would be an invalid contract:

.. code-block:: ini

    [importlinter:contract:my-invalid-contract]
    name = Invalid contract
    type = layers
    layers =
        mypackage.high
        mypackage.blue | mypackage.green : mypackage.yellow  # Invalid as it mixes separators.
        mypackage.low


Custom contract types
---------------------

If none of the built in contract types meets your needs, you can define a custom contract type: see
:doc:`custom_contract_types`.

.. _Shared options:

Options used by multiple contracts
----------------------------------

- ``ignore_imports``: Optional list of imports, each in the form ``mypackage.foo.importer -> mypackage.bar.imported``.
  These imports will be ignored: if the import would cause a contract to be broken, adding it to the list will cause the
  contract be kept instead. Supports :ref:`wildcards`.

- ``unmatched_ignore_imports_alerting``: The alerting level for handling expressions supplied in ``ignore_imports``
  that do not match any imports in the graph. Choices are:

    - ``error``: Error if there are any unmatched expressions (default).
    - ``warn``: Print a warning for each unmatched expression.
    - ``none``: Do not alert.

.. _wildcards:

Wildcards
---------

  Many contract fields refer to sets of modules - some (but not all) of these support wildcards.

  ``*`` stands in for a module name, without including subpackages. ``**`` includes subpackages too.

  Examples:

  - ``mypackage.*``:  matches ``mypackage.foo`` but not ``mypackage.foo.bar``.
  - ``mypackage.*.baz``: matches ``mypackage.foo.baz`` but not ``mypackage.foo.bar.baz``.
  - ``mypackage.*.*``: matches ``mypackage.foo.bar`` and ``mypackage.foobar.baz``.
  - ``mypackage.**``: matches ``mypackage.foo.bar`` and ``mypackage.foo.bar.baz``.
  - ``mypackage.**.qux``: matches ``mypackage.foo.bar.qux`` and ``mypackage.foo.bar.baz.qux``.
  - ``mypackage.foo*``: not a valid expression. (The wildcard must replace a whole module name.)
