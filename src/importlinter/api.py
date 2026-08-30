"""
Module for public-facing Python functions.
"""

from __future__ import annotations
from typing import Optional, Type

from importlinter.application import use_cases
from importlinter.application.ports.reporting import Report
from importlinter.application.sentinels import NotSupplied

from . import configuration

configuration.configure()


def read_configuration(config_filename: str | None = None) -> dict:
    """
    Return a dictionary containing configuration from the supplied file.

    If no filename is supplied, look in the default location
    (see importlinter.cli.lint_imports).

    The dictionary has two keys:
        "session_options": dictionary of strings passed as top level configuration.
        "contracts_options": list of dictionaries, one for each contract, keyed with:
            "name": the name of the contract (str).
            "type": the type of the contract (str).
            (Any other contract-specific configuration.)

    This function is designed for use by external projects wishing to
    analyse the contracts themselves, e.g. to track the number of
    ignored imports.

    Raises:
        FileNotFoundError if no configuration file could be found.
    """
    user_options = use_cases.read_user_options(config_filename)
    return {
        "session_options": user_options.session_options,
        "contracts_options": user_options.contracts_options,
    }


class FailedToCreateReport(Exception):
    """
    Opaque exception raised by create_report if an internal exception is raised by create_report
    (below), including if the exception occurs when reading the user's configuration.
    """
    pass


def create_report(
    config_filename: Optional[str] = None,
    limit_to_contracts: tuple[str, ...] = (),
    cache_dir: str | None | Type[NotSupplied] = NotSupplied,
    is_debug_mode: bool = False,
    # show_timings: bool = False,
    # verbose: bool = False,
) -> Report:
    """
    Create a report of the import contracts.

    Args:
        config_filename:    Filepath for the configuration (e.g. .importlinter, pyproject.toml).
                            If not provided, the default location will be checked.
        limit_to_contracts: If supplied, only report on contracts with the supplied ids.
        cache_dir:          Filepath to cache directory. Pass None to explicitly disable caching; if
                            omitted, import-linter's default cache directory will be used.
        is_debug_mode:      Set to True to raise full internal exceptions with stack traces. By
                            default, exceptions will be rescued and instead a simple opaque
                            exception will be raised.

    Raises:
        FailedToCreateReport if an internal exception is raised.
        Other exceptions may be raised if is_debug_mode is True.


    Not yet implemented::
        show_timings:       whether to show the times taken to build the graph and to check
                            each contract.
        verbose:            if True, noisily output progress as it goes along.
    """
    try:
        user_options = use_cases.read_user_options(config_filename)
        use_cases._register_contract_types(user_options)
        report = use_cases.create_report(
            user_options,
            limit_to_contracts=limit_to_contracts,
            cache_dir=cache_dir,
            show_timings=False,
            verbose=False,
        )
        return report
    except Exception as e:
        if is_debug_mode:
            raise e
        else:
            raise FailedToCreateReport(e)
