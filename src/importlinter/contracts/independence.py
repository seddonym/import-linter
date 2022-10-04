import copy
from itertools import permutations
from typing import List, cast

from typing_extensions import TypedDict

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.configuration import settings
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph

from ._common import (
    DetailedChain,
    Link,
    find_segments,
    render_chain_data,
    segments_to_collapsed_chains,
)


class _SubpackageChainData(TypedDict):
    upstream_module: str
    downstream_module: str
    chains: List[DetailedChain]


class IndependenceContract(Contract):
    """
    Independence contracts check that a set of modules do not depend on each other.

    They do this by checking that there are no imports in any direction between the modules,
    even indirectly.

    Configuration options:

        - modules:        A list of Modules that should be independent of each other.
        - ignore_imports: A set of ImportExpressions. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                          `ignore_imports` set is not found in the graph. Valid values are
                          "none", "warn", "error". Default value is "error".
    """

    type_name = "independence"

    modules = fields.ListField(subfield=fields.ModuleField())
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        invalid_chains: List[_SubpackageChainData] = []
        modules = cast(List[Module], self.modules)

        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        self._check_all_modules_exist_in_graph(graph)

        temp_graph = copy.deepcopy(graph)
        # First pass: direct imports.
        for subpackage_1, subpackage_2 in permutations(modules, r=2):  # type: ignore
            output.verbose_print(
                verbose,
                "Searching for direct imports from " f"{subpackage_1} to {subpackage_2}...",
            )
            with settings.TIMER as timer:
                direct_chains = self._pop_direct_imports(
                    importer_package=subpackage_1,
                    imported_package=subpackage_2,
                    graph=temp_graph,
                )
            if direct_chains:
                invalid_chains.append(
                    {
                        "upstream_module": subpackage_2.name,
                        "downstream_module": subpackage_1.name,
                        "chains": direct_chains,
                    }
                )
            if verbose:
                chain_count = len(direct_chains)
                pluralized = "s" if chain_count != 1 else ""
                output.print(
                    f"Found {chain_count} illegal chain{pluralized} "
                    f"in {timer.duration_in_s}s.",
                )

        # Second pass: indirect imports.
        self._squash_modules(graph=temp_graph, modules_to_squash=modules)
        for subpackage_1, subpackage_2 in permutations(modules, r=2):  # type: ignore
            output.verbose_print(
                verbose,
                "Searching for indirect imports from " f"{subpackage_1} to {subpackage_2}...",
            )
            with settings.TIMER as timer:
                other_independent_packages = [
                    m for m in modules if m not in (subpackage_1, subpackage_2)
                ]
                trimmed_graph = self._make_graph_with_packages_removed(
                    temp_graph, packages_to_remove=other_independent_packages
                )
                indirect_chains = self._get_indirect_collapsed_chains(
                    trimmed_graph=trimmed_graph,
                    reference_graph=graph,
                    importer_package=subpackage_1,
                    imported_package=subpackage_2,
                )
                if indirect_chains:
                    invalid_chains.append(
                        {
                            "upstream_module": subpackage_2.name,
                            "downstream_module": subpackage_1.name,
                            "chains": indirect_chains,
                        }
                    )
            if verbose:
                chain_count = len(indirect_chains)
                pluralized = "s" if chain_count != 1 else ""
                output.print(
                    f"Found {chain_count} illegal chain{pluralized} "
                    f"in {timer.duration_in_s}s.",
                )

        return ContractCheck(
            kept=not bool(invalid_chains),
            warnings=warnings,
            metadata={"invalid_chains": invalid_chains},
        )

    def render_broken_contract(self, check: "ContractCheck") -> None:
        for chains_data in cast(List[_SubpackageChainData], check.metadata["invalid_chains"]):
            downstream, upstream = (
                chains_data["downstream_module"],
                chains_data["upstream_module"],
            )
            output.print(f"{downstream} is not allowed to import {upstream}:")
            output.new_line()

            for chain_data in chains_data["chains"]:
                render_chain_data(chain_data)
                output.new_line()

            output.new_line()

    def _check_all_modules_exist_in_graph(self, graph: ImportGraph) -> None:
        for module in self.modules:  # type: ignore
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")

    def _squash_modules(self, graph: ImportGraph, modules_to_squash: List[Module]) -> None:
        for module in modules_to_squash:
            graph.squash_module(module.name)

    def _make_graph_with_packages_removed(
        self, graph: ImportGraph, packages_to_remove: List[Module]
    ) -> ImportGraph:
        """
        Assumes the packages are squashed.
        """
        new_graph = copy.deepcopy(graph)
        for package in packages_to_remove:
            new_graph.remove_module(package.name)
        return new_graph

    def _get_indirect_collapsed_chains(
        self,
        trimmed_graph: ImportGraph,
        reference_graph: ImportGraph,
        importer_package: Module,
        imported_package: Module,
    ) -> List[DetailedChain]:
        """
        Return chains from the importer to the imported package.

        Assumes the packages are both squashed.
        """
        segments = find_segments(
            trimmed_graph,
            reference_graph=reference_graph,
            importer=importer_package,
            imported=imported_package,
        )
        return segments_to_collapsed_chains(
            reference_graph, segments, importer=importer_package, imported=imported_package
        )

    def _pop_direct_imports(
        self,
        importer_package: Module,
        imported_package: Module,
        graph: ImportGraph,
    ) -> List[DetailedChain]:
        """
        Remove and return direct imports from the importer to the imported package.
        """
        direct_imports: List[DetailedChain] = []
        importer_modules = {importer_package.name} | graph.find_descendants(importer_package.name)
        imported_modules = {imported_package.name} | graph.find_descendants(imported_package.name)

        for importer_module in importer_modules:
            for imported_module in imported_modules:
                import_details = graph.get_import_details(
                    importer=importer_module, imported=imported_module
                )
                if import_details:
                    line_numbers = tuple(cast(int, i["line_number"]) for i in import_details)
                    direct_imports.append(
                        {
                            "chain": [
                                {
                                    "importer": cast(str, import_details[0]["importer"]),
                                    "imported": cast(str, import_details[0]["imported"]),
                                    "line_numbers": line_numbers,
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        }
                    )
                    graph.remove_import(importer=importer_module, imported=imported_module)

        return direct_imports

    def _build_subpackage_chain_data(
        self, upstream_module: Module, downstream_module: Module, graph: ImportGraph
    ) -> _SubpackageChainData:
        """
        Return any import chains from the upstream to downstream module.
        """
        subpackage_chain_data: _SubpackageChainData = {
            "upstream_module": upstream_module.name,
            "downstream_module": downstream_module.name,
            "chains": [],
        }
        assert isinstance(subpackage_chain_data["chains"], list)  # For type checker.
        chains = graph.find_shortest_chains(
            importer=downstream_module.name, imported=upstream_module.name
        )
        if chains:
            for chain in chains:
                chain_data: List[Link] = []
                for importer, imported in [
                    (chain[i], chain[i + 1]) for i in range(len(chain) - 1)
                ]:
                    import_details = graph.get_import_details(importer=importer, imported=imported)
                    line_numbers = tuple(cast(int, j["line_number"]) for j in import_details)
                    chain_data.append(
                        {
                            "importer": importer,
                            "imported": imported,
                            "line_numbers": line_numbers,
                        }
                    )
                detailed_chain: DetailedChain = {
                    "chain": chain_data,
                    "extra_firsts": [],
                    "extra_lasts": [],
                }
                subpackage_chain_data["chains"].append(detailed_chain)

        return subpackage_chain_data
