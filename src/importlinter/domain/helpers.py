import fnmatch
import itertools
from typing import Dict, Iterable, List, Tuple, Union

from importlinter.domain.imports import ImportExpression, Module
from importlinter.domain.ports.graph import ImportGraph


class MissingImport(Exception):
    pass


def pop_imports(
    graph: ImportGraph, imports: Iterable[ImportExpression]
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
        was_any_removed = False

        for (importer, imported) in to_modules(import_to_remove, graph):
            import_details = graph.get_import_details(
                importer=importer.name, imported=imported.name
            )
            if import_details:
                was_any_removed = True
                removed_imports.extend(import_details)
                graph.remove_import(importer=importer.name, imported=imported.name)
        if not was_any_removed:
            raise MissingImport(f"Ignored import {import_to_remove} not present in the graph.")

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

def to_modules(expression: ImportExpression, graph: ImportGraph) -> Iterable[Tuple[Module, Module]]:
    importer = []
    imported = []

    for module in graph.modules:
        if fnmatch.fnmatch(module, expression.importer):
            importer.append(Module(module))
        if fnmatch.fnmatch(module, expression.imported):
            imported.append(Module(module))

    return itertools.product(importer, imported)
