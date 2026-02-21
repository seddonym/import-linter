import pytest
from click.testing import CliRunner

import importlinter.cli
import importlinter.ui


@pytest.mark.no_ui_deps_installed
class TestCliWithoutUiDependencies:
    def test_drawgraph_exits_successfully(self):
        result = CliRunner().invoke(importlinter.cli.import_linter, ["drawgraph", "importlinter"])
        assert result.exit_code == 0

    def test_explore_exits_with_error_and_helpful_message(self):
        result = CliRunner().invoke(importlinter.cli.import_linter, ["explore", "somepackage"])
        assert result.exit_code == 1
        assert "pip install import-linter[ui]" in result.output

    def test_lint_help_exits_successfully(self):
        result = CliRunner().invoke(importlinter.cli.import_linter, ["lint", "--help"])
        assert result.exit_code == 0
