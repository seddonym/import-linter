from .contract import Contract
from .ports.graph import DependencyGraph


class ContractCheck:
    ...


def check_contract(contract: Contract, graph: DependencyGraph) -> ContractCheck:
    check = ContractCheck()
    check.is_valid = True

    for index, higher_layer in enumerate(contract.layers):
        for lower_layer in contract.layers[index + 1:]:
            for container in contract.containers:
                higher_layer_package = '.'.join([container, higher_layer])
                lower_layer_package = '.'.join([container, lower_layer])
                if graph.chain_exists(
                        importer=lower_layer_package,
                        imported=higher_layer_package,
                        as_packages=True,
                ):
                    check.is_valid = False
    return check
