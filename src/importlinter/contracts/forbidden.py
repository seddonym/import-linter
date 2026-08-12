from __future__ import annotations

from operator import attrgetter
from typing import cast
from collections.abc import Iterable, Sequence

import grimp
from grimp import ImportGraph

from importlinter.application import contract_utils, output
from importlinter.application import rendering
from importlinter.application.contract_utils import AlertLevel
from importlinter.configuration import settings
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import module_expressions_to_modules
from importlinter.domain.imports import Module

from ._common import (
    DetailedChain,
    ModulePairChains,
    build_detailed_chain_from_module_names,
    build_detailed_chain_from_route,
    render_chain_data,
)


def _chain_sort_key(chain_data: DetailedChain) -> tuple:
    """
    Return a sort key that orders chains by the modules they pass through.

    Shorter chains sort first, so the most direct routes are reported first.
    """
    links = chain_data["chain"]
    return (len(links), tuple((link["importer"], link["imported"]) for link in links))


def _ancestor_names(module_name: str) -> set[str]:
    """
    Return the names of the module's ancestor packages, not including the module itself.
    """
    components = module_name.split(".")
    return {".".join(components[:index]) for index in range(1, len(components))}


def _any_modules_overlap(
    source_modules: Sequence[Module], forbidden_modules: Sequence[Module]
) -> bool:
    """
    Return whether any source module overlaps with any forbidden module, treated as packages.

    Comparing every pair would be O(N * M); because one module can only contain another if it is
    one of its ancestors, looking the ancestors up in a set is O((N + M) * depth) instead. This
    runs before every batched search, so the difference is worth having.
    """
    source_names = {module.name for module in source_modules}
    forbidden_names = {module.name for module in forbidden_modules}
    if source_names & forbidden_names:
        return True
    return any(
        _ancestor_names(name) & other_names
        for names, other_names in (
            (source_names, forbidden_names),
            (forbidden_names, source_names),
        )
        for name in names
    )


def _modules_overlap(
    source_module: Module, forbidden_module: Module, *, as_packages: bool
) -> bool:
    """
    Return whether the source and forbidden modules overlap: either they are the same module, or,
    when treated as packages, one contains the other.

    Overlapping pairs do not describe a forbiddable import and are skipped by the contract. See the
    forbidden contract documentation for details.
    """
    if source_module == forbidden_module:
        return True
    if as_packages:
        return source_module.is_in_package(forbidden_module) or forbidden_module.is_in_package(
            source_module
        )
    return False


class ForbiddenContract(Contract):
    """
    Forbidden contracts check that one set of modules are not imported by another set of modules.
    Indirect imports will also be checked.

    Where the source and forbidden modules overlap (the same module is in both, or one is a
    subpackage containing the other), the source module is not forbidden from importing the
    forbidden module; such pairs are skipped. This allows a wildcard such as ``mypackage.*`` to be
    used as a forbidden module even when a source module is one of the modules it matches. See the
    documentation for details.

    Configuration options:
        - source_modules:    A set of Modules that should not import the forbidden modules.
        - forbidden_modules: A set of Modules that should not be imported by the source modules.
        - ignore_imports:    A set of ImportExpressions. These imports will be ignored if the import
                             would cause a contract to be broken, adding it to the set will cause
                             the contract be kept instead. (Optional.)
        - allow_indirect_imports:  Whether to allow indirect imports to forbidden modules.
                             "True" or "true" will be treated as True. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                             `ignore_imports` set is not found in the graph. Valid values are
                             "none", "warn", "error". Default value is "error".
        - as_packages:       Whether to treat the source and forbidden modules as packages. If
                             False, each of the modules passed in will be treated as a module
                             rather than a package. Default behaviour is True (treat modules as
                             packages).
    """

    type_name = "forbidden"

    source_modules = fields.SetField(subfield=fields.ModuleExpressionField())
    forbidden_modules = fields.SetField(subfield=fields.ModuleExpressionField())
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    allow_indirect_imports = fields.BooleanField(required=False, default=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)
    as_packages = fields.BooleanField(required=False, default=True)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        source_modules = list(
            module_expressions_to_modules(
                graph,
                self.source_modules,  # type: ignore
            )
        )
        forbidden_modules = list(
            module_expressions_to_modules(
                graph,
                self.forbidden_modules,  # type: ignore
            )
        )

        self._check_all_modules_exist_in_graph(source_modules, graph)
        self._check_external_forbidden_modules(forbidden_modules)

        # We only need to check for illegal imports for forbidden modules that are in the graph.
        forbidden_modules_in_graph = [m for m in forbidden_modules if m.name in graph.modules]

        if self._can_use_batched_search(source_modules, forbidden_modules_in_graph):
            invalid_chains = self._find_invalid_chains_in_one_pass(
                graph, source_modules, forbidden_modules_in_graph, verbose
            )
        else:
            invalid_chains = self._find_invalid_chains_per_pair(
                graph, source_modules, forbidden_modules_in_graph, verbose
            )

        # Sorting by upstream and downstream module ensures that the output is deterministic
        # and that the same upstream and downstream modules are always adjacent in the output.
        return ContractCheck(
            kept=not invalid_chains,
            warnings=warnings,
            metadata={
                "invalid_chains": sorted(
                    invalid_chains,
                    key=lambda data: (data["upstream_module"], data["downstream_module"]),
                )
            },
        )

    def _can_use_batched_search(
        self, source_modules: Sequence[Module], forbidden_modules: Sequence[Module]
    ) -> bool:
        """
        Return whether this contract can be checked with a single graph search.

        The batched search (see _find_invalid_chains_in_one_pass) is dramatically faster, but it
        can't express every configuration, so the slower pair-by-pair search remains the fallback.
        """
        if not self.as_packages:
            # Grimp's layers analysis always treats modules as packages.
            return False
        if self.allow_indirect_imports:
            # This option only looks at direct imports, which the layers analysis can't express.
            return False
        # Grimp raises if any two modules in different layers overlap. The pair-by-pair search
        # skips such pairs individually, but a single overlapping pair would invalidate the
        # whole batch, so any overlap at all sends us down the fallback path.
        return not _any_modules_overlap(source_modules, forbidden_modules)

    def _find_invalid_chains_in_one_pass(
        self,
        graph: ImportGraph,
        source_modules: Sequence[Module],
        forbidden_modules: Sequence[Module],
        verbose: bool,
    ) -> list[ModulePairChains]:
        """
        Return the illegal chains, using a single graph search for every source/forbidden pair.

        A forbidden contract is equivalent to a two-layer architecture: grimp treats a lower
        layer importing a higher one as illegal, so putting the forbidden modules in the higher
        layer and the source modules in the lower layer makes exactly the source -> forbidden
        direction illegal. The layers are non-independent because source modules are free to
        import each other, as are forbidden modules; only the cross-layer direction matters.
        """
        output.verbose_print(
            verbose,
            f"Searching for import chains from {len(source_modules)} source module(s) "
            f"to {len(forbidden_modules)} forbidden module(s)...",
        )
        with settings.TIMER as timer:
            dependencies = graph.find_illegal_dependencies_for_layers(
                layers=(
                    grimp.Layer(*(m.name for m in forbidden_modules), independent=False),
                    grimp.Layer(*(m.name for m in source_modules), independent=False),
                ),
            )
            invalid_chains: list[ModulePairChains] = []
            for dependency in dependencies:
                # Routes come back as an unordered set, so sort the chains they produce to keep
                # the reported output stable between runs.
                chains: list[DetailedChain] = sorted(
                    (build_detailed_chain_from_route(route, graph) for route in dependency.routes),
                    key=_chain_sort_key,
                )
                invalid_chains.append(
                    {
                        "upstream_module": dependency.imported,
                        "downstream_module": dependency.importer,
                        "chains": chains,
                    }
                )
        self._print_chain_count(
            verbose, sum(len(data["chains"]) for data in invalid_chains), timer
        )
        return invalid_chains

    def _print_chain_count(self, verbose: bool, chain_count: int, timer) -> None:
        if not verbose:
            return
        pluralized = "s" if chain_count != 1 else ""
        duration = rendering.format_duration(timer.duration_in_ms)
        output.print(f"Found {chain_count} illegal chain{pluralized} in {duration}.")

    def _find_invalid_chains_per_pair(
        self,
        graph: ImportGraph,
        source_modules: Sequence[Module],
        forbidden_modules_in_graph: Sequence[Module],
        verbose: bool,
    ) -> list[ModulePairChains]:
        """
        Return the illegal chains, using a separate graph search for each source/forbidden pair.

        This is much slower than _find_invalid_chains_in_one_pass, but it supports the
        configurations that the batched search can't express.
        """
        invalid_chains: list[ModulePairChains] = []
        as_packages = cast(bool, self.as_packages)
        allow_indirect_imports = cast(bool, self.allow_indirect_imports)
        sorted_forbidden_modules = sorted(forbidden_modules_in_graph, key=attrgetter("name"))

        for source_module in sorted(source_modules, key=attrgetter("name")):
            for forbidden_module in sorted_forbidden_modules:
                if _modules_overlap(source_module, forbidden_module, as_packages=as_packages):
                    output.verbose_print(
                        verbose,
                        f"Skipping overlapping modules {source_module} and {forbidden_module}.",
                    )
                    continue
                output.verbose_print(
                    verbose,
                    f"Searching for import chains from {source_module} to {forbidden_module}...",
                )
                with settings.TIMER as timer:
                    if allow_indirect_imports:
                        chains = self._get_direct_chains(
                            source_module, forbidden_module, graph, as_packages
                        )
                    else:
                        chains = graph.find_shortest_chains(
                            importer=source_module.name,
                            imported=forbidden_module.name,
                            as_packages=as_packages,
                        )
                    detailed_chains = [
                        build_detailed_chain_from_module_names(chain, graph)
                        for chain in sorted(chains)
                    ]
                if detailed_chains:
                    invalid_chains.append(
                        {
                            "upstream_module": forbidden_module.name,
                            "downstream_module": source_module.name,
                            "chains": detailed_chains,
                        }
                    )
                self._print_chain_count(verbose, len(detailed_chains), timer)

        return invalid_chains

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in check.metadata["invalid_chains"]:
            downstream, upstream = (
                chains_data["downstream_module"],
                chains_data["upstream_module"],
            )
            output.print_error(f"{downstream} is not allowed to import {upstream}:")
            output.new_line()

            for chain_data in chains_data["chains"]:
                render_chain_data(chain_data)
                output.new_line()

            output.new_line()

    def _check_all_modules_exist_in_graph(
        self, modules: Iterable[Module], graph: ImportGraph
    ) -> None:
        for module in modules:
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")

    def _check_external_forbidden_modules(self, forbidden_modules) -> None:
        external_forbidden_modules = self._get_external_forbidden_modules(forbidden_modules)
        if external_forbidden_modules:
            if self._graph_was_built_with_externals():
                for module in external_forbidden_modules:
                    if module.root_package_name != module.name:
                        raise ValueError(
                            f"Invalid forbidden module {module}: "
                            "subpackages of external packages are not valid."
                        )
            else:
                raise ValueError(
                    "The top level configuration must have include_external_packages=True "
                    "when there are external forbidden modules."
                )

    def _get_external_forbidden_modules(self, forbidden_modules) -> set[Module]:
        root_packages = [Module(name) for name in self.session_options["root_packages"]]
        return {
            forbidden_module
            for forbidden_module in cast(list[Module], forbidden_modules)
            if not any(
                forbidden_module.is_in_package(root_package) for root_package in root_packages
            )
        }

    def _graph_was_built_with_externals(self) -> bool:
        return str(self.session_options.get("include_external_packages")).lower() == "true"

    def _get_direct_chains(
        self,
        source_package: Module,
        forbidden_package: Module,
        graph: ImportGraph,
        as_packages: bool,
    ) -> set[tuple[str, ...]]:
        """
        Return the direct imports from the source package to the forbidden package.

        The modules of each package are looked up and then walked, rather than matching import
        expressions, because expression matching scans every import in the graph: its cost grows
        with the size of the whole graph rather than with the size of the packages, and this runs
        once per source/forbidden pair.
        """
        source_modules = self._get_all_modules_in_package(source_package, graph, as_packages)
        forbidden_module_names = {
            module.name
            for module in self._get_all_modules_in_package(forbidden_package, graph, as_packages)
        }

        return {
            (source_module.name, imported_module_name)
            for source_module in source_modules
            for imported_module_name in graph.find_modules_directly_imported_by(source_module.name)
            if imported_module_name in forbidden_module_names
        }

    def _get_all_modules_in_package(
        self, module: Module, graph: ImportGraph, as_packages: bool
    ) -> set[Module]:
        """
        Return all the modules in the supplied module, including itself.

        If the module is squashed, or is not being treated as a package, it will be treated as a
        single module.
        """
        modules = {module}
        if as_packages and not graph.is_module_squashed(module.name):
            modules |= {Module(m) for m in graph.find_descendants(module.name)}
        return modules
