import abc
from typing import Any, Dict, List, Optional, Type

from . import fields
from .ports.graph import ImportGraph


class Contract(abc.ABC):
    def __init__(
        self, name: str, session_options: Dict[str, Any], contract_options: Dict[str, Any]
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
                    errors[field_name] = "This is a required field."
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
    def check(self, graph: ImportGraph) -> "ContractCheck":
        raise NotImplementedError

    @abc.abstractmethod
    def render_broken_contract(self, check: "ContractCheck") -> None:
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

    def __init__(self, kept: bool, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.kept = kept
        self.metadata = metadata if metadata else {}


class NoSuchContractType(Exception):
    pass


class ContractRegistry:
    def __init__(self):
        self._classes_by_name = {}

    def register(self, contract_class: Type[Contract], name: str) -> None:
        self._classes_by_name[name] = contract_class

    def get_contract_class(self, name: str) -> Type[Contract]:
        try:
            return self._classes_by_name[name]
        except KeyError:
            raise NoSuchContractType(name)


registry = ContractRegistry()
