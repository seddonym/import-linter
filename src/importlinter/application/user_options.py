from typing import Any


class InvalidUserOptions(Exception):
    pass


class UserOptions:
    """
    Configuration supplied by the end user.

    Arguments:
        - session_options:   General options relating to the running of the linter.
        - contracts_options: List of the options that will be used to build the contracts.
    """

    def __init__(
        self, session_options: dict[str, Any], contracts_options: list[dict[str, Any]]
    ) -> None:
        self.session_options = session_options
        self.contracts_options = contracts_options

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserOptions):
            return False
        return (self.session_options == other.session_options) and (
            self.contracts_options == other.contracts_options
        )
