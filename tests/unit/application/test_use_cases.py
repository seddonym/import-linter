from typing import List
from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS
from importlinter.domain.contract import Contract

from tests.adapters.user_options import FakeUserOptionReader
from tests.adapters.graph import FakeGraph
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter
from tests.helpers.contracts import AlwaysPassesContract, AlwaysFailsContract


class TestCheckContractsAndPrintReport:
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

    def _configure(self, contracts: List[Contract]):
        settings.configure(
            USER_OPTION_READER=FakeUserOptionReader(),
            GRAPH_BUILDER=FakeGraphBuilder(),
            PRINTER=FakePrinter(),
        )
        settings.USER_OPTION_READER.set_options(
            UserOptions(
                root_package_name='mypackage',
                contracts=contracts,
            )
        )
        settings.GRAPH_BUILDER.set_graph(
            FakeGraph(
                root_package_name='mypackage',
            )
        )
