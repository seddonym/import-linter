from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from collections.abc import Sequence

import grimp
from typing_extensions import TypedDict

from importlinter.application import contract_utils, output
from importlinter.application.contract_utils import AlertLevel
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck, InvalidContractOptions
from importlinter.domain.helpers import module_expressions_to_modules
from importlinter.domain.imports import Module

from ._common import DetailedChain, build_detailed_chain_from_route, render_chain_data


_INDEPENDENT_LAYER_DELIMITER = "|"
_NON_INDEPENDENT_LAYER_DELIMITER = ":"


@dataclass(frozen=True)
class ModuleTail:
    """
    The "tail" of a module name.
    If no `containers` are specified then this is the full module name.
    However, if `containers` are specified then the full module name is made
    by combining the container name with this tail name.
    """

    name: str
    is_optional: bool = False


@dataclass(frozen=True)
class Layer:
    module_tails: set[ModuleTail]
    is_independent: bool = True


class LayerField(fields.Field):
    def parse(self, raw_data: str | list) -> Layer:
        raw_string = fields.StringField().parse(raw_data)
        raw_module_tails = self._parse_raw_module_tails(raw_string)
        module_tails = set()
        for raw_module_tail in raw_module_tails:
            if raw_module_tail.startswith("(") and raw_module_tail.endswith(")"):
                module_tail = raw_module_tail[1:-1]
                is_optional = True
            else:
                module_tail = raw_module_tail
                is_optional = False
            module_tails.add(ModuleTail(name=module_tail, is_optional=is_optional))
        is_independent = self._parse_is_independent(raw_string)
        return Layer(module_tails, is_independent=is_independent)

    @staticmethod
    def _parse_raw_module_tails(raw_string: str) -> list[str]:
        if _INDEPENDENT_LAYER_DELIMITER in raw_string:
            return [item.strip() for item in raw_string.split(_INDEPENDENT_LAYER_DELIMITER)]
        elif _NON_INDEPENDENT_LAYER_DELIMITER in raw_string:
            return [item.strip() for item in raw_string.split(_NON_INDEPENDENT_LAYER_DELIMITER)]
        else:
            return [raw_string.strip()]

    @staticmethod
    def _parse_is_independent(raw_string: str) -> bool:
        if (
            _INDEPENDENT_LAYER_DELIMITER in raw_string
            and _NON_INDEPENDENT_LAYER_DELIMITER in raw_string
        ):
            raise fields.ValidationError(
                "Layer cannot have a mixture of independent and non-independent elements."
            )
        elif _INDEPENDENT_LAYER_DELIMITER in raw_string:
            return True
        elif _NON_INDEPENDENT_LAYER_DELIMITER in raw_string:
            return False
        else:
            return True


class _LayerChainData(TypedDict):
    importer: str
    imported: str
    routes: list[DetailedChain]


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
                              TODO docs.
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
    containers = fields.ListField(subfield=fields.ModuleExpressionField(), required=False)
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
        self.all_module_tails = self._get_all_module_tails_from_layers(self.layers)  # type: ignore

        containers = set()
        if self.containers:
            modules = module_expressions_to_modules(graph, self.containers)  # type: ignore
            containers = {m.name for m in modules}

        if self.containers:
            self._validate_containers(graph, containers)
        else:
            self._check_all_containerless_layers_exist(graph)

        undeclared_modules = self._get_undeclared_modules(graph, containers)

        dependencies = graph.find_illegal_dependencies_for_layers(
            layers=self._grimpify_layers(self.layers),  # type: ignore
            containers=containers,
        )
        invalid_chains = self._build_invalid_chains(dependencies, graph)

        return ContractCheck(
            kept=not (dependencies or undeclared_modules),
            warnings=warnings,
            metadata={
                "invalid_dependencies": invalid_chains,
                "undeclared_modules": undeclared_modules,
            },
        )

    def _get_all_module_tails_from_layers(self, layers: Sequence[Layer]) -> set[ModuleTail]:
        flattened = set()
        for layer in layers:
            flattened.update(layer.module_tails)
        return flattened

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in cast(list[_LayerChainData], check.metadata["invalid_dependencies"]):
            higher_layer, lower_layer = (
                chains_data["imported"],
                chains_data["importer"],
            )
            output.print(f"{lower_layer} is not allowed to import {higher_layer}:")
            output.new_line()

            for chain_data in chains_data["routes"]:
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

    def _validate_containers(self, graph: grimp.ImportGraph, containers: set[str]) -> None:
        root_package_names = self.session_options["root_packages"]
        root_packages = tuple(Module(name) for name in root_package_names)

        for container in containers:
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
        for module_tail in self.all_module_tails:
            if module_tail.is_optional:
                continue
            module_name = ".".join([container, module_tail.name])
            if module_name not in graph.modules:
                raise ValueError(
                    f"Missing layer in container '{container}': "
                    f"module {module_name} does not exist."
                )

    def _get_undeclared_modules(self, graph: grimp.ImportGraph, containers: set[str]) -> set[str]:
        if not self.exhaustive:
            return set()

        undeclared_modules = set()

        exhaustive_ignores: set[str] = self.exhaustive_ignores or set()  # type: ignore
        module_tail_names: set[str] = {module_tail.name for module_tail in self.all_module_tails}
        declared_module_tails = module_tail_names | exhaustive_ignores

        for container in containers:
            for module in graph.find_children(container):
                module_tail = module.rpartition(".")[-1]
                if module_tail not in declared_module_tails:
                    undeclared_modules.add(f"{container}.{module_tail}")

        return undeclared_modules

    def _check_all_containerless_layers_exist(self, graph: grimp.ImportGraph) -> None:
        for layer in self.layers:  # type: ignore
            for module_tail in layer.module_tails:
                if module_tail.is_optional:
                    continue
                if module_tail.name not in graph.modules:
                    raise ValueError(
                        f"Missing layer '{module_tail.name}': "
                        f"module {module_tail.name} does not exist."
                    )

    def _module_from_module_tail(
        self, module_tail: ModuleTail, container: str | None = None
    ) -> Module:
        if container:
            name = ".".join([container, module_tail.name])
        else:
            name = module_tail.name
        return Module(name)

    def _build_invalid_chains(
        self, dependencies: set[grimp.PackageDependency], graph: grimp.ImportGraph
    ) -> list[_LayerChainData]:
        return [
            {
                "imported": dependency.imported,
                "importer": dependency.importer,
                "routes": [build_detailed_chain_from_route(c, graph) for c in dependency.routes],
            }
            for dependency in dependencies
        ]

    @staticmethod
    def _grimpify_layers(layers: list[Layer]) -> list[grimp.Layer]:
        return [
            grimp.Layer(
                *{module_tail.name for module_tail in layer.module_tails},
                independent=layer.is_independent,
            )
            for layer in layers
        ]
