import pytest
from grimp import ImportGraph

from textwrap import dedent
from importlinter.application.output import console
from importlinter.configuration import settings
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.timing import FakeTimer


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=FakeTimer())


class TestForbiddenContract:
    @pytest.mark.parametrize("as_packages", ("False", "True"))
    def test_is_kept_when_no_forbidden_modules_imported(
        self,
        as_packages: bool,
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.blue", "mypackage.yellow"),
            as_packages=as_packages,
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept

    @pytest.mark.parametrize(
        "as_packages, forbidden_modules, expected_invalid_chains",
        [
            (
                True,
                (
                    "mypackage.blue",
                    "mypackage.green",
                    "mypackage.yellow",
                    "mypackage.purple",
                ),
                [
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
                            ],
                            [
                                {
                                    "importer": "mypackage.one.alpha.circle",
                                    "imported": "mypackage.green.beta.sphere",
                                    "line_numbers": (8,),
                                },
                            ],
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
                ],
            ),
            (
                False,
                (
                    "mypackage.blue",
                    "mypackage.green",
                    "mypackage.yellow",
                    "mypackage.purple",
                ),
                [
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
                ],
            ),
        ],
    )
    def test_is_broken_when_forbidden_modules_imported(
        self,
        as_packages: str,
        forbidden_modules: tuple[str],
        expected_invalid_chains: list[dict],
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=forbidden_modules,
            as_packages=as_packages,
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert not contract_check.kept

        expected_metadata = {"invalid_chains": expected_invalid_chains}

        assert expected_metadata == contract_check.metadata

    @pytest.mark.parametrize(
        "as_packages",
        (False, True),
    )
    def test_is_broken_when_forbidden_external_modules_imported(
        self,
        as_packages: str,
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("sqlalchemy", "requests"),
            include_external_packages=True,
            as_packages=as_packages,
        )

        contract_check = contract.check(graph=graph, verbose=False)

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

    @pytest.mark.parametrize(
        "as_packages",
        (
            ("False"),
            ("True"),
        ),
    )
    def test_is_invalid_when_forbidden_externals_but_graph_does_not_include_externals(
        self,
        as_packages: bool,
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("sqlalchemy", "requests"),
            as_packages=as_packages,
        )

        with pytest.raises(
            ValueError,
            match=(
                "The top level configuration must have include_external_packages=True "
                "when there are external forbidden modules."
            ),
        ):
            contract.check(graph=graph, verbose=False)

    @pytest.mark.parametrize(
        "as_packages",
        (
            ("False"),
            ("True"),
        ),
    )
    def test_ignore_imports_tolerates_duplicates(self, as_packages: bool):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.blue", "mypackage.yellow"),
            ignore_imports=(
                "mypackage.three -> mypackage.green",
                "mypackage.utils -> mypackage.purple",
                "mypackage.three -> mypackage.green",
            ),
            include_external_packages=False,
            as_packages=as_packages,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.kept

    def test_wildcards_in_source_modules_are_resolved(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green"),
            source_modules=("mypackage.one.*",),
            include_external_packages=False,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.metadata == {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.one.alpha",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha",
                                "imported": "mypackage.green.beta",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
            ],
        }

    def test_recursive_wildcards_in_source_modules_are_resolved(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green"),
            source_modules=("mypackage.one.**",),
            include_external_packages=False,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.metadata == {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.one.alpha",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha",
                                "imported": "mypackage.green.beta",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
                {
                    "upstream_module": "mypackage.green",
                    "downstream_module": "mypackage.one.alpha.circle",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
            ],
        }

    def test_wildcards_in_forbidden_modules_are_resolved(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green.*"),
            source_modules=("mypackage.one",),
            include_external_packages=False,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.metadata == {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green.beta",
                    "downstream_module": "mypackage.one",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha",
                                "imported": "mypackage.green.beta",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
            ],
        }

    def test_recursive_wildcards_in_forbidden_modules_are_resolved(self):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green.**"),
            source_modules=("mypackage.one",),
            include_external_packages=False,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.metadata == {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.green.beta",
                    "downstream_module": "mypackage.one",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha",
                                "imported": "mypackage.green.beta",
                                "line_numbers": (3,),
                            },
                        ],
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
                {
                    "upstream_module": "mypackage.green.beta.sphere",
                    "downstream_module": "mypackage.one",
                    "chains": [
                        [
                            {
                                "importer": "mypackage.one.alpha.circle",
                                "imported": "mypackage.green.beta.sphere",
                                "line_numbers": (8,),
                            },
                        ],
                    ],
                },
            ],
        }

    @pytest.mark.parametrize(
        "as_packages, forbidden_modules, expected_invalid_chains",
        [
            (
                True,
                ("mypackage.green",),
                [
                    {
                        "upstream_module": "mypackage.green",
                        "downstream_module": "mypackage.one",
                        "chains": [
                            [
                                {
                                    "importer": "mypackage.one.alpha.circle",
                                    "imported": "mypackage.green.beta.sphere",
                                    "line_numbers": (8,),
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
                                },
                            ]
                        ],
                    },
                ],
            ),
            (
                False,
                ("mypackage.green",),
                [
                    {
                        "upstream_module": "mypackage.green",
                        "downstream_module": "mypackage.three",
                        "chains": [
                            [
                                {
                                    "importer": "mypackage.three",
                                    "imported": "mypackage.green",
                                    "line_numbers": (4,),
                                },
                            ]
                        ],
                    },
                ],
            ),
        ],
    )
    def test_ignore_imports_with_wildcards(
        self,
        as_packages: str,
        forbidden_modules: tuple[str],
        expected_invalid_chains: list[dict],
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=forbidden_modules,
            ignore_imports=("mypackage.*.alpha -> mypackage.*.beta",),
            as_packages=as_packages,
        )

        check = contract.check(graph=graph, verbose=False)
        assert check.metadata == {
            "invalid_chains": expected_invalid_chains,
        }

    @pytest.mark.parametrize("as_packages", (False, True))
    def test_ignore_imports_with_recursive_wildcards(
        self,
        as_packages: str,
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.green",),
            ignore_imports=(
                "mypackage.**.alpha -> mypackage.**.beta",
                "mypackage.**.circle -> mypackage.**.sphere",
            ),
            as_packages=as_packages,
        )

        check = contract.check(graph=graph, verbose=False)
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
            ]
        }

    @pytest.mark.parametrize(
        "importer",
        ("mypackage.one", "mypackage.one.alpha"),
    )
    @pytest.mark.parametrize(
        "imported",
        ("mypackage.mauve", "mypackage.mauve.beta"),
    )
    @pytest.mark.parametrize(
        "allow_indirect_imports",
        (False, True),
    )
    def test_allow_indirect_imports(self, importer, imported, allow_indirect_imports):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.mauve",),
            allow_indirect_imports=allow_indirect_imports,
        )
        graph.add_module("mypackage.mauve")
        # Add a direct import.
        graph.add_import(
            importer=importer,
            imported=imported,
            line_number=10,
            line_contents="-",
        )
        # Add an indirect import.
        graph.add_import(
            importer="mypackage.one.delta",
            imported="mypackage.something",
            line_number=20,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.something",
            imported="mypackage.mauve.gamma",
            line_number=30,
            line_contents="-",
        )

        contract_check = contract.check(graph=graph, verbose=False)

        direct_chain = [
            {
                "importer": importer,
                "imported": imported,
                "line_numbers": (10,),
            },
        ]
        indirect_chain = [
            {
                "importer": "mypackage.one.delta",
                "imported": "mypackage.something",
                "line_numbers": (20,),
            },
            {
                "importer": "mypackage.something",
                "imported": "mypackage.mauve.gamma",
                "line_numbers": (30,),
            },
        ]
        if allow_indirect_imports:
            expected_chains = [direct_chain]
        else:
            expected_chains = [direct_chain, indirect_chain]
        assert contract_check.metadata == {
            "invalid_chains": [
                {
                    "upstream_module": "mypackage.mauve",
                    "downstream_module": "mypackage.one",
                    "chains": expected_chains,
                },
            ],
        }

    @pytest.mark.parametrize(
        "as_packages",
        (
            ("False"),
            ("True"),
        ),
    )
    def test_ignore_imports_adds_warnings(self, as_packages: bool):
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
                "as_packages": as_packages,
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert set(contract_check.warnings) == {
            "No matches for ignored import mypackage.one -> mypackage.two.nonexistent.",
            "No matches for ignored import mypackage.*.nonexistent -> mypackage.three.",
        }

    @pytest.mark.parametrize(
        "as_packages",
        (
            ("False"),
            ("True"),
        ),
    )
    @pytest.mark.parametrize(
        "module, expected_error",
        (
            (
                "requests.something",
                (
                    "Invalid forbidden module requests.something: "
                    "subpackages of external packages are not valid."
                ),
            ),
            # N.B. google.protobuf is a namespace package, but unless it is specified
            # as a root package, it will just appear in the graph as an external package
            # named 'google', so won't be treated any differently to other packages.
            (
                "google.protobuf",
                (
                    "Invalid forbidden module google.protobuf: "
                    "subpackages of external packages are not valid."
                ),
            ),
        ),
    )
    def test_is_invalid_when_subpackages_of_external_packages_are_provided(
        self,
        module: str,
        expected_error: str,
        as_packages: bool,
    ):
        graph = self._build_graph()
        contract = self._build_contract(
            forbidden_modules=("mypackage.blue", module),
            include_external_packages=True,
            as_packages=as_packages,
        )

        with pytest.raises(
            ValueError,
            match=expected_error,
        ):
            contract.check(graph=graph, verbose=False)

    def _build_graph(self):
        graph = ImportGraph()
        for module in (
            "one",
            "one.alpha",
            "one.alpha.circle",
            "two",
            "three",
            "blue",
            "green",
            "green.beta",
            "green.beta.sphere",
            "yellow",
            "purple",
            "utils",
        ):
            graph.add_module(f"mypackage.{module}")
        for external_module in ("sqlalchemy", "requests", "google"):
            graph.add_module(external_module, is_squashed=True)
        graph.add_import(
            importer="mypackage.one.alpha",
            imported="mypackage.green.beta",
            line_number=3,
            line_contents="foo",
        )
        graph.add_import(
            importer="mypackage.one.alpha.circle",
            imported="mypackage.green.beta.sphere",
            line_number=8,
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
            importer="mypackage.three",
            imported="sqlalchemy",
            line_number=1,
            line_contents="foo",
        )
        return graph

    def _build_contract(
        self,
        forbidden_modules,
        ignore_imports=None,
        include_external_packages=False,
        allow_indirect_imports=None,
        source_modules=None,
        as_packages=True,
    ):
        session_options = {"root_packages": ["mypackage"]}
        if include_external_packages:
            session_options["include_external_packages"] = "True"

        contract_options = {
            "source_modules": source_modules
            or ("mypackage.one", "mypackage.two", "mypackage.three"),
            "forbidden_modules": forbidden_modules,
            "ignore_imports": ignore_imports or [],
        }

        if allow_indirect_imports is not None:
            contract_options["allow_indirect_imports"] = (
                "true" if allow_indirect_imports else "false"
            )
        contract_options["as_packages"] = "true" if as_packages else "false"

        return ForbiddenContract(
            name="Forbid contract",
            session_options=session_options,
            contract_options=contract_options,
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

        contract_check = contract.check(graph=graph, verbose=False)

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

    with console.capture() as capture:
        contract.render_broken_contract(check)

    assert capture.get() == dedent(
        """\
        mypackage.two is not allowed to import mypackage.purple:

        -   mypackage.two -> mypackage.utils (l.9)
            mypackage.utils -> mypackage.purple (l.1)


        mypackage.three is not allowed to import mypackage.green:

        -   mypackage.three -> mypackage.green (l.4)


        """
    )


class TestVerbosePrint:
    def test_verbose(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=0)
        settings.configure(TIMER=timer)

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
            importer="mypackage.three",
            imported="sqlalchemy",
            line_number=1,
            line_contents="foo",
        )
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
                "ignore_imports": [],
                "allow_indirect_imports": "false",
            },
        )

        with console.capture() as capture:
            contract.check(graph=graph, verbose=True)

        assert capture.get() == dedent(
            """\
            Searching for import chains from mypackage.one to mypackage.blue...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.one to mypackage.green...
            Found 1 illegal chain in 10s.
            Searching for import chains from mypackage.one to mypackage.purple...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.one to mypackage.yellow...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.three to mypackage.blue...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.three to mypackage.green...
            Found 1 illegal chain in 10s.
            Searching for import chains from mypackage.three to mypackage.purple...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.three to mypackage.yellow...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.two to mypackage.blue...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.two to mypackage.green...
            Found 0 illegal chains in 10s.
            Searching for import chains from mypackage.two to mypackage.purple...
            Found 1 illegal chain in 10s.
            Searching for import chains from mypackage.two to mypackage.yellow...
            Found 0 illegal chains in 10s.
            """
        )
