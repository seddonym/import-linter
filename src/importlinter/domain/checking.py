from itertools import permutations

from .contract import Contract, LayerContract, IndependenceContract
from .ports.graph import DependencyGraph


class ContractCheck:
    ...


def check_contract(contract: Contract, graph: DependencyGraph) -> ContractCheck:
    checker = _get_checker(contract)
    check = checker(contract, graph)
    return check


def _get_checker(contract):
    return {
        LayerContract: _layer_contract_checker,
        IndependenceContract: _independence_contract_checker,
    }[contract.__class__]


def _layer_contract_checker(contract: LayerContract, graph: DependencyGraph) -> ContractCheck:
    check = ContractCheck()
    check.is_valid = True
    check.invalid_chains = set()

    for index, higher_layer in enumerate(contract.layers):
        for lower_layer in contract.layers[index + 1:]:
            for container in contract.containers:
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
    return check


def _independence_contract_checker(contract: IndependenceContract, graph: DependencyGraph) -> ContractCheck:
    check = ContractCheck()
    check.is_valid = True

    all_modules_for_each_subpackage = {}

    for module in contract.modules:
        all_modules_for_each_subpackage[module] = {
           module
        } | graph.find_descendants(module)

    for subpackage_1, subpackage_2 in permutations(contract.modules, r=2):
        for importer_module in all_modules_for_each_subpackage[subpackage_1]:
            for imported_module in all_modules_for_each_subpackage[subpackage_2]:
                if graph.find_shortest_chain(
                    importer=importer_module,
                    imported=imported_module,
                ):
                    check.is_valid = False
    return check
