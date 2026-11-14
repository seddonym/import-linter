import importlib
import importlib.util
import itertools
import os
from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass
from copy import copy, deepcopy
from typing import Any
import contextlib
from grimp import ImportGraph
from rich.live import Live
from rich.progress import (
    Progress,
    BarColumn,
    MofNCompleteColumn,
    TextColumn,
)

from ..application import rendering
from ..domain.contract import Contract, InvalidContractOptions, registry
from .output import console
from . import output
from .app_config import settings
from .ports.reporting import Report
from .rendering import render_exception, render_report, format_duration
from ..domain.dotfile import DotGraph, Edge, EdgeArrowhead, EdgeStyle
from .sentinels import NotSupplied
from .user_options import InvalidUserOptions, UserOptions

# Public functions
# ----------------

SUCCESS = True
FAILURE = False


@dataclass(frozen=True)
class ConfigSource:
    """
    The user options read from a single configuration file.

    The filename is None if the file was found using the default search strategy.
    """

    filename: str | None
    user_options: UserOptions


def lint_imports(
    config_filename: str | None = None,
    limit_to_contracts: tuple[str, ...] = (),
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
    is_debug_mode: bool = False,
    show_timings: bool = False,
    no_logo: bool = False,
    verbose: bool = False,
    config_filenames: Sequence[str] = (),
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
        no_logo:            if True, the logo is hidden at startup.
        verbose:            if True, noisily output progress as it goes along.
        config_filenames:   further config files to check in the same run. Each file is read
                            independently, and an import graph is only built once for each
                            distinct graph configuration. If config_filename is also supplied,
                            it is treated as the first file.

    Returns:
        True if the linting passed, False if it didn't.
    """
    if not no_logo:
        rendering.print_title()

    output.verbose_print(verbose, "Verbose mode.")
    try:
        config_sources = _read_config_sources(config_filename, config_filenames)
        for config_source in config_sources:
            _validate_contracts_present(config_source)
        _register_built_in_contract_types()
        report = _create_report_from_sources(
            config_sources, limit_to_contracts, cache_dir, show_timings, verbose
        )
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
    if config_filename:
        raise FileNotFoundError(f"Could not read any configuration from {config_filename}.")
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
    return _create_report_from_sources(
        [ConfigSource(filename=None, user_options=user_options)],
        limit_to_contracts=limit_to_contracts,
        cache_dir=cache_dir,
        show_timings=show_timings,
        verbose=verbose,
    )


def build_dot_graph(
    grimp_graph: ImportGraph,
    module_name: str,
    show_import_totals: bool,
    show_module_counts: bool,
    show_lazy_imports: bool,
    show_cycle_breakers: bool,
    modules: Iterable[str] | None = None,
) -> DotGraph:
    """
    Build a DotGraph visualizing the architecture of the supplied module.

    Shows all the module's children, and the dependencies between them.

    Args:
        grimp_graph: An ImportGraph generated by Grimp.
        module_name: the module to visualize, e.g. 'mypackage.foo'.
        show_import_totals: whether to label the edges with the total amount of imports.
        show_module_counts: whether to display a module count below each node label.
        show_lazy_imports: whether to distinguish dependencies that are entirely lazy
            (every underlying import performed lazily) with an open arrowhead.
        show_cycle_breakers: whether to emphasize cycle-breaker edges.
        See https://grimp.readthedocs.io/en/stable/usage.html#ImportGraph.nominate_cycle_breakers
        modules: if supplied, the exact set of modules to draw as nodes (and between which to
            draw dependencies), instead of the children of module_name. This is used to draw a
            top-level overview of several root packages together.
    """
    if modules is None:
        children: Set[str] = grimp_graph.find_children(module_name)
        cycle_breaker_packages = [module_name]
        # Ordinary child graph: every node shares module_name as a parent, so nodes can be
        # identified by their relative name.
        relative = True
    else:
        children = set(modules)
        cycle_breaker_packages = list(children)
        # Top-level overview: the supplied modules may have different (or no) parents, so nodes
        # must be identified by their fully qualified name to avoid collisions.
        relative = False
    concentrate = not (show_import_totals or show_cycle_breakers)

    cycle_breakers: set[tuple[str, str]] | None = None
    if show_cycle_breakers:
        cycle_breakers = _get_coarse_grained_cycle_breakers(
            grimp_graph, cycle_breaker_packages, children
        )

    dot = DotGraph(title=module_name, concentrate=concentrate, relative=relative)
    for child in children:
        is_package = bool(grimp_graph.find_children(child))
        if is_package:
            rendered = DotGraph.render_module(child) if relative else child
            if show_module_counts:
                module_count = len(grimp_graph.find_descendants(child))
                dot.add_node(child, label=f"{rendered}/\\n{_format_module_count(module_count)}")
            else:
                dot.add_node(child, label=f"{rendered}/")
        else:
            dot.add_node(child)
    for upstream, downstream in itertools.permutations(children, r=2):
        edge = _build_dot_edge(
            grimp_graph,
            upstream,
            downstream,
            show_import_totals=show_import_totals,
            show_lazy_imports=show_lazy_imports,
            cycle_breakers=cycle_breakers,
        )
        if edge:
            dot.add_edge(edge)

    return dot


def _format_module_count(count: int) -> str:
    return f"{count:,}"


# Private functions
# -----------------


def _read_config_sources(
    config_filename: str | None, config_filenames: Sequence[str]
) -> list[ConfigSource]:
    filenames = ([config_filename] if config_filename else []) + list(config_filenames)
    if not filenames:
        return [ConfigSource(filename=None, user_options=read_user_options())]

    config_sources: list[ConfigSource] = []
    seen_paths: set[str] = set()
    for filename in filenames:
        # The same file may be passed twice, e.g. via overlapping shell globs.
        path = _absolute_path(filename)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        config_sources.append(
            ConfigSource(filename=filename, user_options=read_user_options(filename))
        )
    return config_sources


def _validate_contract_ids(config_source: ConfigSource) -> None:
    """
    Raise InvalidUserOptions if any contract id is invalid, or if two contracts in the same
    file share an id.

    Duplicate ids can only happen in toml files (in ini files, the id is the section name).
    """
    seen_ids: set[str] = set()
    for contract_options in config_source.user_options.contracts_options:
        contract_id = contract_options.get("id")
        if contract_id is None:
            continue
        location = (
            _display_filename(config_source.filename)
            if config_source.filename
            else "the configuration"
        )
        # We don't allow colons in contract ids, as they are used to qualify an id
        # with its filename (e.g. --contract=path/to/config.ini:foo). If we allowed them,
        # the qualifier could be ambiguous.
        if ":" in contract_id:
            raise InvalidUserOptions(
                f"The contract id '{contract_id}' in {location} is invalid. "
                "Contract ids may not contain a colon."
            )
        if contract_id in seen_ids:
            raise InvalidUserOptions(
                f"More than one contract in {location} has the id '{contract_id}'. "
                "Contract ids must be unique within a file."
            )
        seen_ids.add(contract_id)


def _register_built_in_contract_types() -> None:
    for name, contract_class in _get_built_in_contract_types():
        registry.register(contract_class, name)


def _create_report_from_sources(
    config_sources: list[ConfigSource],
    limit_to_contracts: tuple[str, ...] = tuple(),
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
    show_timings: bool = False,
    verbose: bool = False,
) -> Report:
    """
    Check the contracts from one or more config sources, returning a report on the results.

    A graph is built once for each distinct graph configuration (root packages,
    include_external_packages and exclude_type_checking_imports), and shared by every
    contract that needs it.
    """
    for config_source in config_sources:
        _validate_contract_ids(config_source)

    selected_contracts = _select_contracts(config_sources, limit_to_contracts)

    # Work out which graphs we need, in the order they're first needed, along with which
    # config sources share each one. If no contracts were selected, we still build the first
    # graph so the report can describe the codebase.
    sources_by_graph_key: dict[tuple, ConfigSource] = {}
    filenames_by_graph_key: dict[tuple, list[str]] = {}
    for config_source, _ in selected_contracts or [(config_sources[0], {})]:
        graph_key = _graph_key(config_source.user_options)
        sources_by_graph_key.setdefault(graph_key, config_source)
        display_name = _display_filename(config_source.filename)
        filenames = filenames_by_graph_key.setdefault(graph_key, [])
        if display_name not in filenames:
            filenames.append(display_name)

    graphs: dict[tuple, ImportGraph] = {}
    report: Report | None = None
    graph_count = len(sources_by_graph_key)
    for graph_index, (graph_key, config_source) in enumerate(
        sources_by_graph_key.items(), start=1
    ):
        user_options = config_source.user_options
        spinner_message = (
            f":brick: Building graph {graph_index}/{graph_count}..."
            if graph_count > 1
            else ":brick: Building graph..."
        )
        with _get_spinner(spinner_message, verbose):
            with settings.TIMER as timer:
                graph = _build_graph(
                    root_package_names=user_options.session_options["root_packages"],
                    cache_dir=cache_dir,
                    include_external_packages=_get_include_external_packages(user_options),
                    exclude_type_checking_imports=_get_exclude_type_checking_imports(user_options),
                    verbose=verbose,
                )
        graph_building_duration = timer.duration_in_ms
        output.verbose_print(
            verbose, f"Built graph in {format_duration(graph_building_duration)}."
        )
        graphs[graph_key] = graph
        filenames = filenames_by_graph_key[graph_key]
        if report is None:
            report = Report(
                graph=graph,
                show_timings=show_timings,
                graph_building_duration=graph_building_duration,
                filenames=filenames,
            )
        else:
            report.add_graph(
                graph, graph_building_duration=graph_building_duration, filenames=filenames
            )
    assert report is not None

    return _check_contracts(
        report,
        [
            (
                _get_contract_class(config_source, contract_options["type"]),
                contract_options,
                config_source.user_options.session_options,
                graphs[_graph_key(config_source.user_options)],
            )
            for config_source, contract_options in selected_contracts
        ],
        verbose=verbose,
    )


def _get_contract_class(config_source: ConfigSource, contract_type: str) -> type[Contract]:
    """
    Return the class for a contract type, as seen from the supplied config source.

    Custom contract types are scoped to the file that registers them: they are only
    available to contracts in that same file, and they may replace a built-in type
    without affecting contracts in other files.
    """
    own_contract_types = dict(_get_plugin_contract_types(config_source.user_options))
    if contract_type in own_contract_types:
        return own_contract_types[contract_type]
    return registry.get_contract_class(contract_type)


def _graph_key(user_options: UserOptions) -> tuple:
    """
    Return a hashable key identifying the graph needed for the supplied user options.

    Two sets of user options with the same key can share a graph.
    """
    return (
        tuple(sorted(user_options.session_options["root_packages"])),
        # An omitted include_external_packages (None) behaves the same as False.
        bool(_get_include_external_packages(user_options)),
        _get_exclude_type_checking_imports(user_options),
    )


def _absolute_path(filename: str) -> str:
    # Resolve symlinks, so that e.g. 'linked/../rules.ini' isn't mistaken for 'rules.ini'.
    return os.path.normcase(os.path.realpath(filename))


def _display_filename(filename: str | None) -> str:
    """
    Return the filename relative to the current working directory, if possible.
    """
    if filename is None:
        return ""
    try:
        # Resolve symlinks, so that two different files aren't displayed identically
        # just because a symlink makes their unresolved paths coincide.
        return os.path.relpath(os.path.realpath(filename))
    except ValueError:
        # On Windows, a path on a different drive can't be made relative.
        return filename


def _normalize_user_options(user_options: UserOptions) -> UserOptions:
    normalized_options = copy(user_options)
    if "root_packages" not in normalized_options.session_options:
        normalized_options.session_options["root_packages"] = [
            normalized_options.session_options["root_package"]
        ]
    if "root_package" in normalized_options.session_options:
        del normalized_options.session_options["root_package"]
    return normalized_options


def _get_spinner(message: str, verbose: bool) -> contextlib.AbstractContextManager:
    if verbose:
        # The output in verbose mode interferes with the spinner so we disable it.
        return contextlib.nullcontext()
    else:
        return console.status(message, spinner="point")


def _validate_contracts_present(config_source: ConfigSource) -> None:
    # Running the linter with nothing to check is almost always a configuration mistake
    # (e.g. [[tool.importlinter.contract]] instead of [[tool.importlinter.contracts]]),
    # so fail rather than report success.
    if not config_source.user_options.contracts_options:
        location = (
            _display_filename(config_source.filename)
            if config_source.filename
            else "the configuration"
        )
        raise InvalidUserOptions(
            f"No contracts found in {location}.\n\n"
            "Each contract goes in an 'importlinter:contract:<name>' section (INI files)\n"
            "or a 'tool.importlinter.contracts' array of tables (TOML files)."
        )


def _validate_root_package_names(root_package_names: list[str]) -> None:
    for name in root_package_names:
        spec = importlib.util.find_spec(name)
        if spec is not None and spec.submodule_search_locations is None:
            raise InvalidUserOptions(
                f"'{name}' is a module, not a package. "
                f"root_packages should only contain packages (directories with __init__.py), "
                f"not individual .py files."
            )


def _build_graph(
    root_package_names: list[str],
    include_external_packages: bool | None,
    exclude_type_checking_imports: bool,
    verbose: bool,
    cache_dir: str | None | type[NotSupplied] = NotSupplied,
) -> ImportGraph:
    _validate_root_package_names(root_package_names)

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


def _check_contracts(
    report: Report,
    contracts_to_check: list[tuple[type[Contract], dict[str, Any], dict[str, Any], ImportGraph]],
    verbose: bool,
) -> Report:
    """
    Check each contract against its graph, adding the results to the report.

    Args:
        contracts_to_check: (contract class, contract options, session options, graph) for
                            each contract.
    """
    contract_checking_progress = _get_contract_checking_progress(verbose)
    with contract_checking_progress:
        with Live(transient=True) as live:
            for (
                contract_class,
                contract_options,
                session_options,
                graph,
            ) in contract_checking_progress.track(contracts_to_check):
                try:
                    contract = contract_class(
                        name=contract_options["name"],
                        session_options=session_options,
                        contract_options=contract_options,
                    )
                except InvalidContractOptions as e:
                    report.add_invalid_contract_options(contract_options["name"], e)
                    return report

                live.update(f"[dim]Checking {contract_options['name']}")
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


def _get_contract_checking_progress(verbose: bool) -> Progress:
    return Progress(
        TextColumn(":face_with_monocle: Checking contracts"),
        BarColumn(),
        MofNCompleteColumn(),
        disable=verbose,
        transient=True,
    )


def _select_contracts(
    config_sources: list[ConfigSource], limit_to_contracts: tuple[str, ...]
) -> list[tuple[ConfigSource, dict[str, Any]]]:
    """
    Return the contracts to check, in configuration order, along with the source of each.

    Each item in limit_to_contracts is either a contract id, or a filename and contract id
    separated by a colon (e.g. 'path/to/config.ini:my-contract'). The second form is needed
    when the same id is used in more than one file.

    Raises:
        ValueError if a contract could not be found, or if an id is ambiguous.
    """
    all_contracts = [
        (source, contract_options)
        for source in config_sources
        for contract_options in source.user_options.contracts_options
    ]
    if not limit_to_contracts:
        return all_contracts

    # Contracts without an "id" key can't be matched by name (this happens with toml configs,
    # where ids are optional), so they fall through to the "Could not find contract" error
    # below instead of raising KeyError.
    missing_contract_ids: list[str] = []
    ambiguous: dict[str, list[tuple[ConfigSource, dict[str, Any]]]] = {}
    selected_indexes: set[int] = set()
    for requested in limit_to_contracts:
        matches = [
            index
            for index, (_, contract_options) in enumerate(all_contracts)
            if contract_options.get("id") == requested
        ]
        if not matches and ":" in requested:
            # Contract ids may not contain a colon, so the part after the last colon is
            # unambiguously the id, and everything before it is the filename.
            requested_filename, _, requested_id = requested.rpartition(":")
            matches = [
                index
                for index, (source, contract_options) in enumerate(all_contracts)
                if source.filename is not None
                and contract_options.get("id") == requested_id
                and _absolute_path(source.filename) == _absolute_path(requested_filename)
            ]

        if not matches:
            missing_contract_ids.append(requested)
        elif len(matches) > 1:
            ambiguous[requested] = [all_contracts[index] for index in matches]
        else:
            selected_indexes.add(matches[0])

    if missing_contract_ids:
        if len(missing_contract_ids) == 1:
            raise ValueError(
                f"Could not find contract '{missing_contract_ids[0]}'.\n\n"
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
    if ambiguous:
        raise ValueError(
            "\n\n".join(
                f"Multiple contracts found with the id '{contract_id}'. "
                "Try including the filename, e.g.\n\n"
                + "\n".join(
                    f"--contract={_display_filename(source.filename)}:{contract_id}"
                    for source, _ in matches_for_id
                    if source.filename is not None
                )
                for contract_id, matches_for_id in ambiguous.items()
            )
        )

    return [contract for index, contract in enumerate(all_contracts) if index in selected_indexes]


def _get_built_in_contract_types() -> list[tuple[str, type[Contract]]]:
    return list(
        map(
            _parse_contract_type_string,
            [
                "forbidden: importlinter.contracts.forbidden.ForbiddenContract",
                "layers: importlinter.contracts.layers.LayersContract",
                "independence: importlinter.contracts.independence.IndependenceContract",
                "protected: importlinter.contracts.protected.ProtectedContract",
                "private_modules: importlinter.contracts.private_modules.PrivateModulesContract",
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


# --- Dot graph generation ---


def _build_dot_edge(
    grimp_graph: ImportGraph,
    upstream: str,
    downstream: str,
    show_import_totals: bool,
    show_lazy_imports: bool,
    cycle_breakers: set[tuple[str, str]] | None,
) -> Edge | None:
    if not grimp_graph.direct_import_exists(
        importer=downstream, imported=upstream, as_packages=True
    ):
        return None

    if show_import_totals:
        number_of_imports = _count_imports_between_packages(
            grimp_graph, importer=downstream, imported=upstream
        )
        label = str(number_of_imports)
    else:
        label = ""

    is_lazy = show_lazy_imports and _is_lazy_dependency(
        grimp_graph, importer=downstream, imported=upstream
    )

    if cycle_breakers is not None and (downstream, upstream) in cycle_breakers:
        style = EdgeStyle.DASHED
    else:
        style = EdgeStyle.SOLID

    arrowhead = EdgeArrowhead.VEE if is_lazy else EdgeArrowhead.NORMAL

    return Edge(
        source=downstream, destination=upstream, label=label, style=style, arrowhead=arrowhead
    )


def _get_coarse_grained_cycle_breakers(
    grimp_graph: ImportGraph, packages: Iterable[str], children: Set[str]
) -> set[tuple[str, str]]:
    # In the form (importer, imported).
    coarse_grained_cycle_breakers: set[tuple[str, str]] = set()

    for fine_grained_cycle_breaker in grimp_graph.nominate_cycle_breakers(*packages):
        importer, imported = fine_grained_cycle_breaker
        importer_ancestor = _get_self_or_ancestor(candidate=importer, ancestors=children)
        imported_ancestor = _get_self_or_ancestor(candidate=imported, ancestors=children)

        if importer_ancestor and imported_ancestor:
            coarse_grained_cycle_breakers.add((importer_ancestor, imported_ancestor))

    return coarse_grained_cycle_breakers


def _get_self_or_ancestor(candidate: str, ancestors: Set[str]) -> str | None:
    for ancestor in ancestors:
        if candidate == ancestor or candidate.startswith(f"{ancestor}."):
            return ancestor
    return None


def _count_imports_between_packages(graph: ImportGraph, *, importer: str, imported: str) -> int:
    return len(_get_direct_imports_between_packages(graph, importer=importer, imported=imported))


def _is_lazy_dependency(graph: ImportGraph, *, importer: str, imported: str) -> bool:
    """
    Return whether every import underlying the dependency between two packages is lazy.

    A coarse-grained edge aggregates all the fine-grained imports between two packages. We only
    consider the dependency lazy if there is at least one import with known details and every such
    import is lazy, i.e. the packages have no import-time coupling whatsoever.
    """
    direct_imports = _get_direct_imports_between_packages(
        graph, importer=importer, imported=imported
    )

    found_lazy_import = False
    for fine_grained_importer, fine_grained_imported in direct_imports:
        for detail in graph.get_import_details(
            importer=fine_grained_importer, imported=fine_grained_imported
        ):
            if not detail["is_lazy"]:
                return False
            found_lazy_import = True

    return found_lazy_import


def _get_direct_imports_between_packages(
    graph: ImportGraph, *, importer: str, imported: str
) -> set[tuple[str, str]]:
    """
    Return the (importer, imported) module pairs for every direct import between two packages.

    Covers all four permutations of the packages and their descendants.
    """
    direct_imports: set[tuple[str, str]] = set()
    for import_expression in (
        f"{importer} -> {imported}",
        f"{importer} -> {imported}.**",
        f"{importer}.** -> {imported}",
        f"{importer}.** -> {imported}.**",
    ):
        for direct_import in graph.find_matching_direct_imports(
            import_expression=import_expression
        ):
            direct_imports.add((direct_import["importer"], direct_import["imported"]))
    return direct_imports
