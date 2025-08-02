import copy
from dataclasses import dataclass
from typing import Any, Optional
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


_PARENT_PACKAGE_FOR_MULTIPLE_ROOTS = "__root__"


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


@dataclass(frozen=True)
class CyclesFamilyKey:
    parent: str
    sibilings: tuple[str, ...]

    def get_siblings_format(self) -> str:
        return "(\n  " + "\n  ".join(f"{sibling}" for sibling in self.sorted_siblings) + "\n)"

    @property
    def sorted_siblings(self) -> tuple[str, ...]:
        return tuple(sorted(self.sibilings))

    def __hash__(self) -> int:
        return hash((self.parent, self.sorted_siblings))


@dataclass(frozen=True)
class Cycle:
    members: tuple[str, ...]
    _family_key: Optional[CyclesFamilyKey] = None

    @property
    def family_key(self) -> CyclesFamilyKey:
        if self._family_key is not None:
            return self._family_key

        parent = _longest_common_package(modules=self.members)
        # If there is no common package, we assume that the cycle is formed between root packages
        if parent is None:
            parent = _PARENT_PACKAGE_FOR_MULTIPLE_ROOTS

        sibilings_set: set[str] = set()
        parent_nesting = parent.count(".")

        for member in self.members:
            if member.startswith(parent) and member != parent:
                sibiling = ".".join(member.split(".")[: parent_nesting + 2])
                sibilings_set.add(sibiling)
            else:
                sibilings_set.add(member.split(".")[0])

        sibilings = tuple(sorted(sibilings_set))
        return CyclesFamilyKey(parent=parent, sibilings=sibilings)

    def get_members_format(self) -> str:
        return "(\n -> " + "\n -> ".join(f"{member}" for member in self.members) + "\n)"


@dataclass(frozen=True)
class CyclesFamily:
    key: CyclesFamilyKey
    cycles: list[Cycle]


class AcyclicContract(Contract):
    """
    A contract that checks whether the dependency graph of modules (or packages)
    stick to an acyclic dependencies principle (ADP).

    ADP is a software design principle defined by
    Robert C. Martin that states that
    "the dependency graph of packages or components should have no cycles".
    This implies that the dependencies form a directed acyclic graph (DAG).

    The found cycles are grouped into cycle families.
    Cycle family aggregates all cycles that have the same
    parent package and the cycle is formed between a particular set of sibilings.
    The example of a cycles family inside django library:

    >>>> Cycles family for parent module 'django'

    Sibilings:
    (
      django.forms
      django.template
      django.utils
    )

    Number of cycles: 1

    Cycle 1:

    (
      -> django.utils.dates
      -> django.utils.translation
      -> django.template
      -> django.forms
      -> django.utils.dates
    )

    <<<< Cycles family for parent module 'django'

    Configuration options (all options are optional):
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True.
        - max_cycles_families: limit a search for cycles to the provided number of cycles families.
            The limited families are not guaranteed to be complete.
        - include_parents: a list of parent modules to include in the search for cycles.
        - exclude_parents: a list of parent modules to exclude from the search for cycles.

        Package dependency between two modules is understood
        as a common package between the two modules, plus the first uncommon part of accordingly,
        the importer and the imported module eg.:
        - importer: "a.b.c.d.x"
        - imported: "a.b.e.f.z"
        - package dependency: ("a.b.c", "a.b.e")

        If no 'include_parents' or 'exclude_parents' are provided, all modules will be considered.
        If a parent module is provided in both 'include_parents' and 'exclude_parents',
        it will be excluded from the search for cycles.

    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)
    max_cycle_families = fields.IntegerField(required=False, default=0)
    include_parents = fields.ListField(subfield=fields.StringField(), required=False, default=[])
    exclude_parents = fields.ListField(subfield=fields.StringField(), required=False, default=[])

    _CYCLE_FAMILIES_METADATA_KEY = "cycle_families"
    _PACKAGE_DEPENDENCY_METADATA_KEY = "package_dependencies"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        """
        Check the import graph for cyclic dependencies.
        """
        if verbose:
            configuration_heading_msg = [
                "CONFIG:\n",
                f"Consider package dependencies: {self._consider_package_dependencies}",
                f"Max cycle families: {self._max_cycles_families}",
                f"Include parents: {self._include_parents}",
                f"Exclude parents: {self._exclude_parents}",
            ]
            output.print_heading(text="\n".join(configuration_heading_msg), level=2)

        contract_metadata: dict[str, Any] = {}
        # If we consider package dependencies,
        # we need to expand the graph with the artificialy created package dependencies.
        if self._consider_package_dependencies:
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

                    graph.add_import(
                        importer=package_dependency[0], imported=package_dependency[1]
                    )
                    already_added_package_dependencies.add(package_dependency)
                    self._add_package_dependency(
                        metadata=contract_metadata,
                        origin_dependency=(importer_module, imported_module),
                        package_dependency=package_dependency,
                    )

        family_key_to_cycles: dict[CyclesFamilyKey, list[Cycle]] = {}

        for importer_module in sorted(graph.modules):
            cycle_members = graph.find_shortest_cycle(
                module=importer_module,
                as_package=False,  # package dependencies are already added to the graph,
                # while turned on, we lose traceability of package dependencies
                # which are logged later for a better understanding
            )

            if cycle_members is None:
                continue

            cycle = Cycle(members=cycle_members)

            if (
                self._include_parents is not None
                and cycle.family_key.parent not in self._include_parents
            ):
                continue

            if (
                self._exclude_parents is not None
                and cycle.family_key.parent in self._exclude_parents
            ):
                continue

            if verbose:
                cycle_members_str = "\n-> ".join(cycle_members)
                warning_msg = (
                    f"Found cycle for module "
                    f"'{importer_module}':{chr(10)}-> {cycle_members_str}{chr(10)}"
                )
                output.print_warning(text=warning_msg)

            if cycle.family_key not in family_key_to_cycles:
                family_key_to_cycles[cycle.family_key] = []

            family_key_to_cycles[cycle.family_key].append(cycle)

            if (
                self._max_cycles_families is not None
                and len(family_key_to_cycles) == self._max_cycles_families
            ):
                break

        cycles_families = [
            CyclesFamily(key=key, cycles=cycles) for key, cycles in family_key_to_cycles.items()
        ]
        contract_check = ContractCheck(kept=len(cycles_families) == 0, metadata=contract_metadata)
        AcyclicContract._set_cycles_in_metadata(
            check=contract_check, cycle_families=cycles_families
        )
        return contract_check

    @staticmethod
    def _add_package_dependency(
        metadata: dict[str, Any],
        origin_dependency: tuple[str, str],
        package_dependency: tuple[str, str],
    ) -> None:
        """
        Adds a package dependency to the contract check metadata.
        """
        if AcyclicContract._PACKAGE_DEPENDENCY_METADATA_KEY not in metadata:
            metadata[AcyclicContract._PACKAGE_DEPENDENCY_METADATA_KEY] = {}

        metadata[AcyclicContract._PACKAGE_DEPENDENCY_METADATA_KEY][
            package_dependency
        ] = origin_dependency

    @staticmethod
    def _get_origin_dependency(
        contract_check: ContractCheck, package_dependency: tuple[str, str]
    ) -> Optional[tuple[str, str]]:
        """
        Retrieves a package dependency from the contract check metadata.
        """
        return contract_check.metadata.get(
            AcyclicContract._PACKAGE_DEPENDENCY_METADATA_KEY, {}
        ).get(package_dependency, None)

    def render_broken_contract(self, check: ContractCheck) -> None:
        cycle_families = AcyclicContract._get_cycles_from_metadata(check=check)

        if not cycle_families:
            return

        number_of_family_package_dependencies = 0

        for cycle_family in cycle_families:
            output.print_error(
                text=f">>>> Cycles family for parent module '{cycle_family.key.parent}'"
            )
            output.print_error(text=f"\nSibilings:\n{cycle_family.key.get_siblings_format()}")
            output.print_error(text=f"\nNumber of cycles: {len(cycle_family.cycles)}\n")
            is_family_package_dependency = False

            for index, cycle in enumerate(cycle_family.cycles, start=1):
                cycle_formatted, is_package_dependency = self._get_cycle_formatted_for_logging(
                    cycle=cycle, contract_check=check
                )
                is_family_package_dependency = (
                    is_family_package_dependency or is_package_dependency
                )
                title = (
                    f"Cycle {index} (package dependency)"
                    if is_package_dependency
                    else f"Cycle {index}"
                )
                output.print_error(text=f"{title}:\n\n{cycle_formatted.get_members_format()}\n")

            number_of_family_package_dependencies += 1 if is_family_package_dependency else 0
            output.print_error(
                text=f"<<<< Cycles family for parent module '{cycle_family.key.parent}'\n"
            )

        summary_msg = (
            f"Number of cycle families found for a contract '{self.name}': {len(cycle_families)}"
        )

        if self._max_cycles_families is not None:
            summary_msg += f" (limit = {self._max_cycles_families})"

        if number_of_family_package_dependencies > 0:
            summary_msg += (
                "\nNumber of cycle families with package dependencies: "
                f"{number_of_family_package_dependencies}"
            )

        output.print_error(text=summary_msg + "\n")

    def _get_cycle_formatted_for_logging(
        self, cycle: Cycle, contract_check: ContractCheck
    ) -> tuple[Cycle, bool]:
        """
        Retrieves a formatted cycle for logging purposes.

        It is useful for a better understanding of package dependencies.
        """
        if self._consider_package_dependencies is False:
            return cycle, False

        formatted_members: list[str] = []
        is_package_dependency = False

        for index, member in enumerate(cycle.members[:-1]):
            package_dependency = (member, cycle.members[index + 1])
            origin_dependency = AcyclicContract._get_origin_dependency(
                contract_check=contract_check, package_dependency=package_dependency
            )

            if origin_dependency is not None:
                if package_dependency[0] != origin_dependency[0]:
                    formatted_members.append(
                        f"{package_dependency[0]} (full path: '{origin_dependency[0]}')"
                    )
                    is_package_dependency = True
                else:
                    formatted_members.append(origin_dependency[0])

                if package_dependency[1] != origin_dependency[1]:
                    formatted_members.append(
                        f"{package_dependency[1]} (full path: '{origin_dependency[1]}')"
                    )
                    is_package_dependency = True
                else:
                    formatted_members.append(origin_dependency[1])
            else:
                if len(formatted_members) == 0:
                    formatted_members.append(package_dependency[0])
                # could have been already added by the previous iteration
                elif formatted_members[-1] != package_dependency[0]:
                    formatted_members.append(package_dependency[0])

                formatted_members.append(package_dependency[1])

        return Cycle(members=tuple(formatted_members)), is_package_dependency

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @property
    def _max_cycles_families(self) -> Optional[int]:
        value_int = self.max_cycle_families.value
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
    def _set_cycles_in_metadata(check: ContractCheck, cycle_families: list[CyclesFamily]) -> None:
        check.metadata[AcyclicContract._CYCLE_FAMILIES_METADATA_KEY] = cycle_families

    @staticmethod
    def _get_cycles_from_metadata(check: ContractCheck) -> list[CyclesFamily]:
        return check.metadata.get(AcyclicContract._CYCLE_FAMILIES_METADATA_KEY, [])
