from __future__ import annotations
from typing import Any


class ValueObject:
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self}>"

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

    def is_in_package(self, package: "Module") -> bool:
        return self == package or self.is_descendant_of(package)


class DirectImport(ValueObject):
    """
    An import between one module and another.
    """

    def __init__(
        self,
        *,
        importer: Module,
        imported: Module,
        line_number: int | None = None,
        line_contents: str | None = None,
    ) -> None:
        self.importer = importer
        self.imported = imported
        self.line_number = line_number
        self.line_contents = line_contents

    def __str__(self) -> str:
        if self.line_number:
            return f"{self.importer} -> {self.imported} (l. {self.line_number})"
        else:
            return f"{self.importer} -> {self.imported}"

    def __hash__(self) -> int:
        return hash((str(self), self.line_contents))


class ModuleExpression(ValueObject):
    """
    A user-submitted expression describing a module or a set of modules.

    Sets of modules are notated using * or ** wildcards.
    Examples:
        "mypackage.foo.bar": a single module
        "mypackage.foo.*": all direct submodules in the foo subpackage
        "mypackage.*.bar": all bar-submodules of any mypackage submodule
        "mypackage.**": all modules in the mypackage package

    Note that * and ** cannot be mixed in the same expression.
    """

    def __init__(self, expression: str) -> None:
        self.expression = expression

    def has_wildcard_expression(self) -> bool:
        return "*" in self.expression

    def __str__(self) -> str:
        return self.expression

    def __lt__(self, other: ModuleExpression) -> bool:
        return self.expression < other.expression


class ImportExpression(ValueObject):
    """
    A user-submitted expression describing an import or set of imports.

    The importer and imported expressions are both ModuleExpressions
    (see ModuleExpression for details).
    """

    def __init__(self, importer: ModuleExpression, imported: ModuleExpression) -> None:
        self.importer = importer
        self.imported = imported

    def has_wildcard_expression(self) -> bool:
        return self.imported.has_wildcard_expression() or self.importer.has_wildcard_expression()

    def __str__(self) -> str:
        return f"{self.importer.expression} -> {self.imported.expression}"
