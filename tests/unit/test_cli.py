"""Tests for CLI behaviour when UI dependencies (fastapi, uvicorn) are optional."""
import importlib
import sys
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from click.testing import CliRunner, Result


@pytest.fixture
def ui_dependencies_absent() -> Iterator[None]:
    """Simulate an environment where the [ui] extra is not installed.

    Removes the cached server module from sys.modules and clears the bound
    attribute on the importlinter.ui package so that a fresh import attempt
    of ``from importlinter.ui import server`` will fail due to missing
    fastapi/uvicorn.
    """
    import importlinter.ui

    server_module_before = sys.modules.pop("importlinter.ui.server", None)
    server_module_bound_on_ui_package = hasattr(importlinter.ui, "server")
    if server_module_bound_on_ui_package:
        delattr(importlinter.ui, "server")

    with patch.dict(sys.modules, {"fastapi": None, "uvicorn": None}):
        yield

    if server_module_before is not None:
        sys.modules["importlinter.ui.server"] = server_module_before
    if server_module_bound_on_ui_package:
        importlinter.ui.server = sys.modules.get("importlinter.ui.server")


class TestCliWithoutUiDependencies:
    """CLI behaviour when [ui] extra is not installed."""

    def test_explore_without_ui_exits_with_error_and_helpful_message(
        self, ui_dependencies_absent: None
    ) -> None:
        import importlinter.cli

        result = CliRunner().invoke(importlinter.cli.import_linter, ["explore", "somepackage"])
        assert result.exit_code == 1
        assert "pip install import-linter[ui]" in result.output

    def test_cli_can_be_imported_without_ui_deps(self, ui_dependencies_absent: None) -> None:
        """Importing the CLI entry point must not fail when UI deps are absent."""
        import importlinter.cli

        importlib.reload(importlinter.cli)
