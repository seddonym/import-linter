import itertools
from typing import Dict, Iterable, List, Tuple, Union, Pattern
import re

from importlinter.domain.imports import ImportExpression, Module, DirectImport
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


def pop_import_expressions(
    graph: ImportGraph, expressions: Iterable[ImportExpression]
) -> List[Dict[str, Union[str, int]]]:
    imports: List[DirectImport] = []
    for expression in expressions:
        was_any_removed = False
        for (importer, imported) in _expression_to_modules(expression, graph):
            import_details = graph.get_import_details(
                importer=importer.name, imported=imported.name
            )
            if import_details:
                imports.append(DirectImport(importer=imported, imported=imported))
                was_any_removed = True
        if not was_any_removed:
            raise MissingImport(
                f"Ignored import expresion {expression} didn't match anything in the graph."
            )
    return pop_imports(graph, imports)


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


def _to_pattern(expression: str) -> Pattern:
    """
    Function which translates an import expression into a regex pattern.
    """
    pattern_parts = []
    for part in expression.split("."):
        if "*" in part:
            pattern_parts.append(part.replace("*", r"[^\.]+"))
        else:
            pattern_parts.append(part)
    return re.compile(r"\.".join(pattern_parts))


def _expression_to_modules(
    expression: ImportExpression, graph: ImportGraph
) -> Iterable[Tuple[Module, Module]]:
    importer = []
    imported = []

    importer_pattern = _to_pattern(expression.importer)
    imported_expression = _to_pattern(expression.imported)

    for module in graph.modules:

        if importer_pattern.match(module):
            importer.append(Module(module))
        if imported_expression.match(module):
            imported.append(Module(module))

    return itertools.product(importer, imported)
