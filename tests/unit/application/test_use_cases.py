import re
import string
from typing import Any
from unittest.mock import sentinel
from textwrap import dedent
from textwrap import indent
import pytest
from importlinter.application.output import console
from grimp import ImportGraph

from importlinter.application.app_config import settings
from importlinter.application.ports.building import GraphBuilder
from importlinter.application.use_cases import (
    FAILURE,
    SUCCESS,
    create_report,
    lint_imports,
)
from importlinter.application.user_options import UserOptions
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.timing import FakeTimer
from tests.adapters.user_options import (
    ExceptionRaisingUserOptionReader,
    FakeUserOptionReader,
)
from importlinter.application import rendering

SOME_CACHE_DIR = "/path/to/some/cache/dir"

INDENTED_LOGO = indent(rendering.TEXT_LOGO, " " * 12)


class TestCheckContractsAndPrintReport:
    def test_all_successful(self):
        self._configure(
            contracts_options=[
                {"type": "always_passes", "name": "Contract foo"},
                {"type": "always_passes", "name": "Contract bar"},
            ]
        )

        with console.capture() as capture:
            result = lint_imports()

        assert result == SUCCESS
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo KEPT
            Contract bar KEPT

            Contracts: 2 kept, 0 broken.
            """
        )

    def test_invalid_contract(self):
        self._configure(
            contracts_options=[
                {
                    "type": "fields",
                    "name": "Contract foo",
                    "single_field": ["one", "two"],
                    "multiple_field": "one",
                    "import_field": "foobar",
                },
                {"type": "always_passes", "name": "Contract bar"},
            ]
        )

        with console.capture() as capture:
            result = lint_imports()

        assert result == FAILURE
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            Contract "Contract foo" is not configured correctly:
                single_field: Expected a single value, got multiple values.
                import_field: Must be in the form "package.importer -> package.imported".
                required_field: This is a required field.
            """
        )

    def test_one_failure(self):
        self._configure(
            contracts_options=[
                {"type": "always_fails", "name": "Contract foo"},
                {"type": "always_passes", "name": "Contract bar"},
            ]
        )

        with console.capture() as capture:
            result = lint_imports()

        assert result == FAILURE
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo BROKEN
            Contract bar KEPT

            Contracts: 1 kept, 1 broken.


            ----------------
            Broken contracts
            ----------------

            Contract foo
            ------------

            This contract will always fail.
            """
        )

    def test_limit_contracts(self):
        self._configure(
            contracts_options=[
                {"type": "always_passes", "id": "blue", "name": "Contract blue"},
                {"type": "always_passes", "id": "green", "name": "Contract green"},
                {"type": "always_fails", "id": "yellow", "name": "Contract yellow"},
                {"type": "always_passes", "id": "purple", "name": "Contract purple"},
            ]
        )

        with console.capture() as capture:
            result = lint_imports(limit_to_contracts=("green", "purple"))

        assert result == SUCCESS
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract green KEPT
            Contract purple KEPT

            Contracts: 2 kept, 0 broken.
            """
        )

    def test_warnings(self):
        self._configure(
            contracts_options=[
                {
                    "type": "always_passes",
                    "name": "Contract foo",
                    "warnings": ["Some warning.", "Another warning."],
                },
                {
                    "type": "always_fails",
                    "name": "Contract bar",
                    "warnings": ["A third warning."],
                },
            ]
        )

        with console.capture() as capture:
            result = lint_imports()

        assert result == FAILURE
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo KEPT (2 warnings)
            Contract bar BROKEN (1 warning)

            Contracts: 1 kept, 1 broken.

            --------
            Warnings
            --------

            Contract foo
            ------------

            - Some warning.
            - Another warning.

            Contract bar
            ------------

            - A third warning.


            ----------------
            Broken contracts
            ----------------

            Contract bar
            ------------

            This contract will always fail.
            """
        )

    def test_timings(self):
        timer = FakeTimer()
        timer.setup(tick_duration=5, increment=10)
        self._configure(
            contracts_options=[
                {
                    "type": "always_passes",
                    "name": "Contract foo",
                },
                {
                    "type": "always_passes",
                    "name": "Contract bar",
                    "warnings": ["A warning."],
                },
            ],
            timer=timer,
        )

        with console.capture() as capture:
            lint_imports(show_timings=True)

        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            Building graph took 5.0s.

            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo KEPT [15s]
            Contract bar KEPT (1 warning) [25s]

            Contracts: 2 kept, 0 broken.

            --------
            Warnings
            --------

            Contract bar
            ------------

            - A warning.
            """
        )

    @pytest.mark.parametrize(
        "cache_dir, expected_graph_building_output",
        (
            (
                "/path/to/cache",
                "Building import graph (cache directory is /path/to/cache)...",
            ),
            (None, "Building import graph (with caching disabled)..."),
            (
                sentinel.not_supplied,
                f"Building import graph (cache directory is {SOME_CACHE_DIR})...",
            ),
        ),
    )
    @pytest.mark.parametrize(
        "verbose, expected_output_template",
        [
            (
                True,
                f"""\
            {INDENTED_LOGO}
            Verbose mode.
            << graph building output >>
            Built graph in 5.0s.
            Checking Contract foo...
            Hello from the noisy contract!
            Contract foo KEPT [15s]
            Checking Contract bar...
            Contract bar KEPT [25s]

            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo KEPT
            Contract bar KEPT

            Contracts: 2 kept, 0 broken.
                """,
            ),
            (
                False,
                f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 26 files, 10 dependencies.
            -----------------------------------

            Contract foo KEPT
            Contract bar KEPT

            Contracts: 2 kept, 0 broken.
                """,
            ),
        ],
    )
    def test_verbose_mode(
        self,
        verbose,
        expected_output_template,
        cache_dir,
        expected_graph_building_output,
    ):
        timer = FakeTimer()
        timer.setup(tick_duration=5, increment=10)
        self._configure(
            contracts_options=[
                {"type": "noisy", "name": "Contract foo"},
                {"type": "always_passes", "name": "Contract bar"},
            ],
            timer=timer,
        )

        kwargs = dict(verbose=verbose, is_debug_mode=True)
        if cache_dir is not sentinel.not_supplied:
            kwargs["cache_dir"] = cache_dir

        with console.capture() as capture:
            lint_imports(**kwargs)

        expected_output = expected_output_template.replace(
            "<< graph building output >>", expected_graph_building_output
        )
        assert capture.get() == dedent(expected_output)

    @pytest.mark.parametrize(
        "passed_arg, expected_cache_dir",
        (
            (sentinel.not_supplied, SOME_CACHE_DIR),
            ("/path/to/cache", "/path/to/cache"),
            (None, None),
        ),
    )
    def test_cache_dir_is_passed_correctly(self, passed_arg, expected_cache_dir):
        builder = FakeGraphBuilder()
        self._configure(contracts_options=[], graph_builder=builder)

        if passed_arg is sentinel.not_supplied:
            lint_imports()
        else:
            lint_imports(cache_dir=passed_arg)

        assert builder.build_arguments["cache_dir"] == expected_cache_dir

    def test_forbidden_import(self):
        """
        Tests the ForbiddenImportContract - a simple contract that
        looks at the graph.
        """
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.foo",
            imported="mypackage.bar",
            line_number=8,
            line_contents="from mypackage import bar",
        )
        graph.add_import(
            importer="mypackage.foo",
            imported="mypackage.bar",
            line_number=16,
            line_contents="from mypackage.bar import something",
        )
        self._configure(
            contracts_options=[
                {"type": "always_passes", "name": "Contract foo"},
                {
                    "type": "forbidden",
                    "name": "Forbidden contract one",
                    "importer": "mypackage.foo",
                    "imported": "mypackage.bar",
                },
                {
                    "type": "forbidden",
                    "name": "Forbidden contract two",
                    "importer": "mypackage.foo",
                    "imported": "mypackage.baz",
                },
            ],
            graph=graph,
        )

        with console.capture() as capture:
            result = lint_imports()

        assert result == FAILURE

        # Expecting 28 files (default graph has 26 modules, we add 2).
        # Expecting 11 dependencies (default graph has 10 imports, we add 2,
        # but it counts as 1 as it's between the same modules).
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            ---------
            Contracts
            ---------

            Analyzed 28 files, 11 dependencies.
            -----------------------------------

            Contract foo KEPT
            Forbidden contract one BROKEN
            Forbidden contract two KEPT

            Contracts: 2 kept, 1 broken.


            ----------------
            Broken contracts
            ----------------

            Forbidden contract one
            ----------------------

            mypackage.foo is not allowed to import mypackage.bar:

                mypackage.foo:8: from mypackage import bar
                mypackage.foo:16: from mypackage.bar import something
            """
        )

    def test_debug_mode_doesnt_swallow_exception(self):
        some_exception = RuntimeError("There was some sort of exception.")
        reader = ExceptionRaisingUserOptionReader(exception=some_exception)
        settings.configure(
            USER_OPTION_READERS={"foo": reader},
            GRAPH_BUILDER=FakeGraphBuilder(),
        )

        with pytest.raises(some_exception.__class__, match=str(some_exception)):
            lint_imports(is_debug_mode=True)

    def test_non_debug_mode_prints_exception(self):
        some_exception = RuntimeError("There was some sort of exception.")
        reader = ExceptionRaisingUserOptionReader(exception=some_exception)
        settings.configure(
            USER_OPTION_READERS={"foo": reader},
            GRAPH_BUILDER=FakeGraphBuilder(),
        )

        with console.capture() as capture:
            lint_imports(is_debug_mode=False)

        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            There was some sort of exception.
            """
        )

    def _configure(
        self,
        contracts_options: list[dict[str, Any]],
        session_options: dict[str, Any] | None = None,
        contract_types: list[str] | None = None,
        graph: ImportGraph | None = None,
        graph_builder: GraphBuilder | None = None,
        timer: FakeTimer | None = None,
    ):
        session_options = session_options or {"root_package": "mypackage"}
        if not contract_types:
            contract_types = [
                "always_passes: tests.helpers.contracts.AlwaysPassesContract",
                "always_fails: tests.helpers.contracts.AlwaysFailsContract",
                "fields: tests.helpers.contracts.FieldsContract",
                "forbidden: tests.helpers.contracts.ForbiddenImportContract",
                "noisy: tests.helpers.contracts.NoisyContract",
            ]
        session_options["contract_types"] = contract_types

        reader = FakeUserOptionReader(
            UserOptions(session_options=session_options, contracts_options=contracts_options)
        )
        settings.configure(
            USER_OPTION_READERS={"foo": reader},
            GRAPH_BUILDER=graph_builder or FakeGraphBuilder(),
            TIMER=timer or FakeTimer(),
            DEFAULT_CACHE_DIR=SOME_CACHE_DIR,
        )
        if graph is None:
            graph = self._build_default_graph()

        settings.GRAPH_BUILDER.inject_graph(graph)

    def _build_default_graph(self):
        graph = ImportGraph()

        # Add 26 modules.
        for letter in string.ascii_lowercase:
            graph.add_module(f"mypackage.{letter}")

        # Add 10 imports in total.
        for imported in ("d", "e", "f"):
            for importer in ("a", "b", "c"):
                graph.add_import(
                    importer=f"mypackage.{importer}", imported=f"mypackage.{imported}"
                )  # 3 * 3 = 9 imports.
        graph.add_import(importer="mypackage.d", imported="mypackage.f")  # 1 extra import.
        return graph


class TestMultipleRootPackages:
    def test_builder_is_called_with_root_packages(self):
        builder = FakeGraphBuilder()
        root_package_names = ["mypackageone", "mypackagetwo"]
        settings.configure(GRAPH_BUILDER=builder)

        create_report(
            UserOptions(
                session_options={"root_packages": root_package_names},
                contracts_options=[],
            )
        )

        assert builder.build_arguments["root_package_names"] == root_package_names


class TestGraphCopying:
    def test_graph_can_be_mutated_without_affecting_other_contracts(self):
        # The MutationCheckContract checks that there are a certain number of modules and imports
        # in the graph, then adds one more module and one more import. We can check two such
        # contracts and the second one will fail, if the graph gets mutated by other contracts.
        session_options = {
            "root_package": "mypackage",
            "contract_types": ["mutation_check: tests.helpers.contracts.MutationCheckContract"],
        }

        reader = FakeUserOptionReader(
            UserOptions(
                session_options=session_options,
                contracts_options=[
                    {
                        "type": "mutation_check",
                        "name": "Contract one",
                        "number_of_modules": "5",
                        "number_of_imports": "2",
                    },
                    {
                        "type": "mutation_check",
                        "name": "Contract two",
                        "number_of_modules": "5",
                        "number_of_imports": "2",
                    },
                ],
            )
        )
        settings.configure(
            USER_OPTION_READERS={"foo": reader},
            GRAPH_BUILDER=FakeGraphBuilder(),
        )

        graph = ImportGraph()

        # Create a graph with five modules and two imports.
        for module in ("one", "two", "three", "four", "five"):
            graph.add_module(module)
        graph.add_import(importer="one", imported="two")
        graph.add_import(importer="one", imported="three")

        settings.GRAPH_BUILDER.inject_graph(graph)

        result = lint_imports(is_debug_mode=True)

        assert result == SUCCESS


class TestCreateReport:
    @pytest.mark.parametrize(
        "limit_to_contracts, expected_message",
        (
            (
                ("a-contract-that-exists", "a-contract-that-doesnt-exist"),
                "Could not find contract 'a-contract-that-doesnt-exist'.\n\n"
                "You asked to limit the check to that contract, but nothing exists with that id.",
            ),
            (
                (
                    "a-contract-that-exists",
                    "a-contract-that-doesnt-exist",
                    "another-contract-that-doesnt-exist",
                ),
                "Could not find the following contract ids: "
                "a-contract-that-doesnt-exist, another-contract-that-doesnt-exist.\n\n"
                "You asked to limit the check to those contracts, but there are no "
                "contracts with those ids.",
            ),
        ),
    )
    def test_raises_exception_if_limited_to_nonexistent_contract(
        self, limit_to_contracts, expected_message
    ):
        settings.configure(GRAPH_BUILDER=FakeGraphBuilder())

        with pytest.raises(
            ValueError,
            match=re.escape(expected_message),
        ):
            create_report(
                user_options=UserOptions(
                    session_options={"root_packages": ["mypackage"]},
                    contracts_options=[
                        {
                            "type": "always_passes",
                            "id": "a-contract-that-exists",
                            "name": "Contract one",
                        },
                    ],
                ),
                limit_to_contracts=limit_to_contracts,
            )


class TestReadUserOptions:
    @pytest.mark.parametrize("filename", [".importlinter", "setup.cfg", "foo", "foo.bar"])
    def test_default_behavior(self, filename):
        expected_error = RuntimeError("expected")

        foo_reader = ExceptionRaisingUserOptionReader(AssertionError)
        ini_reader = ExceptionRaisingUserOptionReader(expected_error)
        toml_reader = ExceptionRaisingUserOptionReader(AssertionError)

        settings.configure(
            USER_OPTION_READERS={
                "foo": foo_reader,
                "ini": ini_reader,
                "toml": toml_reader,
            },
        )
        with pytest.raises(RuntimeError, match="expected"):
            lint_imports(filename, is_debug_mode=True)

    @pytest.mark.parametrize("filename", ["pyproject.toml", "foo.toml"])
    def test_toml_file(self, filename):
        expected_error = RuntimeError("expected")

        foo_reader = ExceptionRaisingUserOptionReader(AssertionError)
        ini_reader = ExceptionRaisingUserOptionReader(AssertionError)
        toml_reader = ExceptionRaisingUserOptionReader(expected_error)

        settings.configure(
            USER_OPTION_READERS={
                "foo": foo_reader,
                "ini": ini_reader,
                "toml": toml_reader,
            },
        )
        with pytest.raises(RuntimeError, match="expected"):
            lint_imports(filename, is_debug_mode=True)
