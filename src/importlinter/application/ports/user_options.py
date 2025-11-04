import abc

from ..user_options import UserOptions


class UserOptionReader(abc.ABC):
    @abc.abstractmethod
    def read_options(self, config_filename: str | None = None) -> UserOptions | None:
        raise NotImplementedError
