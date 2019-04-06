from typing import Optional, Tuple, Union, Set, List, Dict

from importlinter.domain.ports.graph import ImportGraph


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
        import_details: List[Dict[str, Union[str, int]]] = None,
        all_modules: Optional[List[str]] = None,
        module_count: int = 99,
        import_count: int = 999,
    ) -> None:
        self.root_package_name = root_package_name
        self._fake_descendants = descendants if descendants else {}
        self._fake_shortest_chains = shortest_chains if shortest_chains else {}
        self._import_details = import_details if import_details else []
        if all_modules:
            self._modules = all_modules
            self._module_count = len(all_modules)
        else:
            self._module_count = module_count
        self._import_count = import_count
        self._removed_imports: List[Tuple[TwoChain]] = []

    @property
    def modules(self) -> Set[str]:
        """
        The names of all the modules in the graph.
        """
        try:
            return set(self._modules)
        except AttributeError:
            # Fake the size of the set.
            return {str(m) for m in range(self._module_count)}

    def count_imports(self) -> int:
        """
        Return the number of imports in the graph.
        """
        return self._import_count

    def find_descendants(self, module: str) -> Set[str]:
        try:
            descendants_without_root = self._fake_descendants[self._remove_root(module)]
        except KeyError:
            return set()
        else:
            return set(['.'.join([module, d]) for d in descendants_without_root])

    def find_shortest_chain(self, importer: str, imported: str) -> Optional[Tuple[str, ...]]:
        if hasattr(self, '_modules'):
            # If we have set the modules explicitly, we should error if the module isn't in
            # the graph.
            for m in (importer, imported):
                assert m in self._modules, 'Module not in graph.'
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
        imported: str,
    ) -> List[Dict[str, Union[str, int]]]:
        matching_details = []
        for detail in self._import_details:
            if (detail['importer'], detail['imported']) == (importer, imported):
                matching_details.append(detail)
        return matching_details

    def add_import(
            self, *,
            importer: str,
            imported: str,
            line_number: Optional[int] = None,
            line_contents: Optional[str] = None
    ) -> None:
        pass

    def remove_import(self, *, importer: str, imported: str) -> None:
        rootless_importer = self._remove_root(importer)
        rootless_imported = self._remove_root(imported)
        self._fake_shortest_chains = dict([
            (ends, chain) for ends, chain in self._fake_shortest_chains.items()
            if not self._import_is_in_chain(rootless_importer, rootless_imported, chain)
        ])

    def _remove_root(self, module: str) -> str:
        assert module.startswith(self.root_package_name)
        return module[len(self.root_package_name) + 1:]

    def _add_root(self, module: str) -> str:
        return '.'.join([self.root_package_name, module])

    def _import_is_in_chain(self, importer: str, imported: str, chain: Chain) -> bool:
        for pair in [chain[i:i + 2] for i in range(len(chain))]:
            if (importer, imported) == pair:
                return True
        return False
