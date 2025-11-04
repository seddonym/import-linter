from dataclasses import dataclass
import grimp
from importlinter.application import contract_utils
from ._common import Link
from importlinter.domain import helpers, imports
from importlinter import Contract, ContractCheck, fields, output


class ProtectedContract(Contract):
    """
    Protected contracts check that one set of modules is only directly imported by another set of
    modules.

    Configuration options:
        - protected_modules:    The modules that must not be imported except by allowed_importers.
                                The modules that must not be imported except by the list of allowed
                                importers. If `as_packages` is True, descendants of a protected
                                module are also allowed to import each other.
        - allowed_importers:    The only modules allowed to import the protected modules.
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

        allowed_modules = {
            module.name
            for module in helpers.module_expressions_to_modules(
                graph=graph,
                expressions=self.allowed_importers,  # type: ignore
                as_packages=self.as_packages,  # type: ignore
            )
        }

        protected_modules_expressions: set[imports.ModuleExpression] = self.protected_modules  # type: ignore

        illegal_imports_metadata: list[BrokenContractMetadata] = []

        for protected_module_expression in protected_modules_expressions:
            top_level_protected_modules = {
                module.name
                for module in helpers.module_expression_to_modules(
                    graph=graph,
                    expression=protected_module_expression,
                    as_packages=False,
                )
            }

            for top_level_protected_module in sorted(top_level_protected_modules):
                broken_contract_metadata_object = BrokenContractMetadata(
                    top_level_protected_module,
                    [],
                    (
                        protected_module_expression.expression
                        if protected_module_expression.has_wildcard_expression()
                        else None
                    ),
                )

                protected_modules = {top_level_protected_module}
                if self.as_packages and not graph.is_module_squashed(top_level_protected_module):
                    protected_modules.update(graph.find_descendants(top_level_protected_module))

                for protected_module in sorted(protected_modules):
                    illegal_importers = (
                        graph.find_modules_that_directly_import(protected_module)
                        - allowed_modules
                        - protected_modules
                    )

                    for illegal_importer in sorted(illegal_importers):
                        import_details = graph.get_import_details(
                            importer=illegal_importer, imported=protected_module
                        )

                        broken_contract_metadata_object.illegal_links.append(
                            {
                                "importer": illegal_importer,
                                "imported": protected_module,
                                "line_numbers": tuple(
                                    detail["line_number"] for detail in import_details
                                ),
                            }
                        )

                if broken_contract_metadata_object.illegal_links:
                    illegal_imports_metadata.append(broken_contract_metadata_object)

        return ContractCheck(
            kept=not bool(illegal_imports_metadata),
            warnings=warnings,
            metadata={"illegal_imports": illegal_imports_metadata},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        illegal_imports_metadata: list[BrokenContractMetadata] = check.metadata["illegal_imports"]

        for broken_contract_metadata in illegal_imports_metadata:
            expression_warning = ""
            if broken_contract_metadata.original_expression:
                expression_warning = (
                    f"\n(via {broken_contract_metadata.original_expression} expression)"
                )

            output.print_error(
                f"Illegal imports of protected package {broken_contract_metadata.top_level_module}"
                f"{expression_warning}:",
                bold=False,
            )

            output.new_line()

            for illegal_import in broken_contract_metadata.illegal_links:
                importer, imported, line_numbers = (
                    illegal_import["importer"],
                    illegal_import["imported"],
                    illegal_import["line_numbers"],
                )
                output.print_error(
                    f"- {importer} -> {imported} (l.{', '.join(map(str, line_numbers))})",
                    bold=False,
                )
                output.new_line()
        output.new_line()


@dataclass
class BrokenContractMetadata:
    top_level_module: str
    illegal_links: list[Link]
    original_expression: str | None
