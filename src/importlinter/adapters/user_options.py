from importlinter.application.user_options import UserOptions
from importlinter.application.ports import user_options as ports


class UserOptionReader(ports.UserOptionReader):
    def read_options(self) -> UserOptions:
        raise NotImplementedError
