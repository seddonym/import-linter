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
from importlinter.domain.imports import Module

_SELF_OR_CLS = frozenset({"self", "cls"})


@dataclass(frozen=True, order=True)
class PrivateSymbolReference:
    symbol: str
    defining_module: str
    importer: str
    line_number: int
    line_contents: str


class SymbolVisibilityContract(Contract):
    """
    Flag private (``_``-prefixed) symbols that are referenced from another module.

    Import Linter's graph is module-level. This contract therefore uses that graph for
    the set of in-scope modules and for ``ignore_imports``, then scans each module's AST
    for symbol-level references. Dunder names are ignored. Importing a private *module*
    is out of scope (use a protected contract). Cross-module use of a class or instance
    attribute is also out of scope.

    This is VIS001 only. It does not infer that unused public names should be private.
    """

    type_name = "symbol_visibility"

    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore[arg-type]
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore[arg-type]
        )

        in_scope = self._in_scope_modules(graph)
        definitions = self._collect_private_definitions(in_scope, verbose)
        violations = self._collect_references(in_scope, graph, definitions, verbose)

        return ContractCheck(
            kept=not violations,
            warnings=warnings,
            metadata={"violations": violations},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        violations: list[PrivateSymbolReference] = check.metadata["violations"]
        for violation in violations:
            qualified = f"{violation.defining_module}.{violation.symbol}"
            output.print_error(
                f"Private symbol {qualified} is referenced from another module:",
                bold=True,
            )
            output.new_line()
            output.print_error(
                f"-   {violation.importer}:{violation.line_number}: {violation.line_contents}",
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

    def _collect_private_definitions(
        self, in_scope: dict[str, Path], verbose: bool
    ) -> dict[tuple[str, str], None]:
        definitions: dict[tuple[str, str], None] = {}
        for module_name, filename in in_scope.items():
            output.verbose_print(verbose, f"Scanning definitions in {module_name}...")
            tree = _parse_python(filename)
            if tree is None:
                continue
            for name in _module_level_names(tree):
                if _is_private_symbol(name):
                    definitions[(module_name, name)] = None
        return definitions

    def _collect_references(
        self,
        in_scope: dict[str, Path],
        graph: ImportGraph,
        definitions: dict[tuple[str, str], None],
        verbose: bool,
    ) -> list[PrivateSymbolReference]:
        graph_modules = set(graph.modules)
        violations: list[PrivateSymbolReference] = []
        source_lines_by_module: dict[str, list[str]] = {}

        for importer, filename in in_scope.items():
            output.verbose_print(verbose, f"Scanning references in {importer}...")
            tree = _parse_python(filename)
            if tree is None:
                continue
            source_lines = filename.read_text(encoding="utf-8").splitlines()
            source_lines_by_module[importer] = source_lines
            aliases = _imported_module_aliases(tree, importer, filename, graph_modules)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    violations.extend(
                        self._violations_from_import_from(
                            node=node,
                            importer=importer,
                            filename=filename,
                            graph=graph,
                            graph_modules=graph_modules,
                            definitions=definitions,
                            source_lines=source_lines,
                        )
                    )
                elif isinstance(node, ast.Attribute) and _is_private_symbol(node.attr):
                    violation = self._violation_from_attribute(
                        node=node,
                        importer=importer,
                        graph=graph,
                        graph_modules=graph_modules,
                        aliases=aliases,
                        definitions=definitions,
                        source_lines=source_lines,
                    )
                    if violation is not None:
                        violations.append(violation)

        return sorted(set(violations))

    def _violations_from_import_from(
        self,
        node: ast.ImportFrom,
        importer: str,
        filename: Path,
        graph: ImportGraph,
        graph_modules: set[str],
        definitions: dict[tuple[str, str], None],
        source_lines: list[str],
    ) -> list[PrivateSymbolReference]:
        source_module = _resolve_import_from_module(importer, filename, node)
        if source_module is None or source_module not in graph_modules:
            return []
        if source_module == importer:
            return []
        if not graph.direct_import_exists(importer=importer, imported=source_module):
            return []

        violations: list[PrivateSymbolReference] = []
        for alias in node.names:
            if alias.name == "*":
                continue
            if not _is_private_symbol(alias.name):
                continue
            imported_as_module = f"{source_module}.{alias.name}" if source_module else alias.name
            if imported_as_module in graph_modules:
                continue
            if (source_module, alias.name) not in definitions:
                continue
            violations.append(
                PrivateSymbolReference(
                    symbol=alias.name,
                    defining_module=source_module,
                    importer=importer,
                    line_number=node.lineno,
                    line_contents=_line_contents(source_lines, node.lineno),
                )
            )
        return violations

    def _violation_from_attribute(
        self,
        node: ast.Attribute,
        importer: str,
        graph: ImportGraph,
        graph_modules: set[str],
        aliases: dict[str, str],
        definitions: dict[tuple[str, str], None],
        source_lines: list[str],
    ) -> PrivateSymbolReference | None:
        parts = _attribute_root_parts(node.value)
        if parts is None or parts[0] in _SELF_OR_CLS:
            return None
        defining_module = _resolve_attribute_module(parts, aliases, graph_modules)
        if defining_module is None or defining_module == importer:
            return None
        if not graph.direct_import_exists(importer=importer, imported=defining_module):
            return None
        if (defining_module, node.attr) not in definitions:
            return None
        return PrivateSymbolReference(
            symbol=node.attr,
            defining_module=defining_module,
            importer=importer,
            line_number=node.lineno,
            line_contents=_line_contents(source_lines, node.lineno),
        )


def _is_private_symbol(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__")


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


def _module_level_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    body = cast(list[ast.stmt], getattr(tree, "body", []))
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
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
