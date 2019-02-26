from typing import List, Optional, Dict, Any
from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS, FAILURE

from tests.adapters.user_options import FakeUserOptionReader
from tests.adapters.graph import FakeGraph
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter


class TestCheckContractsAndPrintReport:
    printer = FakePrinter()

    def test_all_successful(self):
        self._configure(
            contracts_options=[
                {
                    'class': 'tests.helpers.contracts.AlwaysPassesContract',
                    'name': 'Contract foo',
                },
                {
                    'class': 'tests.helpers.contracts.AlwaysPassesContract',
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

    def test_one_failure(self):
        self._configure(
            contracts_options=[
                {
                    'class': 'tests.helpers.contracts.AlwaysFailsContract',
                    'name': 'Contract foo',
                },
                {
                    'class': 'tests.helpers.contracts.AlwaysPassesContract',
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
                    'class': 'tests.helpers.contracts.AlwaysPassesContract',
                    'name': 'Contract foo',
                },
                {
                    'class': 'tests.helpers.contracts.ForbiddenImportContract',
                    'name': 'Forbidden contract one',
                    'importer': 'mypackage.foo',
                    'imported': 'mypackage.bar',
                },
                {
                    'class': 'tests.helpers.contracts.ForbiddenImportContract',
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
        graph: Optional[FakeGraph] = None,
    ):
        reader = FakeUserOptionReader(
            UserOptions(
                session_options={
                    'root_package_name': 'mypackage',
                },
                contracts_options=contracts_options,
            )
        )
        settings.configure(
            USER_OPTION_READERS=[reader],
            GRAPH_BUILDER=FakeGraphBuilder(),
            PRINTER=self.printer,
        )
        if graph is None:
            graph = FakeGraph(
                root_package_name='mypackage',
                module_count=23,
                import_count=44,
            )
        settings.GRAPH_BUILDER.set_graph(graph)
