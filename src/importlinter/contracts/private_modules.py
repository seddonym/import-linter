from __future__ import annotations

import grimp

from importlinter.application import contract_utils, output
from importlinter.domain import fields, helpers
from importlinter.domain.contract import Contract, ContractCheck

from ._common import Link


class PrivateModulesContract(Contract):
    """
    Private modules contracts check that private modules are only imported from within their
    parent package.

    A module is private if the last component of its name starts with a single underscore,
    e.g. mypackage.foo._bar. (Names like __main__ are not private.) The descendants of a private
    module are covered too.

    A private module may only be imported by its parent package (e.g. mypackage.foo) or by a
    descendant of its parent package, however deeply nested.

    Configuration options:

        - packages:       The packages (and their descendants) whose private modules should be
                          checked. Imports of any other private modules are not checked. If not
                          supplied, the private modules in all of the root packages are checked.
                          (Optional.)
        - ignore_imports: A set of ImportExpressions. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the set will cause
                          the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                          `ignore_imports` set is not found in the graph. Valid values are
                          "none", "warn", "error". Default value is "error".
        - broken_contract_guidance: Guidance explaining how to fix the contract if it's broken.
                          These are displayed after the contract's violations. (Optional.)
    """

    type_name = "private_modules"

    packages = fields.SetField(subfield=fields.ModuleExpressionField(), required=False)
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

        modules_to_check = self._get_modules_to_check(graph)
        illegal_imports: set[tuple[str, str]] = set()
        for private_module in sorted(m for m in modules_to_check if _is_private_module(m)):
            illegal_imports |= _find_imports_from_outside_parent(graph, private_module)

        links = [
            _build_link(graph, importer=importer, imported=imported)
            for importer, imported in sorted(illegal_imports)
        ]
        return ContractCheck(
            kept=not links,
            warnings=list(import_removal.warnings),
            ignored_import_count=import_removal.ignored_import_count,
            metadata={"illegal_imports": links},
        )

    def _get_modules_to_check(self, graph: grimp.ImportGraph) -> set[str]:
        if not self.packages:
            return set(graph.modules)
        modules = helpers.module_expressions_to_modules(
            graph=graph,
            expressions=self.packages,  # type: ignore
            as_packages=True,
            raise_if_unmatched=True,
        )
        return {module.name for module in modules}

    def render_broken_contract(self, check: ContractCheck) -> None:
        output.print_error(
            "Private modules may only be imported from within their parent package:",
            bold=False,
        )
        output.new_line()
        links: list[Link] = check.metadata["illegal_imports"]
        for link in links:
            line_numbers = ", ".join(map(str, link["line_numbers"]))
            output.print_error(
                f"- {link['importer']} -> {link['imported']} (l.{line_numbers})",
                bold=False,
            )
            output.new_line()
        contract_utils.render_broken_contract_guidance(self.broken_contract_guidance)  # type: ignore


def _is_private_module(module: str) -> bool:
    """
    Return whether the last component of the module's name starts with a single underscore.

    Top level modules are never private, as they have no parent package to be private to.
    """
    if "." not in module:
        return False
    name = module.rsplit(".", maxsplit=1)[-1]
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _find_imports_from_outside_parent(
    graph: grimp.ImportGraph, private_module: str
) -> set[tuple[str, str]]:
    """
    Return the (importer, imported) pairs importing the private module, or any of its descendants,
    from outside the private module's parent package.
    """
    parent = private_module.rsplit(".", maxsplit=1)[0]
    # The trailing dot prevents e.g. mypackage.foobar being treated as a descendant of mypackage.foo.
    parent_prefix = f"{parent}."

    imports = set()
    for imported in {private_module} | graph.find_descendants(private_module):
        for importer in graph.find_modules_that_directly_import(imported):
            if importer != parent and not importer.startswith(parent_prefix):
                imports.add((importer, imported))
    return imports


def _build_link(graph: grimp.ImportGraph, importer: str, imported: str) -> Link:
    import_details = graph.get_import_details(importer=importer, imported=imported)
    return Link(
        importer=importer,
        imported=imported,
        line_numbers=tuple(detail["line_number"] for detail in import_details),
    )
