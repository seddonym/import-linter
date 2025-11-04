import enum
from collections.abc import Sequence


from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import ImportExpression, DirectImport, Module
from grimp import ImportGraph


class AlertLevel(enum.Enum):
    NONE = "none"
    WARN = "warn"
    ERROR = "error"


def remove_ignored_imports(
    graph: ImportGraph,
    ignore_imports: Sequence[ImportExpression] | None,
    unmatched_alerting: AlertLevel,
) -> list[str]:
    """
    Remove any ignored imports from the graph.

    Args:
        graph:              The graph that is being checked by a contract.
        ignore_imports:     Any import expressions that indicate imports to ignore.
        unmatched_alerting: An AlertLevel that indicates how to handle any import expressions that
                            don't match any imports. AlertLevel.NONE will ignore them,
                            AlertLevel.WARN will warn for each one, and AlertLevel.ERROR will raise
                            a MissingImport for the first one encountered.

    Returns:
        A list of any warnings to be surfaced to the user.
    """
    imports_to_remove = set()
    unresolved_expressions = set()
    for import_expression in ignore_imports or []:
        matched_imports = graph.find_matching_direct_imports(
            import_expression=str(import_expression)
        )
        if matched_imports:
            imports_to_remove.update(
                {
                    DirectImport(
                        importer=Module(matched_import["importer"]),
                        imported=Module(matched_import["imported"]),
                    )
                    for matched_import in matched_imports
                }
            )
        else:
            unresolved_expressions.add(import_expression)

    warnings = _handle_unresolved_import_expressions(
        unresolved_expressions,
        unmatched_alerting,
    )

    for import_to_remove in imports_to_remove:
        graph.remove_import(
            importer=import_to_remove.importer.name,
            imported=import_to_remove.imported.name,
        )

    return warnings


# Private functions
# -----------------


def _handle_unresolved_import_expressions(
    expressions: set[ImportExpression], alert_level: AlertLevel
) -> list[str]:
    """
    Handle any unresolved import expressions based on the supplied alert level.

    Intended to be called while checking a contract.

    Returns:
        A list of any warnings to be surfaced to the user.
    """
    if alert_level is AlertLevel.NONE:
        return []
    if not expressions:
        return []

    if alert_level is AlertLevel.WARN:
        return [_build_missing_import_message(expression) for expression in expressions]
    else:  # AlertLevel.ERROR
        first_expression = sorted(expressions, key=lambda expression: str(expression))[0]
        raise MissingImport(_build_missing_import_message(first_expression))


def _build_missing_import_message(expression: ImportExpression) -> str:
    return f"No matches for ignored import {expression}."
