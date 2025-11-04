import abc

from grimp import ImportGraph


class GraphBuilder(abc.ABC):
    @abc.abstractmethod
    def build(
        self,
        root_package_names: list[str],
        cache_dir: str | None,
        include_external_packages: bool = False,
        exclude_type_checking_imports: bool = False,
    ) -> ImportGraph:
        raise NotImplementedError
