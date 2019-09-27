import abc
from typing import Dict, List, Optional, Set, Tuple, Union


class ImportGraph(abc.ABC):
    @property
    @abc.abstractmethod
    def modules(self) -> Set[str]:
        """
        The names of all the modules in the graph.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count_imports(self) -> int:
        """
        Return the number of imports in the graph.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_descendants(self, module: str) -> Set[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        raise NotImplementedError

    @abc.abstractmethod
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

    @abc.abstractmethod
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

    @abc.abstractmethod
    def add_import(
        self,
        *,
        importer: str,
        imported: str,
        line_number: Optional[int] = None,
        line_contents: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_import(self, *, importer: str, imported: str) -> None:
        raise NotImplementedError
