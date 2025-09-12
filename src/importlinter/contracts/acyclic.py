import copy
from dataclasses import dataclass
from typing import Any, Optional
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


@dataclass
class Cycle:
    members: tuple[str, ...]
    package_lvl_cycle: bool
    _parent: Optional[str] = None
    _siblings: Optional[tuple[str, ...]] = None

    @property
    def parent(self) -> str:
        if self._parent is None:

            parent = _longest_common_package(modules=self.members)
            # If there is no common package,
            # we assume that the cycle is formed between root packages
            if parent is None:
                parent = _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS

            self._parent = parent

        return self._parent

    @property
    def siblings(self) -> tuple[str, ...]:
        if self._siblings is None:

            siblings_list: list[str] = []
            parent_nesting = self.parent.count(".")

            for member in self.members:
                if member.startswith(self.parent) and member != self.parent:
                    sibiling = ".".join(member.split(".")[: parent_nesting + 2])
                    siblings_list.append(sibiling)
                else:
                    siblings_list.append(member.split(".")[0])

            siblings_unique: list[str] = [siblings_list[0]]

            for sibling in siblings_list[1:]:
                if sibling != siblings_unique[-1]:
                    siblings_unique.append(sibling)

            self._siblings = tuple(siblings_unique)

        return self._siblings


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

    Example output when the contract is broken:

    Package 'django' contains a module dependencies cycle:

        1. 'apps' depends on 'utils':
            - 'django.apps' -> 'django.apps.config' (l.1)
            - 'django.apps.config' -> 'django.utils.module_loading' (l.7)

        2. 'utils' depends on 'apps':
            - 'django.utils.module_loading' -> 'django.apps' (l.48)

    Configuration options (all options are optional):
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True.
        - max_cycles: limit a search for cycles.
            Default is 0 (no limit).
        - include_parents: a list of parent modules to include in the search for cycles. If the list
            is not empty, all packages that are not in the list will be excluded from the search.
            If not provided, all packages will be considered.
        ########## Example usage of include_parents ##########

        Config:

        [importlinter]
        root_packages =
            django

        [importlinter:contract:1]
        name=Acyclic
        type=acyclic
        consider_package_dependencies=true
        max_cycles=1
        include_parents=
            django.contrib

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
            - django.contrib.auth -> django.contrib.auth.admin (django.contrib.auth package dependency)  # noqa E501
            - django.contrib.auth.admin -> django.contrib.admin (l. 2)

        ########## End of include_parents example usage ##########
        - exclude_parents: a list of parent modules to exclude from the search for cycles.
            If a parent module is provided in both 'include_parents' and 'exclude_parents',
            it will be excluded from the search for cycles.

    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)
    max_cycles = fields.IntegerField(required=False, default=0)
    include_parents = fields.ListField(subfield=fields.StringField(), required=False, default=[])
    exclude_parents = fields.ListField(subfield=fields.StringField(), required=False, default=[])

    _CYCLE_FAMILIES_METADATA_KEY = "cycle_families"
    _IMPORT_GRAPH_METADATA_KEY = "import_graph"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        """
        Check the import graph for cyclic dependencies.
        """
        if verbose:
            configuration_heading_msg = [
                "CONFIG:\n",
                f"Consider package dependencies: {self._consider_package_dependencies}",
                f"Max cycles: {self._max_cycles}",
                f"Include parents: {self._include_parents}",
                f"Exclude parents: {self._exclude_parents}",
            ]
            output.print_heading(text="\n".join(configuration_heading_msg), level=2)

        contract_metadata: dict[str, Any] = {}
        package_to_origin_dependency: dict[tuple[str, str], tuple[str, str]] = {}

        if self._consider_package_dependencies:
            # If we consider package dependencies,
            # we need to expand the graph with the artificially created package dependencies.
            graph, package_to_origin_dependency = self._get_graph_including_package_dependencies(
                graph=graph
            )

        cycles: list[Cycle] = []
        unique_member_strings: set[str] = set()

        for importer_module in sorted(graph.modules):
            cycle_members = graph.find_shortest_cycle(
                module=importer_module,
                as_package=False,  # package dependencies are already added to the graph,
                # while turned on, we lose traceability of package dependencies
                # which are logged later for a better understanding of the cycles
            )

            if cycle_members is None:
                continue

            cycle = self._get_cycle(
                cycle_members=cycle_members,
                package_to_origin_dependency=package_to_origin_dependency,
            )

            if self._include_parents is not None and cycle.parent not in self._include_parents:
                continue

            if self._exclude_parents is not None and cycle.parent in self._exclude_parents:
                continue

            unique_member_string = str(cycle.members)

            if unique_member_string not in unique_member_strings:
                unique_member_strings.add(unique_member_string)
                cycles.append(cycle)
            else:
                if verbose:
                    output.print_warning(
                        text=f"Skipping already reported cycle:\n{' -> '.join(cycle.members)}"
                    )

                continue

            if verbose:
                warning_msg = f"Found cycle:\n{' -> '.join(cycle.members)}"
                output.print_warning(text=warning_msg)

            if self._max_cycles is not None and len(cycles) == self._max_cycles:
                break

        if verbose:
            summary_msg = self._get_cycles_summary_msg(cycles=cycles)
            output.print_warning(text=summary_msg)

        contract_check = ContractCheck(kept=len(cycles) == 0, metadata=contract_metadata)
        AcyclicContract._set_cycles_in_metadata(check=contract_check, cycles=cycles)
        AcyclicContract._set_graph_in_metadata(check=contract_check, import_graph=graph)
        return contract_check

    def render_broken_contract(self, check: ContractCheck) -> None:
        cycles = AcyclicContract._get_cycles_from_metadata(check=check)

        if not cycles:
            return

        import_graph = AcyclicContract._get_graph_from_metadata(check=check)

        for cycle in cycles:
            output.print_error(
                text=f"\nPackage {cycle.parent} contains a dependency cycle:"
            )
            index_sibling = 0
            sibling = cycle.siblings[index_sibling]
            dependent_sibling = cycle.siblings[index_sibling + 1]
            output.print_error(
                text=(
                    f"\n  {index_sibling + 1}. "
                    f"{_get_relative_module(sibling, cycle.parent)} depends on "
                    f"{_get_relative_module(dependent_sibling, cycle.parent)}:\n"
                )
            )

            for index_importer, importer in enumerate(cycle.members[:-1]):
                if not importer.startswith(sibling):
                    index_sibling += 1

                    if index_sibling + 1 < len(cycle.siblings):
                        sibling = cycle.siblings[index_sibling]
                        dependent_sibling = cycle.siblings[index_sibling + 1]
                        output.print_error(
                            text=(
                                f"\n  {index_sibling + 1}. "
                                f"{_get_relative_module(sibling, cycle.parent)} depends on "
                                f"{_get_relative_module(dependent_sibling, cycle.parent)}:\n"
                            )
                        )

                imported = cycle.members[index_importer + 1]
                import_details = import_graph.get_import_details(
                    importer=importer, imported=imported
                )
                line_number = import_details[0].get("line_number") if import_details else None

                if line_number is None and not cycle.package_lvl_cycle:
                    raise AcyclicContractError(
                        "Line number is None. This should not happen on a module lvl cycle."
                        f" Importer: {importer}, Imported: {imported}."
                    )

                if line_number is None:
                    dependency_sibling = sibling if imported.startswith(sibling) else dependent_sibling
                    line_info = f"{dependency_sibling} package dependency"
                else:
                    line_info = f"l. {line_number}"

                output.print_error(text=f"      - {importer} -> {imported} ({line_info})")
        
        output.print_error(text="\n")

    def _get_graph_including_package_dependencies(
        self, graph: ImportGraph
    ) -> tuple[ImportGraph, dict[tuple[str, str], tuple[str, str]]]:
        package_to_origin_dependency: dict[tuple[str, str], tuple[str, str]] = {}
        graph = copy.deepcopy(graph)
        already_added_package_dependencies: set[tuple[str, str]] = set()

        for importer_module in sorted(graph.modules):
            imported_modules = graph.find_modules_directly_imported_by(module=importer_module)

            for imported_module in sorted(imported_modules):
                package_dependency = _get_package_dependency(
                    importer=importer_module, imported=imported_module
                )

                if package_dependency is None:
                    continue

                if package_dependency in already_added_package_dependencies:
                    continue

                package_import_already_exists = (
                    graph.get_import_details(
                        importer=package_dependency[0],
                        imported=package_dependency[1],
                    )
                    != []
                )

                if package_import_already_exists:
                    continue

                graph.add_import(importer=package_dependency[0], imported=package_dependency[1])
                already_added_package_dependencies.add(package_dependency)
                package_to_origin_dependency[package_dependency] = (
                    importer_module,
                    imported_module,
                )

        return graph, package_to_origin_dependency

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
        package_to_origin_dependency: dict[tuple[str, str], tuple[str, str]],
    ) -> Cycle:
        """Retrieves a clean cycle taking into account package dependencies."""
        package_lvl_cycle = False

        if self._consider_package_dependencies:
            formatted_members: list[str] = []

            for index, member in enumerate(cycle_members[:-1]):
                package_dependency = (member, cycle_members[index + 1])
                origin_dependency = package_to_origin_dependency.get(package_dependency)

                if origin_dependency is not None:
                    if package_dependency[0] != origin_dependency[0]:
                        formatted_members.append(origin_dependency[0])
                        package_lvl_cycle = True
                    else:
                        formatted_members.append(origin_dependency[0])

                    if package_dependency[1] != origin_dependency[1]:
                        formatted_members.append(origin_dependency[1])
                        package_lvl_cycle = True
                    else:
                        formatted_members.append(origin_dependency[1])
                else:
                    if len(formatted_members) == 0:
                        formatted_members.append(package_dependency[0])
                    # could have been already added by the previous iteration
                    elif formatted_members[-1] != package_dependency[0]:
                        formatted_members.append(package_dependency[0])

                    formatted_members.append(package_dependency[1])
        else:
            formatted_members = list(cycle_members)

        members = _get_clean_cycle_members(cycle_members=formatted_members)
        return Cycle(members=tuple(members), package_lvl_cycle=package_lvl_cycle)

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @property
    def _max_cycles(self) -> Optional[int]:
        value_int = self.max_cycles.value
        return None if value_int < 1 else value_int

    @property
    def _include_parents(self) -> Optional[list[str]]:
        if not self.include_parents:
            return None

        return [module for module in self.include_parents if module]  # type: ignore

    @property
    def _exclude_parents(self) -> Optional[list[str]]:
        if not self.exclude_parents:
            return None

        return [module for module in self.exclude_parents if module]  # type: ignore

    @staticmethod
    def _set_cycles_in_metadata(check: ContractCheck, cycles: list[Cycle]) -> None:
        check.metadata[AcyclicContract._CYCLE_FAMILIES_METADATA_KEY] = cycles

    @staticmethod
    def _get_cycles_from_metadata(check: ContractCheck) -> list[Cycle]:
        return check.metadata.get(AcyclicContract._CYCLE_FAMILIES_METADATA_KEY, [])

    @staticmethod
    def _set_graph_in_metadata(check: ContractCheck, import_graph: ImportGraph) -> None:
        check.metadata[AcyclicContract._IMPORT_GRAPH_METADATA_KEY] = import_graph

    @staticmethod
    def _get_graph_from_metadata(check: ContractCheck) -> ImportGraph:
        return check.metadata[AcyclicContract._IMPORT_GRAPH_METADATA_KEY]


_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS = "__root__"


def _get_clean_cycle_members(cycle_members: list[str]) -> tuple[str, ...]:
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


def _get_relative_module(module: str, parent: str) -> str:
    if parent == _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS:
        return module

    if module == parent:
        return ""

    if module.startswith(f"{parent}."):
        return module.removeprefix(f"{parent}.")

    raise AcyclicContractError(f"Module '{module}' is not a child of parent package '{parent}'.")


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

    return None


def _get_package_dependency(importer: str, imported: str) -> Optional[tuple[str, str]]:
    """
    Get the package dependency between two modules.

    The function checks if there is a common package between the two modules.
    If there is a common package, it returns the package dependency as a tuple of two strings.
    If the common package is the same as the importer or imported module, it returns None.
    """
    common_package = _longest_common_package(modules=(importer, imported))
    # If there is no common package, we check if root packages make package dependency
    if common_package is None:
        imported_split = imported.split(".")
        importer_split = importer.split(".")

        if len(imported_split) == 1 and len(importer_split) == 1:
            return None
        else:
            package_dependency = importer_split[0], imported_split[0]

            if package_dependency[0] == package_dependency[1]:
                return None

            return package_dependency

    if common_package == importer or common_package == imported:
        return None

    importer_reduced = importer.removeprefix(f"{common_package}.")
    imported_reduced = imported.removeprefix(f"{common_package}.")
    importer_package = f"{common_package}.{importer_reduced.split('.')[0]}"
    imported_package = f"{common_package}.{imported_reduced.split('.')[0]}"
    package_dependency = (importer_package, imported_package)

    if package_dependency == (importer, imported) or importer_package == imported_package:
        return None

    return package_dependency
