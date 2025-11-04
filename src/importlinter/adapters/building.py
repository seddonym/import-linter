import grimp
from grimp import ImportGraph

from importlinter.application.ports import building as ports


class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """

    def build(
        self,
        root_package_names: list[str],
        cache_dir: str | None,
        include_external_packages: bool = False,
        exclude_type_checking_imports: bool = False,
    ) -> ImportGraph:
        return grimp.build_graph(
            *root_package_names,
            include_external_packages=include_external_packages,
            exclude_type_checking_imports=exclude_type_checking_imports,
            cache_dir=cache_dir,
        )
