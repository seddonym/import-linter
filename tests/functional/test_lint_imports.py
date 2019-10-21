import os

import pytest

from importlinter import cli

testpackage_directory = os.path.join(os.path.dirname(__file__), "..", "assets", "testpackage")
multipleroots_directory = os.path.join(os.path.dirname(__file__), "..", "assets", "multipleroots")


@pytest.mark.parametrize(
    "working_directory, config_filename, expected_result",
    (
        (testpackage_directory, None, cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".brokencontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".malformedcontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".customkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalbrokencontract.ini", cli.EXIT_STATUS_ERROR),
        (multipleroots_directory, ".multiplerootskeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (multipleroots_directory, ".multiplerootsbrokencontract.ini", cli.EXIT_STATUS_ERROR),
    ),
)
def test_lint_imports(working_directory, config_filename, expected_result):

    os.chdir(working_directory)

    if config_filename:
        result = cli.lint_imports(config_filename=config_filename)
    else:
        result = cli.lint_imports()

    assert expected_result == result


@pytest.mark.parametrize("is_debug_mode", (True, False))
def test_lint_imports_debug_mode(is_debug_mode):
    kwargs = dict(config_filename=".nonexistentcontract.ini", is_debug_mode=is_debug_mode)
    if is_debug_mode:
        with pytest.raises(FileNotFoundError):
            cli.lint_imports(**kwargs)
    else:
        assert cli.EXIT_STATUS_ERROR == cli.lint_imports(**kwargs)
