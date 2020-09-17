from grimp.adaptors.graph import ImportGraph  # type: ignore
from importlinter.domain.helpers import add_imports


def test_add_imports():
    graph = ImportGraph()
    import_details = [
        {"importer": "a", "imported": "b", "line_number": 1, "line_contents": "lorem ipsum"},
        {"importer": "c", "imported": "d", "line_number": 2, "line_contents": "lorem ipsum 2"},
    ]
    assert not graph.modules
    add_imports(graph, import_details)
    assert graph.modules == {"a", "b", "c", "d"}
