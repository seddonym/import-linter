import enum
from collections.abc import Sequence
from dataclasses import dataclass

from grimp import ImportGraph

from importlinter.application import output
from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import DirectImport, ImportExpression, Module


class AlertLevel(enum.Enum):
    NONE = "none"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True)
class ImportRemoval:
    """
    The result of removing a set of ignored imports from a graph.
    """

    removed_imports: frozenset[DirectImport]
    warnings: tuple[str, ...]

    @property
    def ignored_import_count(self) -> int:
        return len(self.removed_imports)


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
                            a MissingImport with all unmatched imports.

    Returns:
        A list of any warnings to be surfaced to the user.
    """
    import_removal = remove_ignored_imports_and_report(graph, ignore_imports, unmatched_alerting)
    return list(import_removal.warnings)


def remove_ignored_imports_and_report(
    graph: ImportGraph,
    ignore_imports: Sequence[ImportExpression] | None,
    unmatched_alerting: AlertLevel,
) -> ImportRemoval:
    """
    Remove any ignored imports from the graph.

    Behaves the same as remove_ignored_imports, except it returns an object
    with more information about what was removed.

    Args:
        graph:              The graph that is being checked by a contract.
        ignore_imports:     Any import expressions that indicate imports to ignore.
        unmatched_alerting: An AlertLevel that indicates how to handle any import expressions that
                            don't match any imports. AlertLevel.NONE will ignore them,
                            AlertLevel.WARN will warn for each one, and AlertLevel.ERROR will raise
                            a MissingImport with all unmatched imports.

    Returns:
        An ImportRemoval, containing the DirectImports that were removed from the graph and any
        warnings to be surfaced to the user.
    """
    imports_to_remove: set[DirectImport] = set()
    unresolved_expressions = []
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
            if import_expression not in unresolved_expressions:
                unresolved_expressions.append(import_expression)

    resolved_warnings = _handle_unresolved_import_expressions(
        unresolved_expressions,
        unmatched_alerting,
    )

    for import_to_remove in imports_to_remove:
        graph.remove_import(
            importer=import_to_remove.importer.name,
            imported=import_to_remove.imported.name,
        )

    return ImportRemoval(
        removed_imports=frozenset(imports_to_remove),
        warnings=tuple(resolved_warnings),
    )


def render_broken_contract_guidance(broken_contract_guidance: str | None) -> None:
    """
    Output any guidance for fixing a broken contract.

    Intended to be called at the end of a contract's render_broken_contract method.

    Args:
        broken_contract_guidance: Guidance supplied by whoever defined the contract.
                                  If there isn't any, nothing is rendered.
    """
    if not broken_contract_guidance:
        return

    output.print(broken_contract_guidance)
    output.new_line()


# Private functions
# -----------------


def _handle_unresolved_import_expressions(
    expressions: list[ImportExpression], alert_level: AlertLevel
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
        messages = [_build_missing_import_message(expr) for expr in expressions]
        raise MissingImport("\n".join(messages))


def _build_missing_import_message(expression: ImportExpression) -> str:
    return f"No matches for ignored import {expression}."
