from typing import Optional, Tuple, Set
import abc


class DependencyGraph(abc.ABC):
    @abc.abstractmethod
    def find_descendants(self, module: str) -> Set[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        raise NotImplementedError
