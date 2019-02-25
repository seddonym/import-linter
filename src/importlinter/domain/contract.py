from typing import Any, Optional, Dict
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
    def render_broken_contract(self, check: 'ContractCheck', printer: Printer) -> None:
        raise NotImplementedError


class InvalidContract(Exception):
    """
    Exception if a contract itself is invalid.

    N. B. This is not the same thing as if a contract is violated; this is raised if the contract
    is not suitable for checking in the first place.
    """
    pass


class ContractCheck:
    """
    Data class to store the result of checking a contract.
    """
    def __init__(
        self,
        kept: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.kept = kept
        self.metadata = metadata if metadata else {}
