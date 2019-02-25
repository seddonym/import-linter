from typing import Set, Tuple, Optional
import abc

from .ports.graph import ImportGraph
from importlinter.application.ports.printing import Printer


class Contract(abc.ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    def check(self, graph: ImportGraph) -> 'ContractCheck':
        raise NotImplementedError

    @abc.abstractmethod
    def report_failure(self, check: 'ContractCheck', printer: Printer) -> None:
        raise NotImplementedError


class InvalidContract(Exception):
    """
    Exception if a contract itself is invalid.

    N. B. This is not the same thing as if a contract is violated; this is raised if the contract
    is not suitable for checking in the first place.
    """
    pass


class ContractCheck:
    def __init__(self) -> None:
        self.invalid_chains: Set[Tuple[str, ...]]
        self.is_valid: Optional[bool] = None
