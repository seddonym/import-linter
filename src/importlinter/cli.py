import os
import sys
from typing import Optional

import click

from . import configuration
from .application import use_cases

configuration.configure()

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
@click.option("--config", default=None, help="The config file to use.")
@click.option("--debug", is_flag=True, help="Run in debug mode.")
@click.option(
    "--show-timings",
    is_flag=True,
    help="Show times taken to build the graph and to check each contract.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Noisily output progress as we go along.",
)
def lint_imports_command(
    config: Optional[str], debug: bool, show_timings: bool, verbose: bool
) -> int:
    """
    The entry point for the CLI command.
    """
    exit_code = lint_imports(
        config_filename=config, is_debug_mode=debug, show_timings=show_timings, verbose=verbose
    )
    sys.exit(exit_code)


def lint_imports(
    config_filename: Optional[str] = None,
    is_debug_mode: bool = False,
    show_timings: bool = False,
    verbose: bool = False,
) -> int:
    """
    Check that a project adheres to a set of contracts.

    This is the main function that runs the linter.

    Args:
        config_filename: The configuration file to use. If not supplied, Import Linter will look
                         for setup.cfg or .importlinter in the current directory.
        is_debug_mode:   Whether debugging should be turned on. In debug mode, exceptions are
                         not swallowed at the top level, so the stack trace can be seen.
        show_timings:    Whether to show the times taken to build the graph and to check
                         each contract.
        verbose:         If True, noisily output progress as we go along.

    Returns:
        EXIT_STATUS_SUCCESS or EXIT_STATUS_ERROR.
    """
    # Add current directory to the path, as this doesn't happen automatically.
    sys.path.insert(0, os.getcwd())

    passed = use_cases.lint_imports(
        config_filename=config_filename,
        is_debug_mode=is_debug_mode,
        show_timings=show_timings,
        verbose=verbose,
    )

    if passed:
        return EXIT_STATUS_SUCCESS
    else:
        return EXIT_STATUS_ERROR
