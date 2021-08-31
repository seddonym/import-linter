from grimp.adaptors.graph import ImportGraph  # type: ignore
from importlinter.domain.helpers import MissingImport, add_imports, import_expressions_to_imports
from importlinter.domain.imports import DirectImport, ImportExpression
import pytest


def test_add_imports():
    graph = ImportGraph()
    import_details = [
        {"importer": "a", "imported": "b", "line_number": 1, "line_contents": "lorem ipsum"},
        {"importer": "c", "imported": "d", "line_number": 2, "line_contents": "lorem ipsum 2"},
    ]
    assert not graph.modules
    add_imports(graph, import_details)
    assert graph.modules == {"a", "b", "c", "d"}


def test_import_expressions_to_imports():
    graph = ImportGraph()
    graph.add_module("mypackage")
    graph.add_module("other")
    graph.add_import(
        importer="mypackage.a", imported="other.foo", line_number=1, line_contents="-"
    )
    graph.add_import(
        importer="mypackage.b", imported="other.foo", line_number=1, line_contents="-"
    )
    graph.add_import(
        importer="mypackage.c", imported="other.baz", line_number=1, line_contents="-"
    )

    expression = ImportExpression(importer="mypackage.*", imported="other.foo")
    assert import_expressions_to_imports(graph, [expression]) == [
        DirectImport(importer="mypackage.a", imported="other.foo"),
        DirectImport(importer="mypackage.b", imported="other.foo"),
    ]


def test_import_expressions_to_imports_fails():
    graph = ImportGraph()
    graph.add_module("mypackage")
    graph.add_module("other")
    graph.add_import(
        importer="mypackage.b", imported="other.foo", line_number=1, line_contents="-"
    )

    expression = ImportExpression(importer="mypackage.a.*", imported="other.foo")
    with pytest.raises(MissingImport):
        import_expressions_to_imports(graph, [expression])
