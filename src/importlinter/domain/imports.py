from typing import Any, Iterable, Tuple
import fnmatch
import itertools
from importlinter.domain.ports.graph import ImportGraph


class ValueObject:
    def __repr__(self) -> str:
        return "<{}: {}>".format(self.__class__.__name__, self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __hash__(self) -> int:
        return hash(str(self))


class Module(ValueObject):
    """
    A Python module.
    """

    def __init__(self, name: str) -> None:
        """
        Args:
            name: The fully qualified name of a Python module, e.g. 'package.foo.bar'.
        """
        self.name = name

    def __str__(self) -> str:
        return self.name

    @property
    def root_package_name(self) -> str:
        return self.name.split(".")[0]

    @property
    def parent(self) -> "Module":
        components = self.name.split(".")
        if len(components) == 1:
            raise ValueError("Module has no parent.")
        return Module(".".join(components[:-1]))

    def is_child_of(self, module: "Module") -> bool:
        try:
            return module == self.parent
        except ValueError:
            # If this module has no parent, then it cannot be a child of the supplied module.
            return False

    def is_descendant_of(self, module: "Module") -> bool:
        return self.name.startswith(f"{module.name}.")

    def is_package(self) -> bool:
        """
        Whether the module can contain other modules.

        Practically, this corresponds to whether a module is an __init__.py file.
        """
        raise NotImplementedError


class ImportExpression(ValueObject):
    """
    A python import expression.
    """

    def __init__(self, importer: str, imported: str) -> None:
        self.importer = importer
        self.imported = imported

    def to_modules(self, graph: ImportGraph) -> Iterable[Tuple[Module, Module]]:
        importer = []
        imported = []

        for module in graph.modules:
            if fnmatch.fnmatch(module, self.importer):
                importer.append(Module(module))
            if fnmatch.fnmatch(module, self.imported):
                imported.append(Module(module))

        return itertools.product(importer, imported)

    def __str__(self) -> str:
        return "{} -> {}".format(self.importer, self.imported)

    def __hash__(self) -> int:
        return hash((self.importer, self.imported))
