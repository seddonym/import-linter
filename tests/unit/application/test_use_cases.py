import string
from typing import Any, Dict, List, Optional

import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore
from importlinter.application.app_config import settings
from importlinter.application.use_cases import FAILURE, SUCCESS, create_report, lint_imports
from importlinter.application.user_options import UserOptions

from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter
from tests.adapters.user_options import ExceptionRaisingUserOptionReader, FakeUserOptionReader


class TestCheckContractsAndPrintReport:
    def test_all_successful(self):
        self._configure(
            contracts_options=[
                {"type": "always_passes", "name": "Contract foo"},
                {"type": "always_passes", "name": "Contract bar"},
            ]
        )

        result = lint_imports()

        assert result == SUCCESS

        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

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

        result = lint_imports()

        assert result == FAILURE

        settings.PRINTER.pop_and_assert(
            """
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

        result = lint_imports()

        assert result == FAILURE

        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

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

        result = lint_imports()

        assert result == FAILURE

        # Expecting 28 files (default graph has 26 modules, we add 2).
        # Expecting 11 dependencies (default graph has 10 imports, we add 2,
        # but it counts as 1 as it's between the same modules).
        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

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

    @pytest.mark.xfail
    def test_debug_mode_doesnt_swallow_exception(self):
        some_exception = RuntimeError("There was some sort of exception.")
        reader = ExceptionRaisingUserOptionReader(exception=some_exception)
        settings.configure(
            USER_OPTION_READERS=[reader], GRAPH_BUILDER=FakeGraphBuilder(), PRINTER=FakePrinter()
        )

        with pytest.raises(some_exception.__class__, match=str(some_exception)):
            lint_imports(is_debug_mode=True)

    def test_non_debug_mode_prints_exception(self):
        some_exception = RuntimeError("There was some sort of exception.")
        reader = ExceptionRaisingUserOptionReader(exception=some_exception)
        settings.configure(
            USER_OPTION_READERS=[reader], GRAPH_BUILDER=FakeGraphBuilder(), PRINTER=FakePrinter()
        )

        lint_imports(is_debug_mode=False)

        settings.PRINTER.pop_and_assert(
            """There was some sort of exception.
            """
        )

    def _configure(
        self,
        contracts_options: List[Dict[str, Any]],
        contract_types: Optional[List[str]] = None,
        graph: Optional[ImportGraph] = None,
    ):
        session_options = {"root_package": "mypackage"}
        if not contract_types:
            contract_types = [
                "always_passes: tests.helpers.contracts.AlwaysPassesContract",
                "always_fails: tests.helpers.contracts.AlwaysFailsContract",
                "fields: tests.helpers.contracts.FieldsContract",
                "forbidden: tests.helpers.contracts.ForbiddenImportContract",
            ]
        session_options["contract_types"] = contract_types  # type: ignore

        reader = FakeUserOptionReader(
            UserOptions(session_options=session_options, contracts_options=contracts_options)
        )
        settings.configure(
            USER_OPTION_READERS=[reader], GRAPH_BUILDER=FakeGraphBuilder(), PRINTER=FakePrinter()
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
        settings.configure(GRAPH_BUILDER=builder, PRINTER=FakePrinter())

        create_report(
            UserOptions(
                session_options={"root_packages": root_package_names}, contracts_options=[]
            )
        )

        assert builder.build_arguments["root_package_names"] == root_package_names
