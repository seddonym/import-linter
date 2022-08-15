"""
Module for public-facing Python functions.
"""
from __future__ import annotations

from importlinter.application import use_cases

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
