from typing import Iterable, Dict, Set
from itertools import permutations

from importlinter.domain.contract import Contract
from importlinter.domain.checking import ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class IndependenceContract(Contract):
    type_name = 'independence'

    def __init__(self, name: str, modules: Iterable[Module]) -> None:
        self.name = name
        self.modules = modules

    def check(self, graph: ImportGraph) -> ContractCheck:
        check = ContractCheck()
        check.is_valid = True
        check.invalid_chains = set()

        all_modules_for_each_subpackage: Dict[Module, Set[Module]] = {}

        for module in self.modules:
            descendants = set(map(Module, graph.find_descendants(module.name)))
            all_modules_for_each_subpackage[module] = {module} | descendants

        for subpackage_1, subpackage_2 in permutations(self.modules, r=2):
            for importer_module in all_modules_for_each_subpackage[subpackage_1]:
                for imported_module in all_modules_for_each_subpackage[subpackage_2]:
                    chain = graph.find_shortest_chain(
                        importer=importer_module.name,
                        imported=imported_module.name,
                    )
                    if chain:
                        check.is_valid = False
                        check.invalid_chains.add(chain)
        return check
