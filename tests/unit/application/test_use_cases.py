from typing import List, Optional
from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS, FAILURE
from importlinter.domain.contract import Contract
from importlinter.domain.imports import Module

from tests.adapters.user_options import FakeUserOptionReader
from tests.adapters.graph import FakeGraph
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter
from tests.helpers.contracts import (
    AlwaysPassesContract, AlwaysFailsContract, ForbiddenImportContract,
)


class TestCheckContractsAndPrintReport:
    printer = FakePrinter()

    def test_all_successful(self):
        self._configure(
            contracts=[
                AlwaysPassesContract(name='Contract foo'),
                AlwaysPassesContract(name='Contract bar'),
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
            contracts=[
                AlwaysFailsContract(name='Contract foo'),
                AlwaysPassesContract(name='Contract bar'),
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
            import_details=(
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
            ),
        )
        self._configure(
            contracts=[
                AlwaysPassesContract(name='Contract foo'),
                ForbiddenImportContract(
                    name='Forbidden contract one',
                    importer=Module('mypackage.foo'),
                    imported=Module('mypackage.bar'),
                ),
                ForbiddenImportContract(
                    name='Forbidden contract two',
                    importer=Module('mypackage.foo'),
                    imported=Module('mypackage.baz'),
                ),
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
        contracts: List[Contract],
        graph: Optional[FakeGraph] = None,
    ):
        reader = FakeUserOptionReader(
            UserOptions(
                root_package_name='mypackage',
                contracts=contracts,
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
