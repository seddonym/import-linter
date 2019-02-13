from typing import Iterable

class Contract:
    ...


class LayerContract(Contract):
    def __init__(self, name: str, containers: Iterable[str], layers: Iterable[str]) -> None:
        self.name = name
        self.containers = containers
        self.layers = layers


class IndependenceContract(Contract):
    ...