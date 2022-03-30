from typing import Dict, Iterator, List, Tuple

from importlinter.domain.contract import Contract, ContractCheck, InvalidContractOptions
from importlinter.domain.ports.graph import ImportGraph


class Reporter:
    ...


class ExceptionReporter:
    ...


class Report:
    def __init__(
        self, graph: ImportGraph, show_timings: bool, graph_building_duration: int
    ) -> None:
        self.graph = graph
        self.show_timings = show_timings
        self.graph_building_duration = graph_building_duration
        self.could_not_run = False
        self.invalid_contract_options: Dict[str, InvalidContractOptions] = {}
        self.contains_failures = False
        self.contracts: List[Contract] = []
        self._check_map: Dict[Contract, ContractCheck] = {}
        self._durations: Dict[Contract, int] = {}
        self.warnings_count = 0
        self.broken_count = 0
        self.kept_count = 0
        self.module_count = len(graph.modules)
        self.import_count = graph.count_imports()

    def add_contract_check(
        self, contract: Contract, contract_check: ContractCheck, duration: int
    ) -> None:
        self.contracts.append(contract)
        self._check_map[contract] = contract_check
        self._durations[contract] = duration
        self.warnings_count += len(contract_check.warnings)
        if contract_check.kept:
            self.kept_count += 1
        else:
            self.broken_count += 1
            self.contains_failures = True

    def get_contracts_and_checks(self) -> Iterator[Tuple[Contract, ContractCheck]]:
        for contract in self.contracts:
            yield contract, self._check_map[contract]

    def get_duration(self, contract) -> int:
        return self._durations[contract]

    def add_invalid_contract_options(
        self, contract_name: str, exception: InvalidContractOptions
    ) -> None:
        self.invalid_contract_options[contract_name] = exception
        self.could_not_run = True
        self.contains_failures = True
