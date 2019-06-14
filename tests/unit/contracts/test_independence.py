import pytest

from importlinter.application.app_config import settings
from importlinter.contracts.independence import IndependenceContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.graph import FakeGraph
from tests.adapters.printing import FakePrinter


@pytest.mark.parametrize(
    "shortest_chains, expected_invalid_chains",
    (
        ({("blue", "orange"): ("blue", "orange"), ("brown", "blue"): ("brown", "blue")}, []),
        (
            {("blue", "green"): ("blue", "green")},
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
        ),
        (
            {("blue.beta.foo", "green"): ("blue.beta.foo", "orange.omega", "green")},
            {
                "upstream_module": "mypackage.green",
                "downstream_module": "mypackage.blue",
                "chains": [
                    [
                        {
                            "importer": "mypackage.blue.beta.foo",
                            "imported": "mypackage.orange.omega",
                            "line_numbers": (9, 109),
                        },
                        {
                            "importer": "mypackage.orange.omega",
                            "imported": "mypackage.green",
                            "line_numbers": (1,),
                        },
                    ]
                ],
            },
        ),
        (
            {("green", "blue.beta.foo"): ("green", "blue.beta.foo")},
            {
                "upstream_module": "mypackage.blue",
                "downstream_module": "mypackage.green",
                "chains": [
                    [
                        {
                            "importer": "mypackage.green",
                            "imported": "mypackage.blue.beta.foo",
                            "line_numbers": (8,),
                        }
                    ]
                ],
            },
        ),
        (
            {("blue", "yellow"): ("blue", "yellow")},
            {
                "upstream_module": "mypackage.yellow",
                "downstream_module": "mypackage.blue",
                "chains": [
                    [
                        {
                            "importer": "mypackage.blue",
                            "imported": "mypackage.yellow",
                            "line_numbers": (3,),
                        }
                    ]
                ],
            },
        ),
        (
            {("blue.beta.foo", "yellow.gamma"): ("blue.beta.foo", "yellow.gamma")},
            {
                "upstream_module": "mypackage.yellow",
                "downstream_module": "mypackage.blue",
                "chains": [
                    [
                        {
                            "importer": "mypackage.blue.beta.foo",
                            "imported": "mypackage.yellow.gamma",
                            "line_numbers": (100,),
                        }
                    ]
                ],
            },
        ),
        (
            {("yellow", "blue"): ("yellow", "blue")},
            {
                "upstream_module": "mypackage.blue",
                "downstream_module": "mypackage.yellow",
                "chains": [
                    [
                        {
                            "importer": "mypackage.yellow",
                            "imported": "mypackage.blue",
                            "line_numbers": (4,),
                        }
                    ]
                ],
            },
        ),
        (
            {("green", "yellow"): ("green", "yellow")},
            {
                "upstream_module": "mypackage.yellow",
                "downstream_module": "mypackage.green",
                "chains": [
                    [
                        {
                            "importer": "mypackage.green",
                            "imported": "mypackage.yellow",
                            "line_numbers": (6,),
                        }
                    ]
                ],
            },
        ),
        (
            {("yellow", "green"): ("yellow", "green")},
            {
                "upstream_module": "mypackage.green",
                "downstream_module": "mypackage.yellow",
                "chains": [
                    [
                        {
                            "importer": "mypackage.yellow",
                            "imported": "mypackage.green",
                            "line_numbers": (10,),
                        }
                    ]
                ],
            },
        ),
    ),
)
def test_independence_contract(shortest_chains, expected_invalid_chains):
    graph = FakeGraph(
        root_package_name="mypackage",
        descendants={"blue": {"alpha", "beta", "beta.foo"}, "yellow": {"gamma", "delta"}},
        import_details=[
            {
                "importer": "mypackage.blue",
                "imported": "mypackage.green",
                "line_number": 10,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.blue.beta.foo",
                "imported": "mypackage.orange.omega",
                "line_number": 9,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.blue.beta.foo",
                "imported": "mypackage.orange.omega",
                "line_number": 109,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.orange.omega",
                "imported": "mypackage.green",
                "line_number": 1,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.green",
                "imported": "mypackage.blue.beta.foo",
                "line_number": 8,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.blue",
                "imported": "mypackage.yellow",
                "line_number": 3,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.blue.beta.foo",
                "imported": "mypackage.yellow.gamma",
                "line_number": 100,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.yellow",
                "imported": "mypackage.blue",
                "line_number": 4,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.green",
                "imported": "mypackage.yellow",
                "line_number": 6,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.yellow",
                "imported": "mypackage.green",
                "line_number": 10,
                "line_contents": "-",
            },
        ],
        shortest_chains=shortest_chains,
        all_modules=[
            "mypackage",
            "mypackage.blue",
            "mypackage.blue.alpha",
            "mypackage.blue.beta",
            "mypackage.blue.beta.foo",
            "mypackage.green",
            "mypackage.yellow",
            "mypackage.yellow.gamma",
            "mypackage.yellow.delta",
        ],
    )
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_package": "mypackage"},
        contract_options={"modules": ("mypackage.blue", "mypackage.green", "mypackage.yellow")},
    )

    contract_check = contract.check(graph=graph)

    if expected_invalid_chains:
        assert not contract_check.kept

        expected_metadata = {"invalid_chains": [expected_invalid_chains]}

        assert expected_metadata == contract_check.metadata
    else:
        assert contract_check.kept


@pytest.mark.parametrize(
    "ignore_imports, is_kept",
    (
        (["mypackage.a -> mypackage.irrelevant"], False),
        (["mypackage.a -> mypackage.indirect"], True),
        (["mypackage.indirect -> mypackage.b"], True),
    ),
)
def test_ignore_imports(ignore_imports, is_kept):
    graph = FakeGraph(
        root_package_name="mypackage",
        import_details=[
            {
                "importer": "mypackage.a",
                "imported": "mypackage.irrelevant",
                "line_number": 1,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.a",
                "imported": "mypackage.indirect",
                "line_number": 1,
                "line_contents": "-",
            },
            {
                "importer": "mypackage.indirect",
                "imported": "mypackage.b",
                "line_number": 1,
                "line_contents": "-",
            },
        ],
        shortest_chains={("a", "b"): ("a", "indirect", "b")},
        all_modules=["mypackage", "mypackage.a", "mypackage.b", "mypackage.indirect"],
    )
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_package": "mypackage"},
        contract_options={
            "modules": ("mypackage.a", "mypackage.b"),
            "ignore_imports": ignore_imports,
        },
    )

    contract_check = contract.check(graph=graph)

    assert is_kept == contract_check.kept


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_package": "mypackage"},
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
    graph = FakeGraph(root_package_name="mypackage", all_modules=["mypackage", "mypackage.foo"])

    contract = IndependenceContract(
        name="Independence contract",
        session_options={"root_package": "mypackage"},
        contract_options={"modules": ["mypackage.foo", "mypackage.bar"]},
    )

    with pytest.raises(ValueError, match=("Module 'mypackage.bar' does not exist.")):
        contract.check(graph=graph)
