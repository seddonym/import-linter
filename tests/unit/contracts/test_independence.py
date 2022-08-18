import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore

from importlinter.application.app_config import settings
from importlinter.contracts.independence import IndependenceContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.printing import FakePrinter


class TestIndependenceContract:
    def _build_default_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.blue",
            "mypackage.blue.alpha",
            "mypackage.blue.beta",
            "mypackage.blue.beta.foo",
            "mypackage.green",
            "mypackage.yellow",
            "mypackage.yellow.gamma",
            "mypackage.yellow.delta",
            "mypackage.other",
        ):
            graph.add_module(module)
        return graph

    def _check_default_contract(self, graph):
        contract = IndependenceContract(
            name="Independence contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "modules": ("mypackage.blue", "mypackage.green", "mypackage.yellow")
            },
        )
        return contract.check(graph=graph)

    def test_when_modules_are_independent(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.green",
            imported="mypackage.other",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert contract_check.kept

    def test_when_root_imports_root_directly(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.green",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue",
                                "imported": "mypackage.green",
                                "line_numbers": (10,),
                            }
                        ]
                    ],
                }
            ]
        }
        assert expected_metadata == contract_check.metadata

    def test_when_root_imports_root_indirectly(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.green",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue",
                                "imported": "mypackage.other",
                                "line_numbers": (10,),
                            },
                            {
                                "importer": "mypackage.other",
                                "imported": "mypackage.green",
                                "line_numbers": (11,),
                            },
                        ]
                    ],
                }
            ]
        }
        assert expected_metadata == contract_check.metadata

    def test_chains_via_other_independent_modules(self):
        # In this case, all chains are included, even though they are repeated elsewhere in the
        # contract check (we may want to change this).
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.green",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.yellow",
            imported="mypackage.blue",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue",
                                "imported": "mypackage.green",
                                "line_numbers": (10,),
                            }
                        ]
                    ],
                },
                {
                    "upstream_module": "mypackage.blue",
                    "downstream_module": "mypackage.yellow",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.yellow",
                                "imported": "mypackage.blue",
                                "line_numbers": (11,),
                            }
                        ]
                    ],
                },
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.yellow",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.yellow",
                                "imported": "mypackage.blue",
                                "line_numbers": (11,),
                            },
                            {
                                "importer": "mypackage.blue",
                                "imported": "mypackage.green",
                                "line_numbers": (10,),
                            },
                        ]
                    ],
                },
            ]
        }
        assert expected_metadata == contract_check.metadata

    def test_when_child_imports_child(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue.alpha",
            imported="mypackage.yellow.gamma",
            line_number=5,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.yellow",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue.alpha",
                                "imported": "mypackage.yellow.gamma",
                                "line_numbers": (5,),
                            }
                        ]
                    ],
                }
            ]
        }
        assert expected_metadata == contract_check.metadata

    def test_when_grandchild_imports_root(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue.beta.foo",
            imported="mypackage.green",
            line_number=8,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue.beta.foo",
                                "imported": "mypackage.green",
                                "line_numbers": (8,),
                            }
                        ]
                    ],
                }
            ]
        }
        assert expected_metadata == contract_check.metadata


@pytest.mark.parametrize(
    "ignore_imports, is_kept",
    (
        (["mypackage.a -> mypackage.irrelevant"], False),
        (["mypackage.a -> mypackage.indirect"], True),
        (["mypackage.indirect -> mypackage.b"], True),
        # Wildcards
        (["mypackage.a -> *.irrelevant"], False),
        (["*.a -> *.indirect"], True),
        (["mypackage.* -> mypackage.b"], True),
    ),
)
def test_ignore_imports(ignore_imports, is_kept):
    graph = ImportGraph()
    graph.add_module("mypackage")
    graph.add_import(
        importer="mypackage.a", imported="mypackage.irrelevant", line_number=1, line_contents="-"
    )
    graph.add_import(
        importer="mypackage.a", imported="mypackage.indirect", line_number=1, line_contents="-"
    )
    graph.add_import(
        importer="mypackage.indirect", imported="mypackage.b", line_number=1, line_contents="-"
    )
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "modules": ("mypackage.a", "mypackage.b"),
            "ignore_imports": ignore_imports,
        },
    )

    contract_check = contract.check(graph=graph)

    assert is_kept == contract_check.kept


def test_ignore_imports_adds_warnings():
    graph = ImportGraph()
    graph.add_module("mypackage")
    graph.add_import(
        importer="mypackage.green", imported="mypackage.blue", line_number=1, line_contents="-"
    )
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "modules": ("mypackage.green", "mypackage.blue"),
            "ignore_imports": [
                "mypackage.green.* -> mypackage.blue",
                "mypackage.nonexistent -> mypackage.blue",
            ],
            "unmatched_ignore_imports_alerting": "warn",
        },
    )

    contract_check = contract.check(graph=graph)

    assert set(contract_check.warnings) == {
        "No matches for ignored import mypackage.green.* -> mypackage.blue.",
        "No matches for ignored import mypackage.nonexistent -> mypackage.blue.",
    }


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={"modules": ["mypackage.blue", "mypackage.green", "mypackage.yellow"]},
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.yellow",
                    "downstream_module": "mypackage.blue",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.blue.foo",
                                "imported": "mypackage.utils.red",
                                "line_numbers": (16, 102),
                            },
                            {
                                "importer": "mypackage.utils.red",
                                "imported": "mypackage.utils.brown",
                                "line_numbers": (1,),
                            },
                            {
                                "importer": "mypackage.utils.brown",
                                "imported": "mypackage.yellow.bar",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.blue.bar",
                                "imported": "mypackage.yellow.baz",
                                "line_numbers": (5,),
                            }
                        ],
                    ],
                },
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.yellow",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.yellow.foo",
                                "imported": "mypackage.green.bar",
                                "line_numbers": (15,),
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
        mypackage.blue is not allowed to import mypackage.yellow:

        -   mypackage.blue.foo -> mypackage.utils.red (l.16, l.102)
            mypackage.utils.red -> mypackage.utils.brown (l.1)
            mypackage.utils.brown -> mypackage.yellow.bar (l.3)

        -   mypackage.blue.bar -> mypackage.yellow.baz (l.5)


        mypackage.yellow is not allowed to import mypackage.green:

        -   mypackage.yellow.foo -> mypackage.green.bar (l.15)


        """
    )


def test_missing_module():
    graph = ImportGraph()
    for module in ("mypackage", "mypackage.foo"):
        graph.add_module(module)

    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={"modules": ["mypackage.foo", "mypackage.bar"]},
    )

    with pytest.raises(ValueError, match=("Module 'mypackage.bar' does not exist.")):
        contract.check(graph=graph)


def test_ignore_imports_tolerates_duplicates():
    graph = ImportGraph()
    graph.add_module("mypackage")
    graph.add_import(
        importer="mypackage.a", imported="mypackage.b", line_number=1, line_contents="-"
    )
    graph.add_import(
        importer="mypackage.a", imported="mypackage.c", line_number=2, line_contents="-"
    )
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={
            "modules": ("mypackage.a", "mypackage.b"),
            "ignore_imports": [
                "mypackage.a -> mypackage.b",
                "mypackage.a -> mypackage.c",
                "mypackage.a -> mypackage.b",
            ],
        },
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept


@pytest.mark.parametrize(
    "independent_modules, is_kept",
    (
        (("namespace.portionone.blue", "namespace.subnamespace.portiontwo.blue"), True),
        (("namespace.portionone.blue", "namespace.subnamespace.portiontwo.green"), False),
        (
            ("namespace.subnamespace.portiontwo.blue", "namespace.subnamespace.portiontwo.green"),
            False,
        ),
    ),
)
def test_namespace_packages(independent_modules, is_kept):
    graph = ImportGraph()
    for module in (
        "portionone",
        "portionone.blue",
        "subnamespace.portiontwo",
        "subnamespace.portiontwo.green",
        "subnamespace.portiontwo.blue",
    ):
        graph.add_module(f"namespace.{module}")
    # Add imports between portions to another.
    graph.add_import(
        importer="namespace.portionone.blue",
        imported="namespace.subnamespace.portiontwo.green",
        line_number=3,
        line_contents="-",
    )
    graph.add_import(
        importer="namespace.subnamespace.portiontwo.blue",
        imported="namespace.subnamespace.portiontwo.green",
        line_number=3,
        line_contents="-",
    )

    contract = IndependenceContract(
        name="Independence contract",
        session_options={
            "root_packages": ["namespace.portionone", "namespace.subnamespace.portiontwo"]
        },
        contract_options={
            "modules": independent_modules,
        },
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept == is_kept
