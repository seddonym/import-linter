import abc
import difflib
from typing import Any

from grimp import ImportGraph

from . import fields


# Options that every contract has, read by the application layer rather than by a field.
COMMON_CONTRACT_OPTIONS = frozenset({"id", "name", "type"})


class Contract(abc.ABC):
    def __init__(
        self,
        name: str,
        session_options: dict[str, Any],
        contract_options: dict[str, Any],
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
                if field.default is not fields.NotSupplied:
                    setattr(self, field_name, field.default)
                elif field.required:
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

        errors.update(self.__class__._get_unrecognized_option_errors(self.contract_options))

        if errors:
            raise InvalidContractOptions(errors)

        self.validate()

    def validate(self) -> None:
        """
        Hook method for validating inter-field dependencies.

        Raise InvalidContractOptions with an error dictionary keyed with the relevant field.
        """
        pass

    @classmethod
    def _get_field_names(cls) -> list[str]:
        """
        Returns:
            The names of all the fields on this contract class.
        """
        names: list[str] = []
        for klass in reversed(cls.__mro__):
            for name, attr in vars(klass).items():
                if isinstance(attr, fields.Field) and name not in names:
                    names.append(name)
        return names

    @classmethod
    def _get_unrecognized_option_errors(cls, contract_options: dict[str, Any]) -> dict[str, str]:
        """
        Returns:
            An error for each contract option that does not correspond to a field. Without
            this, a misspelled optional field (e.g. 'exhaustiv') would be silently ignored.
        """
        recognized = COMMON_CONTRACT_OPTIONS | {
            name for name in dir(cls) if isinstance(getattr(cls, name), fields.Field)
        }

        errors = {}
        for option in sorted(set(contract_options) - recognized):
            message = "Unrecognized option."
            close_matches = difflib.get_close_matches(option, sorted(recognized), n=1)
            if close_matches:
                message += f" Did you mean '{close_matches[0]}'?"
            errors[option] = message
        return errors

    @classmethod
    def _get_field(cls, field_name: str) -> fields.Field:
        return getattr(cls, field_name)

    @abc.abstractmethod
    def check(self, graph: ImportGraph, verbose: bool) -> "ContractCheck":
        """
        Args:
            graph:   Copy of the ImportGraph. May be mutated without affecting other contracts.
            verbose: Whether to output progress noisily. Can be used as a flag to pass
                     to output.verbose_print.
        """
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

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors


class ContractCheck:
    """
    Data class to store the result of checking a contract.
    """

    def __init__(
        self,
        kept: bool,
        metadata: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        ignored_import_count: int = 0,
    ) -> None:
        self.kept = kept
        self.metadata = metadata or {}
        self.warnings = warnings or []
        self.ignored_import_count = ignored_import_count


class NoSuchContractType(Exception):
    pass


class ContractRegistry:
    def __init__(self):
        self._classes_by_name = {}

    def register(self, contract_class: type[Contract], name: str) -> None:
        self._classes_by_name[name] = contract_class

    def get_contract_class(self, name: str) -> type[Contract]:
        try:
            return self._classes_by_name[name]
        except KeyError:
            raise NoSuchContractType(name)


registry = ContractRegistry()
