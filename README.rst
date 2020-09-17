=============
Import Linter
=============

.. image:: https://img.shields.io/pypi/v/import-linter.svg
    :target: https://pypi.org/project/import-linter

.. image:: https://img.shields.io/pypi/pyversions/import-linter.svg
    :alt: Python versions
    :target: https://pypi.org/project/import-linter/

.. image:: https://api.travis-ci.com/seddonym/import-linter.svg?branch=master
    :target: https://travis-ci.com/seddonym/import-linter


Import Linter allows you to define and enforce rules for the imports within and between Python packages.

* Free software: BSD license
* Documentation: https://import-linter.readthedocs.io.

Overview
--------

Import Linter is a command line tool to check that you are following a self-imposed
architecture within your Python project. It does this by analysing the imports between all the modules in one
or more Python packages, and compares this against a set of rules that you provide in a configuration file.

The configuration file contains one or more 'contracts'. Each contract has a specific
type, which determines the sort of rules it will apply. For example, the ``forbidden``
contract type allows you to check that certain modules or packages are not imported by
parts of your project.

Import Linter is particularly useful if you are working on a complex codebase within a team,
when you want to enforce a particular architectural style. In this case you can add
Import Linter to your deployment pipeline, so that any code that does not follow
the architecture will fail tests.

If there isn't a built in contract type that fits your desired architecture, you can define
a custom one.

Quick start
-----------

Install Import Linter::

    pip install import-linter

Decide on the dependency flows you wish to check. In this example, we have
decided to make sure that ``myproject.foo`` has dependencies on neither
``myproject.bar`` nor ``myproject.baz``, so we will use the ``forbidden`` contract type.

Create an ``.importlinter`` file in the root of your project to define your contract(s). In this case:

.. code-block:: ini

    [importlinter]
    root_package = myproject

    [importlinter:contract:1]
    name=Foo doesn't import bar or baz
    type=forbidden
    source_modules=
        myproject.foo
    forbidden_modules=
        myproject.bar
        myproject.baz

Now, from your project root, run::

    lint-imports

If your code violates the contract, you will see an error message something like this:

.. code-block:: text

    =============
    Import Linter
    =============

    ---------
    Contracts
    ---------

    Analyzed 23 files, 44 dependencies.
    -----------------------------------

    Foo doesn't import bar or baz BROKEN

    Contracts: 1 broken.


    ----------------
    Broken contracts
    ----------------

    Foo doesn't import bar or baz
    -----------------------------

    myproject.foo is not allowed to import myproject.bar:

    -   myproject.foo.blue -> myproject.utils.red (l.16)
        myproject.utils.red -> myproject.utils.green (l.1)
        myproject.utils.green -> myproject.bar.yellow (l.3)
