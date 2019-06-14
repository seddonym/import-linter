import abc
from typing import Optional


class Printer(abc.ABC):
    @abc.abstractmethod
    def print(
        self, text: str = "", bold: bool = False, color: Optional[str] = None, newline: bool = True
    ) -> None:
        """
        Prints a line.
        """
        raise NotImplementedError
