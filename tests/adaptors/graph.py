from typing import Optional, Tuple, Dict, Set

from importlinter.domain.ports.graph import DependencyGraph


# A two-tuple representing a chain of imports between two modules.
# Item 0: the name of the downstream (importing) module.
# Item 1: the name of the upstream (imported) module.
TwoChain = Tuple[str, str]
Chain = Tuple[str, ...]


class FakeGraph(DependencyGraph):
    def __init__(
            self,
            root_package: str,
            descendants: Dict[str, Set[str]],
            shortest_chains: Dict[TwoChain, Chain],
    ) -> None:
        self.root_package = root_package
        self._fake_descendants = descendants
        self._fake_shortest_chains = shortest_chains

    # def chain_exists(self, importer: str, imported: str, as_packages: bool = False) -> bool:
    #     assert as_packages is False
    #     for downstream, upstream in self._package_chains:
    #         if importer == downstream and imported == upstream:
    #             return True
    #     return False
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

    def _remove_root(self, module: str) -> str:
        assert module.startswith(self.root_package)
        return module[len(self.root_package) + 1:]

    def _add_root(self, module: str) -> str:
        return '.'.join([self.root_package, module])
