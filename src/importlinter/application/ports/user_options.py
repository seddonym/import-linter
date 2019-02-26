import abc

from ..user_options import UserOptions


class UserOptionReader(abc.ABC):
    @abc.abstractmethod
    def read_options(self) -> UserOptions:
        raise NotImplementedError
