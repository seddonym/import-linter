from grimp.adaptors.graph import ImportGraph
from importlinter.application.app_config import settings
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.domain.contract import ContractCheck

from tests.adapters.printing import FakePrinter


class TestForbiddenContract:
    def test_contract_kept_when_no_forbidden_modules_imported(self):
        graph = self._build_graph()
        contract = self._build_contract(forbidden_modules=("mypackage.blue", "mypackage.yellow"))

        contract_check = contract.check(graph=graph)

        assert contract_check.kept

    def test_contract_broken_when_forbidden_modules_imported(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=(
                "mypackage.blue",
                "mypackage.green",
                "mypackage.yellow",
                "mypackage.purple",
            )
        )

        contract_check = contract.check(graph=graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.one",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha",
                                "imported": "mypackage.green.beta",
                                "line_numbers": (3,),
                            }
                        ]
                    ],
                },
                {
                    "upstream_module": "mypackage.purple",
                    "downstream_module": "mypackage.two",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.two",
                                "imported": "mypackage.utils",
                                "line_numbers": (9,),
                            },
                            {
                                "importer": "mypackage.utils",
                                "imported": "mypackage.purple",
                                "line_numbers": (1,),
                            },
                        ]
                    ],
                },
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.three",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.three",
                                "imported": "mypackage.green",
                                "line_numbers": (4,),
                            }
                        ]
                    ],
                },
            ]
        }

        assert expected_metadata == contract_check.metadata

    def test_contract_broken_when_forbidden_external_modules_imported(self):
        graph = self._build_graph()
        contract = self._build_contract(forbidden_modules=("sqlalchemy", "requests"))

        contract_check = contract.check(graph=graph)

        assert not contract_check.kept

        expected_metadata = {
            "invalid_chains": [
                {
                    "upstream_module": "sqlalchemy",
                    "downstream_module": "mypackage.three",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.three",
                                "imported": "sqlalchemy",
                                "line_numbers": (1,),
                            }
                        ]
                    ],
                }
            ]
        }

        assert expected_metadata == contract_check.metadata

    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "one",
            "one.alpha",
            "two",
            "three",
            "blue",
            "green",
            "green.beta",
            "yellow",
            "purple",
            "utils",
        ):
            graph.add_module(f"mypackage.{module}")
        for external_module in ("sqlalchemy", "requests"):
            graph.add_module(external_module, is_squashed=True)
        graph.add_import(
            importer="mypackage.one.alpha",
            imported="mypackage.green.beta",
            line_number=3,
            line_contents="foo",
        )
        graph.add_import(
            importer="mypackage.three",
            imported="mypackage.green",
            line_number=4,
            line_contents="foo",
        )
        graph.add_import(
            importer="mypackage.two",
            imported="mypackage.utils",
            line_number=9,
            line_contents="foo",
        )
        graph.add_import(
            importer="mypackage.utils",
            imported="mypackage.purple",
            line_number=1,
            line_contents="foo",
        )
        graph.add_import(
            importer="mypackage.three", imported="sqlalchemy", line_number=1, line_contents="foo"
        )
        return graph

    def _build_contract(self, forbidden_modules):
        return ForbiddenContract(
            name="Forbid contract",
            session_options={"root_package": "mypackage"},
            contract_options={
                "source_modules": ("mypackage.one", "mypackage.two", "mypackage.three"),
                "forbidden_modules": forbidden_modules,
            },
        )


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = ForbiddenContract(
        name="Forbid contract",
        session_options={"root_package": "mypackage"},
        contract_options={
            "source_modules": ("mypackage.one", "mypackage.two", "mypackage.three"),
            "forbidden_modules": (
                "mypackage.blue",
                "mypackage.green",
                "mypackage.yellow",
                "mypackage.purple",
            ),
        },
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.purple",
                    "downstream_module": "mypackage.two",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.two",
                                "imported": "mypackage.utils",
                                "line_numbers": (9,),
                            },
                            {
                                "importer": "mypackage.utils",
                                "imported": "mypackage.purple",
                                "line_numbers": (1,),
                            },
                        ]
                    ],
                },
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.three",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.three",
                                "imported": "mypackage.green",
                                "line_numbers": (4,),
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
        mypackage.two is not allowed to import mypackage.purple:

        -   mypackage.two -> mypackage.utils (l.9)
            mypackage.utils -> mypackage.purple (l.1)


        mypackage.three is not allowed to import mypackage.green:

        -   mypackage.three -> mypackage.green (l.4)


        """
    )