from typing import Iterable, Dict, Union, List

from importlinter.domain.ports.graph import ImportGraph
from importlinter.domain.imports import DirectImport


def pop_imports(graph: ImportGraph, imports: Iterable[DirectImport]) -> Iterable[DirectImport]:
    direct_imports = []
    for importer, imported in direct_imports:
        try:
            import_details = graph.get_import_details(importer=importer, imported=imported)
        except ValueError:  # TODO: what's the exception?
            raise RuntimeError('Ignored import {} not present in the graph.')
        direct_imports.extend(import_details)
        graph.remove_import(importer=importer, imported=imported)
    return direct_imports


def add_imports(graph: ImportGraph, import_details: List[Dict[str, Union[str, int]]]) -> None:
    for details in import_details:
        graph.add_import(
            importer=details['importer'],
            imported=details['imported'],
            line_number=details['line_number'],
            line_contents=details['line_contents'],
        )
