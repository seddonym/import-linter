from typing import Iterable, Optional

from .typing import DirectImportTuple


class Contract:
    ...


class LayerContract(Contract):
    def __init__(
        self,
        name: str,
        containers: Iterable[str],
        layers: Iterable[str],
        ignore_imports: Optional[Iterable[DirectImportTuple]] = None,
    ) -> None:
        self.name = name
        self.containers = containers
        self.layers = layers
        self.ignore_imports = ignore_imports if ignore_imports else tuple()


class IndependenceContract(Contract):
    def __init__(self, name: str, modules: Iterable[str]) -> None:
        self.name = name
        self.modules = modules
