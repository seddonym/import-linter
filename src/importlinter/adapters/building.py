from typing import List

import grimp  # type: ignore
from importlinter.application.ports import building as ports
from importlinter.domain.ports.graph import ImportGraph

import pickle
from datetime import datetime

class GraphBuilder(ports.GraphBuilder):
    """
    GraphBuilder that just uses Grimp's standard build_graph function.
    """

    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        LOAD = True
        filename = "/Users/david/kraken.grimp"
        if LOAD:
            print(f'Loading graph at {datetime.now().time()}...')
            pickle_in = open(filename, "rb")
            graph = pickle.load(pickle_in)
            pickle_in.close()
            print(f'Loaded graph at {datetime.now().time()}.')
        else:
            print(f'Building graph at {datetime.now().time()}...')
            graph = grimp.build_graph(
                *root_package_names, include_external_packages=include_external_packages
            )
            print(f'Built graph at {datetime.now().time()}.')
            pickle_out = open(filename, "wb")
            pickle.dump(graph, pickle_out)
            pickle_out.close()
        return graph
