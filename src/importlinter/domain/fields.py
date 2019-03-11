from typing import List, Union, Any
import re
import abc

from importlinter.domain.imports import Module, DirectImport


class Field(abc.ABC):
    @abc.abstractmethod
    def parse(self, raw_data: Union[str, List]) -> Any:
        raise NotImplementedError


class StringField(Field):
    def parse(self, raw_data: Union[str, List]) -> str:
        if not isinstance(raw_data, str):
            raise ValueError('Not a string.')
        return raw_data


class ListField(Field):
    def __init__(self, subfield: Field) -> None:
        self.subfield = subfield

    def parse(self, raw_data: Union[str, List]) ->List[Any]:
        if not isinstance(raw_data, list):
            raise ValueError('Not a list.')
        clean_list = []
        for raw_line in raw_data:
            clean_list.append(self.subfield.parse(raw_line))
        return clean_list


class ModuleField(StringField):
    def parse(self, raw_data: Union[str, List]) -> Module:
        return Module(super().parse(raw_data))


class DirectImportField(StringField):
    # Matches the form 'mypackage.foo -> mypackage.bar'
    DIRECT_IMPORT_STRING_REGEX = re.compile(r'^([\w\.]+) -> ([\w\.]+)$')

    def parse(self, raw_data: Union[str, List]) -> DirectImport:
        string = super().parse(raw_data)
        match = self.DIRECT_IMPORT_STRING_REGEX.match(string)
        if not match:
            raise ValueError(f'Could not parse direct import {direct_import_string}.')
        importer, imported = match.groups()
        return DirectImport(importer=Module(importer), imported=Module(imported))
