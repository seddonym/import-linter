from importlinter.application.user_options import UserOptions
from importlinter.application.ports import user_options as ports


class UserOptionReader(ports.UserOptionReader):
    def set_options(self, user_options: UserOptions) -> None:
        raise NotImplementedError
