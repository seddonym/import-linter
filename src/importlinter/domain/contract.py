from typing import Any, Optional, Dict
import abc

from .ports.graph import ImportGraph


class Contract(abc.ABC):
    @abc.abstractmethod
    def __init__(self, session_options: Dict[str, Any], contract_options: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def check(self, graph: ImportGraph) -> 'ContractCheck':
        raise NotImplementedError

    @abc.abstractmethod
    def render_broken_contract(self, check: 'ContractCheck') -> None:
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
