import pytest
from textwrap import dedent
from grimp import ImportGraph
from importlinter.application.output import console
from importlinter.application.app_config import settings
from importlinter.contracts.layers import Layer, LayerField, LayersContract, ModuleTail
from importlinter.domain.contract import ContractCheck, InvalidContractOptions
from importlinter.domain.helpers import MissingImport
from importlinter.domain import fields
from tests.adapters.timing import FakeTimer


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=FakeTimer())


@pytest.mark.parametrize(
    "data, parsed_data",
    (
        ("one", Layer({ModuleTail(name="one", is_optional=False)})),
        ("(one)", Layer({ModuleTail(name="one", is_optional=True)})),
        (
            "one | two |    three",
            Layer(
                {
                    ModuleTail(name="one"),
                    ModuleTail(name="two"),
                    ModuleTail(name="three"),
                }
            ),
        ),
        (
            "one | (two) | three",
            Layer(
                {
                    ModuleTail(name="one"),
                    ModuleTail(name="two", is_optional=True),
                    ModuleTail(name="three"),
                }
            ),
        ),
        (
            "one : two :    three",
            Layer(
                {
                    ModuleTail(name="one"),
                    ModuleTail(name="two"),
                    ModuleTail(name="three"),
                },
                is_independent=False,
            ),
        ),
        (
            "one : (two) : three",
            Layer(
                {
                    ModuleTail(name="one"),
                    ModuleTail(name="two", is_optional=True),
                    ModuleTail(name="three"),
                },
                is_independent=False,
            ),
        ),
    ),
)
def test_layer_field(data, parsed_data):
    assert LayerField().parse(data) == parsed_data


def test_layer_field_raises_error_if_both_independent_and_non_independent():
    with pytest.raises(fields.ValidationError) as exc_info:
        LayerField().parse("one | two : three")
    assert (
        exc_info.value.message
        == "Layer cannot have a mixture of independent and non-independent elements."
    )


class TestLayerContractSingleContainers:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract()
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_illegal_child_imports_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.high.green")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def test_illegal_grandchild_to_child_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(importer="mypackage.low.white.gamma", imported="mypackage.medium.red")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.high",
            "mypackage.high.green",
            "mypackage.high.blue",
            "mypackage.high.yellow",
            "mypackage.high.yellow.alpha",
            "mypackage.medium",
            "mypackage.medium.orange",
            "mypackage.medium.orange.beta",
            "mypackage.medium.red",
            "mypackage.low",
            "mypackage.low.black",
            "mypackage.low.white",
            "mypackage.low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer="mypackage.high.green", imported="mypackage.medium.orange")
        graph.add_import(importer="mypackage.high.green", imported="mypackage.low.white.gamma")
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.low.white")
        graph.add_import(importer="mypackage.high.blue", imported="mypackage.utils")
        graph.add_import(importer="mypackage.utils", imported="mypackage.medium.red")

        return graph

    def _build_contract(self):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage"],
                "layers": ["high", "medium", "low"],
            },
        )


class TestLayerContractSiblingLayers:
    @pytest.mark.parametrize("layer_independent", (True, False))
    @pytest.mark.parametrize("specify_container", (True, False))
    def test_imports_between_sibling_modules(
        self,
        specify_container: bool,
        layer_independent: bool,
    ):
        contract = self._create_contract(
            specify_container=specify_container,
            layer_independent=layer_independent,
        )
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.high",
            "mypackage.medium_a",
            "mypackage.medium_b",
            "mypackage.medium_c",
            "mypackage.low",
        ):
            graph.add_module(module)
        # Add some legal imports.
        graph.add_import(importer="mypackage.high.green", imported="mypackage.medium.orange")
        graph.add_import(importer="mypackage.utils", imported="mypackage.medium.red")
        # Add an import between sibling modules within the medium layer.
        graph.add_import(
            importer="mypackage.medium_a.blue",
            imported="mypackage.medium_b.red",
            line_number=3,
            line_contents="-",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        if layer_independent:
            assert contract_check.kept is False
            sorted_metadata = _get_sorted_metadata(contract_check)
            assert sorted_metadata == {
                "invalid_dependencies": [
                    {
                        "importer": "mypackage.medium_a",
                        "imported": "mypackage.medium_b",
                        "routes": [
                            {
                                "chain": [
                                    {
                                        "importer": "mypackage.medium_a.blue",
                                        "imported": "mypackage.medium_b.red",
                                        "line_numbers": (3,),
                                    },
                                ],
                                "extra_firsts": [],
                                "extra_lasts": [],
                            }
                        ],
                    },
                ],
                "undeclared_modules": set(),
            }
        else:
            assert contract_check.kept is True

    def _create_contract(self, specify_container: bool, layer_independent: bool):
        package = "mypackage"
        layer_prefix = "" if specify_container else f"{package}."
        layer_delimiter = "|" if layer_independent else ":"
        contract_options = {
            "layers": [
                f"{layer_prefix}high",
                f"{layer_prefix}medium_a {layer_delimiter} {layer_prefix}medium_b "
                f"{layer_delimiter} {layer_prefix}medium_c",
                f"{layer_prefix}low",
            ]
        }
        if specify_container:
            contract_options["containers"] = [package]
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options=contract_options,
        )


class TestLayerMultipleContainers:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract()
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_imports_from_low_to_high_but_in_different_container_doesnt_break_contract(
        self,
    ):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.two.medium.green.beta",
            imported="mypackage.one.high.green",
        )
        graph.add_import(
            importer="mypackage.three.low.cyan", imported="mypackage.two.high.red.alpha"
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_illegal_grandchild_imports_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.two.medium.green.beta",
            imported="mypackage.two.high.red.alpha",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def test_import_via_noncontainer_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.one.medium.orange",
            imported="mypackage.noncontainer.blue",
        )
        graph.add_import(
            importer="mypackage.noncontainer.blue",
            imported="mypackage.two.high.red.alpha",
        )
        graph.add_import(
            importer="mypackage.two.high.red.alpha", imported="mypackage.one.high.green"
        )
        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.one",
            "mypackage.one.high",
            "mypackage.one.high.green",
            "mypackage.one.high.blue",
            "mypackage.one.high.yellow",
            "mypackage.one.high.yellow.alpha",
            "mypackage.one.medium",
            "mypackage.one.medium.orange",
            "mypackage.one.medium.orange.beta",
            "mypackage.one.medium.red",
            "mypackage.one.low",
            "mypackage.one.low.black",
            "mypackage.one.low.white",
            "mypackage.one.low.white.gamma",
            "mypackage.two",
            "mypackage.two.high",
            "mypackage.two.high.red",
            "mypackage.two.high.red.alpha",
            "mypackage.two.medium",
            "mypackage.two.medium.green",
            "mypackage.two.medium.green.beta",
            "mypackage.two.low",
            "mypackage.two.low.blue",
            "mypackage.two.low.blue.gamma",
            "mypackage.three",
            "mypackage.three.high",
            "mypackage.three.high.white",
            "mypackage.three.medium",
            "mypackage.three.medium.purple",
            "mypackage.three.low",
            "mypackage.three.low.cyan",
            "mypackage.noncontainer",
            "mypackage.noncontainer.blue",
        ):
            graph.add_module(module)

        # Add some 'legal' imports, each within their separate containers.
        graph.add_import(
            importer="mypackage.one.high.green", imported="mypackage.one.medium.orange"
        )
        graph.add_import(
            importer="mypackage.one.high.green",
            imported="mypackage.one.low.white.gamma",
        )
        graph.add_import(
            importer="mypackage.one.medium.orange", imported="mypackage.one.low.white"
        )

        graph.add_import(
            importer="mypackage.two.high.red.alpha",
            imported="mypackage.two.medium.green.beta",
        )
        graph.add_import(
            importer="mypackage.two.high.red.alpha",
            imported="mypackage.two.low.blue.gamma",
        )
        graph.add_import(
            importer="mypackage.two.medium.green.beta",
            imported="mypackage.two.low.blue.gamma",
        )

        graph.add_import(
            importer="mypackage.three.high.white",
            imported="mypackage.three.medium.purple",
        )
        graph.add_import(
            importer="mypackage.three.high.white", imported="mypackage.three.low.cyan"
        )
        graph.add_import(
            importer="mypackage.three.medium.purple",
            imported="mypackage.three.low.cyan",
        )

        return graph

    def _build_contract(self):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage.one", "mypackage.two", "mypackage.three"],
                "layers": ["high", "medium", "low"],
            },
        )


class TestLayerContractWildcardContainers:
    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.components.one",
            "mypackage.components.one.high",
            "mypackage.components.one.high.green",
            "mypackage.components.one.high.blue",
            "mypackage.components.one.high.yellow",
            "mypackage.components.one.high.yellow.alpha",
            "mypackage.components.one.medium",
            "mypackage.components.one.medium.orange",
            "mypackage.components.one.medium.orange.beta",
            "mypackage.components.one.medium.red",
            "mypackage.components.one.low",
            "mypackage.components.one.low.black",
            "mypackage.components.one.low.white",
            "mypackage.components.one.low.white.gamma",
            "mypackage.components.two",
            "mypackage.components.two.high",
            "mypackage.components.two.high.red",
            "mypackage.components.two.high.red.alpha",
            "mypackage.components.two.medium",
            "mypackage.components.two.medium.green",
            "mypackage.components.two.medium.green.beta",
            "mypackage.components.two.low",
            "mypackage.components.two.low.blue",
            "mypackage.components.two.low.blue.gamma",
            "mypackage.components.three",
            "mypackage.components.three.high",
            "mypackage.components.three.high.white",
            "mypackage.components.three.medium",
            "mypackage.components.three.medium.purple",
            "mypackage.components.three.low",
            "mypackage.components.three.low.cyan",
            "mypackage.noncontainer",
            "mypackage.noncontainer.blue",
        ):
            graph.add_module(module)

        # Add some 'legal' imports, each within their separate containers.
        graph.add_import(
            importer="mypackage.one.high.green", imported="mypackage.one.medium.orange"
        )
        graph.add_import(
            importer="mypackage.one.high.green",
            imported="mypackage.one.low.white.gamma",
        )
        graph.add_import(
            importer="mypackage.one.medium.orange", imported="mypackage.one.low.white"
        )

        graph.add_import(
            importer="mypackage.two.high.red.alpha",
            imported="mypackage.two.medium.green.beta",
        )
        graph.add_import(
            importer="mypackage.two.high.red.alpha",
            imported="mypackage.two.low.blue.gamma",
        )
        graph.add_import(
            importer="mypackage.two.medium.green.beta",
            imported="mypackage.two.low.blue.gamma",
        )

        graph.add_import(
            importer="mypackage.three.high.white",
            imported="mypackage.three.medium.purple",
        )
        graph.add_import(
            importer="mypackage.three.high.white", imported="mypackage.three.low.cyan"
        )
        graph.add_import(
            importer="mypackage.three.medium.purple",
            imported="mypackage.three.low.cyan",
        )

        return graph

    def _build_contract(self):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage.components.*"],
                "layers": ["high", "medium", "low"],
            },
        )

    def test_containers_can_use_wildcards(self):
        contract = self._build_contract()
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_illegal_grandchild_imports_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.components.two.medium.green.beta",
            imported="mypackage.components.two.high.red.alpha",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False


class TestLayerContractPopulatesMetadata:
    def test_layer_contract_populates_metadata(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add a selection of illegal imports.
        graph.add_import(
            importer="mypackage.low.white.gamma",
            imported="mypackage.utils.foo",
            line_number=3,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=101,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.bar",
            imported="mypackage.high.yellow.alpha",
            line_number=13,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.medium.orange.beta",
            imported="mypackage.high.blue",
            line_number=2,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.low.black",
            imported="mypackage.utils.baz",
            line_number=2,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.baz",
            imported="mypackage.medium.red",
            line_number=3,
            line_contents="-",
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept is False

        sorted_metadata = _get_sorted_metadata(contract_check)
        assert sorted_metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.white.gamma",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.utils.bar",
                                    "line_numbers": (1, 101),
                                },
                                {
                                    "importer": "mypackage.utils.bar",
                                    "imported": "mypackage.high.yellow.alpha",
                                    "line_numbers": (13,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        }
                    ],
                },
                {
                    "imported": "mypackage.medium",
                    "importer": "mypackage.low",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.black",
                                    "imported": "mypackage.utils.baz",
                                    "line_numbers": (2,),
                                },
                                {
                                    "importer": "mypackage.utils.baz",
                                    "imported": "mypackage.medium.red",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        }
                    ],
                },
                {
                    "importer": "mypackage.medium",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.medium.orange.beta",
                                    "imported": "mypackage.high.blue",
                                    "line_numbers": (2,),
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        }
                    ],
                },
            ],
            "undeclared_modules": set(),
        }

    def test_layer_contract_populates_extra_firsts_one_indirect(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with three illegal starting points, only one indirect step.
        for starting_point in (
            "mypackage.low.blue",
            "mypackage.low.green",
            "mypackage.low.red",
        ):
            graph.add_import(
                importer=starting_point,
                imported="mypackage.utils.foo",
                line_number=3,
                line_contents="-",
            )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.high.yellow",
            line_number=1,
            line_contents="-",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.high.yellow",
                                    "line_numbers": (1,),
                                },
                            ],
                            "extra_firsts": [
                                {
                                    "importer": "mypackage.low.green",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.low.red",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_lasts": [],
                        }
                    ],
                }
            ],
            "undeclared_modules": set(),
        }

    def test_layer_contract_populates_extra_firsts_two_indirects(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with two illegal starting points, two indirect steps.
        for starting_point in ("mypackage.low.blue", "mypackage.low.green"):
            graph.add_import(
                importer=starting_point,
                imported="mypackage.utils.foo",
                line_number=3,
                line_contents="-",
            )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.bar",
            imported="mypackage.high.yellow",
            line_number=2,
            line_contents="-",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.utils.bar",
                                    "line_numbers": (1,),
                                },
                                {
                                    "importer": "mypackage.utils.bar",
                                    "imported": "mypackage.high.yellow",
                                    "line_numbers": (2,),
                                },
                            ],
                            "extra_firsts": [
                                {
                                    "importer": "mypackage.low.green",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                }
                            ],
                            "extra_lasts": [],
                        }
                    ],
                }
            ],
            "undeclared_modules": set(),
        }

    def test_layer_contract_populates_extra_lasts_one_indirect(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with three illegal ending points, only one indirect step.
        graph.add_import(
            importer="mypackage.low.yellow",
            imported="mypackage.utils.foo",
            line_number=1,
            line_contents="-",
        )
        for ending_point in (
            "mypackage.high.blue",
            "mypackage.high.green",
            "mypackage.high.red",
        ):
            graph.add_import(
                importer="mypackage.utils.foo",
                imported=ending_point,
                line_number=3,
                line_contents="-",
            )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.yellow",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (1,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.high.blue",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.high.green",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.high.red",
                                    "line_numbers": (3,),
                                },
                            ],
                        }
                    ],
                }
            ],
            "undeclared_modules": set(),
        }

    def test_layer_contract_populates_extra_lasts_two_indirects(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with two illegal ending points, two indirect steps.
        graph.add_import(
            importer="mypackage.low.yellow",
            imported="mypackage.utils.foo",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=10,
            line_contents="-",
        )
        for ending_point in ("mypackage.high.blue", "mypackage.high.green"):
            graph.add_import(
                importer="mypackage.utils.bar",
                imported=ending_point,
                line_number=3,
                line_contents="-",
            )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.yellow",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (1,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.utils.bar",
                                    "line_numbers": (10,),
                                },
                                {
                                    "importer": "mypackage.utils.bar",
                                    "imported": "mypackage.high.blue",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [
                                {
                                    "importer": "mypackage.utils.bar",
                                    "imported": "mypackage.high.green",
                                    "line_numbers": (3,),
                                }
                            ],
                        }
                    ],
                }
            ],
            "undeclared_modules": set(),
        }

    def test_layer_contract_populates_firsts_and_lasts_three_indirects(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with illegal start and ending points, three indirect steps.
        for starting_point in ("mypackage.low.blue", "mypackage.low.green"):
            graph.add_import(
                importer=starting_point,
                imported="mypackage.utils.foo",
                line_number=3,
                line_contents="-",
            )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.bar",
            imported="mypackage.utils.baz",
            line_number=10,
            line_contents="-",
        )
        for ending_point in ("mypackage.high.red", "mypackage.high.yellow"):
            graph.add_import(
                importer="mypackage.utils.baz",
                imported=ending_point,
                line_number=5,
                line_contents="-",
            )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                },
                                {
                                    "importer": "mypackage.utils.foo",
                                    "imported": "mypackage.utils.bar",
                                    "line_numbers": (1,),
                                },
                                {
                                    "importer": "mypackage.utils.bar",
                                    "imported": "mypackage.utils.baz",
                                    "line_numbers": (10,),
                                },
                                {
                                    "importer": "mypackage.utils.baz",
                                    "imported": "mypackage.high.red",
                                    "line_numbers": (5,),
                                },
                            ],
                            "extra_firsts": [
                                {
                                    "importer": "mypackage.low.green",
                                    "imported": "mypackage.utils.foo",
                                    "line_numbers": (3,),
                                }
                            ],
                            "extra_lasts": [
                                {
                                    "importer": "mypackage.utils.baz",
                                    "imported": "mypackage.high.yellow",
                                    "line_numbers": (5,),
                                }
                            ],
                        }
                    ],
                }
            ],
            "undeclared_modules": set(),
        }

    @pytest.mark.parametrize(
        "graph_line_numbers, expected_line_numbers",
        [
            # Add a single import without line number. In this case we expect a None to indicate
            # that there was an import, but we don't where from.
            ((None,), (None,)),
            # Also add three similar imports between the same modules, only two of which contain the
            # line number. There is no way to tell from Grimp's API that there was actually a third
            # import added to the graph, so we expect just to display two line numbers.
            (
                (3, None, 20),
                (
                    3,
                    20,
                ),
            ),
        ],
    )
    def test_accepts_missing_line_numbers(self, graph_line_numbers, expected_line_numbers):
        """
        It's theoretically possible for a graph to have an import without an import details
        associated with it (if it's been manually put together). This test checks that
        the line number of such an import is encoded as a None value in the contract metadata.
        """
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        for line_number in graph_line_numbers:
            if line_number is None:
                import_kwargs = {}
            else:
                import_kwargs = dict(
                    line_number=line_number,
                    line_contents="-",
                )
            graph.add_import(
                importer="mypackage.low.white.gamma",
                imported="mypackage.high.yellow.alpha",
                **import_kwargs,
            )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept is False

        assert contract_check.metadata == {
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.white.gamma",
                                    "imported": "mypackage.high.yellow.alpha",
                                    "line_numbers": expected_line_numbers,
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        },
                    ],
                },
            ],
            "undeclared_modules": set(),
        }

    def _build_graph_without_imports(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.high",
            "mypackage.high.green",
            "mypackage.high.blue",
            "mypackage.high.yellow",
            "mypackage.high.yellow.alpha",
            "mypackage.medium",
            "mypackage.medium.orange",
            "mypackage.medium.orange.beta",
            "mypackage.medium.red",
            "mypackage.low",
            "mypackage.low.black",
            "mypackage.low.white",
            "mypackage.low.white.gamma",
        ):
            graph.add_module(module)
        return graph

    def _create_contract(self):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage"],
                "layers": ["high", "medium", "low"],
            },
        )


class TestIgnoreImports:
    @pytest.mark.parametrize(
        "expression",
        [
            "mypackage.low.black -> mypackage.medium.orange",
            # Wildcards.
            "*.low.black -> mypackage.medium.orange",
            "**.low.black -> mypackage.medium.orange",
            "mypackage.*.black -> mypackage.medium.orange",
            "mypackage.**.black -> mypackage.medium.orange",
            "mypackage.low.* -> mypackage.medium.orange",
            "mypackage.low.** -> mypackage.medium.orange",
            "mypackage.low.black -> *.medium.orange",
            "mypackage.low.black -> **.medium.orange",
            "mypackage.low.black -> mypackage.*.orange",
            "mypackage.low.black -> mypackage.**.orange",
            "mypackage.low.black -> mypackage.medium.*",
            "mypackage.low.black -> mypackage.medium.**",
            "mypackage.*.black -> mypackage.*.orange",
            "mypackage.**.black -> mypackage.**.orange",
            "mypackage.*.* -> mypackage.*.*",
            "mypackage.** -> mypackage.**",
        ],
    )
    def test_one_ignored_from_each_chain_means_contract_is_kept(self, expression):
        contract = self._build_contract(
            ignore_imports=[
                expression,
                "mypackage.utils.foo -> mypackage.utils.bar",
            ]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_ignore_only_one_chain_should_fail_because_of_the_other(self):
        contract = self._build_contract(
            ignore_imports=["mypackage.utils.bar -> mypackage.high.yellow.alpha"]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata["invalid_dependencies"] == [
            {
                "importer": "mypackage.low",
                "imported": "mypackage.medium",
                "routes": [
                    {
                        "chain": [
                            dict(
                                importer="mypackage.low.black",
                                imported="mypackage.medium.orange",
                                line_numbers=(1,),
                            )
                        ],
                        "extra_firsts": [],
                        "extra_lasts": [],
                    }
                ],
            }
        ]

    def test_multiple_ignore_from_same_chain_should_not_error(self):
        contract = self._build_contract(
            ignore_imports=[
                "mypackage.low.white.gamma -> mypackage.utils.foo",
                "mypackage.utils.bar -> mypackage.high.yellow.alpha",
            ]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata["invalid_dependencies"] == [
            {
                "imported": "mypackage.medium",
                "importer": "mypackage.low",
                "routes": [
                    {
                        "chain": [
                            dict(
                                importer="mypackage.low.black",
                                imported="mypackage.medium.orange",
                                line_numbers=(1,),
                            )
                        ],
                        "extra_firsts": [],
                        "extra_lasts": [],
                    }
                ],
            }
        ]

    @pytest.mark.parametrize(
        "expression",
        [
            "mypackage.nonexistent.foo -> mypackage.high",
            "mypackage.nonexistent.* -> mypackage.high",
        ],
    )
    def test_ignore_from_nonexistent_importer_raises_missing_import(self, expression):
        contract = self._build_contract(ignore_imports=[expression])
        graph = self._build_graph()
        message = f"No matches for ignored import {expression}."

        with pytest.raises(MissingImport, match=message):
            contract.check(graph=graph, verbose=False)

    @pytest.mark.parametrize(
        "expression",
        [
            "mypackage.high -> mypackage.nonexistent.foo",
            "mypackage.high -> mypackage.nonexistent.*",
        ],
    )
    def test_ignore_from_nonexistent_imported_raises_missing_import(self, expression):
        contract = self._build_contract(ignore_imports=[expression])
        graph = self._build_graph()
        message = f"No matches for ignored import {expression}."

        with pytest.raises(MissingImport, match=message):
            contract.check(graph=graph, verbose=False)

    def test_ignore_imports_tolerates_duplicates(self):
        contract = self._build_contract(
            ignore_imports=[
                "mypackage.low.black -> mypackage.medium.orange",
                "mypackage.utils.foo -> mypackage.utils.bar",
                "mypackage.low.black -> mypackage.medium.orange",
            ]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept

    def test_ignore_imports_adds_warnings(self):
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage"],
                "layers": ["high", "medium", "low"],
                "ignore_imports": [
                    "mypackage.high -> mypackage.nonexistent.*",
                    "mypackage.high -> mypackage.nonexistent.foo",
                ],
                "unmatched_ignore_imports_alerting": "warn",
            },
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph, verbose=False)

        assert set(contract_check.warnings) == {
            "No matches for ignored import mypackage.high -> mypackage.nonexistent.*.",
            "No matches for ignored import mypackage.high -> mypackage.nonexistent.foo.",
        }

    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.high",
            "mypackage.high.green",
            "mypackage.high.blue",
            "mypackage.high.yellow",
            "mypackage.high.yellow.alpha",
            "mypackage.medium",
            "mypackage.medium.orange",
            "mypackage.medium.orange.beta",
            "mypackage.medium.red",
            "mypackage.low",
            "mypackage.low.black",
            "mypackage.low.white",
            "mypackage.low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer="mypackage.high.green", imported="mypackage.medium.orange")
        graph.add_import(importer="mypackage.high.green", imported="mypackage.low.white.gamma")
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.low.white")
        graph.add_import(importer="mypackage.high.blue", imported="mypackage.utils")
        graph.add_import(importer="mypackage.utils", imported="mypackage.medium.red")

        # Direct illegal import.
        graph.add_import(
            importer="mypackage.low.black",
            imported="mypackage.medium.orange",
            line_number=1,
            line_contents="-",
        )
        # Indirect illegal import.
        graph.add_import(
            importer="mypackage.low.white.gamma",
            imported="mypackage.utils.foo",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.foo",
            imported="mypackage.utils.bar",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.utils.bar",
            imported="mypackage.high.yellow.alpha",
            line_number=1,
            line_contents="-",
        )

        return graph

    def _build_contract(self, ignore_imports):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage"],
                "layers": ["high", "medium", "low"],
                "ignore_imports": ignore_imports,
            },
        )


@pytest.mark.parametrize(
    "include_parentheses, should_raise_exception",
    (
        # (False, True),
        (True, False),
    ),
)
def test_optional_layers(include_parentheses, should_raise_exception):
    graph = ImportGraph()
    for module in (
        "mypackage",
        "mypackage.foo",
        "mypackage.foo.high",
        "mypackage.foo.high.blue",
        "mypackage.foo.low",
        "mypackage.foo.low.alpha",
    ):
        graph.add_module(module)

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "containers": ["mypackage.foo"],
            "layers": ["high", "(medium)" if include_parentheses else "medium", "low"],
        },
    )

    if should_raise_exception:
        with pytest.raises(
            ValueError,
            match=(
                "Missing layer in container 'mypackage.foo': "
                "module mypackage.foo.medium does not exist."
            ),
        ):
            contract.check(graph=graph, verbose=False)
    else:
        contract.check(graph=graph, verbose=False)


def test_missing_containerless_layers_raise_value_error():
    graph = ImportGraph()
    for module in ("foo", "foo.blue", "bar", "bar.green"):
        graph.add_module(module)

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_packages": ["foo", "bar"]},
        contract_options={"containers": [], "layers": ["foo", "bar", "baz"]},
    )

    with pytest.raises(ValueError, match=("Missing layer 'baz': module baz does not exist.")):
        contract.check(graph=graph, verbose=False)


def test_render_broken_contract():
    contract = LayersContract(
        name="Layers contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "containers": ["mypackage"],
            "layers": ["high", "medium", "low"],
        },
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "invalid_dependencies": [
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.high.yellow",
                                    "line_numbers": (6,),
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        },
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.green",
                                    "imported": "mypackage.high.blue",
                                    "line_numbers": (12,),
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        },
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.utils.red",
                                    "line_numbers": (8, 16),
                                },
                                {
                                    "importer": "mypackage.utils.red",
                                    "imported": "mypackage.utils.yellow",
                                    "line_numbers": (2,),
                                },
                                {
                                    "importer": "mypackage.utils.yellow",
                                    "imported": "mypackage.utils.brown",
                                    "line_numbers": (None,),
                                },
                                {
                                    "importer": "mypackage.utils.brown",
                                    "imported": "mypackage.high.green",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_firsts": [
                                {
                                    "importer": "mypackage.low.purple",
                                    "imported": "mypackage.utils.red",
                                    "line_numbers": (11,),
                                },
                                {
                                    "importer": "mypackage.low.white",
                                    "imported": "mypackage.utils.red",
                                    "line_numbers": (1,),
                                },
                            ],
                            "extra_lasts": [
                                {
                                    "importer": "mypackage.utils.brown",
                                    "imported": "mypackage.high.black",
                                    "line_numbers": (11,),
                                },
                                {
                                    "importer": "mypackage.utils.brown",
                                    "imported": "mypackage.high.white",
                                    "line_numbers": (8, 16),
                                },
                            ],
                        },
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.purple",
                                    "imported": "mypackage.utils.yellow",
                                    "line_numbers": (9,),
                                },
                                {
                                    "importer": "mypackage.utils.yellow",
                                    "imported": "mypackage.utils.brown",
                                    "line_numbers": (None,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        },
                    ],
                },
                {
                    "importer": "mypackage.low",
                    "imported": "mypackage.medium",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.low.blue",
                                    "imported": "mypackage.medium.yellow",
                                    "line_numbers": (6,),
                                }
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        }
                    ],
                },
                {
                    "importer": "mypackage.medium",
                    "imported": "mypackage.high",
                    "routes": [
                        {
                            "chain": [
                                {
                                    "importer": "mypackage.medium.blue",
                                    "imported": "mypackage.utils.yellow",
                                    "line_numbers": (8,),
                                },
                                {
                                    "importer": "mypackage.utils.yellow",
                                    "imported": "mypackage.utils.brown",
                                    "line_numbers": (None,),
                                },
                                {
                                    "importer": "mypackage.utils.brown",
                                    "imported": "mypackage.high.green",
                                    "line_numbers": (3,),
                                },
                            ],
                            "extra_firsts": [
                                {
                                    "importer": "mypackage.medium.white",
                                    "imported": "mypackage.utils.yellow",
                                    "line_numbers": (1, 10),
                                }
                            ],
                            "extra_lasts": [
                                {
                                    "importer": "mypackage.utils.brown",
                                    "imported": "mypackage.high.black",
                                    "line_numbers": (11,),
                                }
                            ],
                        }
                    ],
                },
            ],
            "undeclared_modules": {
                "mypackage.purple",
                "mypackage.green",
                "mypackage.brown",
            },
        },
    )

    with console.capture() as capture:
        contract.render_broken_contract(check)

    assert capture.get() == dedent(
        """\
        mypackage.low is not allowed to import mypackage.high:

        - mypackage.low.blue -> mypackage.high.yellow (l.6)

        - mypackage.low.green -> mypackage.high.blue (l.12)

        - mypackage.low.blue (l.8, l.16)
          & mypackage.low.purple (l.11)
          & mypackage.low.white -> mypackage.utils.red (l.1)
          mypackage.utils.red -> mypackage.utils.yellow (l.2)
          mypackage.utils.yellow -> mypackage.utils.brown (l.?)
          mypackage.utils.brown -> mypackage.high.green (l.3)
                                   & mypackage.high.black (l.11)
                                   & mypackage.high.white (l.8, l.16)

        - mypackage.low.purple -> mypackage.utils.yellow (l.9)
          mypackage.utils.yellow -> mypackage.utils.brown (l.?)


        mypackage.low is not allowed to import mypackage.medium:

        - mypackage.low.blue -> mypackage.medium.yellow (l.6)


        mypackage.medium is not allowed to import mypackage.high:

        - mypackage.medium.blue (l.8)
          & mypackage.medium.white -> mypackage.utils.yellow (l.1, l.10)
          mypackage.utils.yellow -> mypackage.utils.brown (l.?)
          mypackage.utils.brown -> mypackage.high.green (l.3)
                                   & mypackage.high.black (l.11)


        The following modules are not listed as layers:

        - mypackage.brown
        - mypackage.green
        - mypackage.purple

        (Since this contract is marked as 'exhaustive', every child of every container 
        must be declared as a layer.)

        """
    )


@pytest.mark.parametrize(
    "container",
    (
        "notingraph",
        "notingraph.foo",
        "notinpackage",  # In graph, but not in package.
        "notinpackage.foo",
        "notinpackage.foo.one",
        "mypackagebeginscorrectly",
    ),
)
def test_invalid_container(container):
    graph = ImportGraph()
    for module in (
        "mypackage",
        "mypackage.foo",
        "mypackage.foo.high",
        "mypackage.foo.medium",
        "mypackage.foo.low",
        "notinpackage",
        "mypackagebeginscorrectly",
    ):
        graph.add_module(module)

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "containers": ["mypackage.foo", container],
            "layers": ["high", "medium", "low"],
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            f"Invalid container '{container}': a container must either be a subpackage of "
            "mypackage, or mypackage itself."
        ),
    ):
        contract.check(graph=graph, verbose=False)


def test_invalid_container_multiple_packages():
    graph = ImportGraph()

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_packages": ["packageone", "packagetwo"]},
        contract_options={
            "containers": ["notinpackages"],
            "layers": ["high", "medium", "low"],
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Invalid container 'notinpackages': a container must either be a root package, "
            r"or a subpackage of one of them. \(The root packages are: packageone, packagetwo.\)"
        ),
    ):
        contract.check(graph=graph, verbose=False)


class TestLayerContractNoContainer:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract_without_containers(
            layers=["mypackage.high", "mypackage.medium", "mypackage.low"]
        )
        graph = self._build_legal_graph(container="mypackage")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_illegal_imports_means_contract_is_broken(self):
        contract = self._build_contract_without_containers(
            layers=["mypackage.high", "mypackage.medium", "mypackage.low"]
        )
        graph = self._build_legal_graph(container="mypackage")
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.high.green")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def test_no_illegal_imports_across_multiple_root_packages_means_contract_is_kept(
        self,
    ):
        contract = self._build_contract_without_containers(
            root_packages=["high", "medium", "low", "utils"],
            layers=["high", "medium", "low"],
        )
        graph = self._build_legal_graph()
        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

    def test_illegal_imports_across_multiple_root_packages_means_contract_is_broken(
        self,
    ):
        contract = self._build_contract_without_containers(layers=["high", "medium", "low"])
        graph = self._build_legal_graph()
        graph.add_import(importer="medium.orange", imported="high.green")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False

    def _build_legal_graph(self, container=None):
        graph = ImportGraph()
        if container:
            graph.add_module(container)
            namespace = f"{container}."
        else:
            namespace = ""

        for module in (
            f"{namespace}high",
            f"{namespace}high.green",
            f"{namespace}high.blue",
            f"{namespace}high.yellow",
            f"{namespace}high.yellow.alpha",
            f"{namespace}medium",
            f"{namespace}medium.orange",
            f"{namespace}medium.orange.beta",
            f"{namespace}medium.red",
            f"{namespace}low",
            f"{namespace}low.black",
            f"{namespace}low.white",
            f"{namespace}low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer=f"{namespace}high.green", imported=f"{namespace}medium.orange")
        graph.add_import(importer=f"{namespace}high.green", imported=f"{namespace}low.white.gamma")
        graph.add_import(importer=f"{namespace}medium.orange", imported=f"{namespace}low.white")
        graph.add_import(importer=f"{namespace}high.blue", imported=f"{namespace}utils")
        graph.add_import(importer=f"{namespace}utils", imported=f"{namespace}medium.red")

        return graph

    def _build_contract_without_containers(self, layers, root_packages=["mypackage"]):
        return LayersContract(
            name="Layer contract",
            session_options={"root_packages": root_packages},
            contract_options={"layers": layers},
        )


class TestLayersContractForNamespacePackages:
    @pytest.mark.parametrize(
        "containers, is_kept",
        [
            (
                (
                    "namespace.subnamespace.portiontwo.green",
                    "namespace.portionone.blue",
                ),
                True,
            ),
            (
                (
                    "namespace.subnamespace.portiontwo.green",
                    "namespace.subnamespace.portiontwo.blue",
                ),
                False,
            ),
        ],
    )
    def test_allows_namespace_containers(self, containers, is_kept):
        graph = ImportGraph()
        for module in (
            "portionone",
            "portionone.blue",
            "portionone.blue.high",
            "portionone.blue.middle",
            "portionone.blue.low",
            "subnamespace.portiontwo",
            "subnamespace.portiontwo.green",
            "subnamespace.portiontwo.green.high",
            "subnamespace.portiontwo.green.middle",
            "subnamespace.portiontwo.green.low",
            "subnamespace.portiontwo.blue",
            "subnamespace.portiontwo.blue.high",
            "subnamespace.portiontwo.blue.middle",
            "subnamespace.portiontwo.blue.low",
        ):
            graph.add_module(f"namespace.{module}")
        # Add legal imports
        for package in (
            "portionone.blue",
            "subnamespace.portiontwo.green",
            "subnamespace.portiontwo.blue",
        ):
            for importer_name, imported_name in (("high", "middle"), ("middle", "low")):
                graph.add_import(
                    importer=f"namespace.{package}.{importer_name}",
                    imported=f"namespace.{package}.{imported_name}",
                    line_number=3,
                    line_contents="-",
                )
        # Add an illegal import
        graph.add_import(
            importer="namespace.subnamespace.portiontwo.blue.low",
            imported="namespace.subnamespace.portiontwo.blue.middle",
            line_number=3,
            line_contents="-",
        )
        contract = LayersContract(
            name="Layers contract",
            session_options={
                "root_packages": [
                    "namespace.portionone",
                    "namespace.subnamespace.portiontwo",
                ]
            },
            contract_options={
                "layers": ["high", "middle", "low"],
                "containers": containers,
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept == is_kept


class TestExhaustiveContracts:
    def test_requires_containers(self):
        with pytest.raises(InvalidContractOptions) as exc_info:
            LayersContract(
                name="Layer contract",
                session_options={"root_packages": ["foo"]},
                contract_options={"layers": ["red", "green"], "exhaustive": "true"},
            )

        assert exc_info.value.args[0] == {
            "exhaustive": "The exhaustive option is not supported for contracts without containers."
        }

    def test_fails_for_single_missing_layer(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo"]},
            contract_options={
                "containers": ["foo"],
                "layers": ["red", "green"],
                "exhaustive": "true",
            },
        )
        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata == {
            "invalid_dependencies": [],
            "undeclared_modules": {"foo.blue"},
        }

    def test_kept_for_ignored_single_missing_layer(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo"]},
            contract_options={
                "containers": ["foo"],
                "layers": ["red", "green"],
                "exhaustive": "true",
                "exhaustive_ignores": ["blue"],
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept

    def test_not_kept_for_multiple_missing_layers(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo"]},
            contract_options={
                "containers": ["foo"],
                "layers": ["red"],
                "exhaustive": "true",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata == {
            "invalid_dependencies": [],
            "undeclared_modules": {"foo.blue", "foo.green"},
        }

    def test_not_kept_for_multiple_missing_layers_some_ignored(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo"]},
            contract_options={
                "containers": ["foo"],
                "layers": ["red"],
                "exhaustive": "true",
                "exhaustive_ignores": ["blue"],
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata == {
            "invalid_dependencies": [],
            "undeclared_modules": {"foo.green"},
        }

    def test_multiple_containers_valid_contract(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo", "bar"]},
            contract_options={
                "containers": ["foo", "bar"],
                "layers": ["red", "green"],
                "exhaustive": "true",
                "exhaustive_ignores": ["blue"],
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept

    @pytest.mark.parametrize("optional_layers_exist", (True, False))
    def test_multiple_containers_optional_layers(self, optional_layers_exist):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo", "bar"]},
            contract_options={
                "containers": ["foo", "bar"],
                "layers": ["red", "green", "(blue)"],
                "exhaustive": "true",
            },
        )
        if optional_layers_exist:
            graph.add_module("foo.blue")
            graph.add_module("bar.blue")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept

    def test_undeclared_modules_in_multiple_containers(self):
        graph = self._setup_graph()
        contract = LayersContract(
            name="Layer contract",
            session_options={"root_packages": ["foo", "bar"]},
            contract_options={
                "containers": ["foo", "bar"],
                "layers": ["red", "green"],
                "exhaustive": "true",
            },
        )
        # Add modules so the undeclared modules are different across containers.
        graph.add_module("foo.brown")
        graph.add_module("bar.yellow")

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is False
        assert contract_check.metadata == {
            "invalid_dependencies": [],
            "undeclared_modules": {"bar.blue", "bar.yellow", "foo.blue", "foo.brown"},
        }

    def _setup_graph(self):
        graph = ImportGraph()
        for container in ("foo", "bar"):
            for module in [
                container,
                f"{container}.red",
                f"{container}.blue",
                f"{container}.green",
            ]:
                graph.add_module(module)

        return graph


def _get_sorted_metadata(contract_check: ContractCheck) -> dict:
    return {
        "invalid_dependencies": sorted(
            contract_check.metadata["invalid_dependencies"],
            key=lambda c: (c["importer"], c["imported"]),
        ),
        "undeclared_modules": contract_check.metadata["undeclared_modules"],
    }
