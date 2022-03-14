import os
from pathlib import Path

import pytest

from importlinter import cli

this_directory = Path(__file__).parent
assets_directory = this_directory / ".." / "assets"

testpackage_directory = assets_directory / "testpackage"
multipleroots_directory = assets_directory / "multipleroots"
unmatched_ignore_imports_directory = testpackage_directory / "unmatched_ignore_imports_alerting"


@pytest.mark.parametrize(
    "working_directory, config_filename, expected_result",
    (
        (testpackage_directory, None, cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".brokencontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".malformedcontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".customkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalbrokencontract.ini", cli.EXIT_STATUS_ERROR),
        (multipleroots_directory, ".multiplerootskeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (multipleroots_directory, ".multiplerootsbrokencontract.ini", cli.EXIT_STATUS_ERROR),
        # TOML versions.
        pytest.param(
            testpackage_directory,
            ".setup.toml",
            cli.EXIT_STATUS_ERROR,
            marks=pytest.mark.toml_not_installed,
        ),
        pytest.param(
            testpackage_directory,
            ".setup.toml",
            cli.EXIT_STATUS_SUCCESS,
            marks=pytest.mark.toml_installed,
        ),
        pytest.param(
            testpackage_directory,
            ".customkeptcontract.toml",
            cli.EXIT_STATUS_ERROR,
            marks=pytest.mark.toml_not_installed,
        ),
        pytest.param(
            testpackage_directory,
            ".customkeptcontract.toml",
            cli.EXIT_STATUS_SUCCESS,
            marks=pytest.mark.toml_installed,
        ),
        pytest.param(
            testpackage_directory,
            ".customkeptcontract.toml",
            cli.EXIT_STATUS_ERROR,
            marks=pytest.mark.toml_not_installed,
        ),
        pytest.param(
            testpackage_directory,
            ".customkeptcontract.toml",
            cli.EXIT_STATUS_SUCCESS,
            marks=pytest.mark.toml_installed,
        ),
        (testpackage_directory, ".externalkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        pytest.param(
            testpackage_directory,
            ".externalkeptcontract.toml",
            cli.EXIT_STATUS_SUCCESS,
            marks=pytest.mark.toml_installed,
        ),
        # Unmatched ignore imports alerting.
        # The return value depends on what this is set to.
        (
            testpackage_directory,
            str(unmatched_ignore_imports_directory / "unspecified.ini"),
            cli.EXIT_STATUS_ERROR,
        ),
        (
            testpackage_directory,
            str(unmatched_ignore_imports_directory / "error.ini"),
            cli.EXIT_STATUS_ERROR,
        ),
        (
            testpackage_directory,
            str(unmatched_ignore_imports_directory / "warn.ini"),
            cli.EXIT_STATUS_SUCCESS,
        ),
        (
            testpackage_directory,
            str(unmatched_ignore_imports_directory / "none.ini"),
            cli.EXIT_STATUS_SUCCESS,
        ),
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
