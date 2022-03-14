import enum
from typing import List, Optional, Sequence, Set

from importlinter.domain import helpers
from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import ImportExpression
from importlinter.domain.ports.graph import ImportGraph


class AlertLevel(enum.Enum):
    NONE = "none"
    WARN = "warn"
    ERROR = "error"


def remove_ignored_imports(
    graph: ImportGraph,
    ignore_imports: Optional[Sequence[ImportExpression]],
    unmatched_alerting: AlertLevel,
) -> List[str]:
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
    imports, unresolved_expressions = helpers.resolve_import_expressions(
        graph=graph, expressions=ignore_imports if ignore_imports else []
    )

    warnings = _handle_unresolved_import_expressions(
        unresolved_expressions,
        unmatched_alerting,  # type: ignore
    )

    helpers.pop_imports(graph, imports)

    return warnings


# Private functions
# -----------------


def _handle_unresolved_import_expressions(
    expressions: Set[ImportExpression], alert_level: AlertLevel
) -> List[str]:
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
