from typing import List, Union, Any
import re
import abc

from importlinter.domain.imports import Module, DirectImport


class Field(abc.ABC):
    def __init__(self, required: bool = True) -> None:
        self.required = required

    @abc.abstractmethod
    def parse(self, raw_data: Union[str, List]) -> Any:
        raise NotImplementedError


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class StringField(Field):
    def parse(self, raw_data: Union[str, List]) -> str:
        if isinstance(raw_data, list):
            raise ValidationError('Expected a single value, got multiple values.')
        return str(raw_data)


class ListField(Field):
    def __init__(self, subfield: Field, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.subfield = subfield

    def parse(self, raw_data: Union[str, List]) ->List[Any]:
        if isinstance(raw_data, tuple):
            raw_data = list(raw_data)
        if not isinstance(raw_data, list):
            raise ValidationError('Expected multiple values, got a single value.')
        clean_list = []
        for raw_line in raw_data:
            clean_list.append(self.subfield.parse(raw_line))
        return clean_list


class ModuleField(StringField):
    def parse(self, raw_data: Union[str, List]) -> Module:
        return Module(super().parse(raw_data))


class DirectImportField(StringField):
    DIRECT_IMPORT_STRING_REGEX = re.compile(r'^([\w\.]+) -> ([\w\.]+)$')

    def parse(self, raw_data: Union[str, List]) -> DirectImport:
        string = super().parse(raw_data)
        match = self.DIRECT_IMPORT_STRING_REGEX.match(string)
        if not match:
            raise ValidationError('Must be in the form "package.importer -> package.imported".')
        importer, imported = match.groups()
        return DirectImport(importer=Module(importer), imported=Module(imported))
