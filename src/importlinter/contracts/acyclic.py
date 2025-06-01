import copy
from dataclasses import dataclass
from grimp import ImportGraph
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.application import output
from importlinter.domain import fields


def _longest_common_package(modules: tuple[str, ...]) -> str:
    sorted_module_parents = [
        ".".join(module.split(".")[:-1])
        for module in sorted(modules, key=lambda x: len(x))
    ]
    first_module = sorted_module_parents[0]
    first_module_length = len(first_module)
    length = first_module_length

    for i in range(1, len(sorted_module_parents)):
        length = min(first_module_length, len(sorted_module_parents[i]))
        while length > 0 and first_module[0:length] != sorted_module_parents[i][0:length]:
            length = length - 1

            if length == 0:
                return ""

    return first_module[0:length]


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
    A contract that checks whether the dependency graph of modules forms a directed acyclic graph (DAG) structure.

    This contract verifies that the directed graph of module imports does not contain any cycles.
    A cycle in the graph implies that there is a circular dependency between modules, which
    violates the tree structure requirement.

    Configuration options:
        - consider_package_dependencies:  Whether to consider cyclic dependencies between packages.
            "True" or "true" will be treated as True. (Optional.)
    """

    type_name = "acyclic"

    consider_package_dependencies = fields.BooleanField(required=False, default=True)

    _CYCLE_FAMILIES_METADATA_KEY = "cycle_families"

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        family_key_to_cycles: dict[CyclesFamilyKey, list[Cycle]] = {}
        # If we consider package dependencies, we need to expand the graph
        if self._consider_package_dependencies:
            graph = copy.deepcopy(graph)

            for importer_module in graph.modules:
                importer_module_family = [importer_module] + self._get_module_ancestors(module=importer_module)
                imported_modules = graph.find_modules_directly_imported_by(module=importer_module)

                for imported_module in imported_modules:
                    imported_module_family = [imported_module] + self._get_module_ancestors(module=imported_module)

                    for imported_module_family_member in imported_module_family:
                        for importer_module_family_member in importer_module_family:
                            if importer_module_family_member.startswith(imported_module_family_member):
                                continue

                            graph.add_import(
                                importer=importer_module_family_member,
                                imported=imported_module_family_member
                            )

        for importer_module in graph.modules:
            cycle_members = graph.find_shortest_cycle(
                module=importer_module,
                as_package=True
            )

            if cycle_members:
                if verbose:
                    output.print_error(text=f"Cycle found in module '{importer_module}': {cycle_members}")

                cycle = Cycle(members=cycle_members)

                if cycle.family_key not in family_key_to_cycles:
                    family_key_to_cycles[cycle.family_key] = []

                family_key_to_cycles[cycle.family_key].append(cycle)

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

        output.print_error(text=f"Acyclic contract broken. Number of cycle families found: {len(cycle_families)}\n")

        for cycle_family in cycle_families:
            output.print_error(
                text=f">>>> Cycle family for parent module '{cycle_family.key.parent}'\n"
            )
            output.print_error(text=f"\nSibilings:\n{cycle_family.key.get_siblings_format()}\n")
            output.print_error(text=f"\nNumber of cycles: {len(cycle_family.cycles)}\n")

            for index, cycle in enumerate(cycle_family.cycles, start=1):
                output.print_error(text=f"Cycle {index}:\n\n{cycle.get_members_format()}\n")

            output.print_error(text=f"<<<< Cycle family for parent module '{cycle_family.key.parent}'\n")

    @property
    def _consider_package_dependencies(self) -> bool:
        return str(self.consider_package_dependencies).lower() == "true"

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
