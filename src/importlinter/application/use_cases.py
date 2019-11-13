import importlib
from copy import copy, deepcopy
from typing import List, Optional, Tuple, Type

from ..domain.contract import Contract, InvalidContractOptions, registry
from ..domain.ports.graph import ImportGraph
from .app_config import settings
from .ports.reporting import Report
from .rendering import render_exception, render_report
from .user_options import UserOptions

# Public functions
# ----------------

SUCCESS = True
FAILURE = False


def lint_imports(config_filename: Optional[str] = None, is_debug_mode: bool = False) -> bool:
    """
    Analyse whether a Python package follows a set of contracts, and report on the results.

    This function attempts to handle and report all exceptions, too.

    Args:
        config_filename: the filename to use to parse user options.
        is_debug_mode:   whether debugging should be turned on. In debug mode, exceptions are
                         not swallowed at the top level, so the stack trace can be seen.

    Returns:
        True if the linting passed, False if it didn't.
    """
    try:
        user_options = _read_user_options(config_filename=config_filename)
        _register_contract_types(user_options)
        report = create_report(user_options)
    except Exception as e:
        if is_debug_mode:
            raise e
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
        root_package_names=user_options.session_options["root_packages"],
        include_external_packages=include_external_packages,
    )
    return _build_report(graph=graph, user_options=user_options)


# Private functions
# -----------------


def _read_user_options(config_filename: Optional[str] = None) -> UserOptions:
    for reader in settings.USER_OPTION_READERS:
        options = reader.read_options(config_filename=config_filename)
        if options:
            normalized_options = _normalize_user_options(options)
            return normalized_options
    raise RuntimeError("Could not read any configuration.")


def _normalize_user_options(user_options: UserOptions) -> UserOptions:
    normalized_options = copy(user_options)
    if "root_packages" not in normalized_options.session_options:
        normalized_options.session_options["root_packages"] = [
            normalized_options.session_options["root_package"]
        ]
    return normalized_options


def _build_graph(
    root_package_names: List[str], include_external_packages: Optional[bool]
) -> ImportGraph:
    return settings.GRAPH_BUILDER.build(
        root_package_names=root_package_names, include_external_packages=include_external_packages
    )


def _build_report(graph: ImportGraph, user_options: UserOptions) -> Report:
    report = Report(graph=graph)
    for contract_options in user_options.contracts_options:
        contract_class = registry.get_contract_class(contract_options["type"])
        try:
            contract = contract_class(
                name=contract_options["name"],
                session_options=user_options.session_options,
                contract_options=contract_options,
            )
        except InvalidContractOptions as e:
            report.add_invalid_contract_options(contract_options["name"], e)
            return report

        # Make a copy so that contracts can mutate the graph without affecting
        # other contract checks.
        copy_of_graph = deepcopy(graph)
        check = contract.check(copy_of_graph)
        report.add_contract_check(contract, check)
    return report


def _register_contract_types(user_options: UserOptions) -> None:
    contract_types = _get_built_in_contract_types() + _get_plugin_contract_types(user_options)
    for name, contract_class in contract_types:
        registry.register(contract_class, name)


def _get_built_in_contract_types() -> List[Tuple[str, Type[Contract]]]:
    return list(
        map(
            _parse_contract_type_string,
            [
                "forbidden: importlinter.contracts.forbidden.ForbiddenContract",
                "layers: importlinter.contracts.layers.LayersContract",
                "independence: importlinter.contracts.independence.IndependenceContract",
            ],
        )
    )


def _get_plugin_contract_types(user_options: UserOptions) -> List[Tuple[str, Type[Contract]]]:
    contract_types = []
    if "contract_types" in user_options.session_options:
        for contract_type_string in user_options.session_options["contract_types"]:
            contract_types.append(_parse_contract_type_string(contract_type_string))
    return contract_types


def _parse_contract_type_string(string) -> Tuple[str, Type[Contract]]:
    components = string.split(": ")
    assert len(components) == 2
    name, contract_class_string = components
    contract_class = _string_to_class(contract_class_string)
    if not issubclass(contract_class, Contract):
        raise TypeError(f"{contract_class} is not a subclass of Contract.")
    return name, contract_class


def _string_to_class(string: str) -> Type:
    """
    Parse a string into a Python class.

    Args:
        string: a fully qualified string of a class, e.g. 'mypackage.foo.MyClass'.

    Returns:
        The class.
    """
    components = string.split(".")
    class_name = components[-1]
    module_name = ".".join(components[:-1])
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    assert isinstance(cls, type)
    return cls


def _get_include_external_packages(user_options: UserOptions) -> Optional[bool]:
    """
    Get a boolean (or None) for the include_external_packages option in user_options.
    """
    try:
        include_external_packages_str = user_options.session_options["include_external_packages"]
    except KeyError:
        return None
    # Cast the string to a boolean.
    return include_external_packages_str in ("True", "true")
