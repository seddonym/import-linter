from importlinter.application.user_options import UserOptions

from importlinter.application.ports.user_options import UserOptionReader


class FakeUserOptionReader(UserOptionReader):
    def __init__(self, user_options: UserOptions):
        self._user_options = user_options

    def read_options(self) -> UserOptions:
        return self._user_options
