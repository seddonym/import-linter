from dataclasses import dataclass
from functools import cached_property
from pprint import pprint
from typing import Any, Optional
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


@dataclass(frozen=True)
class Cycle:
    members: tuple[str, ...]
    package_lvl_cycle: bool

    @cached_property
    def family(self) -> tuple[str, tuple[str, ...]]:
        return (
            self.parent,
            self.siblings
        )

    @cached_property
    def parent(self) -> str:
        parent = _longest_common_package(modules=self.members)
        # If there is no common package,
        # we assume that the cycle is formed between root packages
        if parent is None:
            parent = _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS

        return parent

    @cached_property
    def siblings(self) -> tuple[str, ...]:
        siblings_list: list[str] = []
        parent_nesting = self.parent.count(".")

        for member in self.members:
            if not _is_child(module=member, parent=self.parent):
                raise AcyclicContractError(
                    f"Member '{member}' is not a child of parent package '{self.parent}'."
                )

            sibling = ".".join(member.split(".")[: parent_nesting + 2])
            siblings_list.append(sibling)

        siblings_unique: list[str] = [siblings_list[0]]

        for sibling in siblings_list[1:]:
            if sibling != siblings_unique[-1]:
                siblings_unique.append(sibling)

        return tuple(siblings_unique)


class AcyclicContractError(Exception):
    pass


class AcyclicContract(Contract):
    """
    A contract that checks whether the dependency graph of modules (or packages)
    stick to an acyclic dependencies principle (ADP).
    It indicates that modules (or packages) dependencies form a directed acyclic graph (DAG).

    Package dependency between two modules is understood as a common package between the two
    modules, plus the first uncommon part of accordingly, the importer and the imported module eg.:
    - importer: "a.b.c.d.x"
    - imported: "a.b.e.f.z"
    - package dependency: ("a.b.c", "a.b.e")

    Configuration options:
        - packages: a list of packages to consider in the search for cycles. For each package,
            all its subpackages and modules will be considered in the search for cycles.
            If a package is a subpackage of another provided package, it will be ignored with a warning.
            E.g. if 'a.b' and 'a.b.c' are provided, 'a.b.c' will be ignored.
        - ignore_packages: a set of packages to ignore in the search for cycles.
            If a package is included in both "packages" and "ignore_packages", it will be ignored.
            Default is an empty set.
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True.
            Default is True.
        - max_cycles: limit a search for cycles.
            Default is 0 (no limit).

        ########## Example ##########

        Config:

        [importlinter]
        root_packages =
            django

        [importlinter:contract:1]
        name=Acyclic
        type=acyclic
        packages=
            django.contrib
        max_cycles=1

        Output:

        Acyclic
        -------

        Package django.contrib contains a dependency cycle:

        1. admin depends on auth:

            - django.contrib.admin -> django.contrib.admin.sites (l. 22)
            - django.contrib.admin.sites -> django.contrib.admin.forms (l. 354)
            - django.contrib.admin.forms -> django.contrib.auth.forms (l. 1)

        2. auth depends on admin:

            - django.contrib.auth.forms -> django.contrib.auth (l. 5)
            - django.contrib.auth.admin -> django.contrib.admin (l. 2)

        ########## End of example ##########

    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)
    max_cycles = fields.IntegerField(required=False, default=0)
    packages = fields.SetField(subfield=fields.StringField(), required=True)
    ignore_packages = fields.ListField(subfield=fields.StringField(), required=False, default=[])
    group_by_family = fields.BooleanField(required=False, default=False)

    _CYCLES_METADATA_KEY = "cycles"
    _IMPORT_GRAPH_METADATA_KEY = "import_graph"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        """
        Check the import graph for cyclic dependencies.
        """
        # Validate configuration
        if not self._consider_package_dependencies and self._group_by_family:
            msg = (
                "Configuration error: 'group_by_family' cannot be True if "
                "'consider_package_dependencies' is False."
            )
            raise AcyclicContractError(msg)

        for package in self._packages:
            if package == _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS:
                continue

            if not AcyclicContract._is_internal_module(graph=graph, package=package):
                msg = f"Package '{package}' is not an internal package."
                raise AcyclicContractError(msg)

        for ignore_package in (self._ignore_packages or set()):
            if not AcyclicContract._is_internal_module(graph=graph, package=ignore_package):
                msg = f"Ignore package '{ignore_package}' is not an internal package."
                raise AcyclicContractError(msg)

        if self._ignore_packages and _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS in self._ignore_packages:
            msg = f"Ignore package '{_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS}' cannot be used."
            raise AcyclicContractError(msg)
        # Print configuration
        if verbose:
            configuration_heading_msg = [
                "CONFIG:\n",
                f"Consider package dependencies: {self._consider_package_dependencies}",
                f"Max cycles: {self._max_cycles}",
                f"Packages: {self._packages}",
                f"Ignore packages: {self._ignore_packages}",
            ]
            output.print_heading(text="\n".join(configuration_heading_msg), level=2)
        # Find cycles
        contract_metadata: dict[str, Any] = {}
        cycles: list[Cycle] = []
        unique_member_strings: set[str] = set()
        is_root_included = any(
            package == _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS for package in self._packages
        )

        for importer_module in sorted(graph.modules):
            if not AcyclicContract._is_internal_module(graph=graph, package=importer_module):
                continue

            cycle_members = graph.find_shortest_cycle(
                module=importer_module,
                as_package=self._consider_package_dependencies
            )

            if cycle_members is None:
                continue

            cycle = self._get_cycle(
                cycle_members=cycle_members,
                import_graph=graph
            )

            if not is_root_included and not any(
                _is_child(module=cycle.parent, parent=package) for package in self._packages
            ):
                if verbose:
                    output.print_warning(
                        text=(
                            f"\nSkipping cycle in parent '{cycle.parent}' as it is not in any of "
                            f"the packages {self._packages}."
                        )
                    )

                continue

            if self._ignore_packages is not None and any(
                _is_child(module=cycle.parent, parent=package) for package in self._ignore_packages
            ):
                if verbose:
                    output.print_warning(
                        text=(
                            f"\nSkipping cycle in parent '{cycle.parent}' as it is in "
                            f"the ignored packages {self._ignore_packages}."
                        )
                    )
                continue

            unique_member_string = str(cycle.members)

            if unique_member_string not in unique_member_strings:
                unique_member_strings.add(unique_member_string)
                cycles.append(cycle)
            else:
                if verbose:
                    output.print_warning(
                        text=f"\nSkipping already reported cycle:\n{' -> '.join(cycle.members)}"
                    )

                continue

            if verbose:
                warning_msg = (
                    f"\nFound cycle in a package {cycle.parent}, siblings: {cycle.siblings}, "
                    f"package_lvl_cycle: {cycle.package_lvl_cycle},\nmembers:\n{' -> '.join(cycle.members)}"
                )
                output.print_warning(text=warning_msg)

            if self._max_cycles is not None and len(cycles) == self._max_cycles:
                break
        # Print summary
        if verbose:
            summary_msg = self._get_cycles_summary_msg(cycles=cycles)
            output.print_warning(text=summary_msg)
        # Prepare result
        contract_check = ContractCheck(kept=len(cycles) == 0, metadata=contract_metadata)
        AcyclicContract._set_cycles_in_metadata(check=contract_check, cycles=cycles)
        AcyclicContract._set_graph_in_metadata(check=contract_check, import_graph=graph)
        return contract_check

    def render_broken_contract(self, check: ContractCheck) -> None:
        cycles = AcyclicContract._get_cycles_from_metadata(check=check)

        if not cycles:
            return

        if self._group_by_family:
            # keep only one cycle per family
            cycle_family_counts: dict[tuple[str, tuple[str, ...]], int] = {}
            reduced_cycles: list[Cycle] = []

            for cycle in cycles:
                if not cycle.package_lvl_cycle:
                    reduced_cycles.append(cycle)
                    continue

                if cycle.family not in cycle_family_counts:
                    cycle_family_counts[cycle.family] = 0
                    reduced_cycles.append(cycle)

                cycle_family_counts[cycle.family] += 1

            cycles = reduced_cycles
            # TODO(K4liber): remove debug print
            print(len(cycles))
            pprint(cycle_family_counts)

        import_graph = AcyclicContract._get_graph_from_metadata(check=check)
        # create sorted sections for rendering
        all_sections_sorted: list[tuple[Cycle, list[_CycleRenderingSection]]] = sorted([
            (cycle, _get_sibling_sections(cycle=cycle, consider_package_dependencies=self._consider_package_dependencies))
            for cycle in cycles
        ], key=lambda item: (sum(len(section.imports) for section in item[1]), len(item[1])))

        for cycle, sibiling_cycle_sections in all_sections_sorted:
            msg = (
                f"\nPackage {cycle.parent} contains a {'(package) ' if cycle.package_lvl_cycle else ''}"
                "dependency cycle:"
            )
            output.print_error(text=msg)

            for index_sibling, cycle_section in enumerate(sibiling_cycle_sections):
                output.print_error(
                    text=(
                        f"\n  {index_sibling + 1}. "
                        f"{_cut_module_ancestors(cycle_section.sibling_from, cycle.parent)} depends on "
                        f"{_cut_module_ancestors(cycle_section.sibling_to, cycle.parent)}:\n"
                    )
                )

                if not cycle_section.imports:
                    raise AcyclicContractError(
                        "No imports found between siblings in a cycle. This should not happen."
                        f" Sibling: {cycle_section.sibling_from}, dependent sibling: {cycle_section.sibling_to}."
                    )

                for importer, imported in cycle_section.imports:
                    import_details = import_graph.get_import_details(
                        importer=importer, imported=imported
                    )
                    line_number = import_details[0].get("line_number") if import_details else None

                    if line_number is None and not cycle.package_lvl_cycle:
                        raise AcyclicContractError(
                            "Line number is None. This should not happen on a module lvl cycle."
                            f" Importer: {importer}, Imported: {imported}."
                        )

                    if line_number is not None:
                        line_info = f"l. {line_number}"
                        output.print_error(text=f"      - {importer} -> {imported} ({line_info})")

        output.print_error(text="\n")

    @staticmethod
    def _is_internal_module(graph: ImportGraph, package: str) -> bool:
        return (
            bool(graph.find_matching_modules(expression=package)) and
            not graph.is_module_squashed(package)
        )

    def _get_cycles_summary_msg(self, cycles: list[Cycle]) -> str:
        number_of_package_lvl_cycles = len([cycle for cycle in cycles if cycle.package_lvl_cycle])
        number_of_module_lvl_cycles = len(cycles) - number_of_package_lvl_cycles
        cycles_type = (
            "dependency cycles" if self._consider_package_dependencies else "module level cycles"
        )
        summary_msg = (
            f"\nNumber of {cycles_type} found for a contract '{self.name}': {len(cycles)}\n"
            + (
                f"Package level cycles: {number_of_package_lvl_cycles}\n"
                if self._consider_package_dependencies
                else ""
            )
            + (
                f"Module level cycles: {number_of_module_lvl_cycles}\n"
                if self._consider_package_dependencies
                else ""
            )
            + (f"Limit: {self._max_cycles}\n" if self._max_cycles is not None else "")
        )
        return summary_msg

    def _get_cycle(
        self,
        cycle_members: tuple[str, ...],
        import_graph: ImportGraph
    ) -> Cycle:
        """Retrieves a cycle from cycle members.

        If there is at least one import missing between cycle members,
        it is considered a package level cycle.
        """
        package_lvl_cycle = False
        cycle_members = _get_reordered_cycle_members(cycle_members=list(cycle_members))

        for index, importer in enumerate(cycle_members[:-1]):
            imported = cycle_members[index + 1]

            if not import_graph.get_import_details(
                importer=importer, imported=imported
            ):
                package_lvl_cycle = True

        if import_graph.get_import_details(
            importer=cycle_members[-1], imported=cycle_members[0]
        ):
            package_lvl_cycle = True

        return Cycle(members=cycle_members, package_lvl_cycle=package_lvl_cycle)

    @cached_property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @cached_property
    def _group_by_family(self) -> bool:
        return str(self.group_by_family).lower() == "true"

    @cached_property
    def _max_cycles(self) -> Optional[int]:
        value_int = self.max_cycles.value
        return None if value_int < 1 else value_int

    @cached_property
    def _packages(self) -> set[str]:
        unique_packages: set[str] = set()
        all_packages: list[str] = sorted(
            {module for module in self.packages if module}, key=len  # type: ignore
        )

        if _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS in all_packages and len(all_packages) > 1:
            output.print_warning(
                text=(
                    f"Package '{_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS}' is provided together "
                    "with other packages. It will be the only considered package."
                )
            )
            unique_packages = {_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS}

        else:
            for package in all_packages:
                is_unique = True

                for existing in unique_packages:
                    if _is_child(module=package, parent=existing):
                        output.print_warning(
                            text=f"Skipping redundant package '{package}' "
                            f"as it is a child of already provided '{existing}'."
                        )
                        is_unique = False
                        break

                if not is_unique:
                    continue

                unique_packages.add(package)

        return unique_packages

    @cached_property
    def _ignore_packages(self) -> Optional[set[str]]:
        unique_ignore_packages: set[str] = set()
        all_ignore_packages: list[str] = sorted(
            {module for module in self.ignore_packages if module}, key=len  # type: ignore
        )

        for package in all_ignore_packages:
            is_unique = True

            for existing in unique_ignore_packages:
                if _is_child(module=package, parent=existing):
                    output.print_warning(
                        text=f"Skipping redundant ignore package '{package}' "
                        f"as it is a child of already provided '{existing}'."
                    )
                    is_unique = False
                    break

            if not is_unique:
                continue

            unique_ignore_packages.add(package)

        return unique_ignore_packages if unique_ignore_packages else None

    @staticmethod
    def _set_cycles_in_metadata(check: ContractCheck, cycles: list[Cycle]) -> None:
        check.metadata[AcyclicContract._CYCLES_METADATA_KEY] = cycles

    @staticmethod
    def _get_cycles_from_metadata(check: ContractCheck) -> list[Cycle]:
        return check.metadata.get(AcyclicContract._CYCLES_METADATA_KEY, [])

    @staticmethod
    def _set_graph_in_metadata(check: ContractCheck, import_graph: ImportGraph) -> None:
        check.metadata[AcyclicContract._IMPORT_GRAPH_METADATA_KEY] = import_graph

    @staticmethod
    def _get_graph_from_metadata(check: ContractCheck) -> ImportGraph:
        return check.metadata[AcyclicContract._IMPORT_GRAPH_METADATA_KEY]


_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS = "__root__"


@dataclass(frozen=True)
class _CycleRenderingSection:
    sibling_from: str
    sibling_to: str
    imports: list[tuple[str, str]]


def _get_sibling_sections(cycle: Cycle, consider_package_dependencies: bool) -> list[_CycleRenderingSection]:
    sibiling_sections: list[_CycleRenderingSection] = []
    last_member = 0

    for index_sibling, sibling in enumerate(cycle.siblings[:-1]):
        dependent_sibling = cycle.siblings[index_sibling + 1]
        imports_in_section: list[tuple[str, str]] = []

        for index_importer in range(last_member, len(cycle.members) - 1):
            importer = cycle.members[index_importer]
            imported = cycle.members[index_importer + 1]
            is_new_subsection = (
                _is_child(module=importer, parent=dependent_sibling) and
                not _is_child(module=imported, parent=dependent_sibling)
            )

            if is_new_subsection:
                last_member = index_importer
                break

            if consider_package_dependencies:
                # if we consider package dependencies,
                # we only include imports between the two siblings in the section
                is_import_between_siblings = (
                    _is_child(module=importer, parent=sibling) and
                    _is_child(module=imported, parent=dependent_sibling)
                )

                if is_import_between_siblings:
                    imports_in_section.append((importer, imported))
            else:
                imports_in_section.append((importer, imported))

        sibiling_sections.append(
            _CycleRenderingSection(
                sibling_from=sibling,
                sibling_to=dependent_sibling,
                imports=imports_in_section
            )
        )

    return sibiling_sections


def _get_reordered_cycle_members(cycle_members: list[str]) -> tuple[str, ...]:
    # reorder the cycle to start from the lexicographically smallest member
    min_member = min(cycle_members)
    min_index = cycle_members.index(min_member)
    sorted_members = cycle_members[min_index:] + cycle_members[:min_index] + [min_member]
    # remove duplicated modules placed next to each other
    unique_members: list[str] = [sorted_members[0]]

    for member in sorted_members[1:]:
        if member != unique_members[-1]:
            unique_members.append(member)

    return tuple(unique_members)


def _is_child(module: str, parent: str) -> bool:
    if parent == _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS:
        return True

    return module == parent or module.startswith(f"{parent}.")


def _cut_module_ancestors(module: str, package: str) -> str:
    if package == _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS:
        return module

    if module == package:
        return module.split(".")[-1]

    if _is_child(module=module, parent=package):
        last_ancestor = package.split(".")[-1]
        ancestors_to_cut = package.removesuffix(last_ancestor)
        return module.removeprefix(ancestors_to_cut)

    raise AcyclicContractError(f"Module '{module}' is not a child of parent package '{package}'.")


def _longest_common_package(modules: tuple[str, ...]) -> Optional[str]:
    module_lists = [module.split(".") for module in modules]
    index = 0

    for index, module_part in enumerate(module_lists[0]):
        for other_module in module_lists[1:]:
            if index + 1 > len(other_module) or module_part != other_module[index]:
                longest_common_package = ".".join(module_lists[0][:index])

                if longest_common_package == "":
                    return None
                else:
                    return longest_common_package

    sorted_modules = sorted(modules, key=len)
    return (
        sorted_modules[0]
        if all(_is_child(module=module, parent=sorted_modules[0]) for module in modules)
        else None
    )
