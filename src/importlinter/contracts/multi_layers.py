import copy
from collections.abc import Iterable
from typing import Any, NamedTuple, TypedDict

from importlinter import Contract, ContractCheck
from importlinter.application import output
from importlinter.contracts.layers import LayersContract
from importlinter.domain import fields
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class Layer(NamedTuple):
    name: str


class _DirectImport(TypedDict):
    importer: Module
    imported: Module
    line_number: str
    line_contents: str


class Import(TypedDict):
    importer: Module
    imported: Module
    line_numbers: tuple[str, ...]


class Path(TypedDict):
    chain: list[Import]
    extra_firsts: list[Import]
    extra_lasts: list[Import]


class Violation(NamedTuple):
    higher_layer: Module
    lower_layer: Module
    chains: tuple[Path, ...]


class MultiLayerField(fields.Field):
    def parse(self, raw_data: str | list[Any]) -> tuple[Layer, ...]:
        layers = fields.StringField().parse(raw_data)
        return tuple(Layer(name=name) for name in layers.split(","))


class MultiLayersContract(Contract):
    """
    A kind of hybrid contract between `layers` and `independence`. Where modules
    declared on the same level are independent between each other while they
    individually honor their "lower layers".

    If a layer declares multiple modules, a module "higher" to that layer is allowed to
    import from all of the declared modules.

    Example:
        `higher` is allowed to import all of the `sibling`s below, while none of the
        siblings are allowed to directly, or indirectly import from each other or
        `higher`.

    layers =
        higher
        sibling1,sibling2,sibling3
    """

    type_name = "multi-layers"

    layers = fields.ListField(subfield=MultiLayerField())

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        for multi_layer in self.layers:
            for layer in multi_layer:
                if layer.name not in graph.modules:
                    raise ValueError(
                        f"Missing layer {layer.name!r}: module {layer.name!r} does not exist"
                    )

        violations = []
        for higher_layer, lower_layer in self._get_module_permutations(self.layers):
            temp_graph = copy.deepcopy(graph)
            self._remove_layers(temp_graph, preserve=(higher_layer, lower_layer))

            # Handle direct imports first
            direct_imports: list[list[_DirectImport]] = LayersContract._pop_direct_imports(
                higher_layer, lower_layer, graph
            )
            violation_paths = []
            for direct_import in direct_imports:
                violation_paths.append(
                    Path(
                        chain=[
                            Import(
                                importer=direct_import[0]["importer"],
                                imported=direct_import[0]["imported"],
                                line_numbers=tuple(
                                    violation["line_number"] for violation in direct_import
                                ),
                            )
                        ],
                        extra_firsts=[],
                        extra_lasts=[],
                    )
                )

            # Then handle indirect imports
            violation_paths.extend(
                LayersContract._get_indirect_collapsed_chains(
                    graph, importer_package=lower_layer, imported_package=higher_layer
                )
            )
            if violation_paths:
                violations.append(
                    Violation(
                        higher_layer=higher_layer,
                        lower_layer=lower_layer,
                        chains=tuple(violation_paths),
                    )
                )

        return ContractCheck(
            kept=not bool(violations),
            warnings=None,
            metadata={"violations": violations},
        )

    def _get_module_permutations(self, graph: ImportGraph) -> Iterable[tuple[Module, Module]]:
        for index, multi_layer in enumerate(self.layers):
            for layer in multi_layer:
                # Layers on the same level are always banned to import eachother, so
                # we'll ensure we yield a constraint in both directions
                # This is the regular `"independence"` contract
                for sibling_layer in multi_layer:
                    if sibling_layer != layer:
                        yield Module(layer.name), Module(sibling_layer.name)
                # Layers considered to be higher (i.e. declared before) are allowed to
                # import those that are lower, but not the other way around
                # This is the regular `"layers"` contract
                for lower_multi_layer in self.layers[index + 1 :]:
                    for lower_layer in lower_multi_layer:
                        yield Module(layer.name), Module(lower_layer.name)

    def _remove_layers(self, graph: ImportGraph, preserve: tuple[Module, Module]) -> None:
        for multi_layer in self.layers:
            for layer in multi_layer:
                if layer in graph.modules and Module(layer) not in preserve:
                    for descendant in graph.find_descendants(layer):
                        graph.remove_module(descendant)
                    graph.remove_module(layer)

    def render_broken_contract(self, check: ContractCheck) -> None:
        for violation in check.metadata["violations"]:
            output.print(
                f"{violation.lower_layer} is not allowed to import {violation.higher_layer}:"
            )
            output.new_line()

            for path in violation.chains:
                self.render_path(path)
                output.new_line()

            output.new_line()

    def render_path(self, path: Path) -> None:
        chain = path["chain"]
        self.render_direct_import(chain[0], extra_firsts=path["extra_firsts"], first_line=True)

        for direct_import in chain[1:-1]:
            self.render_direct_import(direct_import)

        if len(chain) > 1:
            self.render_direct_import(chain[-1], extra_lasts=path["extra_lasts"])

    def render_direct_import(
        self,
        direct_import: Import,
        first_line: bool = False,
        extra_firsts: list[Import] | None = None,
        extra_lasts: list[Import] | None = None,
    ) -> None:
        output_lines = []
        if extra_firsts:
            for position, source in enumerate([direct_import] + extra_firsts[:-1]):
                output_lines.append(
                    format_import(
                        importer=source["importer"],
                        imported=None,
                        line_numbers=source["line_numbers"],
                        prefix="& " if position > 0 else "",
                    )
                )

            output_lines.append(
                format_import(
                    importer=extra_firsts[-1]["importer"],
                    imported=extra_firsts[-1]["imported"],
                    line_numbers=extra_firsts[-1]["line_numbers"],
                    prefix="& ",
                )
            )
        else:
            output_lines.append(
                format_import(
                    importer=direct_import["importer"],
                    imported=direct_import["imported"],
                    line_numbers=direct_import["line_numbers"],
                )
            )

        if extra_lasts:
            prefix = ((len(direct_import["importer"]) + 4) * " ") + "& "
            for destination in extra_lasts:
                output_lines.append(
                    format_import(
                        importer=None,
                        imported=destination["imported"],
                        line_numbers=destination["line_numbers"],
                        prefix=prefix,
                    )
                )

        for position, line in enumerate(output_lines):
            if first_line and position == 0:
                output.print_error(f"- {line}", bold=False)
            else:
                output.print_error(f"  {line}", bold=False)


def format_import(
    importer: Module | None,
    imported: Module | None,
    line_numbers: tuple[str, ...],
    prefix: str = "",
) -> str:
    lines_str = ", ".join(f"l.{n}" for n in line_numbers)
    if importer is not None and imported is not None:
        return f"{prefix}{importer} -> {imported} ({lines_str})"
    elif importer is not None:
        return f"{prefix}{importer} ({lines_str})"
    elif imported is not None:
        return f"{prefix}{imported} ({lines_str})"
    else:
        raise TypeError("Both 'importer' and 'imported' cannot be None")
