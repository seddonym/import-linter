from typing import List, Dict, Iterator, Tuple

from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain.contract import ContractCheck, Contract


class Reporter:
    ...


class ExceptionReporter:
    ...


class Report:
    def __init__(self, graph: ImportGraph) -> None:
        self.graph = graph
        self.contains_failures = False
        self.contracts: List[Contract] = []
        self._check_map: Dict[Contract, ContractCheck] = {}
        self.broken_count = 0
        self.kept_count = 0
        self.module_count = len(graph.modules)
        self.import_count = graph.count_imports()

    def add_contract_check(self, contract: Contract, contract_check: ContractCheck) -> None:
        self.contracts.append(contract)
        self._check_map[contract] = contract_check
        if contract_check.is_valid:
            self.kept_count += 1
        else:
            self.broken_count += 1
            self.contains_failures = True

    def get_contracts_and_checks(self) -> Iterator[Tuple[Contract, ContractCheck]]:
        for contract in self.contracts:
            yield contract, self._check_map[contract]
