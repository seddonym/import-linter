import os
import sys
from typing import Optional

import click

from .adapters.building import GraphBuilder
from .adapters.filesystem import FileSystem
from .adapters.printing import ClickPrinter
from .adapters.user_options import IniFileUserOptionReader
from .application import use_cases
from .application.app_config import settings

settings.configure(
    USER_OPTION_READERS=[IniFileUserOptionReader()],
    GRAPH_BUILDER=GraphBuilder(),
    PRINTER=ClickPrinter(),
    FILE_SYSTEM=FileSystem(),
)

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
@click.option("--config", default=None, help="The config file to use.")
@click.option("--debug", is_flag=True, help="Run in debug mode.")
def lint_imports_command(config: Optional[str], debug: bool) -> int:
    """
    The entry point for the CLI command.
    """
    exit_code = lint_imports(config_filename=config, is_debug_mode=debug)
    sys.exit(exit_code)


def lint_imports(config_filename: Optional[str] = None, is_debug_mode: bool = False) -> int:
    """
    Check that a project adheres to a set of contracts.

    This is the main function that runs the linter.

    Args:
        config_filename: The configuration file to use. If not supplied, Import Linter will look
                         for setup.cfg or .importlinter in the current directory.
        is_debug_mode:   Whether debugging should be turned on. In debug mode, exceptions are
                         not swallowed at the top level, so the stack trace can be seen.

    Returns:
        EXIT_STATUS_SUCCESS or EXIT_STATUS_ERROR.
    """
    # Add current directory to the path, as this doesn't happen automatically.
    sys.path.insert(0, os.getcwd())

    passed = use_cases.lint_imports(config_filename=config_filename, is_debug_mode=is_debug_mode)

    if passed:
        return EXIT_STATUS_SUCCESS
    else:
        return EXIT_STATUS_ERROR
