from typing import List

import grimp  # type: ignore
from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        return grimp.build_graph(
            *root_package_names, include_external_packages=include_external_packages
        )
