from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain.imports import Module
from importlinter.application.ports.printing import Printer


class AlwaysPassesContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        contract_check = ContractCheck()
        contract_check.is_valid = True
        return contract_check

    def report_failure(self, check: ContractCheck, printer: Printer) -> None:
        # No need to implement, will never fail.
        raise NotImplementedError


class AlwaysFailsContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        contract_check = ContractCheck()
        contract_check.is_valid = False
        return contract_check

    def report_failure(self, check: ContractCheck, printer: Printer) -> None:
        printer.print('This contract will always fail.')


class ForbiddenImportContract(Contract):
    """
    Contract that defines a single forbidden import between
    two modules.
    """
    def __init__(self, name: str, importer: Module, imported: Module) -> None:
        self.name = name
        self.importer = importer
        self.imported = imported

    def check(self, graph: ImportGraph) -> ContractCheck:
        contract_check = ContractCheck()
        contract_check.forbidden_import_details = graph.get_import_details(
            importer=self.importer.name, imported=self.imported.name)
        import_exists = bool(contract_check.forbidden_import_details)
        contract_check.is_valid = not import_exists
        return contract_check

    def report_failure(self, check: ContractCheck, printer: Printer) -> None:
        printer.print(f'{self.importer} is not allowed to import {self.imported}:')
        printer.print()
        for details in check.forbidden_import_details:
            line_number = details['line_number']
            line_contents = details['line_contents']
            # TODO - this should use indent cursor
            printer.print(f'    {self.importer}:{line_number}: {line_contents}')
