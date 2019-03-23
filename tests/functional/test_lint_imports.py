import os

from importlinter import cli


testpackage_directory = os.path.join(
    os.path.dirname(__file__),
    '..',
    'assets',
    'testpackage',
)


def test_lint_imports():

    os.chdir(testpackage_directory)
    result = cli.lint_imports()

    assert 0 == result
