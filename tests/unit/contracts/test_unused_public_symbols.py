from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent

import grimp

from importlinter.application.output import console
from importlinter.contracts.unused_public_symbols import UnusedPublicSymbolsContract

PACKAGE = "vispkg"


def _purge_package() -> None:
    for key in list(sys.modules):
        if key == PACKAGE or key.startswith(PACKAGE + "."):
            del sys.modules[key]
    importlib.invalidate_caches()


def _write_package(root: Path, files: dict[str, str]) -> None:
    pkg = root / PACKAGE
    pkg.mkdir()
    for relative, contents in files.items():
        path = pkg / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(contents).lstrip("\n"), encoding="utf-8")


@contextmanager
def _graph_for(root: Path, files: dict[str, str]) -> Iterator[grimp.ImportGraph]:
    _purge_package()
    _write_package(root, files)
    sys.path.insert(0, str(root))
    importlib.invalidate_caches()
    try:
        yield grimp.build_graph(PACKAGE)
    finally:
        sys.path.remove(str(root))
        _purge_package()


def _contract(**contract_options: object) -> UnusedPublicSymbolsContract:
    return UnusedPublicSymbolsContract(
        name="Unused public names should be private",
        session_options={"root_packages": [PACKAGE]},
        contract_options=contract_options,
    )


def test_broken_when_public_symbol_has_no_in_package_users(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    symbols = {violation.symbol for violation in check.metadata["violations"]}
    assert "parse_internal_state" in symbols


def test_kept_when_public_symbol_is_imported_from_another_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": """
            from vispkg.a import parse_internal_state
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_public_symbol_is_imported_with_a_relative_import(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": """
            from .a import parse_internal_state
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_public_symbol_is_reached_through_module_attribute(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": """
            from vispkg import a

            a.parse_internal_state()
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_unused_public_name_is_listed_in_all(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            __all__ = ["connect"]

            def connect():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_broken_when_all_is_ignored_and_name_is_unused(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            __all__ = ["connect"]

            def connect():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract(respect_all="false").check(graph=graph, verbose=False)

    assert not check.kept
    symbols = {violation.symbol for violation in check.metadata["violations"]}
    assert "connect" in symbols


def test_kept_when_defined_in_configured_public_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "api.py": """
            def connect():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract(public_modules=[f"{PACKAGE}.api"]).check(graph=graph, verbose=False)

    assert check.kept


def test_public_modules_do_not_treat_descendants_as_public(tmp_path: Path) -> None:
    files = {
        "__init__.py": """
            def connect():
                return 1
        """,
        "internal.py": """
            def leftover():
                return 1
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract(public_modules=[PACKAGE]).check(graph=graph, verbose=False)

    assert not check.kept
    [violation] = [item for item in check.metadata["violations"] if item.symbol == "leftover"]
    assert violation.defining_module == f"{PACKAGE}.internal"
    symbols = {item.symbol for item in check.metadata["violations"]}
    assert "connect" not in symbols


def test_kept_when_star_import_consumes_public_names(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": """
            from vispkg.a import *
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_all_is_dynamic(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            NAMES = ["connect"]
            __all__ = NAMES

            def connect():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_name_is_already_private(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_internal_state():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_homonyms_are_keyed_by_defining_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def helper():
                return "a"
        """,
        "c.py": """
            def helper():
                return "c"
        """,
        "b.py": """
            from vispkg.c import helper
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    [violation] = check.metadata["violations"]
    assert violation.symbol == "helper"
    assert violation.defining_module == f"{PACKAGE}.a"


def test_render_broken_contract(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def parse_internal_state():
                return 1
        """,
        "b.py": "",
    }
    with _graph_for(tmp_path, files) as graph:
        contract = _contract()
        check = contract.check(graph=graph, verbose=False)
        with console.capture() as capture:
            contract.render_broken_contract(check)

    rendered = " ".join(capture.get().split())
    assert (
        "Public symbol vispkg.a.parse_internal_state has no in-package users and is not exported:"
        in rendered
    )
    assert "vispkg.a:" in rendered
    assert "def parse_internal_state():" in rendered


def test_kept_when_graph_has_no_importable_sources() -> None:
    graph = grimp.ImportGraph()
    graph.add_module(PACKAGE)
    graph.add_module(f"{PACKAGE}.a")

    check = _contract().check(graph=graph, verbose=False)

    assert check.kept
