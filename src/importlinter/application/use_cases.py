from typing import Type, List, Tuple, Optional
import importlib

from ..domain.contract import InvalidContractOptions, registry, Contract
from .user_options import UserOptions
from .ports.reporting import Report
from ..domain.ports.graph import ImportGraph
from .app_config import settings
from . rendering import render_report, render_exception


# Public functions
# ----------------

SUCCESS = True
FAILURE = False


def lint_imports(config_filename: Optional[str] = None) -> bool:
    """
    Analyse whether a Python package follows a set of contracts, and report on the results.

    This function attempts to handle and report all exceptions, too.

    Args:
        config_filename: the filename to use to parse user options.

    Returns:
        True if the linting passed, False if it didn't.
    """
    try:
        user_options = _read_user_options(config_filename=config_filename)
        _register_contract_types(user_options)
        report = create_report(user_options)
    except Exception as e:
        render_exception(e)
        return FAILURE

    render_report(report)

    if report.contains_failures:
        return FAILURE
    else:
        return SUCCESS


def create_report(user_options: UserOptions) -> Report:
    """
    Analyse whether a Python package follows a set of contracts, returning a report on the results.

    Raises:
        InvalidUserOptions: if the report could not be run due to invalid user configuration,
                            such as a module that could not be imported.
    """
    include_external_packages = _get_include_external_packages(user_options)
    graph = _build_graph(
        root_package_name=user_options.session_options['root_package'],
        include_external_packages=include_external_packages,
    )
    return _build_report(
        graph=graph,
        user_options=user_options,
    )


# Private functions
# -----------------


def _read_user_options(config_filename: Optional[str] = None) -> UserOptions:
    for reader in settings.USER_OPTION_READERS:
        options = reader.read_options(config_filename=config_filename)
        if options:
            return options
    raise RuntimeError('Could not read any configuration.')


def _build_graph(root_package_name: str, include_external_packages: Optional[bool]) -> ImportGraph:
    return settings.GRAPH_BUILDER.build(
        root_package_name=root_package_name,
        include_external_packages=include_external_packages,
    )


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


def _register_contract_types(user_options: UserOptions) -> None:
    contract_types = (
        _get_built_in_contract_types() + _get_plugin_contract_types(user_options)
    )
    for name, contract_class in contract_types:
        registry.register(contract_class, name)


def _get_built_in_contract_types() -> List[Tuple[str, Type[Contract]]]:
    return list(map(
        _parse_contract_type_string,
        [
            'layers: importlinter.contracts.layers.LayersContract',
            'independence: importlinter.contracts.independence.IndependenceContract',
        ]
    ))


def _get_plugin_contract_types(user_options: UserOptions) -> List[Tuple[str, Type[Contract]]]:
    contract_types = []
    if 'contract_types' in user_options.session_options:
        for contract_type_string in user_options.session_options['contract_types']:
            contract_types.append(
                _parse_contract_type_string(contract_type_string)
            )
    return contract_types


def _parse_contract_type_string(string) -> Tuple[str, Type[Contract]]:
    components = string.split(': ')
    assert len(components) == 2
    name, contract_class_string = components
    contract_class = _string_to_class(contract_class_string)
    if not issubclass(contract_class, Contract):
        raise TypeError(f'{contract_class} is not a subclass of Contract.')
    return name, contract_class


def _string_to_class(string: str) -> Type:
    """
    Parse a string into a Python class.

    Args:
        string: a fully qualified string of a class, e.g. 'mypackage.foo.MyClass'.

    Returns:
        The class.
    """
    components = string.split('.')
    class_name = components[-1]
    module_name = '.'.join(components[:-1])
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    assert isinstance(cls, type)
    return cls


def _get_include_external_packages(user_options: UserOptions) -> Optional[bool]:
    """
    Get a boolean (or None) for the include_external_packages option in user_options.
    """
    try:
        include_external_packages_str = user_options.session_options['include_external_packages']
    except KeyError:
        return None
    # Cast the string to a boolean.
    return include_external_packages_str in ('True', 'true')
