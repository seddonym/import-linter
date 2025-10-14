from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class ValueObject(BaseModel):
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

    name: str

    def __str__(self) -> str:
        return self.name

    @property
    def root_package_name(self) -> str:
        return self.name.split(".")[0]

    @property
    def parent(self) -> Module:
        components = self.name.split(".")
        if len(components) == 1:
            raise ValueError("Module has no parent.")
        return Module(name=".".join(components[:-1]))

    def is_child_of(self, module: Module) -> bool:
        try:
            return module == self.parent
        except ValueError:
            # If this module has no parent, then it cannot be a child of the supplied module.
            return False

    def is_descendant_of(self, module: Module) -> bool:
        return self.name.startswith(f"{module.name}.")

    def is_in_package(self, package: Module) -> bool:
        return self == package or self.is_descendant_of(package)


class DirectImport(ValueObject):
    """
    An import between one module and another.
    """

    importer: Module
    imported: Module
    line_number: Optional[int] = None
    line_contents: Optional[str] = None

    def __str__(self) -> str:
        if self.line_number:
            return "{} -> {} (l. {})".format(self.importer, self.imported, self.line_number)
        else:
            return "{} -> {}".format(self.importer, self.imported)

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

    expression: str

    def has_wildcard_expression(self) -> bool:
        return "*" in self.expression

    def __str__(self) -> str:
        return self.expression


class ImportExpression(ValueObject):
    """
    A user-submitted expression describing an import or set of imports.

    The importer and imported expressions are both ModuleExpressions
    (see ModuleExpression for details).
    """

    importer: ModuleExpression
    imported: ModuleExpression

    def has_wildcard_expression(self) -> bool:
        return self.imported.has_wildcard_expression() or self.importer.has_wildcard_expression()

    def __str__(self) -> str:
        return "{} -> {}".format(self.importer.expression, self.imported.expression)
