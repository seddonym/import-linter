from __future__ import annotations

import ast
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from grimp import ImportGraph

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import module_expressions_to_modules
from importlinter.domain.imports import Module, ModuleExpression

_SELF_OR_CLS = frozenset({"self", "cls"})


@dataclass(frozen=True, order=True)
class UnusedPublicSymbol:
    symbol: str
    defining_module: str
    line_number: int
    line_contents: str


@dataclass(frozen=True)
class _Definition:
    name: str
    line_number: int


class UnusedPublicSymbolsContract(Contract):
    """
    Flag public module-level names that have no in-package users and are not exported.

    A public ``connect()`` with no importers inside the package is not automatically
    ``_connect``. Callers outside the package may still use it. Require ``_`` only when
    all of these hold: the name is not in a static ``__all__`` (unless ``respect_all``
    is false); the defining module is not listed in ``public_modules``; no other
    package module references it.

    Import Linter's graph is module-level. This contract uses that graph for the set of
    in-scope modules, then scans each module's AST. Dynamic ``__all__``, ``getattr``,
    ``importlib``, and similar cases are treated conservatively: if a name cannot be
    shown to be unused, it is not reported. This is VIS002 only. It does not flag
    private names referenced from another module.
    """

    type_name = "unused_public_symbols"

    public_modules = fields.SetField(subfield=fields.ModuleExpressionField(), required=False)
    respect_all = fields.BooleanField(required=False, default=True)
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore[arg-type]
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore[arg-type]
        )

        in_scope = self._in_scope_modules(graph)
        public_module_names = self._public_module_names(graph)
        definitions = self._collect_definitions(in_scope, verbose)
        used = self._collect_used_symbols(in_scope, graph, definitions, verbose)
        violations = self._unused_public_symbols(in_scope, definitions, used, public_module_names)

        return ContractCheck(
            kept=not violations,
            warnings=warnings,
            metadata={"violations": violations},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        violations: list[UnusedPublicSymbol] = check.metadata["violations"]
        for violation in violations:
            qualified = f"{violation.defining_module}.{violation.symbol}"
            output.print_error(
                f"Public symbol {qualified} has no in-package users and is not exported:",
                bold=True,
            )
            output.new_line()
            output.print_error(
                f"-   {violation.defining_module}:{violation.line_number}: "
                f"{violation.line_contents}",
                bold=False,
            )
            output.new_line()

    def _in_scope_modules(self, graph: ImportGraph) -> dict[str, Path]:
        root_packages = [Module(name) for name in self.session_options["root_packages"]]
        located: dict[str, Path] = {}
        for module_name in sorted(graph.modules):
            module = Module(module_name)
            if not any(module.is_in_package(root) for root in root_packages):
                continue
            filename = _module_filename(module_name)
            if filename is not None:
                located[module_name] = filename
        return located

    def _public_module_names(self, graph: ImportGraph) -> set[str]:
        expressions = self.public_modules
        if not expressions:
            return set()
        return {
            module.name
            for module in module_expressions_to_modules(
                graph=graph,
                expressions=cast(set[ModuleExpression], expressions),
                as_packages=False,
            )
        }

    def _collect_definitions(
        self, in_scope: dict[str, Path], verbose: bool
    ) -> dict[str, list[_Definition]]:
        definitions: dict[str, list[_Definition]] = {}
        for module_name, filename in in_scope.items():
            output.verbose_print(verbose, f"Scanning definitions in {module_name}...")
            tree = _parse_python(filename)
            if tree is None:
                continue
            definitions[module_name] = _module_level_definitions(tree)
        return definitions

    def _collect_used_symbols(
        self,
        in_scope: dict[str, Path],
        graph: ImportGraph,
        definitions: dict[str, list[_Definition]],
        verbose: bool,
    ) -> set[tuple[str, str]]:
        graph_modules = set(graph.modules)
        used: set[tuple[str, str]] = set()
        defined_names = {
            (module_name, definition.name)
            for module_name, module_definitions in definitions.items()
            for definition in module_definitions
        }

        for importer, filename in in_scope.items():
            output.verbose_print(verbose, f"Scanning references in {importer}...")
            tree = _parse_python(filename)
            if tree is None:
                continue
            aliases = _imported_module_aliases(tree, importer, filename, graph_modules)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    used.update(
                        self._uses_from_import_from(
                            node=node,
                            importer=importer,
                            filename=filename,
                            graph_modules=graph_modules,
                            definitions=definitions,
                            defined_names=defined_names,
                        )
                    )
                elif isinstance(node, ast.Attribute):
                    use = self._use_from_attribute(
                        node=node,
                        importer=importer,
                        graph_modules=graph_modules,
                        aliases=aliases,
                        defined_names=defined_names,
                    )
                    if use is not None:
                        used.add(use)

        return used

    def _uses_from_import_from(
        self,
        node: ast.ImportFrom,
        importer: str,
        filename: Path,
        graph_modules: set[str],
        definitions: dict[str, list[_Definition]],
        defined_names: set[tuple[str, str]],
    ) -> set[tuple[str, str]]:
        source_module = _resolve_import_from_module(importer, filename, node)
        if source_module is None or source_module not in graph_modules:
            return set()
        if source_module == importer:
            return set()

        uses: set[tuple[str, str]] = set()
        for alias in node.names:
            if alias.name == "*":
                for definition in definitions.get(source_module, []):
                    uses.add((source_module, definition.name))
                continue
            imported_as_module = f"{source_module}.{alias.name}" if source_module else alias.name
            if imported_as_module in graph_modules:
                continue
            if (source_module, alias.name) in defined_names:
                uses.add((source_module, alias.name))
        return uses

    def _use_from_attribute(
        self,
        node: ast.Attribute,
        importer: str,
        graph_modules: set[str],
        aliases: dict[str, str],
        defined_names: set[tuple[str, str]],
    ) -> tuple[str, str] | None:
        parts = _attribute_root_parts(node.value)
        if parts is None or parts[0] in _SELF_OR_CLS:
            return None
        defining_module = _resolve_attribute_module(parts, aliases, graph_modules)
        if defining_module is None or defining_module == importer:
            return None
        if (defining_module, node.attr) not in defined_names:
            return None
        return (defining_module, node.attr)

    def _unused_public_symbols(
        self,
        in_scope: dict[str, Path],
        definitions: dict[str, list[_Definition]],
        used: set[tuple[str, str]],
        public_module_names: set[str],
    ) -> list[UnusedPublicSymbol]:
        respect_all: bool = self.respect_all  # type: ignore[assignment]
        violations: list[UnusedPublicSymbol] = []
        for module_name, module_definitions in definitions.items():
            if module_name in public_module_names:
                continue
            filename = in_scope[module_name]
            tree = _parse_python(filename)
            if tree is None:
                continue
            source_lines = filename.read_text(encoding="utf-8").splitlines()
            exported = _exported_names(tree) if respect_all else set()
            if exported is None:
                continue
            for definition in module_definitions:
                if not _is_public_symbol(definition.name):
                    continue
                if definition.name in exported:
                    continue
                if (module_name, definition.name) in used:
                    continue
                violations.append(
                    UnusedPublicSymbol(
                        symbol=definition.name,
                        defining_module=module_name,
                        line_number=definition.line_number,
                        line_contents=_line_contents(source_lines, definition.line_number),
                    )
                )
        return sorted(violations)


def _is_public_symbol(name: str) -> bool:
    return not name.startswith("_")


def _module_filename(module_name: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None
    if spec is None or spec.origin in (None, "built-in", "frozen"):
        return None
    origin = Path(spec.origin)
    if origin.suffix != ".py":
        return None
    return origin


def _parse_python(filename: Path) -> ast.AST | None:
    try:
        return ast.parse(filename.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _module_level_definitions(tree: ast.AST) -> list[_Definition]:
    definitions: list[_Definition] = []
    body = cast(list[ast.stmt], getattr(tree, "body", []))
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(_Definition(name=node.name, line_number=node.lineno))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    definitions.append(_Definition(name=target.id, line_number=node.lineno))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            definitions.append(_Definition(name=node.target.id, line_number=node.lineno))
    return definitions


def _exported_names(tree: ast.AST) -> set[str] | None:
    """
    Return names listed in a static ``__all__``.

    An empty set means the module has no ``__all__``. ``None`` means ``__all__``
    is present but not a list or tuple of string literals, so every public name
    in the module is treated as exported.
    """
    found = False
    names: set[str] = set()
    body = cast(list[ast.stmt], getattr(tree, "body", []))
    for node in body:
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ):
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "__all__":
                value = node.value
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
        ):
            return None
        if value is None:
            continue
        parsed = _string_literals(value)
        if parsed is None:
            return None
        found = True
        names = parsed
    if not found:
        return set()
    return names


def _string_literals(node: ast.AST) -> set[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return None
    names: set[str] = set()
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            names.add(element.value)
        else:
            return None
    return names


def _is_package_file(filename: Path) -> bool:
    return filename.name == "__init__.py"


def _package_for_relative_import(module_name: str, filename: Path) -> str:
    if _is_package_file(filename):
        return module_name
    if "." not in module_name:
        return ""
    return module_name.rsplit(".", 1)[0]


def _resolve_import_from_module(
    current_module: str, filename: Path, node: ast.ImportFrom
) -> str | None:
    if node.level == 0:
        return node.module

    package = _package_for_relative_import(current_module, filename)
    if node.level > 1:
        parts = package.split(".") if package else []
        drop = node.level - 1
        if drop > len(parts):
            return None
        package = ".".join(parts[:-drop])
    if node.module:
        return f"{package}.{node.module}" if package else node.module
    return package or None


def _imported_module_aliases(
    tree: ast.AST,
    current_module: str,
    filename: Path,
    graph_modules: set[str],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                bound = alias.name if alias.asname else alias.name.split(".", 1)[0]
                aliases[local] = bound
        elif isinstance(node, ast.ImportFrom):
            source = _resolve_import_from_module(current_module, filename, node)
            if source is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                imported_module = f"{source}.{alias.name}" if source else alias.name
                if imported_module in graph_modules:
                    aliases[local] = imported_module
    return aliases


def _attribute_root_parts(node: ast.AST) -> list[str] | None:
    current: ast.AST = node
    if isinstance(current, ast.Call):
        current = current.func
    parts: list[str] = []
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
        if isinstance(current, ast.Call):
            current = current.func
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return parts
    return None


def _resolve_attribute_module(
    parts: list[str], aliases: dict[str, str], graph_modules: set[str]
) -> str | None:
    first = aliases.get(parts[0], parts[0])
    candidate_parts = [first, *parts[1:]]
    for end in range(len(candidate_parts), 0, -1):
        candidate = ".".join(candidate_parts[:end])
        if candidate in graph_modules:
            return candidate
    return None


def _line_contents(source_lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(source_lines):
        return source_lines[lineno - 1].strip()
    return ""
