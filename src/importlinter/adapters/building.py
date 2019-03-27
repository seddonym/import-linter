import grimp  # type: ignore


from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """
    def build(
        self,
        root_package_name: str,
        include_external_packages: bool = False,
    ) -> ImportGraph:
        return grimp.build_graph(
            package_name=root_package_name,
            include_external_packages=include_external_packages,
        )
