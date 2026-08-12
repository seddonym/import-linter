from __future__ import annotations

from typing import cast

import grimp
from grimp import ImportGraph

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import module_expressions_to_modules

from ._common import (
    ModulePairChains,
    build_detailed_chain_from_route,
    render_chain_data,
)

_SubpackageChainData = ModulePairChains


class IndependenceContract(Contract):
    """
    Independence contracts check that a set of modules do not depend on each other.

    They do this by checking that there are no imports in any direction between the modules,
    even indirectly.

    Configuration options:

        - modules:        A set of Modules that should be independent of each other.
        - ignore_imports: A set of ImportExpressions. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                          `ignore_imports` set is not found in the graph. Valid values are
                          "none", "warn", "error". Default value is "error".
    """

    type_name = "independence"

    modules = fields.SetField(subfield=fields.ModuleExpressionField())
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        modules = list(module_expressions_to_modules(graph, self.modules))  # type: ignore
        self._check_all_modules_exist_in_graph(graph, modules)

        dependencies = graph.find_illegal_dependencies_for_layers(
            # A single layer consisting of siblings.
            layers=({module.name for module in modules},),
        )
        invalid_chains = self._build_invalid_chains(dependencies, graph)

        return ContractCheck(
            kept=not dependencies,
            warnings=warnings,
            metadata={"invalid_chains": invalid_chains},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in cast(list[_SubpackageChainData], check.metadata["invalid_chains"]):
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

    def _check_all_modules_exist_in_graph(self, graph: ImportGraph, modules) -> None:
        for module in modules:
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")

    def _build_invalid_chains(
        self, dependencies: set[grimp.PackageDependency], graph: grimp.ImportGraph
    ) -> list[_SubpackageChainData]:
        return [
            {
                "upstream_module": dependency.imported,
                "downstream_module": dependency.importer,
                "chains": [build_detailed_chain_from_route(c, graph) for c in dependency.routes],
            }
            for dependency in dependencies
        ]
