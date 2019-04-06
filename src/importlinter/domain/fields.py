from typing import List, Union, Any
import re
import abc

from importlinter.domain.imports import Module, DirectImport


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class Field(abc.ABC):
    """
    Base class for containers for some data on a Contract.

    Designed to be subclassed, Fields should override the ``parse`` method.
    """
    def __init__(self, required: bool = True) -> None:
        self.required = required

    @abc.abstractmethod
    def parse(self, raw_data: Union[str, List[str]]) -> Any:
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
            raise ValidationError('Expected a single value, got multiple values.')
        return str(raw_data)


class ListField(Field):
    """
    A field for multiple values of any type.

    Arguments:
        - subfield: An instance of a single-value Field. Each item in the list will be the return
                    value of this subfield.
    Usage:

        field = ListField(subfield=AnotherField())

    """
    def __init__(self, subfield: Field, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.subfield = subfield

    def parse(self, raw_data: Union[str, List]) -> List[Any]:
        if isinstance(raw_data, tuple):
            raw_data = list(raw_data)
        if not isinstance(raw_data, list):
            raw_data = [raw_data]  # Single values should just be treated as a single item list.
        clean_list = []
        for raw_line in raw_data:
            clean_list.append(self.subfield.parse(raw_line))
        return clean_list


class ModuleField(Field):
    """
    A field for Modules.
    """
    def parse(self, raw_data: Union[str, List]) -> Module:
        return Module(StringField().parse(raw_data))


class DirectImportField(Field):
    """
    A field for DirectImports.

    Expects raw data in the form: "mypackage.foo.importer -> mypackage.bar.imported".
    """
    DIRECT_IMPORT_STRING_REGEX = re.compile(r'^([\w\.]+) -> ([\w\.]+)$')

    def parse(self, raw_data: Union[str, List]) -> DirectImport:
        string = StringField().parse(raw_data)
        match = self.DIRECT_IMPORT_STRING_REGEX.match(string)
        if not match:
            raise ValidationError('Must be in the form "package.importer -> package.imported".')
        importer, imported = match.groups()
        return DirectImport(importer=Module(importer), imported=Module(imported))
