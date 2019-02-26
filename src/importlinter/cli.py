import click

from .application.use_cases import check_contracts_and_print_report, AlreadyReportedError
from .application.app_config import settings
from .adapters.building import GraphBuilder
from .adapters.printing import ClickPrinter
from .adapters.user_options import UserOptionReader


settings.configure(
    USER_OPTION_READERS=[UserOptionReader()],
    GRAPH_BUILDER=GraphBuilder(),
    PRINTER=ClickPrinter(),
)

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
def main():
    try:
        check_contracts_and_print_report()
    except AlreadyReportedError:
        return EXIT_STATUS_ERROR
    else:
        return EXIT_STATUS_SUCCESS
