from typing import List, Optional, Dict, Any
from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS, FAILURE

from tests.adapters.user_options import FakeUserOptionReader
from tests.adapters.graph import FakeGraph
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter


class TestCheckContractsAndPrintReport:
    def test_all_successful(self):
        self._configure(
            contracts_options=[
                {
                    'type': 'always_passes',
                    'name': 'Contract foo',
                },
                {
                    'type': 'always_passes',
                    'name': 'Contract bar',
                },
            ]
        )

        result = check_contracts_and_print_report()

        assert result == SUCCESS

        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

            ---------
            Contracts
            ---------

            Analyzed 23 files, 44 dependencies.
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
                    'type': 'fields',
                    'name': 'Contract foo',
                    'single_field': ['one', 'two'],
                    'multiple_field': 'one',
                    'import_field': 'foobar',
                },
                {
                    'type': 'always_passes',
                    'name': 'Contract bar',
                },
            ]
        )

        result = check_contracts_and_print_report()

        assert result == FAILURE

        settings.PRINTER.pop_and_assert(
            """
            Contract foo is not configured correctly:

            - single_field: Expected a single value, got multiple values.
            - multiple_field: Expected multiple values, got a single value.
            - import_field: Must be in the form "package.importer -> package.imported".
            - required_field: This is a required field.
            """
        )

    def test_one_failure(self):
        self._configure(
            contracts_options=[
                {
                    'type': 'always_fails',
                    'name': 'Contract foo',
                },
                {
                    'type': 'always_passes',
                    'name': 'Contract bar',
                },
            ]
        )

        result = check_contracts_and_print_report()

        assert result == FAILURE

        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

            ---------
            Contracts
            ---------

            Analyzed 23 files, 44 dependencies.
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
        graph = FakeGraph(
            root_package_name='mypackage',
            import_details=[
                {
                    'importer': 'mypackage.foo',
                    'imported': 'mypackage.bar',
                    'line_number': 8,
                    'line_contents': 'from mypackage import bar',
                },
                {
                    'importer': 'mypackage.foo',
                    'imported': 'mypackage.bar',
                    'line_number': 16,
                    'line_contents': 'from mypackage.bar import something',
                },
            ],
        )
        self._configure(
            contracts_options=[
                {
                    'type': 'always_passes',
                    'name': 'Contract foo',
                },
                {
                    'type': 'forbidden',
                    'name': 'Forbidden contract one',
                    'importer': 'mypackage.foo',
                    'imported': 'mypackage.bar',
                },
                {
                    'type': 'forbidden',
                    'name': 'Forbidden contract two',
                    'importer': 'mypackage.foo',
                    'imported': 'mypackage.baz',
                },
            ],
            graph=graph,
        )

        result = check_contracts_and_print_report()

        assert result == FAILURE

        settings.PRINTER.pop_and_assert(
            """
            =============
            Import Linter
            =============

            ---------
            Contracts
            ---------

            Analyzed 99 files, 999 dependencies.
            ------------------------------------

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

    def _configure(
        self,
        contracts_options: List[Dict[str, Any]],
        contract_types: Optional[List[str]] = None,
        graph: Optional[FakeGraph] = None,
    ):
        session_options = {
            'root_package_name': 'mypackage',
        }
        if not contract_types:
            contract_types = [
                'always_passes: tests.helpers.contracts.AlwaysPassesContract',
                'always_fails: tests.helpers.contracts.AlwaysFailsContract',
                'fields: tests.helpers.contracts.FieldsContract',
                'forbidden: tests.helpers.contracts.ForbiddenImportContract',
            ]
        session_options['contract_types'] = contract_types  # type: ignore

        reader = FakeUserOptionReader(
            UserOptions(
                session_options=session_options,
                contracts_options=contracts_options,
            )
        )
        settings.configure(
            USER_OPTION_READERS=[reader],
            GRAPH_BUILDER=FakeGraphBuilder(),
            PRINTER=FakePrinter(),
        )
        if graph is None:
            graph = FakeGraph(
                root_package_name='mypackage',
                module_count=23,
                import_count=44,
            )
        settings.GRAPH_BUILDER.set_graph(graph)
