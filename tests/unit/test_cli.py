"""Tests for CLI behaviour when UI dependencies (fastapi, uvicorn) are optional."""
import importlib
import sys
from unittest.mock import patch

from click.testing import CliRunner, Result

import importlinter.cli

_NOT_CACHED = object()


class TestCliWithOptionalUiDependencies:
    """CLI behaviour when [ui] extra is (not) installed."""

    def _invoke_explore_without_ui(self) -> Result:
        runner = CliRunner()
        # Remove the cached server module so it is freshly imported (and fails).
        # Also clear the attribute on the importlinter.ui package so that
        # `from importlinter.ui import server` doesn't find an already-bound reference.
        saved = sys.modules.pop("importlinter.ui.server", _NOT_CACHED)
        import importlinter.ui
        had_attr = hasattr(importlinter.ui, "server")
        if had_attr:
            delattr(importlinter.ui, "server")
        try:
            with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
                return runner.invoke(importlinter.cli.import_linter, ["explore", "somepackage"])
        finally:
            if saved is not _NOT_CACHED:
                sys.modules["importlinter.ui.server"] = saved
            if had_attr:
                importlinter.ui.server = sys.modules.get("importlinter.ui.server")

    def test_explore_without_ui_exits_with_error_and_helpful_message(self):
        result = self._invoke_explore_without_ui()
        assert result.exit_code == 1
        assert "pip install import-linter[ui]" in result.output

    def test_cli_can_be_imported_without_ui_deps(self):
        """Importing the CLI entry point must not fail when UI deps are absent."""
        # Remove the cached server module and mark fastapi/uvicorn as absent to
        # simulate an environment where only the base package is installed.
        saved = sys.modules.pop("importlinter.ui.server", _NOT_CACHED)
        try:
            with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
                importlib.reload(importlinter.cli)
        finally:
            if saved is not _NOT_CACHED:
                sys.modules["importlinter.ui.server"] = saved
            # Restore cli module to its original state for subsequent tests.
            importlib.reload(importlinter.cli)
