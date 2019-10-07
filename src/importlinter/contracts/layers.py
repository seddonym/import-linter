from typing import Any, Dict, Iterator, List, Tuple, Union, Optional

from importlinter.application import output
from importlinter.domain import fields, helpers
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class Layer:
    def __init__(self, name: str, is_optional: bool = False) -> None:
        self.name = name
        self.is_optional = is_optional


class LayerField(fields.Field):
    def parse(self, raw_data: Union[str, List]) -> Layer:
        raw_string = fields.StringField().parse(raw_data)
        if raw_string.startswith("(") and raw_string.endswith(")"):
            layer_name = raw_string[1:-1]
            is_optional = True
        else:
            layer_name = raw_string
            is_optional = False
        return Layer(name=layer_name, is_optional=is_optional)


class LayersContract(Contract):
    """
    Defines a 'layered architecture' where there is a unidirectional dependency flow.

    Specifically, higher layers may depend on lower layers, but not the other way around.
    To allow for a repeated pattern of layers across a project, you may also define a set of
    'containers', which are treated as the parent package of the layers.

    Layers are required by default: if a layer is listed in the contract, the contract will be
    broken if the layer doesn’t exist. You can make a layer optional by wrapping it in parentheses.

    Configuration options:

        - layers:         An ordered list of layers. Each layer is the name of a module relative
                          to its parent package. The order is from higher to lower level layers.
        - containers:     A list of the parent Modules of the layers (optional).
        - ignore_imports: A list of DirectImports. These imports will be ignored: if the import
                          would cause a contract to be broken, adding it to the list will cause
                          the contract be kept instead. (Optional.)
    """

    type_name = "layers"

    layers = fields.ListField(subfield=LayerField())
    containers = fields.ListField(subfield=fields.StringField(), required=False)
    ignore_imports = fields.ListField(subfield=fields.DirectImportField(), required=False)

    def check(self, graph: ImportGraph) -> ContractCheck:
        is_kept = True
        invalid_chains = []

        direct_imports_to_ignore = self.ignore_imports if self.ignore_imports else []
        removed_imports = helpers.pop_imports(
            graph, direct_imports_to_ignore  # type: ignore
        )

        if self.containers:
            self._validate_containers(graph)
        else:
            self._check_all_containerless_layers_exist(graph)

        for higher_layer_package, lower_layer_package in self._generate_module_permutations(graph):
            layer_chain_data = self._build_layer_chain_data(
                higher_layer_package=higher_layer_package,
                lower_layer_package=lower_layer_package,
                graph=graph,
            )

            if layer_chain_data["chains"]:
                is_kept = False
                invalid_chains.append(layer_chain_data)

        helpers.add_imports(graph, removed_imports)

        return ContractCheck(kept=is_kept, metadata={"invalid_chains": invalid_chains})

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in check.metadata["invalid_chains"]:
            higher_layer, lower_layer = (chains_data["higher_layer"], chains_data["lower_layer"])
            output.print(f"{lower_layer} is not allowed to import {higher_layer}:")
            output.new_line()

            for chain in chains_data["chains"]:
                first_line = True
                for direct_import in chain:
                    importer, imported = (direct_import["importer"], direct_import["imported"])
                    line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
                    import_string = f"{importer} -> {imported} ({line_numbers})"
                    if first_line:
                        output.print_error(f"-   {import_string}", bold=False)
                        first_line = False
                    else:
                        output.indent_cursor()
                        output.print_error(import_string, bold=False)
                output.new_line()

            output.new_line()

    def _validate_containers(self, graph: ImportGraph) -> None:
        root_package_names = self.session_options["root_packages"]
        for container in self.containers:  # type: ignore
            if Module(container).root_package_name not in root_package_names:
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

    def _check_all_layers_exist_for_container(self, container: str, graph: ImportGraph) -> None:
        for layer in self.layers:  # type: ignore
            if layer.is_optional:
                continue
            layer_module_name = ".".join([container, layer.name])
            if layer_module_name not in graph.modules:
                raise ValueError(
                    f"Missing layer in container '{container}': "
                    f"module {layer_module_name} does not exist."
                )

    def _check_all_containerless_layers_exist(self, graph: ImportGraph) -> None:
        for layer in self.layers:  # type: ignore
            if layer.is_optional:
                continue
            if layer.name not in graph.modules:
                raise ValueError(
                    f"Missing layer '{layer.name}': module {layer.name} does not exist."
                )

    def _generate_module_permutations(self, graph: ImportGraph) -> Iterator[Tuple[Module, Module]]:
        """
        Return all possible combinations of higher level and lower level modules, in pairs.

        Each pair of modules consists of immediate children of two different layers. The first
        module is in a layer higher than the layer of the second module. This means the first
        module is allowed to import the second, but not the other way around.

        Returns:
            module_in_higher_layer, module_in_lower_layer
        """
        # If there are no containers, we still want to run the loop once.
        quasi_containers = self.containers or [None]

        for container in quasi_containers:  # type: ignore
            for index, higher_layer in enumerate(self.layers):  # type: ignore
                higher_layer_module = self._module_from_layer(higher_layer, container)

                if higher_layer_module.name not in graph.modules:
                    continue

                for lower_layer in self.layers[index + 1 :]:  # type: ignore

                    lower_layer_module = self._module_from_layer(lower_layer, container)

                    if lower_layer_module.name not in graph.modules:
                        continue

                    yield higher_layer_module, lower_layer_module

    def _module_from_layer(self, layer: Layer, container: Optional[str] = None) -> Module:
        if container:
            name = ".".join([container, layer.name])
        else:
            name = layer.name
        return Module(name)

    def _build_layer_chain_data(
        self, higher_layer_package: Module, lower_layer_package: Module, graph: ImportGraph
    ) -> Dict[str, Any]:
        layer_chain_data = {
            "higher_layer": higher_layer_package.name,
            "lower_layer": lower_layer_package.name,
            "chains": [],
        }
        assert isinstance(layer_chain_data["chains"], list)  # For type checker.

        chains = graph.find_shortest_chains(
            importer=lower_layer_package.name, imported=higher_layer_package.name
        )
        if chains:
            for chain in chains:
                chain_data = []
                for importer, imported in [
                    (chain[i], chain[i + 1]) for i in range(len(chain) - 1)
                ]:
                    import_details = graph.get_import_details(importer=importer, imported=imported)
                    line_numbers = tuple(j["line_number"] for j in import_details)
                    chain_data.append(
                        {"importer": importer, "imported": imported, "line_numbers": line_numbers}
                    )

                layer_chain_data["chains"].append(chain_data)
        return layer_chain_data
