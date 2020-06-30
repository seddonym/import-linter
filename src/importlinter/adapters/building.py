from typing import List

import grimp  # type: ignore
from grimp import exceptions as grimp_exceptions
from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        try:
            return grimp.build_graph(
                *root_package_names, include_external_packages=include_external_packages
            )
        except grimp_exceptions.SourceSyntaxError as e:
            raise ports.SourceSyntaxError(
                filename=e.filename, lineno=e.lineno, text=e.text,
            )
