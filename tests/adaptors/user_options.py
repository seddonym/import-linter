from importlinter.application.user_options import UserOptions

from importlinter.application.ports.user_options import UserOptionReader


class FakeUserOptionReader(UserOptionReader):
    def __init__(self):
        _user_options = None

    def set(self, user_options: UserOptions) -> None:
        self._user_options = user_options

    def read(self):
        return self._user_options
