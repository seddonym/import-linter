import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore

from importlinter.application.app_config import settings
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.printing import FakePrinter


class TestForbiddenContract:
    def test_is_kept_when_no_forbidden_modules_imported(self):
        graph = self._build_graph()
        contract = self._build_contract(forbidden_modules=("mypackage.blue", "mypackage.yellow"))

        contract_check = contract.check(graph=graph)

        assert contract_check.kept

    def test_is_broken_when_forbidden_modules_imported(self):
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

    def test_is_broken_when_forbidden_external_modules_imported(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("sqlalchemy", "requests"), include_external_packages=True
        )

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

    def test_is_invalid_when_forbidden_externals_but_graph_does_not_include_externals(self):
        graph = self._build_graph()
        contract = self._build_contract(forbidden_modules=("sqlalchemy", "requests"))

        with pytest.raises(
            ValueError,
            match=(
                "The top level configuration must have include_external_packages=True "
                "when there are external forbidden modules."
            ),
        ):
            contract.check(graph=graph)

    def test_ignore_imports_tolerates_duplicates(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.blue", "mypackage.yellow"),
            ignore_imports=(
                "mypackage.three -> mypackage.green",
                "mypackage.utils -> mypackage.purple",
                "mypackage.three -> mypackage.green",
            ),
            include_external_packages=False,
        )

        check = contract.check(graph=graph)
        assert check.kept

    def test_ignore_imports_with_wildcards(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green",),
            ignore_imports=("mypackage.*.alpha -> mypackage.*.beta",),
        )

        check = contract.check(graph=graph)
        assert check.metadata == {
            "invalid_chains": [
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
            ],
        }

    @pytest.mark.parametrize(
        "allow_indirect_imports, contract_is_kept",
        ((None, False), ("false", False), ("True", True), ("true", True), ("anything", False)),
    )
    def test_allow_indirect_imports(self, allow_indirect_imports, contract_is_kept):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.purple"),
            allow_indirect_imports=allow_indirect_imports,
        )

        contract_check = contract.check(graph=graph)

        assert contract_check.kept == contract_is_kept

    def test_ignore_imports_adds_warnings(self):
        graph = self._build_graph()
        contract = ForbiddenContract(
            name="Forbid contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "source_modules": ("mypackage.one", "mypackage.two", "mypackage.three"),
                "forbidden_modules": "mypackage.purple",
                "ignore_imports": [
                    "mypackage.one -> mypackage.two.nonexistent",
                    "mypackage.*.nonexistent -> mypackage.three",
                ],
                "unmatched_ignore_imports_alerting": "warn",
            },
        )

        contract_check = contract.check(graph=graph)

        assert set(contract_check.warnings) == {
            "No matches for ignored import mypackage.one -> mypackage.two.nonexistent.",
            "No matches for ignored import mypackage.*.nonexistent -> mypackage.three.",
        }

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

    def _build_contract(
        self,
        forbidden_modules,
        ignore_imports=None,
        include_external_packages=False,
        allow_indirect_imports=None,
    ):
        session_options = {"root_packages": ["mypackage"]}
        if include_external_packages:
            session_options["include_external_packages"] = "True"

        return ForbiddenContract(
            name="Forbid contract",
            session_options=session_options,
            contract_options={
                "source_modules": ("mypackage.one", "mypackage.two", "mypackage.three"),
                "forbidden_modules": forbidden_modules,
                "ignore_imports": ignore_imports or [],
                "allow_indirect_imports": allow_indirect_imports,
            },
        )


class TestForbiddenContractForNamespacePackages:
    @pytest.mark.parametrize(
        "forbidden, is_kept",
        [
            ("namespace.subnamespace.portiontwo.green", False),
            ("namespace.subnamespace.portiontwo.blue", True),
        ],
    )
    def test_allows_forbidding_of_inter_portion_imports(self, forbidden, is_kept):
        graph = ImportGraph()
        for module in (
            "portionone",
            "portionone.blue",
            "subnamespace.portiontwo",
            "subnamespace.portiontwo.green",
            "subnamespace.portiontwo.blue",
        ):
            graph.add_module(f"namespace.{module}")
        for external_module in ("sqlalchemy", "requests"):
            graph.add_module(external_module, is_squashed=True)
        # Add import from one portion to another.
        graph.add_import(
            importer="namespace.portionone.blue",
            imported="namespace.subnamespace.portiontwo.green",
            line_number=3,
            line_contents="-",
        )
        contract = self._build_contract(
            root_packages=["namespace.portionone", "namespace.subnamespace.portiontwo"],
            source_modules=("namespace.portionone.blue",),
            forbidden_modules=(forbidden,),
        )

        contract_check = contract.check(graph=graph)

        assert contract_check.kept == is_kept

    def _build_contract(
        self,
        root_packages,
        source_modules,
        forbidden_modules,
        include_external_packages=False,
    ):
        session_options = {"root_packages": root_packages}
        if include_external_packages:
            session_options["include_external_packages"] = "True"

        return ForbiddenContract(
            name="Forbid contract",
            session_options=session_options,
            contract_options={
                "source_modules": source_modules,
                "forbidden_modules": forbidden_modules,
            },
        )


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = ForbiddenContract(
        name="Forbid contract",
        session_options={"root_packages": ["mypackage"]},
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
