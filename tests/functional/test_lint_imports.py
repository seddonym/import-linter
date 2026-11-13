import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from importlinter import __version__, cli
from importlinter.application import output

this_directory = Path(__file__).parent
assets_directory = this_directory / ".." / "assets"

testpackage_directory = assets_directory / "testpackage"
multipleroots_directory = assets_directory / "multipleroots"
unmatched_ignore_imports_directory = testpackage_directory / "unmatched_ignore_imports_alerting"
namespace_packages_directory = assets_directory / "namespacepackages"
cyclicpackage_directory = assets_directory / "cycles"

# Add namespace packages to Python path
sys.path.extend(
    [str(namespace_packages_directory / location) for location in ("locationone", "locationtwo")],
)


@pytest.mark.parametrize(
    "working_directory, config_filename, expected_result",
    (
        (testpackage_directory, None, cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".brokencontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".malformedcontract.ini", cli.EXIT_STATUS_ERROR),
        (testpackage_directory, ".customkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalbrokencontract.ini", cli.EXIT_STATUS_ERROR),
        (
            multipleroots_directory,
            ".multiplerootskeptcontract.ini",
            cli.EXIT_STATUS_SUCCESS,
        ),
        (
            multipleroots_directory,
            ".multiplerootsbrokencontract.ini",
            cli.EXIT_STATUS_ERROR,
        ),
        (testpackage_directory, ".setup.toml", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".customkeptcontract.toml", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".externalkeptcontract.toml", cli.EXIT_STATUS_SUCCESS),
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
        # Namespace packages
        (namespace_packages_directory, "keptcontract_portion.ini", cli.EXIT_STATUS_SUCCESS),
        (namespace_packages_directory, "keptcontract_namespace.ini", cli.EXIT_STATUS_SUCCESS),
        (namespace_packages_directory, "brokencontract_portion.ini", cli.EXIT_STATUS_ERROR),
        (namespace_packages_directory, "brokencontract_namespace.ini", cli.EXIT_STATUS_ERROR),
        # Type checking imports
        (testpackage_directory, ".typecheckkeptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (testpackage_directory, ".typecheckbrokencontract.ini", cli.EXIT_STATUS_ERROR),
        # Acyclic siblings
        (cyclicpackage_directory, ".keptcontract.ini", cli.EXIT_STATUS_SUCCESS),
        (cyclicpackage_directory, ".brokencontract.ini", cli.EXIT_STATUS_ERROR),
    ),
)
def test_lint_imports(working_directory, config_filename, expected_result):
    os.chdir(working_directory)

    if config_filename:
        result = cli.lint_imports(config_filename=config_filename)
    else:
        result = cli.lint_imports()

    assert expected_result == result


def test_lint_imports_renders_broken_contract_guidance_for_broken_contract(capsys):
    os.chdir(testpackage_directory)

    result = cli.lint_imports(config_filename=".brokencontractguidance.ini")

    assert cli.EXIT_STATUS_ERROR == result
    captured = capsys.readouterr()
    assert "Use the testpackage.high top-level interface." in captured.out
    assert "More information here: http://docs.example.com/high" in captured.out


def test_lint_imports_raises_clear_error_when_root_package_is_single_file(capsys):
    os.chdir(testpackage_directory)

    result = cli.lint_imports(config_filename=".singlefilemodulecontract.ini")

    assert cli.EXIT_STATUS_ERROR == result
    captured = capsys.readouterr()
    assert "'single_file_module' is a module, not a package" in captured.out


def test_lint_imports_rejects_duplicate_layers(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:layers]\n"
        "name = Duplicate layers\n"
        "type = layers\n"
        "layers =\n"
        "    testpackage.high\n"
        "    testpackage.low : testpackage.high\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, ["--config", str(config)])

    assert result.exit_code == cli.EXIT_STATUS_ERROR
    assert "Modules cannot be in more than one layer:" in result.output
    assert "'testpackage.high'." in result.output
    assert "Traceback" not in result.output


def test_lint_imports_rejects_nested_layers(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:layers]\n"
        "name = Nested layers\n"
        "type = layers\n"
        "layers =\n"
        "    testpackage\n"
        "    testpackage.high\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, ["--config", str(config)])

    assert result.exit_code == cli.EXIT_STATUS_ERROR
    assert "Layers cannot contain other layers:" in result.output
    assert "'testpackage' contains" in result.output
    assert "'testpackage.high'" in result.output
    assert "Traceback" not in result.output


def test_lint_imports_forbidden_out_of_scope_error(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:forbidden]\n"
        "name = Forbidden out of scope\n"
        "type = forbidden\n"
        "source_modules = testpackage.low\n"
        "forbidden_modules = testpackage.medium\n"
        "ignore_imports =\n"
        "    testpackage.utils -> testpackage.high.green\n"
        "out_of_scope_ignore_imports_alerting = error\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, [str(config)])

    assert result.exit_code == cli.EXIT_STATUS_ERROR
    assert "Ignored import testpackage.utils -> testpackage.high.green" in result.output
    assert "is outside the" in result.output
    assert "of the contract." in result.output
    assert "Traceback" not in result.output


def test_lint_imports_forbidden_out_of_scope_warn(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:forbidden]\n"
        "name = Forbidden out of scope warn\n"
        "type = forbidden\n"
        "source_modules = testpackage.low\n"
        "forbidden_modules = testpackage.medium\n"
        "ignore_imports =\n"
        "    testpackage.utils -> testpackage.high.green\n"
        "out_of_scope_ignore_imports_alerting = warn\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, [str(config)])

    assert result.exit_code == cli.EXIT_STATUS_SUCCESS
    assert "Warnings" in result.output
    assert "Ignored import testpackage.utils -> testpackage.high.green" in result.output
    assert "is outside the" in result.output
    assert "of the contract." in result.output
    assert "Traceback" not in result.output


def test_lint_imports_forbidden_out_of_scope_none(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:forbidden]\n"
        "name = Forbidden out of scope none\n"
        "type = forbidden\n"
        "source_modules = testpackage.low\n"
        "forbidden_modules = testpackage.medium\n"
        "ignore_imports =\n"
        "    testpackage.utils -> testpackage.high.green\n"
        "out_of_scope_ignore_imports_alerting = none\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, [str(config)])

    assert result.exit_code == cli.EXIT_STATUS_SUCCESS
    assert "Warnings" not in result.output
    assert "is outside the scope" not in result.output
    assert "Traceback" not in result.output


def test_lint_imports_unsupported_contract_out_of_scope_alerting(tmp_path, monkeypatch):
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\n"
        "root_package = testpackage\n"
        "[importlinter:contract:layers]\n"
        "name = Unsupported contract out of scope\n"
        "type = layers\n"
        "layers =\n"
        "    testpackage.high\n"
        "    testpackage.medium\n"
        "out_of_scope_ignore_imports_alerting = error\n"
    )
    monkeypatch.chdir(testpackage_directory)

    result = CliRunner().invoke(cli.lint_imports_command, [str(config)])

    assert result.exit_code == cli.EXIT_STATUS_ERROR
    assert "out_of_scope_ignore_imports_alerting" in result.output
    assert "not supported for layers contracts." in result.output
    assert "Traceback" not in result.output


class TestMultipleConfigFiles:
    @pytest.mark.parametrize("command", (cli.lint_imports_command, cli.lint_command))
    def test_checks_contracts_from_all_files(self, command, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        result = CliRunner().invoke(
            command, [".brokencontract.ini", ".customkeptcontract.ini", "--no-logo"]
        )

        assert result.exit_code == cli.EXIT_STATUS_ERROR
        assert "Expected broken contract BROKEN" in result.output
        assert "Custom kept contract KEPT" in result.output
        assert "Contracts: 1 kept, 1 broken." in result.output
        # Both files have the same top level configuration, so they share a single graph,
        # and no breakdown table is shown.
        assert "Config files" not in result.output

    def test_builds_a_graph_for_each_distinct_top_level_configuration(self, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        result = CliRunner().invoke(
            cli.lint_imports_command,
            [
                ".customkeptcontract.ini",
                ".typecheckkeptcontract.ini",
                ".customkeptcontract.toml",
                "--no-logo",
                "--show-timings",
            ],
        )

        assert result.exit_code == cli.EXIT_STATUS_SUCCESS, result.output
        assert "Total 3 config files, 2 import graphs." in result.output
        assert "Contracts: 3 kept, 0 broken." in result.output

    def test_config_option_can_be_combined_with_positional_files(self, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        result = CliRunner().invoke(
            cli.lint_imports_command,
            ["--config", ".customkeptcontract.ini", ".typecheckkeptcontract.ini", "--no-logo"],
        )

        assert result.exit_code == cli.EXIT_STATUS_SUCCESS, result.output
        assert "Contracts: 2 kept, 0 broken." in result.output
        assert "DeprecationWarning: The option 'config' is deprecated" in result.output

    def test_ambiguous_contract_id_suggests_filenames(self, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        # Both files have a contract with the id "one".
        result = CliRunner().invoke(
            cli.lint_imports_command,
            [".brokencontract.ini", ".customkeptcontract.ini", "--contract=one", "--no-logo"],
        )

        assert result.exit_code == cli.EXIT_STATUS_ERROR
        assert "Multiple contracts found with the id 'one'." in result.output
        assert "--contract=.brokencontract.ini:one" in result.output
        assert "--contract=.customkeptcontract.ini:one" in result.output

    def test_contract_id_qualified_with_filename(self, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        result = CliRunner().invoke(
            cli.lint_imports_command,
            [
                ".brokencontract.ini",
                ".customkeptcontract.ini",
                "--contract=.customkeptcontract.ini:one",
                "--no-logo",
            ],
        )

        assert result.exit_code == cli.EXIT_STATUS_SUCCESS, result.output
        assert "Custom kept contract KEPT" in result.output
        assert "Expected broken contract" not in result.output

    def test_missing_file_errors(self, monkeypatch):
        monkeypatch.chdir(testpackage_directory)

        result = CliRunner().invoke(
            cli.lint_imports_command,
            [".customkeptcontract.ini", ".doesnotexist.ini", "--no-logo"],
        )

        assert result.exit_code == cli.EXIT_STATUS_ERROR
        assert "Could not find .doesnotexist.ini." in result.output


@pytest.mark.parametrize("is_debug_mode", (True, False))
def test_lint_imports_debug_mode(is_debug_mode):
    os.chdir(testpackage_directory)

    kwargs = dict(config_filename=".nonexistentcontract.ini", is_debug_mode=is_debug_mode)
    if is_debug_mode:
        with pytest.raises(FileNotFoundError):
            cli.lint_imports(**kwargs)
    else:
        assert cli.EXIT_STATUS_ERROR == cli.lint_imports(**kwargs)


def test_show_timings_smoke_test():
    os.chdir(testpackage_directory)
    assert cli.EXIT_STATUS_SUCCESS == cli.lint_imports(show_timings=True)


def test_no_logo_smoke_test():
    os.chdir(testpackage_directory)
    assert cli.EXIT_STATUS_SUCCESS == cli.lint_imports(no_logo=True)


@pytest.mark.parametrize("verbose", (True, False))
def test_logging_configuration_respects_verbose_flag(verbose, capsys):
    os.chdir(testpackage_directory)

    cli.lint_imports(verbose=verbose)

    captured = capsys.readouterr()

    # N.B. "Wrote data cache file" is logged by Grimp.
    assert ("Wrote data cache file" in captured.out) == verbose


@pytest.mark.parametrize("command", (cli.lint_imports_command, cli.import_linter))
def test_versions(command):
    runner = CliRunner()
    result = runner.invoke(command, ["--version"])

    assert result.output == f"import-linter {__version__}\n"


def test_windows_terminal_encoding_smoke_test():
    default_windows_terminal_encoding = "cp1252"
    console = output.Console(
        file=io.TextIOWrapper(
            io.BytesIO(),
            encoding=default_windows_terminal_encoding,
        )
    )
    os.chdir(testpackage_directory)

    with patch.object(output, "console", console):
        cli.lint_imports()
