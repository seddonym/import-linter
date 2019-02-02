from typing import Iterable

from ..domain.contract import Contract


class UserOptions:
    """
    Configuration supplied by the end user.
    """
    def __init__(self, root_package_name: str, contracts: Iterable[Contract]) -> None:
        self.root_package_name = root_package_name
        self.contracts = contracts
