from typing import Optional, Tuple, Union, Set, List, Dict

from importlinter.domain.ports.graph import ImportGraph, GraphBuilder


# A two-tuple representing a chain of imports between two modules.
# Item 0: the name of the downstream (importing) module.
# Item 1: the name of the upstream (imported) module.
TwoChain = Tuple[str, str]
Chain = Tuple[str, ...]


class FakeGraph(ImportGraph):
    def __init__(
            self,
            root_package_name: str,
            descendants: Dict[str, Set[str]] = None,
            shortest_chains: Dict[TwoChain, Chain] = None,
    ) -> None:
        self.root_package_name = root_package_name
        self._fake_descendants = descendants if descendants else {}
        self._fake_shortest_chains = shortest_chains if shortest_chains else {}

    def find_descendants(self, module: str) -> Set[str]:
        try:
            descendants_without_root = self._fake_descendants[self._remove_root(module)]
        except KeyError:
            return set()
        else:
            return set(['.'.join([module, d]) for d in descendants_without_root])

    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        try:
            chain_without_root = self._fake_shortest_chains[
                (self._remove_root(importer), self._remove_root(imported))
            ]
        except KeyError:
            return None
        else:
            return tuple([self._add_root(m) for m in chain_without_root])

    def get_import_details(
            self,
            *,
            importer: str,
            imported: str
    ) -> List[Dict[str, Union[str, int]]]:
        raise NotImplementedError

    def add_import(
            self, *,
            importer: str,
            imported: str,
            line_number: Optional[int] = None,
            line_contents: Optional[str] = None
    ) -> None:
        raise NotImplementedError

    def _remove_root(self, module: str) -> str:
        assert module.startswith(self.root_package_name)
        return module[len(self.root_package_name) + 1:]

    def _add_root(self, module: str) -> str:
        return '.'.join([self.root_package_name, module])


class FakeGraphBuilder(GraphBuilder):
    def set_graph(self, graph: ImportGraph) -> None:
        self._graph = graph

