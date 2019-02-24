from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.ports.graph import ImportGraph
from importlinter.application.ports.printing import Printer


class AlwaysPassesContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        contract_check = ContractCheck()
        contract_check.is_valid = True
        return contract_check

    def report_failure(self, printer: Printer) -> None:
        # No need to implement, will never fail.
        raise NotImplementedError


class AlwaysFailsContract(Contract):
    def check(self, graph: ImportGraph) -> ContractCheck:
        contract_check = ContractCheck()
        contract_check.is_valid = False
        return contract_check

    def report_failure(self, printer: Printer) -> None:
        printer.print('This contract will always fail.')
