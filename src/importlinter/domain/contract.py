from typing import Any, Optional, Dict, List, Type
import importlib
import abc

from .ports.graph import ImportGraph
from . import fields


class Contract(abc.ABC):
    def __init__(
        self,
        name: str,
        session_options: Dict[str, Any],
        contract_options: Dict[str, Any],
    ) -> None:
        self.name = name
        self.session_options = session_options
        self.contract_options = contract_options

        self._populate_fields()

    def _populate_fields(self) -> None:
        """
        Populate the contract's fields from the contract options.

        Raises:
            InvalidContractOptions if the contract options could not be matched to the fields.
        """
        errors = {}
        for field_name in self.__class__._get_field_names():
            field = self.__class__._get_field(field_name)

            try:
                raw_data = self.contract_options[field_name]
            except KeyError:
                if field.required:
                    errors[field_name] = 'This is a required field.'
                else:
                    setattr(self, field_name, None)
                continue

            try:
                clean_data = field.parse(raw_data)
            except fields.ValidationError as e:
                errors[field_name] = str(e)
                continue
            setattr(self, field_name, clean_data)

        if errors:
            raise InvalidContractOptions(errors)

    @classmethod
    def _get_field_names(cls) -> List[str]:
        """
        Returns:
            The names of all the fields on this contract class.
        """
        return [name for name, attr in cls.__dict__.items() if isinstance(attr, fields.Field)]

    @classmethod
    def _get_field(cls, field_name: str) -> fields.Field:
        return getattr(cls, field_name)

    @abc.abstractmethod
    def check(self, graph: ImportGraph) -> 'ContractCheck':
        raise NotImplementedError

    @abc.abstractmethod
    def render_broken_contract(self, check: 'ContractCheck') -> None:
        raise NotImplementedError


class InvalidContractOptions(Exception):
    """
    Exception if a contract itself is invalid.

    N. B. This is not the same thing as if a contract is violated; this is raised if the contract
    is not suitable for checking in the first place.
    """
    def __init__(self, errors: Dict[str, str]) -> None:
        self.errors = errors


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


class ContractRegistry:
    def get_contract_class(self, type_name: str) -> Type[Contract]:
        components = type_name.split('.')
        contract_class_name = components[-1]
        module_name = '.'.join(components[:-1])
        module = importlib.import_module(module_name)
        contract_class = getattr(module, contract_class_name)
        if not issubclass(contract_class, Contract):
            raise TypeError(f'{contract_class} is not a subclass of Contract.')
        return contract_class


registry = ContractRegistry()
