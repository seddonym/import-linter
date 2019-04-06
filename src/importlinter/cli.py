from typing import Optional
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
@click.option('--config', default=None, help='The config file to use.')
def lint_imports_command(config: Optional[str]) -> int:
    """
    The entry point for the CLI command.
    """
    exit_code = lint_imports(config_filename=config)
    sys.exit(exit_code)


def lint_imports(config_filename: Optional[str] = None) -> int:
    """
    Check that a project adheres to a set of contracts.

    This is the main function that runs the linter.

    Args:
        config_filename: The configuration file to use. If not supplied, Import Linter will look
        for setup.cfg or .importlinter in the current directory.

    Returns:
        EXIT_STATUS_SUCCESS or EXIT_STATUS_ERROR.
    """
    # Add current directory to the path, as this doesn't happen automatically.
    sys.path.insert(0, os.getcwd())

    passed = use_cases.lint_imports(config_filename=config_filename)

    if passed:
        return EXIT_STATUS_SUCCESS
    else:
        return EXIT_STATUS_ERROR
