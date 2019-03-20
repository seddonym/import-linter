import sys
import os

import click

from .application import use_cases
from .application.app_config import settings
from .adapters.building import GraphBuilder
from .adapters.printing import ClickPrinter
from .adapters.filesystem import FileSystem
from .adapters.user_options import IniFileUserOptionReader


settings.configure(
    USER_OPTION_READERS=[
        IniFileUserOptionReader(),
    ],
    GRAPH_BUILDER=GraphBuilder(),
    PRINTER=ClickPrinter(),
    FILE_SYSTEM=FileSystem(),
)

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
def lint_imports_command():
    lint_imports()


def lint_imports():
    # Add current directory to the path, as this doesn't happen automatically.
    sys.path.insert(0, os.getcwd())

    passed = use_cases.lint_imports()

    if passed:
        return EXIT_STATUS_SUCCESS
    else:
        return EXIT_STATUS_ERROR
