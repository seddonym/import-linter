from typing import List, Dict, Any


class UserOptions:
    """
    Configuration supplied by the end user.
    """
    def __init__(
        self,
        session_options: Dict[str, Any],
        contracts_options: List[Dict[str, Any]],
    ) -> None:
        self.session_options = session_options
        self.contracts_options = contracts_options
