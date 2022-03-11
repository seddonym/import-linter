from typing import Sequence

from importlinter.application import output
from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import ImportExpression
from importlinter.application.contract_utils import AlertLevel


@enum.unique
class AlertLevel(enum.Enum):
    NONE = "none"
    WARN = "warn"
    ERROR = "error"


def handle_unresolved_import_expressions(
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
