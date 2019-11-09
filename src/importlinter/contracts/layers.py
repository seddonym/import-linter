import copy
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from networkx.algorithms import simple_paths

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
        self._call_count = 0

        print(f"Beginning layer analysis at {datetime.now().time()}...")
        for (
            higher_layer_package,
            lower_layer_package,
            container,
        ) in self._generate_module_permutations(graph):
            layer_chain_data = self._build_layer_chain_data(
                higher_layer_package=higher_layer_package,
                lower_layer_package=lower_layer_package,
                container=container,
                graph=graph,
            )

            if layer_chain_data["chains"]:
                is_kept = False
                invalid_chains.append(layer_chain_data)
        print(
            f"Finished layer analysis at {datetime.now().time()}. {self._call_count} calls made."
        )

        helpers.add_imports(graph, removed_imports)

        return ContractCheck(kept=is_kept, metadata={"invalid_chains": invalid_chains})

    def render_broken_contract(self, check: ContractCheck) -> None:
        for chains_data in check.metadata["invalid_chains"]:
            higher_layer, lower_layer = (chains_data["higher_layer"], chains_data["lower_layer"])
            output.print(f"{lower_layer} is not allowed to import {higher_layer}:")
            output.new_line()

            for chain_data in chains_data["chains"]:
                self._render_chain_data(chain_data)
                output.new_line()

            output.new_line()

    def _render_chain_data(self, chain_data: Dict) -> None:
        main_chain = chain_data["chain"]
        self._render_direct_import(
            main_chain[0], extra_firsts=chain_data["extra_firsts"], first_line=True
        )

        for direct_import in main_chain[1:-1]:
            self._render_direct_import(direct_import)

        if len(main_chain) > 1:
            self._render_direct_import(main_chain[-1], extra_lasts=chain_data["extra_lasts"])

    def _render_chain_firsts(self, direct_imports):
        output.print_error("Firsts...")

    def _render_chain_lasts(self, direct_imports):
        output.print_error("Lasts...")

    def _render_direct_import(
        self,
        direct_import,
        first_line: bool = False,
        extra_firsts: Optional[List] = None,
        extra_lasts: Optional[List] = None,
    ) -> None:
        import_strings = []
        if extra_firsts:
            for position, source in enumerate([direct_import] + extra_firsts[:-1]):
                prefix = "& " if position > 0 else ""
                importer = source["importer"]
                line_numbers = ", ".join(f"l.{n}" for n in source["line_numbers"])
                import_strings.append(f"{prefix}{importer} ({line_numbers})")
            importer, imported = extra_firsts[-1]["importer"], extra_firsts[-1]["imported"]
            line_numbers = ", ".join(f"l.{n}" for n in extra_firsts[-1]["line_numbers"])
            import_strings.append(f"& {importer} -> {imported} ({line_numbers})")
        else:
            importer, imported = direct_import["importer"], direct_import["imported"]
            line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
            import_strings.append(f"{importer} -> {imported} ({line_numbers})")

        if extra_lasts:
            indent_string = (len(direct_import["importer"]) + 4) * " "
            for destination in extra_lasts:
                imported = destination["imported"]
                line_numbers = ", ".join(f"l.{n}" for n in destination["line_numbers"])
                import_strings.append(f"{indent_string}& {imported} ({line_numbers})")

        for position, import_string in enumerate(import_strings):
            if first_line and position == 0:
                output.print_error(f"- {import_string}", bold=False)
            else:
                output.print_error(f"  {import_string}", bold=False)

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

                    yield higher_layer_module, lower_layer_module, container

    def _module_from_layer(self, layer: Layer, container: Optional[str] = None) -> Module:
        if container:
            name = ".".join([container, layer.name])
        else:
            name = layer.name
        return Module(name)

    def _build_layer_chain_data(
        self,
        higher_layer_package: Module,
        lower_layer_package: Module,
        container: Optional[str],
        graph: ImportGraph,
    ) -> Dict[str, Any]:
        print(higher_layer_package, " to ", lower_layer_package)
        detailed_chains = []
        self._call_count += 1
        timepoint = datetime.now()
        temp_graph = copy.deepcopy(graph)
        # print(f"Copied graph in {(datetime.now() - timepoint).microseconds / 1000}.")
        timepoint = datetime.now()
        self._remove_other_layers(
            temp_graph,
            container=container,
            layers_to_preserve=(higher_layer_package, lower_layer_package),
        )
        # print(f"Removed other layers in {(datetime.now() - timepoint).microseconds / 1000}.")
        timepoint = datetime.now()
        # Assemble direct imports between the layers, then remove them.
        import_details_between_layers = self._pop_direct_imports(
            higher_layer_package=higher_layer_package,
            lower_layer_package=lower_layer_package,
            graph=temp_graph,
        )
        for import_details_list in import_details_between_layers:
            line_numbers = tuple(j["line_number"] for j in import_details_list)
            detailed_chains.append(
                [
                    {
                        "importer": import_details_list[0]["importer"],
                        "imported": import_details_list[0]["imported"],
                        "line_numbers": line_numbers,
                    }
                ]
            )
        # print(f"Got direct imports in {(datetime.now() - timepoint).microseconds / 1000}.")
        # Assemble indirect imports between the layers.
        timepoint = datetime.now()

        # ALTERNATIVE ALGORITHM
        layer_chain_data = {
            "higher_layer": higher_layer_package.name,
            "lower_layer": lower_layer_package.name,
            "chains": self._collapse_detailed_chains(detailed_chains),
        }

        indirect_chain_data = self._get_indirect_collapsed_chains(
            temp_graph, higher_layer_package, lower_layer_package
        )
        layer_chain_data["chains"].extend(indirect_chain_data)

        # chains = (
        #     temp_graph.find_shortest_chains(
        #         importer=lower_layer_package.name, imported=higher_layer_package.name
        #     )
        #     or []
        # )
        # print(f"Found shortest chains in {(datetime.now() - timepoint).microseconds / 1000}.")
        # timepoint = datetime.now()
        # for chain in chains:
        #     detailed_chain = []
        #     for importer, imported in [(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]:
        #         import_details = temp_graph.get_import_details(
        #             importer=importer, imported=imported
        #         )
        #         line_numbers = tuple(j["line_number"] for j in import_details)
        #         detailed_chain.append(
        #             {"importer": importer, "imported": imported, "line_numbers": line_numbers}
        #         )
        #
        #     detailed_chains.append(detailed_chain)
        # # print(f"Got import details of indirect chains in {(datetime.now() - timepoint).microseconds / 1000}.")
        #
        # timepoint = datetime.now()
        # layer_chain_data = {
        #     "higher_layer": higher_layer_package.name,
        #     "lower_layer": lower_layer_package.name,
        #     "chains": self._collapse_detailed_chains(detailed_chains),
        # }
        # print(f"Collapsed indirect chains in {(datetime.now() - timepoint).microseconds / 1000}.")
        # assert isinstance(layer_chain_data["chains"], list)  # For type checker.

        return layer_chain_data

    @classmethod
    def _get_indirect_collapsed_chains(cls, graph, importer_package, imported_package):
        """
        Squashes the two packages.
        Gets a list of paths between them, called segments.
        Add the heads and tails to the segments.
        Return a list of detailed chains in the following format:

        [
            {
                "chain": <detailed chain>,
                "extra_firsts": [
                    <import details>,
                    ...
                ],
                "extra_lasts": [
                    <import details>,
                    <import details>,
                    ...
                ],
            }
        ]
        """
        temp_graph = copy.deepcopy(graph)

        cls._squash_module(temp_graph, importer_package)
        cls._squash_module(temp_graph, imported_package)

        segments = cls._find_segments(
            temp_graph, importer=importer_package, imported=imported_package
        )

        return cls._segments_to_collapsed_chains(
            graph, segments, importer=importer_package, imported=imported_package
        )

    @classmethod
    def _squash_module(cls, graph: ImportGraph, package: Module):
        for descendant in graph.find_descendants(package.name):
            for imported_module in graph.find_modules_directly_imported_by(descendant):
                graph.add_import(importer=package.name, imported=imported_module)
                # Hack due to bug with Grimp (see a few lines below too).
                graph._import_details.setdefault(package.name, [])
                graph._import_details[package.name].append(
                    {
                        "importer": package.name,
                        "imported": imported_module,
                        "line_number": None,
                        "line_contents": None,
                    }
                )
            for importing_module in graph.find_modules_that_directly_import(descendant) | {
                package.name
            }:
                graph.add_import(importer=importing_module, imported=package.name)
                graph._import_details.setdefault(importing_module, [])
                graph._import_details[importing_module].append(
                    {
                        "importer": importing_module,
                        "imported": package.name,
                        "line_number": None,
                        "line_contents": None,
                    }
                )
            graph.remove_module(descendant)
        if package.name in graph.modules:
            graph._mark_module_as_squashed(package.name)
        else:
            graph.add_module(package.name, is_squashed=True)

    @classmethod
    def _find_segments(cls, graph, importer: Module, imported: Module):
        """
        Return list of headless and tailless detailed chains.
        """
        segments = []
        for chain in simple_paths.all_simple_paths(
            graph._networkx_graph, source=importer.name, target=imported.name
        ):
            # chain = graph.find_shortest_chain(importer=importer.name, imported=imported.name)
            if len(chain) == 2:
                continue
                # Not sure why this happens?
                raise ValueError("Direct chain found - these should have been removed.")
            detailed_chain = []
            for importer, imported in [(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]:
                import_details = graph.get_import_details(importer=importer, imported=imported)
                line_numbers = tuple(j["line_number"] for j in import_details)
                detailed_chain.append(
                    {"importer": importer, "imported": imported, "line_numbers": line_numbers}
                )
            segments.append(detailed_chain)
        return segments

    @classmethod
    def _segments_to_collapsed_chains(cls, graph, segments, importer: Module, imported: Module):
        collapsed_chains = []
        for segment in segments:
            head_imports = []
            imported_module = segment[0]["imported"]
            candidate_modules = graph.find_modules_that_directly_import(imported_module)
            for module in [m for m in candidate_modules if Module(m).is_descendant_of(importer)]:
                import_details_list = graph.get_import_details(
                    importer=module, imported=imported_module
                )
                line_numbers = tuple(j["line_number"] for j in import_details_list)
                head_imports.append(
                    {
                        "importer": import_details_list[0]["importer"],
                        "imported": import_details_list[0]["imported"],
                        "line_numbers": line_numbers,
                    }
                )

            tail_imports = []
            importer_module = segment[-1]["importer"]
            candidate_modules = graph.find_modules_directly_imported_by(importer_module)
            for module in [m for m in candidate_modules if Module(m).is_descendant_of(imported)]:
                import_details_list = graph.get_import_details(
                    importer=importer_module, imported=module
                )
                line_numbers = tuple(j["line_number"] for j in import_details_list)
                tail_imports.append(
                    {
                        "importer": import_details_list[0]["importer"],
                        "imported": import_details_list[0]["imported"],
                        "line_numbers": line_numbers,
                    }
                )

            collapsed_chains.append(
                {
                    "chain": [head_imports[0]] + segment[1:-1] + [tail_imports[0]],
                    "extra_firsts": head_imports[1:],
                    "extra_lasts": tail_imports[1:],
                }
            )

        return collapsed_chains

    @classmethod
    def _collapse_detailed_chains(cls, detailed_chains):
        """
        Return a list of collapsed chains in the following format:

        [
            {
                "chain": <detailed chain>,
                "extra_firsts": [
                    <import details>,
                    ...
                ],
                "extra_lasts": [
                    <import details>,
                    <import details>,
                    ...
                ],
            }
        ]
        """
        collapsed_chain_by_headless_hash = {}
        collapsed_chains = []
        for detailed_chain in detailed_chains:
            collapsed_chain = {"chain": detailed_chain, "extra_firsts": [], "extra_lasts": []}
            if len(detailed_chain) > 2:
                headless_hash = cls._hash_detailed_chain(detailed_chain[1:-1])
                try:
                    matching_collapsed_chain = collapsed_chain_by_headless_hash[headless_hash]
                except KeyError:
                    collapsed_chain_by_headless_hash[headless_hash] = collapsed_chain
                else:
                    if collapsed_chain["chain"][0] != matching_collapsed_chain["chain"][0]:
                        matching_collapsed_chain["extra_firsts"].append(detailed_chain[0])
                    if collapsed_chain["chain"][-1] != matching_collapsed_chain["chain"][-1]:
                        matching_collapsed_chain["extra_lasts"].append(
                            collapsed_chain["chain"][-1]
                        )
            elif len(detailed_chain) == 2:
                headless_hash = cls._hash_detailed_chain(detailed_chain[1:])
                try:
                    matching_collapsed_chain = collapsed_chain_by_headless_hash[headless_hash]
                except KeyError:
                    collapsed_chain_by_headless_hash[headless_hash] = collapsed_chain
                else:
                    matching_collapsed_chain["extra_firsts"].append(detailed_chain[0])
            else:
                collapsed_chains.append(collapsed_chain)

        collapsed_chain_by_tailless_hash = {}
        for collapsed_chain in collapsed_chain_by_headless_hash.values():
            tailless_hash = cls._hash_detailed_chain(collapsed_chain["chain"][:-1])
            try:
                matching_collapsed_chain = collapsed_chain_by_tailless_hash[tailless_hash]
            except KeyError:
                collapsed_chain_by_tailless_hash[tailless_hash] = collapsed_chain
            else:
                matching_collapsed_chain["extra_lasts"].append(collapsed_chain["chain"][-1])

        collapsed_chains.extend(collapsed_chain_by_tailless_hash.values())

        return collapsed_chains

    @classmethod
    def _hash_detailed_chain(cls, detailed_chain):
        list_to_turn_to_tuple = []
        for import_detail in detailed_chain:
            list_to_turn_to_tuple.append(
                (
                    import_detail["importer"],
                    import_detail["imported"],
                    import_detail["line_numbers"],
                )
            )
        return hash(tuple(list_to_turn_to_tuple))

    def _remove_other_layers(self, graph, container, layers_to_preserve):
        for index, layer in enumerate(self.layers):  # type: ignore
            candidate_layer = self._module_from_layer(layer, container)
            if candidate_layer not in layers_to_preserve:
                self._remove_layer(graph, layer_package=candidate_layer)

    def _remove_layer(self, graph, layer_package):
        for module in graph.find_descendants(layer_package):
            graph.remove_module(module)
        graph.remove_module(layer_package)

    def _pop_direct_imports(self, higher_layer_package, lower_layer_package, graph):
        import_details_list = []
        lower_layer_modules = {lower_layer_package.name} | graph.find_descendants(
            lower_layer_package
        )
        for lower_layer_module in lower_layer_modules:
            imported_modules = graph.find_modules_directly_imported_by(lower_layer_module)
            for imported_module in imported_modules:
                if Module(imported_module).is_descendant_of(Module(higher_layer_package)):
                    import_details_list.append(
                        graph.get_import_details(
                            importer=lower_layer_module, imported=imported_module
                        )
                    )
                    graph.remove_import(importer=lower_layer_module, imported=imported_module)
        return import_details_list
