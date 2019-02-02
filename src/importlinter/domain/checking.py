from .contract import Contract
from .ports.graph import DependencyGraph


class ContractCheck:
    ...


def check_contract(contract: Contract, graph: DependencyGraph) -> ContractCheck:
    check = ContractCheck()
    check.is_valid = True

    for index, higher_layer in enumerate(contract.layers):
        for lower_layer in contract.layers[index + 1:]:
            if graph.chain_exists(importer=lower_layer, imported=higher_layer, as_packages=True):
                check.is_valid = False
    return check
