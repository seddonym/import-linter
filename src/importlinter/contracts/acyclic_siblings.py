from __future__ import annotations
import grimp
from importlinter.application import rendering
import dataclasses
from importlinter.configuration import settings
from collections.abc import Set, Mapping
from typing import cast
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import module_expressions_to_modules
from importlinter.domain import fields
from importlinter.domain.imports import ModuleExpression
from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from dataclasses import dataclass

DEFAULT_DEPTH = 10
MAX_DEPENDENCIES_TO_RENDER = 5

# (importer, imported)
Import = tuple[str, str]


@dataclass(frozen=True, order=True)
class PackageSummary:
    package: str
    dependencies: Set[Dependency]


@dataclass(frozen=True, order=True)
class Dependency:
    downstream: str
    upstream: str
    num_imports: int


class AcyclicSiblingsContract(Contract):
    type_name = "acyclic_siblings"

    ancestors = fields.SetField(subfield=fields.ModuleExpressionField())
    depth = fields.IntegerField(minimum=0, default=DEFAULT_DEPTH)
    skip_descendants = fields.SetField(subfield=fields.ModuleExpressionField(), required=False)
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)

    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        self._check_no_ancestors_and_descendant_expressions_are_the_same()
        ancestors = self._get_concrete_ancestors(graph)
        descendants_to_skip = self._get_concrete_skipped_descendants(graph)
        depth: int = self.depth  # type: ignore

        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        cycle_breakers_by_package: dict[str, set[Import]] = {}

        for ancestor in sorted(ancestors):
            cycle_breakers_by_package_for_ancestor = self._nominate_cycle_breakers_recursively(
                graph, ancestor, depth, descendants_to_skip, verbose
            )
            cycle_breakers_by_package.update(cycle_breakers_by_package_for_ancestor)

        return ContractCheck(
            kept=not bool(cycle_breakers_by_package),
            warnings=warnings,
            metadata={
                "cycle_breakers_by_package": cycle_breakers_by_package,
                "summaries": self._build_summaries(cycle_breakers_by_package),
            },
        )

    def _check_no_ancestors_and_descendant_expressions_are_the_same(self) -> None:
        if self.skip_descendants and self.ancestors:
            overlap = cast(set, self.ancestors) & cast(set, self.skip_descendants)
            if overlap:
                first_overlap = sorted(list(overlap))[0]
                assert isinstance(first_overlap, ModuleExpression)
                if first_overlap.has_wildcard_expression():
                    raise ValueError(
                        f"Cannot skip descendant '{first_overlap}' as the same expression is in ancestors."
                    )
                else:
                    raise ValueError(f"Cannot skip '{first_overlap}' as it is also an ancestor.")

    def _get_concrete_ancestors(self, graph: grimp.ImportGraph) -> set[str]:
        ancestor_modules = module_expressions_to_modules(
            graph,
            sorted(self.ancestors),  # type: ignore
            raise_if_unmatched=True,
        )
        ancestors = {m.name for m in ancestor_modules}

        return ancestors

    def _get_concrete_skipped_descendants(self, graph: grimp.ImportGraph) -> set[str]:
        if self.skip_descendants is None:
            return set()

        skipped = module_expressions_to_modules(
            graph,
            sorted(self.skip_descendants),  # type: ignore
            raise_if_unmatched=True,
        )
        return {m.name for m in skipped}

    def _nominate_cycle_breakers_recursively(
        self,
        graph: grimp.ImportGraph,
        ancestor: str,
        remaining_depth: int,
        descendants_to_skip: set[str],
        verbose: bool,
    ) -> dict[str, set[Import]]:
        cycle_breakers_by_package: dict[str, set[Import]] = {}
        children = graph.find_children(ancestor)
        if not children:
            # Stop drilling down.
            return cycle_breakers_by_package

        # Check for cycles, assuming there are at least two.
        # (You can't have a cycle with only one child.)
        if len(children) >= 2:
            output.verbose_print(
                verbose,
                f"Searching for cycles between children of {ancestor}...",
            )
            with settings.TIMER as timer:
                cycle_breakers = graph.nominate_cycle_breakers(ancestor)
            duration = rendering.format_duration(timer.duration_in_ms)
            if cycle_breakers:
                cycle_breakers_by_package[ancestor] = cycle_breakers
                num_cycle_breakers = len(cycle_breakers)
                pluralized_cycles = "cycle" if num_cycle_breakers == 1 else "cycles"
                output.verbose_print(
                    verbose, f"Found {num_cycle_breakers} {pluralized_cycles} in {duration}."
                )
            else:
                output.verbose_print(
                    verbose,
                    f"No cycles found ({duration}).",
                )

        if remaining_depth:
            for child in sorted(children - descendants_to_skip):
                if cycle_breakers_by_descendant := self._nominate_cycle_breakers_recursively(
                    graph, child, remaining_depth - 1, descendants_to_skip, verbose
                ):
                    cycle_breakers_by_package.update(cycle_breakers_by_descendant)

        return cycle_breakers_by_package

    def _build_summaries(
        self, cycle_breakers_by_package: Mapping[str, Set[Import]]
    ) -> set[PackageSummary]:
        summaries: set[PackageSummary] = set()
        for package, cycle_breakers in cycle_breakers_by_package.items():
            summaries.add(
                PackageSummary(package, self._build_dependencies(package, cycle_breakers))
            )
        return summaries

    def _build_dependencies(
        self, package: str, cycle_breakers: Set[Import]
    ) -> frozenset[Dependency]:
        dependencies_by_child_pairs: dict[Import, Dependency] = {}
        package_components = package.split(".")
        num_dependency_components = len(package_components) + 1
        for importer, imported in cycle_breakers:
            downstream_child = ".".join(importer.split(".")[:num_dependency_components])
            upstream_child = ".".join(imported.split(".")[:num_dependency_components])
            child_pair = (downstream_child, upstream_child)
            try:
                existing_dependency = dependencies_by_child_pairs[child_pair]
                dependency = dataclasses.replace(
                    existing_dependency, num_imports=existing_dependency.num_imports + 1
                )
            except KeyError:
                dependency = Dependency(
                    downstream=downstream_child,
                    upstream=upstream_child,
                    num_imports=1,
                )
            dependencies_by_child_pairs[child_pair] = dependency

        return frozenset(dependencies_by_child_pairs.values())

    def render_broken_contract(self, check: ContractCheck) -> None:
        for summary in sorted(check.metadata["summaries"]):
            output.print_error(f"No cycles are allowed in {summary.package}.")
            num_dependencies = len(summary.dependencies)
            pluralized_dependencies = "dependencies" if num_dependencies != 1 else "dependency"
            output.print_error(
                f"It could be made acyclic by removing {num_dependencies} {pluralized_dependencies}:"
            )
            output.new_line()

            for dependency in sorted(summary.dependencies)[:MAX_DEPENDENCIES_TO_RENDER]:
                relative_downstream = dependency.downstream.split(".")[-1]
                relative_upstream = dependency.upstream.split(".")[-1]
                pluralized_import = "imports" if dependency.num_imports != 1 else "import"
                output.print_error(
                    f"- .{relative_downstream} -> .{relative_upstream} ({dependency.num_imports} {pluralized_import})"
                )

            num_extra = max(len(summary.dependencies) - MAX_DEPENDENCIES_TO_RENDER, 0)
            if num_extra:
                output.print_error(f"(and {num_extra} more).")
            output.new_line()
