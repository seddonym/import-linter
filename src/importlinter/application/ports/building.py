import abc

from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(abc.ABC):
    @abc.abstractmethod
    def build(
        self,
        root_package_name: str,
        include_external_packages: bool = False,
    ) -> ImportGraph:
        raise NotImplementedError
