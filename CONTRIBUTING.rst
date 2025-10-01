============
Contributing
============

We welcome contributions to Import Linter.

Bug reports
===========

When `reporting a bug <https://github.com/seddonym/import-linter/issues>`_ please include:

    * Your operating system name and version.
    * Any details about your local setup that might be helpful in troubleshooting.
    * Detailed steps to reproduce the bug.

Feature requests and feedback
=============================

The best way to send feedback is to file an issue at https://github.com/seddonym/import-linter/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible.
* Remember that this is a volunteer-driven project.

Submitting pull requests
========================

Before spending time working on a pull request, we highly recommend filing a Github issue and engaging with the
project maintainer (David Seddon) to align on the direction you're planning to take. This can save a lot of your
precious time!

This doesn't apply to trivial pull requests such as spelling corrections.

For merging, you should:

1. Include passing tests (run ``just test-all``).
2. Update documentation when there's new API, functionality etc.
3. Add a note to ``CHANGELOG.rst`` about the changes.
4. Add yourself to ``AUTHORS.rst``.

Development
===========

System prerequisites
--------------------

Make sure these are installed first.

- `git <https://github.com/git-guides/install-git>`_
- `uv <https://docs.astral.sh/uv/#installation>`_
- `just <https://just.systems/man/en/packages.html>`_

Setup
-----

You don't need to activate or manage a virtual environment - this is taken care in the background of by ``uv``.

1. Fork `import-linter <https://github.com/seddonym/import-linter>`_
   (look for the "Fork" button).
2. Clone your fork locally::

    git clone git@github.com:your_name_here/import-linter.git

3. Change into the directory you just cloned::

    cd import-linter

4. Set up pre-commit. (Optional, but recommended.)::

    just install-precommit


You will now be able to run commands prefixed with ``just``, providing you're in the Import Linter directory.
To see available commands, run ``just``.

Formatting code
---------------

::

    just format

Running linters
---------------

::

    just lint

Running tests
-------------

When you're developing a feature, you'll probably want to run tests quickly, using just the latest supported Python version::

    just test


There are also version-specific test commands (e.g. ``just test-3-13``) - run ``just help`` to see which ones.

Finally, you can run all of the tests in parallel with ``just test-all``. This gives a more complete picture of whether
the changes are compatible with all supported versions, but any failure output may be difficult to read.

Before you push
---------------

It's a good idea to run ``just check`` before getting a review. This will run linters, docs build and tests under
every supported Python version.

Building documentation
----------------------

To build docs and open them in a browser::

    just build-and-open-docs

Or, if you just want to build them::

    just build-docs

Releasing to Pypi
=================

(Only maintainers can do this.)

1. Choose a new version number (based on `semver <https://semver.org/>`_).
2. ``git pull origin main``
3. Update ``CHANGELOG.rst`` with the new version number.
4. Update the ``release`` variable in ``docs/conf.py`` with the new version number.
5. Update the ``__version__`` variable in ``src/importlinter/__init__.py`` with the new version number.
6. Update ``project.version`` in ``pyproject.toml`` with the new version number.
7. ``git commit -am "Release v{new version number"``
8. ``git push``
9. Wait for tests to pass on CI.
10. ``git tag v{new version number}``
11. ``git push --tags``
12. This should kick start the Github ``release`` workflow which releases the project to PyPI.
