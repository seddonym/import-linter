from collections.abc import Iterable
import grimp
from importlinter.application import contract_utils
from importlinter.domain import helpers, imports
from importlinter import Contract, ContractCheck, fields, output


class ProtectedContract(Contract):
    """
    Protected contracts check that one set of modules is only directly imported by another set of
     modules.
    Configuration options:
        - protected_modules:    The modules that must not be imported except by the list of
                                 importers, and by each other.
        - allowed_importers:    The only modules allowed to import the target modules.
        - ignore_imports:       A set of ImportExpressions. These imports will be ignored if the
                                 import would cause a contract to be broken, adding it to the set
                                 will cause the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                                 `ignore_imports` set is not found in the graph. Valid values are
                                 "none", "warn", "error". Default value is "error".
        - as_packages:          Whether to treat the protected and allowed modules as packages. If
                                 False, each of the modules passed in will be treated as a module
                                 rather than a package. Default behaviour is True (treat modules as
                                 packages).
    """

    type_name = "protected"

    protected_modules = fields.ListField(subfield=fields.ModuleExpressionField())
    allowed_importers = fields.ListField(subfield=fields.ModuleExpressionField())

    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(
        contract_utils.AlertLevel, default=contract_utils.AlertLevel.ERROR
    )

    as_packages = fields.BooleanField(required=False, default=True)

    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        protected_modules = self._resolve_module_expressions(
            self.protected_modules, graph  # type: ignore
        )
        allowed_modules = self._resolve_module_expressions(
            self.allowed_importers, graph  # type: ignore
        )

        # Target modules can import between themselves
        allowed_modules.update(protected_modules)

        illegal_imports: list[grimp.DetailedImport] = []
        for protected_module in protected_modules:
            illegal_importers = (
                graph.find_modules_that_directly_import(protected_module) - allowed_modules
            )
            for illegal_importer in illegal_importers:
                illegal_imports.append(
                    *graph.get_import_details(importer=illegal_importer, imported=protected_module)
                )

        return ContractCheck(
            kept=not bool(illegal_imports),
            warnings=warnings,
            metadata={"illegal_imports": illegal_imports},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        illegal_imports = check.metadata["illegal_imports"]

        output.print_error(
            "Following imports do not respect the protected policy:",
            bold=False,
        )

        for illegal_import in illegal_imports:
            importer, imported, line_number = (
                illegal_import["importer"],
                illegal_import["imported"],
                illegal_import["line_number"],
            )
            output.print_error(f"{importer} -> {imported} (l.{line_number})")
        output.new_line()

    def _resolve_module_expressions(
        self,
        root_modules: Iterable[imports.ModuleExpression],
        graph: grimp.ImportGraph,
    ) -> set[str]:
        resolved_modules = {
            module.name for module in helpers.module_expressions_to_modules(graph, root_modules)
        }
        if self.as_packages:
            resolved_modules.update(
                {
                    descendant
                    for module in resolved_modules
                    for descendant in graph.find_descendants(module)
                }
            )

        return resolved_modules
