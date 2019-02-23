import textwrap

from importlinter.application.ports.printing import Printer


class FakePrinter(Printer):
    def __init__(self) -> None:
        self._buffer = ""

    def print(self, string: str) -> None:
        dedented_string = textwrap.dedent(string)
        self._buffer += dedented_string

    def pop_and_assert(self, expected_string):
        """
        Assert that the string is what is in the buffer, removing it from the buffer.
        """
        popped_string = self._buffer
        self._buffer = ""
        assert popped_string == textwrap.dedent(expected_string)
