from grimp import ImportGraph

from importlinter.application import output
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck


class AlwaysPassesContract(Contract):
    warnings = fields.ListField(subfield=fields.StringField(), required=False)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        return ContractCheck(kept=True, warnings=self.warnings)  # type: ignore

    def render_broken_contract(self, check: "ContractCheck") -> None:
        # No need to implement, will never fail.
        raise NotImplementedError  # pragma: nocover


class AlwaysFailsContract(Contract):
    warnings = fields.ListField(subfield=fields.StringField(), required=False)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        return ContractCheck(kept=False, warnings=self.warnings)  # type: ignore

    def render_broken_contract(self, check: "ContractCheck") -> None:
        output.print("This contract will always fail.")


class NoisyContract(Contract):
    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        output.verbose_print(verbose, "Hello from the noisy contract!")
        return ContractCheck(kept=True)

    def render_broken_contract(self, check: "ContractCheck") -> None:
        # No need to implement, will never fail.
        raise NotImplementedError  # pragma: nocover


class ForbiddenImportContract(Contract):
    """
    Contract that defines a single forbidden import between
    two modules.
    """

    importer = fields.ModuleField()
    imported = fields.ModuleField()

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        forbidden_import_details = graph.get_import_details(
            importer=self.importer.name,  # type: ignore[attr-defined]
            imported=self.imported.name,  # type: ignore[attr-defined]
        )
        import_exists = bool(forbidden_import_details)

        return ContractCheck(
            kept=not import_exists,
            metadata={"forbidden_import_details": forbidden_import_details},
        )

    def render_broken_contract(self, check: "ContractCheck") -> None:
        output.print(f"{self.importer} is not allowed to import {self.imported}:")
        output.print()
        for details in check.metadata["forbidden_import_details"]:
            line_number = details["line_number"]
            line_contents = details["line_contents"]
            output.indent_cursor()
            output.print(f"{self.importer}:{line_number}: {line_contents}")


class FieldsContract(Contract):
    single_field = fields.StringField()
    multiple_field = fields.ListField(subfield=fields.StringField())
    import_field = fields.ImportExpressionField()
    required_field = fields.StringField()  # Fields are required by default.

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        raise NotImplementedError

    def render_broken_contract(self, check: "ContractCheck") -> None:
        raise NotImplementedError


class MutationCheckContract(Contract):
    """
    Contract for checking that contracts can't mutate the graph for other contracts.

    It checks that there are a certain number of modules and imports in the graph, then adds
    an extra import containing two new modules. We can check two such contracts and the second one
    will fail, if the graph gets mutated by other contracts.
    """

    number_of_modules = fields.IntegerField()
    number_of_imports = fields.IntegerField()

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        number_of_modules = int(self.number_of_modules)  # type: ignore
        number_of_imports = int(self.number_of_imports)  # type: ignore
        if not all(
            [
                number_of_modules == len(graph.modules),
                number_of_imports == graph.count_imports(),
            ]
        ):
            raise RuntimeError("Contract was mutated.")

        # Mutate graph.
        graph.add_import(importer="added-by-contract-1", imported="added-by-contract-2")
        return ContractCheck(kept=True)

    def render_broken_contract(self, check: "ContractCheck") -> None:
        raise NotImplementedError
