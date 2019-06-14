from importlinter.application.ports.building import GraphBuilder
from importlinter.domain.ports.graph import ImportGraph


class FakeGraphBuilder(GraphBuilder):
    def build(
        self, root_package_name: str, include_external_packages: bool = False
    ) -> ImportGraph:
        return self._graph

    def set_graph(self, graph: ImportGraph) -> None:
        self._graph = graph
