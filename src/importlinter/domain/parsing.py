from typing import List
import re

from .imports import DirectImport, Module


# Matches the form 'mypackage.foo -> mypackage.bar'
DIRECT_IMPORT_STRING_REGEX = re.compile(r'^([\w\.]+) -> ([\w\.]+)$')


def strings_to_direct_imports(direct_import_strings: List[str]) -> List[DirectImport]:
    """
    Convert a list of strings in the form 'mypackage.foo -> mypackage.bar' to DirectImports.
    """
    return [string_to_direct_import(s) for s in direct_import_strings]


def string_to_direct_import(direct_import_string: str) -> DirectImport:
    """
    Convert a string in the form 'mypackage.foo -> mypackage.bar' to a DirectImport.
    """
    match = DIRECT_IMPORT_STRING_REGEX.match(direct_import_string)
    if not match:
        raise ValueError(f'Could not parse direct import {direct_import_string}.')
    importer, imported = match.groups()
    return DirectImport(importer=Module(importer), imported=Module(imported))
