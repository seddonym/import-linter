from typing import Optional
import abc

from ..user_options import UserOptions


class UserOptionReader(abc.ABC):
    @abc.abstractmethod
    def read_options(self) -> Optional[UserOptions]:
        raise NotImplementedError
