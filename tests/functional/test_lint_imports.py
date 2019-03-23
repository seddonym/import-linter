import os

import pytest

from importlinter import cli


testpackage_directory = os.path.join(
    os.path.dirname(__file__),
    '..',
    'assets',
    'testpackage',
)


@pytest.mark.parametrize(
    'config_filename, expected_result',
    (
        (None, cli.EXIT_STATUS_SUCCESS),
        ('.brokencontract.ini', cli.EXIT_STATUS_ERROR),
        ('.malformedcontract.ini', cli.EXIT_STATUS_ERROR),
    )
)
def test_lint_imports(config_filename, expected_result):

    os.chdir(testpackage_directory)

    if config_filename:
        result = cli.lint_imports(config_filename=config_filename)
    else:
        result = cli.lint_imports()

    assert expected_result == result
