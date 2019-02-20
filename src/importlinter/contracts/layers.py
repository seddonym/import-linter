from typing import Optional, Iterable

from importlinter.domain.contract import Contract
from importlinter.domain.checking import ContractCheck
from importlinter.domain.imports import DirectImport, Module
from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain import helpers


class LayersContract(Contract):
    type_name = 'layers'

    def __init__(
        self,
        name: str,
        containers: Iterable[Module],
        layers: Iterable[str],
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

        for index, higher_layer in enumerate( self.layers):
            for lower_layer in  self.layers[index + 1:]:
                for container in self.containers:
                    higher_layer_package = '.'.join([container, higher_layer])
                    lower_layer_package = '.'.join([container, lower_layer])

                    higher_layer_modules = {
                                               higher_layer_package
                                           } | graph.find_descendants(higher_layer_package)

                    lower_layer_modules = {
                                              lower_layer_package
                                          } | graph.find_descendants(lower_layer_package)

                    for higher_layer_module in higher_layer_modules:
                        for lower_layer_module in lower_layer_modules:
                            chain = graph.find_shortest_chain(
                                importer=lower_layer_module,
                                imported=higher_layer_module,
                            )
                            if chain:
                                check.is_valid = False
                                check.invalid_chains.add(chain)

        helpers.add_imports(graph, removed_imports)

        return check
