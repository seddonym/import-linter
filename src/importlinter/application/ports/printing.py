import abc


class Printer(abc.ABC):
    @abc.abstractmethod
    def print(self, string: str) -> None:
        raise NotImplementedError
