from typing import Dict, Any

from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain import fields
from importlinter.domain.imports import Module
from importlinter.application import output


class AlwaysPassesContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        return ContractCheck(
            kept=True,
        )

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        # No need to implement, will never fail.
        raise NotImplementedError  # pragma: nocover


class AlwaysFailsContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        return ContractCheck(
            kept=False,
        )

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        output.print('This contract will always fail.')


class ForbiddenImportContract(Contract):
    """
    Contract that defines a single forbidden import between
    two modules.
    """
    importer = fields.ModuleField()
    imported = fields.ModuleField()

    def check(self, graph: ImportGraph) -> ContractCheck:
        forbidden_import_details = graph.get_import_details(
            importer=self.importer.name, imported=self.imported.name)
        import_exists = bool(forbidden_import_details)

        return ContractCheck(
            kept=not import_exists,
            metadata={
                'forbidden_import_details': forbidden_import_details,
            }
        )

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        output.print(f'{self.importer} is not allowed to import {self.imported}:')
        output.print()
        for details in check.metadata['forbidden_import_details']:
            line_number = details['line_number']
            line_contents = details['line_contents']
            output.indent_cursor()
            output.print(f'{self.importer}:{line_number}: {line_contents}')


class FieldsContract(Contract):
    single_field = fields.StringField()
    multiple_field = fields.ListField(subfield=fields.StringField())
    import_field = fields.DirectImportField()
    required_field = fields.StringField()  # Fields are required by default.

    def check(self, graph: ImportGraph) -> ContractCheck:
        raise NotImplementedError

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        raise NotImplementedError
