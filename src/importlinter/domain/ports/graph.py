from typing import Dict, List, Optional, Set, Tuple, Union

# N.B. typing_extensions can be changed to typing once drop support for Python 3.7.
from typing_extensions import Protocol


class ImportGraph(Protocol):
    @property
    def modules(self) -> Set[str]:
        """
        The names of all the modules in the graph.
        """
        raise NotImplementedError

    def count_imports(self) -> int:
        """
        Return the number of imports in the graph.
        """
        raise NotImplementedError

    def find_children(self, module: str) -> Set[str]:
        raise NotImplementedError

    def find_descendants(self, module: str) -> Set[str]:
        raise NotImplementedError

    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        raise NotImplementedError

    def find_shortest_chains(self, importer: str, imported: str) -> Set[Tuple[str, ...]]:
        """
        Find the shortest import chains that exist between the importer and imported, and
        between any modules contained within them. Only one chain per upstream/downstream pair
        will be included. Any chains that are contained within other chains in the result set
        will be excluded.

        Returns:
            A set of tuples of strings. Each tuple is ordered from importer to imported modules.
        """
        raise NotImplementedError

    def get_import_details(
        self, *, importer: str, imported: str
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Returns a list of the details of every direct import between two modules, in the form:
        [
            {
                'importer': 'mypackage.importer',
                'imported': 'mypackage.imported',
                'line_number': 5,
                'line_contents': 'from mypackage import imported',
            },
            (additional imports here)
        ]
        """
        raise NotImplementedError

    def add_import(
        self,
        *,
        importer: str,
        imported: str,
        line_number: Optional[int] = None,
        line_contents: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    def remove_import(self, *, importer: str, imported: str) -> None:
        raise NotImplementedError

    def find_modules_directly_imported_by(self, module: str) -> Set[str]:
        raise NotImplementedError

    def find_modules_that_directly_import(self, module: str) -> Set[str]:
        raise NotImplementedError

    def squash_module(self, module: str) -> None:
        raise NotImplementedError

    def remove_module(self, module: str) -> None:
        raise NotImplementedError
