from typing import Optional, Tuple, Set, Dict, List, Union
import abc


class ImportGraph(abc.ABC):
    @abc.abstractmethod
    def find_descendants(self, module: str) -> Set[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_import_details(
        self,
        *,
        importer: str,
        imported: str
    ) -> List[Dict[str, Union[str, int]]]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_import(
        self, *,
        importer: str,
        imported: str,
        line_number: Optional[int] = None,
        line_contents: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    def remove_import(self, *, importer: str, imported: str) -> None:
        raise NotImplementedError


class GraphBuilder(abc.ABC):
    @abc.abstractmethod
    def set_graph(self, graph: ImportGraph) -> None:
        raise NotImplementedError
