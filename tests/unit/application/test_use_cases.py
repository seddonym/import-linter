import os
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
    build_dot_graph,
    create_report,
    _create_report_from_sources,
    _format_module_count,
    _read_config_sources,
    _register_built_in_contract_types,
    lint_imports,
)
from importlinter.application.user_options import InvalidUserOptions
from importlinter.domain.contract import NoSuchContractType
from importlinter.domain.dotfile import DotGraph, Edge, EdgeArrowhead, EdgeStyle
from importlinter.application.user_options import UserOptions
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.timing import FakeTimer
from tests.adapters.user_options import (
    ExceptionRaisingUserOptionReader,
    FakeMultipleFileUserOptionReader,
    FakeUserOptionReader,
)
from importlinter.adapters.filesystem import FileSystem
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
            ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
            ┃ Config files ┃ Graph build duration ┃
            ┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
            │              │                 5.0s │
            └──────────────┴──────────────────────┘

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

    def test_no_logo(self):
        self._configure(
            contracts_options=[
                {"type": "always_passes", "name": "Contract foo"},
                {"type": "always_passes", "name": "Contract bar"},
            ]
        )

        with console.capture() as capture:
            lint_imports(no_logo=True)

        assert capture.get() == dedent(
            """\
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
        self._configure(
            contracts_options=[{"type": "always_passes", "name": "Contract foo"}],
            graph_builder=builder,
        )

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

    def test_no_contracts_is_a_failure(self):
        builder = FakeGraphBuilder()
        self._configure(contracts_options=[], graph_builder=builder)

        with console.capture() as capture:
            result = lint_imports()

        assert result == FAILURE
        assert capture.get() == dedent(
            f"""\
            {INDENTED_LOGO}
            No contracts found in the configuration.

            Each contract goes in an 'importlinter:contract:<name>' section (INI files)
            or a 'tool.importlinter.contracts' array of tables (TOML files).
            """
        )
        # Fail before building the graph: there is nothing to check it against.
        assert not hasattr(builder, "build_arguments")

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

    def test_raises_could_not_find_error_when_contracts_lack_id(self):
        # Toml configs don't require contract ids. If `--contract` is passed and some
        # contracts lack an id, we should fall through to the normal "Could not find
        # contract" error instead of raising KeyError. Regression test for #314.
        settings.configure(GRAPH_BUILDER=FakeGraphBuilder())

        with pytest.raises(
            ValueError,
            match=re.escape("Could not find contract 'foo'."),
        ):
            create_report(
                user_options=UserOptions(
                    session_options={"root_packages": ["mypackage"]},
                    contracts_options=[
                        {"type": "always_passes", "name": "Contract one"},
                        {"type": "always_passes", "name": "Contract two"},
                    ],
                ),
                limit_to_contracts=("foo",),
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


class RecordingGraphBuilder(GraphBuilder):
    """
    Graph builder that records every build, and returns a graph chosen by the build arguments.
    """

    def __init__(self, graphs_by_exclude_type_checking_imports: dict[bool, ImportGraph]):
        self._graphs = graphs_by_exclude_type_checking_imports
        self.builds: list[dict[str, Any]] = []

    def build(
        self,
        root_package_names: list[str],
        cache_dir: str | None,
        include_external_packages: bool = False,
        exclude_type_checking_imports: bool = False,
    ) -> ImportGraph:
        self.builds.append(
            {
                "root_package_names": root_package_names,
                "cache_dir": cache_dir,
                "include_external_packages": include_external_packages,
                "exclude_type_checking_imports": exclude_type_checking_imports,
            }
        )
        return self._graphs[exclude_type_checking_imports]


class TestMultipleConfigFiles:
    CONTRACT_TYPES = [
        "always_passes: tests.helpers.contracts.AlwaysPassesContract",
        "always_fails: tests.helpers.contracts.AlwaysFailsContract",
        "forbidden: tests.helpers.contracts.ForbiddenImportContract",
    ]

    def test_contracts_from_files_with_same_top_level_config_share_one_graph(self):
        builder = self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra/two.ini": self._options(
                    [{"type": "always_passes", "name": "Contract two"}]
                ),
                "extra/three.toml": self._options(
                    [{"type": "always_passes", "name": "Contract three"}]
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filenames=("main.ini", "extra/two.ini", "extra/three.toml"),
                no_logo=True,
            )

        assert result == SUCCESS
        assert len(builder.builds) == 1
        assert capture.get() == dedent(
            """\
            ---------
            Contracts
            ---------

            Analyzed 3 files, 1 dependencies.
            ---------------------------------

            Contract one KEPT
            Contract two KEPT
            Contract three KEPT

            Contracts: 3 kept, 0 broken.
            """
        )

    def test_builds_one_graph_per_distinct_top_level_config(self):
        # The import from mypackage.a to mypackage.b is only in the graph that
        # includes type checking imports, so only the first file's contract is broken.
        builder = self._configure(
            {
                "main.ini": self._options(
                    [self._forbidden_contract("Contract one")],
                ),
                "extra.ini": self._options(
                    [self._forbidden_contract("Contract two")],
                    exclude_type_checking_imports="True",
                ),
                "another.ini": self._options(
                    [self._forbidden_contract("Contract three")],
                    exclude_type_checking_imports="True",
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filenames=("main.ini", "extra.ini", "another.ini"), no_logo=True
            )

        assert result == FAILURE
        assert [build["exclude_type_checking_imports"] for build in builder.builds] == [
            False,
            True,
        ]
        output = capture.get()
        assert "Analyzed 5 files, 1 dependencies." in output
        assert "Contract one BROKEN" in output
        assert "Contract two KEPT" in output
        assert "Contract three KEPT" in output
        assert "Contracts: 2 kept, 1 broken." in output

    def test_each_contract_receives_its_own_files_session_options(self):
        self._configure(
            {
                "main.ini": self._options(
                    [self._forbidden_contract("Contract one")],
                ),
                "extra.ini": self._options(
                    [self._forbidden_contract("Contract two")],
                    exclude_type_checking_imports="True",
                ),
            }
        )

        report = create_report_from_files("main.ini", "extra.ini")

        session_options_by_name = {
            contract.name: contract.session_options for contract in report.contracts
        }
        assert "exclude_type_checking_imports" not in session_options_by_name["Contract one"]
        assert session_options_by_name["Contract two"]["exclude_type_checking_imports"] == "True"

    def test_shows_combined_graph_building_time(self):
        timer = FakeTimer()
        timer.setup(tick_duration=5, increment=0)
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options(
                    [{"type": "always_passes", "name": "Contract two"}],
                    exclude_type_checking_imports="True",
                ),
            },
            timer=timer,
        )

        with console.capture() as capture:
            lint_imports(config_filenames=("main.ini", "extra.ini"), show_timings=True)

        assert "Total 2 config files, 2 import graphs." in capture.get()
        assert "10s" in capture.get()

    def test_shows_which_files_share_each_graph(self):
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "same.ini": self._options([{"type": "always_passes", "name": "Contract two"}]),
                "extra.ini": self._options(
                    [{"type": "always_passes", "name": "Contract three"}],
                    exclude_type_checking_imports="True",
                ),
            },
        )

        with console.capture() as capture:
            lint_imports(config_filenames=("main.ini", "same.ini", "extra.ini"), no_logo=True)

        output = capture.get()
        assert "Config files" in output
        assert "Duration" not in output
        assert "main.ini, same.ini" in output
        assert "extra.ini" in output
        assert "Total 3 config files, 2 import graphs." in output

    def test_shows_graph_durations_when_show_timings_is_used(self):
        timer = FakeTimer()
        timer.setup(tick_duration=5, increment=0)
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "same.ini": self._options([{"type": "always_passes", "name": "Contract two"}]),
                "extra.ini": self._options(
                    [{"type": "always_passes", "name": "Contract three"}],
                    exclude_type_checking_imports="True",
                ),
            },
            timer=timer,
        )

        with console.capture() as capture:
            lint_imports(config_filenames=("main.ini", "same.ini", "extra.ini"), show_timings=True)

        output = capture.get()
        assert "Graph build duration" in output
        assert "5.0s" in output
        assert "main.ini, same.ini" in output
        assert "extra.ini" in output
        assert "Total 3 config files, 2 import graphs." in output

    def test_does_not_show_graph_breakdown_for_a_single_graph(self):
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options([{"type": "always_passes", "name": "Contract two"}]),
            },
        )

        with console.capture() as capture:
            lint_imports(config_filenames=("main.ini", "extra.ini"), no_logo=True)

        output = capture.get()
        assert "Graph" not in output

    def test_does_not_show_total_row_for_a_single_graph(self):
        timer = FakeTimer()
        timer.setup(tick_duration=5, increment=0)
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options([{"type": "always_passes", "name": "Contract two"}]),
            },
            timer=timer,
        )

        with console.capture() as capture:
            lint_imports(config_filenames=("main.ini", "extra.ini"), show_timings=True)

        output = capture.get()
        assert "Config files" in output
        assert "Total" not in output

    def test_only_builds_graphs_needed_by_selected_contracts(self):
        builder = self._configure(
            {
                "main.ini": self._options(
                    [{"type": "always_passes", "id": "one", "name": "Contract one"}]
                ),
                "extra.ini": self._options(
                    [{"type": "always_passes", "id": "two", "name": "Contract two"}],
                    exclude_type_checking_imports="True",
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filenames=("main.ini", "extra.ini"),
                limit_to_contracts=("two",),
                no_logo=True,
            )

        assert result == SUCCESS
        assert [build["exclude_type_checking_imports"] for build in builder.builds] == [True]
        assert "Contract one" not in capture.get()
        assert "Contract two KEPT" in capture.get()

    def test_config_filename_is_treated_as_first_file(self):
        builder = self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options([{"type": "always_passes", "name": "Contract two"}]),
            }
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filename="main.ini", config_filenames=("extra.ini",), no_logo=True
            )

        assert result == SUCCESS
        assert len(builder.builds) == 1
        output = capture.get()
        assert output.index("Contract one KEPT") < output.index("Contract two KEPT")

    def test_file_passed_more_than_once_is_only_read_once(self):
        self._configure(
            {"main.ini": self._options([{"type": "always_passes", "name": "Contract one"}])}
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filenames=("main.ini", "./main.ini", "main.ini"), no_logo=True
            )

        assert result == SUCCESS
        assert settings.USER_OPTION_READERS["ini"].read_filenames == ["main.ini"]
        assert "Contracts: 1 kept, 0 broken." in capture.get()

    def test_errors_if_file_has_no_configuration(self):
        self._configure(
            {"main.ini": self._options([{"type": "always_passes", "name": "Contract one"}])}
        )

        with pytest.raises(
            FileNotFoundError, match=re.escape("Could not read any configuration from extra.ini.")
        ):
            lint_imports(config_filenames=("main.ini", "extra.ini"), is_debug_mode=True)

    def test_ambiguous_contract_id_errors_with_filename_suggestions(self):
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract one"}]
                ),
                "extra/two.ini": self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract two"}]
                ),
            }
        )

        with pytest.raises(ValueError) as exc_info:
            lint_imports(
                config_filenames=("main.ini", "extra/two.ini"),
                limit_to_contracts=("my-contract",),
                is_debug_mode=True,
            )

        assert str(exc_info.value) == (
            "Multiple contracts found with the id 'my-contract'. "
            "Try including the filename, e.g.\n\n"
            "--contract=main.ini:my-contract\n"
            f"--contract={os.path.join('extra', 'two.ini')}:my-contract"
        )

    def test_ambiguous_contract_id_through_symlink_gives_usable_suggestions(self, tmp_path):
        if not hasattr(os, "symlink"):
            pytest.skip("Symlinks not supported.")
        (tmp_path / "extra" / "nested").mkdir(parents=True)
        try:
            os.symlink(tmp_path / "extra" / "nested", tmp_path / "linked")
        except OSError:
            pytest.skip("Symlinks not supported.")
        # Through the symlink, linked/../rules.ini is extra/rules.ini, not rules.ini -
        # but os.path.relpath doesn't know that, and displays both the same way.
        main = str(tmp_path / "rules.ini")
        extra = os.path.join(str(tmp_path), "linked", "..", "rules.ini")
        self._configure(
            {
                main: self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract one"}]
                ),
                extra: self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract two"}]
                ),
            }
        )

        with pytest.raises(ValueError) as exc_info:
            lint_imports(
                config_filenames=(main, extra),
                limit_to_contracts=("my-contract",),
                is_debug_mode=True,
            )

        suggestions = re.findall(r"^--contract=(.+)$", str(exc_info.value), re.MULTILINE)
        assert len(suggestions) == 2
        # The suggestions must be distinguishable, even though the two files share a
        # display name when symlinks aren't resolved.
        assert suggestions[0] != suggestions[1]

        # Using the second suggestion should actually select the second file's contract.
        with console.capture() as capture:
            result = lint_imports(
                config_filenames=(main, extra),
                limit_to_contracts=(suggestions[1],),
                no_logo=True,
            )

        assert result == SUCCESS
        output = capture.get()
        assert "Contract two KEPT" in output
        assert "Contract one" not in output

    def test_same_id_in_different_files_is_allowed_without_contract_option(self):
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract one"}]
                ),
                "extra.ini": self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract two"}]
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(config_filenames=("main.ini", "extra.ini"), no_logo=True)

        assert result == SUCCESS
        assert "Contracts: 2 kept, 0 broken." in capture.get()

    @pytest.mark.parametrize(
        "requested",
        (
            "extra/two.ini:my-contract",
            "./extra/two.ini:my-contract",
            "extra/../extra/two.ini:my-contract",
        ),
    )
    def test_contract_id_can_be_qualified_with_filename(self, requested):
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "always_fails", "id": "my-contract", "name": "Contract one"}]
                ),
                "extra/two.ini": self._options(
                    [
                        {"type": "always_passes", "id": "my-contract", "name": "Contract two"},
                        {"type": "always_fails", "id": "other", "name": "Contract three"},
                    ]
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(
                config_filenames=("main.ini", "extra/two.ini"),
                limit_to_contracts=(requested,),
                no_logo=True,
            )

        assert result == SUCCESS
        output = capture.get()
        assert "Contract two KEPT" in output
        assert "Contract one" not in output
        assert "Contract three" not in output

    def test_contract_id_containing_colon_is_rejected(self):
        self._configure(
            {
                "pyproject.toml": self._options(
                    [{"type": "always_fails", "id": "scope:one", "name": "Contract one"}]
                ),
            }
        )

        with pytest.raises(
            InvalidUserOptions,
            match=re.escape(
                "The contract id 'scope:one' in pyproject.toml is invalid. "
                "Contract ids may not contain a colon."
            ),
        ):
            lint_imports(config_filenames=("pyproject.toml",), is_debug_mode=True)

    def test_qualified_contract_id_with_unknown_filename_is_not_found(self):
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "always_passes", "id": "my-contract", "name": "Contract one"}]
                ),
            }
        )

        with pytest.raises(
            ValueError, match=re.escape("Could not find contract 'other.ini:my-contract'.")
        ):
            lint_imports(
                config_filenames=("main.ini",),
                limit_to_contracts=("other.ini:my-contract",),
                is_debug_mode=True,
            )

    def test_duplicate_ids_within_a_single_file_error(self):
        self._configure(
            {
                "pyproject.toml": self._options(
                    [
                        {"type": "always_passes", "id": "my-contract", "name": "Contract one"},
                        {"type": "always_passes", "id": "my-contract", "name": "Contract two"},
                    ]
                ),
            }
        )

        with pytest.raises(
            InvalidUserOptions,
            match=re.escape(
                "More than one contract in pyproject.toml has the id 'my-contract'. "
                "Contract ids must be unique within a file."
            ),
        ):
            lint_imports(config_filenames=("pyproject.toml",), is_debug_mode=True)

    def test_same_custom_contract_type_name_in_different_files_are_independent(self):
        # Each file registers "custom" as a different class. Since custom contract types are
        # scoped to the file that declares them, this isn't a conflict.
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "custom", "name": "Contract one"}],
                    contract_types=["custom: tests.helpers.contracts.AlwaysPassesContract"],
                ),
                "extra.ini": self._options(
                    [{"type": "custom", "name": "Contract two"}],
                    contract_types=["custom: tests.helpers.contracts.AlwaysFailsContract"],
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(config_filenames=("main.ini", "extra.ini"), no_logo=True)

        assert result == FAILURE
        output = capture.get()
        assert "Contract one KEPT" in output
        assert "Contract two BROKEN" in output

    def test_custom_contract_type_is_not_available_in_other_files(self):
        # main.ini registers "custom", but extra.ini never declares it, so it can't use it.
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "custom", "name": "Contract one"}],
                    contract_types=["custom: tests.helpers.contracts.AlwaysPassesContract"],
                ),
                "extra.ini": self._options([{"type": "custom", "name": "Contract two"}]),
            }
        )

        with pytest.raises(NoSuchContractType, match=re.escape("custom")):
            lint_imports(config_filenames=("main.ini", "extra.ini"), is_debug_mode=True)

    def test_file_replacing_built_in_contract_type_does_not_affect_other_files(self):
        self._configure(
            {
                "main.ini": self._options(
                    [{"type": "forbidden", "name": "Contract one"}],
                    contract_types=["forbidden: tests.helpers.contracts.AlwaysPassesContract"],
                ),
                "extra.ini": self._options(
                    [
                        {
                            "type": "forbidden",
                            "name": "Contract two",
                            "source_modules": ["mypackage.a"],
                            "forbidden_modules": ["mypackage.b"],
                        }
                    ],
                    contract_types=["always_passes: tests.helpers.contracts.AlwaysPassesContract"],
                ),
            }
        )

        with console.capture() as capture:
            result = lint_imports(config_filenames=("main.ini", "extra.ini"), no_logo=True)

        assert result == FAILURE
        output = capture.get()
        # main.ini's replacement applies to its own contract...
        assert "Contract one KEPT" in output
        # ...but extra.ini's contract is still checked by the built-in forbidden contract.
        assert "Contract two BROKEN" in output

    def test_errors_if_a_file_has_no_contracts(self):
        self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options([]),
            }
        )

        with pytest.raises(
            InvalidUserOptions, match=re.escape("No contracts found in extra.ini.")
        ):
            lint_imports(config_filenames=("main.ini", "extra.ini"), is_debug_mode=True)

    def test_omitted_and_false_include_external_packages_share_a_graph(self):
        builder = self._configure(
            {
                "main.ini": self._options([{"type": "always_passes", "name": "Contract one"}]),
                "extra.ini": self._options(
                    [{"type": "always_passes", "name": "Contract two"}],
                    include_external_packages="False",
                ),
            }
        )

        with console.capture():
            result = lint_imports(config_filenames=("main.ini", "extra.ini"), no_logo=True)

        assert result == SUCCESS
        assert len(builder.builds) == 1

    def test_files_reached_through_a_symlink_are_not_treated_as_duplicates(self, tmp_path):
        if not hasattr(os, "symlink"):
            pytest.skip("Symlinks not supported.")
        (tmp_path / "extra" / "nested").mkdir(parents=True)
        try:
            os.symlink(tmp_path / "extra" / "nested", tmp_path / "linked")
        except OSError:
            pytest.skip("Symlinks not supported.")
        # Through the symlink, linked/../rules.ini is extra/rules.ini, not rules.ini.
        main = str(tmp_path / "rules.ini")
        extra = os.path.join(str(tmp_path), "linked", "..", "rules.ini")
        self._configure(
            {
                main: self._options([{"type": "always_passes", "name": "Contract one"}]),
                extra: self._options([{"type": "always_passes", "name": "Contract two"}]),
            }
        )

        with console.capture() as capture:
            result = lint_imports(config_filenames=(main, extra), no_logo=True)

        assert result == SUCCESS
        assert "Contract one KEPT" in capture.get()
        assert "Contract two KEPT" in capture.get()

    # Helpers

    def _options(
        self,
        contracts_options: list[dict[str, Any]],
        contract_types: list[str] | None = None,
        **extra_session_options: str,
    ) -> UserOptions:
        return UserOptions(
            session_options={
                "root_package": "mypackage",
                "contract_types": contract_types or self.CONTRACT_TYPES,
                **extra_session_options,
            },
            contracts_options=contracts_options,
        )

    def _forbidden_contract(self, name: str) -> dict[str, Any]:
        return {
            "type": "forbidden",
            "name": name,
            "importer": "mypackage.a",
            "imported": "mypackage.b",
        }

    def _configure(
        self,
        user_options_by_filename: dict[str, UserOptions],
        timer: FakeTimer | None = None,
    ) -> RecordingGraphBuilder:
        graph_with_type_checking_imports = ImportGraph()
        for module in ("mypackage", "mypackage.a", "mypackage.b"):
            graph_with_type_checking_imports.add_module(module)
        graph_with_type_checking_imports.add_import(
            importer="mypackage.a",
            imported="mypackage.b",
            line_number=3,
            line_contents="from mypackage import b",
        )
        graph_without_type_checking_imports = ImportGraph()
        for module in ("mypackage", "mypackage.a"):
            graph_without_type_checking_imports.add_module(module)

        builder = RecordingGraphBuilder(
            {
                False: graph_with_type_checking_imports,
                True: graph_without_type_checking_imports,
            }
        )
        reader = FakeMultipleFileUserOptionReader(user_options_by_filename)
        settings.configure(
            USER_OPTION_READERS={"ini": reader, "toml": reader},
            GRAPH_BUILDER=builder,
            FILE_SYSTEM=FileSystem(),
            TIMER=timer or FakeTimer(),
            DEFAULT_CACHE_DIR=SOME_CACHE_DIR,
        )
        return builder


def create_report_from_files(*filenames: str):
    config_sources = _read_config_sources(None, filenames)
    _register_built_in_contract_types()
    return _create_report_from_sources(config_sources)


# Dot graph generation tests
# --------------------------

SOME_ROOT_PACKAGE = "mypackage"
SOME_MODULE = f"{SOME_ROOT_PACKAGE}.foo"


def _build_fake_graph(package_name: str) -> ImportGraph:
    graph = ImportGraph()
    graph.add_module(package_name)

    graph.add_module(SOME_MODULE)

    for child in ("blue", "green", "yellow", "red"):
        graph.add_module(f"{SOME_MODULE}.{child}")

    # As with a real graph, every import has line details. Where is_lazy is omitted, it defaults
    # to a normal (eager) import.
    graph.add_import(
        importer=f"{SOME_MODULE}.blue.alpha",
        imported=f"{SOME_MODULE}.green",
        line_number=1,
        line_contents="import mypackage.foo.green",
    )
    # The only import between green and yellow is lazy, so the whole dependency is lazy.
    graph.add_import(
        importer=f"{SOME_MODULE}.green",
        imported=f"{SOME_MODULE}.yellow.beta",
        line_number=1,
        line_contents="lazy from mypackage.foo import yellow",
        is_lazy=True,
    )
    # Add 4 imports between blue and red in different permutations of root and descendants.
    graph.add_import(
        importer=f"{SOME_MODULE}.blue",
        imported=f"{SOME_MODULE}.red",
        line_number=1,
        line_contents="import mypackage.foo.red",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.blue",
        imported=f"{SOME_MODULE}.red.gamma",
        line_number=2,
        line_contents="import mypackage.foo.red.gamma",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.blue.alpha",
        imported=f"{SOME_MODULE}.red",
        line_number=1,
        line_contents="import mypackage.foo.red",
    )
    # Only one of the four blue -> red imports is lazy, so the dependency is not wholly lazy.
    graph.add_import(
        importer=f"{SOME_MODULE}.blue.delta",
        imported=f"{SOME_MODULE}.red.epsilon",
        line_number=1,
        line_contents="lazy from mypackage.foo import red",
        is_lazy=True,
    )
    # Add a cycle.
    graph.add_import(
        importer=f"{SOME_MODULE}.red.epsilon",
        imported=f"{SOME_MODULE}.blue.alpha",
        line_number=1,
        line_contents="import mypackage.foo.blue",
    )

    return graph


class TestBuildDotGraph:
    def test_builds_graph_with_correct_nodes_and_edges(self):
        grimp_graph = _build_fake_graph(SOME_ROOT_PACKAGE)

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=False,
        )

        assert dot == DotGraph(
            title=SOME_MODULE,
            concentrate=True,
            nodes={
                "mypackage.foo.green",
                "mypackage.foo.blue",
                "mypackage.foo.yellow",
                "mypackage.foo.red",
            },
            node_labels={
                "mypackage.foo.blue": ".blue/",
                "mypackage.foo.yellow": ".yellow/",
                "mypackage.foo.red": ".red/",
            },
            edges={
                Edge("mypackage.foo.blue", "mypackage.foo.green"),
                Edge("mypackage.foo.green", "mypackage.foo.yellow"),
                Edge("mypackage.foo.blue", "mypackage.foo.red"),
                Edge("mypackage.foo.red", "mypackage.foo.blue"),
            },
        )

    def test_draws_supplied_modules_as_overview(self):
        grimp_graph = ImportGraph()
        for package in ("blue", "green"):
            grimp_graph.add_module(package)
            grimp_graph.add_module(f"{package}.one")
        # green depends on blue.
        grimp_graph.add_import(
            importer="green.one",
            imported="blue.one",
            line_number=1,
            line_contents="import blue.one",
        )

        dot = build_dot_graph(
            grimp_graph,
            "",
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=False,
            modules=["blue", "green"],
        )

        assert dot == DotGraph(
            title="",
            concentrate=True,
            nodes={"blue", "green"},
            node_labels={"blue": "blue/", "green": "green/"},
            edges={Edge("green", "blue")},
            relative=False,
        )

    def test_draws_supplied_subpackages_with_distinct_identifiers(self):
        # Two subpackages that share a last component ('api') must not collide when drawn on an
        # overview: they need fully qualified identifiers, not relative ones.
        grimp_graph = ImportGraph()
        for package in ("blue", "green"):
            grimp_graph.add_module(package)
            grimp_graph.add_module(f"{package}.api")
            grimp_graph.add_module(f"{package}.api.handlers")
        # green.api depends on blue.api.
        grimp_graph.add_import(
            importer="green.api.handlers",
            imported="blue.api.handlers",
            line_number=1,
            line_contents="import blue.api.handlers",
        )

        dot = build_dot_graph(
            grimp_graph,
            "",
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=False,
            modules=["blue.api", "green.api"],
        )

        assert dot == DotGraph(
            title="",
            concentrate=True,
            nodes={"blue.api", "green.api"},
            node_labels={"blue.api": "blue.api/", "green.api": "green.api/"},
            edges={Edge("green.api", "blue.api")},
            relative=False,
        )
        # The rendered output must keep the nodes distinct (not merged into a single ".api" node
        # with a self-edge).
        rendered = dot.render()
        assert '"blue.api"' in rendered
        assert '"green.api"' in rendered
        assert '"green.api" ->  "blue.api"' in rendered

    def test_draws_only_supplied_modules_ignoring_sibling_subpackages(self):
        # Only the supplied modules are drawn, even when their parents contain other subpackages.
        grimp_graph = ImportGraph()
        for package in ("blue", "green"):
            grimp_graph.add_module(package)
            for child in ("api", "db", "utils"):
                grimp_graph.add_module(f"{package}.{child}")
                grimp_graph.add_module(f"{package}.{child}.handlers")
        # green.api depends on blue.api.
        grimp_graph.add_import(
            importer="green.api.handlers",
            imported="blue.api.handlers",
            line_number=1,
            line_contents="import blue.api.handlers",
        )
        # green.db depends on blue.db, but neither was supplied, so this must not be drawn.
        grimp_graph.add_import(
            importer="green.db.handlers",
            imported="blue.db.handlers",
            line_number=1,
            line_contents="import blue.db.handlers",
        )

        dot = build_dot_graph(
            grimp_graph,
            "",
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=False,
            modules=["blue.api", "green.api"],
        )

        # The sibling subpackages (blue.db, blue.utils, green.db, green.utils) exist in the graph
        # but were not supplied, so only blue.api and green.api are drawn.
        assert dot == DotGraph(
            title="",
            concentrate=True,
            nodes={"blue.api", "green.api"},
            node_labels={"blue.api": "blue.api/", "green.api": "green.api/"},
            edges={Edge("green.api", "blue.api")},
            relative=False,
        )

    def test_shows_import_totals(self):
        grimp_graph = _build_fake_graph(SOME_ROOT_PACKAGE)

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=True,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=False,
        )

        assert dot == DotGraph(
            title=SOME_MODULE,
            concentrate=False,
            nodes={
                "mypackage.foo.green",
                "mypackage.foo.blue",
                "mypackage.foo.yellow",
                "mypackage.foo.red",
            },
            node_labels={
                "mypackage.foo.blue": ".blue/",
                "mypackage.foo.yellow": ".yellow/",
                "mypackage.foo.red": ".red/",
            },
            edges={
                Edge("mypackage.foo.blue", "mypackage.foo.green", label="1"),
                Edge("mypackage.foo.green", "mypackage.foo.yellow", label="1"),
                Edge("mypackage.foo.blue", "mypackage.foo.red", label="4"),
                Edge("mypackage.foo.red", "mypackage.foo.blue", label="1"),
            },
        )

    def test_shows_module_counts(self):
        grimp_graph = _build_fake_graph(SOME_ROOT_PACKAGE)

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=False,
            show_module_counts=True,
            show_lazy_imports=False,
            show_cycle_breakers=False,
        )

        assert dot.node_labels == {
            "mypackage.foo.blue": ".blue/\\n2",
            "mypackage.foo.yellow": ".yellow/\\n1",
            "mypackage.foo.red": ".red/\\n2",
        }

    def test_shows_cycle_breakers(self):
        grimp_graph = _build_fake_graph(SOME_ROOT_PACKAGE)

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=False,
            show_cycle_breakers=True,
        )

        assert dot == DotGraph(
            title=SOME_MODULE,
            concentrate=False,
            nodes={
                "mypackage.foo.green",
                "mypackage.foo.blue",
                "mypackage.foo.yellow",
                "mypackage.foo.red",
            },
            node_labels={
                "mypackage.foo.blue": ".blue/",
                "mypackage.foo.yellow": ".yellow/",
                "mypackage.foo.red": ".red/",
            },
            edges={
                Edge("mypackage.foo.blue", "mypackage.foo.green"),
                Edge("mypackage.foo.green", "mypackage.foo.yellow"),
                Edge("mypackage.foo.blue", "mypackage.foo.red"),
                Edge("mypackage.foo.red", "mypackage.foo.blue", style=EdgeStyle.DASHED),
            },
        )

    def test_shows_lazy_imports(self):
        grimp_graph = _build_fake_graph(SOME_ROOT_PACKAGE)

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=True,
            show_cycle_breakers=False,
        )

        assert dot == DotGraph(
            title=SOME_MODULE,
            concentrate=True,
            nodes={
                "mypackage.foo.green",
                "mypackage.foo.blue",
                "mypackage.foo.yellow",
                "mypackage.foo.red",
            },
            node_labels={
                "mypackage.foo.blue": ".blue/",
                "mypackage.foo.yellow": ".yellow/",
                "mypackage.foo.red": ".red/",
            },
            edges={
                # Eager dependency: unchanged.
                Edge("mypackage.foo.blue", "mypackage.foo.green"),
                # Wholly lazy dependency: solid line with an open arrowhead.
                Edge(
                    "mypackage.foo.green",
                    "mypackage.foo.yellow",
                    arrowhead=EdgeArrowhead.VEE,
                ),
                # Only partially lazy, so it stays a normal solid edge.
                Edge("mypackage.foo.blue", "mypackage.foo.red"),
                Edge("mypackage.foo.red", "mypackage.foo.blue"),
            },
        )

    def test_lazy_and_cycle_breaker_styling_compose(self):
        # A minimal cycle whose only breaker (b -> a) is itself wholly lazy.
        grimp_graph = ImportGraph()
        grimp_graph.add_module(SOME_ROOT_PACKAGE)
        grimp_graph.add_module(SOME_MODULE)
        grimp_graph.add_module(f"{SOME_MODULE}.a")
        grimp_graph.add_module(f"{SOME_MODULE}.b")
        grimp_graph.add_import(
            importer=f"{SOME_MODULE}.a",
            imported=f"{SOME_MODULE}.b",
            line_number=1,
            line_contents="import mypackage.foo.b",
        )
        grimp_graph.add_import(
            importer=f"{SOME_MODULE}.b",
            imported=f"{SOME_MODULE}.a",
            line_number=1,
            line_contents="lazy import mypackage.foo.a",
            is_lazy=True,
        )

        dot = build_dot_graph(
            grimp_graph,
            SOME_MODULE,
            show_import_totals=False,
            show_module_counts=False,
            show_lazy_imports=True,
            show_cycle_breakers=True,
        )

        assert dot.edges == {
            # Eager import: unchanged.
            Edge("mypackage.foo.a", "mypackage.foo.b"),
            # Both a cycle breaker and wholly lazy: the dashed line and open arrowhead compose.
            Edge(
                "mypackage.foo.b",
                "mypackage.foo.a",
                style=EdgeStyle.DASHED,
                arrowhead=EdgeArrowhead.VEE,
            ),
        }


class TestFormatModuleCount:
    @pytest.mark.parametrize(
        "count, expected",
        [
            (0, "0"),
            (1, "1"),
            (999, "999"),
            (1_000, "1,000"),
            (1_234_567, "1,234,567"),
        ],
    )
    def test_formats_with_thousands_separator(self, count, expected):
        assert _format_module_count(count) == expected
