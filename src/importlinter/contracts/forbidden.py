from __future__ import annotations

from typing import cast
from collections.abc import Iterable

from grimp import ImportGraph

from importlinter.application import contract_utils, output
from importlinter.application import rendering
from importlinter.application.contract_utils import AlertLevel
from importlinter.configuration import settings
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import module_expressions_to_modules
from importlinter.domain.imports import Module

from ._common import format_line_numbers


class ForbiddenContract(Contract):
    """
    Forbidden contracts check that one set of modules are not imported by another set of modules.
    Indirect imports will also be checked.

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
        is_kept = True
        invalid_chains = []

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

        def sort_key(module):
            return module.name

        for source_module in sorted(source_modules, key=sort_key):
            for forbidden_module in sorted(forbidden_modules_in_graph, key=sort_key):
                output.verbose_print(
                    verbose,
                    f"Searching for import chains from {source_module} to {forbidden_module}...",
                )
                with settings.TIMER as timer:
                    subpackage_chain_data = {
                        "upstream_module": forbidden_module.name,
                        "downstream_module": source_module.name,
                        "chains": [],
                    }

                    if str(self.allow_indirect_imports).lower() == "true":
                        chains = self._get_direct_chains(
                            source_module,
                            forbidden_module,
                            graph,
                            self.as_packages,  # type:ignore
                        )
                    else:
                        chains = graph.find_shortest_chains(
                            importer=source_module.name,
                            imported=forbidden_module.name,
                            as_packages=self.as_packages,  # type:ignore
                        )
                    if chains:
                        is_kept = False
                        for chain in sorted(chains):
                            chain_data = []
                            for importer, imported in [
                                (chain[i], chain[i + 1]) for i in range(len(chain) - 1)
                            ]:
                                import_details = graph.get_import_details(
                                    importer=importer, imported=imported
                                )
                                line_numbers = tuple(j["line_number"] for j in import_details)
                                chain_data.append(
                                    {
                                        "importer": importer,
                                        "imported": imported,
                                        "line_numbers": line_numbers,
                                    }
                                )
                            subpackage_chain_data["chains"].append(chain_data)  # type: ignore
                if subpackage_chain_data["chains"]:
                    invalid_chains.append(subpackage_chain_data)
                if verbose:
                    chain_count = len(subpackage_chain_data["chains"])
                    pluralized = "s" if chain_count != 1 else ""
                    duration = rendering.format_duration(timer.duration_in_ms)
                    output.print(
                        f"Found {chain_count} illegal chain{pluralized} in {duration}.",
                    )

        # Sorting by upstream and downstream module ensures that the output is deterministic
        # and that the same upstream and downstream modules are always adjacent in the output.
        def chain_sort_key(chain_data):
            return (chain_data["upstream_module"], chain_data["downstream_module"])

        return ContractCheck(
            kept=is_kept,
            warnings=warnings,
            metadata={"invalid_chains": sorted(invalid_chains, key=chain_sort_key)},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        count = 0
        for chains_data in check.metadata["invalid_chains"]:
            downstream, upstream = (
                chains_data["downstream_module"],
                chains_data["upstream_module"],
            )
            output.print_error(f"{downstream} is not allowed to import {upstream}:")
            output.new_line()
            count += len(chains_data["chains"])
            for chain in chains_data["chains"]:
                first_line = True
                for direct_import in chain:
                    importer, imported = (
                        direct_import["importer"],
                        direct_import["imported"],
                    )
                    line_numbers = format_line_numbers(direct_import["line_numbers"])
                    import_string = f"{importer} -> {imported} ({line_numbers})"
                    if first_line:
                        output.print_error(f"-   {import_string}", bold=False)
                        first_line = False
                    else:
                        output.indent_cursor()
                        output.print_error(import_string, bold=False)
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
        chains: set[tuple[str, ...]] = set()
        source_modules = (
            self._get_all_modules_in_package(source_package, graph)
            if as_packages
            else {source_package}
        )
        forbidden_modules = (
            self._get_all_modules_in_package(forbidden_package, graph)
            if as_packages
            else {forbidden_package}
        )
        for source_module in source_modules:
            imported_module_names = graph.find_modules_directly_imported_by(source_module.name)
            for imported_module_name in imported_module_names:
                imported_module = Module(imported_module_name)
                if imported_module in forbidden_modules:
                    chains.add((source_module.name, imported_module.name))
        return chains

    def _get_all_modules_in_package(self, module: Module, graph: ImportGraph) -> set[Module]:
        """
        Return all the modules in the supplied module, including itself.

        If the module is squashed, it will be treated as a single module.
        """
        importer_modules = {module}
        if not graph.is_module_squashed(module.name):
            importer_modules |= {Module(m) for m in graph.find_descendants(module.name)}
        return importer_modules
