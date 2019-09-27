from typing import List

from importlinter.application.ports.building import GraphBuilder
from importlinter.domain.ports.graph import ImportGraph


class FakeGraphBuilder(GraphBuilder):
    """
    Graph builder that allows you to specify the graph ahead of time.

    To use, call inject_graph with the graph you wish to inject, ahead
    of when the builder would be called.
    """

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        return self._graph

    def inject_graph(self, graph: ImportGraph) -> None:
        self._graph = graph
