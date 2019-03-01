import grimp


from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(ports.GraphBuilder):
    def build(self, root_package_name: str) -> ImportGraph:
        return grimp.build_graph(root_package_name)
