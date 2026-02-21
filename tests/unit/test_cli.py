"""Tests for CLI behaviour when UI dependencies (fastapi, uvicorn) are optional."""
import importlib
import sys
from unittest.mock import patch

from click.testing import CliRunner

import importlinter.cli as cli_module
from importlinter.cli import import_linter


class TestExploreWithoutUiDependencies:
    """explore should fail gracefully when the [ui] extra is not installed."""

    def test_exits_with_error_code(self):
        runner = CliRunner()
        with patch.dict(sys.modules, {"importlinter.ui.server": None}):
            result = runner.invoke(import_linter, ["explore", "somepackage"])
        assert result.exit_code == 1

    def test_prints_helpful_message(self):
        runner = CliRunner()
        with patch.dict(sys.modules, {"importlinter.ui.server": None}):
            result = runner.invoke(import_linter, ["explore", "somepackage"])
        assert "pip install import-linter[ui]" in result.output


class TestLintWithoutUiDependencies:
    """lint-imports and import-linter lint should work without UI dependencies."""

    def test_lint_imports_command_does_not_require_ui_deps(self):
        """Importing the CLI entry point must not fail when UI deps are absent."""
        # If the top-level import of server were present, reloading cli without
        # fastapi would raise an ImportError.  Patching out the server module
        # simulates the absence of the [ui] extra.
        with patch.dict(sys.modules, {"importlinter.ui.server": None, "fastapi": None}):
            # Re-importing should not raise even when fastapi is "missing".
            try:
                importlib.reload(cli_module)
            finally:
                # Restore the real module for other tests.
                importlib.reload(cli_module)
