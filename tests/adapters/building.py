from importlinter.domain.ports.graph import ImportGraph
from importlinter.application.ports.building import GraphBuilder


class FakeGraphBuilder(GraphBuilder):
    def build(self, root_package_name: str) -> ImportGraph:
        return self._graph

    def set_graph(self, graph: ImportGraph) -> None:
        self._graph = graph
