import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import importlinter.cli
import importlinter.ui


class TestCliWithoutUiDependencies:
    @pytest.fixture(autouse=True)
    def ui_dependencies_absent(self):
        """Simulate an environment where the [ui] extra is not installed."""
        server_module = sys.modules.pop("importlinter.ui.server", None)
        server_module_is_bound_on_ui_package = hasattr(importlinter.ui, "server")
        if server_module_is_bound_on_ui_package:
            delattr(importlinter.ui, "server")

        with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
            yield

        if server_module is not None:
            sys.modules["importlinter.ui.server"] = server_module
        if server_module_is_bound_on_ui_package:
            if server_module is not None:
                importlinter.ui.server = server_module

    def test_explore_exits_with_error_and_helpful_message(self):
        result = CliRunner().invoke(importlinter.cli.import_linter, ["explore", "somepackage"])
        assert result.exit_code == 1
        assert "pip install import-linter[ui]" in result.output

    def test_drawgraph_exits_successfully(self):
        result = CliRunner().invoke(
            importlinter.cli.import_linter, ["drawgraph", "importlinter"]
        )
        assert result.exit_code == 0

    def test_lint_help_exits_successfully(self):
        result = CliRunner().invoke(importlinter.cli.import_linter, ["lint", "--help"])
        assert result.exit_code == 0
