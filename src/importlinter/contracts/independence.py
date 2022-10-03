from itertools import permutations
from typing import List, Tuple, cast, Optional

from typing_extensions import TypedDict

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.configuration import settings
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class _Link(TypedDict):
    importer: str
    imported: str
    line_numbers: Tuple[int, ...]


_Chain = List[_Link]


class _DetailedChain(TypedDict):
    chain: _Chain
    extra_firsts: List[_Link]
    extra_lasts: List[_Link]


class _SubpackageChainData(TypedDict):
    upstream_module: str
    downstream_module: str
    chains: List[_DetailedChain]


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
        invalid_chains = []

        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        self._check_all_modules_exist_in_graph(graph)

        for subpackage_1, subpackage_2 in permutations(self.modules, r=2):  # type: ignore
            output.verbose_print(
                verbose,
                "Searching for import chains from " f"{subpackage_1} to {subpackage_2}...",
            )
            with settings.TIMER as timer:
                subpackage_chain_data = self._build_subpackage_chain_data(
                    upstream_module=subpackage_2,
                    downstream_module=subpackage_1,
                    graph=graph,
                )
            if subpackage_chain_data["chains"]:
                invalid_chains.append(subpackage_chain_data)
            if verbose:
                chain_count = len(subpackage_chain_data["chains"])
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
        # count = 0
        # for chains_data in check.metadata["invalid_chains"]:
        #     downstream, upstream = (
        #         chains_data["downstream_module"],
        #         chains_data["upstream_module"],
        #     )
        #     output.print_error(f"{downstream} is not allowed to import {upstream}:")
        #     output.new_line()
        #     count += len(chains_data["chains"])
        #     for chain in chains_data["chains"]:
        #         first_line = True
        #         for direct_import in chain:
        #             importer, imported = (direct_import["importer"], direct_import["imported"])
        #             line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
        #             import_string = f"{importer} -> {imported} ({line_numbers})"
        #             if first_line:
        #                 output.print_error(f"-   {import_string}", bold=False)
        #                 first_line = False
        #             else:
        #                 output.indent_cursor()
        #                 output.print_error(import_string, bold=False)
        #         output.new_line()
        #
        #     output.new_line()

        for chains_data in cast(List[_SubpackageChainData], check.metadata["invalid_chains"]):
            downstream, upstream = (chains_data["downstream_module"], chains_data["upstream_module"])
            output.print(f"{downstream} is not allowed to import {upstream}:")
            output.new_line()

            for chain_data in chains_data["chains"]:
                self._render_chain_data(chain_data)
                output.new_line()

            output.new_line()

    def _render_chain_data(self, chain_data: _DetailedChain) -> None:
        main_chain = chain_data["chain"]
        self._render_direct_import(
            main_chain[0], extra_firsts=chain_data["extra_firsts"], first_line=True
        )

        for direct_import in main_chain[1:-1]:
            self._render_direct_import(direct_import)

        if len(main_chain) > 1:
            self._render_direct_import(main_chain[-1], extra_lasts=chain_data["extra_lasts"])

    def _render_direct_import(
        self,
        direct_import,
        first_line: bool = False,
        extra_firsts: Optional[List] = None,
        extra_lasts: Optional[List] = None,
    ) -> None:
        import_strings = []
        if extra_firsts:
            for position, source in enumerate([direct_import] + extra_firsts[:-1]):
                prefix = "& " if position > 0 else ""
                importer = source["importer"]
                line_numbers = ", ".join(f"l.{n}" for n in source["line_numbers"])
                import_strings.append(f"{prefix}{importer} ({line_numbers})")
            importer, imported = extra_firsts[-1]["importer"], extra_firsts[-1]["imported"]
            line_numbers = ", ".join(f"l.{n}" for n in extra_firsts[-1]["line_numbers"])
            import_strings.append(f"& {importer} -> {imported} ({line_numbers})")
        else:
            importer, imported = direct_import["importer"], direct_import["imported"]
            line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
            import_strings.append(f"{importer} -> {imported} ({line_numbers})")

        if extra_lasts:
            indent_string = (len(direct_import["importer"]) + 4) * " "
            for destination in extra_lasts:
                imported = destination["imported"]
                line_numbers = ", ".join(f"l.{n}" for n in destination["line_numbers"])
                import_strings.append(f"{indent_string}& {imported} ({line_numbers})")

        for position, import_string in enumerate(import_strings):
            if first_line and position == 0:
                output.print_error(f"- {import_string}", bold=False)
            else:
                output.print_error(f"  {import_string}", bold=False)

    def _check_all_modules_exist_in_graph(self, graph: ImportGraph) -> None:
        for module in self.modules:  # type: ignore
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")

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
                chain_data: List[_Link] = []
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
                detailed_chain: _DetailedChain = {
                    "chain": chain_data,
                    "extra_firsts": [],
                    "extra_lasts": [],
                }
                subpackage_chain_data["chains"].append(detailed_chain)

        return subpackage_chain_data
