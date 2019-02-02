import abc


class DependencyGraph(abc.ABC):
    @abc.abstractmethod
    def chain_exists(self, importer: str, imported: str, as_packages: bool = False) -> bool:
        raise NotImplementedError
