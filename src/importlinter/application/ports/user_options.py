import abc
from typing import Optional

from ..user_options import UserOptions


class UserOptionReader(abc.ABC):
    @abc.abstractmethod
    def read_options(self, config_filename: Optional[str] = None) -> Optional[UserOptions]:
        raise NotImplementedError
