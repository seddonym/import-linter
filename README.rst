=============
Import Linter
=============

.. image:: https://img.shields.io/pypi/v/import-linter.svg
    :target: https://pypi.org/project/import-linter

.. image:: https://img.shields.io/pypi/pyversions/import-linter.svg
    :alt: Python versions
    :target: https://pypi.org/project/import-linter/

.. image:: https://api.travis-ci.org/seddonym/import-linter.svg?branch=master
    :target: https://travis-ci.org/seddonym/import-linter


Import Linter allows you to define and enforce rules for the internal and external imports within your Python project.

* Free software: BSD license
* Documentation: https://import-linter.readthedocs.io.

**Warning:** This software is currently in alpha. This means there are likely to be changes that break backward
compatibility. However, due to it being a development tool (rather than something that needs to be installed
on a production system), it may be suitable for inclusion in your testing pipeline. It also means we actively
encourage people to try it out and `submit bug reports`_.

.. _submit bug reports: https://import-linter.readthedocs.io/en/latest/contributing.html#bug-reports

Overview
--------

Import Linter is a command line tool to check that you are following a self-imposed
architecture within your Python project. It does this by analysing the imports between all the modules in a Python
package, and compares this against a set of rules that you provide in a configuration file.

The configuration file contains one or more 'contracts'. Each contract has a specific
type, which determines the sort of rules it will apply. For example, the ``independence``
contract type checks that there are no imports, in either direction, between a set
of subpackages.

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
decided to make sure that there are no dependencies between ``myproject.foo``
and ``myproject.bar``, so we will use the ``independence`` contract type.

Create an ``.importlinter`` file in the root of your project. For example:

.. code-block:: ini

    [importlinter]
    root_package = myproject

    [importlinter:contract:1]
    name=Foo and bar are decoupled
    type=independence
    modules=
        myproject.foo
        myproject.bar

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

    Foo and bar are decoupled BROKEN

    Contracts: 1 broken.


    ----------------
    Broken contracts
    ----------------

    Foo and bar are decoupled
    -------------------------

    myproject.foo is not allowed to import myproject.bar:

    -   myproject.foo.blue -> myproject.utils.red (l.16)
        myproject.utils.red -> myproject.utils.green (l.1)
        myproject.utils.green -> myproject.bar.yellow (l.3)
