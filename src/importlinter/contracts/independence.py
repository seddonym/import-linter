from typing import Dict, Set, Any
from itertools import permutations

from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class IndependenceContract(Contract):
    type_name = 'independence'

    def __init__(
        self,
        name: str,
        session_options: Dict[str, Any],
        contract_options: Dict[str, Any],
    ) -> None:
        super().__init__(name, session_options, contract_options)
        self.modules = list(map(Module, contract_options['modules']))

    def check(self, graph: ImportGraph) -> ContractCheck:
        is_kept = True
        invalid_chains = set()

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
                        is_kept = False
                        invalid_chains.add(chain)
        return ContractCheck(kept=is_kept, metadata={'invalid_chains': invalid_chains})

    def render_broken_contract(self, check: 'ContractCheck') -> None:
        raise NotImplementedError
