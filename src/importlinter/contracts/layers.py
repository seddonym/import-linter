from typing import Optional, Iterable, List

from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import DirectImport, Module
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain import helpers


class LayersContract(Contract):
    type_name = 'layers'

    def __init__(
        self,
        name: str,
        containers: Iterable[Module],
        layers: List[str],
        ignore_imports: Optional[Iterable[DirectImport]] = None,
    ) -> None:
        self.name = name
        self.containers = containers
        self.layers = layers
        self.ignore_imports = ignore_imports if ignore_imports else tuple()

    def check(self, graph: ImportGraph) -> ContractCheck:
        check = ContractCheck()
        check.is_valid = True

        direct_imports_to_ignore = self.ignore_imports
        removed_imports = helpers.pop_imports(graph, direct_imports_to_ignore)

        check.invalid_chains = set()

        for index, higher_layer in enumerate(self.layers):
            for lower_layer in self.layers[index + 1:]:
                for container in self.containers:
                    higher_layer_package = Module('.'.join([container.name, higher_layer]))
                    lower_layer_package = Module('.'.join([container.name, lower_layer]))

                    descendants = set(
                        map(Module, graph.find_descendants(higher_layer_package.name)))
                    higher_layer_modules = {higher_layer_package} | descendants

                    descendants = set(map(Module, graph.find_descendants(lower_layer_package.name)))
                    lower_layer_modules = {lower_layer_package} | descendants

                    for higher_layer_module in higher_layer_modules:
                        for lower_layer_module in lower_layer_modules:
                            chain = graph.find_shortest_chain(
                                importer=lower_layer_module.name,
                                imported=higher_layer_module.name,
                            )
                            if chain:
                                check.is_valid = False
                                check.invalid_chains.add(chain)

        helpers.add_imports(graph, removed_imports)

        return check
