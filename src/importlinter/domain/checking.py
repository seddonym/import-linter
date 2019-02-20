from typing import Iterable
from itertools import permutations

from .typing import DirectImportTuple
from .valueobjects import DirectImport
from .contract import Contract, LayerContract, IndependenceContract
from .ports.graph import ImportGraph


class InvalidContract(Exception):
    """
    Exception if a contract itself is invalid.

    N. B. This is not the same thing as if a contract is violated; this is raised if the contract
    is not suitable for checking in the first place.
    """
    pass


class ContractCheck:
    ...


def check_contract(contract: Contract, graph: ImportGraph) -> ContractCheck:
    checker = _get_checker(contract)
    check = checker(contract, graph)
    return check


def _get_checker(contract):
    return {
        LayerContract: _layer_contract_checker,
        IndependenceContract: _independence_contract_checker,
    }[contract.__class__]


def _layer_contract_checker(contract: LayerContract, graph: ImportGraph) -> ContractCheck:



def _independence_contract_checker


def _tuples_to_direct_imports(import_tuples: Iterable[DirectImportTuple]) -> DirectImport:
    direct_imports = []
    for importer, imported in import_tuples:
        direct_imports.append(
            DirectImport(importer=importer, imported=imported),
        )
    return direct_imports
