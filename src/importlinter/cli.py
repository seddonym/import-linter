import os
import sys
from logging import config as logging_config
from typing import Optional, Tuple, Type, Union

import click

from importlinter.application.sentinels import NotSupplied

from . import configuration
from .application import use_cases

configuration.configure()

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


@click.command()
@click.option("--config", default=None, help="The config file to use.")
@click.option(
    "--contract",
    default=list,
    multiple=True,
    help="Limit the check to the supplied contract identifier. May be passed multiple times.",
)
@click.option("--cache-dir", default=None, help="The directory to use for caching.")
@click.option("--no-cache", is_flag=True, help="Disable caching.")
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
    config: Optional[str],
    contract: Tuple[str, ...],
    cache_dir: Optional[str],
    no_cache: bool,
    debug: bool,
    show_timings: bool,
    verbose: bool,
) -> int:
    """
    Check that a project adheres to a set of contracts.
    """
    exit_code = lint_imports(
        config_filename=config,
        limit_to_contracts=contract,
        cache_dir=cache_dir,
        no_cache=no_cache,
        is_debug_mode=debug,
        show_timings=show_timings,
        verbose=verbose,
    )
    sys.exit(exit_code)


def lint_imports(
    config_filename: Optional[str] = None,
    limit_to_contracts: Tuple[str, ...] = (),
    cache_dir: Optional[str] = None,
    no_cache: bool = False,
    is_debug_mode: bool = False,
    show_timings: bool = False,
    verbose: bool = False,
) -> int:
    """
    Check that a project adheres to a set of contracts.

    This is the main function that runs the linter.

    Args:
        config_filename:    the filename to use to parse user options.
        limit_to_contracts: if supplied, only lint the contracts with the supplied ids.
        cache_dir:          the directory to use for caching, defaults to '.import_linter_cache'.
        no_cache:           if True, disable caching.
        is_debug_mode:      whether debugging should be turned on. In debug mode, exceptions are
                            not swallowed at the top level, so the stack trace can be seen.
        show_timings:       whether to show the times taken to build the graph and to check
                            each contract.
        verbose:            if True, noisily output progress as it goes along.

    Returns:
        EXIT_STATUS_SUCCESS or EXIT_STATUS_ERROR.
    """
    # Add current directory to the path, as this doesn't happen automatically.
    sys.path.insert(0, os.getcwd())

    _configure_logging(verbose)

    combined_cache_dir = _combine_caching_arguments(cache_dir, no_cache)

    passed = use_cases.lint_imports(
        config_filename=config_filename,
        limit_to_contracts=limit_to_contracts,
        cache_dir=combined_cache_dir,
        is_debug_mode=is_debug_mode,
        show_timings=show_timings,
        verbose=verbose,
    )

    if passed:
        return EXIT_STATUS_SUCCESS
    else:
        return EXIT_STATUS_ERROR


def _combine_caching_arguments(
    cache_dir: Optional[str], no_cache: bool
) -> Union[str, None, Type[NotSupplied]]:
    if no_cache:
        return None
    if cache_dir is None:
        return NotSupplied
    return cache_dir


def _configure_logging(verbose: bool) -> None:
    logger_names = ("importlinter", "grimp", "_rustgrimp")
    logging_config.dictConfig(
        {
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO" if verbose else "WARNING",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                logger_name: {
                    "level": "INFO",
                    "handlers": ["console"],
                }
                for logger_name in logger_names
            },
        }
    )
