import abc

from .reporting import Report


class Printer(abc.ABC):
    @abc.abstractmethod
    def print(self, report: Report) -> None:
        raise NotImplementedError
