import copy
from dataclasses import dataclass
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


class AcyclicContractError(Exception):
    pass


def _longest_common_package(modules: tuple[str, ...]) -> str:
    parents: list[str] = []

    for module in sorted(modules, key=lambda x: len(x)):
        module_parent = ".".join(module.split(".")[:-1])
        parents.append(module_parent if module_parent != "" else module)

    longest_common_package = parents[0]
    longest_common_package_length = len(longest_common_package)
    current_length = longest_common_package_length

    for parent in parents[1:]:
        current_length = min(longest_common_package_length, len(parent))
        while current_length > 0 and longest_common_package[0:current_length] != parent[0:current_length]:
            current_length = current_length - 1

            if current_length == 0:
                raise AcyclicContractError(f"No common package for the provided modules: {modules}")

    return longest_common_package[0:current_length]


def _get_package_dependency(importer: str, imported: str) -> tuple[str, str] | None:
    try:
        common_package = _longest_common_package(modules=(importer, imported))
    except AcyclicContractError:
        return None

    if common_package == importer or common_package == imported:
        return None

    importer_reduced = importer.removeprefix(f"{common_package}.")
    imported_reduced = imported.removeprefix(f"{common_package}.")
    importer_package = f"{common_package}.{importer_reduced.split('.')[0]}"
    imported_package = f"{common_package}.{imported_reduced.split('.')[0]}"

    if (importer, imported) == (importer_package, imported_package):
        return None
    
    return (importer_package, imported_package)


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
    _family_key: CyclesFamilyKey | None = None

    @property
    def family_key(self) -> CyclesFamilyKey:
        if self._family_key is not None:
            return self._family_key

        parent = _longest_common_package(modules=self.members)
        sibilings_set: set[str] = set()
        parent_nesting = parent.count(".")

        for member in self.members:
            if member.startswith(parent) and member != parent:
                sibiling = ".".join(member.split(".")[:parent_nesting + 2])
                sibilings_set.add(sibiling)

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

    The acyclic dependencies principle (ADP) is a software design principle defined by 
    Robert C. Martin that states that "the dependency graph of packages or components should have no cycles".
    This implies that the dependencies form a directed acyclic graph (DAG).

    The found cycles are grouped into cycle families. Cycle family aggregates all cycles that have the same 
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

    Configuration options:
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True. (Optional.)
        - max_cycles_families: stop searching for cycles after the provided number of cycles families
            have been found.
    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)
    max_cycle_families = fields.StringField(required=False, default="0")

    _CYCLE_FAMILIES_METADATA_KEY = "cycle_families"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        # If we consider package dependencies, we need to expand the graph with the artificialy created imports 
        # from importer module ancestors to imported module ancestors. It allows to mimic package dependencies.
        if verbose:
            # TODO(K4liber): those should not be print_heading
            output.print_heading(text=f"Consider package dependencies: {self._consider_package_dependencies}", level=1)
            output.print_heading(text=f"Max cycle families: {self._max_cycles_families}", level=1)

        if self._consider_package_dependencies:
            graph = copy.deepcopy(graph)
            _already_added_package_dependencies: set[tuple[str, str]] = set()

            for importer_module in sorted(graph.modules):
                imported_modules = graph.find_modules_directly_imported_by(module=importer_module)

                for imported_module in sorted(imported_modules):
                    package_dependency = _get_package_dependency(importer=importer_module, imported=imported_module)

                    if package_dependency is None or package_dependency in _already_added_package_dependencies:
                        continue

                    if verbose:
                        # TODO(K4liber): this should not be print_heading
                        output.print_heading(
                            text=f"Adding package dependency ({package_dependency[0]} -> {package_dependency[1]}) "
                                 f"based on import ({importer_module} -> {imported_module})",
                            level=1
                        )
                    
                    importer_package, imported_module = package_dependency
                    graph.add_import(
                        importer=importer_package,
                        imported=imported_module
                    )
                    _already_added_package_dependencies.add(package_dependency)

        family_key_to_cycles: dict[CyclesFamilyKey, list[Cycle]] = {}

        for importer_module in graph.modules:
            cycle_members = graph.find_shortest_cycle(
                module=importer_module,
                as_package=True
            )

            if cycle_members is None:
                continue

            if verbose:
                output.print_error(text=f"Cycle found in module '{importer_module}': {cycle_members}")

            cycle = Cycle(members=cycle_members)

            if cycle.family_key not in family_key_to_cycles:
                family_key_to_cycles[cycle.family_key] = []

            family_key_to_cycles[cycle.family_key].append(cycle)

            if self._max_cycles_families is not None and len(family_key_to_cycles) == self._max_cycles_families:
                break

        cycles_families = [
            CyclesFamily(key=key, cycles=cycles)
            for key, cycles in family_key_to_cycles.items()
        ]
        contract_check = ContractCheck(kept=len(cycles_families) == 0, metadata={})
        AcyclicContract._set_cycles_in_metadata(check=contract_check, cycle_families=cycles_families)
        return contract_check

    def render_broken_contract(self, check: ContractCheck) -> None:
        cycle_families = AcyclicContract._get_cycles_from_metadata(check=check)

        if not cycle_families:
            return

        for cycle_family in cycle_families:
            output.print_error(
                text=f">>>> Cycles family for parent module '{cycle_family.key.parent}'"
            )
            output.print_error(text=f"\nSibilings:\n{cycle_family.key.get_siblings_format()}")
            output.print_error(text=f"\nNumber of cycles: {len(cycle_family.cycles)}\n")

            for index, cycle in enumerate(cycle_family.cycles, start=1):
                output.print_error(text=f"Cycle {index}:\n\n{cycle.get_members_format()}\n")

            output.print_error(text=f"<<<< Cycles family for parent module '{cycle_family.key.parent}'\n")
        
        summary_msg = f"Acyclic contract broken. Number of cycle families found: {len(cycle_families)}"

        if self._max_cycles_families is not None:
            summary_msg += f" (limit = {self._max_cycles_families})"

        output.print_error(text=summary_msg + "\n")

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

    @property
    def _max_cycles_families(self) -> int | None:
        value_int = int(str(self.max_cycle_families))
        return None if value_int < 1 else value_int

    @staticmethod
    def _get_module_ancestors(module: str) -> list[str]:
        module_ancestors: list[str] = []
        module_split = module.split(".")
        del module_split[-1]

        while module_split:
            module_ancestors.append(".".join(module_split))
            del module_split[-1]

        return module_ancestors

    @staticmethod
    def _set_cycles_in_metadata(check: ContractCheck, cycle_families: list[CyclesFamily]) -> None:
        check.metadata[AcyclicContract._CYCLE_FAMILIES_METADATA_KEY] = cycle_families

    @staticmethod
    def _get_cycles_from_metadata(check: ContractCheck) -> list[CyclesFamily]:
        return check.metadata.get(AcyclicContract._CYCLE_FAMILIES_METADATA_KEY, [])
