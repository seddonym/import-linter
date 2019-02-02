import click

from .application.use_cases import analyse_and_report, AlreadyReportedError
from .application.app_config import settings
from .adaptors.graph import build_graph
from .adaptors.rendering import report_exception, render_report

settings.configure(
    BUILD_GRAPH=build_graph,
    REPORT_EXCEPTION=report_exception,
    RENDER_REPORT=render_report,
)

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
def main():
    try:
        analyse_and_report()
    except AlreadyReportedError:
        return EXIT_STATUS_ERROR
    else:
        return EXIT_STATUS_SUCCESS
