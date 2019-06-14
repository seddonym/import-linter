from typing import Dict, Iterable, List, Union

from importlinter.domain.imports import DirectImport
from importlinter.domain.ports.graph import ImportGraph


class MissingImport(Exception):
    pass


def pop_imports(
    graph: ImportGraph, imports: Iterable[DirectImport]
) -> List[Dict[str, Union[str, int]]]:
    """
    Removes the supplied direct imports from the graph.

    Returns:
        The list of import details that were removed, including any additional metadata.

    Raises:
        MissingImport if the import is not present in the graph.
    """
    removed_imports: List[Dict[str, Union[str, int]]] = []
    for import_to_remove in imports:
        import_details = graph.get_import_details(
            importer=import_to_remove.importer.name, imported=import_to_remove.imported.name
        )
        if not import_details:
            raise MissingImport(f"Ignored import {import_to_remove} not present in the graph.")
        removed_imports.extend(import_details)
        graph.remove_import(
            importer=import_to_remove.importer.name, imported=import_to_remove.imported.name
        )
    return removed_imports


def add_imports(graph: ImportGraph, import_details: List[Dict[str, Union[str, int]]]) -> None:
    """
    Adds the supplied import details to the graph.

    Intended to be the reverse of pop_imports, so the following code should leave the
    graph unchanged:

        import_details = pop_imports(graph, imports)
        add_imports(graph, import_details)
    """
    for details in import_details:
        assert isinstance(details["importer"], str)
        assert isinstance(details["imported"], str)
        assert isinstance(details["line_number"], int)
        assert isinstance(details["line_contents"], str)
        graph.add_import(
            importer=details["importer"],
            imported=details["imported"],
            line_number=details["line_number"],
            line_contents=details["line_contents"],
        )
