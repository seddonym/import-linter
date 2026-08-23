from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent

import grimp

from importlinter.application.output import console
from importlinter.contracts.symbol_visibility import SymbolVisibilityContract

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


def _contract(**contract_options: object) -> SymbolVisibilityContract:
    return SymbolVisibilityContract(
        name="Private symbols stay in their module",
        session_options={"root_packages": [PACKAGE]},
        contract_options=contract_options,
    )


def test_kept_when_private_symbol_is_only_used_in_defining_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1

            def public():
                return _parse_config()
        """,
        "b.py": """
            from vispkg.a import public
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_broken_when_private_symbol_is_imported_from_another_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1
        """,
        "b.py": """
            from vispkg.a import _parse_config
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    [violation] = check.metadata["violations"]
    assert violation.symbol == "_parse_config"
    assert violation.defining_module == f"{PACKAGE}.a"
    assert violation.importer == f"{PACKAGE}.b"


def test_broken_when_private_symbol_is_imported_with_a_relative_import(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1
        """,
        "b.py": """
            from .a import _parse_config
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    [violation] = check.metadata["violations"]
    assert violation.defining_module == f"{PACKAGE}.a"
    assert violation.importer == f"{PACKAGE}.b"


def test_broken_when_private_symbol_is_reached_through_module_attribute(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1
        """,
        "b.py": """
            from vispkg import a

            value = a._parse_config()
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    symbols = {violation.symbol for violation in check.metadata["violations"]}
    assert "_parse_config" in symbols


def test_kept_when_attribute_is_on_imported_class_not_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            class Owner:
                def _hidden(self):
                    return 1
        """,
        "b.py": """
            from vispkg.a import Owner

            Owner()._hidden()
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_private_name_is_a_dunder(tmp_path: Path) -> None:
    files = {
        "__init__.py": """
            __all__ = ["public"]
        """,
        "a.py": """
            from vispkg import __all__
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_kept_when_private_name_is_a_submodule(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "_hidden.py": """
            VALUE = 1
        """,
        "b.py": """
            from vispkg import _hidden
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert check.kept


def test_homonyms_are_keyed_by_defining_module(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _helper():
                return "a"
        """,
        "c.py": """
            def _helper():
                return "c"
        """,
        "b.py": """
            from vispkg.a import _helper
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract().check(graph=graph, verbose=False)

    assert not check.kept
    [violation] = check.metadata["violations"]
    assert violation.defining_module == f"{PACKAGE}.a"


def test_ignore_imports_skips_the_private_symbol_reference(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1
        """,
        "b.py": """
            from vispkg.a import _parse_config
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        check = _contract(
            ignore_imports=(f"{PACKAGE}.b -> {PACKAGE}.a",),
        ).check(graph=graph, verbose=False)

    assert check.kept


def test_render_broken_contract(tmp_path: Path) -> None:
    files = {
        "__init__.py": "",
        "a.py": """
            def _parse_config():
                return 1
        """,
        "b.py": """
            from vispkg.a import _parse_config
        """,
    }
    with _graph_for(tmp_path, files) as graph:
        contract = _contract()
        check = contract.check(graph=graph, verbose=False)
        with console.capture() as capture:
            contract.render_broken_contract(check)

    rendered = capture.get()
    assert "Private symbol vispkg.a._parse_config is referenced from another module:" in rendered
    assert "vispkg.b:" in rendered
    assert "from vispkg.a import _parse_config" in rendered


def test_kept_when_graph_has_no_importable_sources() -> None:
    graph = grimp.ImportGraph()
    graph.add_module(PACKAGE)
    graph.add_module(f"{PACKAGE}.a")

    check = _contract().check(graph=graph, verbose=False)

    assert check.kept
