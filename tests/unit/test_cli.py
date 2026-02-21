"""Tests for CLI behaviour when UI dependencies (fastapi, uvicorn) are optional."""
import importlib
import sys
from unittest.mock import patch

from click.testing import CliRunner

import importlinter.cli as cli_module
from importlinter.cli import import_linter


class TestExploreWithoutUiDependencies:
    """explore should fail gracefully when the [ui] extra is not installed."""

    def _invoke_explore_without_ui(self):
        runner = CliRunner()
        # Remove the cached server module so it is freshly imported (and fails).
        saved = sys.modules.pop("importlinter.ui.server", ...)
        try:
            with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
                return runner.invoke(import_linter, ["explore", "somepackage"])
        finally:
            if saved is not ...:
                sys.modules["importlinter.ui.server"] = saved

    def test_exits_with_error_code(self):
        result = self._invoke_explore_without_ui()
        assert result.exit_code == 1

    def test_prints_helpful_message(self):
        result = self._invoke_explore_without_ui()
        assert "pip install import-linter[ui]" in result.output


class TestLintWithoutUiDependencies:
    """lint-imports and import-linter lint should work without UI dependencies."""

    def test_lint_imports_command_does_not_require_ui_deps(self):
        """Importing the CLI entry point must not fail when UI deps are absent."""
        # Remove the cached server module and mark fastapi/uvicorn as absent to
        # simulate an environment where only the base package is installed.
        saved = sys.modules.pop("importlinter.ui.server", ...)
        try:
            with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
                importlib.reload(cli_module)
        finally:
            if saved is not ...:
                sys.modules["importlinter.ui.server"] = saved
            # Restore cli module to its original state for subsequent tests.
            importlib.reload(cli_module)
