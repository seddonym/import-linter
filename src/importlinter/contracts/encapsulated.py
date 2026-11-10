from __future__ import annotations

import grimp

from importlinter import Contract, ContractCheck, fields, output
from importlinter.application import contract_utils
from importlinter.domain import helpers

from ._common import Link


class EncapsulatedContract(Contract):
    """
    Encapsulated contracts check that a set of modules is isolated from the rest of the project.

    The modules are treated as a single unit, made up of the listed modules and all of their
    descendants. The listed modules don't need to be adjacent: for example, a feature split
    across a data layer and a domain layer can form one unit. Imports within the unit are always
    allowed. Imports across its boundary are not:

        - The unit must not import any other module in the project, except for the modules it is
          allowed to import. (Imports of external packages are not affected.)
        - Other modules in the project must not import the unit, except for its public modules.

    Only direct imports are checked: an indirect import has to begin or end with a direct import
    across the boundary, which is reported instead.

    Configuration options:

        - modules:        The modules that make up the unit. Descendants are included too.
        - public_modules: Modules (and their descendants) within the unit that other modules are
                          allowed to import. (Optional.)
        - allow_imports_to: Modules (and their descendants) outside the unit that the unit is
                          allowed to import, such as shared utilities. This only affects imports
                          out of the unit: these modules still can't import the unit except via
                          its public modules. (Optional.)
        - ignore_imports: A set of ImportExpressions. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                          `ignore_imports` set is not found in the graph. Valid values are
                          "none", "warn", "error". Default value is "error".
        - broken_contract_guidance: Guidance explaining how to fix the contract if it's broken.
                          These are displayed after the contract's violations. (Optional.)
    """

    type_name = "encapsulated"

    modules = fields.SetField(subfield=fields.ModuleExpressionField())
    public_modules = fields.SetField(subfield=fields.ModuleExpressionField(), required=False)
    allow_imports_to = fields.SetField(subfield=fields.ModuleExpressionField(), required=False)
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(
        contract_utils.AlertLevel, default=contract_utils.AlertLevel.ERROR
    )
    broken_contract_guidance = fields.TextField(required=False)

    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        import_removal = contract_utils.remove_ignored_imports_and_report(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        unit = self._get_modules(graph, self.modules)
        public = self._get_modules(graph, self.public_modules or ())
        public_modules_outside_unit = public - unit
        if public_modules_outside_unit:
            raise ValueError(
                "Public modules must be within the encapsulated modules, but these are not: "
                f"{', '.join(sorted(public_modules_outside_unit))}."
            )

        # Check the listed modules themselves, not their descendants: allowing a parent package of
        # the unit is fine, and means the unit may import anything else in that package.
        allowed_modules_inside_unit = (
            self._get_modules(graph, self.allow_imports_to or (), as_packages=False) & unit
        )
        if allowed_modules_inside_unit:
            raise ValueError(
                "Modules in allow_imports_to must be outside the encapsulated modules, but these "
                f"are not: {', '.join(sorted(allowed_modules_inside_unit))}."
            )
        allowed = self._get_modules(graph, self.allow_imports_to or ())

        root_packages = tuple(self.session_options["root_packages"])
        root_package_prefixes = tuple(f"{root}." for root in root_packages)

        def is_in_project(module: str) -> bool:
            return module in root_packages or module.startswith(root_package_prefixes)

        outbound: list[Link] = []
        inbound: list[Link] = []
        for module in sorted(unit):
            # Check outbound imports.
            for imported in sorted(
                graph.find_modules_directly_imported_by(module) - unit - allowed
            ):
                if is_in_project(imported):
                    outbound.append(self._build_link(graph, importer=module, imported=imported))

            # Check inbound imports.
            if module in public:
                # Imports to the public API are fine.
                continue
            for importer in sorted(graph.find_modules_that_directly_import(module) - unit):
                if is_in_project(importer):
                    inbound.append(self._build_link(graph, importer=importer, imported=module))

        return ContractCheck(
            kept=not (outbound or inbound),
            warnings=list(import_removal.warnings),
            ignored_import_count=import_removal.ignored_import_count,
            # Outbound: imports from the unit to other modules in the project, other than the ones
            # it is allowed to import.
            # Inbound: imports into the unit from anywhere other than a public module.
            metadata={"outbound": outbound, "inbound": inbound},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        outbound: list[Link] = check.metadata["outbound"]
        inbound: list[Link] = check.metadata["inbound"]

        if outbound:
            output.print_error(
                "Imports out of the encapsulated modules are not allowed:", bold=False
            )
            output.new_line()
            self._render_links(outbound)

        if inbound:
            if self.public_modules:
                heading = (
                    "Imports into the encapsulated modules are only allowed "
                    "via the public modules:"
                )
            else:
                heading = "Imports into the encapsulated modules are not allowed:"
            output.print_error(heading, bold=False)
            output.new_line()
            self._render_links(inbound)

        contract_utils.render_broken_contract_guidance(self.broken_contract_guidance)  # type: ignore

    @staticmethod
    def _render_links(links: list[Link]) -> None:
        for link in links:
            line_numbers = ", ".join(map(str, link["line_numbers"]))
            output.print_error(
                f"- {link['importer']} -> {link['imported']} (l.{line_numbers})", bold=False
            )
            output.new_line()
        output.new_line()

    @staticmethod
    def _get_modules(graph: grimp.ImportGraph, expressions, as_packages: bool = True) -> set[str]:
        modules = helpers.module_expressions_to_modules(
            graph=graph,
            expressions=expressions,
            as_packages=as_packages,
            raise_if_unmatched=True,
        )
        return {module.name for module in modules}

    @staticmethod
    def _build_link(graph: grimp.ImportGraph, importer: str, imported: str) -> Link:
        import_details = graph.get_import_details(importer=importer, imported=imported)
        return Link(
            importer=importer,
            imported=imported,
            line_numbers=tuple(detail["line_number"] for detail in import_details),
        )
