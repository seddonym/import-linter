import importlib
from copy import copy, deepcopy
from typing import Any

from grimp import ImportGraph

from ..application import rendering
from ..domain.contract import Contract, InvalidContractOptions, registry
from . import output
from .app_config import settings
from .ports.reporting import Report
from .rendering import render_exception, render_report, format_duration
from .sentinels import NotSupplied
from .user_options import UserOptions

# Public functions
# ----------------

SUCCESS = True
FAILURE = False

from rich.console import Console
from rich.align import Align

console = Console(log_path=False, style="dim")


def lint_imports(
    config_filename: str | None = None,
    limit_to_contracts: tuple[str, ...] = (),
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
    is_debug_mode: bool = False,
    show_timings: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Analyse whether a Python package follows a set of contracts, and report on the results.

    This function attempts to handle and report all exceptions, too.

    Args:
        config_filename:    the filename to use to parse user options.
        limit_to_contracts: if supplied, only lint the contracts with the supplied ids.
        cache_dir:          the directory to use for caching. Pass None to disable caching.
        is_debug_mode:      whether debugging should be turned on. In debug mode, exceptions are
                            not swallowed at the top level, so the stack trace can be seen.
        show_timings:       whether to show the times taken to build the graph and to check
                            each contract.
        verbose:            if True, noisily output progress as it goes along.

    Returns:
        True if the linting passed, False if it didn't.
    """
    heading = Align(
        """
╔══╗─────────▶╔╗ ╔╗      ╔╗
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╬══╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║║ ═╣╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╣ ═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩══╩╝
  │   ║║◀───────────────┘                
  └──▶╚╝
    """,
        align="left",
    )

    console.print(heading, style="medium_orchid")

    from time import sleep

    with console.status(":brick: Building graph...", spinner="growVertical") as status:
        console.log("Found cache in .import_linter_cache/")
        sleep(1)
        console.log("Analyzed 38 files, 80 dependencies.")
        status.update(status="[bold blue] Checking contracts", spinner="bounce")
        console.log("[green][italic]Sample contract three[/italic] KEPT")
        sleep(0.3)
        console.log("[red][italic]Sample contract two[/italic] BROKEN")
        sleep(0.2)
        console.log("[green][italic]Sample contract three[/italic] KEPT")
        sleep(0.1)
        console.log("[bold] :checkered_flag: Check complete.")

        # for i in track(range(5), description="[medium_orchid] :brick: Building graph..."):
        #     time.sleep(0.1)  # Simulate work being done

        # contracts = ["Contract one", "Contract two", "Contract three"]
        # with Progress() as progress:
        #     tasks = []
        #     for contract in contracts:
        #         tasks.append(
        #             progress.add_task(
        #                 f"[medium_orchid] :face_with_monocle: Checking [italic]{contract}[/italic]...",
        #                 total=10,
        #             )
        #         )
        #
        # task1 = progress.add_task("[red]Linting...", total=1000)
        # task2 = progress.add_task("[green]Processing...", total=1000)
        # task3 = progress.add_task("[cyan]Cooking...", total=1000)

        # while not progress.finished:
        #     for task in tasks:
        #         for _ in range(10):
        #             progress.update(task, advance=1)
        #             time.sleep(0.2)

    # output.print_heading("Import Linter", output.HEADING_LEVEL_ONE)
    output.verbose_print(verbose, "Verbose mode.")
    try:
        user_options = read_user_options(config_filename=config_filename)
        _register_contract_types(user_options)
        report = create_report(user_options, limit_to_contracts, cache_dir, show_timings, verbose)
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


def read_user_options(config_filename: str | None = None) -> UserOptions:
    """
    Return the UserOptions object from the supplied config file.

    If no filename is supplied, look in the default location
    (see importlinter.cli.lint_imports).

    Raises:
        FileNotFoundError if no configuration file could be found.
    """
    readers = settings.USER_OPTION_READERS.values()
    if config_filename:
        if config_filename.endswith(".toml"):
            readers = [settings.USER_OPTION_READERS["toml"]]
        else:
            readers = [settings.USER_OPTION_READERS["ini"]]

    for reader in readers:
        options = reader.read_options(config_filename=config_filename)
        if options:
            normalized_options = _normalize_user_options(options)
            return normalized_options
    raise FileNotFoundError("Could not read any configuration.")


def create_report(
    user_options: UserOptions,
    limit_to_contracts: tuple[str, ...] = tuple(),
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
    show_timings: bool = False,
    verbose: bool = False,
) -> Report:
    """
    Analyse whether a Python package follows a set of contracts, returning a report on the results.

    Raises:
        InvalidUserOptions: if the report could not be run due to invalid user configuration,
                            such as a module that could not be imported.
    """
    include_external_packages = _get_include_external_packages(user_options)
    exclude_type_checking_imports = _get_exclude_type_checking_imports(user_options)
    from rich.status import Status

    status = Status("Building import graph...")
    status.start()
    # print(status)
    with settings.TIMER as timer:
        graph = _build_graph(
            root_package_names=user_options.session_options["root_packages"],
            cache_dir=cache_dir,
            include_external_packages=include_external_packages,
            exclude_type_checking_imports=exclude_type_checking_imports,
            verbose=verbose,
        )
        # import time
        #
        # time.sleep(1)
    status.stop()

    # while not progress.finished:
    #     progress.update(task1, advance=0.5)
    #     progress.update(task2, advance=0.3)
    #     progress.update(task3, advance=0.9)
    #     time.sleep(0.02)
    graph_building_duration = timer.duration_in_ms

    output.verbose_print(verbose, f"Built graph in {format_duration(graph_building_duration)}.")

    return _build_report(
        graph=graph,
        graph_building_duration=graph_building_duration,
        user_options=user_options,
        limit_to_contracts=limit_to_contracts,
        show_timings=show_timings,
        verbose=verbose,
    )


# Private functions
# -----------------


def _normalize_user_options(user_options: UserOptions) -> UserOptions:
    normalized_options = copy(user_options)
    if "root_packages" not in normalized_options.session_options:
        normalized_options.session_options["root_packages"] = [
            normalized_options.session_options["root_package"]
        ]
    if "root_package" in normalized_options.session_options:
        del normalized_options.session_options["root_package"]
    return normalized_options


def _build_graph(
    root_package_names: list[str],
    include_external_packages: bool | None,
    exclude_type_checking_imports: bool,
    verbose: bool,
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
) -> ImportGraph:
    if cache_dir == NotSupplied:
        cache_dir = settings.DEFAULT_CACHE_DIR

    if cache_dir:
        output.verbose_print(verbose, f"Building import graph (cache directory is {cache_dir})...")
    else:
        output.verbose_print(verbose, "Building import graph (with caching disabled)...")

    return settings.GRAPH_BUILDER.build(
        root_package_names=root_package_names,
        include_external_packages=include_external_packages,
        exclude_type_checking_imports=exclude_type_checking_imports,
        cache_dir=cache_dir,
    )


def _build_report(
    graph: ImportGraph,
    graph_building_duration: int,
    user_options: UserOptions,
    limit_to_contracts: tuple[str, ...],
    show_timings: bool,
    verbose: bool,
) -> Report:
    report = Report(
        graph=graph,
        show_timings=show_timings,
        graph_building_duration=graph_building_duration,
    )
    contracts_options = _filter_contract_options(
        user_options.contracts_options, limit_to_contracts
    )
    for contract_options in contracts_options:
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

        output.verbose_print(verbose, f"Checking {contract.name}...")
        with settings.TIMER as timer:
            # Make a copy so that contracts can mutate the graph without affecting
            # other contract checks.
            copy_of_graph = deepcopy(graph)
            check = contract.check(copy_of_graph, verbose=verbose)
        duration_ms = timer.duration_in_ms
        report.add_contract_check(contract, check, duration=duration_ms)
        if verbose:
            rendering.render_contract_result_line(contract, check, duration=duration_ms)

    output.verbose_print(verbose, newline=True)
    return report


def _filter_contract_options(
    contracts_options: list[dict[str, Any]], limit_to_contracts: tuple[str, ...]
) -> list[dict[str, Any]]:
    if limit_to_contracts:
        # Validate the supplied contract ids.
        registered_contract_ids = {option["id"] for option in contracts_options}
        missing_contract_ids = set(limit_to_contracts) - registered_contract_ids
        if missing_contract_ids:
            if len(missing_contract_ids) == 1:
                raise ValueError(
                    f"Could not find contract '{missing_contract_ids.pop()}'.\n\n"
                    "You asked to limit the check to that contract, but nothing exists "
                    "with that id."
                )
            else:
                raise ValueError(
                    "Could not find the following contract ids: "
                    f"{', '.join(sorted(missing_contract_ids))}.\n\n"
                    "You asked to limit the check to those contracts, but there are no "
                    "contracts with those ids."
                )
        else:
            return [o for o in contracts_options if o["id"] in limit_to_contracts]
    else:
        return contracts_options


def _register_contract_types(user_options: UserOptions) -> None:
    contract_types = _get_built_in_contract_types() + _get_plugin_contract_types(user_options)
    for name, contract_class in contract_types:
        registry.register(contract_class, name)


def _get_built_in_contract_types() -> list[tuple[str, type[Contract]]]:
    return list(
        map(
            _parse_contract_type_string,
            [
                "forbidden: importlinter.contracts.forbidden.ForbiddenContract",
                "layers: importlinter.contracts.layers.LayersContract",
                "independence: importlinter.contracts.independence.IndependenceContract",
                "protected: importlinter.contracts.protected.ProtectedContract",
                "acyclic_siblings: importlinter.contracts.acyclic_siblings.AcyclicSiblingsContract",
            ],
        )
    )


def _get_plugin_contract_types(
    user_options: UserOptions,
) -> list[tuple[str, type[Contract]]]:
    contract_types = []
    if "contract_types" in user_options.session_options:
        for contract_type_string in user_options.session_options["contract_types"]:
            contract_types.append(_parse_contract_type_string(contract_type_string))
    return contract_types


def _parse_contract_type_string(string) -> tuple[str, type[Contract]]:
    components = string.split(": ")
    assert len(components) == 2
    name, contract_class_string = components
    contract_class = _string_to_class(contract_class_string)
    if not issubclass(contract_class, Contract):
        raise TypeError(f"{contract_class} is not a subclass of Contract.")
    return name, contract_class


def _string_to_class(string: str) -> type:
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


def _get_include_external_packages(user_options: UserOptions) -> bool | None:
    """
    Get a boolean (or None) for the include_external_packages option in user_options.
    """
    try:
        include_external_packages_str = user_options.session_options["include_external_packages"]
    except KeyError:
        return None
    # Cast the string to a boolean.
    return include_external_packages_str in ("True", "true")


def _get_exclude_type_checking_imports(user_options: UserOptions) -> bool:
    """
    Get a boolean for the exclude_type_checking_imports option in user_options.
    """
    try:
        exclude_type_checking_imports_str = user_options.session_options[
            "exclude_type_checking_imports"
        ]
    except KeyError:
        return False
    # Cast the string to a boolean.
    return exclude_type_checking_imports_str in ("True", "true")


def _get_show_timings(user_options: UserOptions) -> bool:
    """
    Get a boolean (or None) for the show_timings option in user_options.
    """
    try:
        show_timings_str = user_options.session_options["show_timings"]
    except KeyError:
        return False
    # Cast the string to a boolean.
    return show_timings_str in ("True", "true")
