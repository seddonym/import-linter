from itertools import permutations

from importlinter.application import output
from importlinter.domain import fields, helpers
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.ports.graph import ImportGraph


class IndependenceContract(Contract):
    """
    Independence contracts check that a set of modules do not depend on each other.

    They do this by checking that there are no imports in any direction between the modules,
    even indirectly.

    Configuration options:

        - modules:        A list of Modules that should be independent from each other.
        - ignore_imports: A set of DirectImports. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
    """

    type_name = "independence"

    modules = fields.ListField(subfield=fields.ModuleField())
    ignore_imports = fields.SetField(subfield=fields.DirectImportField(), required=False)

    def check(self, graph: ImportGraph) -> ContractCheck:
        is_kept = True
        invalid_chains = []

        helpers.pop_imports(
            graph, self.ignore_imports if self.ignore_imports else []  # type: ignore
        )

        self._check_all_modules_exist_in_graph(graph)

        for subpackage_1, subpackage_2 in permutations(self.modules, r=2):  # type: ignore
            subpackage_chain_data = {
                "upstream_module": subpackage_2.name,
                "downstream_module": subpackage_1.name,
                "chains": [],
            }
            assert isinstance(subpackage_chain_data["chains"], list)  # For type checker.
            chains = graph.find_shortest_chains(
                importer=subpackage_1.name, imported=subpackage_2.name
            )
            if chains:
                is_kept = False
                for chain in chains:
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
                subpackage_chain_data["chains"].append(chain_data)
            if subpackage_chain_data["chains"]:
                invalid_chains.append(subpackage_chain_data)

        return ContractCheck(kept=is_kept, metadata={"invalid_chains": invalid_chains})

    def render_broken_contract(self, check: "ContractCheck") -> None:
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
                    importer, imported = (direct_import["importer"], direct_import["imported"])
                    line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
                    import_string = f"{importer} -> {imported} ({line_numbers})"
                    if first_line:
                        output.print_error(f"-   {import_string}", bold=False)
                        first_line = False
                    else:
                        output.indent_cursor()
                        output.print_error(import_string, bold=False)
                output.new_line()

            output.new_line()

    def _check_all_modules_exist_in_graph(self, graph: ImportGraph) -> None:
        for module in self.modules:  # type: ignore
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")
