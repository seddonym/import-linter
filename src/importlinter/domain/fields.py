import abc
from enum import Enum
from typing import Generic, Iterable, List, Set, Type, TypeVar, Union, cast

from importlinter.domain.imports import ImportExpression, Module

FieldValue = TypeVar("FieldValue")


class NotSupplied:
    """Sentinel to use in place of None for a default argument value."""

    pass


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class Field(Generic[FieldValue], abc.ABC):
    """
    Base class for containers for some data on a Contract.

    Arguments:
        - required: if the field requires a value (default True).
        - default: a value to use if no value is supplied.

    Designed to be subclassed, Fields should override the ``parse`` method.
    """

    def __init__(
        self,
        required: Union[bool, Type[NotSupplied]] = NotSupplied,
        default: Union[FieldValue, Type[NotSupplied]] = NotSupplied,
    ) -> None:

        if default is NotSupplied:
            if required is NotSupplied:
                self.required = True
            else:
                required = cast(bool, required)
                self.required = required
        else:
            # A default was supplied.
            if required is True:
                # It doesn't make sense to require a field and provide a default.
                raise ValueError("A required field cannot also provide a default value.")
            else:
                self.required = False

        self.default = default

    @abc.abstractmethod
    def parse(self, raw_data: Union[str, List[str]]) -> FieldValue:
        """
        Given some raw data supplied by a user, return some clean data.

        Raises:
            ValidationError if the data is invalid.
        """
        raise NotImplementedError


class StringField(Field):
    """
    A field for single values of strings.
    """

    def parse(self, raw_data: Union[str, List]) -> str:
        if isinstance(raw_data, list):
            raise ValidationError("Expected a single value, got multiple values.")
        return str(raw_data)


class BaseMultipleValueField(Field):
    """
    An abstract field for multiple values of any type.

    Arguments:
        - subfield: An instance of a single-value Field. Each item in the iterable will be
                    the return value of this subfield.

    """

    def __init__(self, subfield: Field, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.subfield = subfield

    @abc.abstractmethod
    def parse(self, raw_data: Union[str, List]) -> Iterable[FieldValue]:
        if isinstance(raw_data, tuple):
            raw_data = list(raw_data)
        if not isinstance(raw_data, list):
            raw_data = [raw_data]  # Single values should just be treated as a single item list.
        clean_list = []
        for raw_line in raw_data:
            clean_list.append(self.subfield.parse(raw_line))
        return clean_list


class ListField(BaseMultipleValueField):
    """
    A field for multiple values of any type.

    Fields values are returned in list sorted by parsing order.

    Usage:

        field = ListField(subfield=AnotherField())
    """

    def parse(self, raw_data: Union[str, List]) -> List[FieldValue]:
        return list(super().parse(raw_data))


class SetField(BaseMultipleValueField):
    """
    A field for multiple, unique values of any type.

    Fields values are returned inordered in set.

    Usage:

        field = SetField(subfield=AnotherField())

    """

    def parse(self, raw_data: Union[str, List]) -> Set[FieldValue]:
        return set(super().parse(raw_data))


class ModuleField(Field):
    """
    A field for Modules.
    """

    def parse(self, raw_data: Union[str, List]) -> Module:
        return Module(StringField().parse(raw_data))


class ImportExpressionField(Field):
    """
    A field for ImportExpressions.

    Expects raw data in the form:
        "mypackage.foo.importer -> mypackage.bar.imported".

    In addition, it handles wildcards:
        "mypackage.*.importer -> mypackage.bar.*"
    """

    def parse(self, raw_data: Union[str, List]) -> ImportExpression:
        string = StringField().parse(raw_data)
        importer, _, imported = string.partition(" -> ")

        if not (importer and imported):
            raise ValidationError('Must be in the form "package.importer -> package.imported".')

        self._validate_wildcard(importer)
        self._validate_wildcard(imported)

        return ImportExpression(importer=importer, imported=imported)

    def _validate_wildcard(self, expression: str) -> None:
        for part in expression.split("."):
            if len(part) > 1 and "*" in part:
                raise ValidationError("A wildcard can only replace a whole module.")


class EnumField(Field):
    """
    A field constrained by the values of an Enum.

    Currently only Enums with string values are supported.

    Raises a ValidationError if the supplied string value does not match one of the Enum
    members' values.

    Example:

        import enum

        class Color(enum.Enum):
            RED = "red"
            BLUE = "blue"
            LIGHT_BLUE = "light blue"

        field = EnumField(Color, default=Color.RED)

        assert field.parse("blue") == Color.BLUE
        assert field.parse("light blue") == Color.LIGHT_BLUE
        assert field.parse("") == Color.RED
    """

    def __init__(self, enum: Type[Enum], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._check_supported_enum_class(enum)
        self.enum = enum

    def parse(self, raw_data: Union[str, List]) -> Enum:
        if isinstance(raw_data, list):
            raise ValidationError("Expected a single value, got multiple values.")

        stripped_data = raw_data.strip()

        if stripped_data == "":
            return cast(Enum, self.default)

        member_by_value = {m.value: m for m in self.enum}
        try:
            return member_by_value[stripped_data]
        except KeyError:
            values = list(member_by_value.keys())
            expectation_string = ", ".join(f"'{i}'" for i in values[:-1]) + f" or '{values[-1]}'"
            raise ValidationError(
                f"Invalid value '{stripped_data}': " f"expected {expectation_string}."
            )

    def _check_supported_enum_class(self, enum: Type[Enum]) -> None:
        for member in enum:
            # Check it's a string.
            if not isinstance(member.value, str):
                raise TypeError(
                    "Unsupported Enum for EnumField: member values must all be strings."
                )
