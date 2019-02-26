from typing import Dict, Any

from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain.imports import Module
from importlinter.application import output


class AlwaysPassesContract(Contract):
    def __init__(self, session_options: Dict[str, Any], contract_options: Dict[str, Any]) -> None:
        raise NotImplementedError

    def check(self, graph: ImportGraph) -> ContractCheck:
        return ContractCheck(
            kept=True,
        )

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        # No need to implement, will never fail.
        raise NotImplementedError


class AlwaysFailsContract(Contract):
    def __init__(self, session_options: Dict[str, Any], contract_options: Dict[str, Any]) -> None:
        raise NotImplementedError

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
    def __init__(self, session_options: Dict[str, Any], contract_options: Dict[str, Any]) -> None:
        raise NotImplementedError
    # def __init__(self, name: str, importer: Module, imported: Module) -> None:
    #     # TODO - should this get the root package name?
    #     # TODO - should this be where we validate the contract?
    #     # TODO - should this receive just a dict of primitives from the config?
    #     self.name = name
    #     self.importer = importer
    #     self.imported = imported

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
