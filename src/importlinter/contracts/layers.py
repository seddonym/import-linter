from __future__ import annotations

import itertools
from typing import List, cast

import grimp
from typing_extensions import TypedDict

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck, InvalidContractOptions
from importlinter.domain.imports import Module

from ._common import Chain, DetailedChain, Link, render_chain_data


class Layer:
    def __init__(self, name: str, is_optional: bool = False) -> None:
        self.name = name
        self.is_optional = is_optional


class LayerField(fields.Field):
    def parse(self, raw_data: str | list) -> Layer:
        raw_string = fields.StringField().parse(raw_data)
        if raw_string.startswith("(") and raw_string.endswith(")"):
            layer_name = raw_string[1:-1]
            is_optional = True
        else:
            layer_name = raw_string
            is_optional = False
        return Layer(name=layer_name, is_optional=is_optional)


class _LayerChainData(TypedDict):
    higher_layer: str
    lower_layer: str
    chains: list[DetailedChain]


_UNKNOWN_LINE_NUMBER = -1


class LayersContract(Contract):
    """
    Defines a 'layered architecture' where there is a unidirectional dependency flow.

    Specifically, higher layers may depend on lower layers, but not the other way around.
    To allow for a repeated pattern of layers across a project, you may also define a set of
    'containers', which are treated as the parent package of the layers.

    Layers are required by default: if a layer is listed in the contract, the contract will be
    broken if the layer doesn’t exist. You can make a layer optional by wrapping it in parentheses.

    Configuration options:

        - layers:             An ordered list of layers. Each layer is the name of a module relative
                              to its parent package. The order is from higher to lower level layers.
        - containers:         A list of the parent Modules of the layers. (Optional.)
        - ignore_imports:     A set of ImportExpressions. These imports will be ignored: if the
                              import would cause a contract to be broken, adding it to the set will
                              cause the contract be kept instead. (Optional.)
        - unmatched_ignore_imports_alerting:
                              Decides how to report when the expression in the `ignore_imports` set
                              is not found in the graph. Valid values are "none", "warn", "error".
                              (Optional, defaults to "error".)
        - exhaustive:         If True, check that the contract declares every possible layer in
                              its list of layers to check. (Optional, default False.)
        - exhaustive_ignores: A set of potential layers to ignore in exhaustiveness checks.
                              (Optional.)
    """

    type_name = "layers"

    layers = fields.ListField(subfield=LayerField())
    containers = fields.ListField(subfield=fields.StringField(), required=False)
    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(AlertLevel, default=AlertLevel.ERROR)
    exhaustive = fields.BooleanField(default=False)
    exhaustive_ignores = fields.SetField(subfield=fields.StringField(), required=False)

    def validate(self) -> None:
        if self.exhaustive and not self.containers:
            raise InvalidContractOptions(
                {
                    "exhaustive": (
                        "The exhaustive option is not supported for contracts without containers."
                    )
                }
            )

    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,  # type: ignore
            unmatched_alerting=self.unmatched_ignore_imports_alerting,  # type: ignore
        )

        if self.containers:
            self._validate_containers(graph)
        else:
            self._check_all_containerless_layers_exist(graph)

        undeclared_modules = self._get_undeclared_modules(graph)

        dependencies = graph.find_illegal_dependencies_for_layers(
            layers=tuple(layer.name for layer in self.layers),  # type: ignore
            containers=self.containers,  # type: ignore
        )
        invalid_chains = self._build_invalid_chains(dependencies, graph)

        return ContractCheck(
            kept=not (dependencies or undeclared_modules),
            warnings=warnings,
            metadata={
                "invalid_chains": invalid_chains,
                "undeclared_modules": undeclared_modules,
            },
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in cast(List[_LayerChainData], check.metadata["invalid_chains"]):
            higher_layer, lower_layer = (chains_data["higher_layer"], chains_data["lower_layer"])
            output.print(f"{lower_layer} is not allowed to import {higher_layer}:")
            output.new_line()

            for chain_data in chains_data["chains"]:
                render_chain_data(chain_data)
                output.new_line()

            output.new_line()

        if check.metadata["undeclared_modules"]:
            output.print("The following modules are not listed as layers:")
            output.new_line()
            for module in sorted(check.metadata["undeclared_modules"]):
                output.print_error(f"- {module}", bold=False)
            output.new_line()
            output.print(
                "(Since this contract is marked as 'exhaustive', every child of every "
                "container must be declared as a layer.)"
            )
            output.new_line()

    def _validate_containers(self, graph: grimp.ImportGraph) -> None:
        root_package_names = self.session_options["root_packages"]
        root_packages = tuple(Module(name) for name in root_package_names)

        for container in self.containers:  # type: ignore
            if not any(
                Module(container).is_in_package(root_package) for root_package in root_packages
            ):
                if len(root_package_names) == 1:
                    root_package_name = root_package_names[0]
                    error_message = (
                        f"Invalid container '{container}': a container must either be a "
                        f"subpackage of {root_package_name}, or {root_package_name} itself."
                    )
                else:
                    packages_string = ", ".join(root_package_names)
                    error_message = (
                        f"Invalid container '{container}': a container must either be a root "
                        f"package, or a subpackage of one of them. "
                        f"(The root packages are: {packages_string}.)"
                    )
                raise ValueError(error_message)
            self._check_all_layers_exist_for_container(container, graph)

    def _check_all_layers_exist_for_container(
        self, container: str, graph: grimp.ImportGraph
    ) -> None:
        for layer in self.layers:  # type: ignore
            if layer.is_optional:
                continue
            layer_module_name = ".".join([container, layer.name])
            if layer_module_name not in graph.modules:
                raise ValueError(
                    f"Missing layer in container '{container}': "
                    f"module {layer_module_name} does not exist."
                )

    def _get_undeclared_modules(self, graph: grimp.ImportGraph) -> set[str]:
        if not self.exhaustive:
            return set()

        undeclared_modules = set()

        exhaustive_ignores: set[str] = self.exhaustive_ignores or set()  # type: ignore
        layers: set[str] = {layer.name for layer in self.layers}  # type: ignore
        declared_modules = layers | exhaustive_ignores

        for container in self.containers:  # type: ignore[attr-defined]
            for module in graph.find_children(container):
                undotted_module = module.rpartition(".")[-1]
                if undotted_module not in declared_modules:
                    undeclared_modules.add(f"{container}.{undotted_module}")

        return undeclared_modules

    def _check_all_containerless_layers_exist(self, graph: grimp.ImportGraph) -> None:
        for layer in self.layers:  # type: ignore
            if layer.is_optional:
                continue
            if layer.name not in graph.modules:
                raise ValueError(
                    f"Missing layer '{layer.name}': module {layer.name} does not exist."
                )

    def _module_from_layer(self, layer: Layer, container: str | None = None) -> Module:
        if container:
            name = ".".join([container, layer.name])
        else:
            name = layer.name
        return Module(name)

    def _build_invalid_chains(
        self, dependencies: set[grimp.PackageDependency], graph: grimp.ImportGraph
    ) -> list[_LayerChainData]:
        return [
            {
                "higher_layer": dependency.downstream,
                "lower_layer": dependency.upstream,
                "chains": [
                    self._build_detailed_chain_from_route(c, graph) for c in dependency.routes
                ],
            }
            for dependency in dependencies
        ]

    def _build_detailed_chain_from_route(
        self, route: grimp.Route, graph: grimp.ImportGraph
    ) -> DetailedChain:
        ordered_heads = sorted(route.heads)
        extra_firsts: list[Link] = [
            {
                "importer": head,
                "imported": route.middle[0],
                "line_numbers": self._get_line_numbers(
                    importer=head, imported=route.middle[0], graph=graph
                ),
            }
            for head in ordered_heads[1:]
        ]
        ordered_tails = sorted(route.tails)
        extra_lasts: list[Link] = [
            {
                "imported": tail,
                "importer": route.middle[-1],
                "line_numbers": self._get_line_numbers(
                    imported=tail, importer=route.middle[-1], graph=graph
                ),
            }
            for tail in ordered_tails[1:]
        ]
        chain_as_strings = [ordered_heads[0], *route.middle, ordered_tails[0]]
        chain_as_links: Chain = [
            {
                "importer": importer,
                "imported": imported,
                "line_numbers": self._get_line_numbers(
                    importer=importer, imported=imported, graph=graph
                ),
            }
            for importer, imported in _pairwise(chain_as_strings)
        ]
        return {
            "chain": chain_as_links,
            "extra_firsts": extra_firsts,
            "extra_lasts": extra_lasts,
        }

    def _get_line_numbers(
        self, importer: str, imported: str, graph: grimp.ImportGraph
    ) -> tuple[int | None, ...]:
        details = graph.get_import_details(importer=importer, imported=imported)
        line_numbers = tuple(i["line_number"] for i in details) if details else (None,)
        return line_numbers


def _pairwise(iterable):
    """
    Return successive overlapping pairs taken from the input iterable.
    pairwise('ABCDEFG') --> AB BC CD DE EF FG

    TODO: Replace with itertools.pairwise once on Python 3.10.
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)
