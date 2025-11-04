from importlinter.application.ports.user_options import UserOptionReader
from importlinter.application.user_options import UserOptions


class FakeUserOptionReader(UserOptionReader):
    def __init__(self, user_options: UserOptions):
        self._user_options = user_options

    def read_options(self, config_filename: str | None = None) -> UserOptions | None:
        return self._user_options


class ExceptionRaisingUserOptionReader(UserOptionReader):
    def __init__(self, exception: Exception):
        self._exception = exception

    def read_options(self, config_filename: str | None = None) -> UserOptions | None:
        raise self._exception
