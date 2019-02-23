import abc

from ..user_options import UserOptions


class UserOptionReader(abc.ABC):
    @abc.abstractmethod
    def set_options(self, user_options: UserOptions) -> None:
        raise NotImplementedError
