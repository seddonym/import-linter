from grimp import ImportGraph

from importlinter.application.ports.building import GraphBuilder


class FakeGraphBuilder(GraphBuilder):
    """
    Graph builder for when you don't actually want to build a graph.

    Features
    ========

    Injecting a graph
    -----------------

    This builder doesn't build a graph. Instead, call inject_graph with the graph you wish to
    inject, ahead of when the builder would be called.

    If inject_graph isn't called, an empty Grimp ImportGraph will be returned.

    Determining the build arguments
    -------------------------------

    The arguments the builder was last called with are stored in self.build_arguments.
    """

    def build(
        self,
        root_package_names: list[str],
        cache_dir: str | None,
        include_external_packages: bool = False,
        exclude_type_checking_imports: bool = False,
    ) -> ImportGraph:
        self.build_arguments = {
            "root_package_names": root_package_names,
            "cache_dir": cache_dir,
            "include_external_packages": include_external_packages,
            "exclude_type_checking_imports": exclude_type_checking_imports,
        }
        return getattr(self, "_graph", ImportGraph())

    def inject_graph(self, graph: ImportGraph) -> None:
        self._graph = graph
