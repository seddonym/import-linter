import importlib
import os
import sys
from logging import config as logging_config
import grimp


import click

from importlinter.application.sentinels import NotSupplied

from . import configuration
from .application import use_cases
from .application import rendering

configuration.configure()

EXIT_STATUS_SUCCESS = 0
EXIT_STATUS_ERROR = 1


def check_options(f):
    """Decorator that applies all check command options."""
    f = click.option(
        "--verbose",
        is_flag=True,
        help="Noisily output progress as we go along.",
    )(f)
    f = click.option(
        "--show-timings",
        is_flag=True,
        help="Show times taken to build the graph and to check each contract.",
    )(f)
    f = click.option("--debug", is_flag=True, help="Run in debug mode.")(f)
    f = click.option("--no-cache", is_flag=True, help="Disable caching.")(f)
    f = click.option("--cache-dir", default=None, help="The directory to use for caching.")(f)
    f = click.option(
        "--contract",
        default=list,
        multiple=True,
        help="Limit the check to the supplied contract identifier. May be passed multiple times.",
    )(f)
    f = click.option("--config", default=None, help="The config file to use.")(f)
    return f


def _run_check(
    config: str | None,
    contract: tuple[str, ...],
    cache_dir: str | None,
    no_cache: bool,
    debug: bool,
    show_timings: bool,
    verbose: bool,
) -> None:
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


@click.command()
@check_options
def lint_imports_command(**kwargs) -> None:
    """Check that a project adheres to a set of contracts."""
    _run_check(**kwargs)


@click.group(invoke_without_command=True)
@click.pass_context
def import_linter(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        rendering.print_title()
        click.echo(ctx.get_help())


@import_linter.command("lint")
@check_options
def lint_command(**kwargs) -> None:
    """Check that a project adheres to a set of contracts."""
    _run_check(**kwargs)


@import_linter.command()
@click.argument("module_name")
def explore(module_name: str) -> None:
    """Launch the interactive UI in a local browser.

    MODULE_NAME is the importable Python module to explore (e.g. 'django.db.models').
    """
    try:
        server = importlib.import_module("importlinter.ui.server")
    except ImportError:
        click.echo(
            "The 'explore' command requires additional dependencies. "
            "Install them with: pip install import-linter[ui]",
            err=True,
        )
        sys.exit(1)
    rendering.print_title()
    server.launch(module_name)


@import_linter.command()
@click.argument("module_name")
@click.option("--show-import-totals", is_flag=True, help="Label arrows with import counts.")
@click.option(
    "--show-cycle-breakers",
    is_flag=True,
    help="Mark dependencies that, if removed, would make the graph acyclic.",
)
def drawgraph(module_name: str, show_import_totals: bool, show_cycle_breakers: bool) -> None:
    """Output a DOT format graph of a module's dependencies to stdout.

    MODULE_NAME is the importable Python module to graph (e.g. 'django.db.models').
    """
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    top_level_package = module_name.split(".")[0]
    try:
        __import__(top_level_package)
    except ImportError:
        click.echo(
            f"Could not import '{top_level_package}'. "
            f"Make sure the package is installed or the current directory contains it.",
            err=True,
        )
        sys.exit(1)

    grimp_graph = grimp.build_graph(top_level_package)
    dot = use_cases.build_dot_graph(
        grimp_graph, module_name, show_import_totals, show_cycle_breakers
    )
    click.echo(dot.render(), nl=False)


def lint_imports(
    config_filename: str | None = None,
    limit_to_contracts: tuple[str, ...] = (),
    cache_dir: str | None = None,
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
    cache_dir: str | None, no_cache: bool
) -> str | None | type[NotSupplied]:
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
