from importlinter.application.app_config import settings
from importlinter.application.user_options import UserOptions
from importlinter.application.use_cases import check_contracts_and_print_report, SUCCESS

from tests.adapters.user_options import FakeUserOptionReader
from tests.adapters.graph import FakeGraph
from tests.adapters.building import FakeGraphBuilder
from tests.adapters.printing import FakePrinter
from tests.helpers.contracts import AlwaysPassesContract


def test_check_contracts_and_print_report():
    settings.configure(
        USER_OPTION_READER=FakeUserOptionReader(),
        GRAPH_BUILDER=FakeGraphBuilder(),
        PRINTER=FakePrinter(),
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

    assert result == SUCCESS
