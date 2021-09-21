import itertools
import re
from typing import Dict, Iterable, List, Pattern, Set, Tuple, Union, cast

from importlinter.domain.imports import DirectImport, ImportExpression, Module
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
        MissingImport if an import is not present in the graph.
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


def import_expressions_to_imports(
    graph: ImportGraph, expressions: Iterable[ImportExpression]
) -> List[DirectImport]:
    """
    Returns a list of imports in a graph, given some import expressions.

    Raises:
        MissingImport if an import is not present in the graph. For a wildcarded import expression,
        this is raised if there is not at least one match.
    """
    imports: Set[DirectImport] = set()
    for expression in expressions:
        matched = False
        for (importer, imported) in _expression_to_modules(expression, graph):
            import_details = graph.get_import_details(
                importer=importer.name, imported=imported.name
            )
            if import_details:
                for individual_import_details in import_details:
                    imports.add(
                        DirectImport(
                            importer=Module(cast(str, individual_import_details["importer"])),
                            imported=Module(cast(str, individual_import_details["imported"])),
                            line_number=cast(int, individual_import_details["line_number"]),
                            line_contents=cast(str, individual_import_details["line_contents"]),
                        )
                    )
                matched = True
        if not matched:
            raise MissingImport(
                f"Ignored import expression {expression} didn't match anything in the graph."
            )
    return list(imports)


def pop_import_expressions(
    graph: ImportGraph, expressions: Iterable[ImportExpression]
) -> List[Dict[str, Union[str, int]]]:
    """
    Removes any imports matching the supplied import expressions from the graph.

    Returns:
        The list of imports that were removed, including any additional metadata.
    Raises:
        MissingImport if an import is not present in the graph. For a wildcarded import expression,
        this is raised if there is not at least one match.
    """
    imports = import_expressions_to_imports(graph, expressions)
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
        if "*" == part:
            pattern_parts.append(part.replace("*", r"[^\.]+"))
        else:
            pattern_parts.append(part)
    return re.compile(r"^" + r"\.".join(pattern_parts) + r"$")


def _expression_to_modules(
    expression: ImportExpression, graph: ImportGraph
) -> Iterable[Tuple[Module, Module]]:
    if not expression.has_wildcard_expression():
        return [(Module(expression.importer), Module(expression.imported))]

    importer = []
    imported = []

    importer_pattern = _to_pattern(expression.importer)
    imported_expression = _to_pattern(expression.imported)

    for module in graph.modules:

        if importer_pattern.match(module):
            importer.append(Module(module))
        if imported_expression.match(module):
            imported.append(Module(module))

    return itertools.product(set(importer), set(imported))
