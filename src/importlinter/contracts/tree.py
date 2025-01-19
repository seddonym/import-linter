from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
import networkx as nx  # type: ignore[import-untyped]
from importlinter.application import output
from importlinter.domain import fields


class TreeContract(Contract):
    """
    A contract that checks whether the dependency graph of modules forms a tree structure.

    This contract verifies that the directed graph of module imports does not contain any cycles.
    A cycle in the graph implies that there is a circular dependency between modules, which
    violates the tree structure requirement.

    The `check` method constructs a directed graph using NetworkX, where nodes represent modules
    and edges represent import relationships. It then uses NetworkX's `simple_cycles` function
    to detect any cycles in the graph.

    Configuration options:
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True. (Optional.)
    """

    type_name = "tree"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)

    _CYCLES_METADATA_KEY = "cycles"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        nx_graph = nx.DiGraph()

        for importer_module in graph.modules:
            importer_module_family = [importer_module] + (
                self._get_module_ancestors(module=importer_module)
                if self._consider_package_dependencies
                else []
            )
            imported_modules = graph.find_modules_directly_imported_by(module=importer_module)

            for importer_module_family_member in importer_module_family:
                nx_graph.add_node(node_for_adding=importer_module_family_member)

                for imported_module in imported_modules:
                    imported_module_family = [imported_module] + (
                        self._get_module_ancestors(module=imported_module)
                        if self._consider_package_dependencies
                        else []
                    )

                    for imported_module_family_member in imported_module_family:
                        if importer_module_family_member == imported_module_family_member:
                            continue

                        if not nx_graph.has_node(n=imported_module_family_member):
                            nx_graph.add_node(node_for_adding=imported_module_family_member)

                        nx_graph.add_edge(
                            u_of_edge=importer_module_family_member,
                            v_of_edge=imported_module_family_member,
                        )

        cycles = list(nx.simple_cycles(G=nx_graph))
        return ContractCheck(kept=len(cycles) == 0, metadata={self._CYCLES_METADATA_KEY: cycles})

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @staticmethod
    def _get_module_ancestors(module: str) -> list[str]:
        module_ancestors = []
        module_split = module.split(".")
        del module_split[-1]

        while module_split:
            module_ancestors.append(".".join(module_split))
            del module_split[-1]

        return module_ancestors

    def render_broken_contract(self, check: ContractCheck) -> None:
        for cycle in check.metadata.get(self._CYCLES_METADATA_KEY, []):
            output.print_error(text=f"Cycle found: {cycle}")
            output.new_line()
