import copy
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


class AcyclicContract(Contract):
    """
    A contract that checks whether the dependency graph of modules forms a directed acyclic graph (DAG) structure.

    This contract verifies that the directed graph of module imports does not contain any cycles.
    A cycle in the graph implies that there is a circular dependency between modules, which
    violates the tree structure requirement.

    Configuration options:
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True. (Optional.)
    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)

    _CYCLES_METADATA_KEY = "cycles"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        cycles: list[tuple[str, ...]] = []
        
        if self._consider_package_dependencies:
            graph = copy.deepcopy(graph)

            for importer_module in graph.modules:
                importer_module_family = [importer_module] + (
                    self._get_module_ancestors(module=importer_module)
                    if self._consider_package_dependencies
                    else []
                )

                # Add the importer module and its family members to the graph.
                for importer_module_family_member in importer_module_family:
                    graph.add_module(module=importer_module_family_member)

                imported_modules = graph.find_modules_directly_imported_by(module=importer_module)

                for imported_module in imported_modules:
                    imported_module_family = [imported_module] + (
                        self._get_module_ancestors(module=imported_module)
                        if self._consider_package_dependencies
                        else []
                    )

                    for imported_module_family_member in imported_module_family:

                        if imported_module_family_member not in graph.modules:
                            graph.add_module(imported_module_family_member)

                        for importer_module_family_member in importer_module_family:
                            # Ignore self-imports.
                            if imported_module_family_member == importer_module_family_member:
                                continue

                            graph.add_import(
                                importer=importer_module_family_member,
                                imported=imported_module_family_member
                            )

        for importer_module in graph.modules:
            cycle = graph.find_shortest_cycle(
                module=importer_module
            )

            if cycle:
                if verbose:
                    output.print_error(text=f"Cycle found in module '{importer_module}': {cycle}")

                cycles.append(cycle)

        contract_check = ContractCheck(kept=len(cycles) == 0, metadata={})
        AcyclicContract._set_cycles_in_metadata(check=contract_check, cycles=cycles)
        return contract_check

    def render_broken_contract(self, check: ContractCheck) -> None:
        for cycle in AcyclicContract._get_cycles_from_metadata(check=check):
            output.print_error(text=f"Cycle found: {cycle}")
            output.new_line()

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @staticmethod
    def _get_module_ancestors(module: str) -> list[str]:
        module_ancestors: list[str] = []
        module_split = module.split(".")
        del module_split[-1]

        while module_split:
            module_ancestors.append(".".join(module_split))
            del module_split[-1]

        return module_ancestors

    @staticmethod
    def _set_cycles_in_metadata(check: ContractCheck, cycles: list[tuple[str, ...]]) -> None:
        check.metadata[AcyclicContract._CYCLES_METADATA_KEY] = cycles

    @staticmethod
    def _get_cycles_from_metadata(check: ContractCheck) -> list[tuple[str, ...]]:
        return check.metadata.get(AcyclicContract._CYCLES_METADATA_KEY, [])
