from ..domain.contract import InvalidContractOptions, registry
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
        root_package_name=user_options.session_options['root_package_name'],
    )
    report = _build_report(
        graph=graph,
        user_options=user_options,
    )

    _print_report(report)

    if report.contains_failures:
        return FAILURE
    else:
        return SUCCESS


def _read_user_options() -> UserOptions:
    for reader in settings.USER_OPTION_READERS:
        options = reader.read_options()
        if options:
            return options
    raise RuntimeError('Could not read any configuration.')


def _build_graph(root_package_name: str) -> ImportGraph:
    return settings.GRAPH_BUILDER.build(root_package_name=root_package_name)


def _print_exception(exception: Exception) -> None:
    settings.PRINTER(exception)


def _build_report(graph: ImportGraph, user_options: UserOptions) -> Report:
    report = Report(graph=graph)
    for contract_options in user_options.contracts_options:
        contract_class = registry.get_contract_class(contract_options['type'])
        try:
            contract = contract_class(
                name=contract_options['name'],
                session_options=user_options.session_options,
                contract_options=contract_options)
        except InvalidContractOptions as e:
            report.add_invalid_contract_options(contract_options['name'], e)
            return report

        check = contract.check(graph)
        report.add_contract_check(contract, check)
    return report


def _print_report(report: Report) -> None:
    render_report(
        report=report,
    )


# def _get_contract_class(contract_type_string: str) -> Type[Contract]:
#     registry.
#     components = contract_class_string.split('.')
#     contract_class_name = components[-1]
#     module_name = '.'.join(components[:-1])
#     module = importlib.import_module(module_name)
#     contract_class = getattr(module, contract_class_name)
#     if not issubclass(contract_class, Contract):
#         raise TypeError(f'{contract_class} is not a subclass of Contract.')
#     return contract_class
