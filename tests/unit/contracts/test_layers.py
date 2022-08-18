import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore

from importlinter.application.app_config import settings
from importlinter.contracts.layers import LayersContract
from importlinter.domain.contract import ContractCheck
from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import Module
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
            session_options={"root_packages": ["mypackage"]},
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
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "containers": ["mypackage.one", "mypackage.two", "mypackage.three"],
                "layers": ["high", "medium", "low"],
            },
        )


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

        contract_check = contract.check(graph=graph)
        assert contract_check.kept is False

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.medium",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
                    "higher_layer": "mypackage.medium",
                    "lower_layer": "mypackage.low",
                    "chains": [
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
            ]
        }

    def test_layer_contract_populates_extra_firsts_one_indirect(self):
        graph = self._build_graph_without_imports()
        contract = self._create_contract()

        # Add imports with three illegal starting points, only one indirect step.
        for starting_point in ("mypackage.low.blue", "mypackage.low.green", "mypackage.low.red"):
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

        contract_check = contract.check(graph=graph)

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
            ]
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

        contract_check = contract.check(graph=graph)

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
            ]
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
        for ending_point in ("mypackage.high.blue", "mypackage.high.green", "mypackage.high.red"):
            graph.add_import(
                importer="mypackage.utils.foo",
                imported=ending_point,
                line_number=3,
                line_contents="-",
            )

        contract_check = contract.check(graph=graph)

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
            ]
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

        contract_check = contract.check(graph=graph)

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
            ]
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

        contract_check = contract.check(graph=graph)

        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
            ]
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
            contract_options={"containers": ["mypackage"], "layers": ["high", "medium", "low"]},
        )


class TestIgnoreImports:
    @pytest.mark.parametrize(
        "expression",
        [
            "mypackage.low.black -> mypackage.medium.orange",
            # Wildcards.
            "*.low.black -> mypackage.medium.orange",
            "mypackage.*.black -> mypackage.medium.orange",
            "mypackage.low.* -> mypackage.medium.orange",
            "mypackage.low.black -> *.medium.orange",
            "mypackage.low.black -> mypackage.*.orange",
            "mypackage.low.black -> mypackage.medium.*",
            "mypackage.*.black -> mypackage.*.orange",
            "mypackage.*.* -> mypackage.*.*",
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
                "lower_layer": "mypackage.low",
                "higher_layer": "mypackage.medium",
                "chains": [
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

        contract_check = contract.check(graph=graph)

        assert contract_check.kept is False
        assert contract_check.metadata["invalid_chains"] == [
            {
                "higher_layer": "mypackage.medium",
                "lower_layer": "mypackage.low",
                "chains": [
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
            contract.check(graph=graph)

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
            contract.check(graph=graph)

    def test_ignore_imports_tolerates_duplicates(self):
        contract = self._build_contract(
            ignore_imports=[
                "mypackage.low.black -> mypackage.medium.orange",
                "mypackage.utils.foo -> mypackage.utils.bar",
                "mypackage.low.black -> mypackage.medium.orange",
            ]
        )
        graph = self._build_graph()

        contract_check = contract.check(graph=graph)

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

        contract_check = contract.check(graph=graph)

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
            contract.check(graph=graph)
    else:
        contract.check(graph=graph)


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
        session_options={"root_packages": ["mypackage"]},
        contract_options={"containers": ["mypackage"], "layers": ["high", "medium", "low"]},
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "invalid_chains": [
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
                                    "line_numbers": (10,),
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
                                    "line_numbers": (10,),
                                },
                            ],
                            "extra_firsts": [],
                            "extra_lasts": [],
                        },
                    ],
                },
                {
                    "lower_layer": "mypackage.low",
                    "higher_layer": "mypackage.medium",
                    "chains": [
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
                    "lower_layer": "mypackage.medium",
                    "higher_layer": "mypackage.high",
                    "chains": [
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
                                    "line_numbers": (10,),
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
            ]
        },
    )

    contract.render_broken_contract(check)

    settings.PRINTER.pop_and_assert(
        """
        mypackage.low is not allowed to import mypackage.high:

        - mypackage.low.blue -> mypackage.high.yellow (l.6)

        - mypackage.low.green -> mypackage.high.blue (l.12)

        - mypackage.low.blue (l.8, l.16)
          & mypackage.low.purple (l.11)
          & mypackage.low.white -> mypackage.utils.red (l.1)
          mypackage.utils.red -> mypackage.utils.yellow (l.2)
          mypackage.utils.yellow -> mypackage.utils.brown (l.10)
          mypackage.utils.brown -> mypackage.high.green (l.3)
                                   & mypackage.high.black (l.11)
                                   & mypackage.high.white (l.8, l.16)

        - mypackage.low.purple -> mypackage.utils.yellow (l.9)
          mypackage.utils.yellow -> mypackage.utils.brown (l.10)


        mypackage.low is not allowed to import mypackage.medium:

        - mypackage.low.blue -> mypackage.medium.yellow (l.6)


        mypackage.medium is not allowed to import mypackage.high:

        - mypackage.medium.blue (l.8)
          & mypackage.medium.white -> mypackage.utils.yellow (l.1, l.10)
          mypackage.utils.yellow -> mypackage.utils.brown (l.10)
          mypackage.utils.brown -> mypackage.high.green (l.3)
                                   & mypackage.high.black (l.11)


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
            contract_options={"layers": layers},
        )


class TestGetIndirectCollapsedChains:
    def test_no_chains(self):
        graph = self._build_legal_graph()

        assert [] == LayersContract._get_indirect_collapsed_chains(
            graph, importer_package=Module("medium"), imported_package=Module("high")
        )

    def test_direct_imports_raises_value_error(self):
        graph = self._build_legal_graph()

        self._make_detailed_chain_and_add_to_graph(graph, "medium.orange", "high.yellow")

        with pytest.raises(
            ValueError, match="Direct chain found - these should have been removed."
        ):
            LayersContract._get_indirect_collapsed_chains(
                graph, importer_package=Module("medium"), imported_package=Module("high")
            )

    def test_chain_length_2_is_included(self):
        graph = self._build_legal_graph()

        chain = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.orange", "utils.brown", "high.yellow"
        )

        assert [
            {"chain": chain, "extra_firsts": [], "extra_lasts": []}
        ] == LayersContract._get_indirect_collapsed_chains(
            graph, importer_package=Module("medium"), imported_package=Module("high")
        )

    def test_chain_length_3_is_included(self):
        graph = self._build_legal_graph()

        chain = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.orange", "utils.brown", "utils.grey", "high.yellow"
        )

        assert [
            {"chain": chain, "extra_firsts": [], "extra_lasts": []}
        ] == LayersContract._get_indirect_collapsed_chains(
            graph, importer_package=Module("medium"), imported_package=Module("high")
        )

    def test_multiple_chains_of_length_2_same_segment(self):
        graph = self._build_legal_graph()

        chain1 = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.blue", "utils.brown", "high.green.foo"
        )
        chain2 = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.orange.foo", "utils.brown", "high.yellow"
        )

        assert [
            {"chain": chain1, "extra_firsts": [chain2[0]], "extra_lasts": [chain2[-1]]}
        ] == LayersContract._get_indirect_collapsed_chains(
            graph, importer_package=Module("medium"), imported_package=Module("high")
        )

    def test_multiple_chains_of_length_3_same_segment(self):
        graph = self._build_legal_graph()

        chain1 = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.blue", "utils.brown", "utils.grey", "high"
        )
        chain2 = self._make_detailed_chain_and_add_to_graph(
            graph, "medium.orange.foo", "utils.brown", "utils.grey", "high.yellow"
        )

        assert [
            {"chain": chain1, "extra_firsts": [chain2[0]], "extra_lasts": [chain2[-1]]}
        ] == LayersContract._get_indirect_collapsed_chains(
            graph, importer_package=Module("medium"), imported_package=Module("high")
        )

    def _build_legal_graph(self):
        graph = ImportGraph()

        for module in (
            "high",
            "high.green",
            "high.blue",
            "high.yellow",
            "high.yellow.alpha",
            "medium",
            "medium.orange",
            "medium.orange.beta",
            "medium.red",
            "low",
            "low.black",
            "low.white",
            "low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer="high.green", imported="medium.orange")
        graph.add_import(importer="high.green", imported="low.white.gamma")
        graph.add_import(importer="medium.orange", imported="low.white")
        graph.add_import(importer="high.blue", imported="utils")
        graph.add_import(importer="utils", imported="medium.red")

        return graph

    def _make_detailed_chain_and_add_to_graph(self, graph, *items):
        detailed_chain = []
        for index in range(len(items) - 1):
            line_numbers = (3, index + 100)  # Some identifiable line numbers.
            direct_import = {
                "importer": items[index],
                "imported": items[index + 1],
                "line_numbers": line_numbers,
            }
            for line_number in line_numbers:
                graph.add_import(
                    importer=direct_import["importer"],
                    imported=direct_import["imported"],
                    line_number=line_number,
                    line_contents="Foo",
                )
            detailed_chain.append(direct_import)
        return detailed_chain


class TestLayersContractForNamespacePackages:
    @pytest.mark.parametrize(
        "containers, is_kept",
        [
            (("namespace.subnamespace.portiontwo.green", "namespace.portionone.blue"), True),
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
                "root_packages": ["namespace.portionone", "namespace.subnamespace.portiontwo"]
            },
            contract_options={
                "layers": ["high", "middle", "low"],
                "containers": containers,
            },
        )

        contract_check = contract.check(graph=graph)

        assert contract_check.kept == is_kept


class TestPopDirectImports:
    def test_direct_import_between_descendants(self):
        graph = self._build_graph()
        direct_import = self._add_direct_import(graph, importer="low.green", imported="high.blue")

        # Add some other imports that we don't want to be affected.
        other_imports = self._add_other_imports(graph, importer="low.green", imported="high.blue")

        result = LayersContract._pop_direct_imports(
            higher_layer_package=Module("high"), lower_layer_package=Module("low"), graph=graph
        )

        assert [[direct_import]] == result
        self._assert_import_was_popped(graph, direct_import)
        self._assert_imports_were_not_popped(graph, other_imports)

    def test_direct_import_between_roots(self):
        graph = self._build_graph()
        direct_import = self._add_direct_import(graph, importer="low", imported="high")

        # Add some other imports that we don't want to be affected.
        other_imports = self._add_other_imports(graph, importer="low", imported="high")

        result = LayersContract._pop_direct_imports(
            higher_layer_package=Module("high"), lower_layer_package=Module("low"), graph=graph
        )

        assert [[direct_import]] == result
        self._assert_import_was_popped(graph, direct_import)
        self._assert_imports_were_not_popped(graph, other_imports)

    def test_direct_import_root_to_descendant(self):
        graph = self._build_graph()
        direct_import = self._add_direct_import(graph, importer="low", imported="high.blue")

        # Add some other imports that we don't want to be affected.
        other_imports = self._add_other_imports(graph, importer="low", imported="high.blue")

        result = LayersContract._pop_direct_imports(
            higher_layer_package=Module("high"), lower_layer_package=Module("low"), graph=graph
        )

        assert [[direct_import]] == result
        self._assert_import_was_popped(graph, direct_import)
        self._assert_imports_were_not_popped(graph, other_imports)

    def test_direct_import_descendant_to_root(self):
        graph = self._build_graph()
        direct_import = self._add_direct_import(graph, importer="low.green", imported="high")

        # Add some other imports that we don't want to be affected.
        other_imports = self._add_other_imports(graph, importer="low.green", imported="high")

        result = LayersContract._pop_direct_imports(
            higher_layer_package=Module("high"), lower_layer_package=Module("low"), graph=graph
        )

        assert [[direct_import]] == result
        self._assert_import_was_popped(graph, direct_import)
        self._assert_imports_were_not_popped(graph, other_imports)

    def _build_graph(self):
        graph = ImportGraph()
        graph.add_module("high")
        graph.add_module("low")
        return graph

    def _add_direct_import(self, graph, importer, imported):
        direct_import = dict(
            importer=importer, imported=imported, line_number=99, line_contents="blah"
        )
        graph.add_import(**direct_import)
        return direct_import

    def _add_other_imports(self, graph, importer, imported):
        other_imports = (
            dict(importer=importer, imported="foo", line_number=2, line_contents="blah"),
            dict(importer="bar", imported=imported, line_number=3, line_contents="blah"),
        )
        for other_import in other_imports:
            graph.add_import(**other_import)
        return other_imports

    def _assert_import_was_popped(self, graph, direct_import):
        assert not graph.direct_import_exists(
            importer=direct_import["importer"], imported=direct_import["imported"]
        )

    def _assert_imports_were_not_popped(self, graph, other_imports):
        for other_import in other_imports:
            assert graph.direct_import_exists(
                importer=other_import["importer"], imported=other_import["imported"]
            )
