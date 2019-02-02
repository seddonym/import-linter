from typing import Iterable, Tuple

from importlinter.domain.ports.graph import DependencyGraph


# A two-tuple representing a chain of imports between two modules.
# Item 0: the name of the downstream (importing) module.
# Item 1: the name of the upstream (imported) module.
Chain = Tuple[str, str]


class FakeGraph(DependencyGraph):
    def __init__(self, root_package: str, package_chains: Iterable[Chain]) -> None:
        self.root_package = root_package
        self._package_chains = package_chains

    def chain_exists(self, importer: str, imported: str, as_packages: bool = False) -> bool:
        assert as_packages is True
        for downstream, upstream in self._package_chains:
            if importer == downstream and imported == upstream:
                return True
        return False
