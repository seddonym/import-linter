from __future__ import annotations

from grimp import ImportGraph

from importlinter.application import contract_utils, output
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck


class StandaloneContract(Contract):
    """
    Standalone contracts check that a set of modules are standalone, that is not importing
    or imported by any other modules in the graph.

    Configuration options:

        - modules:        A list of Modules that should be standalone.
        - ignore_imports: A set of ImportExpressions. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
    """

    type_name = "standalone"

    modules = fields.ListField(subfield=fields.ModuleField())
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting="none",  # type: ignore
        )

        self._check_all_modules_exist_in_graph(graph)

        violations = {}
        for module in self.modules:  # type: ignore
            imports = graph.find_modules_directly_imported_by(module.name)
            imported_by = graph.find_modules_that_directly_import(module.name)
            if imported_by or imports:
                violations[module.name] = [
                    (module.name, import_expression) for import_expression in imported_by
                ] + [(import_expression, module.name) for import_expression in imports]

        kept = all(len(violation) == 0 for violation in violations.values())
        return ContractCheck(
            kept=kept,
            warnings=warnings,
            metadata={"violations": violations},
        )

    def render_broken_contract(self, check: "ContractCheck") -> None:
        for module_name, connections in check.metadata["violations"].items():
            output.print(f"{module_name} must be standalone:")
            output.new_line()
            for upstream, downstream in connections:
                output.print_error(f"- {downstream} is not allowed to import {upstream}")
            output.new_line()

    def _check_all_modules_exist_in_graph(self, graph: ImportGraph) -> None:
        for module in self.modules:  # type: ignore
            if module.name not in graph.modules:
                raise ValueError(f"Module '{module.name}' does not exist.")
