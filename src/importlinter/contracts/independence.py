from typing import Iterable
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

        all_modules_for_each_subpackage = {}

        for module in self.modules:
            all_modules_for_each_subpackage[module] = {
               module
            } | graph.find_descendants(module)

        for subpackage_1, subpackage_2 in permutations(self.modules, r=2):
            for importer_module in all_modules_for_each_subpackage[subpackage_1]:
                for imported_module in all_modules_for_each_subpackage[subpackage_2]:
                    chain = graph.find_shortest_chain(
                        importer=importer_module,
                        imported=imported_module,
                    )
                    if chain:
                        check.is_valid = False
                        check.invalid_chains.add(chain)
        return check
