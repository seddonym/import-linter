import abc


class Printer(abc.ABC):
    @abc.abstractmethod
    def print(
        self,
        text: str = "",
        bold: bool = False,
        color: str | None = None,
        newline: bool = True,
        as_log: bool = False,
    ) -> None:
        """
        Prints a line.
        """
        raise NotImplementedError
