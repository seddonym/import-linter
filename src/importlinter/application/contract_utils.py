import enum
from typing import Optional, Sequence

from importlinter.application import output
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
) -> None:
    """
    Remove any ignored imports from the graph.

    Args:
        graph:              The graph that is being checked by a contract.
        ignore_imports:     Any import expressions that indicate imports to ignore.
        unmatched_alerting: An AlertLevel that indicates how to handle any import expressions that
                            don't match any imports. AlertLevel.NONE will ignore them,
                            AlertLevel.WARN will warn for each one, and AlertLevel.ERROR will raise
                            an exception for the first one encountered.
    """
    unresolved = helpers.pop_unresolved_import_expressions(
        graph, ignore_imports if ignore_imports else []  # type: ignore
    )[1]
    _handle_unresolved_import_expressions(
        unresolved,
        unmatched_alerting,  # type: ignore
    )


# Private functions
# -----------------


def _handle_unresolved_import_expressions(
    expressions: Sequence[ImportExpression], alert_level: AlertLevel
) -> None:
    """
    Handle any unresolved import expressions based on the supplied alert level.

    Intended to be called while checking a contract.
    """
    if alert_level is AlertLevel.NONE:
        return
    if not expressions:
        return

    if alert_level is AlertLevel.WARN:
        for expression in expressions:
            output.print_warning(
                f"Ignored import expression {expression} " "didn't match anything in the graph."
            )
    else:  # AlertLevel.ERROR
        expression_str = sorted(str(expression) for expression in expressions)[0]
        raise MissingImport(
            f"Ignored import expression {expression_str} " "didn't match anything in the graph."
        )
