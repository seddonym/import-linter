from typing import Iterable

from ..domain.contract import Contract
from .user_options import UserOptions
from .ports.reporting import Report
from ..domain.ports.graph import ImportGraph
from .app_config import settings
from .rendering import render_report


class AlreadyReportedError(Exception):
    pass


SUCCESS, FAILURE = 'SUCCESS', 'FAILURE'


def check_contracts_and_print_report():
    """
    Analyse whether a Python package follows a set of contracts, and report on the results.

    If an an error is encountered, or if the contracts are not followed, it will report the details
    and then raise an AlreadyReportedError.
    """
    user_options = _read_user_options()
    graph = _build_graph(
        root_package_name=user_options.root_package_name,
    )
    report = _build_report(
        graph=graph,
        contracts=user_options.contracts,
    )

    _print_report(report)

    if report.contains_failures:
        return FAILURE
    else:
        return SUCCESS

    # try:
    #     user_options = _read_user_options()
    #     graph = _build_graph(
    #         root_package_name=user_options.root_package_name,
    #     )
    #     report = _build_report(
    #         graph=graph,
    #         contracts=user_options.contracts,
    #     )
    # except Exception as e:
    #     _print_exception(e)
    #     raise AlreadyReportedError



def _read_user_options() -> UserOptions:
    return settings.USER_OPTION_READER.read()


def _build_graph(root_package_name: str) -> ImportGraph:
    return settings.GRAPH_BUILDER.build(root_package_name=root_package_name)


def _print_exception(exception: Exception) -> None:
    settings.PRINTER(exception)


def _build_report(graph: ImportGraph, contracts: Iterable[Contract]) -> Report:
    report = Report(graph=graph)
    for contract in contracts:
        check = contract.check(graph)
        report.add_contract_check(contract, check)
    return report


def _print_report(report: Report) -> None:
    render_report(
        printer=settings.PRINTER,
        report=report,
    )
