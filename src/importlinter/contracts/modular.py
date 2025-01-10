from __future__ import annotations

from copy import deepcopy

from grimp import ImportGraph

from importlinter.application import output
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.helpers import _to_pattern
from importlinter.domain.imports import Module


# TODO: import from helpers once https://github.com/seddonym/import-linter/pull/220 is merged
def _resolve_wildcards(value: str, graph: ImportGraph) -> set[Module]:
    pattern = _to_pattern(value)
    return {Module(module) for module in graph.modules if pattern.match(module)}


class ModularContract(Contract):
    """
    Modular contracts check that one set of modules has no children with circular dependencies.
    Indirect imports will also be checked.
    Configuration options:
        - modules:    A list of Modules that should be modular.
    """

    type_name = "modular"

    modules = fields.ListField(subfield=fields.ModuleField())

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        violations = {}
        for module in self.modules:  # type: ignore
            direct_submodules = _resolve_wildcards(f"{module.name}.*", graph)
            squashed_graph = deepcopy(graph)
            for m in direct_submodules:
                squashed_graph.squash_module(m.name)

            dependencies = squashed_graph.find_illegal_dependencies_for_layers(
                layers=({y.name for y in direct_submodules},),
            )
            violations[module.name] = sorted(
                {
                    f"{dependency.imported} <- {dependency.importer}"
                    for dependency in dependencies
                    if squashed_graph.find_shortest_chains(
                        dependency.imported, dependency.importer
                    )
                }
            )

        kept = all(len(violation) == 0 for violation in violations.values())
        return ContractCheck(kept=kept, warnings=None, metadata={"violations": violations})

    def render_broken_contract(self, check: "ContractCheck") -> None:
        for module_name, violations in check.metadata["violations"].items():
            output.print(
                f"child modules of {module_name} must be modular and thus circular dependencies "
                "are not allowed:"
            )
            output.new_line()
            for violation in violations:
                output.print_error(f"- {violation}")
            output.new_line()
