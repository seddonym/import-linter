import grimp  # type: ignore


from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """
    def build(self, root_package_name: str) -> ImportGraph:
        return grimp.build_graph(root_package_name)
