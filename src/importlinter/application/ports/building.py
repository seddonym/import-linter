import abc
from typing import List, Optional

from importlinter.domain.ports.graph import ImportGraph


class GraphBuilder(abc.ABC):
    @abc.abstractmethod
    def build(
        self,
        root_package_names: List[str],
        cache_dir: Optional[str],
        include_external_packages: bool = False,
    ) -> ImportGraph:
        raise NotImplementedError
