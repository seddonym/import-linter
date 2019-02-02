from typing import Iterable

from ..domain.contract import Contract
from .user_options import UserOptions
from .ports.report import Report
from .ports.graph import Graph
from .app_config import settings


class AlreadyReportedError(Exception):
    pass


def analyse_and_report():
    """
    Analyse whether a Python package follows a set of contracts, and report on the results.

    If an an error is encountered, or if the contracts are not followed, it will report the details
    and then raise an AlreadyReportedError.
    """
    try:
        user_options = _read_user_options()
        graph = _build_graph(
            root_package_name=user_options.root_package_name,
        )
        report = _build_report(
            graph=graph,
            contracts=user_options.contracts,
        )
    except Exception as e:
        _report_exception(e)
        raise AlreadyReportedError

    _render_report(report)

    if report.contains_failures:
        raise AlreadyReportedError


def _read_user_options() -> UserOptions:
    return UserOptions(
        root_package_name='grimp',
        contracts=(
            Contract(),
            Contract(),
        )
    )


def _build_graph(root_package_name: str) -> Graph:
    return settings.BUILD_GRAPH(root_package_name)


def _report_exception(exception: Exception) -> None:
    settings.REPORT_EXCEPTION(exception)


def _build_report(graph: Graph, contracts: Iterable[Contract]) -> Report:
    report = Report(graph=graph)
    for contract in contracts:
        ...


def _render_report(report: Report) -> None:
    settings.RENDER_REPORT(report=report)
