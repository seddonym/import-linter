import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore
from importlinter.application.app_config import settings
from importlinter.contracts.layers import LayersContract
from importlinter.domain.contract import ContractCheck
from importlinter.domain.helpers import MissingImport

from tests.adapters.printing import FakePrinter


class TestLayerContractSingleContainers:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract()
        graph = self._build_graph()

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    def test_illegal_child_imports_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.high.green")

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is False

    def test_illegal_grandchild_to_child_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(importer="mypackage.low.white.gamma", imported="mypackage.medium.red")

        contract_check = contract.check(graph=graph)

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
            session_options={"root_package": "mypackage"},
            contract_options={"containers": ["mypackage"], "layers": ["high", "medium", "low"]},
        )


class TestLayerMultipleContainers:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract()
        graph = self._build_graph()

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    def test_imports_from_low_to_high_but_in_different_container_doesnt_break_contract(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.two.medium.green.beta", imported="mypackage.one.high.green"
        )
        graph.add_import(
            importer="mypackage.three.low.cyan", imported="mypackage.two.high.red.alpha"
        )

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    def test_illegal_grandchild_imports_means_contract_is_broken(self):
        contract = self._build_contract()
        graph = self._build_graph()
        graph.add_import(
            importer="mypackage.two.medium.green.beta", imported="mypackage.two.high.red.alpha"
        )

        contract_check = contract.check(graph=graph)

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
        ):
            graph.add_module(module)

        # Add some 'legal' imports, each within their separate containers.
        graph.add_import(
            importer="mypackage.one.high.green", imported="mypackage.one.medium.orange"
        )
        graph.add_import(
            importer="mypackage.one.high.green", imported="mypackage.one.low.white.gamma"
        )
        graph.add_import(
            importer="mypackage.one.medium.orange", imported="mypackage.one.low.white"
        )

        graph.add_import(
            importer="mypackage.two.high.red.alpha", imported="mypackage.two.medium.green.beta"
        )
        graph.add_import(
            importer="mypackage.two.high.red.alpha", imported="mypackage.two.low.blue.gamma"
        )
        graph.add_import(
            importer="mypackage.two.medium.green.beta", imported="mypackage.two.low.blue.gamma"
        )

        graph.add_import(
            importer="mypackage.three.high.white", imported="mypackage.three.medium.purple"
        )
        graph.add_import(
            importer="mypackage.three.high.white", imported="mypackage.three.low.cyan"
        )
        graph.add_import(
            importer="mypackage.three.medium.purple", imported="mypackage.three.low.cyan"
        )

        return graph

    def _build_contract(self):
        return LayersContract(
            name="Layer contract",
            session_options={"root_package": "mypackage"},
            contract_options={
                "containers": ["mypackage.one", "mypackage.two", "mypackage.three"],
                "layers": ["high", "medium", "low"],
            },
        )


def test_layer_contract_populates_metadata():
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
    graph.add_import(
        importer="mypackage.low.white.gamma",
        imported="mypackage.utils.foo",
        line_number=3,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.utils.foo",
        imported="mypackage.utils.bar",
        line_number=1,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.utils.foo",
        imported="mypackage.utils.bar",
        line_number=101,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.utils.bar",
        imported="mypackage.high.yellow.alpha",
        line_number=13,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.medium.orange.beta",
        imported="mypackage.high.blue",
        line_number=2,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.low.black",
        imported="mypackage.utils.baz",
        line_number=2,
        line_contents="-",
    ),
    graph.add_import(
        importer="mypackage.utils.baz",
        imported="mypackage.medium.red",
        line_number=3,
        line_contents="-",
    ),

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_package": "mypackage"},
        contract_options={"containers": ["mypackage"], "layers": ["high", "medium", "low"]},
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept is False

    assert contract_check.metadata == {
        "invalid_chains": [
            {
                "higher_layer": "mypackage.high",
                "lower_layer": "mypackage.medium",
                "chains": [
                    [
                        {
                            "importer": "mypackage.medium.orange.beta",
                            "imported": "mypackage.high.blue",
                            "line_numbers": (2,),
                        }
                    ]
                ],
            },
            {
                "higher_layer": "mypackage.high",
                "lower_layer": "mypackage.low",
                "chains": [
                    [
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
                    ]
                ],
            },
            {
                "higher_layer": "mypackage.medium",
                "lower_layer": "mypackage.low",
                "chains": [
                    [
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
                    ]
                ],
            },
        ]
    }


class TestIgnoreImports:
    def test_one_ignored_from_each_chain_means_contract_is_kept(self):
        contract = self._build_contract(
            ignore_imports=[
                "mypackage.low.black -> mypackage.medium.orange",
                "mypackage.utils.foo -> mypackage.utils.bar",
            ]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    def test_ignore_only_one_chain_should_fail_because_of_the_other(self):
        contract = self._build_contract(
            ignore_imports=["mypackage.utils.bar -> mypackage.high.yellow.alpha"]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is False
        assert contract_check.metadata["invalid_chains"] == [
            {
                "higher_layer": "mypackage.medium",
                "lower_layer": "mypackage.low",
                "chains": [
                    [
                        dict(
                            importer="mypackage.low.black",
                            imported="mypackage.medium.orange",
                            line_numbers=(1,),
                        )
                    ]
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

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is False
        assert contract_check.metadata["invalid_chains"] == [
            {
                "higher_layer": "mypackage.medium",
                "lower_layer": "mypackage.low",
                "chains": [
                    [
                        dict(
                            importer="mypackage.low.black",
                            imported="mypackage.medium.orange",
                            line_numbers=(1,),
                        )
                    ]
                ],
            }
        ]

    def test_ignore_from_nonexistent_importer_raises_missing_import(self):
        contract = self._build_contract(
            ignore_imports=["mypackage.nonexistent.foo -> mypackage.high"]
        )
        graph = self._build_graph()

        with pytest.raises(MissingImport):
            contract.check(graph=graph)

    def test_ignore_from_nonexistent_imported_raises_missing_import(self):
        contract = self._build_contract(
            ignore_imports=["mypackage.high -> mypackage.nonexistent.foo"]
        )
        graph = self._build_graph()

        with pytest.raises(MissingImport):
            contract.check(graph=graph)

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
            session_options={"root_package": "mypackage"},
            contract_options={
                "containers": ["mypackage"],
                "layers": ["high", "medium", "low"],
                "ignore_imports": ignore_imports,
            },
        )


@pytest.mark.parametrize(
    "include_parentheses, should_raise_exception", ((False, True), (True, False))
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
        session_options={"root_package": "mypackage"},
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
            contract.check(graph=graph)
    else:
        contract.check(graph=graph)


@pytest.mark.xfail
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
        contract.check(graph=graph)


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = LayersContract(
        name="Layers contract",
        session_options={"root_package": "mypackage"},
        contract_options={"containers": ["mypackage"], "layers": ["high", "medium", "low"]},
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "invalid_chains": [
                {
                    "higher_layer": "mypackage.high",
                    "lower_layer": "mypackage.low",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.low.blue",
                                "imported": "mypackage.utils.red",
                                "line_numbers": (8, 16),
                            },
                            {
                                "importer": "mypackage.utils.red",
                                "imported": "mypackage.utils.yellow",
                                "line_numbers": (1,),
                            },
                            {
                                "importer": "mypackage.utils.yellow",
                                "imported": "mypackage.high.green",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.low.purple",
                                "imported": "mypackage.high.brown",
                                "line_numbers": (9,),
                            }
                        ],
                    ],
                },
                {
                    "higher_layer": "mypackage.medium",
                    "lower_layer": "mypackage.low",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.low.blue",
                                "imported": "mypackage.medium.yellow",
                                "line_numbers": (6,),
                            }
                        ]
                    ],
                },
                {
                    "higher_layer": "mypackage.high",
                    "lower_layer": "mypackage.medium",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.medium",
                                "imported": "mypackage.high.cyan.alpha",
                                "line_numbers": (2,),
                            }
                        ]
                    ],
                },
            ]
        },
    )

    contract.render_broken_contract(check)

    settings.PRINTER.pop_and_assert(
        """
        mypackage.low is not allowed to import mypackage.high:

        -   mypackage.low.blue -> mypackage.utils.red (l.8, l.16)
            mypackage.utils.red -> mypackage.utils.yellow (l.1)
            mypackage.utils.yellow -> mypackage.high.green (l.3)

        -   mypackage.low.purple -> mypackage.high.brown (l.9)


        mypackage.low is not allowed to import mypackage.medium:

        -   mypackage.low.blue -> mypackage.medium.yellow (l.6)


        mypackage.medium is not allowed to import mypackage.high:

        -   mypackage.medium -> mypackage.high.cyan.alpha (l.2)


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
        session_options={"root_package": "mypackage"},
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
        contract.check(graph=graph)


def test_invalid_container_multiple_packages():
    graph = ImportGraph()

    contract = LayersContract(
        name="Layer contract",
        session_options={"root_packages": ["packageone", "packagetwo"]},
        contract_options={"containers": ["notinpackages"], "layers": ["high", "medium", "low"]},
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Invalid container 'notinpackages': a container must either be a root package, "
            r"or a subpackage of one of them. \(The root packages are: packageone, packagetwo.\)"
        ),
    ):
        contract.check(graph=graph)


class TestLayerContractNoContainer:
    def test_no_illegal_imports_means_contract_is_kept(self):
        contract = self._build_contract_without_containers(
            layers=["mypackage.high", "mypackage.medium", "mypackage.low"]
        )
        graph = self._build_legal_graph(container="mypackage")

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    @pytest.mark.xfail
    def test_illegal_imports_means_contract_is_broken(self):
        contract = self._build_contract_without_containers(
            layers=["mypackage.high", "mypackage.medium", "mypackage.low"]
        )
        graph = self._build_legal_graph(container="mypackage")
        graph.add_import(importer="mypackage.medium.orange", imported="mypackage.high.green")

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is False

    def test_no_illegal_imports_across_multiple_root_packages_means_contract_is_kept(self):
        contract = self._build_contract_without_containers(
            root_packages=["high", "medium", "low", "utils"], layers=["high", "medium", "low"]
        )
        graph = self._build_legal_graph()
        contract_check = contract.check(graph=graph)

        assert contract_check.kept is True

    @pytest.mark.xfail
    def test_illegal_imports_across_multiple_root_packages_means_contract_is_broken(self):
        contract = self._build_contract_without_containers(layers=["high", "medium", "low"])
        graph = self._build_legal_graph()
        graph.add_import(importer="medium.orange", imported="high.green")

        contract_check = contract.check(graph=graph)

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
            contract_options={"containers": [], "layers": layers},
        )
