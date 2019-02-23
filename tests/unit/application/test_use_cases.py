from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS, FAILURE

from tests.adaptors.user_options import FakeUserOptionReader
from tests.adaptors.graph import FakeGraphBuilder, FakeGraph
from tests.adaptors.printing import FakePrinter
from tests.helpers.contracts import AlwaysPassesContract


def test_check_contracts_and_print_report():
    settings.configure(
        USER_OPTION_READER=FakeUserOptionReader(),
        GRAPH_BUILDER=FakeGraphBuilder(),
        EXCEPTION_PRINTER=FakePrinter(),
        REPORT_PRINTER=FakePrinter(),
    )
    settings.USER_OPTION_READER.set_options(
        UserOptions(
            root_package_name='mypackage',
            contracts=(
                AlwaysPassesContract(name='Contract foo'),
                AlwaysPassesContract(name='Contract bar'),
            )
        )
    )
    settings.GRAPH_BUILDER.set_graph(
        FakeGraph(
            root_package_name='mypackage',
        )
    )

    result = check_contracts_and_print_report()

    settings.REPORT_PRINTER.pop_and_assert("""
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
    """)

    assert result == SUCCESS

