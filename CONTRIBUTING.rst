============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

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
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that code contributions are welcome :)

Submitting pull requests
========================

Before spending time working on a pull request, we highly recommend filing a Github issue and engaging with the
project maintainer (David Seddon) to align on the direction you're planning to take. This can save a lot of your
precious time!

This doesn't apply to trivial pull requests such as spelling corrections.

For merging, you should:

1. Include passing tests (run ``tox``).
2. Update documentation when there's new API, functionality etc.
3. Add a note to ``CHANGELOG.rst`` about the changes.
4. Add yourself to ``AUTHORS.rst``.

Development
===========

To set up `import-linter` for local development:

1. Fork `import-linter <https://github.com/seddonym/import-linter>`_
   (look for the "Fork" button).
2. Clone your fork locally::

    git clone git@github.com:your_name_here/import-linter.git

3. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

4. When you're done making changes, run all the checks with `tox <https://tox.wiki/en/latest/installation.html>`_ one command::

    tox

5. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

6. Submit a pull request through the GitHub website.

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
